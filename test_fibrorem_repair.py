"""Test Mode 2 complet FIBROREM / FIBREPIK — diagnostic + repair (sans LLM).

Profil : SAME_FAMILY (FIBREPIK = génération antérieure de FIBROREM),
RCT open-label vs SOC, critère primaire PRO/subjectif sans aveugle.
Attendu : is_fully_repairable=True, mix LOW/MEDIUM/HIGH, aucun BLOCKING.
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données FIBROREM / étude FIBREPIK
# ---------------------------------------------------------------------------

FIBREPIK_JSON = {
    "acronym": "FIBREPIK",
    "title": (
        "FIBREPIK — RCT comparant l'ablation endométriale par radiofréquence "
        "(génération précédente) vs traitement médical dans les ménorragies sur fibromes sous-muqueux"
    ),
    "publication_year": 2020,
    "registration_id": "NCT03541278",
    "funding_type": "industry",
    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "OPEN_LABEL",
    "who_is_blinded": None,
    "allocation_concealment": True,
    "protocol_registered_before_enrollment": True,
    "has_comparator": True,
    "comparator_type": "STANDARD_OF_CARE",
    "comparator_description": (
        "Traitement médical standard : progestérone micronisée ou acide tranexamique "
        "selon protocole institutionnel"
    ),
    "n_patients": 156,
    "age_min": 30,
    "age_max": 50,
    "key_inclusion_criteria": [
        "Ménorragies (score PBLAC > 100) liées à fibrome(s) sous-muqueux type 0/1 (FIGO)",
        "MMSE > 24",
        "Souhait de conservation utérine",
    ],
    "key_exclusion_criteria": [
        "Fibrome > 5 cm",
        "Grossesse ou désir de grossesse",
        "Traitement hormonal en cours",
    ],
    "device_studied": "FIBREPIK (système d'ablation endométriale par radiofréquence, v1)",
    "care_setting": "hospital",
    "operator_training_required": True,
    "follow_up_months": 12.0,
    "longest_follow_up_months": 12.0,
    "dropout_rate_pct": 9.0,
    "primary_analysis_set": "ITT",
    "sample_size_calculation_provided": True,
    "primary_endpoint_met": True,
    "study_countries": ["France", "Belgique"],
    "key_safety_signals": [
        "Perforation utérine per-procédure : 1.3% groupe FIBREPIK",
        "Infection post-procédure : 2.6% groupe FIBREPIK",
    ],
    "endpoints": [
        {
            "name": "Score de qualité de vie (questionnaire UFS-QoL) à 12 mois",
            "is_primary": True,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Taux de ré-intervention à 12 mois",
            "is_primary": False,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Score PBLAC (perte sanguine objectivée) à 3 et 6 mois",
            "is_primary": False,
            "time_point": "6 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
    ],
    "device_alignment": {
        "device_match_type": "SAME_FAMILY",
        "device_description_study": "FIBREPIK (ablation endométriale RF, v1)",
        "device_description_claim": "FIBROREM (ablation endométriale RF, v2)",
        "justification": (
            "FIBREPIK et FIBROREM appartiennent à la même famille technologique "
            "(ablation endométriale par radiofréquence) mais sont des générations distinctes : "
            "v2 (FIBROREM) intègre un contrôle de température amélioré et une électrode redessinée. "
            "Aucune étude de bridging technique disponible à ce jour."
        ),
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "Ménorragies sur fibrome sous-muqueux type 0/1, 30–50 ans",
        "population_description_claim": "Ménorragies liées aux fibromes sous-muqueux",
        "eligibility_shift": "NONE",
        "justification": "Population alignée avec l'indication revendiquée.",
    },
    "context_alignment": {
        "context_match_type": "SAME_HEALTHCARE_SYSTEM",
        "study_country": "France/Belgique",
        "target_country": "France",
        "care_pathway_match": "YES",
        "organization_dependency": "MEDIUM",
        "justification": (
            "Étude franco-belge — parcours de soins très comparable à la France. "
            "Procédure réalisée en centre hospitalier sous anesthésie locale ou générale."
        ),
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "FIBROREM réduit les saignements anormaux et améliore la qualité de vie "
        "chez les femmes présentant des ménorragies liées à des fibromes sous-muqueux "
        "éligibles à une ablation endométriale"
    ),
    intervention="FIBROREM système d'ablation endométriale par radiofréquence v2",
    domain="gynecology",
    endpoints=[
        Endpoint(
            "Score de qualité de vie (UFS-QoL) à 12 mois",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=True,
            description="questionnaire patient-rapporté, sans aveugle possible en design ouvert",
        ),
        Endpoint(
            "Taux de ré-intervention à 12 mois",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="événement clinique objectif — non adjudiqué formellement",
        ),
        Endpoint(
            "Score PBLAC (perte sanguine objectivée)",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="mesure semi-objective via carnet de suivi patient",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

_SEPARATOR = "─" * 70

print("=" * 70)
print("  MODE 2 — FIBROREM / FIBREPIK — diagnostic + repair (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(FIBREPIK_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  blinding        : {study.blinding_level.value}")
print(f"  comparateur     : {study.comparator_type.value} — {study.comparator_description[:55]}")
print(f"  n_patients      : {study.n_patients}")
print(f"  follow_up       : {study.follow_up_months} mois")
print(f"  countries       : {study.study_countries}")
if study.key_safety_signals:
    print("  Safety signals  :")
    for s in study.key_safety_signals:
        print(f"    ⚠  {s}")
print("  Endpoints :")
for e in study.endpoints:
    tag = "PRIMARY  " if e.is_primary else "SECONDARY"
    print(f"    [{tag}] {e.name}")

if study.device_alignment:
    d = study.device_alignment
    print(f"\n  Device alignment : {d.device_match_type.value}")
    print(f"    Étudié    : {d.device_description_study}")
    print(f"    Revendiqué: {d.device_description_claim}")
    print(f"    Justif.   : {d.justification[:75]}")

print(f"\n{_SEPARATOR}")
print("[2] Enrichissement claim + analyse épistémique (DIAGNOSTIC)...")
enrich_claim_with_study_object(claim, study)
output = analyze(claim)

print(f"  Claim level       : {output.claim_level.value}")
print(f"  Causal structure  : {output.causal_structure.value}")
print(f"  Design recommandé : {output.design_recommendation.primary_design.value}")
if output.design_recommendation.rationale:
    print(f"  Rationale         : {output.design_recommendation.rationale[:90]}")
if output.bias_flags:
    print("  BiasFlags :")
    for bd in output.bias_flags:
        print(f"    [{bd.severity}] {bd.flag.value}")
        print(f"           → {bd.detail[:85]}")
else:
    print("  BiasFlags : aucun")
if output.cas_output:
    cas = output.cas_output
    print(f"  CAS : {cas.cas_score:.2f} → {cas.verdict.value}")
    if cas.risks:
        for r in cas.risks[:3]:
            print(f"    · [{r.risk_level}] {r.description[:78]}")

print(f"\n{_SEPARATOR}")
print("[3] ComparisonReport — Claim ↔ Study...")
report = compare_claim_to_study(claim, study, epistemic_output=output)

print(f"  Overall risk : {report.overall_risk.value}")
print(f"  Gaps ({len(report.gaps)}) :")
for g in report.gaps:
    print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:90]}")
    if g.has_critique:
        print(f"           HAS : {str(g.has_critique)[:85]}")

print(f"\n{'=' * 70}")
print("[4]  BOUTON REPAIR  — actions concrètes")
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
    print("\n  Gaps non réparables :")
    for g in repair_plan.non_repairable_gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:80]}")

if repair_plan.actions:
    print(f"\n  Actions ({len(repair_plan.actions)}) — triées par effort :\n")
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
