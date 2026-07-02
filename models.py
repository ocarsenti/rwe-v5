"""Core domain models for the Causal Design Repair Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Core enums
# ---------------------------------------------------------------------------

class ClaimLevel(Enum):
    A = "MECHANISM"
    B = "PROCESS"
    C = "OUTCOME"
    D = "COMPLETE_CHAIN"


class ComparatorFeasibility(Enum):
    """Whether a concurrent comparator was realistically available for this indication.

    HAS does not penalize single-arm designs uniformly: it distinguishes a comparator
    that exists and is of a similar-enough modality to make a head-to-head comparison
    feasible/ethical (FEASIBLE — e.g. another hip prosthesis for a hip prosthesis) from
    a case where the only alternative is a fundamentally different, harder-to-randomize-
    against modality (DIFFERENT_MODALITY — e.g. open-heart surgery vs. a transcatheter
    device) or where no alternative treatment exists at all (NO_ALTERNATIVE).
    """
    FEASIBLE = "FEASIBLE"
    DIFFERENT_MODALITY = "DIFFERENT_MODALITY"
    NO_ALTERNATIVE = "NO_ALTERNATIVE"
    UNKNOWN = "UNKNOWN"


class EndpointNature(Enum):
    OBJECTIVE = "OBJECTIVE"
    SUBJECTIVE = "SUBJECTIVE"
    INSTRUMENTED = "INSTRUMENTED"


class CausalRole(Enum):
    INDEPENDENT = "INDEPENDENT"
    MEDIATED = "MEDIATED"
    CIRCULAR = "CIRCULAR"


class CausalStructure(Enum):
    DIRECT = "DIRECT"
    MEDIATED = "MEDIATED"
    CIRCULAR = "CIRCULAR"
    INVALID = "INVALID"


class BiasFlag(Enum):
    CIRCULARITY_RISK = "CIRCULARITY_RISK"
    DETECTION_BIAS = "DETECTION_BIAS"
    PERCEPTION_BIAS = "PERCEPTION_BIAS"
    MEDIATION_GAP = "MEDIATION_GAP"
    PROCESS_TAUTOLOGY = "PROCESS_TAUTOLOGY"
    SURROGATE_RISK = "SURROGATE_RISK"
    ADJUDICATION_RISK = "ADJUDICATION_RISK"
    NO_COMPARATOR = "NO_COMPARATOR"


class RepairType(Enum):
    ENDPOINT_REPLACEMENT = "ENDPOINT_REPLACEMENT"
    ENDPOINT_ADDITION = "ENDPOINT_ADDITION"
    CLAIM_REFORMULATION = "CLAIM_REFORMULATION"
    DESIGN_CHANGE = "DESIGN_CHANGE"


class StudyDesign(Enum):
    RCT = "RCT"
    SHAM_RCT = "SHAM_RCT"
    PRAGMATIC_RCT = "PRAGMATIC_RCT"
    COHORT = "COHORT"
    ITS = "ITS"
    BEFORE_AFTER = "BEFORE_AFTER"
    MATCHED_OBSERVATIONAL = "MATCHED_OBSERVATIONAL"
    # Single-arm, confirmatory, pre-specified/documented performance objective
    # (FDA/PMA "Objective Performance Criterion" pathway) — distinct from
    # EXPLORATORY: has a pre-registered success threshold and justified sample
    # size, used to support a confirmatory claim rather than to generate one.
    # cf. EDWARDS SAPIEN 3 / EDWARDS ALTERRA (avis CNEDiMTS 7873): 61-patient
    # pivotal study, primary endpoint compared to a documented performance
    # objective, accepted by HAS (SA Suffisant) — not treated as exploratory.
    SINGLE_ARM_PERFORMANCE_GOAL = "SINGLE_ARM_PERFORMANCE_GOAL"
    EXPLORATORY = "EXPLORATORY"
    NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE"


class Mode(Enum):
    REVIEW = "REVIEW"
    DESIGN = "DESIGN"


class EvidenceDesignType(Enum):
    INDIVIDUAL_RCT = "INDIVIDUAL_RCT"
    PRAGMATIC_RCT = "PRAGMATIC_RCT"
    CLUSTER_RCT = "CLUSTER_RCT"
    REGISTRY_RCT = "REGISTRY_RCT"
    STEPPED_WEDGE = "STEPPED_WEDGE"
    CONTROLLED_ITS = "CONTROLLED_ITS"
    TARGET_TRIAL_EMULATION = "TARGET_TRIAL_EMULATION"
    EXTERNAL_CONTROL_COHORT = "EXTERNAL_CONTROL_COHORT"


# ---------------------------------------------------------------------------
# V2 repair enums
# ---------------------------------------------------------------------------

class FailureArchetype(Enum):
    DETECTION_LOOP = "DETECTION_LOOP_FAILURE"
    MEASUREMENT_CIRCULARITY = "MEASUREMENT_CIRCULARITY_FAILURE"
    SUBJECTIVE_ENDPOINT = "SUBJECTIVE_ENDPOINT_FAILURE"
    MEDIATION_GAP = "MEDIATION_GAP_FAILURE"
    PROCESS_TAUTOLOGY = "PROCESS_TAUTOLOGY_FAILURE"


class EndpointTier(Enum):
    INDEPENDENT = "INDEPENDENT"
    DEVICE_INFLUENCED = "DEVICE_INFLUENCED"
    PROXY = "PROXY"
    SUBJECTIVE = "SUBJECTIVE"


class EndpointRepairKind(Enum):
    HARD_CLINICAL = "HARD_CLINICAL"
    SOFT_CLINICAL = "SOFT_CLINICAL"
    UTILIZATION_INDEPENDENT = "UTILIZATION_INDEPENDENT"
    SURVIVAL = "SURVIVAL"
    BIOMARKER = "BIOMARKER"


class EndpointRank(Enum):
    GOLD = "GOLD_STANDARD"
    ACCEPTABLE = "ACCEPTABLE_SECONDARY"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# V3 Gold Dataset / Regulatory Labeling enums
# ---------------------------------------------------------------------------

class EndpointStatus(Enum):
    ACCEPTABLE = "ACCEPTABLE"
    ACCEPTABLE_WITH_CONDITIONS = "ACCEPTABLE_WITH_CONDITIONS"
    INVALID_AS_PRIMARY_ONLY = "INVALID_AS_PRIMARY_ONLY"
    INVALID_UNLESS_REDEFINED = "INVALID_UNLESS_REDEFINED"


class IssueType(Enum):
    MEASUREMENT_CIRCULARITY = "MEASUREMENT_CIRCULARITY"
    CARE_PATHWAY_BIAS = "CARE_PATHWAY_BIAS"
    DETECTION_ACCELERATION = "DETECTION_ACCELERATION"
    SUBJECTIVE_ENDPOINT_BIAS = "SUBJECTIVE_ENDPOINT_BIAS"


class RepairEndpointType(Enum):
    HARD_CLINICAL = "HARD_CLINICAL"
    UTILIZATION = "UTILIZATION"
    BIOMARKER = "BIOMARKER"
    PROM = "PROM"
    SURVIVAL = "SURVIVAL"


class RegulatoryStrength(Enum):
    PRIMARY_CANDIDATE = "PRIMARY_CANDIDATE"
    SECONDARY_ONLY = "SECONDARY_ONLY"
    EXPLORATORY = "EXPLORATORY"


class DesignTypeRequired(Enum):
    RCT = "RCT"
    PRAGMATIC_RCT = "PRAGMATIC_RCT"
    REGISTRY_RCT = "REGISTRY_RCT"
    OBSERVATIONAL = "OBSERVATIONAL"


class BiasThreshold(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FinalRegulatoryStatus(Enum):
    ACCEPTABLE_PRIMARY_WITH_CONDITIONS = "ACCEPTABLE_PRIMARY_WITH_CONDITIONS"
    ACCEPTABLE_SECONDARY_ONLY = "ACCEPTABLE_SECONDARY_ONLY"
    ACCEPTABLE_WITH_REDESIGN = "ACCEPTABLE_WITH_REDESIGN"
    INVALID_AS_PRIMARY_ENDPOINT_ONLY = "INVALID_AS_PRIMARY_ENDPOINT_ONLY"
    REJECTED_UNLESS_EXTERNAL_VALIDATION = "REJECTED_UNLESS_EXTERNAL_VALIDATION"


# ---------------------------------------------------------------------------
# V3 Gold Dataset dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DeviceContext:
    name: str
    domain: str
    intervention_type: str

    def to_dict(self) -> dict:
        return {"name": self.name, "domain": self.domain, "intervention_type": self.intervention_type}


@dataclass
class CausalGraphSummary:
    summary: str
    mediators: list[str]
    measurement_influence_paths: list[str]

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "mediators": self.mediators,
            "measurement_influence_paths": self.measurement_influence_paths,
        }


@dataclass
class IssueDetection:
    primary_issue_type: IssueType
    severity_score: float

    def to_dict(self) -> dict:
        return {"primary_issue_type": self.primary_issue_type.value, "severity_score": self.severity_score}


@dataclass
class OriginalEndpointAssessment:
    name: str
    status: EndpointStatus
    failure_mode: str

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status.value, "failure_mode": self.failure_mode}


@dataclass
class RepairEndpointGold:
    endpoint_name: str
    type: RepairEndpointType
    robustness_score: float
    regulatory_strength: RegulatoryStrength

    def to_dict(self) -> dict:
        return {
            "endpoint_name": self.endpoint_name,
            "type": self.type.value,
            "robustness_score": self.robustness_score,
            "regulatory_strength": self.regulatory_strength.value,
        }


@dataclass
class EndpointGoldAnalysis:
    original_endpoint: OriginalEndpointAssessment
    repair_endpoints: list[RepairEndpointGold]

    def to_dict(self) -> dict:
        return {
            "original_endpoint": self.original_endpoint.to_dict(),
            "repair_endpoints": [r.to_dict() for r in self.repair_endpoints],
        }


@dataclass
class RegulatoryConditions:
    blinding_required: bool
    independent_adjudication_required: bool
    external_data_source_required: bool
    endpoint_repositioning: str
    design_type_required: DesignTypeRequired
    acceptable_bias_threshold: BiasThreshold

    def to_dict(self) -> dict:
        return {
            "blinding_required": self.blinding_required,
            "independent_adjudication_required": self.independent_adjudication_required,
            "external_data_source_required": self.external_data_source_required,
            "endpoint_repositioning": self.endpoint_repositioning,
            "design_type_required": self.design_type_required.value,
            "acceptable_bias_threshold": self.acceptable_bias_threshold.value,
        }


@dataclass
class GoldCaseOutput:
    case_id: str
    device_context: DeviceContext
    causal_graph: CausalGraphSummary
    issue_detection: IssueDetection
    endpoint_analyses: list[EndpointGoldAnalysis]
    regulatory_conditions: list[RegulatoryConditions]
    has_interpretation: str
    final_regulatory_status: FinalRegulatoryStatus

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "device_context": self.device_context.to_dict(),
            "causal_graph": self.causal_graph.to_dict(),
            "issue_detection": self.issue_detection.to_dict(),
            "endpoint_analyses": [ea.to_dict() for ea in self.endpoint_analyses],
            "regulatory_conditions": [rc.to_dict() for rc in self.regulatory_conditions],
            "has_interpretation": self.has_interpretation,
            "final_regulatory_status": self.final_regulatory_status.value,
        }


@dataclass
class GoldDatasetRow:
    device: str
    original_endpoint: str
    failure_type: str
    severity: float
    acceptable_primary: str
    required_design: str
    best_repair_endpoint: str
    regulatory_risk_level: str

    def to_dict(self) -> dict:
        return {
            "device": self.device,
            "original_endpoint": self.original_endpoint,
            "failure_type": self.failure_type,
            "severity": self.severity,
            "acceptable_primary": self.acceptable_primary,
            "required_design": self.required_design,
            "best_repair_endpoint": self.best_repair_endpoint,
            "regulatory_risk_level": self.regulatory_risk_level,
        }


# ---------------------------------------------------------------------------
# V4 Design Mode dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DAGEdge:
    source: str
    target: str
    edge_type: str = "CAUSAL"

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "edge_type": self.edge_type}


@dataclass
class TargetDAG:
    intervention: str
    mediators: list[str]
    outcomes: list[str]
    prohibited_outcomes: list[str]
    edges: list[DAGEdge]

    def to_dict(self) -> dict:
        return {
            "intervention": self.intervention,
            "mediators": self.mediators,
            "outcomes": self.outcomes,
            "prohibited_outcomes": self.prohibited_outcomes,
            "edges": [e.to_dict() for e in self.edges],
        }


@dataclass
class IdentificationRequirements:
    randomization_needed: bool
    blinding_needed: bool
    adjudication_needed: bool
    external_data_needed: bool
    mediator_measurement_needed: bool
    minimum_design_strength: float

    def to_dict(self) -> dict:
        return {
            "randomization_needed": self.randomization_needed,
            "blinding_needed": self.blinding_needed,
            "adjudication_needed": self.adjudication_needed,
            "external_data_needed": self.external_data_needed,
            "mediator_measurement_needed": self.mediator_measurement_needed,
            "minimum_design_strength": self.minimum_design_strength,
        }


@dataclass
class EndpointFamily:
    family_name: str
    endpoints: list[str]
    independence_from_device: float
    regulatory_weight: str

    def to_dict(self) -> dict:
        return {
            "family_name": self.family_name,
            "endpoints": self.endpoints,
            "independence_from_device": self.independence_from_device,
            "regulatory_weight": self.regulatory_weight,
        }


@dataclass
class DesignCandidate:
    design_type: EvidenceDesignType
    design_name: str
    causal_strength: float
    expected_biases: list[str]
    endpoint_compatibility: list[str]
    feasibility: float
    has_acceptability: float

    def to_dict(self) -> dict:
        return {
            "design_type": self.design_type.value,
            "design_name": self.design_name,
            "causal_strength": self.causal_strength,
            "expected_biases": self.expected_biases,
            "endpoint_compatibility": self.endpoint_compatibility,
            "feasibility": self.feasibility,
            "has_acceptability": self.has_acceptability,
        }


@dataclass
class DesignSpace:
    candidates: list[DesignCandidate]

    def to_dict(self) -> dict:
        return {"candidates": [c.to_dict() for c in self.candidates]}


@dataclass
class ManifoldPoint:
    design: DesignCandidate
    identification_score: float
    bias_risk: float
    operational_complexity: float
    regulatory_acceptability: float

    def to_dict(self) -> dict:
        return {
            "design": self.design.design_name,
            "design_type": self.design.design_type.value,
            "identification_score": self.identification_score,
            "bias_risk": self.bias_risk,
            "operational_complexity": self.operational_complexity,
            "regulatory_acceptability": self.regulatory_acceptability,
        }


@dataclass
class RegulatoryManifold:
    points: list[ManifoldPoint]

    def to_dict(self) -> dict:
        return {"points": [p.to_dict() for p in self.points]}

    def best_point(self) -> ManifoldPoint:
        return max(self.points, key=lambda p: p.regulatory_acceptability - p.bias_risk)


@dataclass
class DesignModeOutput:
    mode: str
    claim_text: str
    intervention: str
    domain: str
    target_dag: TargetDAG
    identification: IdentificationRequirements
    endpoint_families: list[EndpointFamily]
    design_space: DesignSpace
    regulatory_manifold: RegulatoryManifold
    regulatory_strategy: str
    epistemic_manifold: Optional["EpistemicManifoldOutput"] = None

    def to_dict(self) -> dict:
        d = {
            "mode": self.mode,
            "claim_text": self.claim_text,
            "intervention": self.intervention,
            "domain": self.domain,
            "target_dag": self.target_dag.to_dict(),
            "identification": self.identification.to_dict(),
            "endpoint_families": [f.to_dict() for f in self.endpoint_families],
            "design_space": self.design_space.to_dict(),
            "regulatory_manifold": self.regulatory_manifold.to_dict(),
            "regulatory_strategy": self.regulatory_strategy,
        }
        if self.epistemic_manifold is not None:
            d["epistemic_manifold"] = self.epistemic_manifold.to_dict()
        return d


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Endpoint:
    name: str
    nature: EndpointNature
    causal_role: CausalRole
    is_primary: bool = False
    description: str = ""
    is_validated_surrogate: bool = False
    is_feasibility_accepted_surrogate: bool = False
    is_independently_adjudicated: bool = False


@dataclass
class ClinicalClaim:
    text: str
    intervention: str
    level: Optional[ClaimLevel] = None
    endpoints: list[Endpoint] = field(default_factory=list)
    domain: str = ""
    device_alignment: Optional["DeviceAlignment"] = None
    population_alignment: Optional["PopulationAlignment"] = None
    context_alignment: Optional["ContextAlignment"] = None
    study_design: Optional["StudyDesign"] = None
    n_patients: Optional[int] = None
    has_comparator: Optional[bool] = None
    comparator_feasibility: "ComparatorFeasibility" = ComparatorFeasibility.UNKNOWN
    follow_up_months: Optional[float] = None
    study_countries: list[str] = field(default_factory=list)


@dataclass
class BiasDetection:
    flag: BiasFlag
    severity: str  # HIGH, MEDIUM, LOW
    detail: str


@dataclass
class RepairStrategy:
    type: RepairType
    description: str
    effect_on_causality: str


@dataclass
class DesignRecommendation:
    primary_design: StudyDesign
    alternatives: list[StudyDesign] = field(default_factory=list)
    rationale: str = ""


@dataclass
class EndpointAnalysis:
    endpoint: Endpoint
    nature: EndpointNature
    causal_role: CausalRole
    flags: list[BiasFlag] = field(default_factory=list)


# ---------------------------------------------------------------------------
# V2 repair dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FailureDiagnosis:
    failure_type: FailureArchetype
    severity: float
    is_rct_valid: str  # "true", "false", "conditional"

    def to_dict(self) -> dict:
        return {
            "failure_type": self.failure_type.value,
            "severity": self.severity,
            "is_RCT_valid": self.is_rct_valid,
        }


@dataclass
class EndpointRepairCandidate:
    endpoint: str
    type: EndpointRepairKind
    causal_role: str  # PRIMARY, SECONDARY, MEDIATOR
    why_valid: str
    risk_reduction: list[str]

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "type": self.type.value,
            "causal_role": self.causal_role,
            "why_valid": self.why_valid,
            "risk_reduction": self.risk_reduction,
        }


@dataclass
class EndpointRepairBlock:
    original_endpoint: str
    failure_reason: str
    repairs: list[EndpointRepairCandidate]

    def to_dict(self) -> dict:
        return {
            "original_endpoint": self.original_endpoint,
            "failure_reason": self.failure_reason,
            "repairs": [r.to_dict() for r in self.repairs],
        }


@dataclass
class CausalChainStep:
    node: str
    role: str  # INTERVENTION, MEDIATOR, OUTCOME
    measurable: bool
    requires_mediation_assumption: bool
    rct_valid_at_step: bool

    def to_dict(self) -> dict:
        return {
            "node": self.node,
            "role": self.role,
            "measurable": self.measurable,
            "requires_mediation_assumption": self.requires_mediation_assumption,
            "rct_valid_at_step": self.rct_valid_at_step,
        }


@dataclass
class DesignJustification:
    design: StudyDesign
    why_valid: str
    failures_prevented: list[str]

    def to_dict(self) -> dict:
        return {
            "design": self.design.value,
            "why_valid": self.why_valid,
            "failures_prevented": self.failures_prevented,
        }


@dataclass
class RankedEndpoint:
    endpoint: str
    rank: EndpointRank
    reason: str
    bias_score: float

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "rank": self.rank.value,
            "reason": self.reason,
            "bias_score": self.bias_score,
        }


@dataclass
class RepairPlanV2:
    status: str  # "REPAIRABLE" or "NON_REPAIRABLE"
    failure_diagnosis: FailureDiagnosis
    endpoint_repairs: list[EndpointRepairBlock]
    causal_chain: list[CausalChainStep]
    recommended_designs: list[DesignJustification]
    endpoint_ranking: list[RankedEndpoint]
    problem_summary: str
    non_repairable_reason: str = ""

    def to_dict(self) -> dict:
        d = {
            "status": self.status,
            "failure_diagnosis": self.failure_diagnosis.to_dict(),
            "endpoint_repairs": [er.to_dict() for er in self.endpoint_repairs],
            "causal_chain": [cs.to_dict() for cs in self.causal_chain],
            "recommended_designs": [dj.to_dict() for dj in self.recommended_designs],
            "endpoint_ranking": [re.to_dict() for re in self.endpoint_ranking],
            "problem_summary": self.problem_summary,
        }
        if self.status == "NON_REPAIRABLE":
            d["reason"] = self.non_repairable_reason
            d["implication"] = "no causal inference possible under current design space"
        return d


# ---------------------------------------------------------------------------
# Legacy compat — keep RepairPlan for backward-compat serialization
# ---------------------------------------------------------------------------

@dataclass
class RepairPlan:
    problem_summary: str
    failure_modes: list[str]
    repair_strategies: list[RepairStrategy]
    recommended_minimal_change: str
    resulting_designs: list[StudyDesign]


# ---------------------------------------------------------------------------
# Engine output
# ---------------------------------------------------------------------------

@dataclass
class EngineOutput:
    claim_level: ClaimLevel
    endpoint_analysis: list[EndpointAnalysis]
    causal_structure: CausalStructure
    bias_flags: list[BiasDetection]
    design_recommendation: DesignRecommendation
    repair_plan: Optional[RepairPlan]
    repair_plan_v2: Optional[RepairPlanV2]
    regulatory_readout: str
    manifold_position: Optional["EpistemicManifoldPosition"] = None
    repair_delta: Optional["RepairManifoldDelta"] = None
    cas_output: Optional["CASOutput"] = None

    def to_dict(self) -> dict:
        d = {
            "claim_level": self.claim_level.value,
            "endpoint_analysis": [
                {
                    "name": ea.endpoint.name,
                    "nature": ea.nature.value,
                    "causal_role": ea.causal_role.value,
                    "flags": [f.value for f in ea.flags],
                }
                for ea in self.endpoint_analysis
            ],
            "causal_structure": self.causal_structure.value,
            "bias_flags": [
                {"flag": bd.flag.value, "severity": bd.severity, "detail": bd.detail}
                for bd in self.bias_flags
            ],
            "design_recommendation": {
                "primary_design": self.design_recommendation.primary_design.value,
                "alternatives": [a.value for a in self.design_recommendation.alternatives],
                "rationale": self.design_recommendation.rationale,
            },
            "repair_engine": self._repair_dict(),
            "regulatory_readout": self.regulatory_readout,
        }
        if self.manifold_position is not None:
            d["epistemic_manifold"] = self.manifold_position.to_dict()
        if self.repair_delta is not None:
            d["repair_manifold_delta"] = self.repair_delta.to_dict()
        if self.cas_output is not None:
            d["cas_output"] = self.cas_output.to_dict()
        return d

    def _repair_dict(self) -> dict:
        if self.repair_plan_v2:
            return self.repair_plan_v2.to_dict()
        if not self.repair_plan:
            return {
                "status": "NO_REPAIR_NEEDED",
                "problem_summary": "No repair needed",
                "failure_modes": [],
                "repair_strategies": [],
                "recommended_minimal_change": "None",
                "resulting_designs": [],
            }
        rp = self.repair_plan
        return {
            "problem_summary": rp.problem_summary,
            "failure_modes": rp.failure_modes,
            "repair_strategies": [
                {
                    "type": rs.type.value,
                    "description": rs.description,
                    "effect_on_causality": rs.effect_on_causality,
                }
                for rs in rp.repair_strategies
            ],
            "recommended_minimal_change": rp.recommended_minimal_change,
            "resulting_designs": [d.value for d in rp.resulting_designs],
        }


# ---------------------------------------------------------------------------
# Epistemic Manifold (shared layer)
# ---------------------------------------------------------------------------

class ManifoldRegion(Enum):
    INVALID = "INVALID"
    FRAGILE = "FRAGILE"
    ACCEPTABLE = "ACCEPTABLE"


# ---------------------------------------------------------------------------
# CAS (Claim Alignment Score) enums
# ---------------------------------------------------------------------------

class DeviceMatchType(Enum):
    EXACT_DEVICE = "EXACT_DEVICE"
    SAME_FAMILY = "SAME_FAMILY"
    PROXY_DEVICE = "PROXY_DEVICE"
    DIFFERENT_DEVICE = "DIFFERENT_DEVICE"
    UNKNOWN = "UNKNOWN"


class PopulationMatchType(Enum):
    EXACT_INDICATION = "EXACT_INDICATION"
    NARROWER_SUBGROUP = "NARROWER_SUBGROUP"
    BROADER_POPULATION = "BROADER_POPULATION"
    DIFFERENT_POPULATION = "DIFFERENT_POPULATION"
    UNKNOWN = "UNKNOWN"


class ContextMatchType(Enum):
    SAME_HEALTHCARE_SYSTEM = "SAME_HEALTHCARE_SYSTEM"
    PARTIALLY_COMPARABLE = "PARTIALLY_COMPARABLE"
    DIFFERENT_SYSTEM = "DIFFERENT_SYSTEM"
    UNKNOWN = "UNKNOWN"


class CarePathwayMatch(Enum):
    YES = "YES"
    PARTIAL = "PARTIAL"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class EligibilityShift(Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    MAJOR = "MAJOR"


class OrganizationDependency(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CASVerdict(Enum):
    ACCEPTABLE = "ACCEPTABLE"
    WEAK_EVIDENCE = "WEAK_EVIDENCE"
    REJECTED = "REJECTED"


@dataclass
class ManifoldCoordinates:
    outcome_independence: float
    contamination_risk: float
    randomization_strength: float
    blinding_strength: float
    temporal_depth: float
    endpoint_clinical_validity: float
    data_source_independence: float

    def to_dict(self) -> dict:
        return {
            "outcome_independence": round(self.outcome_independence, 3),
            "contamination_risk": round(self.contamination_risk, 3),
            "randomization_strength": round(self.randomization_strength, 3),
            "blinding_strength": round(self.blinding_strength, 3),
            "temporal_depth": round(self.temporal_depth, 3),
            "endpoint_clinical_validity": round(self.endpoint_clinical_validity, 3),
            "data_source_independence": round(self.data_source_independence, 3),
        }

    def as_vector(self) -> list[float]:
        return [
            self.outcome_independence,
            self.contamination_risk,
            self.randomization_strength,
            self.blinding_strength,
            self.temporal_depth,
            self.endpoint_clinical_validity,
            self.data_source_independence,
        ]

    def aggregate_score(self) -> float:
        v = self.as_vector()
        return sum(v) / len(v)


@dataclass
class BiasVector:
    circularity: float = 0.0
    detection: float = 0.0
    perception: float = 0.0
    mediation_gap: float = 0.0
    tautology: float = 0.0

    def to_dict(self) -> dict:
        return {
            "circularity": round(self.circularity, 3),
            "detection": round(self.detection, 3),
            "perception": round(self.perception, 3),
            "mediation_gap": round(self.mediation_gap, 3),
            "tautology": round(self.tautology, 3),
        }

    def magnitude(self) -> float:
        vals = [self.circularity, self.detection, self.perception,
                self.mediation_gap, self.tautology]
        return (sum(v * v for v in vals) ** 0.5)


@dataclass
class RepairDirection:
    axis: str
    current: float
    target: float
    delta: float
    action: str

    def to_dict(self) -> dict:
        return {
            "axis": self.axis,
            "current": round(self.current, 3),
            "target": round(self.target, 3),
            "delta": round(self.delta, 3),
            "action": self.action,
        }


@dataclass
class EpistemicManifoldPosition:
    coordinates: ManifoldCoordinates
    region: ManifoldRegion
    bias_vector: BiasVector
    repair_directions: list[RepairDirection]
    regulatory_status: str

    def to_dict(self) -> dict:
        return {
            "coordinates": self.coordinates.to_dict(),
            "region": self.region.value,
            "aggregate_score": round(self.coordinates.aggregate_score(), 3),
            "bias_vector": self.bias_vector.to_dict(),
            "bias_magnitude": round(self.bias_vector.magnitude(), 3),
            "repair_directions": [r.to_dict() for r in self.repair_directions],
            "regulatory_status": self.regulatory_status,
        }


@dataclass
class DesignManifoldPoint:
    design_name: str
    design_type: str
    coordinates: ManifoldCoordinates
    region: ManifoldRegion
    regulatory_acceptability: float
    feasibility: float

    def to_dict(self) -> dict:
        return {
            "design_name": self.design_name,
            "design_type": self.design_type,
            "coordinates": self.coordinates.to_dict(),
            "region": self.region.value,
            "aggregate_score": round(self.coordinates.aggregate_score(), 3),
            "regulatory_acceptability": round(self.regulatory_acceptability, 3),
            "feasibility": round(self.feasibility, 3),
        }


@dataclass
class ManifoldFeasibleRegion:
    min_outcome_independence: float
    min_randomization_strength: float
    min_endpoint_clinical_validity: float
    max_contamination_risk: float
    description: str

    def to_dict(self) -> dict:
        return {
            "min_outcome_independence": round(self.min_outcome_independence, 3),
            "min_randomization_strength": round(self.min_randomization_strength, 3),
            "min_endpoint_clinical_validity": round(self.min_endpoint_clinical_validity, 3),
            "max_contamination_risk": round(self.max_contamination_risk, 3),
            "description": self.description,
        }


@dataclass
class EpistemicManifoldOutput:
    design_points: list[DesignManifoldPoint]
    feasible_region: ManifoldFeasibleRegion
    optimal_design: Optional[DesignManifoldPoint]
    recommended_design_name: str

    def to_dict(self) -> dict:
        return {
            "design_points": [p.to_dict() for p in self.design_points],
            "feasible_region": self.feasible_region.to_dict(),
            "optimal_design": self.optimal_design.to_dict() if self.optimal_design else None,
            "recommended_design_name": self.recommended_design_name,
        }


@dataclass
class RepairManifoldDelta:
    before: ManifoldCoordinates
    after: ManifoldCoordinates
    repair_vectors: list[RepairDirection]
    region_before: ManifoldRegion
    region_after: ManifoldRegion

    def to_dict(self) -> dict:
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "repair_vectors": [r.to_dict() for r in self.repair_vectors],
            "region_before": self.region_before.value,
            "region_after": self.region_after.value,
        }


# ---------------------------------------------------------------------------
# CAS (Claim Alignment Score) dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DeviceAlignment:
    device_match_type: DeviceMatchType
    device_description_claim: str
    device_description_study: str
    justification: str = ""

    def to_dict(self) -> dict:
        return {
            "device_match_type": self.device_match_type.value,
            "device_description_claim": self.device_description_claim,
            "device_description_study": self.device_description_study,
            "justification": self.justification,
        }


@dataclass
class PopulationAlignment:
    population_match_type: PopulationMatchType
    population_description_claim: str
    population_description_study: str
    subgroup_description: str = ""
    eligibility_shift: EligibilityShift = EligibilityShift.NONE
    justification: str = ""

    def to_dict(self) -> dict:
        return {
            "population_match_type": self.population_match_type.value,
            "population_description_claim": self.population_description_claim,
            "population_description_study": self.population_description_study,
            "subgroup_description": self.subgroup_description,
            "eligibility_shift": self.eligibility_shift.value,
            "justification": self.justification,
        }


@dataclass
class ContextAlignment:
    context_match_type: ContextMatchType
    care_pathway_match: CarePathwayMatch
    organization_dependency: OrganizationDependency
    study_country: str = ""
    target_country: str = "France"
    justification: str = ""

    def to_dict(self) -> dict:
        return {
            "context_match_type": self.context_match_type.value,
            "care_pathway_match": self.care_pathway_match.value,
            "organization_dependency": self.organization_dependency.value,
            "study_country": self.study_country,
            "target_country": self.target_country,
            "justification": self.justification,
        }


@dataclass
class CASGatingResult:
    device_gate_passed: bool
    device_gate_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "device_gate_passed": self.device_gate_passed,
            "device_gate_reason": self.device_gate_reason,
        }


@dataclass
class CASRisk:
    dimension: str
    risk_level: str
    description: str

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "risk_level": self.risk_level,
            "description": self.description,
        }


@dataclass
class CASOutput:
    claim_text: str
    intervention: str
    domain: str
    device_alignment: DeviceAlignment
    population_alignment: PopulationAlignment
    context_alignment: ContextAlignment
    d_device: float
    d_population: float
    d_context: float
    cas_score: float
    gating: CASGatingResult
    verdict: CASVerdict
    risks: list[CASRisk]
    regulatory_interpretation: str

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "intervention": self.intervention,
            "domain": self.domain,
            "device_alignment": self.device_alignment.to_dict(),
            "population_alignment": self.population_alignment.to_dict(),
            "context_alignment": self.context_alignment.to_dict(),
            "scores": {
                "d_device": round(self.d_device, 3),
                "d_population": round(self.d_population, 3),
                "d_context": round(self.d_context, 3),
                "cas_score": round(self.cas_score, 3),
            },
            "gating": self.gating.to_dict(),
            "verdict": self.verdict.value,
            "risks": [r.to_dict() for r in self.risks],
            "regulatory_interpretation": self.regulatory_interpretation,
        }
