"""Test Mode 2 complet BRAINXPERT / BENEFIC — sans appel LLM.

Profil : DIFFERENT_DEVICE (CAPTEX 355 ≠ BRAINXPERT), CAS REJECTED,
gap dispositif CRITICAL bloquant.
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données BRAINXPERT / étude BENEFIC
# ---------------------------------------------------------------------------

BENEFIC_JSON = {
    "acronym": "BENEFIC",
    "title": "BENEFIC — Étude de la stimulation cognitive par CAPTEX 355 chez les patients MCI",
    "publication_year": 2022,
    "registration_id": "NCT03812224",
    "funding_type": "industry",
    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "SINGLE_BLIND",
    "who_is_blinded": "évaluateur",
    "allocation_concealment": True,
    "protocol_registered_before_enrollment": True,
    "has_comparator": True,
    "comparator_type": "SHAM",
    "comparator_description": "Stimulation SHAM (électrodes inactives, procédure identique)",
    "n_patients": 96,
    "age_min": 55,
    "age_max": 80,
    "key_inclusion_criteria": [
        "Trouble cognitif léger (MCI) diagnostiqué selon critères Petersen",
        "Score MMSE entre 24 et 28",
        "Autonomie préservée pour les activités quotidiennes",
    ],
    "key_exclusion_criteria": [
        "Démence avérée (MMSE < 24)",
        "Antécédent d'épilepsie",
        "Traitement par anticholinestérasique en cours",
    ],
    "device_studied": "CAPTEX 355 (stimulateur cognitif transcutané)",
    "care_setting": "outpatient",
    "operator_training_required": True,
    "follow_up_months": 6.0,
    "longest_follow_up_months": 6.0,
    "dropout_rate_pct": 10.0,
    "primary_analysis_set": "ITT",
    "sample_size_calculation_provided": True,
    "primary_endpoint_met": True,
    "study_countries": ["France"],
    "key_safety_signals": [
        "Érythème cutané léger au site d'application : 8% groupe actif",
    ],
    "endpoints": [
        {
            "name": "Score MoCA (Montreal Cognitive Assessment) à 6 mois",
            "is_primary": True,
            "time_point": "6 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Score ADAS-Cog à 6 mois",
            "is_primary": False,
            "time_point": "6 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": False,
        },
    ],
    "device_alignment": {
        "device_match_type": "DIFFERENT_DEVICE",
        "device_description_study": "CAPTEX 355 (stimulateur cognitif transcutané)",
        "device_description_claim": "BRAINXPERT (casque de neurostimulation cognitive)",
        "justification": (
            "CAPTEX 355 et BRAINXPERT sont deux dispositifs distincts : "
            "fréquences de stimulation différentes (10 Hz vs 40 Hz), "
            "zones cibles différentes (frontal vs temporal), "
            "aucune étude de bridging disponible."
        ),
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "MCI, MMSE 24–28",
        "population_description_claim": "Trouble cognitif léger (MCI)",
        "eligibility_shift": "NONE",
        "justification": "Population alignée avec l'indication revendiquée.",
    },
    "context_alignment": {
        "context_match_type": "SAME_HEALTHCARE_SYSTEM",
        "study_country": "France",
        "target_country": "France",
        "care_pathway_match": "YES",
        "organization_dependency": "LOW",
        "justification": "Étude française — contexte identique.",
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "BRAINXPERT améliore les fonctions cognitives (mémoire, attention) "
        "et ralentit le déclin cognitif chez les patients atteints de trouble "
        "cognitif léger (MCI)"
    ),
    intervention="BRAINXPERT casque de neurostimulation cognitive",
    domain="neurology",
    endpoints=[
        Endpoint(
            "Score MoCA à 6 mois",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=True,
            description="évaluation cognitive standardisée par évaluateur — score PRO-adjacent",
        ),
        Endpoint(
            "Score ADAS-Cog à 6 mois",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="échelle cognitive standardisée",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

print("=" * 70)
print("  MODE 2 — BRAINXPERT / BENEFIC — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(BENEFIC_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  blinding        : {study.blinding_level.value}")
print(f"  has_comparator  : {study.has_comparator}  ({study.comparator_type.value})")
print(f"  n_patients      : {study.n_patients}")
print(f"  follow_up       : {study.follow_up_months} mois")
print(f"  countries       : {study.study_countries}")
if study.key_safety_signals:
    for s in study.key_safety_signals:
        print(f"    ⚠  {s}")
print(f"  endpoints       :")
for e in study.endpoints:
    tag = "PRIMARY" if e.is_primary else "SECONDARY"
    print(f"    [{tag}] {e.name}")

if study.device_alignment:
    d = study.device_alignment
    print(f"\n  Device alignment : {d.device_match_type.value}")
    print(f"    Étudié   : {d.device_description_study}")
    print(f"    Revendiqué: {d.device_description_claim}")
    print(f"    Justif.  : {d.justification[:80]}")

print("\n" + "─" * 70)
print("[2] Enrichissement claim + analyse épistémique...")
enrich_claim_with_study_object(claim, study)
output = analyze(claim)

print(f"  Claim level       : {output.claim_level.value}")
print(f"  Causal structure  : {output.causal_structure.value}")
print(f"  Design recommandé : {output.design_recommendation.primary_design.value}")
if output.bias_flags:
    print("  BiasFlags :")
    for bd in output.bias_flags:
        print(f"    [{bd.severity}] {bd.flag.value} — {bd.detail[:75]}")
else:
    print("  BiasFlags : aucun")

if output.cas_output:
    cas = output.cas_output
    print(f"  CAS : {cas.cas_score:.2f} → {cas.verdict.value}")
else:
    print("  CAS : non calculé (device différent)")

print("\n" + "─" * 70)
print("[3] ComparisonReport — Claim ↔ Study...")
report = compare_claim_to_study(claim, study, epistemic_output=output)

print(f"  Overall risk : {report.overall_risk.value}")
if report.gaps:
    print(f"  Gaps ({len(report.gaps)}) :")
    for g in report.gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:90]}")

print("\n" + "=" * 70)
print("[4]  BOUTON REPAIR  — actions de réparation concrètes")
print("=" * 70)

repair_plan = repair_comparison(report, claim, epistemic_output=output)

print(f"\n  Fully repairable : {repair_plan.is_fully_repairable}")
print(f"  Résumé : {repair_plan.repair_summary}")

_effort_label = {
    GapRepairEffort.LOW:      "✅ IMMÉDIAT      ",
    GapRepairEffort.MEDIUM:   "🔧 AMENDEMENT   ",
    GapRepairEffort.HIGH:     "🏗  NOUVELLE ÉTUDE",
    GapRepairEffort.BLOCKING: "🚫 BLOQUANT     ",
}

if repair_plan.non_repairable_gaps:
    print(f"\n  Gaps non réparables sans nouvelle étude :")
    for g in repair_plan.non_repairable_gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:85]}")

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
