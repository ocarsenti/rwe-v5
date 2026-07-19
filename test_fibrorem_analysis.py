"""Analyse complète FIBROREM (Remedee Labs) — basée sur les vraies données HAS/CNEDiMTS.

Sources :
- Avis CNEDiMTS du 11 mars 2025 (FIBROREM_LPPR.txt)
- Étude FIBREPIK (NCT05058092, Chipon et al. 2022, rapport 22/11/2023)
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison

# ── CLAIM (revendication réelle du demandeur) ──────────────────────────────
CLAIM = ClinicalClaim(
    text=(
        "Le bracelet FIBROREM utilise la neuromodulation par émission d'ondes millimétriques "
        "(61,25 GHz) pour libérer des endorphines endogènes au niveau central, soulageant les "
        "symptômes de patients adultes atteints de fibromyalgie modérée à sévère "
        "(score FIQ ≥ 39) en comparaison à la prise en charge thérapeutique classique "
        "individualisée et pluridisciplinaire."
    ),
    intervention="FIBROREM, bracelet de neuromodulation par émission d'ondes millimétriques associé à l'application mobile myRemedee (Remedee Labs)",
    endpoints=[
        Endpoint(
            name="score FIQ (Fibromyalgia Impact Questionnaire) à 3 mois",
            nature=EndpointNature.SUBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Réduction cliniquement pertinente du FIQ ≥14% entre J0 et 3 mois — auto-questionnaire complété par le patient avant consultation",
        ),
        Endpoint(
            name="qualité du sommeil (Pittsburgh Sleep Quality Index)",
            nature=EndpointNature.SUBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=False,
            description="Évolution du score PSQI entre J0 et 3 mois",
        ),
        Endpoint(
            name="douleur moyenne hebdomadaire (EVA 11 points)",
            nature=EndpointNature.SUBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=False,
            description="Score EVA moyen sur 7 jours consécutifs à 1, 2 et 3 mois",
        ),
        Endpoint(
            name="anxiété et dépression (HAD)",
            nature=EndpointNature.SUBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=False,
            description="Score HAD à J0 et 3 mois",
        ),
    ],
    domain="fibromyalgie / douleur chronique",
)

# ── ÉTUDE FIBREPIK (données réelles reconstituées depuis l'avis HAS) ───────
FIBREPIK_JSON = {
    "acronym": "FIBREPIK",
    "title": "A drug free solution for improving the quality of life of fibromyalgia patients — étude de supériorité contrôlée randomisée",
    "publication_year": 2023,
    "registration_id": "NCT05058092",
    "funding_type": "industry",

    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "open_label",
    "who_is_blinded": None,
    "allocation_concealment": False,  # La randomisation réalisée par les coachs — non en aveugle
    "protocol_registered_before_enrollment": True,

    "has_comparator": True,
    "comparator_type": "standard_of_care",
    "comparator_description": "Prise en charge conventionnelle standardisée de la douleur seule (sans bracelet ni accompagnement personnalisé)",

    "n_patients": 170,
    "age_min": 18,
    "age_max": None,
    "key_inclusion_criteria": [
        "Diagnostic clinique de fibromyalgie selon critères ACR 2016",
        "Score FIQ ≥ 39 (formes modérées à sévères)",
        "Adulte majeur",
        "Possession d'un smartphone compatible",
    ],
    "key_exclusion_criteria": [
        "Épisode dépressif caractérisé (DSM-5)",
        "Modification substantielle de traitement dans les 3 mois précédents",
        "Pathologie inflammatoire chronique associée",
        "Pathologie dermatologique au niveau des poignets",
        "Implant chirurgical, tatouage ou piercing aux deux poignets",
    ],

    "device_studied": "Bracelet FIBROREM génération REM-2 (précédente génération — la demande porte sur REM-3)",
    "care_setting": "outpatient",
    "operator_training_required": True,

    "follow_up_months": 3,
    "longest_follow_up_months": 9,
    "dropout_rate_pct": 10.0,

    "primary_analysis_set": "mITT",  # Pas ITT strict : 165/170 analysés
    "sample_size_calculation_provided": True,

    "primary_endpoint_met": True,  # p=0.021 MAIS analyse non ITT stricte + données manquantes

    "study_countries": ["France"],

    "key_safety_signals": [
        "Sensations de chaleur (17,8%)",
        "Douleurs locales (17,8%)",
        "Paresthésies / lourdeur (14,5%)",
        "Céphalées (14,5%)",
        "3 EIG non liés au bracelet (dépression, intoxication médicamenteuse)",
    ],

    "endpoints": [
        {
            "name": "score FIQ à 3 mois (réduction ≥14%)",
            "is_primary": True,
            "time_point": "3 mois",
            "description": "Réduction cliniquement pertinente du FIQ ≥14% entre J0 et 3 mois — auto-questionnaire complété par le patient avant consultation médicale",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "superior",
            "reached_significance": True,
        },
        {
            "name": "EVA douleur moyenne hebdomadaire",
            "is_primary": False,
            "time_point": "1, 2 et 3 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        },
        {
            "name": "Pittsburgh Sleep Quality Index",
            "is_primary": False,
            "time_point": "3 mois",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": None,
        },
    ],
}

def run():
    study = _parse_study_object_result(FIBREPIK_JSON, CLAIM.intervention, CLAIM.text)
    enrich_claim_with_study_object(CLAIM, study)
    engine_out = analyze(CLAIM)
    comparison = compare_claim_to_study(CLAIM, study, epistemic_output=engine_out)
    repairs = repair_comparison(comparison, CLAIM, epistemic_output=engine_out)
    return study, engine_out, comparison, repairs

if __name__ == "__main__":
    study, out, comp, rep = run()
    print("=== ENGINE OUTPUT ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Design: {out.design_recommendation}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps: {len(comp.gaps)}")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension}: {g.description[:100]}")
