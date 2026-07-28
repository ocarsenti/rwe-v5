"""Analyse MAIOREGEN PRIME (substitut chondral et ostéochondral, Fin-Ceramica).

Source : avis CNEDiMTS du 6 mai 2025 (CNEDIMTS-7282_MAIOREGEN_PRIME).
Décision réelle : Service Attendu INSUFFISANT (refus, primo-inscription).

Point de modélisation important : la revendication du demandeur cible
spécifiquement les "lésions ostéochondrales profondes" (Outerbridge Grade
IV) — le seul sous-groupe où l'étude Kon et al. montre une différence
statistiquement significative (+12,4 points IKDC, analyse post-hoc, non
prévue au protocole selon HAS). Sur la population totale pré-spécifiée,
la différence n'est PAS significative. Modélisé ici sur le résultat
global pré-spécifié (primary_endpoint_met=False), pas sur le sous-groupe
post-hoc favorable — pour ne pas fabriquer un succès qui n'est pas le
résultat principal réel de l'étude. Le mécanisme "cherry-picking d'un
sous-groupe post-hoc" n'a pas de gap dédié dans le moteur actuel (angle
mort noté, pas simulé artificiellement).
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
        "Lésions ostéochondrales profondes, uniques/multiples avec une atteinte sévère du tissu "
        "sous-chondral, Outerbridge Grade IV. Les lésions peuvent être d'origine traumatique, "
        "post-traumatique ou dégénérative, ainsi que causées par une ostéochondrite disséquante (OCD)."
    ),
    intervention="MAIOREGEN PRIME, substitut chondral et ostéochondral (matrice collagène-hydroxyapatite, Fin-Ceramica)",
    endpoints=[
        Endpoint(
            name="score IKDC subjectif à 24 mois",
            nature=EndpointNature.SUBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Auto-évaluation fonctionnelle du genou, critère de jugement principal de l'étude pivot.",
        ),
    ],
    domain="orthopédie / réparation cartilagineuse",
)

STUDY_JSON = {
    "acronym": "Kon et al. 2018",
    "title": (
        "A multilayer biomaterial for osteochondral regeneration shows superiority vs "
        "microfractures for the treatment of osteochondral lesions in a multicentre randomized trial at 2 years"
    ),
    "publication_year": 2018,
    "registration_id": "NCT01282034",
    "funding_type": "industry",

    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "SINGLE_BLIND",  # patient en aveugle du traitement (pas l'évaluateur)
    "who_is_blinded": "patient",
    "allocation_concealment": None,  # non précisé dans l'avis
    "protocol_registered_before_enrollment": True,
    "is_multicentric": True,  # 15 centres, 9 pays

    "has_comparator": True,
    "comparator_type": "active",  # techniques de stimulation de la moelle osseuse (BMS), traitement actif de référence
    "comparator_description": (
        "Techniques de stimulation de la moelle osseuse (forage sous-chondral ou microfractures selon Steadman)."
    ),

    "n_patients": 118,  # population ITT ; analyse focalisée sur la population PP (n=100 : 51/49)
    "age_min": 18,
    "age_max": 60,
    "key_inclusion_criteria": [
        "Âge 18-60 ans",
        "Lésion chondrale symptomatique du genou grade III/IV (Outerbridge) ou lésion ostéochondrale",
        "Lésion unique, 2 à 9 cm²",
    ],
    "key_exclusion_criteria": [
        "IMC > 30",
        "Arthrose avancée (Kellgren-Lawrence ≥ 3)",
        "Lésions multiples ou en miroir",
    ],

    "device_studied": "MAIOREGEN PRIME (étude Kon et al. 2018)",
    "care_setting": "inpatient",
    "operator_training_required": True,  # chirurgien orthopédique

    "follow_up_months": 24,
    "longest_follow_up_months": 24,
    "dropout_rate_pct": 19.0,  # 124 randomisés -> 100 en population PP analysée (~19% d'attrition)

    # cf. avis, texte exact : "La taille de l'échantillon pour chaque groupe de l'étude a été
    # estimée à 67 patients... En raison d'une période de recrutement prolongée, il a été décidé
    # d'interrompre l'étude" — calcul fourni mais cible NON atteinte (51/49 au lieu de 67/67).
    # Modélisé à True (le calcul existe et est documenté) ; la nuance "cible non atteinte" n'a
    # pas de champ dédié dans le schéma actuel du moteur.
    "sample_size_calculation_provided": True,

    "primary_analysis_set": "PP",  # analyse focalisée sur la population per-protocol, pas ITT
    "primary_endpoint_met": False,  # IKDC subjectif à 24 mois, population totale : "N.S." (non significatif)

    "study_countries": ["Allemagne", "Autriche", "Belgique", "Italie", "Norvège", "Pologne", "Suède", "Suisse", "Afrique du Sud"],

    # cf. avis, "Bilan des données", citation exacte : "les deux groupes ne sont pas
    # complètement homogènes (plus de lésions rotuliennes pour le groupe BMS) et d'autres
    # interventions chirurgicales sont effectuées dans le même temps dans le groupe matrice"
    "baseline_groups_comparable": False,
    "baseline_imbalance_description": (
        "Davantage de lésions rotuliennes dans le groupe BMS (40,8% vs 23,5%) ; répartition "
        "différente entre condyle/trochlée/patella selon le bras."
    ),

    # Modélisé ici pour représenter la même famille de biais de co-intervention que
    # confounding_concomitant (asymétrie d'intervention entre bras), mais il s'agit ici
    # d'interventions CHIRURGICALES concomitantes (pas de traitements médicamenteux) — cf.
    # avis : "d'autres interventions chirurgicales sont effectuées dans le même temps dans le
    # groupe matrice" (37,3% vs 28,6% de chirurgie associée). Choix de modélisation à valider :
    # le champ est nommé "traitements" mais son mécanisme (confusion par intervention
    # asymétrique) s'applique conceptuellement à ce cas.
    "concomitant_treatments_present": True,
    "concomitant_treatments_controlled": False,
    "concomitant_treatments_description": (
        "Chirurgie associée réalisée dans le même temps opératoire chez 37,3% des patients du "
        "groupe MAIOREGEN PRIME contre 28,6% du groupe BMS — asymétrie non contrôlée entre bras."
    ),

    "key_safety_signals": [
        "3 complications sévères groupe MAIOREGEN PRIME (adhésions articulaires x2, douleur persistante x1) vs 1 groupe BMS",
    ],

    "multiple_studies_detected": True,
    "other_studies_mentioned": [
        "Revue systématique Ambrosi et al. 2019 (16 études, 471 patients, dont 15 observationnelles)",
        "5 études observationnelles complémentaires (Condello, Delcogliano, Di Martino, Sessa x2) — valeur exploratoire",
    ],

    # cf. avis : score IKDC, KOOS, Tegner, VAS douleur, MOCART (IRM) — au moins 4 familles de
    # critères secondaires distincts évalués à plusieurs temps, sans mention de correction du
    # risque alpha.
    "secondary_endpoints_alpha_correction": False,

    "endpoints": [
        {
            "name": "score IKDC subjectif à 24 mois",
            "is_primary": True,
            "time_point": "24 mois",
            "description": "Critère de jugement principal, population totale : différence non significative (N.S.).",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": False,
        },
        {"name": "Score KOOS (douleur, symptômes, fonction, sport, qualité de vie)", "is_primary": False, "result_direction": "not_reported", "reached_significance": None},
        {"name": "Score d'activité de Tegner", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
        {"name": "Douleur (échelle VAS)", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
        {"name": "Score MOCART (évaluation IRM de la réparation cartilagineuse)", "is_primary": False, "result_direction": "not_reported", "reached_significance": None},
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
    print("=== ENGINE OUTPUT — MAIOREGEN PRIME ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps ({len(comp.gaps)}):")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension} ({g.topic}): {g.description[:120]}")
    print(f"\nDécision HAS réelle : DEFAVORABLE (SA Insuffisant, avis 06/05/2025, primo-inscription)")
