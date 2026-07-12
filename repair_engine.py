"""Repair engine V2 — clinically precise, HAS-style, 5-step pipeline.

Transforms invalid study designs into valid ones via:
  Step 1: Failure archetype diagnosis
  Step 2: Per-endpoint repair generation (3+ alternatives each)
  Step 3: Causal chain reconstruction
  Step 4: Study design repair
  Step 5: Endpoint ranking (GOLD / ACCEPTABLE / REJECTED)
"""

from __future__ import annotations

from models import (
    BiasDetection,
    BiasFlag,
    CausalChainStep,
    CausalRole,
    CausalStructure,
    ClaimLevel,
    ClinicalClaim,
    DesignJustification,
    DesignRecommendation,
    EndpointAnalysis,
    EndpointNature,
    EndpointRank,
    EndpointRepairBlock,
    EndpointRepairCandidate,
    EndpointRepairKind,
    FailureArchetype,
    FailureDiagnosis,
    RankedEndpoint,
    RepairPlan,
    RepairPlanV2,
    RepairStrategy,
    RepairType,
    StudyDesign,
)


# ===================================================================
# DOMAIN-SPECIFIC REPAIR KNOWLEDGE BASE
# ===================================================================

DETECTION_REPAIRS: dict[str, list[dict]] = {
    "time-to-detection": [
        {
            "endpoint": "taux de complications adjugé indépendamment à 12 mois (CEC)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "La survenue de complications est évaluée par un comité d'adjudication "
                         "indépendant du dispositif. La mesure est ainsi découplée de l'intervention.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "taux d'escalade thérapeutique vérifié par revue indépendante du dossier médical",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Les décisions thérapeutiques sont documentées dans le dossier médical "
                         "indépendamment du dispositif. Capture l'impact clinique en aval sans "
                         "données générées par le dispositif.",
            "risk_reduction": ["supprime la circularité"],
        },
        {
            "endpoint": "hospitalisations non programmées issues de la base hospitalière administrative "
                        "(non déclenchées par alerte du dispositif)",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Les hospitalisations sont enregistrées dans les bases administratives "
                         "indépendamment du dispositif. L'ascertainment de l'outcome est "
                         "entièrement découplé du mécanisme d'intervention.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
    ],
    "alert": [
        {
            "endpoint": "taux d'hospitalisation non programmée depuis les données d'assurance maladie (PMSI/SNDS)",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Les données d'hospitalisation issues des remboursements sont collectées "
                         "indépendamment du dispositif d'alerte. Aucune influence du dispositif sur l'ascertainment.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "taux d'événements cliniques confirmés, adjugés par un comité d'endpoint en aveugle",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Le comité d'adjudication indépendant évalue les événements sans connaissance "
                         "de l'assignation au bras dispositif. Élimine l'influence du dispositif sur l'outcome.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "mortalité toutes causes à 30 jours depuis le registre d'état civil",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "La mortalité est ascertée depuis les données d'état civil, "
                         "entièrement indépendante du fonctionnement du dispositif ou de la génération d'alertes.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
    ],
    "monitoring": [
        {
            "endpoint": "mortalité toutes causes à 12 mois depuis le registre d'état civil",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "La mortalité est le critère clinique le plus robuste. L'ascertainment "
                         "via le registre d'état civil est entièrement indépendant du dispositif de monitoring.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "passages aux urgences non programmés issus des données administratives hospitalières",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "Les passages aux urgences sont enregistrés dans les systèmes d'information "
                         "hospitaliers indépendamment du dispositif de monitoring. Capture les événements cliniques en aval.",
            "risk_reduction": ["supprime la circularité"],
        },
        {
            "endpoint": "progression de la maladie confirmée par revue d'imagerie indépendante "
                        "(lecture centrale en aveugle)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "La revue centralisée par des radiologues en aveugle du bras de traitement "
                         "garantit que l'évaluation de la progression est indépendante du dispositif de monitoring.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
    ],
    "detection": [
        {
            "endpoint": "taux de diagnostic confirmé par revue anatomopathologique ou d'imagerie indépendante",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "La confirmation diagnostique par un anatomopathologiste ou radiologue "
                         "n'utilisant pas le dispositif élimine la boucle détection-ascertainment.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "délai jusqu'à l'initiation du traitement documenté dans le dossier prescripteur",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "L'initiation thérapeutique est une décision clinique documentée dans "
                         "le dossier prescripteur. Dépendance partielle au dispositif si l'alerte déclenche "
                         "l'action, mais la décision reste clinicien-dépendante.",
            "risk_reduction": ["supprime la circularité"],
        },
        {
            "endpoint": "taux de complications cliniques à 6 mois (adjugé indépendamment)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Les complications sont des événements cliniques évalués indépendamment "
                         "du mécanisme de détection. L'outcome en aval valide que la détection précoce "
                         "se traduit par un bénéfice clinique.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
    ],
    "time-to-treatment": [
        {
            "endpoint": "mortalité toutes causes à 90 jours depuis les données de sortie hospitalière",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "La mortalité est ascertée depuis les données de sortie/décès "
                         "indépendamment du système de triage. Valide que la rapidité du triage "
                         "se traduit en bénéfice de survie.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "état fonctionnel à 90 jours (modified Rankin Scale, évaluateur en aveugle)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "La mRS est évaluée par un neurologue en aveugle du bras de traitement. "
                         "Critère standard AVC indépendant du mécanisme de triage.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "durée de séjour en réanimation depuis les données administratives hospitalières",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "La durée en réanimation est documentée dans les systèmes d'information "
                         "hospitaliers indépendamment du résultat du triage IA. Capture l'utilisation "
                         "des ressources en aval des décisions cliniques.",
            "risk_reduction": ["supprime la circularité"],
        },
    ],
    "screening": [
        {
            "endpoint": "stade au diagnostic depuis les données du registre du cancer",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Le stade du cancer issu des données de registre est déterminé par "
                         "l'anatomopathologie et l'imagerie, indépendamment de la méthode de dépistage.",
            "risk_reduction": ["supprime le biais de détection"],
        },
        {
            "endpoint": "mortalité spécifique à 5 ans depuis le registre d'état civil",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "Mortalité cause-spécifique depuis les données de registre. "
                         "Indépendante du mécanisme de dépistage.",
            "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
        },
        {
            "endpoint": "taux de cancers d'intervalle (diagnostiqués entre deux tours de dépistage)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Les cancers d'intervalle sont diagnostiqués via les filières cliniques "
                         "habituelles, sans passer par le dispositif de dépistage.",
            "risk_reduction": ["supprime le biais de détection"],
        },
    ],
}

# Gait/mobility-assistance devices (orthoses, exosquelettes...) whose circular
# endpoints are the device's own biomechanical output (joint kinematics/kinetics
# it was mechanically adjusted to produce) — the generic fallback below (mortality,
# adjudicated clinical events) is a poor fit for this population, which is not
# typically at elevated near-term mortality risk from the condition itself.
_GAIT_MOBILITY_REPAIRS: list[dict] = [
    {
        "endpoint": "taux de chutes documentées (carnet de suivi + confirmation médicale) sur 12 mois",
        "type": EndpointRepairKind.HARD_CLINICAL,
        "causal_role": "PRIMARY",
        "why_valid": "La chute est un événement clinique patient-pertinent, ascerté indépendamment "
                     "des paramètres biomécaniques propres au réglage du dispositif — directement lié "
                     "au risque fonctionnel que la compensation du déficit de marche vise à réduire.",
        "risk_reduction": ["supprime la circularité"],
    },
    {
        "endpoint": "passages aux urgences ou hospitalisations liés à une chute depuis les données "
                    "administratives (PMSI/SNDS)",
        "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
        "causal_role": "PRIMARY",
        "why_valid": "Les recours aux soins pour chute sont enregistrés dans les bases administratives "
                     "hospitalières, indépendamment du réglage du dispositif.",
        "risk_reduction": ["supprime la circularité", "supprime le biais de détection"],
    },
    {
        "endpoint": "échelle de mobilité fonctionnelle validée (ex : Functional Ambulation Category, "
                    "Timed Up and Go) par évaluateur indépendant en aveugle du réglage",
        "type": EndpointRepairKind.SOFT_CLINICAL,
        "causal_role": "SECONDARY",
        "why_valid": "Score fonctionnel standardisé évalué par un tiers indépendant du réglage de "
                     "l'articulation, plutôt qu'un paramètre biomécanique intrinsèque au dispositif.",
        "risk_reduction": ["supprime la circularité"],
    },
]
DETECTION_REPAIRS["marche"] = _GAIT_MOBILITY_REPAIRS
DETECTION_REPAIRS["cinématique"] = _GAIT_MOBILITY_REPAIRS
DETECTION_REPAIRS["biomécanique"] = _GAIT_MOBILITY_REPAIRS

SUBJECTIVE_REPAIRS: dict[str, list[dict]] = {
    "pain": [
        {
            "endpoint": "consommation totale d'analgésiques en mg-équivalent morphine/jour sur 12 semaines",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "PRIMARY",
            "why_valid": "La consommation médicamenteuse est objectivement enregistrée dans les données "
                         "de dispensation officinale. La réduction des analgésiques est un proxy objectif "
                         "de la diminution de la douleur, non soumis à l'effet placebo.",
            "risk_reduction": ["supprime le biais de perception", "ancrage objectif"],
        },
        {
            "endpoint": "distance au test de marche de 6 minutes (en mètres) à 3 et 6 mois",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Test fonctionnel standardisé mesuré par un évaluateur en aveugle. "
                         "La performance physique est moins sensible à l'effet placebo "
                         "que les échelles de douleur auto-rapportées.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "taux de retour au travail à 6 mois depuis les données employeur/assurance",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "Le statut professionnel est objectivement vérifiable dans les données employeur "
                         "ou d'assurance. Capture l'impact fonctionnel de la réduction de la douleur dans la vie quotidienne.",
            "risk_reduction": ["supprime le biais de perception", "ancrage objectif"],
        },
        {
            "endpoint": "efficacité du sommeil nocturne par actimétrie au poignet sur 4 semaines (%)",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "SECONDARY",
            "why_valid": "L'actimétrie fournit une mesure objective et continue du sommeil. "
                         "L'amélioration des troubles du sommeil liés à la douleur est un corrélat objectif "
                         "de l'effet analgésique.",
            "risk_reduction": ["supprime le biais de perception"],
        },
    ],
    "quality of life": [
        {
            "endpoint": "taux d'hospitalisation toutes causes à 12 mois depuis les données d'assurance maladie",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Les hospitalisations issues des données administratives sont objectives et non "
                         "influencées par la perception du patient. Les événements de qualité de vie "
                         "nécessitant une hospitalisation ont une signification clinique certaine.",
            "risk_reduction": ["supprime le biais de perception", "ancrage objectif"],
        },
        {
            "endpoint": "score FIM (Functional Independence Measure) évalué par un évaluateur en aveugle",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "La FIM est évaluée par un évaluateur formé et en aveugle. Elle couvre les domaines "
                         "moteurs et cognitifs avec un score standardisé moins sensible au biais d'attente du patient.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "nombre de jours vivants et hors hôpital à 12 mois",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Critère composite issu des données administratives capturant à la fois "
                         "la survie et l'absence d'hospitalisation. Entièrement objectif.",
            "risk_reduction": ["supprime le biais de perception", "ancrage objectif"],
        },
    ],
    "qol": [
        {
            "endpoint": "taux d'hospitalisation toutes causes à 12 mois depuis les données d'assurance maladie",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Critère administratif non influencé par la perception du patient.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "jours vivants et hors hôpital à 12 mois",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Critère composite objectif issu des données administratives.",
            "risk_reduction": ["supprime le biais de perception", "ancrage objectif"],
        },
        {
            "endpoint": "score FIM (Functional Independence Measure) par évaluateur en aveugle",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Mesure fonctionnelle standardisée évaluée par un observateur.",
            "risk_reduction": ["supprime le biais de perception"],
        },
    ],
    "satisfaction": [
        {
            "endpoint": "taux d'adhérence au traitement depuis les données de dispensation officinale",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "SECONDARY",
            "why_valid": "L'adhérence mesurée par les données de pharmacie est objective. "
                         "La poursuite du traitement est un proxy de préférence révélée pour la satisfaction.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "taux d'arrêt de traitement à 6 mois",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "L'arrêt de traitement est un événement binaire objectif. "
                         "Les patients réellement insatisfaits cessent le traitement.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "recours aux soins dans les 12 mois post-intervention depuis les données d'assurance maladie",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "Données administratives capturant le recours à des soins supplémentaires. "
                         "Proxy objectif des besoins non couverts.",
            "risk_reduction": ["supprime le biais de perception"],
        },
    ],
    "fatigue": [
        {
            "endpoint": "nombre de pas quotidiens par accéléromètre validé sur 4 semaines",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "SECONDARY",
            "why_valid": "L'actimétrie fournit une mesure objective et continue de l'activité physique. "
                         "Moins sensible au biais de déclaration que les questionnaires de fatigue.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "VO2max au test d'effort cardio-pulmonaire à l'inclusion et à 3 mois",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "La VO2max est une mesure physiologique objective de la capacité d'effort. "
                         "Évaluation standardisée par un technicien en aveugle.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "jours d'arrêt de travail sur 6 mois depuis les données employeur",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "L'arrêt de travail est objectivement documenté. "
                         "Capture l'impact fonctionnel de la fatigue dans la vie quotidienne.",
            "risk_reduction": ["supprime le biais de perception", "ancrage objectif"],
        },
    ],
    "symptom score": [
        {
            "endpoint": "taux d'hospitalisation non programmée depuis les données administratives",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Hospitalisation issue des données administratives. La dégradation "
                         "symptomatique conduisant à une hospitalisation est un événement clinique objectif en aval.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "taux de modification thérapeutique depuis les dossiers prescripteurs",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Les modifications de traitement documentées par les prescripteurs reflètent "
                         "des changements symptomatiques cliniquement significatifs, non la perception seule du patient.",
            "risk_reduction": ["supprime le biais de perception"],
        },
        {
            "endpoint": "taux de passages aux urgences depuis le système d'information hospitalier",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "Les passages aux urgences sont des événements objectifs enregistrés dans les "
                         "systèmes hospitaliers. Les crises symptomatiques menant aux urgences ont une signification clinique.",
            "risk_reduction": ["supprime le biais de perception"],
        },
    ],
}

MEDIATION_INTERMEDIATES: dict[str, list[dict]] = {
    "neurostimulat": [
        {
            "endpoint": "taux sérique de bêta-endorphines à 2h et 4h post-stimulation (ELISA)",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "MEDIATOR",
            "why_valid": "Mesure biochimique directe du mécanisme revendiqué. Si la neurostimulation "
                         "revendique une libération d'endorphines, les taux d'endorphines doivent être "
                         "mesurés pour valider la chaîne causale.",
            "risk_reduction": ["comble le gap de médiation"],
        },
        {
            "endpoint": "test sensoriel quantitatif (seuil de douleur thermique) par évaluateur en aveugle",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "MEDIATOR",
            "why_valid": "Mesure psychophysique objective du traitement de la douleur. Relie le mécanisme "
                         "(libération d'endorphines) à l'outcome (réduction de la douleur) par une "
                         "mesure indépendante et non subjective.",
            "risk_reduction": ["comble le gap de médiation", "ancrage objectif"],
        },
    ],
    "stimulat": [
        {
            "endpoint": "variation du biomarqueur cible depuis la baseline (dosage spécifique à l'indication)",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "MEDIATOR",
            "why_valid": "Mesure biologique directe de l'effet de stimulation revendiqué.",
            "risk_reduction": ["comble le gap de médiation"],
        },
    ],
    "modulat": [
        {
            "endpoint": "biomarqueur d'activation de la voie cible (sérum ou tissu)",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "MEDIATOR",
            "why_valid": "Le marqueur biologique de la modulation de voie valide le mécanisme causal "
                         "avant la mesure de l'outcome.",
            "risk_reduction": ["comble le gap de médiation"],
        },
    ],
    "monitoring": [
        {
            "endpoint": "délai entre le début des symptômes et la modification thérapeutique initiée par le clinicien",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "MEDIATOR",
            "why_valid": "La modification thérapeutique est l'acte clinique qui médiatise le lien entre "
                         "le monitoring (processus) et la survie (outcome). La décision clinicienne "
                         "est le maillon critique de la chaîne causale.",
            "risk_reduction": ["comble le gap de médiation"],
        },
    ],
    "triage": [
        {
            "endpoint": "délai porte-à-aiguille documenté dans les données du service des urgences",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "MEDIATOR",
            "why_valid": "Le délai de processus issu des données des urgences (non du système IA) "
                         "relie la priorisation au triage à l'outcome clinique.",
            "risk_reduction": ["comble le gap de médiation"],
        },
    ],
}


# ===================================================================
# STEP 1 — Failure archetype diagnosis
# ===================================================================

def _diagnose_failure(
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
) -> FailureDiagnosis:
    """Classify into primary failure archetype with severity.

    Primary-endpoint-aware: circularity/detection on secondary endpoints only
    does not block the entire design.
    """

    primary_eps = [ea for ea in endpoint_analyses if ea.endpoint.is_primary]
    primary_circular = any(ea.causal_role == CausalRole.CIRCULAR for ea in primary_eps)
    primary_detection = any(BiasFlag.DETECTION_BIAS in ea.flags for ea in primary_eps)

    has_circular = any(ea.causal_role == CausalRole.CIRCULAR for ea in endpoint_analyses)
    has_detection = BiasFlag.DETECTION_BIAS in bias_flags
    has_perception = BiasFlag.PERCEPTION_BIAS in bias_flags
    has_mediation = BiasFlag.MEDIATION_GAP in bias_flags
    has_tautology = BiasFlag.PROCESS_TAUTOLOGY in bias_flags

    if primary_circular and primary_detection:
        return FailureDiagnosis(
            failure_type=FailureArchetype.DETECTION_LOOP,
            severity=0.9,
            is_rct_valid="false",
        )
    if primary_circular:
        return FailureDiagnosis(
            failure_type=FailureArchetype.MEASUREMENT_CIRCULARITY,
            severity=0.85,
            is_rct_valid="false",
        )

    if has_circular and has_detection:
        return FailureDiagnosis(
            failure_type=FailureArchetype.DETECTION_LOOP,
            severity=0.9,
            is_rct_valid="false",
        )
    if has_circular:
        return FailureDiagnosis(
            failure_type=FailureArchetype.MEASUREMENT_CIRCULARITY,
            severity=0.85,
            is_rct_valid="false",
        )
    if has_tautology:
        return FailureDiagnosis(
            failure_type=FailureArchetype.PROCESS_TAUTOLOGY,
            severity=0.8,
            is_rct_valid="false",
        )
    if has_perception:
        return FailureDiagnosis(
            failure_type=FailureArchetype.SUBJECTIVE_ENDPOINT,
            severity=0.6,
            is_rct_valid="conditional",
        )

    if has_detection and not primary_detection:
        return FailureDiagnosis(
            failure_type=FailureArchetype.MEDIATION_GAP,
            severity=0.4,
            is_rct_valid="conditional",
        )

    if has_mediation:
        return FailureDiagnosis(
            failure_type=FailureArchetype.MEDIATION_GAP,
            severity=0.5,
            is_rct_valid="conditional",
        )

    if structure == CausalStructure.CIRCULAR:
        return FailureDiagnosis(
            failure_type=FailureArchetype.MEASUREMENT_CIRCULARITY,
            severity=0.85,
            is_rct_valid="false",
        )

    return FailureDiagnosis(
        failure_type=FailureArchetype.MEDIATION_GAP,
        severity=0.3,
        is_rct_valid="conditional",
    )


# ===================================================================
# STEP 2 — Per-endpoint repair generation
# ===================================================================

def _generate_endpoint_repairs(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    bias_flags: list[BiasFlag],
    failure: FailureDiagnosis,
) -> list[EndpointRepairBlock]:
    """Generate precise repair candidates for each failed endpoint."""
    blocks = []

    for ea in endpoint_analyses:
        ep_name_lower = ea.endpoint.name.lower()
        ep_desc_lower = ea.endpoint.description.lower() if ea.endpoint.description else ""
        combined = f"{ep_name_lower} {ep_desc_lower}"

        repairs: list[EndpointRepairCandidate] = []
        failure_reason = ""

        if ea.causal_role == CausalRole.CIRCULAR or BiasFlag.DETECTION_BIAS in ea.flags:
            failure_reason = _build_precise_failure_reason_detection(ea, claim)
            repairs.extend(_lookup_detection_repairs(combined))

        if ea.nature == EndpointNature.SUBJECTIVE:
            if not failure_reason:
                failure_reason = _build_precise_failure_reason_subjective(ea)
            repairs.extend(_lookup_subjective_repairs(combined))

        if BiasFlag.MEDIATION_GAP in bias_flags and not repairs:
            failure_reason = _build_precise_failure_reason_mediation(ea, claim)
            repairs.extend(_lookup_mediation_repairs(claim))

        if not repairs:
            continue

        seen = set()
        deduped = []
        for r in repairs:
            if r.endpoint not in seen:
                seen.add(r.endpoint)
                deduped.append(r)

        blocks.append(EndpointRepairBlock(
            original_endpoint=ea.endpoint.name,
            failure_reason=failure_reason,
            repairs=deduped[:5],
        ))

    if BiasFlag.MEDIATION_GAP in bias_flags and not blocks:
        mediator_repairs = _lookup_mediation_repairs(claim)
        if mediator_repairs:
            blocks.append(EndpointRepairBlock(
                original_endpoint="[missing mediator endpoint]",
                failure_reason=(
                    f"Claim at {claim.level.value} level asserts a causal chain "
                    f"({claim.intervention} → outcome) but no intermediate process "
                    f"endpoint validates the mediation step. The causal link between "
                    f"mechanism and outcome is assumed, not measured."
                ),
                repairs=mediator_repairs,
            ))

    return blocks


def _build_precise_failure_reason_detection(
    ea: EndpointAnalysis, claim: ClinicalClaim,
) -> str:
    return (
        f"'{ea.endpoint.name}' is structurally circular: {claim.intervention} "
        f"generates or influences the measurement used as endpoint. The device "
        f"cannot be both the intervention and the measurement instrument — "
        f"outcome ascertainment is not independent of treatment arm assignment. "
        f"Any difference observed may reflect device sensitivity, not clinical benefit."
    )


def _build_precise_failure_reason_subjective(ea: EndpointAnalysis) -> str:
    return (
        f"'{ea.endpoint.name}' is a patient-reported subjective measure. Without "
        f"blinding (sham control), any observed effect cannot be distinguished from "
        f"placebo response, expectation bias, or Hawthorne effect. HAS/CNEDiMTS "
        f"methodology requires either objective anchoring or sham-controlled design "
        f"when subjective endpoints are primary."
    )


def _build_precise_failure_reason_mediation(
    ea: EndpointAnalysis, claim: ClinicalClaim,
) -> str:
    return (
        f"'{ea.endpoint.name}' measures a clinical outcome, but the claim is at "
        f"{claim.level.value} level. The causal chain from {claim.intervention} "
        f"to this outcome requires intermediate steps (mechanism → process → outcome) "
        f"that are not measured. Mediation is assumed but not validated."
    )


def _lookup_detection_repairs(text: str) -> list[EndpointRepairCandidate]:
    """Look up detection/circularity repairs from knowledge base."""
    candidates = []
    for keyword, entries in DETECTION_REPAIRS.items():
        if keyword in text:
            for entry in entries:
                candidates.append(EndpointRepairCandidate(
                    endpoint=entry["endpoint"],
                    type=entry["type"],
                    causal_role=entry["causal_role"],
                    why_valid=entry["why_valid"],
                    risk_reduction=entry["risk_reduction"],
                ))
    if not candidates:
        candidates.append(EndpointRepairCandidate(
            endpoint="independently adjudicated clinical event rate at 12 months",
            type=EndpointRepairKind.HARD_CLINICAL,
            causal_role="PRIMARY",
            why_valid="Clinical events adjudicated by independent committee blinded "
                      "to treatment arm. Decouples outcome from device mechanism.",
            risk_reduction=["removes circularity", "removes detection bias"],
        ))
        candidates.append(EndpointRepairCandidate(
            endpoint="all-cause mortality from civil registry",
            type=EndpointRepairKind.SURVIVAL,
            causal_role="PRIMARY",
            why_valid="Hardest clinical endpoint, ascertained from official records "
                      "independent of any device.",
            risk_reduction=["removes circularity", "removes detection bias"],
        ))
        candidates.append(EndpointRepairCandidate(
            endpoint="unplanned hospitalization rate from administrative database",
            type=EndpointRepairKind.UTILIZATION_INDEPENDENT,
            causal_role="SECONDARY",
            why_valid="Hospital admissions from administrative data are independent "
                      "of the device.",
            risk_reduction=["removes circularity"],
        ))
    return candidates


def _lookup_subjective_repairs(text: str) -> list[EndpointRepairCandidate]:
    """Look up subjective endpoint repairs from knowledge base."""
    candidates = []
    for keyword, entries in SUBJECTIVE_REPAIRS.items():
        if keyword in text:
            for entry in entries:
                candidates.append(EndpointRepairCandidate(
                    endpoint=entry["endpoint"],
                    type=entry["type"],
                    causal_role=entry["causal_role"],
                    why_valid=entry["why_valid"],
                    risk_reduction=entry["risk_reduction"],
                ))
    if not candidates:
        candidates.append(EndpointRepairCandidate(
            endpoint="all-cause hospitalization rate from insurance claims at 12 months",
            type=EndpointRepairKind.UTILIZATION_INDEPENDENT,
            causal_role="PRIMARY",
            why_valid="Objective administrative outcome not influenced by patient "
                      "perception. Captures clinically significant health events.",
            risk_reduction=["removes perception bias"],
        ))
        candidates.append(EndpointRepairCandidate(
            endpoint="healthcare resource utilization from administrative records",
            type=EndpointRepairKind.UTILIZATION_INDEPENDENT,
            causal_role="SECONDARY",
            why_valid="Administrative data capturing care consumption. Objective proxy.",
            risk_reduction=["removes perception bias"],
        ))
        candidates.append(EndpointRepairCandidate(
            endpoint="treatment discontinuation rate at 6 months",
            type=EndpointRepairKind.SOFT_CLINICAL,
            causal_role="SECONDARY",
            why_valid="Binary objective event. Patients discontinuing is a "
                      "revealed-preference indicator.",
            risk_reduction=["removes perception bias"],
        ))
    return candidates


def _lookup_mediation_repairs(claim: ClinicalClaim) -> list[EndpointRepairCandidate]:
    """Look up mediation gap repairs from knowledge base."""
    candidates = []
    combined = f"{claim.text} {claim.intervention}".lower()

    for keyword, entries in MEDIATION_INTERMEDIATES.items():
        if keyword in combined:
            for entry in entries:
                candidates.append(EndpointRepairCandidate(
                    endpoint=entry["endpoint"],
                    type=entry["type"],
                    causal_role=entry["causal_role"],
                    why_valid=entry["why_valid"],
                    risk_reduction=entry["risk_reduction"],
                ))

    if not candidates:
        candidates.append(EndpointRepairCandidate(
            endpoint="process endpoint measuring intermediate clinical action "
                     "(treatment change, referral, dose adjustment)",
            type=EndpointRepairKind.SOFT_CLINICAL,
            causal_role="MEDIATOR",
            why_valid="Intermediate endpoint that bridges mechanism to outcome. "
                      "Must be measured to validate the assumed causal chain.",
            risk_reduction=["fills mediation gap"],
        ))

    return candidates


# ===================================================================
# STEP 3 — Causal chain reconstruction
# ===================================================================

def _reconstruct_causal_chain(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    endpoint_repairs: list[EndpointRepairBlock],
    bias_flags: list[BiasFlag],
    structure: CausalStructure,
) -> list[CausalChainStep]:
    """Rebuild the corrected causal chain."""
    chain = []

    chain.append(CausalChainStep(
        node=claim.intervention,
        role="INTERVENTION",
        measurable=True,
        requires_mediation_assumption=False,
        rct_valid_at_step=(structure != CausalStructure.CIRCULAR),
    ))

    has_mediation_gap = BiasFlag.MEDIATION_GAP in bias_flags
    has_circularity = structure == CausalStructure.CIRCULAR or BiasFlag.CIRCULARITY_RISK in bias_flags

    if has_mediation_gap or claim.level == ClaimLevel.D:
        mediator_name = _extract_mediator_from_repairs(endpoint_repairs, claim)
        chain.append(CausalChainStep(
            node=mediator_name,
            role="MEDIATOR",
            measurable=has_mediation_gap is False,
            requires_mediation_assumption=has_mediation_gap,
            rct_valid_at_step=not has_circularity,
        ))

    repaired_primary = _extract_primary_from_repairs(endpoint_repairs, endpoint_analyses)
    chain.append(CausalChainStep(
        node=repaired_primary,
        role="OUTCOME",
        measurable=True,
        requires_mediation_assumption=False,
        rct_valid_at_step=not has_circularity,
    ))

    return chain


def _extract_mediator_from_repairs(
    repairs: list[EndpointRepairBlock], claim: ClinicalClaim,
) -> str:
    for block in repairs:
        for r in block.repairs:
            if r.causal_role == "MEDIATOR":
                return r.endpoint
    combined = f"{claim.text} {claim.intervention}".lower()
    if "neurostimulat" in combined:
        return "endorphin release (serum beta-endorphin level)"
    if "monitoring" in combined or "alert" in combined:
        return "clinician-initiated treatment modification"
    if "triage" in combined:
        return "door-to-needle time (from ED records)"
    return "[unmeasured mediator — must be specified]"


def _extract_primary_from_repairs(
    repairs: list[EndpointRepairBlock],
    endpoint_analyses: list[EndpointAnalysis],
) -> str:
    for block in repairs:
        for r in block.repairs:
            if r.causal_role == "PRIMARY":
                return f"{r.endpoint} [REPAIRED]"

    for ea in endpoint_analyses:
        if ea.endpoint.is_primary and ea.causal_role != CausalRole.CIRCULAR:
            return ea.endpoint.name

    return "[primary endpoint to be determined after repair]"


# ===================================================================
# STEP 4 — Study design repair
# ===================================================================

def _repair_study_designs(
    claim: ClinicalClaim,
    bias_flags: list[BiasFlag],
    failure: FailureDiagnosis,
    has_subjective_only: bool,
) -> list[DesignJustification]:
    """Return only designs valid under repaired endpoints."""
    designs = []

    has_circularity = failure.failure_type in (
        FailureArchetype.DETECTION_LOOP,
        FailureArchetype.MEASUREMENT_CIRCULARITY,
    )

    if has_subjective_only:
        designs.append(DesignJustification(
            design=StudyDesign.SHAM_RCT,
            why_valid="Sham control enables blinding for subjective endpoints. "
                      "After adding objective co-primary endpoints, the sham arm "
                      "controls perception bias on remaining patient-reported outcomes.",
            failures_prevented=["perception bias", "expectation bias"],
        ))

    if not has_circularity:
        designs.append(DesignJustification(
            design=StudyDesign.RCT,
            why_valid="After endpoint repair (replacing circular/detection-biased endpoints "
                      "with independently ascertained outcomes), randomized controlled trial "
                      "is valid. Treatment arm assignment does not influence outcome measurement.",
            failures_prevented=["confounding", "selection bias"],
        ))

    if has_circularity:
        designs.append(DesignJustification(
            design=StudyDesign.PRAGMATIC_RCT,
            why_valid="After replacing device-generated endpoints with administrative or "
                      "independently adjudicated outcomes, a pragmatic RCT using routine "
                      "care data for outcome ascertainment eliminates circularity.",
            failures_prevented=["circularity", "detection bias"],
        ))

    if claim.level in (ClaimLevel.B, ClaimLevel.C):
        designs.append(DesignJustification(
            design=StudyDesign.COHORT,
            why_valid="Prospective cohort with independent endpoint ascertainment. "
                      "Valid when randomization is not feasible, provided confounders "
                      "are measured and adjusted.",
            failures_prevented=["detection bias"],
        ))

    if claim.level == ClaimLevel.B and not has_circularity:
        designs.append(DesignJustification(
            design=StudyDesign.ITS,
            why_valid="Interrupted time series is valid when the endpoint is independent "
                      "of the intervention mechanism and measured at population level "
                      "from administrative data.",
            failures_prevented=["confounding (temporal)"],
        ))

    if not designs:
        designs.append(DesignJustification(
            design=StudyDesign.PRAGMATIC_RCT,
            why_valid="After endpoint repair, pragmatic RCT with administrative outcome "
                      "ascertainment is the minimal valid design.",
            failures_prevented=["circularity", "detection bias"],
        ))

    return designs


# ===================================================================
# STEP 5 — Endpoint ranking
# ===================================================================

def _rank_endpoints(
    endpoint_analyses: list[EndpointAnalysis],
    endpoint_repairs: list[EndpointRepairBlock],
    bias_flags: list[BiasFlag],
) -> list[RankedEndpoint]:
    """Rank all endpoints (original + repaired) as GOLD / ACCEPTABLE / REJECTED."""
    ranked = []

    for ea in endpoint_analyses:
        if ea.causal_role == CausalRole.CIRCULAR:
            ranked.append(RankedEndpoint(
                endpoint=ea.endpoint.name,
                rank=EndpointRank.REJECTED,
                reason=(
                    f"Structurally circular — {ea.endpoint.name} is generated or "
                    f"influenced by the device. Cannot serve as primary or secondary "
                    f"endpoint in a comparative study."
                ),
                bias_score=0.95,
            ))
        elif ea.nature == EndpointNature.SUBJECTIVE and BiasFlag.PERCEPTION_BIAS in bias_flags:
            ranked.append(RankedEndpoint(
                endpoint=ea.endpoint.name,
                rank=EndpointRank.REJECTED,
                reason=(
                    f"Subjective endpoint without blinding. In open-label design, "
                    f"patient-reported outcomes are subject to expectation and placebo "
                    f"bias. Acceptable only as secondary endpoint in sham-controlled design."
                ),
                bias_score=0.7,
            ))
        elif ea.nature == EndpointNature.SUBJECTIVE:
            ranked.append(RankedEndpoint(
                endpoint=ea.endpoint.name,
                rank=EndpointRank.ACCEPTABLE,
                reason="Subjective but acceptable as secondary when paired with objective primary.",
                bias_score=0.5,
            ))
        elif BiasFlag.DETECTION_BIAS in ea.flags:
            ranked.append(RankedEndpoint(
                endpoint=ea.endpoint.name,
                rank=EndpointRank.REJECTED,
                reason=(
                    f"Detection bias — outcome ascertainment influenced by intervention. "
                    f"Not acceptable as primary endpoint."
                ),
                bias_score=0.85,
            ))
        elif ea.nature == EndpointNature.OBJECTIVE and ea.causal_role == CausalRole.INDEPENDENT:
            ranked.append(RankedEndpoint(
                endpoint=ea.endpoint.name,
                rank=EndpointRank.GOLD,
                reason="Objective, independently ascertained endpoint. HAS-acceptable as primary.",
                bias_score=0.1,
            ))
        else:
            ranked.append(RankedEndpoint(
                endpoint=ea.endpoint.name,
                rank=EndpointRank.ACCEPTABLE,
                reason="Acceptable with appropriate study design controls.",
                bias_score=0.3,
            ))

    for block in endpoint_repairs:
        for r in block.repairs:
            if r.type in (EndpointRepairKind.SURVIVAL, EndpointRepairKind.HARD_CLINICAL):
                ranked.append(RankedEndpoint(
                    endpoint=r.endpoint,
                    rank=EndpointRank.GOLD,
                    reason=f"[REPAIRED] {r.why_valid}",
                    bias_score=0.05 if r.type == EndpointRepairKind.SURVIVAL else 0.1,
                ))
            elif r.type == EndpointRepairKind.UTILIZATION_INDEPENDENT:
                ranked.append(RankedEndpoint(
                    endpoint=r.endpoint,
                    rank=EndpointRank.GOLD,
                    reason=f"[REPAIRED] {r.why_valid}",
                    bias_score=0.15,
                ))
            elif r.type == EndpointRepairKind.BIOMARKER:
                ranked.append(RankedEndpoint(
                    endpoint=r.endpoint,
                    rank=EndpointRank.ACCEPTABLE,
                    reason=f"[REPAIRED] {r.why_valid}",
                    bias_score=0.2,
                ))
            else:
                ranked.append(RankedEndpoint(
                    endpoint=r.endpoint,
                    rank=EndpointRank.ACCEPTABLE,
                    reason=f"[REPAIRED] {r.why_valid}",
                    bias_score=0.3,
                ))

    ranked.sort(key=lambda r: (
        {EndpointRank.GOLD: 0, EndpointRank.ACCEPTABLE: 1, EndpointRank.REJECTED: 2}[r.rank],
        r.bias_score,
    ))

    return ranked


# ===================================================================
# LEGACY COMPAT — generate_repair_plan (V1 output)
# ===================================================================

def generate_repair_plan(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
    bias_detections: list[BiasDetection],
    design: DesignRecommendation,
) -> RepairPlan | None:
    """Generate legacy RepairPlan for backward compatibility."""
    strategies = []
    failure_modes = []

    if not bias_flags and structure == CausalStructure.DIRECT:
        return None

    if BiasFlag.CIRCULARITY_RISK in bias_flags or structure == CausalStructure.CIRCULAR:
        fm, strats = _legacy_repair_circularity(endpoint_analyses, claim)
        failure_modes.extend(fm)
        strategies.extend(strats)

    if BiasFlag.DETECTION_BIAS in bias_flags:
        fm, strats = _legacy_repair_detection(endpoint_analyses, claim)
        failure_modes.extend(fm)
        strategies.extend(strats)

    if BiasFlag.MEDIATION_GAP in bias_flags:
        fm, strats = _legacy_repair_mediation(claim)
        failure_modes.extend(fm)
        strategies.extend(strats)

    if BiasFlag.PERCEPTION_BIAS in bias_flags:
        fm, strats = _legacy_repair_subjective(endpoint_analyses)
        failure_modes.extend(fm)
        strategies.extend(strats)

    if BiasFlag.PROCESS_TAUTOLOGY in bias_flags:
        fm, strats = _legacy_repair_tautology(claim)
        failure_modes.extend(fm)
        strategies.extend(strats)

    if not strategies:
        if structure == CausalStructure.MEDIATED:
            strategies.append(RepairStrategy(
                type=RepairType.ENDPOINT_ADDITION,
                description="Add intermediate process endpoint to complete mediation chain.",
                effect_on_causality="Completes the causal chain from intervention to outcome.",
            ))
            failure_modes.append("Incomplete mediation chain — missing intermediate endpoint.")

    if not strategies:
        return None

    problem_summary = _build_problem_summary(bias_flags, structure)
    minimal_change = _select_minimal_change(strategies)
    resulting_designs = _compute_resulting_designs(claim, bias_flags, strategies)

    return RepairPlan(
        problem_summary=problem_summary,
        failure_modes=failure_modes,
        repair_strategies=strategies,
        recommended_minimal_change=minimal_change,
        resulting_designs=resulting_designs,
    )


# ===================================================================
# V2 — Main entry point
# ===================================================================

def generate_repair_plan_v2(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
    bias_detections: list[BiasDetection],
    design: DesignRecommendation,
) -> RepairPlanV2 | None:
    """Generate V2 repair plan — 5-step clinically precise pipeline."""
    if not bias_flags and structure == CausalStructure.DIRECT:
        return None

    # Step 1
    failure = _diagnose_failure(endpoint_analyses, structure, bias_flags)

    # Step 2
    endpoint_repairs = _generate_endpoint_repairs(
        claim, endpoint_analyses, bias_flags, failure,
    )

    all_circular = (
        endpoint_analyses
        and all(ea.causal_role == CausalRole.CIRCULAR for ea in endpoint_analyses)
        and not endpoint_repairs
    )
    if all_circular:
        return RepairPlanV2(
            status="NON_REPAIRABLE",
            failure_diagnosis=failure,
            endpoint_repairs=[],
            causal_chain=[],
            recommended_designs=[],
            endpoint_ranking=_rank_endpoints(endpoint_analyses, [], bias_flags),
            problem_summary=(
                "All endpoints are structurally circular with intervention mechanism. "
                "No valid causal estimand can be identified under current endpoint space."
            ),
            non_repairable_reason=(
                "all endpoints are structurally circular with intervention mechanism"
            ),
        )

    # Step 3
    causal_chain = _reconstruct_causal_chain(
        claim, endpoint_analyses, endpoint_repairs, bias_flags, structure,
    )

    # Step 4
    has_subjective_only = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    recommended_designs = _repair_study_designs(
        claim, bias_flags, failure, has_subjective_only,
    )

    # Step 5
    endpoint_ranking = _rank_endpoints(
        endpoint_analyses, endpoint_repairs, bias_flags,
    )

    problem_summary = _build_problem_summary(bias_flags, structure)

    return RepairPlanV2(
        status="REPAIRABLE",
        failure_diagnosis=failure,
        endpoint_repairs=endpoint_repairs,
        causal_chain=causal_chain,
        recommended_designs=recommended_designs,
        endpoint_ranking=endpoint_ranking,
        problem_summary=problem_summary,
    )


# ===================================================================
# Legacy helpers
# ===================================================================

def _legacy_repair_circularity(
    endpoint_analyses: list[EndpointAnalysis],
    claim: ClinicalClaim,
) -> tuple[list[str], list[RepairStrategy]]:
    failure_modes = []
    strategies = []
    circular_eps = [ea for ea in endpoint_analyses if ea.causal_role == CausalRole.CIRCULAR]

    for ea in circular_eps:
        combined = f"{ea.endpoint.name.lower()} {ea.endpoint.description.lower()}"
        failure_modes.append(
            f"'{ea.endpoint.name}' is structurally circular: {claim.intervention} "
            f"generates or influences the measurement. Outcome ascertainment is not "
            f"independent of treatment arm assignment."
        )
        repairs = _lookup_detection_repairs(combined)
        if repairs:
            top = repairs[0]
            strategies.append(RepairStrategy(
                type=RepairType.ENDPOINT_REPLACEMENT,
                description=(
                    f"Replace '{ea.endpoint.name}' with {top.endpoint}"
                ),
                effect_on_causality=top.why_valid,
            ))
        else:
            strategies.append(RepairStrategy(
                type=RepairType.ENDPOINT_REPLACEMENT,
                description=(
                    f"Replace '{ea.endpoint.name}' with independently adjudicated "
                    f"clinical event rate at 12 months"
                ),
                effect_on_causality=(
                    "Decouples outcome from device mechanism via independent adjudication."
                ),
            ))

    return failure_modes, strategies


def _legacy_repair_detection(
    endpoint_analyses: list[EndpointAnalysis],
    claim: ClinicalClaim,
) -> tuple[list[str], list[RepairStrategy]]:
    failure_modes = []
    strategies = []
    detection_eps = [ea for ea in endpoint_analyses if BiasFlag.DETECTION_BIAS in ea.flags]

    for ea in detection_eps:
        failure_modes.append(
            f"'{ea.endpoint.name}' has detection bias — outcome ascertainment "
            f"is influenced by {claim.intervention}."
        )

    if detection_eps:
        strategies.append(RepairStrategy(
            type=RepairType.ENDPOINT_ADDITION,
            description=(
                "Add independently adjudicated clinical outcome (e.g., complication "
                "rate, survival) as co-primary endpoint to anchor detection-based findings."
            ),
            effect_on_causality=(
                "Validates that detection leads to clinically meaningful benefit "
                "via an outcome independent of the device."
            ),
        ))

    return failure_modes, strategies


def _legacy_repair_mediation(
    claim: ClinicalClaim,
) -> tuple[list[str], list[RepairStrategy]]:
    mediator_repairs = _lookup_mediation_repairs(claim)
    mediator_desc = mediator_repairs[0].endpoint if mediator_repairs else (
        "intermediate process endpoint (treatment change, referral, adherence)"
    )

    failure_modes = [
        f"Claim at {claim.level.value} level but endpoints measure clinical outcomes. "
        f"Causal chain from {claim.intervention} to outcome is not specified."
    ]
    strategies = [
        RepairStrategy(
            type=RepairType.ENDPOINT_ADDITION,
            description=f"Add mediator endpoint: {mediator_desc}",
            effect_on_causality="Completes the causal chain: mechanism → process → outcome.",
        ),
        RepairStrategy(
            type=RepairType.CLAIM_REFORMULATION,
            description=(
                "Reformulate claim directly at outcome level (Level C) to eliminate "
                "mediation gap."
            ),
            effect_on_causality="Aligns claim level with measured endpoints.",
        ),
    ]
    return failure_modes, strategies


def _legacy_repair_subjective(
    endpoint_analyses: list[EndpointAnalysis],
) -> tuple[list[str], list[RepairStrategy]]:
    failure_modes = [
        "All endpoints are patient-reported subjective measures. Without blinding, "
        "perceived benefit cannot be separated from placebo effect."
    ]
    strategies = []

    for ea in endpoint_analyses:
        combined = f"{ea.endpoint.name.lower()} {ea.endpoint.description.lower()}"
        proxies = _lookup_subjective_repairs(combined)
        if proxies:
            top = proxies[0]
            strategies.append(RepairStrategy(
                type=RepairType.ENDPOINT_ADDITION,
                description=f"Add objective co-primary: {top.endpoint}",
                effect_on_causality=top.why_valid,
            ))

    strategies.append(RepairStrategy(
        type=RepairType.DESIGN_CHANGE,
        description="Require sham-controlled double-blind RCT design.",
        effect_on_causality=(
            "Controls perception bias through blinding, making subjective "
            "endpoints valid primary outcomes."
        ),
    ))
    return failure_modes, strategies


def _legacy_repair_tautology(
    claim: ClinicalClaim,
) -> tuple[list[str], list[RepairStrategy]]:
    failure_modes = [
        "Process endpoint is the intervention itself — measuring what the device "
        "does as an outcome is tautological."
    ]
    strategies = [
        RepairStrategy(
            type=RepairType.ENDPOINT_ADDITION,
            description=(
                "Add downstream clinical endpoint (Level C) — e.g., complication rate, "
                "hospitalization, or survival — to demonstrate process translates to "
                "patient benefit."
            ),
            effect_on_causality=(
                "Breaks tautology by requiring evidence that the process change "
                "translates into clinical outcome improvement."
            ),
        ),
        RepairStrategy(
            type=RepairType.CLAIM_REFORMULATION,
            description="Reformulate claim to target clinical outcomes, not process metrics.",
            effect_on_causality="Aligns study with a testable causal hypothesis.",
        ),
    ]
    return failure_modes, strategies


def _build_problem_summary(bias_flags: list[BiasFlag], structure: CausalStructure) -> str:
    parts = []
    if structure == CausalStructure.CIRCULAR:
        parts.append("circular causal structure")
    if BiasFlag.CIRCULARITY_RISK in bias_flags:
        parts.append("endpoint circularity")
    if BiasFlag.DETECTION_BIAS in bias_flags:
        parts.append("detection bias")
    if BiasFlag.PERCEPTION_BIAS in bias_flags:
        parts.append("perception bias (all subjective endpoints)")
    if BiasFlag.MEDIATION_GAP in bias_flags:
        parts.append("mediation gap between claim and endpoints")
    if BiasFlag.PROCESS_TAUTOLOGY in bias_flags:
        parts.append("process tautology")
    if not parts:
        return "Structural issues detected in causal design."
    return "Study design has: " + "; ".join(parts) + "."


def _select_minimal_change(strategies: list[RepairStrategy]) -> str:
    priority = [
        RepairType.ENDPOINT_REPLACEMENT,
        RepairType.ENDPOINT_ADDITION,
        RepairType.DESIGN_CHANGE,
        RepairType.CLAIM_REFORMULATION,
    ]
    for ptype in priority:
        for s in strategies:
            if s.type == ptype:
                return s.description
    return strategies[0].description if strategies else "No repair available."


def _compute_resulting_designs(
    claim: ClinicalClaim,
    bias_flags: list[BiasFlag],
    strategies: list[RepairStrategy],
) -> list[StudyDesign]:
    has_design_change = any(s.type == RepairType.DESIGN_CHANGE for s in strategies)
    has_subjective_issue = BiasFlag.PERCEPTION_BIAS in bias_flags

    if has_subjective_issue and has_design_change:
        return [StudyDesign.SHAM_RCT, StudyDesign.RCT]
    if claim.level in (ClaimLevel.C, ClaimLevel.D):
        return [StudyDesign.RCT, StudyDesign.COHORT]
    if claim.level == ClaimLevel.B:
        return [StudyDesign.COHORT, StudyDesign.ITS, StudyDesign.BEFORE_AFTER]
    return [StudyDesign.RCT, StudyDesign.COHORT]
