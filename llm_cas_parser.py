"""LLM-based CAS parser — infers alignment dimensions from free-text descriptions.

The user provides two things:
  1. The CLAIM (what they want to demonstrate, for which device, for which population)
  2. The STUDY (what study they have, what device it tested, what population, where)

The LLM infers the 3 CAS dimensions: device match, population match, context match.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import anthropic

_client = None

SYSTEM_PROMPT = """Tu es un expert en évaluation réglementaire des dispositifs médicaux (CNEDiMTS/HAS).

Ta tâche : comparer la REVENDICATION d'un demandeur avec l'ÉTUDE qu'il fournit comme preuve, et déterminer l'ALIGNEMENT entre les deux sur 3 dimensions.

## Dimension 1 : DEVICE (Alignement dispositif)
Compare le dispositif revendiqué et le dispositif étudié.
- "EXACT_DEVICE" : c'est exactement le même dispositif (même modèle, même version, même fabricant)
- "SAME_FAMILY" : même fabricant ou même famille technologique, mais version différente, ou données d'un prédécesseur direct
- "PROXY_DEVICE" : dispositif d'un autre fabricant utilisé comme proxy, ou technologie similaire mais pas le même produit
- "DIFFERENT_DEVICE" : aucune donnée spécifique au dispositif, études portant sur d'autres dispositifs/technologies
- "UNKNOWN" : impossible de déterminer

## Dimension 2 : POPULATION (Alignement population)
Compare la population cible de la revendication et la population étudiée.
- "EXACT_INDICATION" : la population étudiée correspond exactement à l'indication revendiquée
- "NARROWER_SUBGROUP" : l'étude couvre un sous-groupe de l'indication (ex: seulement les cas légers, seulement un type de traitement)
- "BROADER_POPULATION" : l'étude inclut une population plus large que l'indication (ex: critères d'inclusion plus larges, sévérité différente)
- "DIFFERENT_POPULATION" : la population étudiée ne correspond pas à l'indication revendiquée
- "UNKNOWN" : impossible de déterminer

## Dimension 3 : CONTEXT (Alignement contexte de soins)
Compare le contexte de l'étude et le contexte cible de déploiement (France par défaut).
- "SAME_HEALTHCARE_SYSTEM" : étude réalisée dans le même système de soins, parcours de soins comparable
- "PARTIALLY_COMPARABLE" : étude dans un pays/système partiellement comparable, ou étude monocentrique avec extrapolation limitée
- "DIFFERENT_SYSTEM" : système de soins fondamentalement différent (ex: USA vs France pour un parcours de soins spécifique)
- "UNKNOWN" : impossible de déterminer

## Champs complémentaires
- care_pathway_match : "YES" (parcours identique), "PARTIAL" (similaire avec des écarts), "NO" (parcours différent), "UNKNOWN"
- eligibility_shift : "NONE" (pas d'écart), "MINOR" (écarts mineurs), "MAJOR" (écarts importants dans les critères d'inclusion/sévérité)
- organization_dependency : "LOW" (résultat peu dépendant de l'organisation), "MEDIUM", "HIGH" (résultat très dépendant de l'organisation de soins, ex: télésurveillance)

## Instructions
- Sois STRICT dans ton évaluation. Si l'étude porte sur un autre dispositif, c'est PROXY_DEVICE ou DIFFERENT_DEVICE, pas SAME_FAMILY.
- Regarde les NOMS des dispositifs. Si le nom diffère entre claim et étude, c'est au minimum SAME_FAMILY.
- Pour la population, regarde les CRITÈRES D'INCLUSION, pas juste la pathologie générale.
- Pour le contexte, le parcours de soins français a ses spécificités (OAM avant SAOS, recommandations HAS, etc.)
- Fournis des justifications courtes mais précises.

## Traçabilité (obligatoire)
Pour CHAQUE dimension (device_alignment, population_alignment, context_alignment), fournis
un champ "source_quote" : une citation VERBATIM (copiée mot pour mot, sans paraphrase) de
l'ÉTUDE qui soutient directement le verdict donné. Si le verdict est "UNKNOWN", ou si aucun
passage précis du texte ne le justifie, laisse "source_quote" vide ("") plutôt que d'inventer
ou de paraphraser une citation — une citation inventée est pire qu'une absence de citation.

Réponds UNIQUEMENT en JSON valide."""

USER_TEMPLATE = """Compare cette REVENDICATION et cette ÉTUDE pour déterminer l'alignement :

## REVENDICATION (ce que le demandeur veut démontrer)
{claim_text}

## ÉTUDE (les données cliniques fournies)
{study_text}

Réponds en JSON avec ce format exact :
{{
  "claim_parsed": {{
    "device_name": "...",
    "target_population": "...",
    "intended_benefit": "...",
    "domain": "..."
  }},
  "study_parsed": {{
    "device_name": "...",
    "study_population": "...",
    "study_country": "...",
    "study_design_brief": "..."
  }},
  "device_alignment": {{
    "device_match_type": "EXACT_DEVICE" | "SAME_FAMILY" | "PROXY_DEVICE" | "DIFFERENT_DEVICE" | "UNKNOWN",
    "device_description_claim": "...",
    "device_description_study": "...",
    "justification": "...",
    "source_quote": "..."
  }},
  "population_alignment": {{
    "population_match_type": "EXACT_INDICATION" | "NARROWER_SUBGROUP" | "BROADER_POPULATION" | "DIFFERENT_POPULATION" | "UNKNOWN",
    "population_description_claim": "...",
    "population_description_study": "...",
    "subgroup_description": "...",
    "eligibility_shift": "NONE" | "MINOR" | "MAJOR",
    "justification": "...",
    "source_quote": "..."
  }},
  "context_alignment": {{
    "context_match_type": "SAME_HEALTHCARE_SYSTEM" | "PARTIALLY_COMPARABLE" | "DIFFERENT_SYSTEM" | "UNKNOWN",
    "care_pathway_match": "YES" | "PARTIAL" | "NO" | "UNKNOWN",
    "organization_dependency": "LOW" | "MEDIUM" | "HIGH",
    "study_country": "...",
    "target_country": "France",
    "justification": "...",
    "source_quote": "..."
  }}
}}"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _call_llm_for_cas_raw(claim_text: str, study_text: str, lang: str = "fr") -> dict:
    """Single raw LLM call — temperature=0, no consensus, no citation verification.
    Factored out of parse_cas_with_llm so parse_cas_with_llm_consensus can fire
    several of these in parallel and vote on the results (see below)."""
    client = _get_client()

    lang_label = "French" if lang == "fr" else "English"
    lang_instruction = (
        f"\n\nIMPORTANT: Return all description and justification fields in {lang_label}. "
        f"Enum values must stay in English."
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        temperature=0,
        system=SYSTEM_PROMPT + lang_instruction,
        messages=[
            {"role": "user", "content": USER_TEMPLATE.format(
                claim_text=claim_text, study_text=study_text,
            )},
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        from llm_evidence_parser import _repair_truncated_json
        return _repair_truncated_json(raw)


def parse_cas_with_llm(claim_text: str, study_text: str, lang: str = "fr") -> dict:
    """Single-call parse (temperature=0, no consensus, no citation verification).
    Kept for backward compatibility and for callers that explicitly want a fast
    single pass. Prefer parse_cas_with_llm_consensus for anything feeding
    regulatory output — a single call has no self-consistency check and no
    anti-fabrication guard on the alignment verdicts."""
    return _call_llm_for_cas_raw(claim_text, study_text, lang=lang)


def _verify_cas_citations(data: dict, study_text: str) -> list[str]:
    """Niveau 2 — deterministic, verbatim citation check (the same anti-fabrication
    check llm_evidence_parser.py's _apply_citation_verification already applies to
    StudyObject fields, extended here to the 3 CAS alignment dimensions).

    For each dimension, if source_quote isn't a verbatim substring of study_text,
    the match_type is reset to UNKNOWN and the dimension is recorded as rejected —
    an unverifiable citation is treated as no evidence, not weak evidence.

    Returns the list of rejected "{dimension}.{match_type_field}" field paths.
    """
    from llm_evidence_parser import _citation_verified

    rejected: list[str] = []
    dims = [
        ("device_alignment", "device_match_type"),
        ("population_alignment", "population_match_type"),
        ("context_alignment", "context_match_type"),
    ]
    for dim_key, match_key in dims:
        dim = data.get(dim_key) or {}
        if not isinstance(dim, dict):
            continue
        match_value = dim.get(match_key, "UNKNOWN")
        if match_value == "UNKNOWN":
            continue
        if not _citation_verified(dim.get("source_quote"), study_text):
            rejected.append(f"{dim_key}.{match_key}")
            dim[match_key] = "UNKNOWN"
    return rejected


def parse_cas_with_llm_consensus(
    claim_text: str, study_text: str, lang: str = "fr", n_calls: int = 3,
) -> tuple[dict, list[str], list[str]]:
    """Niveau 3 — self-consistency loop for claim/study alignment extraction.

    Runs n_calls parallel raw parses of the SAME (claim_text, study_text) pair
    and merges them via the same per-field majority vote that
    parse_study_object_with_llm_consensus already uses for StudyObject parsing
    (llm_evidence_parser._majority_vote — reused, not reimplemented, so the two
    consensus mechanisms in the codebase can't silently drift apart). Citation
    verification (Niveau 2) then runs on the CONSENSUS result, not on each raw
    call individually — a citation only counts if the value it supports survived
    the vote.

    This closes the one gap identified in the 3-tier architecture review: claim
    parsing previously had neither Niveau 2 (citation check) nor Niveau 3
    (consensus), unlike study-object parsing which already had both.

    Returns (consensus_dict, unstable_fields, citation_rejected_fields).
    """
    from llm_evidence_parser import _majority_vote

    _get_client()  # initialize before spawning threads, avoid a lazy-init race
    with ThreadPoolExecutor(max_workers=n_calls) as pool:
        futures = [
            pool.submit(_call_llm_for_cas_raw, claim_text, study_text, lang)
            for _ in range(n_calls)
        ]
        raw_results = [f.result() for f in futures]

    unstable_fields: list[str] = []
    consensus_data = _majority_vote(raw_results, "", unstable_fields)
    citation_rejected_fields = _verify_cas_citations(consensus_data, study_text)
    return consensus_data, unstable_fields, citation_rejected_fields


def parse_cas_smart(claim_text: str, study_text: str, lang: str = "fr") -> dict | None:
    """Production entry point (used by api.py's /api/smart-cas). Runs the
    consensus + citation-verification pipeline rather than a single raw call.

    unstable_fields / citation_rejected_fields are stashed under the
    "_consensus_meta" key so existing callers that read known top-level keys
    (parsed.get("device_alignment"), etc.) are unaffected — only callers that
    know to look for "_consensus_meta" see the new audit trail.
    """
    try:
        consensus, unstable_fields, citation_rejected_fields = parse_cas_with_llm_consensus(
            claim_text, study_text, lang=lang,
        )
        consensus["_consensus_meta"] = {
            "unstable_fields": unstable_fields,
            "citation_rejected_fields": citation_rejected_fields,
            "n_calls": 3,
        }
        return consensus
    except Exception:
        return None
