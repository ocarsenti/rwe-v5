"""Test Mode 2 complet FIREHAWK LIBERTY / TARGET ALL COMERS — sans appel LLM.

Reconstruit fidèlement depuis l'avis CNEDiMTS du 23/04/2024 (renouvellement
d'inscription, SR Suffisant, ASR V). Cas atypique dans le corpus : contrairement
aux cas de refus déjà testés (FIBROREM, BRAINXPERT, SOMNIO...), FIREHAWK LIBERTY
est un renouvellement FAVORABLE, sans aucune nouvelle donnée spécifique au
dispositif — l'extrapolation depuis FIREHAWK (génération antérieure, même
revêtement/principe actif, seul le cathéter de largage change) avait déjà été
acceptée par la Commission en 2020.

Données utilisées : résultats à 5 ans de TARGET ALL COMERS (Lansky et al. 2023,
EuroIntervention), RCT multicentrique européenne FIREHAWK vs XIENCE, n=1653,
non-infériorité, TLF comparable entre bras (17.1% vs 16.3%), pas de signal de
sécurité (thrombose de stent 2.8% vs 3.0%).

Sert de cas de calibration "négatif" : peu/pas de bias_flags ou gaps attendus,
cohérent avec une décision HAS favorable.
"""

import sys
sys.path.insert(0, "/home/claude/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données FIREHAWK LIBERTY / étude TARGET ALL COMERS (résultats à 5 ans)
# ---------------------------------------------------------------------------

FIREHAWK_JSON = {
    "acronym": "TARGET ALL COMERS",
    "title": (
        "TARGET ALL COMERS — RCT multicentrique européenne, stent FIREHAWK "
        "(abluminal groove-filled biodegradable polymer sirolimus-eluting) "
        "vs XIENCE (durable polymer everolimus-eluting), résultats à 5 ans"
    ),
    "publication_year": 2023,
    "registration_id": None,
    "funding_type": "industry",
    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "open_label",
    "who_is_blinded": None,
    "allocation_concealment": True,
    "protocol_registered_before_enrollment": True,
    "has_comparator": True,
    "comparator_type": "ACTIVE",
    "comparator_description": "XIENCE (stent actif everolimus, polymère durable)",
    "n_patients": 1653,
    "age_min": None,
    "age_max": None,
    "key_inclusion_criteria": [
        "Patients 'vie réelle' éligibles à une angioplastie coronaire",
        "Toutes situations de la maladie coronaire (maladie stable, SCA)",
    ],
    "key_exclusion_criteria": [],
    "device_studied": "FIREHAWK (endoprothèse coronaire sirolimus, génération antérieure à FIREHAWK LIBERTY)",
    "care_setting": "hospital",
    "operator_training_required": True,
    "follow_up_months": 60.0,
    "longest_follow_up_months": 60.0,
    "dropout_rate_pct": 6.2,
    "primary_analysis_set": "ITT",
    "sample_size_calculation_provided": True,
    "primary_endpoint_met": True,
    "study_countries": ["Europe"],
    "key_safety_signals": [
        "Thrombose de stent définie/probable : 2.8% (FIREHAWK) vs 3.0% (XIENCE) à 5 ans — comparable",
    ],
    "endpoints": [
        {
            "name": "TLF — échec de revascularisation de la lésion cible (décès cardiaque + IDM lié au vaisseau cible + TLR-ID) à 1 an",
            "is_primary": True,
            "time_point": "1 an (données à 5 ans rapportées ici en suivi étendu)",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": True,
            "result_direction": "NON_INFERIOR",
            "reached_significance": True,
        },
        {
            "name": "TVR — revascularisation du vaisseau cible",
            "is_primary": False,
            "time_point": "5 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": True,
            "result_direction": "NON_INFERIOR",
            "reached_significance": True,
        },
        {
            "name": "Thrombose de stent définie/probable",
            "is_primary": False,
            "time_point": "5 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": True,
            "result_direction": "NON_INFERIOR",
            "reached_significance": True,
        },
    ],
    "device_alignment": {
        "device_match_type": "SAME_FAMILY",
        "device_description_study": "FIREHAWK (cathéter de largage 6F, revêtement/principe actif identique)",
        "device_description_claim": "FIREHAWK LIBERTY (cathéter de largage 5F, +8mm de longueur disponible)",
        "justification": (
            "Seul le système d'implantation (cathéter de largage) diffère entre "
            "FIREHAWK et FIREHAWK LIBERTY ; endoprothèse, polymère biodégradable "
            "et sirolimus identiques. Extrapolation déjà acceptée par la Commission "
            "en 2020 (avis du 01/09/2020) et reconduite au renouvellement de 2024."
        ),
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "Insuffisance coronaire, lésion(s) de novo, toutes situations (maladie stable, SCA), 'vie réelle'",
        "population_description_claim": "Insuffisance coronaire imputable à une ou des lésion(s) de novo d'une artère coronaire native ≥ 2,25 mm",
        "eligibility_shift": "NONE",
        "justification": "Population de l'étude 'all comers' alignée avec l'indication générale revendiquée.",
    },
    "context_alignment": {
        "context_match_type": "SAME_HEALTHCARE_SYSTEM",
        "study_country": "Europe",
        "target_country": "France",
        "care_pathway_match": "YES",
        "organization_dependency": "LOW",
        "justification": (
            "Étude multicentrique européenne, angioplastie coronaire = pratique "
            "standard en cardiologie interventionnelle française, pas d'expertise "
            "centralisée spécifique requise au-delà du cadre réglementaire habituel."
        ),
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "FIREHAWK LIBERTY est efficace et sûr dans le traitement de l'insuffisance "
        "coronaire imputable à une ou des lésion(s) de novo d'une artère coronaire "
        "native ≥ 2,25 mm de diamètre, dans toutes les situations de la maladie "
        "coronaire (maladie stable, SCA), avec une non-infériorité par rapport à "
        "XIENCE"
    ),
    intervention="FIREHAWK LIBERTY (endoprothèse coronaire sirolimus)",
    domain="cardiology",
    endpoints=[
        Endpoint(
            "TLF — échec de revascularisation de la lésion cible à 1 an",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=True,
            is_validated_surrogate=False,
            description="composite décès cardiaque + IDM lié au vaisseau cible + TLR-ID, adjudiqué",
        ),
        Endpoint(
            "TVR — revascularisation du vaisseau cible",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="critère clinique dur, adjudiqué",
        ),
        Endpoint(
            "Thrombose de stent définie/probable",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="critère de sécurité, adjudiqué (définition ARC)",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

print("=" * 70)
print("  MODE 2 — FIREHAWK LIBERTY / TARGET ALL COMERS — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(FIREHAWK_JSON, claim.intervention, claim.text)
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
else:
    print("  Gaps : aucun")

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
else:
    print("\n  Aucune action de réparation nécessaire.")
