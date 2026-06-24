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
        text="OdySight enables earlier detection of visual acuity degradation "
             "through remote monitoring, reducing time-to-detection of macular "
             "degeneration progression.",
        intervention="OdySight remote visual acuity monitoring device",
        endpoints=[
            Endpoint(
                name="time-to-detection of progression",
                nature=EndpointNature.INSTRUMENTED,
                causal_role=CausalRole.CIRCULAR,
                is_primary=True,
                description="Time from baseline to device-detected visual acuity change",
            ),
        ],
        domain="ophthalmology",
    )


def _case_moovcare() -> tuple[str, ClinicalClaim]:
    return "CASE_MOOVCARE", ClinicalClaim(
        text="Moovcare improves overall survival in lung cancer patients "
             "through web-based symptom monitoring and early alert to physicians.",
        intervention="Moovcare web-based symptom monitoring application",
        endpoints=[
            Endpoint(
                name="overall survival",
                nature=EndpointNature.OBJECTIVE,
                causal_role=CausalRole.MEDIATED,
                is_primary=True,
                description="Time from randomization to death from any cause",
            ),
            Endpoint(
                name="time-to-treatment modification",
                nature=EndpointNature.OBJECTIVE,
                causal_role=CausalRole.MEDIATED,
                is_primary=False,
                description="Time from symptom alert to treatment change",
            ),
        ],
        domain="oncology",
    )


def _case_remedee() -> tuple[str, ClinicalClaim]:
    return "CASE_REMEDEE", ClinicalClaim(
        text="Remedee wristband uses millimeter-wave neurostimulation to trigger "
             "endorphin release, reducing chronic pain.",
        intervention="Remedee millimeter-wave neurostimulation wristband",
        endpoints=[
            Endpoint(
                name="pain VAS score",
                nature=EndpointNature.SUBJECTIVE,
                causal_role=CausalRole.INDEPENDENT,
                is_primary=True,
                description="Visual analog scale for pain intensity",
            ),
            Endpoint(
                name="patient quality of life",
                nature=EndpointNature.SUBJECTIVE,
                causal_role=CausalRole.INDEPENDENT,
                is_primary=False,
                description="SF-36 quality of life questionnaire",
            ),
        ],
        domain="pain management",
    )


def _case_ai_triage() -> tuple[str, ClinicalClaim]:
    return "CASE_AI_TRIAGE_AVC", ClinicalClaim(
        text="AI triage system reduces time-to-treatment for stroke patients "
             "by automated detection and prioritization of brain CT scans.",
        intervention="AI-powered CT scan triage and prioritization system",
        endpoints=[
            Endpoint(
                name="time-to-treatment",
                nature=EndpointNature.INSTRUMENTED,
                causal_role=CausalRole.CIRCULAR,
                is_primary=True,
                description="Time from scan acquisition to treatment initiation, "
                            "triggered by AI alert",
            ),
        ],
        domain="emergency neurology",
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
