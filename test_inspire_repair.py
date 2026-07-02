"""Test Mode 2 complet INSPIRE IV / EFFECT — diagnostic + repair (sans LLM).

Profil : SAME_FAMILY (INSPIRE II + IV mélangés), monogroupe sans comparateur,
critère principal IAH à 0.5 mois (PSG post-titration, surrogate non validé HAS).
Attendu : overall_risk=CRITICAL (≥2 HIGH), is_fully_repairable=True, mix MEDIUM/HIGH.
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données INSPIRE IV / étude EFFECT
# ---------------------------------------------------------------------------

EFFECT_JSON = {
    "acronym": "EFFECT",
    "title": (
        "EFFECT — Registre multicentrique de stimulation hypoglosse (INSPIRE II et IV) "
        "dans l'apnée obstructive du sommeil sévère réfractaire au PPC"
    ),
    "publication_year": 2023,
    "registration_id": "NCT04200053",
    "funding_type": "industry",
    "study_design": "SINGLE_ARM",
    "is_randomized": False,
    "blinding_level": "OPEN_LABEL",
    "who_is_blinded": None,
    "allocation_concealment": False,
    "protocol_registered_before_enrollment": True,
    "has_comparator": False,
    "comparator_type": None,
    "comparator_description": None,
    "n_patients": 198,
    "age_min": 22,
    "age_max": 75,
    "key_inclusion_criteria": [
        "SAHOS sévère (IAH ≥ 30 événements/heure) confirmé par PSG",
        "Intolérance ou refus du PPC documenté (≥ 3 mois de traitement insuffisant)",
        "IMC ≤ 32 kg/m²",
        "Absence de collapsus palatal concentrique complet (évaluation DISE)",
    ],
    "key_exclusion_criteria": [
        "SAHOS central (IAH central > 25% de l'IAH total)",
        "Déficit neuromusculaire affectant la déglutition",
        "BPCO sévère associée",
    ],
    "device_studied": "INSPIRE (II et IV — proportion IV : 68%, II : 32%)",
    "care_setting": "hospital",
    "operator_training_required": True,
    "follow_up_months": 0.5,
    "longest_follow_up_months": 12.0,
    "dropout_rate_pct": 8.0,
    "primary_analysis_set": "PP",
    "sample_size_calculation_provided": False,
    "primary_endpoint_met": True,
    "study_countries": ["France", "Allemagne", "Belgique"],
    "key_safety_signals": [
        "Inconfort lié à la stimulation (paresthésies langue) : 12% — réglage ajusté",
        "Infection du site d'implantation : 1.5%",
        "Révision chirurgicale du générateur : 2.0%",
    ],
    "endpoints": [
        {
            "name": "Indice d'apnées-hypopnées (IAH) à la PSG de titration (0.5 mois)",
            "is_primary": True,
            "time_point": "0.5 mois post-activation",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Indice de désaturation en oxygène (IDO) à 0.5 mois",
            "is_primary": False,
            "time_point": "0.5 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Score de somnolence Epworth (ESS) à 12 mois",
            "is_primary": False,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Score de qualité de vie (FOSQ-10) à 12 mois",
            "is_primary": False,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
    ],
    "device_alignment": {
        "device_match_type": "SAME_FAMILY",
        "device_description_study": "INSPIRE (II et IV — 68% IV, 32% II)",
        "device_description_claim": "INSPIRE IV système de stimulation hypoglosse",
        "justification": (
            "L'étude EFFECT inclut un mélange de patients traités avec INSPIRE II (génération "
            "antérieure) et INSPIRE IV (génération actuelle). Les résultats globaux ne permettent "
            "pas d'isoler l'effet propre d'INSPIRE IV. Pas d'analyse par sous-groupe génération "
            "préspécifiée. Différences techniques : INSPIRE IV intègre un capteur respiratoire "
            "amélioré (précision de détection +15%) et une batterie longue durée (10 ans vs 7 ans)."
        ),
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "SAHOS sévère (IAH ≥ 30), PPC-intolérant, IMC ≤ 32",
        "population_description_claim": "SAHOS sévère réfractaire au PPC",
        "eligibility_shift": "NONE",
        "justification": "Population alignée avec l'indication revendiquée.",
    },
    "context_alignment": {
        "context_match_type": "SAME_HEALTHCARE_SYSTEM",
        "study_country": "France/Allemagne/Belgique",
        "target_country": "France",
        "care_pathway_match": "YES",
        "organization_dependency": "HIGH",
        "justification": (
            "Étude franco-germano-belge. La stimulation hypoglosse est pratiquée en France "
            "dans des centres de référence avec expertise en somnologie interventionnelle. "
            "Dépendance organisationnelle élevée : pose + titration requiert équipe pluridisciplinaire "
            "(somnologue, ORL, chirurgien implanteur)."
        ),
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "INSPIRE IV réduit l'index apnée-hypopnée (IAH) et améliore la qualité de vie "
        "chez les patients adultes atteints de SAHOS sévère en échec ou intolérance au PPC"
    ),
    intervention="INSPIRE IV système de stimulation hypoglosse (neurostimulateur implantable)",
    domain="somnologie",
    endpoints=[
        Endpoint(
            "Indice d'apnées-hypopnées (IAH) à la PSG de titration",
            EndpointNature.OBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=True,
            is_validated_surrogate=False,
            description="Surrogate polysomnographique — non reconnu par HAS comme endpoint clinique dur en SAHOS",
        ),
        Endpoint(
            "Indice de désaturation en oxygène (IDO)",
            EndpointNature.OBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=False,
            is_validated_surrogate=False,
            description="Marqueur fonctionnel intermédiaire — même statut surrogate que l'IAH",
        ),
        Endpoint(
            "Score Epworth (ESS) à 12 mois",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="Questionnaire de somnolence diurne — patient-rapporté, sans aveugle",
        ),
        Endpoint(
            "Score FOSQ-10 (qualité de vie) à 12 mois",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="Questionnaire de qualité de vie spécifique SAHOS — patient-rapporté",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

_SEPARATOR = "─" * 70

print("=" * 70)
print("  MODE 2 — INSPIRE IV / EFFECT — diagnostic + repair (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(EFFECT_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  blinding        : {study.blinding_level.value}")
print(f"  has_comparator  : {study.has_comparator}")
print(f"  n_patients      : {study.n_patients}")
print(f"  follow_up       : {study.follow_up_months} mois (PSG titration)")
print(f"  follow_up_max   : {study.longest_follow_up_months} mois")
print(f"  countries       : {study.study_countries}")
if study.key_safety_signals:
    print("  Safety signals  :")
    for s in study.key_safety_signals:
        print(f"    ⚠  {s}")
print("  Endpoints :")
for e in study.endpoints:
    tag = "PRIMARY  " if e.is_primary else "SECONDARY"
    surr = " [surrogate]" if not e.is_validated_surrogate else " [validé]"
    print(f"    [{tag}] {e.name}{surr}")

if study.device_alignment:
    d = study.device_alignment
    print(f"\n  Device alignment : {d.device_match_type.value}")
    print(f"    Étudié    : {d.device_description_study}")
    print(f"    Revendiqué: {d.device_description_claim}")
    print(f"    Justif.   : {d.justification[:80]}")

print(f"\n{_SEPARATOR}")
print("[2] Enrichissement claim + analyse épistémique (DIAGNOSTIC)...")
enrich_claim_with_study_object(claim, study)
output = analyze(claim)

print(f"  Claim level       : {output.claim_level.value}")
print(f"  Causal structure  : {output.causal_structure.value}")
print(f"  Design recommandé : {output.design_recommendation.primary_design.value}")
if output.design_recommendation.rationale:
    print(f"  Rationale         : {output.design_recommendation.rationale[:85]}")
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
    for r in cas.risks[:3]:
        print(f"    · [{r.risk_level}] {r.description[:75]}")

print(f"\n{_SEPARATOR}")
print("[3] ComparisonReport — Claim ↔ Study...")
report = compare_claim_to_study(claim, study, epistemic_output=output)

print(f"  Overall risk : {report.overall_risk.value}")
print(f"  Gaps ({len(report.gaps)}) :")
for g in report.gaps:
    print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:88]}")
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
