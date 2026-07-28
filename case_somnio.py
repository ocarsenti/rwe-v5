"""Analyse SOMNIO (thérapie cognitivo-comportementale numérique de l'insomnie, ResMed).

Source : avis CNEDiMTS du 15 juillet 2025 (CNEDIMTS-7781_SOMNIO).
Décision réelle : Service Attendu INSUFFISANT (refus).

Ce cas est explicitement cité dans le code de study_object.py comme source
du mécanisme confounding_concomitant ("biais de confusion majeur" — pas de
suivi de la consommation d'hypnotiques concomitants). Reconstruction fidèle
à l'avis, y compris ses points forts méthodologiques réels (ITT, calcul de
taille d'échantillon, groupes comparables à l'inclusion) pour ne pas
sur-noircir le tableau.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison

CLAIM = ClinicalClaim(
    text="Traitement de l'insomnie chronique chez l'adulte.",
    intervention="SOMNIO, thérapie cognitivo-comportementale numérique de l'insomnie (application mobile/web, ResMed / Mementor DE GmbH)",
    endpoints=[
        Endpoint(
            name="sévérité de l'insomnie (score ISI) à 8 semaines",
            nature=EndpointNature.SUBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Auto-questionnaire ISI (Insomnia Severity Index), critère de jugement principal.",
        ),
    ],
    domain="psychiatrie / troubles du sommeil",
)

STUDY_JSON = {
    "acronym": "Schuffelen et al. 2023",
    "title": "The clinical effects of digital cognitive behavioral therapy for insomnia in a heterogenous study sample: results from a randomized controlled trial",
    "publication_year": 2023,
    "registration_id": "DRKS00024477",
    "funding_type": "industry",

    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "OPEN_LABEL",
    "who_is_blinded": None,
    "allocation_concealment": True,  # randomisation par membres non informés des affectations précédentes
    "protocol_registered_before_enrollment": True,
    "is_multicentric": False,  # un centre investigateur (Düsseldorf), recrutement national

    "has_comparator": True,
    "comparator_type": "standard_of_care",
    "comparator_description": (
        "Liste d'attente + soins courants (absence de traitement, traitements médicamenteux "
        "et/ou prise en charge psychologique) — pas le traitement de référence (TCC-i en présentiel)."
    ),

    "n_patients": 238,
    "age_min": 18,
    "age_max": None,
    "key_inclusion_criteria": [
        "Âge ≥ 18 ans",
        "Diagnostic d'insomnie chronique selon le DSM-5 (entretien téléphonique)",
    ],
    "key_exclusion_criteria": [
        "Consommation régulière d'alcool, de cannabis ou d'autres drogues",
        "Idées ou intentions suicidaires dans les 2 semaines précédentes",
        "Épilepsie, schizophrénie, épisode psychotique aigu",
    ],

    "device_studied": "SOMNIO (version allemande) associé aux soins courants vs liste d'attente + soins courants",
    "care_setting": "outpatient",
    "operator_training_required": False,  # utilisation autonome par le patient

    "follow_up_months": 2,  # critère principal évalué à 8 semaines
    "longest_follow_up_months": 12,
    "dropout_rate_pct": 30.0,  # ~30% de données manquantes à 12 mois (non rapporté pour cette raison)

    "primary_analysis_set": "ITT",  # analyse en intention de traiter avec imputation multiple
    "sample_size_calculation_provided": True,  # calcul explicite (ANCOVA, n=220 cible)

    "primary_endpoint_met": True,  # p<0.001, d de Cohen = -2,08

    "study_countries": ["Allemagne"],

    "baseline_groups_comparable": True,  # caractéristiques similaires à l'inclusion (cf. tableau avis)

    # cf. avis, "Bilan des données" : "l'absence de description des traitements
    # hypnotiques pris concomitamment et de l'évolution de leur posologie au
    # cours du temps... constitue un biais de confusion majeur"
    "concomitant_treatments_present": True,  # 41,5%/36,7% des patients sous somnifères à l'inclusion
    "concomitant_treatments_controlled": False,
    "concomitant_treatments_description": (
        "Consommation d'hypnotiques/psychotropes non suivie au cours de l'étude, malgré leur "
        "présence à l'inclusion chez ~40% des patients des deux groupes."
    ),

    "key_safety_signals": [],  # aucun événement indésirable rapporté dans le groupe SOMNIO

    "multiple_studies_detected": True,
    "other_studies_mentioned": [
        "Maurer et al. 2025 (RCT, SOMNIO vs agenda du sommeil) — non retenue par HAS, niveau de preuve insuffisant",
        "Maurer et al. 2025 (observationnelle, n=5000, vie réelle) — retenue mais valeur exploratoire seulement "
        "(biais d'attrition, population moins sévère que l'indication, non protocolisée)",
    ],

    # cf. avis, "Commentaires" : "Nombreux critères de jugement secondaires à
    # valeur exploratoire (pas de prise en compte de la multiplicité des tests)"
    "secondary_endpoints_alpha_correction": False,

    "endpoints": [
        {
            "name": "sévérité de l'insomnie (score ISI) à 8 semaines",
            "is_primary": True,
            "time_point": "8 semaines",
            "description": "Auto-questionnaire, critère de jugement principal.",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "superior",
            "reached_significance": True,
        },
        {"name": "Fatigue (échelle FSS)", "is_primary": False, "result_direction": "superior", "reached_significance": None},
        {"name": "Somnolence diurne (échelle d'Epworth)", "is_primary": False, "result_direction": "superior", "reached_significance": None},
        {"name": "Pensées et attitudes dysfonctionnelles (DBAS)", "is_primary": False, "result_direction": "superior", "reached_significance": None},
        {"name": "Bien-être (WHO-5)", "is_primary": False, "result_direction": "superior", "reached_significance": None},
        {"name": "Qualité de vie — santé physique (WHOQOL-BREF)", "is_primary": False, "result_direction": "superior", "reached_significance": None},
        {"name": "Qualité de vie — santé psychologique (WHOQOL-BREF)", "is_primary": False, "result_direction": "not_reported", "reached_significance": None},
        {"name": "Symptômes dépressifs (ADS-K)", "is_primary": False, "result_direction": "superior", "reached_significance": None},
        {"name": "Anxiété (STAI-T)", "is_primary": False, "result_direction": "superior", "reached_significance": None},
        {"name": "Agenda du sommeil — efficacité du sommeil", "is_primary": False, "result_direction": "superior", "reached_significance": None},
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
    print("=== ENGINE OUTPUT — SOMNIO ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps ({len(comp.gaps)}):")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension} ({g.topic}): {g.description[:110]}")
    print(f"\nDécision HAS réelle : DEFAVORABLE (SA Insuffisant, avis 15/07/2025)")
