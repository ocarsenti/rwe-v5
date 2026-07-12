"""ODYSIGHT / TIL-003 — repair loop : avant → repair → après.

Cas bloquant : claim niveau C (outcome) avec endpoint circulaire + design exploratoire.
Le repair LOW propose une reformulation en claim de performance (niveau A) qui
change complètement le profil de risque sans nouvelle étude.
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


def run_pipeline(study_json, claim):
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
    for g in report.gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:85]}")
        if g.has_critique:
            print(f"           HAS : {str(g.has_critique)[:82]}")
    if not report.gaps:
        print("    ✅  Aucun gap identifié")
    if output.bias_flags:
        for bd in output.bias_flags:
            print(f"  BiasFlag [{bd.severity}] {bd.flag.value}")


# ============================================================
# ÉTUDE TIL-003 (commune aux deux scénarios)
# ============================================================

TIL003_JSON = {
    "acronym": "TIL-003",
    "title": "Étude rétrospective ODYSIGHT — impact dans la prise en charge des maculopathies",
    "publication_year": 2023,
    "funding_type": "industry",
    "study_design": "EXPLORATORY",
    "is_randomized": False,
    "blinding_level": "OPEN_LABEL",
    "has_comparator": False,
    "comparator_type": None,
    "comparator_description": None,
    "n_patients": 112,
    "follow_up_months": 12.0,
    "longest_follow_up_months": 12.0,
    "study_countries": ["France"],
    "key_safety_signals": [],
    "endpoints": [
        {
            "name": "délai de détection rechute DMLA par l'application",
            "is_primary": True,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        },
        {
            # TIL-003 a aussi comparé les alertes ODYSIGHT vs rechutes confirmées
            # par l'ophtalmologue — données disponibles dans le rapport
            "name": "sensibilité de détection des rechutes DMLA vs confirmation ophtalmologue",
            "is_primary": False,
            "time_point": "12 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": True,
            "result_direction": "SUPERIOR",
            "reached_significance": True,
        },
    ],
    "device_alignment": {
        "device_match_type": "EXACT_DEVICE",
        "device_description_study": "ODYSIGHT application de monitoring visuel",
        "device_description_claim": "ODYSIGHT application de monitoring visuel",
        "justification": "Même dispositif que la revendication.",
    },
    "population_alignment": {
        "population_match_type": "NARROWER_SUBGROUP",
        "population_description_study": "DMLA exsudative sous anti-VEGF, 112 patients",
        "population_description_claim": "DMLA exsudative",
        "eligibility_shift": "MINOR",
        "justification": "L'étude ne couvre que les patients déjà sous anti-VEGF (112 patients), "
                          "un sous-groupe plus restreint que l'indication revendiquée (DMLA exsudative, "
                          "sans restriction de traitement concomitant).",
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

# ============================================================
# AVANT — claim niveau C (outcome)
# "ODYSIGHT réduit le délai de traitement des rechutes DMLA"
# ============================================================

CLAIM_AVANT = ClinicalClaim(
    text=(
        "ODYSIGHT détecte précocement les rechutes de DMLA et réduit le délai "
        "de consultation ophtalmologique chez les patients sous anti-VEGF"
    ),
    intervention="ODYSIGHT application de monitoring visuel",
    domain="ophthalmology",
    endpoints=[
        Endpoint(
            "délai de détection rechute DMLA par l'application",
            EndpointNature.INSTRUMENTED,
            CausalRole.CIRCULAR,
            is_primary=True,
            description="délai mesuré par l'app elle-même — ascertainment non indépendant",
        ),
        Endpoint(
            "acuité visuelle à 12 mois",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="non mesuré dans TIL-003",
        ),
    ],
)

study_avant, output_avant, report_avant = run_pipeline(TIL003_JSON, CLAIM_AVANT)
print_diagnostic("AVANT — claim outcome (niveau C) : réduction délai traitement", report_avant, output_avant)

# ── bouton repair ─────────────────────────────────────────────────────────

print(f"\n{'=' * 70}")
print("  BOUTON REPAIR")
print(f"{'=' * 70}")
repair_plan = repair_comparison(report_avant, CLAIM_AVANT, epistemic_output=output_avant)
print(f"\n  is_fully_repairable : {repair_plan.is_fully_repairable}")
print(f"  {repair_plan.repair_summary}\n")
for i, a in enumerate(repair_plan.actions, 1):
    label = _effort_label.get(a.effort, a.effort.value)
    print(f"  {i}. {label} [{a.gap_severity}] {a.gap_dimension.upper()}")
    print(f"     → {a.description}")
    if a.specific_suggestion:
        lines = [a.specific_suggestion[j:j+85] for j in range(0, min(len(a.specific_suggestion), 255), 85)]
        for line in lines:
            print(f"       {line}")

# ============================================================
# APRÈS — claim reformulée niveau A (performance diagnostique)
# Repair LOW appliqué : "ODYSIGHT détecte les rechutes DMLA
# avec sensibilité X% vs examen ophtalmologique de référence"
# ============================================================
#
# Ce que ça change :
#   - Claim level : C (outcome) → A (performance diagnostique)
#   - Endpoint primaire : CIRCULAR (délai détection par l'app)
#                      → INDEPENDENT (sensibilité vs ophtalmologue)
#   - La circularité disparaît : on compare l'app à une référence externe
#   - Un design exploratoire est acceptable pour un claim de niveau A
#     (étude de performance diagnostique)

CLAIM_APRES = ClinicalClaim(
    text=(
        "ODYSIGHT détecte les rechutes de DMLA exsudative avec une sensibilité ≥ 80% "
        "et une spécificité ≥ 75% vs la confirmation par examen ophtalmologique de référence, "
        "chez les patients sous anti-VEGF en suivi mensuel"
    ),
    intervention="ODYSIGHT application de monitoring visuel",
    domain="ophthalmology",
    endpoints=[
        Endpoint(
            "sensibilité et VPP vs examen ophtalmologique de référence",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,   # comparé à une référence externe — plus circulaire
            is_primary=True,
            is_independently_adjudicated=True,
            description=(
                "signaux ODYSIGHT validés ou infirmés par ophtalmologue en aveugle "
                "(gold standard : examen OCT + FO) — ascertainment indépendant du dispositif"
            ),
        ),
        Endpoint(
            "spécificité (taux de faux positifs) vs examen de référence",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            is_independently_adjudicated=True,
            description="confirmation indépendante de l'absence de rechute",
        ),
    ],
)

study_apres, output_apres, report_apres = run_pipeline(TIL003_JSON, CLAIM_APRES)
print_diagnostic(
    "APRÈS repair LOW — claim performance diagnostique (niveau A) : sensibilité/spécificité",
    report_apres, output_apres
)

# ── synthèse ─────────────────────────────────────────────────────────────

print(f"\n{'=' * 70}")
print("  SYNTHÈSE — évolution des gaps")
print(f"{'=' * 70}")
print(f"  {'Dossier':<52} {'Risk':<10} Gaps")
print(f"  {_SEP[:68]}")


def risk_emoji(r):
    return {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(r, r)


for label, report in [
    ("AVANT — claim outcome (réduit délai traitement)", report_avant),
    ("APRÈS LOW — claim performance (sensibilité/spéc.)", report_apres),
]:
    risk = report.overall_risk.value
    n = len(report.gaps)
    dims = ", ".join(f"[{g.severity}]{g.dimension}" for g in report.gaps) or "aucun"
    print(f"  {label:<52} {risk_emoji(risk)} {risk:<8} {n} gap(s) : {dims}")

print(f"""
  ─ Ce que le repair LOW change ──────────────────────────────────────
  La circularité disparaît parce que la claim ne revendique plus une
  réduction du délai de traitement (outcome clinique), mais une capacité
  de détection mesurée contre un étalon externe indépendant (ophtalmologue).
  Le même design exploratoire TIL-003 devient acceptable pour ce niveau
  de claim — une étude de performance diagnostique n'a pas besoin d'un RCT.
""")
