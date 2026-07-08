"""LLM-based CAS parser — infers alignment dimensions from free-text descriptions.

The user provides two things:
  1. The CLAIM (what they want to demonstrate, for which device, for which population)
  2. The STUDY (what study they have, what device it tested, what population, where)

The LLM infers the 3 CAS dimensions: device match, population match, context match.
"""

from __future__ import annotations

import json

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
    "justification": "..."
  }},
  "population_alignment": {{
    "population_match_type": "EXACT_INDICATION" | "NARROWER_SUBGROUP" | "BROADER_POPULATION" | "DIFFERENT_POPULATION" | "UNKNOWN",
    "population_description_claim": "...",
    "population_description_study": "...",
    "subgroup_description": "...",
    "eligibility_shift": "NONE" | "MINOR" | "MAJOR",
    "justification": "..."
  }},
  "context_alignment": {{
    "context_match_type": "SAME_HEALTHCARE_SYSTEM" | "PARTIALLY_COMPARABLE" | "DIFFERENT_SYSTEM" | "UNKNOWN",
    "care_pathway_match": "YES" | "PARTIAL" | "NO" | "UNKNOWN",
    "organization_dependency": "LOW" | "MEDIUM" | "HIGH",
    "study_country": "...",
    "target_country": "France",
    "justification": "..."
  }}
}}"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def parse_cas_with_llm(claim_text: str, study_text: str, lang: str = "fr") -> dict:
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


def parse_cas_smart(claim_text: str, study_text: str, lang: str = "fr") -> dict | None:
    try:
        return parse_cas_with_llm(claim_text, study_text, lang=lang)
    except Exception:
        return None
