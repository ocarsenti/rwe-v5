"""Study Object — complete structured representation of a clinical study (Mode 2 / Repair).

StudyObject is richer than StudyParseResult (Mode 1):
  - full trial identity (acronym, registration, funding)
  - blinding, randomization, allocation concealment
  - comparator type and description
  - population details (age range, inclusion/exclusion criteria)
  - per-endpoint results (direction, significance, adjudication)
  - statistical setup (analysis set, sample size calculation)
  - dropout rate, care setting

ComparisonReport is the structured output of comparing a ClinicalClaim to a StudyObject.
It produces:
  - per-dimension gaps (device / population / context / design / endpoint)
  - overall risk level
  - simulated HAS critique bullets
  - ordered repair priority
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

from endpoint_classifier import is_known_validated_surrogate
from models import (
    BiasFlag,
    CausalRole,
    ClaimLevel,
    ClinicalClaim,
    ComparatorFeasibility,
    DeviceAlignment,
    DeviceMatchType,
    Endpoint,
    EndpointNature,
    PopulationAlignment,
    PopulationMatchType,
    ContextAlignment,
    ContextMatchType,
    StudyDesign,
)

if TYPE_CHECKING:
    from models import EngineOutput


# ---------------------------------------------------------------------------
# New enums
# ---------------------------------------------------------------------------

class BlindingLevel(Enum):
    OPEN_LABEL = "OPEN_LABEL"
    SINGLE_BLIND = "SINGLE_BLIND"
    DOUBLE_BLIND = "DOUBLE_BLIND"
    SHAM_CONTROLLED = "SHAM_CONTROLLED"
    UNKNOWN = "UNKNOWN"


class ComparatorType(Enum):
    SHAM = "SHAM"
    PLACEBO = "PLACEBO"
    ACTIVE = "ACTIVE"
    STANDARD_OF_CARE = "STANDARD_OF_CARE"
    BEST_AVAILABLE = "BEST_AVAILABLE"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class AnalysisSet(Enum):
    ITT = "ITT"
    mITT = "mITT"
    PP = "PP"
    FAS = "FAS"
    UNKNOWN = "UNKNOWN"


class CareSetting(Enum):
    INPATIENT = "INPATIENT"
    OUTPATIENT = "OUTPATIENT"
    HOME = "HOME"
    HYBRID = "HYBRID"
    UNKNOWN = "UNKNOWN"


class ResultDirection(Enum):
    IMPROVED = "IMPROVED"
    NOT_IMPROVED = "NOT_IMPROVED"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class FundingType(Enum):
    INDUSTRY = "INDUSTRY"
    ACADEMIC = "ACADEMIC"
    PUBLIC = "PUBLIC"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class OverallRisk(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# StudyEndpoint — richer than EndpointEvidence (Mode 1)
# ---------------------------------------------------------------------------

@dataclass
class StudyEndpoint:
    name: str
    is_primary: bool = False
    time_point: str = ""
    is_validated_surrogate: bool = False
    is_feasibility_accepted_surrogate: bool = False
    is_independently_adjudicated: bool = False
    result_direction: ResultDirection = ResultDirection.UNKNOWN
    reached_significance: Optional[bool] = None
    nature: EndpointNature = EndpointNature.OBJECTIVE
    causal_role: CausalRole = CausalRole.INDEPENDENT
    # True when the endpoint's value in the evaluated device's arm is a pre-specified
    # protocol parameter rather than a measured outcome (e.g. contrast volume fixed at
    # 5 mL by design), while the comparator arm's value is genuinely measured — makes
    # any "superiority" on this criterion tautological by construction, not a real
    # comparative finding. cf. avis CNEDiMTS VIS-RX 8145 (étude Nishi et al. 2023).
    value_fixed_by_protocol: bool = False

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "is_primary": self.is_primary,
            "time_point": self.time_point,
            "is_validated_surrogate": self.is_validated_surrogate,
            "is_feasibility_accepted_surrogate": self.is_feasibility_accepted_surrogate,
            "is_independently_adjudicated": self.is_independently_adjudicated,
            "result_direction": self.result_direction.value,
            "nature": self.nature.value,
            "causal_role": self.causal_role.value,
            "value_fixed_by_protocol": self.value_fixed_by_protocol,
        }
        if self.reached_significance is not None:
            d["reached_significance"] = self.reached_significance
        return d


# ---------------------------------------------------------------------------
# StudyObject
# ---------------------------------------------------------------------------

@dataclass
class StudyObject:
    # Identity
    acronym: str = ""
    title: str = ""
    publication_year: Optional[int] = None
    registration_id: str = ""
    funding_type: FundingType = FundingType.UNKNOWN

    # Design
    study_design: Optional[StudyDesign] = None
    is_randomized: bool = False
    blinding_level: BlindingLevel = BlindingLevel.UNKNOWN
    who_is_blinded: list[str] = field(default_factory=list)
    allocation_concealment: Optional[bool] = None
    protocol_registered_before_enrollment: Optional[bool] = None
    is_multicentric: Optional[bool] = None

    # Comparator
    has_comparator: Optional[bool] = None
    comparator_type: ComparatorType = ComparatorType.UNKNOWN
    comparator_description: str = ""
    comparator_feasibility: ComparatorFeasibility = ComparatorFeasibility.UNKNOWN

    # Confounding / co-intervention (cf. avis CNEDiMTS SOMNIO 7781: SA Insuffisant
    # because the observed effect could not be attributed to the device — concomitant
    # hypnotic treatments were neither described nor controlled)
    concomitant_treatments_present: Optional[bool] = None
    concomitant_treatments_controlled: Optional[bool] = None
    concomitant_treatments_description: str = ""

    # Performance goal justification — only relevant when study_design is
    # SINGLE_ARM_PERFORMANCE_GOAL (cf. avis CNEDiMTS SAPIEN 3/ALTERRA 7873: accepted
    # design, but HAS's residual critique was the absence of documented clinical
    # justification for the pre-specified success threshold itself)
    performance_goal_clinically_justified: Optional[bool] = None

    # CE marking scope — does the population and/or anatomical usage described in
    # the study fall within the device's approved CE marking scope? Distinct from
    # population_alignment (claim vs. study): this checks study vs. regulatory
    # approval scope. A study conducted outside the CE-marked indication (broader
    # population, different anatomical site or usage) cannot alone support a claim
    # scoped to the approved indication without an explicit extrapolation analysis.
    indication_matches_ce_marking: Optional[bool] = None

    # Population
    n_patients: Optional[int] = None
    age_min: Optional[float] = None
    age_max: Optional[float] = None
    key_inclusion_criteria: list[str] = field(default_factory=list)
    key_exclusion_criteria: list[str] = field(default_factory=list)

    # Intervention
    device_studied: str = ""
    care_setting: CareSetting = CareSetting.UNKNOWN
    operator_training_required: Optional[bool] = None

    # Follow-up
    follow_up_months: Optional[float] = None
    longest_follow_up_months: Optional[float] = None
    dropout_rate_pct: Optional[float] = None

    # Endpoints
    endpoints: list[StudyEndpoint] = field(default_factory=list)
    # Set true when multiple primary endpoints are covered by a documented
    # multiplicity-control procedure (gatekeeping, hierarchical testing,
    # alpha-splitting) — cf. avis CNEDiMTS ENTERRA II 7254: accepted but with a
    # downgraded ASA specifically because of endpoint multiplicity without hierarchy.
    endpoint_hierarchy_prespecified: Optional[bool] = None

    # Statistics
    primary_analysis_set: AnalysisSet = AnalysisSet.UNKNOWN
    sample_size_calculation_provided: bool = False

    # Context
    study_countries: list[str] = field(default_factory=list)

    # Results
    primary_endpoint_met: Optional[bool] = None
    key_safety_signals: list[str] = field(default_factory=list)

    # CAS alignment (populated by LLM parser)
    device_alignment: Optional[DeviceAlignment] = None
    population_alignment: Optional[PopulationAlignment] = None
    context_alignment: Optional[ContextAlignment] = None

    def to_dict(self) -> dict:
        return {
            "acronym": self.acronym,
            "title": self.title,
            "publication_year": self.publication_year,
            "registration_id": self.registration_id,
            "funding_type": self.funding_type.value,
            "study_design": self.study_design.value if self.study_design else None,
            "is_randomized": self.is_randomized,
            "blinding_level": self.blinding_level.value,
            "who_is_blinded": self.who_is_blinded,
            "allocation_concealment": self.allocation_concealment,
            "protocol_registered_before_enrollment": self.protocol_registered_before_enrollment,
            "is_multicentric": self.is_multicentric,
            "has_comparator": self.has_comparator,
            "comparator_type": self.comparator_type.value,
            "comparator_description": self.comparator_description,
            "comparator_feasibility": self.comparator_feasibility.value,
            "concomitant_treatments_present": self.concomitant_treatments_present,
            "concomitant_treatments_controlled": self.concomitant_treatments_controlled,
            "concomitant_treatments_description": self.concomitant_treatments_description,
            "performance_goal_clinically_justified": self.performance_goal_clinically_justified,
            "indication_matches_ce_marking": self.indication_matches_ce_marking,
            "n_patients": self.n_patients,
            "age_min": self.age_min,
            "age_max": self.age_max,
            "key_inclusion_criteria": self.key_inclusion_criteria,
            "key_exclusion_criteria": self.key_exclusion_criteria,
            "device_studied": self.device_studied,
            "care_setting": self.care_setting.value,
            "operator_training_required": self.operator_training_required,
            "follow_up_months": self.follow_up_months,
            "longest_follow_up_months": self.longest_follow_up_months,
            "dropout_rate_pct": self.dropout_rate_pct,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "endpoint_hierarchy_prespecified": self.endpoint_hierarchy_prespecified,
            "primary_analysis_set": self.primary_analysis_set.value,
            "sample_size_calculation_provided": self.sample_size_calculation_provided,
            "study_countries": self.study_countries,
            "primary_endpoint_met": self.primary_endpoint_met,
            "key_safety_signals": self.key_safety_signals,
        }


# ---------------------------------------------------------------------------
# ComparisonReport — Claim ↔ Study gap analysis
# ---------------------------------------------------------------------------

@dataclass
class ClaimStudyGap:
    dimension: str    # "device", "population", "context", "design", "endpoint"
    severity: str     # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    has_critique: str

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "severity": self.severity,
            "description": self.description,
            "has_critique": self.has_critique,
        }


@dataclass
class ComparisonReport:
    claim_text: str
    device_studied: str
    gaps: list[ClaimStudyGap]
    overall_risk: OverallRisk
    has_critique_simulation: list[str]
    repair_priority: list[str]

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "device_studied": self.device_studied,
            "gaps": [g.to_dict() for g in self.gaps],
            "overall_risk": self.overall_risk.value,
            "has_critique_simulation": self.has_critique_simulation,
            "repair_priority": self.repair_priority,
        }


# ---------------------------------------------------------------------------
# compare_claim_to_study — main comparison function
# ---------------------------------------------------------------------------

def compare_claim_to_study(
    claim: ClinicalClaim,
    study: StudyObject,
    epistemic_output: Optional["EngineOutput"] = None,
) -> ComparisonReport:
    """Compare a ClinicalClaim to a StudyObject and produce a ComparisonReport.

    epistemic_output: if provided (from engine.analyze()), enriches endpoint gap detection
    with classified CausalRole and EndpointNature.
    """
    # Propagate claim_level from epistemic output when not set on the claim object
    if epistemic_output is not None and claim.level is None:
        claim.level = epistemic_output.claim_level

    gaps: list[ClaimStudyGap] = []

    if study.device_alignment:
        gap = _device_gap(study.device_alignment, study)
        if gap:
            gaps.append(gap)

    if study.population_alignment:
        gap = _population_gap(study.population_alignment)
        if gap:
            gaps.append(gap)

    if study.context_alignment:
        gap = _context_gap(study.context_alignment)
        if gap:
            gaps.append(gap)

    gaps.extend(_design_gaps(claim, study))
    gaps.extend(_endpoint_gaps(claim, study, epistemic_output))

    overall_risk = _compute_overall_risk(gaps)
    has_critique = _simulate_has_critique(gaps, claim, study)
    repair_priority = _compute_repair_priority(gaps)

    return ComparisonReport(
        claim_text=claim.text,
        device_studied=study.device_studied,
        gaps=gaps,
        overall_risk=overall_risk,
        has_critique_simulation=has_critique,
        repair_priority=repair_priority,
    )


# ---------------------------------------------------------------------------
# Gap detectors (internal)
# ---------------------------------------------------------------------------

def _device_gap(alignment: DeviceAlignment, study: StudyObject) -> ClaimStudyGap | None:
    m = alignment.device_match_type
    if m == DeviceMatchType.EXACT_DEVICE:
        return None
    severity_map = {
        DeviceMatchType.SAME_FAMILY: "MEDIUM",
        DeviceMatchType.PROXY_DEVICE: "HIGH",
        DeviceMatchType.DIFFERENT_DEVICE: "CRITICAL",
        DeviceMatchType.UNKNOWN: "MEDIUM",
    }
    critique_map = {
        "MEDIUM": (
            "La transposabilité entre générations ou variantes d'un même dispositif ne peut être "
            "présupposée : les propriétés mécaniques, les paramètres de délivrance ou les "
            "caractéristiques d'utilisation peuvent différer de façon cliniquement significative. "
            "Des données démontrant l'équivalence de performance (banc d'essai + données cliniques "
            "comparatives) sont requises pour établir la transposabilité."
        ),
        # PROXY_DEVICE — a *different manufacturer's* device in the same functional
        # category, not a generation of the claimed device's own product line. HAS
        # treats this materially worse than SAME_FAMILY: cf. avis INCEPTIV (Medtronic),
        # which extrapolates freely from its own predecessor INTELLIS (SAME_FAMILY,
        # accepted) but explicitly refuses to extrapolate from EVOKE (Saluda,
        # PROXY_DEVICE) despite EVOKE being "le seul autre stimulateur médullaire"
        # with the same closed-loop mechanism — and cf. SCEWO BRO (avis 7425),
        # rejected outright (SA insuffisant) for relying solely on TOPCHAIR-S
        # (different manufacturer) with no device-specific data of its own.
        "HIGH": (
            "Le dispositif étudié n'est pas une génération ou variante du dispositif "
            "revendiqué, mais un dispositif distinct d'un autre fabricant, seulement "
            "analogue par sa catégorie fonctionnelle ou son mécanisme. HAS ne traite pas "
            "ce cas comme une passerelle intra-produit : sans donnée clinique propre au "
            "dispositif revendiqué, l'intérêt thérapeutique ne peut être établi, quelle "
            "que soit la similarité fonctionnelle apparente avec le dispositif analogue."
        ),
        "CRITICAL": (
            "La preuve générée sur un dispositif ne peut être directement transposée à un "
            "dispositif différent, même de mécanisme proche. Le principe d'évaluation "
            "dispositif-spécifique impose que les données probantes portent sur le dispositif exact "
            "faisant l'objet de la revendication. Toute extrapolation constitue une rupture du "
            "lien preuve-revendication."
        ),
    }
    severity = severity_map[m]
    desc = (
        f"Dispositif étudié ({study.device_studied or alignment.device_description_study}) "
        f"≠ dispositif revendiqué ({alignment.device_description_claim}). "
        f"{alignment.justification}"
    )
    return ClaimStudyGap(
        dimension="device",
        severity=severity,
        description=desc,
        has_critique=critique_map[severity],
    )


def _population_gap(alignment: PopulationAlignment) -> ClaimStudyGap | None:
    m = alignment.population_match_type
    if m == PopulationMatchType.EXACT_INDICATION:
        return None
    severity_map = {
        PopulationMatchType.NARROWER_SUBGROUP: "MEDIUM",
        PopulationMatchType.BROADER_POPULATION: "MEDIUM",
        PopulationMatchType.DIFFERENT_POPULATION: "HIGH",
        PopulationMatchType.UNKNOWN: "LOW",
    }
    critique_map = {
        "MEDIUM": (
            "Un écart entre population étudiée et indication revendiquée fragilise la validité "
            "externe : les résultats obtenus dans une population ne peuvent être extrapolés à une "
            "autre sans justification de la comparabilité clinique (épidémiologie, sévérité, "
            "co-morbidités, traitements concomitants)."
        ),
        "HIGH": (
            "Pour soutenir une revendication dans une indication donnée, les données probantes "
            "doivent porter sur la population cible ou sur une population dont la comparabilité "
            "est formellement démontrée. Des données générées dans une population différente ne "
            "permettent pas d'établir l'évidence dans l'indication revendiquée sans analyse "
            "explicite de transposabilité."
        ),
        "LOW": (
            "L'alignement entre population étudiée et indication revendiquée est incertain. "
            "Une description explicite des critères d'éligibilité et de leur correspondance "
            "avec la population cible est nécessaire pour évaluer la validité externe "
            "de la revendication."
        ),
    }
    severity = severity_map[m]
    desc = (
        f"Population étudiée ({alignment.population_description_study}) "
        f"vs. indication revendiquée ({alignment.population_description_claim}). "
        f"{alignment.justification}"
    )
    return ClaimStudyGap(
        dimension="population",
        severity=severity,
        description=desc,
        has_critique=critique_map[severity],
    )


def _context_gap(alignment: ContextAlignment) -> ClaimStudyGap | None:
    m = alignment.context_match_type
    if m == ContextMatchType.SAME_HEALTHCARE_SYSTEM:
        return None
    severity_map = {
        ContextMatchType.PARTIALLY_COMPARABLE: "LOW",
        ContextMatchType.DIFFERENT_SYSTEM: "MEDIUM",
        ContextMatchType.UNKNOWN: "LOW",
    }
    critique_map = {
        "LOW": (
            "Les données proviennent d'un système de santé partiellement comparable à la France. "
            "Un écart de contexte — même modéré — peut affecter la transposabilité si les "
            "pratiques cliniques, la formation des opérateurs ou le parcours de soins diffèrent "
            "de façon significative."
        ),
        "MEDIUM": (
            "Les données proviennent d'un système de santé substantiellement différent de la "
            "France. L'applicabilité au contexte français ne peut être présupposée : le parcours "
            "de soins, les pratiques cliniques, la formation des opérateurs et le profil "
            "épidémiologique des patients peuvent différer de façon cliniquement significative."
        ),
    }
    severity = severity_map[m]
    desc = (
        f"Contexte de l'étude : {alignment.study_country} "
        f"→ cible : {alignment.target_country}. {alignment.justification}"
    )
    return ClaimStudyGap(
        dimension="context",
        severity=severity,
        description=desc,
        has_critique=critique_map[severity],
    )


def _design_gaps(claim: ClinicalClaim, study: StudyObject) -> list[ClaimStudyGap]:
    gaps = []

    # No comparator for C/D claims — but only penalize when a comparator was
    # realistically feasible. HAS itself does not fault single-arm designs when the
    # only alternative is a fundamentally different, harder-to-randomize-against
    # modality (e.g. open-heart surgery vs. a transcatheter device) or when no
    # alternative treatment exists at all — cf. EDWARDS SAPIEN 3 / EDWARDS ALTERRA
    # (CNEDiMTS avis, code 7873): accepted single-arm, FAVORABLE, no comparator
    # critique — vs. APTA SANS CIMENT (code 7313): single-arm penalized explicitly
    # because a directly comparable hip prosthesis existed and wasn't used.
    if study.has_comparator is False and claim.level in (ClaimLevel.C, ClaimLevel.D):
        if study.comparator_feasibility in (
            ComparatorFeasibility.DIFFERENT_MODALITY,
            ComparatorFeasibility.NO_ALTERNATIVE,
        ):
            gaps.append(ClaimStudyGap(
                dimension="design",
                severity="LOW",
                description=(
                    "Étude sans comparateur pour une revendication d'outcome (niveau C/D), "
                    "mais absence justifiée : aucune alternative de modalité comparable "
                    "n'était raisonnablement disponible pour un essai comparatif."
                ),
                has_critique=(
                    "Le counterfactuel n'est pas observé directement, mais un design "
                    "comparatif n'était pas raisonnablement faisable ou éthique ici — "
                    "la seule alternative identifiée relève d'une modalité de prise en "
                    "charge fondamentalement différente (ex. chirurgie invasive vs. "
                    "dispositif mini-invasif) ou n'existe pas. Un design mono-bras "
                    "comparé à un objectif de performance documenté est acceptable dans "
                    "ce contexte, sous réserve que ce seuil de performance soit "
                    "lui-même correctement justifié."
                ),
            ))
        else:
            gaps.append(ClaimStudyGap(
                dimension="design",
                severity="HIGH",
                description=(
                    "Étude sans comparateur pour une revendication d'outcome (niveau C/D). "
                    "Le counterfactuel n'est pas observé."
                ),
                has_critique=(
                    "Sans groupe contrôle concurrent, l'amélioration observée ne peut être attribuée "
                    "causalement au dispositif : l'histoire naturelle de la pathologie, une régression "
                    "vers la moyenne ou des co-interventions constituent des explications alternatives "
                    "non éliminables. Pour soutenir une revendication d'outcome, le counterfactuel "
                    "doit être observé."
                ),
            ))

    # Population/anatomical usage studied outside the device's CE-marked scope —
    # even a well-conducted study cannot support a claim scoped to the approved
    # indication if the population or anatomical usage it actually covers falls
    # outside the device's CE marking: the evidence bears on a use the device is
    # not certified for, and extrapolation back to the approved scope is not
    # automatic. Same style as the has_comparator rule above: a single explicit
    # boolean check surfaced as a design/regulatory-scope gap.
    if study.indication_matches_ce_marking is False:
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="HIGH",
            description=(
                "Population ou usage anatomique étudié en dehors du périmètre du "
                "marquage CE du dispositif."
            ),
            has_critique=(
                "Lorsque la population étudiée ou l'usage anatomique décrit dans "
                "l'étude excède le périmètre couvert par le marquage CE du "
                "dispositif, les données générées portent sur un usage pour lequel "
                "le dispositif n'est pas certifié : leur transposition à "
                "l'indication revendiquée, elle-même bornée par ce marquage, ne "
                "peut être présupposée. Une analyse explicite de la "
                "transposabilité entre l'usage étudié et le périmètre certifié "
                "est requise, ou une étude conduite dans le périmètre approuvé."
            ),
        ))

    # Single-center (or unknown centricity) study for an outcome claim — effects
    # observed at a single site may reflect local factors (expertise de l'opérateur,
    # sélection des patients, adhérence au protocole propre au centre) rather than
    # an effect generalizable to d'autres centres. Same style as the has_comparator
    # rule above: flagged only for outcome-level claims (C/D).
    if (
        study.is_multicentric is False or study.is_multicentric is None
    ) and claim.level in (ClaimLevel.C, ClaimLevel.D):
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="MEDIUM",
            description=(
                "Étude mono-centrique ou centricité non renseignée pour une "
                "revendication d'outcome (niveau C/D)."
            ),
            has_critique=(
                "Une étude menée dans un seul centre (ou dont le caractère "
                "multicentrique n'est pas documenté) expose à un risque de biais lié "
                "au site : l'expertise de l'opérateur, la sélection des patients et "
                "l'adhérence au protocole propres à ce centre peuvent expliquer tout "
                "ou partie du bénéfice observé, sans que celui-ci soit généralisable "
                "à d'autres centres. Une étude multicentrique, ou à défaut une "
                "justification explicite de la représentativité du centre unique, est "
                "requise pour soutenir une revendication d'outcome."
            ),
        ))

    # Confounding / uncontrolled co-intervention — the observed effect may not be
    # attributable to the device if concomitant treatments are present and neither
    # described nor controlled. cf. avis CNEDiMTS SOMNIO 7781 (SA Insuffisant):
    # HAS's real objection was not the endpoint's causal nature but concomitant
    # hypnotic treatments left undescribed/uncontrolled — a basic causal-identification
    # threat distinct from the endpoint-validity gaps below.
    if (
        study.concomitant_treatments_present is True
        and study.concomitant_treatments_controlled is not True
        and claim.level in (ClaimLevel.C, ClaimLevel.D)
    ):
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="HIGH",
            description=(
                "Traitements concomitants présents dans la population d'étude, non "
                "décrits ou non contrôlés (facteur de confusion)."
                + (f" {study.concomitant_treatments_description}" if study.concomitant_treatments_description else "")
            ),
            has_critique=(
                "Lorsque des traitements concomitants pertinents pour l'indication sont "
                "présents dans la population étudiée sans être décrits, exclus par les "
                "critères d'éligibilité, ou ajustés dans l'analyse, l'effet observé ne peut "
                "être attribué au dispositif seul : le traitement concomitant constitue une "
                "explication causale alternative non éliminée. Une description exhaustive "
                "des co-interventions et, si elles ne peuvent être exclues, un ajustement "
                "statistique pré-spécifié (stratification, covariable, sensibilité) sont "
                "requis pour établir l'attribution causale."
            ),
        ))

    # Open-label with subjective primary endpoint
    claim_primary_subjective = any(
        ep.nature == EndpointNature.SUBJECTIVE and ep.is_primary
        for ep in claim.endpoints
    )
    if (
        claim_primary_subjective
        and study.blinding_level not in (BlindingLevel.DOUBLE_BLIND, BlindingLevel.SHAM_CONTROLLED)
    ):
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="HIGH",
            description=(
                "Critère principal patient-rapporté (PRO/subjectif) sans aveugle ni sham. "
                f"Design : {study.blinding_level.value}."
            ),
            has_critique=(
                "L'association d'un critère patient-rapporté et d'une évaluation en ouvert génère "
                "structurellement des biais d'expectation et d'effet placebo : le patient "
                "connaissant son traitement, ses réponses sont influencées par ses attentes "
                "indépendamment de l'effet réel du dispositif. Ce mécanisme fragilise "
                "l'attribution causale de l'amélioration observée."
            ),
        ))

    # Exploratory design for C/D claim
    if study.study_design == StudyDesign.EXPLORATORY and claim.level in (ClaimLevel.C, ClaimLevel.D):
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="CRITICAL",
            description=(
                "Design exploratoire (série de cas / pilote) pour une revendication d'outcome. "
                "Niveau de preuve rarement jugé suffisant pour ce niveau de revendication."
            ),
            has_critique=(
                "Une étude exploratoire (série de cas, pilote, mono-bras sans hypothèse "
                "pré-enregistrée) génère des hypothèses, elle ne les confirme pas. "
                "Pour soutenir une revendication d'outcome (niveau C/D), un design confirmatoire "
                "avec hypothèse pré-enregistrée, critère primaire défini et calcul de puissance "
                "est requis."
            ),
        ))

    # Single-arm confirmatory design vs. a documented, pre-specified performance
    # objective — weaker than a comparative/randomized design (no concurrent
    # counterfactual), but NOT exploratory: it has a pre-registered success
    # threshold and a justified sample size. cf. EDWARDS SAPIEN 3 / EDWARDS
    # ALTERRA (avis CNEDiMTS 7873): accepted by HAS (SA Suffisant, ASA II) as a
    # pivotal study, not treated as exploratory/pilot.
    if (
        study.study_design == StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL
        and claim.level in (ClaimLevel.C, ClaimLevel.D)
    ):
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="HIGH",
            description=(
                "Étude mono-bras confirmatoire comparée à un objectif de performance "
                "pré-spécifié, pour une revendication d'outcome. Design pivot accepté "
                "en l'absence de comparateur faisable, mais reste plus faible qu'un "
                "design comparatif ou randomisé."
            ),
            has_critique=(
                "Un design mono-bras comparé à un objectif de performance documenté et "
                "pré-enregistré peut soutenir une revendication d'outcome quand aucun "
                "comparateur de modalité comparable n'est disponible — c'est un design "
                "pivot reconnu (FDA/PMA) pour les dispositifs à haut risque. Mais sans "
                "counterfactuel concurrent, l'attribution causale reste plus fragile "
                "qu'avec un comparateur : le seuil de performance retenu doit lui-même "
                "être solidement justifié cliniquement."
            ),
        ))

    # Pre-specified performance goal without documented clinical justification —
    # distinct from the general single-arm-vs-comparator weakness above: even when
    # a single-arm-performance-goal design is itself accepted (no feasible
    # comparator), the numeric success threshold used for "success" must itself be
    # clinically justified (derived from a historical benchmark, clinical consensus,
    # or documented regulatory criterion), not an arbitrary statistical target.
    # cf. avis CNEDiMTS SAPIEN 3/ALTERRA 7873: accepted single-arm pivotal design,
    # but HAS's residual critique was the absence of documented clinical
    # justification for the performance objective itself.
    if (
        study.study_design == StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL
        and study.performance_goal_clinically_justified is not True
        and claim.level in (ClaimLevel.C, ClaimLevel.D)
    ):
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="MEDIUM",
            description=(
                "Seuil de performance pré-spécifié sans justification clinique "
                "documentée pour le seuil de succès retenu."
            ),
            has_critique=(
                "Un design mono-bras comparé à un objectif de performance n'est "
                "valide que si le seuil de succès lui-même est cliniquement "
                "justifié — dérivé d'une donnée de référence historique, d'un "
                "consensus clinique ou d'un critère réglementaire documenté. Un "
                "seuil statistique non justifié cliniquement ne permet pas "
                "d'établir qu'un résultat au-dessus du seuil équivaut à un "
                "bénéfice clinique pertinent."
            ),
        ))

    # Non-randomized comparative study for outcome claim
    if (
        not study.is_randomized
        and study.has_comparator is True
        and claim.level in (ClaimLevel.C, ClaimLevel.D)
        and study.study_design not in (StudyDesign.MATCHED_OBSERVATIONAL,)
    ):
        gaps.append(ClaimStudyGap(
            dimension="design",
            severity="MEDIUM",
            description=(
                "Étude comparative non randomisée pour une revendication d'outcome. "
                "Risque de biais de sélection non contrôlé."
            ),
            has_critique=(
                "Dans une étude comparative non randomisée, la comparabilité des groupes n'est "
                "pas garantie par le design. Sans ajustement pré-spécifié sur les facteurs de "
                "confusion mesurés (score de propension, IPTW ou régression multivariée), un "
                "biais de sélection résiduel ne peut être exclu et la comparaison ne permet pas "
                "de conclusion causale robuste."
            ),
        ))

    # Follow-up adequacy — two tiers
    if study.follow_up_months is not None and claim.level in (ClaimLevel.C, ClaimLevel.D):
        fu = study.follow_up_months
        if fu < 12:
            gaps.append(ClaimStudyGap(
                dimension="design",
                severity="MEDIUM",
                description=(
                    f"Suivi de {fu} mois insuffisant pour confirmer la durabilité du bénéfice "
                    "sur un critère d'outcome dans une affection chronique."
                ),
                has_critique=(
                    "Pour une revendication d'outcome sur une affection chronique, un suivi "
                    "inférieur à 12 mois ne permet pas d'établir la durabilité du bénéfice : "
                    "les effets à court terme peuvent s'estomper, des complications tardives "
                    "peuvent émerger, et la période couverte n'est pas cliniquement significative. "
                    "Un suivi d'au moins 12 mois est requis ; 24 mois pour les pathologies chroniques."
                ),
            ))
        elif fu < 24:
            gaps.append(ClaimStudyGap(
                dimension="design",
                severity="LOW",
                description=(
                    f"Suivi de {fu} mois : durabilité à long terme (≥ 24 mois) non confirmée. "
                    "La durabilité reste à établir sur des données complémentaires."
                ),
                has_critique=(
                    "Pour les affections chroniques, un suivi de 12 à 24 mois laisse ouverte "
                    "la question de la durabilité à long terme : le maintien de l'effet au-delà "
                    "de 24 mois, le taux de ré-intervention et la sécurité long terme restent "
                    "à confirmer. Des données complémentaires à 24 mois sont nécessaires pour "
                    "établir la durabilité du bénéfice."
                ),
            ))

    return gaps


def _endpoint_gaps(
    claim: ClinicalClaim,
    study: StudyObject,
    epistemic_output: Optional["EngineOutput"],
) -> list[ClaimStudyGap]:
    gaps = []

    # Use epistemic output for classified endpoint analysis
    if epistemic_output:
        for bd in epistemic_output.bias_flags:
            if bd.flag == BiasFlag.CIRCULARITY_RISK:
                gaps.append(ClaimStudyGap(
                    dimension="endpoint",
                    severity="CRITICAL",
                    description=(
                        "Critère principal circulaire : le dispositif mesure ce qu'il traite. "
                        "L'ascertainment de l'outcome n'est pas indépendant du traitement."
                    ),
                    has_critique=(
                        "Un critère circulaire viole le principe d'indépendance de l'ascertainment : "
                        "le dispositif ne peut être simultanément l'intervention évaluée et "
                        "l'instrument de détection de son propre effet. Les événements ainsi "
                        "détectés dépendent structurellement de la sensibilité du dispositif, "
                        "non de l'évolution clinique réelle du patient. "
                        "Un critère strictement indépendant (données administratives, CEC) est requis."
                    ),
                ))
            elif bd.flag == BiasFlag.SURROGATE_RISK:
                # Check if any primary endpoint is marked feasibility-accepted
                _primary_eps = [ep for ep in claim.endpoints if ep.is_primary]
                _is_feasibility = any(
                    getattr(ep, "is_feasibility_accepted_surrogate", False)
                    for ep in _primary_eps
                )
                if _is_feasibility:
                    gaps.append(ClaimStudyGap(
                        dimension="endpoint",
                        severity="MEDIUM",
                        description=(
                            "Critère principal = surrogate accepté par défaut de faisabilité "
                            "(endpoint clinique dur non réalisable dans ce contexte). "
                            "Données post-marché requises pour confirmer le bénéfice clinique."
                        ),
                        has_critique=(
                            "Lorsqu'un endpoint clinique dur n'est pas réalisable à court terme, "
                            "un surrogate peut être accepté à titre conditionnel, sous réserve que "
                            "son lien avec le bénéfice clinique soit biologiquement plausible. "
                            "Cette acceptation conditionnelle impose un programme de suivi "
                            "post-marché permettant de confirmer ultérieurement le bénéfice sur "
                            "des critères cliniques durs (registre, PMSI/SNDS, données de "
                            "morbi-mortalité à 36–60 mois)."
                        ),
                    ))
                else:
                    _has_known_surrogate = any(
                        not getattr(ep, "is_validated_surrogate", False)
                        and is_known_validated_surrogate(ep)
                        for ep in _primary_eps
                    )
                    _critique = (
                        "Un surrogate non formellement validé par FDA/EMA/HAS dans cette "
                        "indication ne peut être présupposé prédictif du bénéfice clinique : "
                        "la corrélation surrogate→outcome doit être démontrée par des essais "
                        "randomisés dans l'indication précise. En l'absence de cette "
                        "validation, le lien causal entre amélioration du surrogate et "
                        "bénéfice patient reste une hypothèse non démontrée."
                    )
                    if _has_known_surrogate:
                        _critique += (
                            " Ce critère évoque un surrogate largement documenté dans la "
                            "littérature (ex. HbA1c, LDL-C, pression artérielle) : si sa "
                            "validation est établie pour cette indication et cette "
                            "population précises, renseigner is_validated_surrogate=True "
                            "sur l'endpoint plutôt que de laisser ce flag manuel non coché "
                            "par défaut."
                        )
                    gaps.append(ClaimStudyGap(
                        dimension="endpoint",
                        severity="HIGH",
                        description=(
                            "Critère principal = surrogate non validé réglementairement "
                            "dans cette indication."
                        ),
                        has_critique=_critique,
                    ))
            elif bd.flag == BiasFlag.DETECTION_BIAS:
                gaps.append(ClaimStudyGap(
                    dimension="endpoint",
                    severity="HIGH",
                    description=(
                        "Biais de détection : l'ascertainment de l'outcome est influencé "
                        "par le dispositif (alerte, détection, monitoring)."
                    ),
                    has_critique=(
                        "Un endpoint de détection présente un biais structurel : la fréquence "
                        "des événements détectés est une fonction de la sensibilité du dispositif, "
                        "non uniquement de l'évolution clinique du patient. L'augmentation du "
                        "nombre d'événements détectés peut refléter une meilleure surveillance "
                        "sans traduire un bénéfice clinique réel. Un critère indépendant du "
                        "dispositif (CEC, données administratives) est requis pour isoler "
                        "l'effet clinique."
                    ),
                ))
            elif bd.flag == BiasFlag.PROTOCOL_FIXED_ENDPOINT:
                gaps.append(ClaimStudyGap(
                    dimension="endpoint",
                    severity="HIGH",
                    description=(
                        "Critère principal comparatif dont la valeur, dans le bras du "
                        "dispositif évalué, est fixée à l'avance par le protocole (paramètre "
                        "de design) plutôt que mesurée comme résultat."
                    ),
                    has_critique=(
                        "Lorsque la valeur d'un critère de jugement comparatif est fixée à "
                        "l'avance par le protocole dans le bras du dispositif évalué, alors "
                        "qu'elle est réellement mesurée dans le bras comparateur, toute "
                        "« supériorité » observée sur ce critère est tautologique par "
                        "construction : elle reflète le paramètre de design choisi, pas un "
                        "effet causal du dispositif. Un critère dont la valeur est mesurée "
                        "de façon symétrique dans les deux bras est requis pour établir une "
                        "comparaison interprétable."
                    ),
                ))
            elif bd.flag == BiasFlag.NO_COMPARATOR:
                pass  # covered in design gaps

    # Endpoint multiplicity without hierarchy — multiple co-primary endpoints inflate
    # the type-I error rate unless a multiplicity-control procedure (gatekeeping,
    # hierarchical testing, alpha-splitting) is pre-specified. cf. avis CNEDiMTS
    # ENTERRA II 7254: accepted, but with a downgraded ASA specifically because of
    # endpoint multiplicity without hierarchy — a statistical-rigor problem distinct
    # from any individual endpoint's causal validity.
    primary_study_eps_for_multiplicity = [e for e in study.endpoints if e.is_primary]
    if (
        len(primary_study_eps_for_multiplicity) > 1
        and study.endpoint_hierarchy_prespecified is not True
    ):
        gaps.append(ClaimStudyGap(
            dimension="endpoint",
            severity="MEDIUM",
            description=(
                f"Multiplicité des critères de jugement principaux "
                f"({len(primary_study_eps_for_multiplicity)} critères co-primaires) "
                "sans hiérarchisation statistique pré-spécifiée."
            ),
            has_critique=(
                "Plusieurs critères sont désignés co-primaires sans procédure de "
                "contrôle de la multiplicité pré-spécifiée (hiérarchisation séquentielle, "
                "gatekeeping, répartition du risque alpha) : le risque d'erreur de première "
                "espèce global est inflaté au-delà du seuil nominal, et une conclusion de "
                "succès sur l'un des critères ne peut être interprétée isolément. Une "
                "hiérarchie de test pré-spécifiée dans le plan d'analyse statistique, "
                "verrouillée avant la levée de l'aveugle, est requise."
            ),
        ))

    # Check study-level endpoint adjudication gap (independent of epistemic output)
    primary_study_eps = [e for e in study.endpoints if e.is_primary]
    if primary_study_eps:
        has_objective_non_adjudicated = any(
            not e.is_independently_adjudicated
            for e in primary_study_eps
        )
        claim_has_objective_independent = any(
            ep.nature == EndpointNature.OBJECTIVE
            and ep.causal_role != CausalRole.CIRCULAR
            and ep.is_primary
            for ep in claim.endpoints
        )
        if has_objective_non_adjudicated and claim_has_objective_independent:
            gaps.append(ClaimStudyGap(
                dimension="endpoint",
                severity="MEDIUM",
                description=(
                    "Critère objectif principal sans adjudication indépendante documentée "
                    "(pas de CEC mentionné)."
                ),
                has_critique=(
                    "Pour les critères objectifs composites ou événementiels, l'absence de comité "
                    "d'adjudication indépendant expose à un biais de classification : les "
                    "investigateurs, non en aveugle du traitement, peuvent classer différemment "
                    "les événements selon le groupe. Sans CEC, le risque de biais de "
                    "classification est non contrôlé et l'objectivité de la mesure ne peut "
                    "être garantie."
                ),
            ))

    return gaps


def _compute_overall_risk(gaps: list[ClaimStudyGap]) -> OverallRisk:
    if any(g.severity == "CRITICAL" for g in gaps):
        return OverallRisk.CRITICAL
    high_count = sum(1 for g in gaps if g.severity == "HIGH")
    if high_count >= 2:
        return OverallRisk.CRITICAL
    if high_count == 1:
        return OverallRisk.HIGH
    if any(g.severity == "MEDIUM" for g in gaps):
        return OverallRisk.MEDIUM
    if gaps:
        return OverallRisk.LOW
    return OverallRisk.LOW


def _simulate_has_critique(
    gaps: list[ClaimStudyGap],
    claim: ClinicalClaim,
    study: StudyObject,
) -> list[str]:
    critiques = [g.has_critique for g in gaps if g.has_critique]

    if len(gaps) >= 3:
        critiques.append(
            "L'accumulation de plusieurs faiblesses méthodologiques (design, endpoint, alignement) "
            "rend difficile l'attribution du bénéfice observé au dispositif. "
            "La commission recommandera une étude de meilleur niveau de preuve avant inscription."
        )

    if not critiques:
        critiques.append(
            "Aucun gap majeur identifié entre l'étude soumise et la revendication. "
            "Le dossier est méthodologiquement cohérent."
        )

    return critiques


def _compute_repair_priority(gaps: list[ClaimStudyGap]) -> list[str]:
    _order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_gaps = sorted(gaps, key=lambda g: _order.get(g.severity, 4))
    return [g.description for g in sorted_gaps]


# ---------------------------------------------------------------------------
# enrich_claim_with_study_object — merge StudyObject into ClinicalClaim
# ---------------------------------------------------------------------------

def enrich_claim_with_study_object(
    claim: ClinicalClaim,
    study: StudyObject,
) -> ClinicalClaim:
    """Merge study object fields into a ClinicalClaim in-place. Returns same claim."""
    if study.study_design is not None:
        claim.study_design = study.study_design
    if study.n_patients is not None:
        claim.n_patients = study.n_patients
    if study.has_comparator is not None:
        claim.has_comparator = study.has_comparator
    if study.comparator_feasibility != ComparatorFeasibility.UNKNOWN:
        claim.comparator_feasibility = study.comparator_feasibility
    if study.indication_matches_ce_marking is not None:
        claim.indication_matches_ce_marking = study.indication_matches_ce_marking
    if study.follow_up_months is not None:
        claim.follow_up_months = study.follow_up_months
    if study.study_countries:
        claim.study_countries = study.study_countries

    # Replace the claim's endpoints (guessed from the bare claim sentence, before the
    # study text was available) with the study's actual endpoints — now that the study
    # parser classifies nature/causal_role too, this is what the epistemic core should
    # reason about, not a placeholder invented without seeing the submitted evidence.
    if study.endpoints:
        claim.endpoints = [
            Endpoint(
                name=ep.name,
                nature=ep.nature,
                causal_role=ep.causal_role,
                is_primary=ep.is_primary,
                is_validated_surrogate=ep.is_validated_surrogate,
                is_feasibility_accepted_surrogate=ep.is_feasibility_accepted_surrogate,
                is_independently_adjudicated=ep.is_independently_adjudicated,
                value_fixed_by_protocol=ep.value_fixed_by_protocol,
            )
            for ep in study.endpoints
        ]

    if study.device_alignment is not None:
        claim.device_alignment = study.device_alignment
    if study.population_alignment is not None:
        claim.population_alignment = study.population_alignment
    if study.context_alignment is not None:
        claim.context_alignment = study.context_alignment

    return claim
