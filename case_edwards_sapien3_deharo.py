"""Analyse EDWARDS SAPIEN 3 — revendication de revalorisation d'ASR (high-risk/
contre-indication chirurgicale) basée sur l'étude Deharo et al. 2020.

Source : avis CNEDiMTS du 26/03/2024 (CNEDIMTS-7350_EDWARDS_SAPIEN_3), fourni
par Olivier (upload PDF complet).

Décision réelle sur CETTE revendication précise : ASR I demandée, REJETÉE —
la Commission a maintenu ASR V (absence d'amélioration) pour cette
sous-population, en raison des limites méthodologiques de l'étude Deharo et
al. Le SR global du dispositif reste par ailleurs Suffisant (dossier globalement
solide, porté par PARTNER 3 pour le bas risque) — ce cas teste spécifiquement
si le moteur repère la faiblesse d'UNE étude dans un dossier par ailleurs
robuste, sans le noyer dans le reste.
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
        "Chez les patients contre-indiqués à la chirurgie de remplacement valvulaire aortique ou "
        "à haut risque chirurgical (score STS ou EuroSCORE II ≥ 8%), la bioprothèse EDWARDS "
        "SAPIEN 3 associée au système COMMANDER présente une amélioration majeure du service "
        "rendu (ASR I) par rapport aux autres bioprothèses valvulaires aortiques implantées par "
        "voie transcathéter, notamment la gamme COREVALVE EVOLUT."
    ),
    intervention="EDWARDS SAPIEN 3 avec système COMMANDER, bioprothèse valvulaire aortique transfémorale (Edwards Lifesciences)",
    endpoints=[
        Endpoint(
            name="supériorité clinique vs COREVALVE EVOLUT R (mortalité, AVC, réhospitalisation)",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Revendication de supériorité clinique justifiant une ASR I par rapport au comparateur actif EVOLUT R.",
        ),
    ],
    domain="cardiologie / valvulopathies",
)

STUDY_JSON = {
    "acronym": "Deharo et al. 2020",
    "title": (
        "Impact of Sapien 3 balloon-expandable versus Evolut R self-expandable transcatheter "
        "aortic valve implantation in patients with aortic stenosis: data from a nationwide analysis"
    ),
    "publication_year": 2020,
    "registration_id": "",
    "funding_type": "unknown",

    "study_design": "COHORT",  # rétrospective, base médico-administrative (PMSI)
    "is_randomized": False,
    "blinding_level": "OPEN_LABEL",  # étude rétrospective sur données administratives, pas d'aveugle possible
    "who_is_blinded": None,
    "allocation_concealment": None,
    "protocol_registered_before_enrollment": False,  # étude rétrospective sur base existante, pas de protocole a priori

    "has_comparator": True,
    "comparator_type": "active",  # COREVALVE EVOLUT R, un comparateur actif, pas un placebo/soin standard
    "comparator_description": "COREVALVE EVOLUT R, autre bioprothèse valvulaire aortique transcathéter auto-expansible.",

    "n_patients": 20918,  # identifiés avant appariement ; 10459 par bras après appariement par score de propension
    "age_min": None,
    "age_max": None,  # âge moyen 83 ans dans les deux bras

    "key_inclusion_criteria": [
        "Patients identifiés via code diagnostic CIM-10 (I350, I352, I060), acte d'implantation DBFL001 "
        "et code LPP de la bioprothèse implantée (EDWARDS SAPIEN 3 ou COREVALVE EVOLUT R), 2014-2018",
    ],
    "key_exclusion_criteria": [],

    "device_studied": "EDWARDS SAPIEN 3 (étude Deharo et al. 2020, comparaison à COREVALVE EVOLUT R)",
    "care_setting": "inpatient",
    "operator_training_required": None,

    "follow_up_months": 12,  # suivi moyen de 358 jours ± 384
    "longest_follow_up_months": 12,
    "dropout_rate_pct": None,  # non applicable — étude sur base médico-administrative rétrospective

    "primary_analysis_set": None,
    "sample_size_calculation_provided": False,  # étude sur base de données existante, pas de calcul a priori

    "primary_endpoint_met": None,  # multiples critères, non hiérarchisés — pas de verdict unique possible

    "study_countries": ["France"],
    "is_multicentric": True,  # base nationale PMSI, tous établissements français

    # cf. avis, texte exact : "il persiste un risque de biais de confusion inhérent à ce type
    # d'étude où certaines variables d'importance ne sont pas prises en compte lors de
    # l'appariement des patients" (préférence du praticien, caractéristiques anatomiques) —
    # confusion résiduelle au-delà des 38 variables déjà incluses dans le score de propension,
    # pas un facteur de confusion identifié et non contrôlé au sens classique (concomitant_treatments).
    # Modélisé ici via baseline_groups_comparable=False, le plus proche mécanisme existant.
    "baseline_groups_comparable": False,
    "baseline_imbalance_description": (
        "Score de propension incluant 38 variables mais ne capturant pas la préférence du "
        "praticien ni certaines caractéristiques anatomiques ; légèrement plus de patients "
        "fragiles dans le groupe COREVALVE EVOLUT R."
    ),

    "key_safety_signals": [],

    "multiple_studies_detected": True,
    "other_studies_mentioned": [
        "Méta-analyse Senguttuvan et al. 2023 (n=3141, générations de valves anciennes, retenue séparément)",
        "PARTNER 3 (bas risque, non concerné par cette revendication ASR I)",
    ],

    # cf. avis, texte exact : "Les critères de jugement étaient multiples et non hiérarchisés."
    "endpoints": [
        {"name": "décès toutes causes", "is_primary": True, "result_direction": "superior", "reached_significance": True},
        {"name": "décès cardiovasculaires", "is_primary": True, "result_direction": "superior", "reached_significance": True},
        {"name": "AVC", "is_primary": True, "result_direction": "not_reported", "reached_significance": False},
        {"name": "réhospitalisation pour insuffisance cardiaque", "is_primary": True, "result_direction": "superior", "reached_significance": True},
        {"name": "composite décès cardiovasculaire + AVC + réhospitalisation IC", "is_primary": True, "result_direction": "superior", "reached_significance": True},
        {"name": "nouveau stimulateur cardiaque à 30 jours", "is_primary": True, "result_direction": "superior", "reached_significance": True},
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
    print("=== ENGINE OUTPUT — EDWARDS SAPIEN 3 (revendication ASR I, étude Deharo) ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps ({len(comp.gaps)}):")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension} ({g.topic}): {g.description[:120]}")
    print(f"\nDécision HAS réelle sur cette revendication : ASR I refusée, maintien ASR V")
    print("(SR global du dispositif par ailleurs Suffisant, non remis en cause)")
