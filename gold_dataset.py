"""Gold dataset — CNEDiMTS gold standard reasoning dataset.

Defines the 4 mandatory cases and generates the full gold dataset table.
Each case is processed independently with consistent:
  - severity scoring
  - bias taxonomy
  - regulatory interpretation logic
"""

from __future__ import annotations

import json

from models import (
    CausalRole,
    ClinicalClaim,
    Endpoint,
    EndpointNature,
    GoldCaseOutput,
    GoldDatasetRow,
)
from engine import analyze
from regulatory_labeler import label_case, build_gold_dataset_rows


# ===================================================================
# 4 MANDATORY CASES
# ===================================================================

def _case_odysight() -> tuple[str, ClinicalClaim]:
    return "CASE_ODYSIGHT", ClinicalClaim(
        text="OdySight permet une détection plus précoce de la dégradation "
             "de l'acuité visuelle grâce au monitoring à distance, réduisant "
             "le délai de détection de la progression de la dégénérescence maculaire.",
        intervention="OdySight, dispositif de monitoring visuel à distance",
        endpoints=[
            Endpoint(
                name="délai de détection de la progression",
                nature=EndpointNature.INSTRUMENTED,
                causal_role=CausalRole.CIRCULAR,
                is_primary=True,
                description="Temps entre l'inclusion et la détection par le dispositif d'un changement d'acuité visuelle",
            ),
        ],
        domain="ophtalmologie",
    )


def _case_moovcare() -> tuple[str, ClinicalClaim]:
    return "CASE_MOOVCARE", ClinicalClaim(
        text="Moovcare améliore la survie globale des patients atteints de "
             "cancer du poumon grâce au suivi des symptômes par application web "
             "et à l'alerte précoce des médecins.",
        intervention="Moovcare, application web de suivi des symptômes",
        endpoints=[
            Endpoint(
                name="survie globale",
                nature=EndpointNature.OBJECTIVE,
                causal_role=CausalRole.MEDIATED,
                is_primary=True,
                description="Temps entre la randomisation et le décès, toutes causes confondues",
            ),
            Endpoint(
                name="délai de modification du traitement",
                nature=EndpointNature.OBJECTIVE,
                causal_role=CausalRole.MEDIATED,
                is_primary=False,
                description="Temps entre l'alerte symptomatique et le changement de traitement",
            ),
        ],
        domain="oncologie",
    )


def _case_remedee() -> tuple[str, ClinicalClaim]:
    return "CASE_REMEDEE", ClinicalClaim(
        text="FIBROREM soulage les symptômes de patients adultes atteints de "
             "fibromyalgie modérée à sévère (score FIQ ≥ 39) par rapport à la "
             "prise en charge thérapeutique classique individualisée et "
             "pluridisciplinaire.",
        intervention="FIBROREM, bracelet de neuromodulation par émission d'ondes millimétriques associé à l'application mobile myRemedee (Remedee Labs)",
        endpoints=[
            Endpoint(
                name="score FIQ (Fibromyalgia Impact Questionnaire) à 3 mois",
                nature=EndpointNature.SUBJECTIVE,
                causal_role=CausalRole.INDEPENDENT,
                is_primary=True,
                description="Réduction cliniquement pertinente du score FIQ ≥ 14% entre J0 et 3 mois — auto-questionnaire complété par le patient avant consultation médicale",
            ),
            Endpoint(
                name="score EVA douleur hebdomadaire",
                nature=EndpointNature.SUBJECTIVE,
                causal_role=CausalRole.INDEPENDENT,
                is_primary=False,
                description="Score EVA moyen sur 7 jours consécutifs à 1, 2 et 3 mois",
            ),
            Endpoint(
                name="qualité du sommeil (Pittsburgh Sleep Quality Index)",
                nature=EndpointNature.SUBJECTIVE,
                causal_role=CausalRole.INDEPENDENT,
                is_primary=False,
                description="Score PSQI à J0 et 3 mois",
            ),
            Endpoint(
                name="anxiété et dépression (HAD)",
                nature=EndpointNature.SUBJECTIVE,
                causal_role=CausalRole.INDEPENDENT,
                is_primary=False,
                description="Score HAD à J0 et 3 mois",
            ),
        ],
        domain="fibromyalgie / douleur chronique",
    )


def _case_ai_triage() -> tuple[str, ClinicalClaim]:
    return "CASE_AI_TRIAGE_AVC", ClinicalClaim(
        text="Le système de triage par IA réduit le délai de prise en charge "
             "des patients victimes d'AVC grâce à la détection automatisée et "
             "la priorisation des scanners cérébraux.",
        intervention="Système de triage et priorisation des scanners cérébraux par IA",
        endpoints=[
            Endpoint(
                name="délai de prise en charge",
                nature=EndpointNature.INSTRUMENTED,
                causal_role=CausalRole.CIRCULAR,
                is_primary=True,
                description="Temps entre l'acquisition du scanner et l'initiation du traitement, "
                            "déclenché par l'alerte IA",
            ),
        ],
        domain="neurologie d'urgence",
    )


ALL_CASES = [_case_odysight, _case_moovcare, _case_remedee, _case_ai_triage]


# ===================================================================
# PROCESSING
# ===================================================================

def process_case(case_id: str, claim: ClinicalClaim) -> GoldCaseOutput:
    engine_output = analyze(claim)
    return label_case(case_id, claim, engine_output)


def process_all_cases() -> list[GoldCaseOutput]:
    results = []
    for case_fn in ALL_CASES:
        case_id, claim = case_fn()
        results.append(process_case(case_id, claim))
    return results


def generate_gold_dataset() -> list[GoldDatasetRow]:
    cases = process_all_cases()
    return build_gold_dataset_rows(cases)


def generate_gold_dataset_json() -> str:
    cases = process_all_cases()
    rows = build_gold_dataset_rows(cases)

    output = {
        "cases": [c.to_dict() for c in cases],
        "gold_dataset_table": [r.to_dict() for r in rows],
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def generate_cases_json() -> str:
    cases = process_all_cases()
    return json.dumps([c.to_dict() for c in cases], indent=2, ensure_ascii=False)
