"""Test Mode 2 complet ODYSIGHT — sans appel LLM.

Construit le StudyObject directement depuis les données connues de TIL-003,
puis exécute: enrich → analyze → compare → repair_comparison (bouton repair).
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données ODYSIGHT / TIL-003 (issues de la session précédente)
# ---------------------------------------------------------------------------

ODYSIGHT_JSON = {
    "acronym": "TIL-003",
    "title": "Étude rétrospective ODYSIGHT — impact dans la prise en charge des maculopathies",
    "publication_year": 2023,
    "registration_id": None,
    "funding_type": "industry",
    "study_design": "EXPLORATORY",
    "is_randomized": False,
    "blinding_level": "open_label",
    "who_is_blinded": None,
    "allocation_concealment": False,
    "protocol_registered_before_enrollment": False,
    "has_comparator": False,
    "comparator_type": "none",
    "comparator_description": "Aucun groupe contrôle",
    "n_patients": None,
    "age_min": None,
    "age_max": None,
    "key_inclusion_criteria": [
        "Patients atteints de maculopathies chroniques (DMLA exsudative, OMD)",
    ],
    "key_exclusion_criteria": [],
    "device_studied": "ODYSIGHT application de monitoring visuel",
    "care_setting": "outpatient",
    "operator_training_required": False,
    "follow_up_months": None,
    "longest_follow_up_months": None,
    "dropout_rate_pct": None,
    "primary_analysis_set": "unknown",
    "sample_size_calculation_provided": False,
    "primary_endpoint_met": None,
    "study_countries": ["France"],
    "key_safety_signals": [],
    "endpoints": [
        {
            "name": "délai de détection rechute DMLA par l'application",
            "is_primary": True,
            "time_point": None,
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        }
    ],
    "device_alignment": {
        "device_match_type": "EXACT_DEVICE",
        "device_description_study": "ODYSIGHT application de monitoring visuel",
        "device_description_claim": "ODYSIGHT application de monitoring visuel",
        "justification": "Même dispositif que la revendication.",
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "DMLA exsudative, OMD",
        "population_description_claim": "DMLA exsudative",
        "eligibility_shift": "NONE",
        "justification": "Population alignée.",
    },
    "context_alignment": {
        "context_match_type": "SAME_HEALTHCARE_SYSTEM",
        "study_country": "France",
        "target_country": "France",
        "care_pathway_match": "YES",
        "organization_dependency": "LOW",
        "justification": "Étude française.",
    },
}

claim = ClinicalClaim(
    text="ODYSIGHT détecte précocement les rechutes de DMLA et réduit le délai de traitement chez les patients sous anti-VEGF",
    intervention="ODYSIGHT application de monitoring visuel",
    domain="ophthalmology",
    endpoints=[
        Endpoint(
            "délai de détection rechute DMLA par l'application",
            EndpointNature.INSTRUMENTED,
            CausalRole.CIRCULAR,
            is_primary=True,
            description="time-to-detection by device algorithm — alert-triggered",
        ),
        Endpoint(
            "acuité visuelle finale",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="final visual acuity — not measured in TIL-003",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline complet
# ---------------------------------------------------------------------------

print("=" * 70)
print("  MODE 2 — ODYSIGHT / TIL-003 — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject depuis données connues...")
study = _parse_study_object_result(ODYSIGHT_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  is_randomized   : {study.is_randomized}")
print(f"  has_comparator  : {study.has_comparator}")
print(f"  countries       : {study.study_countries}")
print(f"  endpoints       : {[e.name for e in study.endpoints]}")

print("\n" + "─" * 70)
print("[2] Enrichissement claim + analyse épistémique...")
enrich_claim_with_study_object(claim, study)
output = analyze(claim)

print(f"  Causal structure  : {output.causal_structure.value}")
print(f"  Design recommandé : {output.design_recommendation.primary_design.value}")
if output.bias_flags:
    print("  BiasFlags :")
    for bd in output.bias_flags:
        print(f"    [{bd.severity}] {bd.flag.value} — {bd.detail[:70]}")

if output.cas_output:
    cas = output.cas_output
    print(f"  CAS : {cas.cas_score:.2f} → {cas.verdict.value}")

print("\n" + "─" * 70)
print("[3] ComparisonReport — Claim ↔ Study...")
report = compare_claim_to_study(claim, study, epistemic_output=output)

print(f"  Overall risk : {report.overall_risk.value}")
if report.gaps:
    print(f"  Gaps ({len(report.gaps)}) :")
    for g in report.gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:85]}")

print("\n" + "=" * 70)
print("[4]  BOUTON REPAIR  — actions de réparation concrètes")
print("=" * 70)

repair_plan = repair_comparison(report, claim, epistemic_output=output)

print(f"\n  Fully repairable : {repair_plan.is_fully_repairable}")
print(f"  Résumé : {repair_plan.repair_summary}")

_effort_label = {
    GapRepairEffort.LOW:      "✅ IMMÉDIAT     ",
    GapRepairEffort.MEDIUM:   "🔧 AMENDEMENT  ",
    GapRepairEffort.HIGH:     "🏗  NOUVELLE ÉTUDE",
    GapRepairEffort.BLOCKING: "🚫 BLOQUANT    ",
}

if repair_plan.non_repairable_gaps:
    print(f"\n  Gaps non réparables sans nouvelle étude :")
    for g in repair_plan.non_repairable_gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:80]}")

if repair_plan.actions:
    print(f"\n  Actions ({len(repair_plan.actions)}) — triées par effort croissant :\n")
    for i, a in enumerate(repair_plan.actions, 1):
        label = _effort_label.get(a.effort, a.effort.value)
        print(f"  ── Action {i} ──────────────────────────────────────────────────────")
        print(f"  {label}  [{a.gap_severity}] {a.gap_dimension.upper()}")
        print(f"  Type    : {a.repair_type.value}")
        print(f"  Action  : {a.description}")
        lines = [a.specific_suggestion[j:j+90] for j in range(0, len(a.specific_suggestion), 90)]
        print(f"  Détail  : {lines[0]}")
        for line in lines[1:]:
            print(f"            {line}")
        if a.removes_risk:
            print(f"  Élimine : {', '.join(a.removes_risk)}")
        print()
