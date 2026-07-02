"""INSPIRE IV / EFFECT — repair loop : avant → repair → après.

Démonstration du cycle complet :
  1. Dossier initial   → diagnostic (gaps)
  2. Bouton repair     → actions concrètes
  3. Dossier corrigé   → re-diagnostic (gaps résiduels)
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

_SEP = "─" * 70
_effort_label = {
    GapRepairEffort.LOW:      "✅ IMMÉDIAT      ",
    GapRepairEffort.MEDIUM:   "🔧 AMENDEMENT   ",
    GapRepairEffort.HIGH:     "🏗  NOUVELLE ÉTUDE",
    GapRepairEffort.BLOCKING: "🚫 BLOQUANT     ",
}


def run_pipeline(label, study_json, claim):
    """Instancie StudyObject, enrichit la claim, diagnostique, et retourne (report, output)."""
    study = _parse_study_object_result(study_json, claim.intervention, claim.text)
    enrich_claim_with_study_object(claim, study)
    output = analyze(claim)
    report = compare_claim_to_study(claim, study, epistemic_output=output)
    return study, output, report


def print_diagnostic(label, report, output):
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"{'=' * 70}")
    print(f"  Overall risk : {report.overall_risk.value}   ({len(report.gaps)} gap(s))")
    if report.gaps:
        for g in report.gaps:
            print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:85]}")
    else:
        print("    ✅  Aucun gap identifié")
    if output.bias_flags:
        for bd in output.bias_flags:
            print(f"  BiasFlag [{bd.severity}] {bd.flag.value}")


# ============================================================
# DOSSIER INITIAL
# ============================================================

EFFECT_AVANT = {
    "acronym": "EFFECT",
    "study_design": "SINGLE_ARM",
    "is_randomized": False,
    "blinding_level": "OPEN_LABEL",
    "has_comparator": False,
    "comparator_type": None,
    "comparator_description": None,
    "n_patients": 198,
    "follow_up_months": 0.5,
    "longest_follow_up_months": 12.0,
    "study_countries": ["France", "Allemagne", "Belgique"],
    "key_safety_signals": ["Infection site implantation : 1.5%"],
    "endpoints": [
        {
            "name": "IAH à la PSG de titration (0.5 mois)",
            "is_primary": True,
            "time_point": "0.5 mois",
            "is_validated_surrogate": False,
            "is_feasibility_accepted_surrogate": True,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
        {
            "name": "Score Epworth (ESS) à 12 mois",
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
        "device_description_study": "INSPIRE II + IV (68% IV, 32% II)",
        "device_description_claim": "INSPIRE IV système de stimulation hypoglosse",
        "justification": (
            "Mélange INSPIRE II (32%) et IV (68%) — pas d'analyse séparée par génération. "
            "Différences techniques : capteur respiratoire amélioré, batterie 10 ans vs 7 ans."
        ),
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": "SAHOS sévère (IAH ≥ 30), PPC-intolérant, IMC ≤ 32",
        "population_description_claim": "SAHOS sévère réfractaire au PPC",
        "eligibility_shift": "NONE",
        "justification": "Population alignée.",
    },
    "context_alignment": {
        "context_match_type": "SAME_HEALTHCARE_SYSTEM",
        "study_country": "France/Allemagne/Belgique",
        "target_country": "France",
        "care_pathway_match": "YES",
        "organization_dependency": "HIGH",
        "justification": "Étude franco-germano-belge, contexte comparable.",
    },
}

CLAIM_AVANT = ClinicalClaim(
    text=(
        "INSPIRE IV réduit l'IAH et améliore la qualité de vie "
        "chez les patients adultes SAHOS sévère réfractaires au PPC"
    ),
    intervention="INSPIRE IV système de stimulation hypoglosse",
    domain="somnologie",
    endpoints=[
        Endpoint(
            "IAH à la PSG de titration (0.5 mois)",
            EndpointNature.OBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=True,
            is_validated_surrogate=False,
        ),
        Endpoint(
            "Score Epworth (ESS) à 12 mois",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
        ),
    ],
)

# ── étape 1 : diagnostic initial ──────────────────────────────────────────

study_avant, output_avant, report_avant = run_pipeline(
    "AVANT — dossier initial", EFFECT_AVANT, CLAIM_AVANT
)
print_diagnostic("AVANT — dossier initial (EFFECT tel que soumis)", report_avant, output_avant)

# ── étape 2 : repair ──────────────────────────────────────────────────────

print(f"\n{'=' * 70}")
print("  BOUTON REPAIR — actions recommandées")
print(f"{'=' * 70}")
repair_plan = repair_comparison(report_avant, CLAIM_AVANT, epistemic_output=output_avant)
print(f"\n  is_fully_repairable : {repair_plan.is_fully_repairable}")
print(f"  {repair_plan.repair_summary}\n")
for i, a in enumerate(repair_plan.actions, 1):
    label = _effort_label.get(a.effort, a.effort.value)
    print(f"  {i}. {label} [{a.gap_severity}] {a.gap_dimension.upper()}")
    print(f"     → {a.description}")


# ============================================================
# DOSSIER CORRIGÉ (repairs LOW + MEDIUM appliqués)
# ============================================================
#
# Repairs appliqués :
#   [LOW]    claim_restriction : restreindre la claim à INSPIRE IV pur
#            → device_alignment passe de SAME_FAMILY à EXACT_DEVICE
#   [LOW]    adjudication_addition : lecture PSG centralisée
#            → is_independently_adjudicated=True sur l'IAH
#   [MEDIUM] bridging_study : sous-groupe IV isolé (68% = 135 patients)
#            → device_alignment EXACT_DEVICE confirmé

EFFECT_APRES_MEDIUM = dict(EFFECT_AVANT)
EFFECT_APRES_MEDIUM["device_alignment"] = {
    "device_match_type": "EXACT_DEVICE",
    "device_description_study": "INSPIRE IV (sous-groupe 135/198 patients)",
    "device_description_claim": "INSPIRE IV système de stimulation hypoglosse",
    "justification": (
        "Analyse en sous-groupe préspécifiée sur les 135 patients INSPIRE IV (68%). "
        "Caractéristiques équilibrées vs sous-groupe II (données bridging technique fournies). "
        "Résultats IAH et ESS similaires entre générations — équivalence confirmée."
    ),
}
EFFECT_APRES_MEDIUM["endpoints"] = [
    {
        "name": "IAH à la PSG de titration (0.5 mois) — lecture centralisée",
        "is_primary": True,
        "time_point": "0.5 mois",
        "is_validated_surrogate": False,
        "is_feasibility_accepted_surrogate": True,   # ← conservé : IAH reste primaire + registre post-marché
        "is_independently_adjudicated": True,         # ← adjudication_addition appliquée
        "result_direction": "SUPERIOR",
        "reached_significance": True,
    },
    {
        "name": "Score Epworth (ESS) à 12 mois",
        "is_primary": False,
        "time_point": "12 mois",
        "is_validated_surrogate": False,
        "is_independently_adjudicated": False,
        "result_direction": "SUPERIOR",
        "reached_significance": True,
    },
]

CLAIM_APRES_MEDIUM = ClinicalClaim(
    text=(
        "INSPIRE IV (sous-groupe 135 patients) réduit l'IAH à la PSG de titration "
        "chez les patients adultes SAHOS sévère réfractaires au PPC"
    ),
    intervention="INSPIRE IV système de stimulation hypoglosse",
    domain="somnologie",
    endpoints=[
        Endpoint(
            "IAH à la PSG de titration — lecture PSG centralisée en aveugle",
            EndpointNature.OBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=True,
            is_validated_surrogate=False,
            is_feasibility_accepted_surrogate=True,   # IAH reste primaire, registre post-marché engagé
        ),
        Endpoint(
            "Score Epworth (ESS) à 12 mois",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
        ),
    ],
)

_, output_medium, report_medium = run_pipeline(
    "APRÈS repairs LOW+MEDIUM", EFFECT_APRES_MEDIUM, CLAIM_APRES_MEDIUM
)
print_diagnostic(
    "APRÈS repairs LOW+MEDIUM (sous-groupe IV isolé + lecture PSG centralisée + registre post-marché)",
    report_medium, output_medium
)

# ── tableau de synthèse ───────────────────────────────────────────────────

print(f"\n{'=' * 70}")
print("  SYNTHÈSE — évolution des gaps")
print(f"{'=' * 70}")
print(f"  {'Dossier':<48} {'Risk':<10} Gaps")
print(f"  {_SEP[:65]}")


def risk_emoji(r):
    return {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(r, r)


for label, report in [
    ("AVANT (dossier initial EFFECT)", report_avant),
    ("APRÈS LOW+MEDIUM (dossier corrigé)", report_medium),
]:
    risk = report.overall_risk.value
    n = len(report.gaps)
    dims = ", ".join(f"[{g.severity}]{g.dimension}" for g in report.gaps) or "aucun"
    print(f"  {label:<48} {risk_emoji(risk)} {risk:<8} {n} gap(s) : {dims}")
