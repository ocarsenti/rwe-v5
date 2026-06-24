"""LLM-based claim parser — extracts structured clinical claim data from free text.

Uses Claude as primary parser, falls back to regex-based parser if unavailable.
"""

from __future__ import annotations

import json
import os

import anthropic

from models import (
    CausalRole,
    ClaimLevel,
    ClinicalClaim,
    Endpoint,
    EndpointNature,
)
from claim_parser import classify_claim as regex_classify_claim

_client = None

SYSTEM_PROMPT = """Tu es un expert en évaluation réglementaire des dispositifs médicaux numériques (CNEDiMTS/HAS).

À partir d'une revendication clinique en texte libre, tu dois extraire les informations structurées suivantes.

## Niveau de revendication (claim_level)
- "MECHANISM" (A) : la revendication porte sur un mécanisme biologique/physique (ex: stimulation nerveuse, libération d'endorphines)
- "PROCESS" (B) : la revendication porte sur un processus de soin (ex: monitoring, triage, détection précoce, alerte)
- "OUTCOME" (C) : la revendication porte sur un résultat clinique (ex: survie, douleur, qualité de vie, complications)
- "COMPLETE_CHAIN" (D) : la revendication couvre plusieurs niveaux (mécanisme + processus, processus + outcome, ou chaîne complète)

## Endpoints
Pour chaque critère d'évaluation (endpoint) mentionné ou implicite dans la revendication :
- name : nom court de l'endpoint
- nature : OBJECTIVE (mesure indépendante de l'observateur : mortalité, hospitalisations, biomarqueurs), SUBJECTIVE (dépend du patient/observateur : douleur VAS, qualité de vie, satisfaction), INSTRUMENTED (mesuré par le dispositif lui-même : temps de détection, alertes générées)
- causal_role : INDEPENDENT (l'endpoint ne dépend pas du mécanisme d'action du dispositif), MEDIATED (l'endpoint est atteint via un médiateur — le dispositif n'agit pas directement dessus), CIRCULAR (l'endpoint dépend directement du fonctionnement du dispositif — le dispositif est à la fois l'intervention et l'instrument de mesure)
- is_primary : true si c'est le critère principal, false sinon
- description : description courte

## Domaine
Le domaine médical (ex: ophthalmology, oncology, pain management, emergency neurology, cardiology)

## Intervention
Le nom/description du dispositif médical évalué.

IMPORTANT : Sois particulièrement attentif à la CIRCULARITÉ. Si le dispositif mesure/détecte quelque chose et que l'endpoint EST ce que le dispositif mesure/détecte, alors le causal_role est CIRCULAR. C'est le piège principal des DMN.

Réponds UNIQUEMENT en JSON valide, sans commentaire."""

USER_TEMPLATE = """Analyse cette revendication clinique et extrais les données structurées :

"{claim_text}"

Réponds en JSON avec ce format exact :
{{
  "claim_level": "MECHANISM" | "PROCESS" | "OUTCOME" | "COMPLETE_CHAIN",
  "intervention": "...",
  "domain": "...",
  "endpoints": [
    {{
      "name": "...",
      "nature": "OBJECTIVE" | "SUBJECTIVE" | "INSTRUMENTED",
      "causal_role": "INDEPENDENT" | "MEDIATED" | "CIRCULAR",
      "is_primary": true | false,
      "description": "..."
    }}
  ]
}}"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def parse_claim_with_llm(claim_text: str, lang: str = "fr") -> ClinicalClaim:
    """Parse a free-text clinical claim using Claude and return a structured ClinicalClaim."""
    client = _get_client()

    lang_label = "French" if lang == "fr" else "English"
    lang_instruction = (
        f"\n\nIMPORTANT: The input may be in any language. "
        f"Always return the 'intervention', 'domain', endpoint 'name' and 'description' fields in {lang_label}, "
        f"regardless of the input language. Translate if needed. "
        f"The JSON field names and enum values (MECHANISM, OBJECTIVE, CIRCULAR, etc.) must stay in English."
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT + lang_instruction,
        messages=[
            {"role": "user", "content": USER_TEMPLATE.format(claim_text=claim_text)},
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(raw)

    level_map = {
        "MECHANISM": ClaimLevel.A,
        "PROCESS": ClaimLevel.B,
        "OUTCOME": ClaimLevel.C,
        "COMPLETE_CHAIN": ClaimLevel.D,
    }

    endpoints = []
    for ep_data in data.get("endpoints", []):
        endpoints.append(Endpoint(
            name=ep_data["name"],
            nature=EndpointNature(ep_data["nature"]),
            causal_role=CausalRole(ep_data["causal_role"]),
            is_primary=ep_data.get("is_primary", False),
            description=ep_data.get("description", ""),
        ))

    claim = ClinicalClaim(
        text=claim_text,
        intervention=data.get("intervention", ""),
        level=level_map.get(data.get("claim_level"), ClaimLevel.B),
        endpoints=endpoints,
        domain=data.get("domain", ""),
    )

    return claim


def parse_claim_smart(claim_text: str, lang: str = "fr") -> ClinicalClaim:
    """Parse with LLM, fall back to regex if LLM fails."""
    try:
        return parse_claim_with_llm(claim_text, lang=lang)
    except Exception:
        claim = ClinicalClaim(text=claim_text, intervention="")
        claim.level = regex_classify_claim(claim)
        return claim
