"""Analyse TRIPLE ACTION (articulation de cheville modulaire, Alianza/Becker Orthopedic).

Source : avis CNEDiMTS du 28 janvier 2025 (CNEDIMTS-7620_TRIPLE_ACTION).
Décision réelle : Service Attendu INSUFFISANT (refus).

Reconstruction fidèle à l'avis — tout champ non mentionné dans l'avis est
laissé à None/vide plutôt que deviné (ex: blinding_level, follow_up_months,
care_setting : rien dans l'avis ne les précise pour ce type d'étude
biomécanique en laboratoire de marche).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison

CLAIM = ClinicalClaim(
    text=(
        "Compensation de déficits fonctionnels de la marche pour des flexions plantaires "
        "(équin) ou dorsales (talus) excessives ou limitées, non fixées, avec absence "
        "d'altération du contrôle de la phase d'appui et/ou de la phase pendulaire rendant "
        "la marche inefficace et fatigante chez les enfants et les adultes."
    ),
    intervention=(
        "TRIPLE ACTION, articulation de cheville modulaire pour orthèse du membre inférieur "
        "(Alianza Techniques d'Orthopédie / Becker Orthopedic)"
    ),
    endpoints=[
        Endpoint(
            name="efficacité et confort de la marche (réduction de la fatigue)",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description=(
                "Amélioration de l'efficacité fonctionnelle de la marche et réduction de la "
                "fatigue liée aux déficits de flexion plantaire/dorsale, telle que revendiquée "
                "dans l'indication."
            ),
        ),
    ],
    domain="orthopédie / rééducation fonctionnelle de la marche",
)

# Étude Kobayashi et al. 2018 (n=10) — la plus grande des 2 études fournies.
# L'étude Kobayashi et al. 2016 (n=6) est signalée séparément via
# multiple_studies_detected, pas fusionnée dedans (méthodologie quasi
# identique et mêmes limites, selon l'avis).
STUDY_JSON = {
    "acronym": "Kobayashi 2018",
    "title": (
        "The effects of an articulated ankle-foot orthosis with resistance-adjustable "
        "joints on lower limb joint kinematics and kinetics during gait in individuals "
        "post-stroke"
    ),
    "publication_year": 2018,
    "registration_id": "",
    "funding_type": "unknown",

    "study_design": "EXPLORATORY",
    "is_randomized": False,
    "blinding_level": "UNKNOWN",  # non précisé dans l'avis pour ce type d'étude biomécanique
    "who_is_blinded": None,
    "allocation_concealment": None,
    "protocol_registered_before_enrollment": None,

    "has_comparator": False,
    "comparator_type": None,
    "comparator_description": "",

    "n_patients": 10,
    "age_min": None,
    "age_max": None,  # âge moyen 58 ans (ET=13) rapporté, pas de min/max
    "key_inclusion_criteria": [
        "Minimum 6 mois après un AVC avec hémiparésie",
        "Capacité à marcher en sécurité sur tapis roulant instrumenté avec AFO",
    ],
    "key_exclusion_criteria": [],

    "device_studied": (
        "Orthèse articulée cheville-pied avec articulations TRIPLE ACTION "
        "(étude Kobayashi et al. 2018)"
    ),
    "care_setting": "",
    "operator_training_required": None,

    "follow_up_months": None,  # évaluation ponctuelle en laboratoire de marche, pas de suivi longitudinal
    "longest_follow_up_months": None,
    "dropout_rate_pct": None,

    "primary_analysis_set": None,
    "sample_size_calculation_provided": False,  # "Aucun calcul concernant le nombre de sujets nécessaires"

    "primary_endpoint_met": None,  # critères non hiérarchisés, résultats non interprétables selon HAS

    "study_countries": ["USA"],

    "key_safety_signals": [],  # "Non décrits dans les études" ; matériovigilance : aucun événement

    "multiple_studies_detected": True,
    "other_studies_mentioned": [
        "Kobayashi et al. 2016 (n=6) — étude antérieure sur genu recurvatum, "
        "mêmes limites méthodologiques (non comparative, monocentrique, critères biomécaniques)"
    ],

    "endpoints": [
        {
            "name": "angle de flexion plantaire maximal de la cheville",
            "is_primary": True,  # "critères de jugement non hiérarchisés" — aucun désigné comme principal
            "time_point": "sous 8 réglages de résistance",
            "description": "Critère biomécanique, non clinique.",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        },
        {
            "name": "moment maximal de dorsiflexion de la cheville",
            "is_primary": True,
            "time_point": "sous 8 réglages de résistance",
            "description": "Critère biomécanique, non clinique.",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        },
        {
            "name": "angle d'extension maximal du genou",
            "is_primary": True,
            "time_point": "sous 8 réglages de résistance",
            "description": "Critère biomécanique, non clinique.",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        },
        {
            "name": "moment de flexion maximal du genou",
            "is_primary": True,
            "time_point": "sous 8 réglages de résistance",
            "description": "Critère biomécanique, non clinique.",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        },
    ],
}


def run():
    study = _parse_study_object_result(STUDY_JSON, CLAIM.intervention, CLAIM.text)
    enrich_claim_with_study_object(CLAIM, study)
    engine_out = analyze(CLAIM)
    comparison = compare_claim_to_study(CLAIM, study, epistemic_output=engine_out)
    repairs = repair_comparison(comparison, CLAIM, epistemic_output=engine_out)
    return study, engine_out, comparison, repairs


if __name__ == "__main__":
    study, out, comp, rep = run()
    print("=== ENGINE OUTPUT — TRIPLE ACTION ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps ({len(comp.gaps)}):")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension} ({g.topic}): {g.description[:110]}")
    print(f"\nDécision HAS réelle : DEFAVORABLE (SA Insuffisant, avis 28/01/2025)")
