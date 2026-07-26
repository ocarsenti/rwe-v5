"""Analyse VIS-RX (cathéter d'imagerie endocoronaire OCT, Terumo/Gentuity).

Source : avis CNEDiMTS du 9 juin 2026 (CNEDIMTS-8145_VIS-RX), primo-inscription.
Décision réelle : Service Attendu INSUFFISANT (refus).

Deux points de modélisation notables :
1. La SEULE étude comparative (Nishi et al. 2023) a un critère de jugement
   principal purement technique (volume de produit de contraste injecté),
   PAS un critère clinique — alors que la revendication porte sur le
   guidage du traitement avec une ASA III (amélioration modérée du service
   rendu, donc un bénéfice clinique implicite). De plus, ce volume était
   FIXÉ À L'AVANCE (5 ml) pour le bras VIS-RX, pas mesuré naturellement —
   cf. avis : "avec un volume de produit de contraste fixé à l'avance pour
   VIS RX" — rendant la "supériorité" statistique sur ce paramètre
   difficile à interpréter comme un effet réel.
2. Aucune des 3 études retenues (Caron, Quimby, Nishi) n'inclut les
   lésions complexes (tronc commun gauche, vraie bifurcation, lésions
   longues) qui sont pourtant la cible exacte de la revendication —
   mismatch population/indication explicite dans l'avis.
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
        "Guidage au traitement chez les patients nécessitant une angioplastie avec pose de stent "
        "pour un syndrome coronaire chronique (SCC) ou un syndrome coronaire aigu (SCA), pour les "
        "lésions coronaires complexes, en particulier tronc commun gauche, vraie bifurcation, "
        "lésions longues (≥ 30 mm)."
    ),
    intervention="VIS-RX, cathéter d'imagerie endocoronaire par tomographie par cohérence optique (OCT) (Terumo / Gentuity)",
    endpoints=[
        Endpoint(
            name="qualité du guidage de l'angioplastie sur lésions complexes (bénéfice clinique, ASA III revendiquée)",
            nature=EndpointNature.OBJECTIVE,
            causal_role=CausalRole.MEDIATED,  # guidage -> meilleur résultat clinique en aval, pas l'outcome lui-même
            is_primary=True,
            description=(
                "Amélioration modérée du service rendu par rapport à l'angiographie coronaire seule, "
                "pour le guidage du traitement sur lésions coronaires complexes."
            ),
        ),
    ],
    domain="cardiologie interventionnelle",
)

# Nishi et al. 2023 — seule étude comparative parmi les 3 retenues (Caron et
# Quimby sont non comparatives, simple bras, sans comparateur).
STUDY_JSON = {
    "acronym": "Nishi et al. 2023",
    "title": "Efficacy of a new generation intracoronary optical coherence tomography imaging system with fast pullback",
    "publication_year": 2023,
    "registration_id": "",
    "funding_type": "unknown",

    "study_design": "COHORT",  # comparaison intra-patient (chaque patient évalué avec les 2 cathéters), pas un essai randomisé de traitement
    "is_randomized": False,  # seul l'ordre d'ANALYSE des images était randomisé, pas l'attribution du cathéter
    "blinding_level": "OPEN_LABEL",
    "who_is_blinded": None,
    "allocation_concealment": None,
    "protocol_registered_before_enrollment": False,

    "has_comparator": True,
    "comparator_type": "active",  # DRAGONFLY OPTIS, un autre cathéter OCT déjà inscrit
    "comparator_description": "Cathéter DRAGONFLY OPTIS, comparaison intra-patient (mêmes artères évaluées par les 2 systèmes).",

    "n_patients": 10,  # 28 artères évaluées chez 10 patients
    "age_min": None,
    "age_max": None,

    "key_inclusion_criteria": [
        "Patients tout-venant avec maladie coronaire, programmés pour une OCT",
    ],
    "key_exclusion_criteria": [
        "Lésions très tortueuses ou sévèrement calcifiées",
        "Thrombus massif",
    ],

    "device_studied": "VIS-RX (étude Nishi et al. 2023, comparaison à DRAGONFLY OPTIS)",
    "care_setting": "inpatient",
    "operator_training_required": None,

    "follow_up_months": None,  # évaluation peropératoire ponctuelle, pas de suivi longitudinal
    "longest_follow_up_months": None,
    "dropout_rate_pct": None,

    "primary_analysis_set": None,
    "sample_size_calculation_provided": True,  # calcul explicite pour n=10, basé sur la comparaison du volume de contraste

    "primary_endpoint_met": True,  # différence statistiquement significative sur le volume de contraste (p<0,001)

    "study_countries": ["Japon"],
    "is_multicentric": False,

    "key_safety_signals": [],  # aucun événement indésirable rapporté

    "multiple_studies_detected": True,
    "other_studies_mentioned": [
        "Caron et al. 2025 (n=44, monocentrique USA, simple bras, sans comparateur, aucun critère d'inclusion défini)",
        "Quimby et al. 2025 (n=75, multicentrique USA, simple bras, sans comparateur, lésions complexes exclues/non renseignées)",
        "Garin et al. 2024 — écartée par HAS (n=14, méthodologie faible)",
        "Bezerra et al. 2023 — écartée par HAS (absence de critères de sélection et de jugement définis)",
    ],

    # cf. avis, citation exacte : "avec un volume de produit de contraste fixé à l'avance pour
    # VIS RX" — le critère de jugement principal (volume de contraste) est un paramètre
    # technique/procédural, pas un critère clinique, alors que la revendication porte sur un
    # bénéfice clinique (ASA III). Valeur FIXÉE (non mesurée naturellement) dans le bras VIS-RX,
    # ce qui limite fortement l'interprétabilité de la "supériorité" statistique observée.
    "endpoints": [
        {
            "name": "volume de produit de contraste injecté par acquisition OCT",
            "is_primary": True,
            "time_point": "peropératoire, par acquisition",
            "description": (
                "Critère technique/procédural (pas clinique) — valeur FIXÉE à l'avance (5 ml) pour "
                "le bras VIS-RX plutôt que mesurée naturellement, contre mesure libre pour DRAGONFLY OPTIS."
            ),
            "causal_role": "MEDIATED",  # paramètre procédural/de ressource, pas le bénéfice clinique final
            "value_fixed_by_protocol": True,  # cf. doc du parseur, cite explicitement ce cas
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "superior",
            "reached_significance": True,
        },
        {"name": "longueur de l'image nette (CIL)", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
        {"name": "aire de référence proximale", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
        {"name": "diamètre de référence proximal", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
        {"name": "aire de référence minimale (MLA)", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
        {"name": "diamètre de référence minimum", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
        {"name": "aire et diamètre de référence distale", "is_primary": False, "result_direction": "not_reported", "reached_significance": False},
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
    print("=== ENGINE OUTPUT — VIS-RX ===")
    print(f"Bias flags: {[b.flag.value for b in out.bias_flags]}")
    print(f"Overall risk: {comp.overall_risk}")
    print(f"Gaps ({len(comp.gaps)}):")
    for g in comp.gaps:
        print(f"  [{g.severity}] {g.dimension} ({g.topic}): {g.description[:120]}")
    print(f"\nDécision HAS réelle : DEFAVORABLE (SA Insuffisant, avis 09/06/2026, primo-inscription)")
    print("Point clé HAS : \"les résultats de la seule étude comparative ne permettent pas de")
    print("mettre en évidence l'intérêt de VIS-RX en raison des limites sur l'interprétation du")
    print("critère de jugement principal\" — critère technique, valeur fixée a priori, pas clinique.")
