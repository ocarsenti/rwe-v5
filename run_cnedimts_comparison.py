"""
Comparaison pipeline RWE-v5 vs critiques réelles CNEDiMTS
15 avis représentatifs — LPPR + LATM + PECAN
"""

from __future__ import annotations
import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from models import (
    ClinicalClaim, Endpoint, EndpointNature, CausalRole, ClaimLevel,
)
from engine import analyze

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ep(name, nature, role, primary=True, desc="",
       validated_surrogate=False, adjudicated=False):
    return Endpoint(
        name=name,
        nature=nature,
        causal_role=role,
        is_primary=primary,
        description=desc,
        is_validated_surrogate=validated_surrogate,
        is_independently_adjudicated=adjudicated,
    )


# ---------------------------------------------------------------------------
# 15 ClinicalClaims basés sur les avis CNEDiMTS
# ---------------------------------------------------------------------------

CASES = [

    # 1 — INSPIRE IV (LPPR, FAVORABLE, mars 2022)
    # Critique HAS : endpoint IAH = surrogate, population très sélectionnée (échec PPC),
    # données ADHERE (registre) non randomisées
    {
        "id": "INSPIRE_IV",
        "has_decision": "FAVORABLE (ASA IV)",
        "has_critique": "Endpoint IAH = surrogate polysomnographique. Données ADHERE non randomisées. Population très sélectionnée.",
        "claim": ClinicalClaim(
            text="INSPIRE IV stimule le nerf hypoglosse et réduit l'IAH chez les patients SAHOS modéré à sévère en échec de PPC",
            intervention="INSPIRE IV",
            domain="respiratory",
            endpoints=[
                ep("IAH — Indice Apnée-Hypopnée", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                   primary=True, desc="mesure polysomnographique du nombre d'apnées par heure"),
                ep("somnolence diurne ESS", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
                ep("qualité de vie FOSQ", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
            ]
        ),
    },

    # 2 — EDWARDS SAPIEN 3 (LPPR, FAVORABLE, mars 2024)
    # Critique HAS : étude PARTNER 3 en ouvert → risque adjudication AVC/réhospitalisation.
    # Nouvelles données principalement non spécifiques (méta-analyse).
    {
        "id": "EDWARDS_SAPIEN_3",
        "has_decision": "FAVORABLE (ASA IV/V selon sous-groupe)",
        "has_critique": "Données non spécifiques (méta-analyse). Étude PARTNER 3 ouverte → biais adjudication AVC et réhospitalisations. Nouvelle indication (faible risque chirurgical) peu documentée.",
        "claim": ClinicalClaim(
            text="EDWARDS SAPIEN 3 réduit la mortalité et les complications cardiovasculaires chez les patients avec sténose aortique sévère",
            intervention="EDWARDS SAPIEN 3",
            domain="cardiology",
            endpoints=[
                ep("mortalité toutes causes à 30 jours", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="all-cause mortality 30-day", adjudicated=True),
                ep("AVC à 30 jours", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="stroke — open-label trial PARTNER 3"),
                ep("réhospitalisation cardiovasculaire", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="cardiovascular rehospitalization — open-label trial"),
            ]
        ),
    },

    # 3 — ZEPHYR (LPPR, FAVORABLE, juin 2024)
    # Critique HAS : VEMS = critère fonctionnel surrogate, suivi 12 mois court, études mixtes
    {
        "id": "ZEPHYR",
        "has_decision": "FAVORABLE (ASR III)",
        "has_critique": "Endpoint VEMS = critère fonctionnel (surrogate). Hétérogénéité des études. Suivi 12 mois insuffisant pour emphysème.",
        "claim": ClinicalClaim(
            text="ZEPHYR réduit la distension pulmonaire et améliore la fonction respiratoire chez les patients BPCO emphysème sévère",
            intervention="ZEPHYR valves endobronchiques",
            domain="respiratory",
            endpoints=[
                ep("VEMS — Volume Expiratoire Maximal Seconde", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                   primary=True, desc="functional spirometry measure — surrogate for dyspnea and hospitalization"),
                ep("dyspnée mMRC", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
                ep("test de marche 6 minutes", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
            ]
        ),
    },

    # 4 — FREESTYLE LIBRE 2 PLUS (LPPR, FAVORABLE, 2023)
    # Critique HAS : HbA1c validée comme surrogate dans le diabète type 1 + données spécifiques
    # Expected : relativement propre (is_validated_surrogate=True)
    {
        "id": "FREESTYLE_LIBRE_2_PLUS",
        "has_decision": "FAVORABLE (ASA IV)",
        "has_critique": "Données comparatives limitées. Transposabilité populations (adultes vs pédiatrique). Durée suivi.",
        "claim": ClinicalClaim(
            text="FreeStyle Libre 2 Plus améliore le contrôle glycémique et réduit l'HbA1c chez les patients diabétiques type 1",
            intervention="FreeStyle Libre 2 Plus",
            domain="endocrinology",
            endpoints=[
                ep("HbA1c — hémoglobine glyquée", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                   primary=True, desc="validated glycemic surrogate for diabetes outcomes",
                   validated_surrogate=True),
                ep("temps dans la cible glycémique TIR", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                   primary=False, desc="time-in-range glycemic metric"),
            ]
        ),
    },

    # 5 — ODYSIGHT (LATM, INDETERMINÉ)
    # Critique HAS : endpoint = détection précoce par l'app → tautologie instrumentale
    {
        "id": "ODYSIGHT",
        "has_decision": "INDETERMINÉ",
        "has_critique": "Endpoint primaire = délai de détection par le dispositif lui-même. Design non comparatif. Pas d'impact démontré sur la perte visuelle finale.",
        "claim": ClinicalClaim(
            text="ODYSIGHT détecte précocement les rechutes de DMLA et réduit le délai de traitement chez les patients sous anti-VEGF",
            intervention="ODYSIGHT application de monitoring visuel",
            domain="ophthalmology",
            endpoints=[
                ep("délai de détection rechute DMLA", EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR,
                   primary=True, desc="time-to-detection by device — alert-triggered"),
                ep("délai de traitement anti-VEGF", EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR,
                   primary=False, desc="time-to-treatment triggered by device alert"),
            ]
        ),
    },

    # 6 — BRAINXPERT (LPPR, SA INSUFFISANT)
    # Critique HAS : données non spécifiques. Score cognitif MMSE = surrogate. Pas d'étude RCT spécifique.
    {
        "id": "BRAINXPERT",
        "has_decision": "SA INSUFFISANT",
        "has_critique": "Données non spécifiques (MCT génériques). Score cognitif MMSE = surrogate non validé dans ce contexte. Absence d'étude contrôlée spécifique.",
        "claim": ClinicalClaim(
            text="BRAINXPERT améliore les fonctions cognitives des patients adultes avec maladie d'Alzheimer légère à modérée",
            intervention="BRAINXPERT boisson à base de triglycérides à chaîne moyenne",
            domain="neurology",
            endpoints=[
                ep("score MMSE", EndpointNature.SUBJECTIVE, CausalRole.MEDIATED,
                   primary=True, desc="Mini Mental State Examination — cognitive surrogate score"),
                ep("performance cognitive MCI", EndpointNature.SUBJECTIVE, CausalRole.MEDIATED,
                   primary=False),
            ]
        ),
    },

    # 7 — INCEPTIV (LPPR, FAVORABLE)
    # Critique HAS : critère jugement principal ≠ réduction douleur (non-infériorité sur perte d'efficacité)
    # Étude single-arm avec période test préalable
    {
        "id": "INCEPTIV",
        "has_decision": "FAVORABLE (ASA IV)",
        "has_critique": "Critère de jugement principal = perte d'efficacité sur la douleur (non-infériorité), pas la réduction de douleur elle-même. Étude bras unique. Pas de comparateur actif randomisé.",
        "claim": ClinicalClaim(
            text="INCEPTIV réduit la douleur chronique chez les patients avec douleur neuropathique réfractaire par stimulation médullaire",
            intervention="INCEPTIV stimulateur médullaire",
            domain="pain",
            endpoints=[
                ep("réduction douleur NRS", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="numeric rating scale — patient-reported pain"),
                ep("qualité de vie SF-36", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
            ]
        ),
    },

    # 8 — OPTILUME (LPPR, FAVORABLE)
    # Critique HAS : IPSS = score subjectif (patient-reported). RCT ouvert.
    {
        "id": "OPTILUME",
        "has_decision": "FAVORABLE (ASA IV)",
        "has_critique": "Endpoint IPSS = score subjectif patient. Étude ouverte (absence de sham). Durée suivi 12 mois.",
        "claim": ClinicalClaim(
            text="OPTILUME réduit les symptômes urinaires obstructifs chez les patients avec sténose urétrale récidivante",
            intervention="OPTILUME ballonnet urétral avec paclitaxel",
            domain="urology",
            endpoints=[
                ep("score IPSS", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="International Prostate Symptom Score — patient-reported urinary symptoms"),
                ep("débit urinaire maximal Qmax", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                   primary=False, desc="urinary flow rate — functional surrogate"),
            ]
        ),
    },

    # 9 — NAVITOR (LPPR, FAVORABLE)
    # Critique HAS : données extrapolées depuis COREVALVE. Endpoint mortalité/fuite paravalvulaire.
    # Étude ouverte, fuites paravalvulaires = jugement subjectif en ouvert
    {
        "id": "NAVITOR",
        "has_decision": "FAVORABLE (ASA V par rapport à EVOLUT PRO+)",
        "has_critique": "Données essentiellement issues de COREVALVE (données non spécifiques). Fuites paravalvulaires = endpoint objectif mais adjudication en ouvert. Mortalité toutes causes clean.",
        "claim": ClinicalClaim(
            text="NAVITOR réduit la mortalité et les fuites paravalvulaires chez les patients avec sténose aortique sévère à haut risque",
            intervention="NAVITOR bioprothèse aortique",
            domain="cardiology",
            endpoints=[
                ep("mortalité toutes causes à 30 jours", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="all-cause mortality 30 days"),
                ep("fuites paravalvulaires modérées à sévères", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="paravalvular leak grading — open-label echocardiography assessment"),
                ep("mortalité ou morbidité irréversible à 30 jours", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="composite — open-label adjudication"),
            ]
        ),
    },

    # 10 — URGOSTART (LPPR, FAVORABLE)
    # Critique HAS : taux de cicatrisation = endpoint subjectif/clinicien en ouvert
    {
        "id": "URGOSTART",
        "has_decision": "FAVORABLE (ASR III)",
        "has_critique": "Taux de cicatrisation = endpoint objectif mais évaluation clinicien en ouvert. Population hétérogène (ulcères veineux + diabétiques). Durée suivi variable.",
        "claim": ClinicalClaim(
            text="URGOSTART accélère la cicatrisation des plaies chroniques chez les patients avec ulcères veineux et plaies diabétiques",
            intervention="URGOSTART pansement TLC-NOSF",
            domain="wound_care",
            endpoints=[
                ep("taux de cicatrisation complète", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="complete wound healing rate — clinician assessed, open-label"),
                ep("progression cicatrisation", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
            ]
        ),
    },

    # 11 — FIBROREM (LPPR, SA INSUFFISANT)
    # Critique HAS : FIQ = score patient auto-rapporté. Étude ouverte monocentrique, non comparative.
    {
        "id": "FIBROREM",
        "has_decision": "SA INSUFFISANT",
        "has_critique": "Score FIQ = endpoint subjectif patient sans aveugle. Étude ouverte non comparative. Taille échantillon très faible.",
        "claim": ClinicalClaim(
            text="FIBROREM améliore la qualité de vie et réduit l'impact fonctionnel de la fibromyalgie",
            intervention="FIBROREM dispositif de neurostimulation",
            domain="pain",
            endpoints=[
                ep("score FIQ — Fibromyalgia Impact Questionnaire", EndpointNature.SUBJECTIVE, CausalRole.MEDIATED,
                   primary=True, desc="patient self-reported fibromyalgia impact — open-label single arm"),
                ep("score PGIC — Patient Global Impression of Change", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
            ]
        ),
    },

    # 12 — PRESAGE CARE (PECAN, DÉFAVORABLE)
    # Critique HAS : endpoint hospitalisations = détecté/évité par le dispositif lui-même.
    # Données insuffisantes. PECAN refusé.
    {
        "id": "PRESAGE_CARE",
        "has_decision": "DÉFAVORABLE",
        "has_critique": "Endpoint hospitalisations évitables = directement influencé par le dispositif de surveillance (cercle vicieux). Données insuffisantes. Design non comparatif.",
        "claim": ClinicalClaim(
            text="PRESAGE CARE réduit les hospitalisations en urgence évitables grâce à la télésurveillance prédictive chez les patients insuffisants cardiaques",
            intervention="PRESAGE CARE plateforme télésurveillance prédictive",
            domain="cardiology",
            endpoints=[
                ep("hospitalisations en urgence évitées", EndpointNature.INSTRUMENTED, CausalRole.CIRCULAR,
                   primary=True, desc="device-predicted hospitalization — monitoring-triggered intervention"),
                ep("morbi-mortalité cardiovasculaire", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False),
            ]
        ),
    },

    # 13 — CUREETY TECHCARE 2023 (LATM, FAVORABLE)
    # Critique HAS : qualité de vie = critère secondaire de l'étude Basch. Population danoise (T09).
    {
        "id": "CUREETY_TECHCARE",
        "has_decision": "FAVORABLE",
        "has_critique": "Endpoint principal = survie globale (Basch 2016). Données qualité de vie = critère secondaire. Population danoise (Danemark ≠ France). Étude monocentrique.",
        "claim": ClinicalClaim(
            text="CUREETY TECHCARE améliore la qualité de vie des patients en oncologie sous chimiothérapie via le suivi des symptômes en temps réel",
            intervention="CUREETY TECHCARE application de suivi symptômes oncologie",
            domain="oncology",
            endpoints=[
                ep("qualité de vie QLQ-C30", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="patient-reported quality of life — cancer patients on chemo"),
                ep("survie globale", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=False, desc="overall survival — secondary endpoint Basch 2016"),
            ]
        ),
    },

    # 14 — EVOLUT FX (LPPR, FAVORABLE)
    # Critique HAS : ASA V vs EVOLUT PRO+ seulement. Données COREVALVE non spécifiques.
    # Étude ouverte → ADJUDICATION_RISK sur endpoints non-mortalité
    {
        "id": "EVOLUT_FX",
        "has_decision": "FAVORABLE (ASA V vs EVOLUT PRO+)",
        "has_critique": "Non-infériorité vs EVOLUT PRO+ uniquement. Pas de données vs chirurgie en faible risque. Fuites paravalvulaires adjudication ouverte.",
        "claim": ClinicalClaim(
            text="EVOLUT FX est non inférieur à EVOLUT PRO+ pour la réduction de la mortalité et de la morbidité cardiovasculaire à 30 jours",
            intervention="EVOLUT FX bioprothèse aortique auto-expansible",
            domain="cardiology",
            endpoints=[
                ep("mortalité toutes causes à 30 jours", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="all-cause mortality 30-day — adjudicated"),
                ep("fuites paravalvulaires modérées à sévères", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="paravalvular regurgitation — open-label echocardiographic assessment"),
                ep("complications procédurales majeures", EndpointNature.OBJECTIVE, CausalRole.INDEPENDENT,
                   primary=True, desc="major procedural complications — open-label adjudication"),
            ]
        ),
    },

    # 15 — FREESTYLE LIBRE SELECT (LPPR, FAVORABLE)
    # Critique HAS : ASA V. Données limitées propres à ce nouveau modèle.
    {
        "id": "FREESTYLE_LIBRE_SELECT",
        "has_decision": "FAVORABLE (ASA V)",
        "has_critique": "ASA V (pas d'amélioration vs FL2 Plus). Données propres limitées pour ce nouveau modèle. HbA1c comme endpoint glycémique validé.",
        "claim": ClinicalClaim(
            text="FreeStyle Libre Select améliore l'autosurveillance glycémique en complément de la glycémie capillaire chez les patients diabétiques",
            intervention="FreeStyle Libre Select capteur glucose interstitiel",
            domain="endocrinology",
            endpoints=[
                ep("HbA1c", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                   primary=True, desc="glycated hemoglobin — validated glycemic surrogate",
                   validated_surrogate=True),
                ep("temps dans la cible TIR", EndpointNature.OBJECTIVE, CausalRole.MEDIATED,
                   primary=False),
            ]
        ),
    },
]


# ---------------------------------------------------------------------------
# Run pipeline + print comparison
# ---------------------------------------------------------------------------

def run():
    print("=" * 80)
    print("COMPARAISON RWE-v5 vs CRITIQUES CNEDiMTS — 15 AVIS")
    print("=" * 80)

    summary_rows = []

    for case in CASES:
        cid = case["id"]
        output = analyze(case["claim"])

        flags = [bd.flag.value for bd in output.bias_flags]
        structure = output.causal_structure.value
        design = output.design_recommendation.primary_design.value

        print(f"\n{'─' * 70}")
        print(f"  {cid}")
        print(f"  HAS : {case['has_decision']}")
        print(f"{'─' * 70}")
        print(f"  Structure causale  : {structure}")
        print(f"  Design recommandé  : {design}")

        if flags:
            print(f"  BiasFlags détectés :")
            for bd in output.bias_flags:
                print(f"    [{bd.severity}] {bd.flag.value}")
        else:
            print(f"  BiasFlags détectés : aucun")

        print(f"  Critique HAS réelle :")
        for line in case["has_critique"].split("."):
            line = line.strip()
            if line:
                print(f"    · {line}")

        # Alignment check
        algo_issues = set(flags)
        has_text = case["has_critique"].lower()

        matches = []
        misses = []
        if "SURROGATE_RISK" in algo_issues and ("surrogate" in has_text or "critère fonctionnel" in has_text or "critère de jugement" in has_text):
            matches.append("SURROGATE_RISK ✓")
        if "ADJUDICATION_RISK" in algo_issues and ("ouvert" in has_text or "adjudication" in has_text or "biais" in has_text):
            matches.append("ADJUDICATION_RISK ✓")
        if "CIRCULARITY_RISK" in algo_issues and ("dispositif" in has_text or "tautol" in has_text or "cercle" in has_text or "détect" in has_text):
            matches.append("CIRCULARITY_RISK ✓")
        if "DETECTION_BIAS" in algo_issues and ("détect" in has_text or "alerte" in has_text or "surveillance" in has_text):
            matches.append("DETECTION_BIAS ✓")
        if "PERCEPTION_BIAS" in algo_issues and ("subjectif" in has_text or "patient" in has_text or "aveugle" in has_text or "ouvert" in has_text):
            matches.append("PERCEPTION_BIAS ✓")

        if matches:
            print(f"  Alignement algo/HAS : {' | '.join(matches)}")
        else:
            print(f"  Alignement algo/HAS : —")

        summary_rows.append({
            "id": cid,
            "decision": case["has_decision"][:20],
            "flags": ", ".join(flags) if flags else "—",
            "structure": structure,
            "design": design,
        })

    # Summary table
    print(f"\n\n{'=' * 80}")
    print("TABLEAU RÉCAPITULATIF")
    print(f"{'=' * 80}")
    print(f"{'Dispositif':<25} {'Décision HAS':<22} {'Structure':<12} {'BiasFlags'}")
    print(f"{'─' * 25} {'─' * 22} {'─' * 12} {'─' * 40}")
    for r in summary_rows:
        print(f"{r['id']:<25} {r['decision']:<22} {r['structure']:<12} {r['flags']}")


if __name__ == "__main__":
    run()
