"""Analyse I-STOP (bandelette sous-urétrale, DiLo Medical / Apis Technologies).

Source : avis CNEDiMTS du 26 mars 2024 (CNEDIMTS-7439_I-STOP), renouvellement
d'inscription intra-GHS.
Décision réelle : Service Rendu INSUFFISANT (refus).

Note de contexte importante (hors scope du moteur, qui analyse le design des
études soumises, pas la conformité administrative) : la raison principale du
refus HAS est que l'étude post-inscription VIGI-ISTOP, demandée dès 2020,
n'a jamais livré de résultats (seul un protocole a été fourni). Ce n'est pas
un défaut de méthodologie d'étude à proprement parler, mais un engagement
réglementaire non tenu. Le moteur ne peut évaluer que les données
effectivement soumises (études Collet et al. et Crites-Bachert et al.),
qui présentent elles-mêmes de vraies faiblesses méthodologiques indépendantes
de ce problème d'engagement — c'est ce que ce script teste.
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
        "Incontinence urinaire féminine d'effort pure ou prédominante associée à une "
        "hypermobilité urétrale prédominante après échec des traitements conservateurs "
        "ou d'emblée en cas d'incontinence urinaire d'effort sévère ; incontinence urinaire "
        "féminine d'effort pure ou prédominante associée à une hypermobilité urétrale "
        "prédominante récidivante après échec d'un traitement chirurgical antérieur."
    ),
    intervention="I-STOP, bandelette sous-urétrale implantée par voie rétropubienne ou transobturatrice (DiLo Medical / Apis Technologies)",
    endpoints=[
        Endpoint(
            name="guérison de l'incontinence urinaire d'effort et satisfaction des patientes",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.INDEPENDENT,
            is_primary=True,
            description="Résolution des fuites urinaires d'effort et satisfaction globale rapportée par les patientes.",
        ),
    ],
    domain="urologie / incontinence urinaire féminine",
)

# Étude Collet et al. (non publiée, n=420) — la plus grande des 2 études
# spécifiques soumises pour le renouvellement 2024. Crites-Bachert et al.
# (n=300, États-Unis) signalée séparément.
STUDY_JSON = {
    "acronym": "Collet et al.",
    "title": (
        "Étude rétrospective évaluant la sécurité et l'efficacité des bandelettes "
        "synthétiques I-STOP dans le traitement de l'incontinence urinaire d'effort de la femme"
    ),
    "publication_year": None,  # non publiée
    "registration_id": "",
    "funding_type": "unknown",

    "study_design": "COHORT",
    "is_randomized": False,
    "blinding_level": "OPEN_LABEL",  # auto-questionnaire, pas d'aveugle possible/mentionné
    "who_is_blinded": None,
    "allocation_concealment": None,
    "protocol_registered_before_enrollment": False,  # inclusions rétrospectives

    "has_comparator": False,
    "comparator_type": None,
    "comparator_description": "",

    "n_patients": 420,
    "age_min": None,
    "age_max": None,  # âge moyen 56,98 ans (ET=11,50) à l'implantation, pas de min/max
    "key_inclusion_criteria": [
        "Patientes adultes avec incontinence urinaire d'effort de tout stade après traitement conservateur",
        "Opérées entre juin 2004 et juin 2018 dans le centre recruteur",
        "Ayant répondu au questionnaire de l'étude (envoyé en juin 2020)",
    ],
    "key_exclusion_criteria": [],

    "device_studied": "Bandelette sous-urétrale I-STOP (étude Collet et al., non publiée)",
    "care_setting": "",
    "operator_training_required": None,

    "follow_up_months": 24,   # recul à 2 ans rapporté pour un sous-groupe (n=90)
    "longest_follow_up_months": 180,  # recul à 15 ans rapporté pour un sous-groupe (n=93)
    "dropout_rate_pct": None,  # non précisé : pas de dénominateur des patientes éligibles non répondantes

    "primary_analysis_set": None,
    "sample_size_calculation_provided": False,  # non mentionné, questionnaire non validé

    "primary_endpoint_met": None,  # critères non hiérarchisés, résultats descriptifs seulement

    "study_countries": ["France"],

    "key_safety_signals": [
        "Reprise chirurgicale liée à la bandelette : 2,14% (population totale)",
        "Récidive/persistance d'IUE autodéclarée : jusqu'à 40,86% (sous-groupe 15 ans de recul)",
    ],

    "multiple_studies_detected": True,
    "other_studies_mentioned": [
        "Crites-Bachert et al. 2021 (n=300, États-Unis) — étude rétrospective mono-opérateur, "
        "mêmes limites méthodologiques (non comparative, monocentrique, questionnaires non validés)"
    ],

    "endpoints": [
        {
            "name": "satisfaction des patientes et récidive/persistance de l'IUE (auto-questionnaire non validé)",
            "is_primary": True,
            "time_point": "recueil ponctuel par questionnaire postal en juin 2020, recul variable (2 à 15 ans)",
            "description": (
                "Taux de satisfaction globale et de récidive/persistance de l'IUE, recueillis via un "
                "questionnaire élaboré spécifiquement pour l'étude, non validé, envoyé par courrier."
            ),
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "mixed",  # 72% satisfaction globale mais 37-41% récidive/persistance selon sous-groupe
            "reached_significance": None,  # étude descriptive, pas de test statistique comparatif
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
    print("=== ENGINE OUTPUT — I-STOP ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps ({len(comp.gaps)}):")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension} ({g.topic}): {g.description[:110]}")
    print(f"\nDécision HAS réelle : DEFAVORABLE (SR Insuffisant, avis 26/03/2024)")
    print("Note : refus principalement motivé par l'absence de résultats de l'étude")
    print("post-inscription demandée (VIGI-ISTOP) — hors scope du moteur (engagement")
    print("réglementaire, pas méthodologie d'étude).")
