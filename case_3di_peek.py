"""Analyse Implant osseux sur mesure 3di en PEEK (substitut crânien, 3di GmbH).

Source : avis CNEDiMTS du 3 décembre 2024 (CNEDIMTS-7534), primo-inscription.
Décision réelle : Service Attendu INSUFFISANT (refus).

Point de modélisation central : HAS souligne "l'absence de données cliniques
SPÉCIFIQUES de l'implant osseux sur mesure 3di en PEEK" — tout ce qui est
fourni concerne des implants PEEK génériques d'autres fabricants (méta-
analyse Punchak et al. 2017, étude Jonkergouw et al., revues systématiques),
jamais le produit 3di lui-même. C'est structurellement le même problème que
BRAINXPERT (CAPTEX 355 ≠ BRAINXPERT) : dispositif étudié ≠ dispositif
revendiqué — modélisé ici via device_studied explicitement différent du
produit de la demande.

Étude retenue pour le STUDY_JSON : méta-analyse Punchak et al. 2017 (183
patients, 15 études), la plus volumineuse des données non spécifiques
analysées par HAS.
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
        "Reconstruction crânienne, sur entente préalable : soit en première intention, en cas de "
        "défect osseux situé dans la zone fronto-temporale ou de grande taille (supérieur à 35 cm²), "
        "soit en deuxième intention, après échec ou impossibilité de l'autogreffe."
    ),
    intervention="Implant osseux sur mesure 3di en PEEK (substitut crânien non résorbable, 3di GmbH)",
    endpoints=[
        Endpoint(
            name="succès de la reconstruction crânienne (absence de complication/échec de l'implant)",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Efficacité et sécurité de l'implant sur mesure 3di en PEEK pour la reconstruction crânienne revendiquée.",
        ),
    ],
    domain="neurochirurgie / reconstruction crânienne",
)

STUDY_JSON = {
    "acronym": "Punchak et al. 2017",
    "title": "Outcomes following polyetheretherketone (PEEK) cranioplasty: systematic review and meta-analysis",
    "publication_year": 2017,
    "registration_id": "",
    "funding_type": "unknown",

    "study_design": "EXPLORATORY",  # méta-analyse de séries de cas et études rétrospectives hétérogènes, pas d'ECR
    "is_randomized": False,
    "blinding_level": "UNKNOWN",
    "who_is_blinded": None,
    "allocation_concealment": None,
    "protocol_registered_before_enrollment": False,  # méthode de réalisation de la méta-analyse non détaillée

    "has_comparator": True,  # sous-comparaisons vs autogreffe osseuse et vs mesh titane au sein de la méta-analyse
    "comparator_type": "active",
    "comparator_description": "Autogreffe osseuse et mesh en titane, comparés indirectement via les études incluses.",

    "n_patients": 183,
    "age_min": None,
    "age_max": None,

    "key_inclusion_criteria": [
        "Séries de cas, analyses comparatives rétrospectives, études de cohorte prospective, rapports de cas",
        "Études décrivant les résultats d'une cranioplastie avec un implant en PEEK (tous fabricants)",
    ],
    "key_exclusion_criteria": [
        "Abstracts et études ne permettant pas de stratifier les résultats par technique de cranioplastie",
    ],

    # cf. avis, citation exacte : "l'implant sur mesure 3di en PEEK ne répond pas aux
    # spécifications techniques minimales de la ligne générique" ET "absence de données
    # cliniques spécifiques" — les études de la méta-analyse portent sur des implants PEEK
    # d'AUTRES fabricants, jamais sur le produit 3di lui-même.
    "device_studied": (
        "Implants PEEK génériques multi-fabricants (méta-analyse de 15 études) — "
        "non spécifiques au produit 3di GmbH objet de la demande"
    ),
    "care_setting": "inpatient",
    "operator_training_required": None,

    "follow_up_months": 24,  # durée de suivi médiane 24,1 mois
    "longest_follow_up_months": 60,  # durées de suivi variables, jusqu'à 5 ans selon les études incluses
    "dropout_rate_pct": None,

    "primary_analysis_set": None,
    "sample_size_calculation_provided": False,

    "primary_endpoint_met": False,  # "aucune différence significative" vs autogreffe ou titane sur complications/échec

    "study_countries": [],  # non précisé, méta-analyse multi-pays

    "key_safety_signals": [
        "28 complications (15,3%) sur les 183 patients ayant reçu l'implant PEEK",
        "16 échecs de l'implant (8,7%)",
    ],

    "multiple_studies_detected": True,
    "other_studies_mentioned": [
        "Jonkergouw et al. 2016 (n=38 patients, 40 implants, bicentrique, rétrospective, non randomisée)",
        "Abu-Ghname et al. 2019 (revue systématique pédiatrique, 640 patients, 20 études hétérogènes)",
        "Van de Vijfeijken et al. (revue de 228 études, 7749 patients, critères non hiérarchisés, "
        "biais de confusion noté : implants hydroxyapatite posés sur défauts plus petits/moins risqués)",
        "Rapport de suivi post-commercialisation 3di GmbH (6046 implants) — ÉCARTÉ par HAS, non publié, "
        "aucun rapport signé par des investigateurs",
    ],

    # cf. avis, citation exacte : "Les critères de jugements principaux, non hiérarchisés
    # étaient les suivants : Infections de l'implant ; Complications ; Taux d'échec."
    "device_alignment": {
        "device_match_type": "DIFFERENT_DEVICE",
        "device_description_study": "Implants PEEK génériques de plusieurs fabricants tiers (méta-analyse Punchak et al.)",
        "justification": (
            "Aucune des études incluses ne porte sur le produit 3di GmbH objet de la demande — "
            "cf. avis : « La Commission souligne l'absence de données cliniques spécifiques de "
            "l'implant osseux sur mesure 3di en PEEK »."
        ),
    },

    "endpoints": [
        {
            "name": "infections de l'implant",
            "is_primary": True,
            "description": "Critère co-principal, non hiérarchisé.",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": False,
        },
        {
            "name": "complications (toutes causes)",
            "is_primary": True,
            "description": "Critère co-principal, non hiérarchisé.",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": False,
        },
        {
            "name": "taux d'échec de l'implant",
            "is_primary": True,
            "description": "Critère co-principal, non hiérarchisé (infection ou résorption nécessitant retrait/remplacement).",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "not_reported",
            "reached_significance": False,
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
    print("=== ENGINE OUTPUT — IMPLANT 3DI EN PEEK ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps ({len(comp.gaps)}):")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension} ({g.topic}): {g.description[:120]}")
    print(f"\nDécision HAS réelle : DEFAVORABLE (SA Insuffisant, avis 03/12/2024, primo-inscription)")
    print("Point clé HAS : \"absence de données cliniques spécifiques\" du produit 3di lui-même.")
