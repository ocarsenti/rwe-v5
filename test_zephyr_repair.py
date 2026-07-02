"""Test Mode 2 complet ZEPHYR / LIBERATE — sans appel LLM.

Profil : EXACT_DEVICE, RCT open-label vs SOC, critère primaire VEMS (surrogate
non validé HAS pour BLVR/BPCO), signal sécurité pneumothorax 26.6%.
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données ZEPHYR / étude LIBERATE
# ---------------------------------------------------------------------------

ZEPHYR_JSON = {
    "acronym": "LIBERATE",
    "title": "LIBERATE — RCT multicentrique ZEPHYR valve vs soins standards, emphysème hétérogène",
    "publication_year": 2018,
    "registration_id": "NCT01796392",
    "funding_type": "industry",
    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "open_label",
    "who_is_blinded": None,
    "allocation_concealment": True,
    "protocol_registered_before_enrollment": True,
    "has_comparator": True,
    "comparator_type": "STANDARD_OF_CARE",
    "comparator_description": "Soins standards (réhabilitation respiratoire, bronchodilatateurs)",
    "n_patients": 190,
    "age_min": 40,
    "age_max": 75,
    "key_inclusion_criteria": [
        "BPCO sévère (VEMS 15–45% prédit)",
        "Emphysème hétérogène dominant au lobe supérieur",
        "Absence de collatéralité interlobaire (Chartis)",
        "Réhabilitation respiratoire complétée",
    ],
    "key_exclusion_criteria": [
        "VEMS < 15% prédit",
        "PaO2 < 45 mmHg",
        "Tabagisme actif",
    ],
    "device_studied": "ZEPHYR valve endobronchique",
    "care_setting": "hospital",
    "operator_training_required": True,
    "follow_up_months": 12.0,
    "longest_follow_up_months": 12.0,
    "dropout_rate_pct": 14.0,
    "primary_analysis_set": "ITT",
    "sample_size_calculation_provided": True,
    "primary_endpoint_met": True,
    "study_countries": ["USA", "Europe"],
    "key_safety_signals": [
        "Pneumothorax : 26.6% dans le groupe ZEPHYR vs 1.0% contrôle",
        "Hémoptysie sévère : 1.5% groupe ZEPHYR",
        "Hospitalisation pour cause respiratoire : 18.0% groupe ZEPHYR",
    ],
    "endpoints": [
        {
            "name": "VEMS (FEV1 % prédit) — variation à 12 mois",
            "is_primary": True,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Score SGRQ (qualité de vie respiratoire)",
            "is_primary": False,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Test de marche 6 minutes (TM6)",
            "is_primary": False,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
    ],
    "device_alignment": {
        "device_match_type": "EXACT_DEVICE",
        "device_description_study": "ZEPHYR valve endobronchique (Pulmonx)",
        "device_description_claim": "ZEPHYR valve endobronchique",
        "justification": "Dispositif identique à la revendication.",
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "BPCO sévère emphysème hétérogène, VEMS 15–45%",
        "population_description_claim": "BPCO sévère avec emphysème hétérogène",
        "eligibility_shift": "NONE",
        "justification": "Population alignée avec l'indication revendiquée.",
    },
    "context_alignment": {
        "context_match_type": "PARTIALLY_COMPARABLE",
        "study_country": "USA/Europe",
        "target_country": "France",
        "care_pathway_match": "PARTIAL",
        "organization_dependency": "HIGH",
        "justification": (
            "Étude multicentrique USA/Europe. La BLVR est pratiquée en France "
            "mais nécessite une expertise centralisée (centres experts). "
            "Contexte partiellement comparable."
        ),
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "ZEPHYR améliore la fonction pulmonaire (VEMS) et la qualité de vie "
        "chez les patients atteints de BPCO sévère avec emphysème hétérogène "
        "non éligibles à la chirurgie de réduction de volume pulmonaire"
    ),
    intervention="ZEPHYR valve endobronchique",
    domain="pulmonology",
    endpoints=[
        Endpoint(
            "VEMS (FEV1 % prédit) — variation à 12 mois",
            EndpointNature.OBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=True,
            is_validated_surrogate=False,
            description="spirométrie standardisée — surrogate fonctionnel non validé pour BLVR",
        ),
        Endpoint(
            "Score SGRQ (qualité de vie respiratoire)",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="questionnaire patient-rapporté, design ouvert",
        ),
        Endpoint(
            "Test de marche 6 minutes",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="mesure fonctionnelle standardisée",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

print("=" * 70)
print("  MODE 2 — ZEPHYR / LIBERATE — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(ZEPHYR_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  is_randomized   : {study.is_randomized}")
print(f"  has_comparator  : {study.has_comparator}  ({study.comparator_type.value})")
print(f"  n_patients      : {study.n_patients}")
print(f"  follow_up       : {study.follow_up_months} mois")
print(f"  countries       : {study.study_countries}")
print(f"  safety signals  : {len(study.key_safety_signals)}")
for s in study.key_safety_signals:
    print(f"    ⚠  {s}")
print(f"  endpoints       :")
for e in study.endpoints:
    tag = "PRIMARY" if e.is_primary else "SECONDARY"
    print(f"    [{tag}] {e.name} — validated_surrogate={e.is_validated_surrogate}")

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
