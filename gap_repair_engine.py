"""Gap Repair Engine — maps ComparisonReport gaps to concrete repair actions.

Entry point: repair_comparison(report, claim, epistemic_output=None) → GapRepairPlan
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

from models import ClinicalClaim, ClaimLevel
from study_object import ClaimStudyGap, ComparisonReport, OverallRisk

if TYPE_CHECKING:
    from models import EngineOutput


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GapRepairType(Enum):
    ENDPOINT_REPLACEMENT    = "endpoint_replacement"
    ENDPOINT_ADDITION       = "endpoint_addition"
    ADJUDICATION_ADDITION   = "adjudication_addition"
    SURROGATE_VALIDATION    = "surrogate_validation"
    POSTMARKET_REGISTRY     = "postmarket_registry"
    CONTROL_ARM_ADDITION    = "control_arm_addition"
    DESIGN_CONFIRMATORY     = "design_confirmatory"
    DESIGN_SHAM             = "design_sham"
    FOLLOW_UP_EXTENSION     = "follow_up_extension"
    STUDY_COMMISSION        = "study_commission"
    BRIDGING_STUDY          = "bridging_study"
    CLAIM_RESTRICTION       = "claim_restriction"
    CONTEXT_TRANSPOSABILITY = "context_transposability"


class GapRepairEffort(Enum):
    LOW      = "low"       # Amendable sans nouvelle étude
    MEDIUM   = "medium"    # Amendement de protocole ou sous-étude
    HIGH     = "high"      # Nouvelle étude ou refonte majeure
    BLOCKING = "blocking"  # Non réparable avec les données existantes


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GapRepairAction:
    gap_dimension: str
    gap_severity: str
    repair_type: GapRepairType
    description: str
    specific_suggestion: str
    effort: GapRepairEffort
    removes_risk: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gap_dimension": self.gap_dimension,
            "gap_severity": self.gap_severity,
            "repair_type": self.repair_type.value,
            "description": self.description,
            "specific_suggestion": self.specific_suggestion,
            "effort": self.effort.value,
            "removes_risk": self.removes_risk,
        }


@dataclass
class GapRepairPlan:
    claim_text: str
    overall_risk: str
    actions: list[GapRepairAction]
    non_repairable_gaps: list[ClaimStudyGap]
    repair_summary: str
    is_fully_repairable: bool

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "overall_risk": self.overall_risk,
            "is_fully_repairable": self.is_fully_repairable,
            "repair_summary": self.repair_summary,
            "actions": [a.to_dict() for a in self.actions],
            "non_repairable_gaps": [
                {"dimension": g.dimension, "severity": g.severity, "description": g.description}
                for g in self.non_repairable_gaps
            ],
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def repair_comparison(
    report: ComparisonReport,
    claim: ClinicalClaim,
    epistemic_output: Optional["EngineOutput"] = None,
) -> GapRepairPlan:
    """Generate repair actions for all gaps in a ComparisonReport.

    Delegates endpoint gap repairs to repair_engine blocks when epistemic_output
    is provided; builds structural repairs (device/population/context/design)
    from gap dimension and severity directly.
    """
    actions: list[GapRepairAction] = []
    non_repairable: list[ClaimStudyGap] = []

    for gap in report.gaps:
        gap_actions, is_blocking = _repair_gap(gap, claim, epistemic_output)
        actions.extend(gap_actions)
        if is_blocking:
            non_repairable.append(gap)

    # Deduplicate by (repair_type, description, specific_suggestion)
    seen: set[tuple] = set()
    deduped: list[GapRepairAction] = []
    for a in actions:
        key = (a.repair_type, a.description, a.specific_suggestion[:80])
        if key not in seen:
            seen.add(key)
            deduped.append(a)
    actions = deduped

    _effort_order = {
        GapRepairEffort.LOW: 0,
        GapRepairEffort.MEDIUM: 1,
        GapRepairEffort.HIGH: 2,
        GapRepairEffort.BLOCKING: 3,
    }
    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    actions.sort(key=lambda a: (
        _effort_order[a.effort],
        _sev_order.get(a.gap_severity, 4),
    ))

    is_fully_repairable = len(non_repairable) == 0
    repair_summary = _build_summary(actions, non_repairable, report.overall_risk)

    return GapRepairPlan(
        claim_text=report.claim_text,
        overall_risk=report.overall_risk.value,
        actions=actions,
        non_repairable_gaps=non_repairable,
        repair_summary=repair_summary,
        is_fully_repairable=is_fully_repairable,
    )


# ---------------------------------------------------------------------------
# Gap dispatcher
# ---------------------------------------------------------------------------

def _repair_gap(
    gap: ClaimStudyGap,
    claim: ClinicalClaim,
    epistemic_output: Optional["EngineOutput"],
) -> tuple[list[GapRepairAction], bool]:
    """Returns (actions, is_blocking_for_original_claim)."""
    dim = gap.dimension
    if dim == "device":
        return _repair_device_gap(gap, claim)
    if dim == "population":
        return _repair_population_gap(gap, claim)
    if dim == "context":
        return _repair_context_gap(gap, claim)
    if dim == "design":
        return _repair_design_gap(gap, claim)
    if dim == "endpoint":
        return _repair_endpoint_gap(gap, claim, epistemic_output)
    return [], False


# ---------------------------------------------------------------------------
# DEVICE
# ---------------------------------------------------------------------------

def _repair_device_gap(
    gap: ClaimStudyGap, claim: ClinicalClaim,
) -> tuple[list[GapRepairAction], bool]:
    actions = []
    is_blocking = False

    if gap.severity == "CRITICAL":
        # DIFFERENT_DEVICE — étude sur un autre dispositif
        actions.append(GapRepairAction(
            gap_dimension="device",
            gap_severity=gap.severity,
            repair_type=GapRepairType.STUDY_COMMISSION,
            description="Commanditer une étude spécifique au dispositif revendiqué",
            specific_suggestion=(
                f"Le dispositif étudié est fondamentalement différent de '{claim.intervention}'. "
                "Aucune extrapolation n'est possible. Il faut commanditer un nouvel essai ou "
                f"une nouvelle cohorte prospective spécifique à '{claim.intervention}' "
                "dans l'indication cible."
            ),
            effort=GapRepairEffort.BLOCKING,
            removes_risk=["mismatch dispositif", "extrapolation inter-dispositifs"],
        ))
        # Alternative : restreindre la revendication au dispositif étudié
        actions.append(GapRepairAction(
            gap_dimension="device",
            gap_severity=gap.severity,
            repair_type=GapRepairType.CLAIM_RESTRICTION,
            description="Restreindre la revendication au dispositif réellement étudié",
            specific_suggestion=(
                "Alternative immédiate : reformuler la revendication pour couvrir uniquement "
                "le dispositif testé dans l'étude (référence exacte), en supprimant "
                f"'{claim.intervention}' du champ de la claim si ce n'est pas le dispositif étudié."
            ),
            effort=GapRepairEffort.LOW,
            removes_risk=["mismatch dispositif"],
        ))
        is_blocking = True

    else:
        # SAME_FAMILY — même famille, génération différente
        actions.append(GapRepairAction(
            gap_dimension="device",
            gap_severity=gap.severity,
            repair_type=GapRepairType.BRIDGING_STUDY,
            description="Étude pont ou sous-groupe spécifique au dispositif revendiqué",
            specific_suggestion=(
                "Le dispositif étudié appartient à la même famille mais est une génération "
                f"différente de '{claim.intervention}'. Options : "
                "(1) Étude de bridging technique démontrant l'équivalence de performance "
                "entre les deux générations (données banc d'essai + clinique). "
                "(2) Sous-groupe d'analyse restreint aux patients traités avec la version revendiquée, "
                "si disponible dans l'étude."
            ),
            effort=GapRepairEffort.MEDIUM,
            removes_risk=["extrapolation génération dispositif"],
        ))
        actions.append(GapRepairAction(
            gap_dimension="device",
            gap_severity=gap.severity,
            repair_type=GapRepairType.CLAIM_RESTRICTION,
            description="Restreindre la revendication à la génération étudiée",
            specific_suggestion=(
                "Reformuler la revendication pour couvrir explicitement la génération ou "
                "le modèle testé dans l'étude (numéro de référence exact). "
                "Étendre ensuite la claim à la version actuelle via un dossier de bridging."
            ),
            effort=GapRepairEffort.LOW,
            removes_risk=["extrapolation génération dispositif"],
        ))

    return actions, is_blocking


# ---------------------------------------------------------------------------
# POPULATION
# ---------------------------------------------------------------------------

def _repair_population_gap(
    gap: ClaimStudyGap, claim: ClinicalClaim,
) -> tuple[list[GapRepairAction], bool]:
    actions = []

    if gap.severity == "HIGH":
        # Population totalement différente
        actions.append(GapRepairAction(
            gap_dimension="population",
            gap_severity=gap.severity,
            repair_type=GapRepairType.STUDY_COMMISSION,
            description="Commanditer une étude dans la population cible",
            specific_suggestion=(
                "La population étudiée ne correspond pas à l'indication revendiquée. "
                "Une nouvelle étude dans la population cible est nécessaire. "
                "Préciser : critères d'inclusion/exclusion alignés avec l'indication revendiquée, "
                "effectif calculé sur la population cible."
            ),
            effort=GapRepairEffort.HIGH,
            removes_risk=["extrapolation population", "indication non étudiée"],
        ))
        actions.append(GapRepairAction(
            gap_dimension="population",
            gap_severity=gap.severity,
            repair_type=GapRepairType.CLAIM_RESTRICTION,
            description="Restreindre la revendication à la population étudiée",
            specific_suggestion=(
                "Reformuler la revendication pour couvrir uniquement la population "
                "réellement incluse dans l'étude. Supprimer les sous-populations ou "
                "indications non couvertes par les critères d'éligibilité de l'étude."
            ),
            effort=GapRepairEffort.LOW,
            removes_risk=["extrapolation population"],
        ))

    else:
        # MEDIUM — sous-groupe ou tranche d'âge
        actions.append(GapRepairAction(
            gap_dimension="population",
            gap_severity=gap.severity,
            repair_type=GapRepairType.CLAIM_RESTRICTION,
            description="Restreindre la revendication à la population réellement étudiée",
            specific_suggestion=(
                "La population étudiée diffère partiellement de l'indication revendiquée "
                "(sous-groupe, tranche d'âge, sévérité). Options : "
                "(1) Restreindre la revendication aux critères d'éligibilité de l'étude. "
                "(2) Fournir une analyse de sous-groupe pré-spécifiée couvrant la population cible. "
                "(3) Argumenter la transposabilité biologique ou clinique si justifiable."
            ),
            effort=GapRepairEffort.LOW,
            removes_risk=["extrapolation population partielle"],
        ))

    return actions, False


# ---------------------------------------------------------------------------
# CONTEXT
# ---------------------------------------------------------------------------

def _repair_context_gap(
    gap: ClaimStudyGap, claim: ClinicalClaim,
) -> tuple[list[GapRepairAction], bool]:
    actions = []

    actions.append(GapRepairAction(
        gap_dimension="context",
        gap_severity=gap.severity,
        repair_type=GapRepairType.CONTEXT_TRANSPOSABILITY,
        description="Fournir une analyse de transposabilité au contexte français",
        specific_suggestion=(
            "Les données proviennent d'un système de santé différent de la France. "
            "Soumettre à la HAS une analyse de transposabilité documentant : "
            "(1) Comparaison du parcours de soins et des pratiques cliniques, "
            "(2) Équivalence de la formation opérateur et des conditions d'accès, "
            "(3) Comparabilité de la population (épidémiologie, co-morbidités), "
            "(4) Données de vie réelle françaises si disponibles (registres, PMSI, SNDS)."
        ),
        effort=GapRepairEffort.MEDIUM,
        removes_risk=["non-transposabilité contexte", "hétérogénéité système de santé"],
    ))

    if gap.severity == "MEDIUM":
        # Système très différent — envisager étude française
        actions.append(GapRepairAction(
            gap_dimension="context",
            gap_severity=gap.severity,
            repair_type=GapRepairType.STUDY_COMMISSION,
            description="Conduire une étude dans le contexte français",
            specific_suggestion=(
                "Pour une revendication de niveau D (efficience en conditions réelles françaises), "
                "conduire une étude prospective en France : cohorte de vraie vie, "
                "étude pharmaco-épidémiologique sur données SNDS/PMSI, ou registre national. "
                "Objectif : démontrer que le bénéfice observé à l'étranger se réplique "
                "dans le parcours de soins français."
            ),
            effort=GapRepairEffort.HIGH,
            removes_risk=["non-transposabilité contexte"],
        ))

    return actions, False


# ---------------------------------------------------------------------------
# DESIGN
# ---------------------------------------------------------------------------

_DOMAIN_ANCHORS: dict[str, str] = {
    "neurology": (
        "(a) Taux de conversion vers la démence (critères DSM-5/NIA-AA) par évaluateur indépendant, "
        "(b) IRM volumétrique hippocampique par lecture centralisée en aveugle, "
        "(c) ADL/IADL évalués par clinicien indépendant, "
        "(d) Biomarqueurs CSF (tau, phospho-tau, amyloid-42) ou TEP amyloïde."
    ),
    "cardiology": (
        "(a) MACE (décès cardiovasculaire, IDM, AVC) adjugés par CEC indépendant, "
        "(b) Hospitalisations pour insuffisance cardiaque depuis données administratives (PMSI), "
        "(c) Mortalité toutes causes depuis registre civil, "
        "(d) Fraction d'éjection VG par échocardiographie centralisée en aveugle."
    ),
    "pulmonology": (
        "(a) Exacerbations sévères nécessitant hospitalisation (données PMSI/SNDS), "
        "(b) Mortalité toutes causes ou respiratoire depuis registre civil, "
        "(c) Test de marche 6 minutes (TM6) par évaluateur certifié indépendant, "
        "(d) Spirométrie centralisée (VEMS, CVF) par technicien indépendant en aveugle."
    ),
    "ophthalmology": (
        "(a) Acuité visuelle (ETDRS) par évaluateur certifié en aveugle du bras de traitement, "
        "(b) Perte ≥ 15 lettres ETDRS adjugée indépendamment, "
        "(c) Conversion vers forme exsudative par OCT lu en aveugle (lecture centralisée), "
        "(d) Taux de recours urgents en ophtalmologie (données PMSI)."
    ),
    "oncology": (
        "(a) Survie globale (OS) depuis registre civil, "
        "(b) Survie sans progression (PFS) par imagerie centralisée en aveugle (RECIST 1.1), "
        "(c) Taux de réponse complète/partielle confirmé par comité de révision indépendant, "
        "(d) Qualité de vie (EORTC QLQ-C30) comme co-critère si SHAM disponible."
    ),
    "orthopedics": (
        "(a) Taux de révision chirurgicale depuis registre national des implants, "
        "(b) Imagerie centralisée (radiographie, IRM) lue en aveugle, "
        "(c) Score fonctionnel standardisé (KOOS, OHS, WOMAC) par évaluateur indépendant, "
        "(d) Taux de complications majeures adjugées par CEC."
    ),
    "diabetes": (
        "(a) HbA1c par laboratoire central indépendant (en aveugle), "
        "(b) Taux d'hypoglycémies sévères depuis données PMSI/SNDS, "
        "(c) Glycémie interstitielle (TIR/TAR) par téléchargement aveugle du lecteur, "
        "(d) MACE à 12 mois adjugés par CEC indépendant."
    ),
    "gynecology": (
        "(a) Taux de ré-intervention chirurgicale à 24 mois (hystérectomie ou procédure secondaire) depuis données PMSI, "
        "(b) Volume fibrome/utérin par IRM pelvienne lue en aveugle (lecture centralisée), "
        "(c) Pertes sanguines objectivées par score PBLAC validé (carnet photographique standardisé), "
        "(d) Taux d'anémie ferriprive (Hb < 12 g/dL) par biologie centralisée à 6 et 12 mois."
    ),
    "sleep_medicine": (
        "(a) Événements cardiovasculaires majeurs (MACE : décès CV, IDM, AVC) adjugés par CEC indépendant, "
        "(b) Hospitalisations toutes causes depuis données administratives (PMSI/SNDS), "
        "(c) Mortalité toutes causes depuis registre civil à 36 mois, "
        "(d) Score de qualité de vie validé (FOSQ-10 ou SF-36) évalué en aveugle par évaluateur indépendant."
    ),
}

_DOMAIN_ANCHORS_DEFAULT = (
    "(a) Taux d'hospitalisations non planifiées (données PMSI/administratives), "
    "(b) Mortalité toutes causes (registre civil), "
    "(c) Évaluation fonctionnelle standardisée par évaluateur indépendant en aveugle, "
    "(d) Biomarqueur objectif validé dans l'indication (imagerie centralisée, biologie)."
)

# FR/EN/synonym → canonical key used in _DOMAIN_ANCHORS
_DOMAIN_ALIASES: dict[str, str] = {
    "neurologie": "neurology", "neurological": "neurology", "cognitif": "neurology",
    "cognitive": "neurology", "neuroscience": "neurology", "dementia": "neurology",
    "cardiologie": "cardiology", "cardiovascular": "cardiology", "cardiac": "cardiology",
    "heart": "cardiology", "coronary": "cardiology",
    "pneumologie": "pulmonology", "respiratory": "pulmonology", "pulmonaire": "pulmonology",
    "pulmonary": "pulmonology", "bpco": "pulmonology", "copd": "pulmonology",
    "ophtalmologie": "ophthalmology", "ophtalmo": "ophthalmology", "ocular": "ophthalmology",
    "retinal": "ophthalmology", "vision": "ophthalmology", "rétine": "ophthalmology",
    "oncologie": "oncology", "cancer": "oncology", "tumor": "oncology", "tumeur": "oncology",
    "orthopédie": "orthopedics", "orthopedic": "orthopedics", "arthroplasty": "orthopedics",
    "traumatologie": "orthopedics", "implant": "orthopedics",
    "diabète": "diabetes", "diabetic": "diabetes", "endocrinologie": "diabetes",
    "glycémie": "diabetes", "glucose": "diabetes",
    "gynécologie": "gynecology", "gynecologie": "gynecology", "gynecological": "gynecology",
    "obstétrique": "gynecology", "obstetric": "gynecology", "utérin": "gynecology",
    "fibrome": "gynecology", "endométrial": "gynecology", "menorrhagia": "gynecology",
    "ménorragie": "gynecology",
    "somnologie": "sleep_medicine", "sommeil": "sleep_medicine", "sahos": "sleep_medicine",
    "sleep apnea": "sleep_medicine", "apnée": "sleep_medicine", "osas": "sleep_medicine",
    "hypoglosse": "sleep_medicine", "stimulation hypoglosse": "sleep_medicine",
}


def _normalize_domain(domain: str) -> str:
    """Return canonical domain key (used in _DOMAIN_ANCHORS) from any FR/EN/synonym."""
    d = domain.lower().strip()
    if d in _DOMAIN_ANCHORS:
        return d
    for alias, canonical in _DOMAIN_ALIASES.items():
        if alias in d:
            return canonical
    return d


def _domain_objective_anchors(domain: str) -> str:
    canonical = _normalize_domain(domain)
    return _DOMAIN_ANCHORS.get(canonical, _DOMAIN_ANCHORS_DEFAULT)


def _repair_design_gap(
    gap: ClaimStudyGap, claim: ClinicalClaim,
) -> tuple[list[GapRepairAction], bool]:
    actions = []
    desc = gap.description.lower()

    # 1. Exploratory design — CRITICAL, non-repairable
    if "exploratoire" in desc or gap.severity == "CRITICAL":
        actions.append(GapRepairAction(
            gap_dimension="design",
            gap_severity=gap.severity,
            repair_type=GapRepairType.DESIGN_CONFIRMATORY,
            description="Convertir en design confirmatoire pré-enregistré",
            specific_suggestion=(
                "Une étude exploratoire (série de cas, pilote, mono-bras sans hypothèse "
                "pré-enregistrée) répond à un objectif de génération d'hypothèses, non de "
                "confirmation. Elle ne permet pas d'établir un effet causal et ne soutient "
                "pas une revendication d'outcome (niveau C/D). "
                "Éléments requis pour un design confirmatoire : "
                "(1) Hypothèse primaire pré-spécifiée et enregistrée (ClinicalTrials.gov, EUDAMED), "
                "(2) Calcul du nombre de sujets nécessaires (NSN) sur le critère primaire, "
                "(3) Plan d'analyse statistique verrouillé avant la levée de l'aveugle, "
                "(4) Critère principal préalablement défini comme co-primaire ou primaire, "
                "(5) DSMB indépendant si essai contrôlé."
            ),
            effort=GapRepairEffort.BLOCKING,
            removes_risk=["design exploratoire", "p-hacking", "hypothèse post-hoc"],
        ))
        return actions, True

    # 2. No comparator for C/D claim
    if "sans comparateur" in desc or "comparateur" in desc:
        _claim_level = getattr(claim, "level", None)
        control_type = (
            "SHAM ou comparateur actif" if _claim_level and _claim_level.value in ("C", "D")
            else "comparateur approprié"
        )
        actions.append(GapRepairAction(
            gap_dimension="design",
            gap_severity=gap.severity,
            repair_type=GapRepairType.CONTROL_ARM_ADDITION,
            description=f"Ajouter un bras contrôle ({control_type})",
            specific_suggestion=(
                f"Revendication niveau {_claim_level.value if _claim_level else 'C/D'} "
                "sans comparateur : le contrefactuel n'est pas observé. Options : "
                "(C) Essai contrôlé randomisé avec comparateur actif (SOC) ou SHAM. "
                "(D) RCT pragmatique vs. soins standards, ou cohorte prospective avec "
                "groupe contrôle concurrent (appariement par score de propension pré-spécifié). "
                "Attention : un design mono-bras avec contrôle historique est insuffisant "
                "sauf données publiées robustes et population strictement identique."
            ),
            effort=GapRepairEffort.HIGH,
            removes_risk=["absence de comparateur", "biais de confusion", "régression vers la moyenne"],
        ))
        return actions, False

    # 3. Open-label with subjective primary
    if "patient-rapporté" in desc or "subjectif" in desc or "pro" in desc:
        actions.append(GapRepairAction(
            gap_dimension="design",
            gap_severity=gap.severity,
            repair_type=GapRepairType.DESIGN_SHAM,
            description="Passer en design SHAM-contrôlé en double aveugle",
            specific_suggestion=(
                "Critère principal patient-rapporté (PRO) en design ouvert : inacceptable pour HAS. "
                "Solution préférentielle : essai SHAM-contrôlé avec aveugle patient. "
                "Design SHAM : procédure de sham identique en apparence à l'intervention active, "
                "patient en aveugle, évaluateur PRO en aveugle. "
                "Critère de jugement PRO reste valide si aveugle est correctement maintenu."
            ),
            effort=GapRepairEffort.HIGH,
            removes_risk=["biais de perception", "effet placebo", "biais d'expectation"],
        ))
        anchors = _domain_objective_anchors(getattr(claim, "domain", "") or "")
        actions.append(GapRepairAction(
            gap_dimension="design",
            gap_severity=gap.severity,
            repair_type=GapRepairType.ENDPOINT_ADDITION,
            description="Ajouter un co-critère primaire objectif adapté à l'indication",
            specific_suggestion=(
                "Si le design SHAM est infaisable : ajouter un co-critère primaire objectif "
                "indépendant du dispositif. Options spécifiques à l'indication : "
                f"{anchors} "
                "Le critère subjectif peut rester en critère secondaire."
            ),
            effort=GapRepairEffort.MEDIUM,
            removes_risk=["biais de perception", "effet Hawthorne"],
        ))
        return actions, False

    # 4. Short / insufficient follow-up
    if "suivi" in desc or "mois" in desc:
        is_durability_only = "durabilité" in desc  # LOW gap (12–24 mois)
        if is_durability_only:
            action_desc = "Étendre le suivi à 24 mois pour confirmer la durabilité"
            suggestion = (
                "Pour une affection chronique, un suivi inférieur à 24 mois laisse ouverte "
                "la question de la durabilité à long terme : maintien de l'effet, taux de "
                "ré-intervention et sécurité long terme restent à établir. "
                "Options : (1) Registre post-commercialisation ou cohorte de suivi avec données "
                "à 24 mois (taux de ré-intervention, maintien de l'effet, sécurité long terme). "
                "(2) Étude de prolongation ouverte à partir de l'essai principal. "
                "(3) Extraction PMSI/SNDS sur la cohorte traitée pour données médico-administratives."
            )
        else:
            action_desc = "Allonger le suivi à ≥ 12 mois minimum, 24 mois recommandés"
            suggestion = (
                "Un suivi inférieur à 12 mois ne couvre pas une durée cliniquement significative "
                "pour une affection chronique : les effets bénéfiques peuvent s'estomper et "
                "des complications tardives peuvent émerger après cette période. "
                "Options : (1) Amendement de protocole pour extension de suivi (si étude en cours). "
                "(2) Étude de prolongation ouverte à l'issue du suivi principal. "
                "(3) Registre post-commercialisation avec données de suivi long terme (24 mois minimum "
                "pour les implants, ablation endométriale, neurostimulation, pathologies respiratoires)."
            )
        actions.append(GapRepairAction(
            gap_dimension="design",
            gap_severity=gap.severity,
            repair_type=GapRepairType.FOLLOW_UP_EXTENSION,
            description=action_desc,
            specific_suggestion=suggestion,
            effort=GapRepairEffort.MEDIUM,
            removes_risk=["suivi insuffisant", "durabilité non confirmée à long terme"],
        ))
        return actions, False

    # 5. Non-randomized comparative
    actions.append(GapRepairAction(
        gap_dimension="design",
        gap_severity=gap.severity,
        repair_type=GapRepairType.CONTROL_ARM_ADDITION,
        description="Ajouter la randomisation ou un ajustement pré-spécifié des facteurs de confusion",
        specific_suggestion=(
            "Étude comparative non randomisée : risque de biais de sélection résiduel. "
            "Options par ordre de robustesse : "
            "(1) Randomisation : transformer en RCT si faisable. "
            "(2) Score de propension pré-spécifié (matching ou IPTW) avec rapport de sensibilité. "
            "(3) Variable instrumentale ou différences-en-différences si randomisation impossible. "
            "Le plan d'analyse des facteurs de confusion doit être enregistré avant la collecte."
        ),
        effort=GapRepairEffort.MEDIUM,
        removes_risk=["biais de sélection", "confusion résiduelle"],
    ))
    return actions, False


# ---------------------------------------------------------------------------
# ENDPOINT
# ---------------------------------------------------------------------------

def _circularity_level_ab_action(
    gap: ClaimStudyGap, claim: ClinicalClaim,
) -> list[GapRepairAction]:
    """Return a LOW-effort claim reformulation option when claim is level A or B.

    For process/mechanism-level claims, the circularity is resolvable without a new
    study by scoping the claim to technical performance (sensitivity/specificity/precision)
    rather than clinical benefit.
    """
    claim_level = getattr(claim, "level", None)
    if claim_level is None or claim_level.value not in ("MECHANISM", "PROCESS"):
        return []
    return [GapRepairAction(
        gap_dimension="endpoint",
        gap_severity=gap.severity,
        repair_type=GapRepairType.CLAIM_RESTRICTION,
        description="Reformuler la revendication en claim de performance technique (niveau A)",
        specific_suggestion=(
            "La circularité est réparable sans nouvelle étude si la revendication est reformulée "
            "en claim de performance technique (niveau A), qui ne requiert pas d'endpoint clinique "
            "indépendant. Exemples de formulation acceptables : "
            "'[Dispositif] détecte [condition] avec une sensibilité de X% et une spécificité de Y% "
            "vs. [gold standard]' ; "
            "'[Dispositif] mesure [paramètre] avec une concordance de ±Z vs. méthode de référence'. "
            "Ce niveau est validable avec les études de performance existantes (ex : TIL-001, TIL-002 "
            "pour ODYSIGHT) sans endpoint clinique indépendant. "
            "Note : ce niveau A ne soutient pas de revendication de bénéfice clinique ou "
            "médico-économique. La revendication clinique (niveau C/D) nécessitera une étude "
            "avec endpoint strictement indépendant du dispositif."
        ),
        effort=GapRepairEffort.LOW,
        removes_risk=["circularité sur claim de performance"],
    )]


def _repair_endpoint_gap(
    gap: ClaimStudyGap,
    claim: ClinicalClaim,
    epistemic_output: Optional["EngineOutput"],
) -> tuple[list[GapRepairAction], bool]:
    actions = []
    desc = gap.description.lower()

    # 1. Delegate to existing repair_plan_v2 ONLY for circularity/detection gaps.
    # Skip MEDIATOR repairs — they propose intermediate steps for already-valid outcome
    # endpoints, which inverts the logic (the outcome IS the target, not what to replace).
    is_circularity_gap = "circulaire" in desc
    is_detection_gap = "détection" in desc or "alerte" in desc or "monitoring" in desc
    if (is_circularity_gap or is_detection_gap) and epistemic_output and epistemic_output.repair_plan_v2:
        plan = epistemic_output.repair_plan_v2
        for block in plan.endpoint_repairs:
            for r in block.repairs[:2]:
                if r.causal_role == "MEDIATOR":
                    continue  # skip: adds intermediate step for an already-valid outcome endpoint
                actions.append(GapRepairAction(
                    gap_dimension="endpoint",
                    gap_severity=gap.severity,
                    repair_type=GapRepairType.ENDPOINT_REPLACEMENT,
                    description=f"Remplacer '{block.original_endpoint}'",
                    specific_suggestion=f"{r.endpoint} — {r.why_valid}",
                    effort=GapRepairEffort.HIGH,
                    removes_risk=list(r.risk_reduction),
                ))
        if actions and is_circularity_gap:
            actions.extend(_circularity_level_ab_action(gap, claim))
        if actions:
            return actions, gap.severity == "CRITICAL"

    # 2. CIRCULARITY_RISK (fallback si pas de repair_plan_v2)
    if is_circularity_gap and not actions:
        actions.extend(_circularity_level_ab_action(gap, claim))
        # Option principale : remplacer par un outcome indépendant (toujours requiert nouvelle étude)
        actions.append(GapRepairAction(
            gap_dimension="endpoint",
            gap_severity=gap.severity,
            repair_type=GapRepairType.ENDPOINT_REPLACEMENT,
            description="Remplacer le critère circulaire par un outcome indépendant",
            specific_suggestion=(
                "Le critère principal est généré ou influencé par le dispositif lui-même : "
                "structure causale circulaire. Remplacer par : "
                "(1) Taux d'événements cliniques adjugés indépendamment à 12 mois (CEC), "
                "(2) Mortalité toutes causes depuis le registre d'état civil, "
                "(3) Hospitalisations non planifiées depuis les données administratives (PMSI/SNDS). "
                "Le nouveau critère doit être strictement indépendant du mécanisme du dispositif."
            ),
            effort=GapRepairEffort.HIGH,
            removes_risk=["circularité", "biais de détection", "absence d'indépendance de l'ascertainment"],
        ))
        return actions, True  # blocking — nouvelle étude nécessaire pour claim clinique

    # 3. SURROGATE_RISK
    if "surrogate" in desc or "substitution" in desc:
        anchors = _domain_objective_anchors(getattr(claim, "domain", "") or "")
        # Check if any primary endpoint is flagged as feasibility-accepted
        _primary_eps = [ep for ep in (getattr(claim, "endpoints", None) or []) if ep.is_primary]
        _is_feasibility = any(
            getattr(ep, "is_feasibility_accepted_surrogate", False) for ep in _primary_eps
        )
        if _is_feasibility:
            # Surrogate accepted by default of feasibility — lighter repair path
            actions.append(GapRepairAction(
                gap_dimension="endpoint",
                gap_severity=gap.severity,
                repair_type=GapRepairType.POSTMARKET_REGISTRY,
                description="Mettre en place un programme de données post-marché (registre/PMSI)",
                specific_suggestion=(
                    "Lorsqu'un endpoint clinique dur n'est pas réalisable à court terme, un "
                    "surrogate peut être accepté à titre conditionnel, sous réserve que sa "
                    "relation causale avec le bénéfice clinique soit biologiquement plausible. "
                    "Engagement requis : (1) Registre post-commercialisation prospectif avec "
                    "données de morbi-mortalité à 36–60 mois (hospitalisations PMSI, mortalité "
                    "registre civil, événements cardiovasculaires adjugés par CEC). "
                    "(2) Rapport intermédiaire à 18 mois soumis à la CNEDiMTS. "
                    "(3) Analyse en sous-groupe sur les patients de la génération évaluée "
                    "(si mix de versions dans l'étude index). "
                    "Ce programme remplace l'obligation de nouvelle étude à court terme."
                ),
                effort=GapRepairEffort.MEDIUM,
                removes_risk=["surrogate conditionnel", "absence de données long terme"],
            ))
        else:
            # Standard surrogate — requires endpoint replacement or formal validation
            actions.append(GapRepairAction(
                gap_dimension="endpoint",
                gap_severity=gap.severity,
                repair_type=GapRepairType.ENDPOINT_REPLACEMENT,
                description="Remplacer le surrogate par un endpoint clinique dur adapté à l'indication",
                specific_suggestion=(
                    "Le critère de substitution n'est pas formellement validé dans cette indication. "
                    "Remplacer par un critère clinique dur comme critère primaire. "
                    f"Options spécifiques à l'indication : {anchors} "
                    "Le surrogate peut rester en critère secondaire exploratoire."
                ),
                effort=GapRepairEffort.HIGH,
                removes_risk=["surrogate non validé", "rupture du lien surrogate→outcome"],
            ))
            actions.append(GapRepairAction(
                gap_dimension="endpoint",
                gap_severity=gap.severity,
                repair_type=GapRepairType.SURROGATE_VALIDATION,
                description="Obtenir une validation formelle du surrogate dans cette indication",
                specific_suggestion=(
                    "Alternative : valider formellement le surrogate auprès de HAS/FDA/EMA. "
                    "Dossier requis : (1) Méta-analyse de RCTs démontrant la corrélation "
                    "surrogate→outcome dans cette indication précise, "
                    "(2) Plausibilité biologique de la chaîne causale documentée, "
                    "(3) Absence de contestation dans la littérature des 5 dernières années. "
                    "Note : la validation est indication-spécifique."
                ),
                effort=GapRepairEffort.HIGH,
                removes_risk=["surrogate non validé"],
            ))
        return actions, False

    # 4. DETECTION_BIAS (fallback)
    if "détection" in desc or "alerte" in desc or "monitoring" in desc:
        actions.append(GapRepairAction(
            gap_dimension="endpoint",
            gap_severity=gap.severity,
            repair_type=GapRepairType.ENDPOINT_ADDITION,
            description="Ajouter un outcome clinique indépendant du dispositif",
            specific_suggestion=(
                "Le biais de détection est présent : la fréquence des événements détectés "
                "dépend de la sensibilité du dispositif. Ajouter comme co-critère primaire "
                "un outcome clinique indépendant : "
                "(1) Événements confirmés par CEC indépendant (non déclenché par le dispositif), "
                "(2) Hospitalisations depuis données administratives (PMSI/SNDS), "
                "(3) Mortalité depuis registre civil."
            ),
            effort=GapRepairEffort.HIGH,
            removes_risk=["biais de détection", "dépendance ascertainment/traitement"],
        ))
        return actions, False

    # 5. ADJUDICATION_RISK — CEC pour événements, lecture centralisée pour mesures
    if "adjudic" in desc:
        primary_ep_names = " ".join(
            ep.name.lower() for ep in claim.endpoints if ep.is_primary
        )
        is_measurement_ep = any(
            kw in primary_ep_names
            for kw in ("vems", "fev", "spirom", "score", "moca", "mmse", "adas",
                       "acuité", "acuity", "pression", "glyc", "hba1c", "imc", "bmi")
        )
        if is_measurement_ep:
            specific = (
                "Le critère primaire est une mesure (score ou paramètre physiologique), "
                "non un événement clinique. La réponse adaptée n'est pas un CEC mais "
                "une lecture centralisée standardisée : "
                "(1) Évaluateur indépendant formé et certifié, en aveugle du bras de traitement, "
                "(2) Protocole d'évaluation pré-spécifié (conditions, équipement, intervalles), "
                "(3) Calcul de fiabilité inter-évaluateur (ICC ou kappa) inclus dans le rapport, "
                "(4) Double lecture pour les cas ambigus avec procédure de résolution. "
                "Amendable sur une étude en cours — coût faible, impact HAS fort."
            )
        else:
            specific = (
                "Critère événementiel objectif sans adjudication indépendante documentée. "
                "Mettre en place un CEC (Comité d'Évaluation des Critères) : "
                "(1) Charter d'adjudication pré-spécifié avant la levée de l'aveugle, "
                "(2) Au moins 3 experts indépendants en aveugle du bras de traitement, "
                "(3) Procédure de résolution des désaccords documentée, "
                "(4) Rapport de divergence CEC vs. investigateur soumis aux régulateurs. "
                "Amendable sur une étude en cours — coût modéré, impact HAS fort."
            )
        actions.append(GapRepairAction(
            gap_dimension="endpoint",
            gap_severity=gap.severity,
            repair_type=GapRepairType.ADJUDICATION_ADDITION,
            description=(
                "Mettre en place une lecture centralisée standardisée"
                if is_measurement_ep else
                "Ajouter un comité d'adjudication indépendant (CEC)"
            ),
            specific_suggestion=specific,
            effort=GapRepairEffort.LOW,
            removes_risk=["biais d'adjudication", "ascertainment non indépendant"],
        ))
        return actions, False

    # 6. Fallback générique endpoint
    actions.append(GapRepairAction(
        gap_dimension="endpoint",
        gap_severity=gap.severity,
        repair_type=GapRepairType.ENDPOINT_REPLACEMENT,
        description="Remplacer ou compléter le critère de jugement problématique",
        specific_suggestion=(
            "Le critère de jugement présente un risque épistémique identifié. "
            "Consulter l'analyse épistémique complète (BiasFlags) pour les "
            "recommandations de remplacement spécifiques."
        ),
        effort=GapRepairEffort.HIGH,
        removes_risk=["risque endpoint non qualifié"],
    ))
    return actions, False


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _build_summary(
    actions: list[GapRepairAction],
    non_repairable: list[ClaimStudyGap],
    overall_risk: OverallRisk,
) -> str:
    if not actions and not non_repairable:
        return "Aucune action de réparation nécessaire."

    low_count = sum(1 for a in actions if a.effort == GapRepairEffort.LOW)
    medium_count = sum(1 for a in actions if a.effort == GapRepairEffort.MEDIUM)
    high_count = sum(1 for a in actions if a.effort in (
        GapRepairEffort.HIGH, GapRepairEffort.BLOCKING,
    ))

    if non_repairable:
        dims = ", ".join(g.dimension for g in non_repairable)
        return (
            f"{len(non_repairable)} gap(s) non réparable(s) sans nouvelle étude "
            f"({dims}). "
            f"{low_count} action(s) immédiate(s), {medium_count} par amendement, "
            f"{high_count} nécessitant une nouvelle étude. "
            f"Risque global actuel : {overall_risk.value}."
        )

    if high_count == 0:
        return (
            f"Tous les gaps sont réparables sans nouvelle étude. "
            f"{low_count} action(s) immédiate(s), {medium_count} par amendement de protocole. "
            f"Risque résiduel après réparation : LOW."
        )

    return (
        f"{len(actions)} action(s) de réparation identifiées. "
        f"{low_count} immédiate(s) (sans nouvelle étude), "
        f"{medium_count} par amendement, "
        f"{high_count} nécessitant une nouvelle étude ou refonte majeure. "
        f"Risque global actuel : {overall_risk.value}."
    )
