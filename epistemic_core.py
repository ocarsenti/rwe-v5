"""Epistemic core — SINGLE source of truth for all causal/regulatory reasoning.

Absorbs design_engine.py. Both REVIEW and DESIGN modes use this core.

Responsibilities:
  - causal graph representation
  - identification logic
  - mediator detection
  - endpoint classification
  - bias taxonomy
  - regulatory constraints
  - design space generation
  - regulatory manifold computation
"""

from __future__ import annotations

from models import (
    BiasFlag,
    CausalRole,
    CausalStructure,
    ClaimLevel,
    ClinicalClaim,
    DAGEdge,
    DesignCandidate,
    DesignRecommendation,
    DesignSpace,
    EndpointAnalysis,
    EndpointFamily,
    EndpointNature,
    EvidenceDesignType,
    IdentificationRequirements,
    ManifoldPoint,
    RegulatoryManifold,
    StudyDesign,
    TargetDAG,
)

from claim_parser import parse_claim, classify_claim
from endpoint_classifier import classify_endpoint, classify_endpoints
from causal_graph_builder import build_causal_structure, detect_structural_issues
from bias_detector import build_bias_detections
from repair_engine import generate_repair_plan, generate_repair_plan_v2


# ===================================================================
# DESIGN RECOMMENDATION (absorbed from design_engine.py)
# ===================================================================

def recommend_design(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
) -> DesignRecommendation:
    if structure == CausalStructure.INVALID:
        return DesignRecommendation(
            primary_design=StudyDesign.NOT_IDENTIFIABLE,
            alternatives=[StudyDesign.EXPLORATORY],
            rationale="No identifiable causal estimand — exploratory study only.",
        )

    if structure == CausalStructure.CIRCULAR:
        return DesignRecommendation(
            primary_design=StudyDesign.NOT_IDENTIFIABLE,
            alternatives=[StudyDesign.BEFORE_AFTER, StudyDesign.EXPLORATORY],
            rationale=(
                "Circular causal structure blocks standard comparative designs. "
                "Repair the endpoint structure before selecting a design."
            ),
        )

    all_subjective = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    if all_subjective:
        return DesignRecommendation(
            primary_design=StudyDesign.SHAM_RCT,
            alternatives=[StudyDesign.RCT],
            rationale=(
                "All endpoints are subjective — double-blind or sham-controlled "
                "RCT required to control perception bias."
            ),
        )

    if BiasFlag.DETECTION_BIAS in bias_flags:
        if BiasFlag.CIRCULARITY_RISK in bias_flags:
            return DesignRecommendation(
                primary_design=StudyDesign.NOT_IDENTIFIABLE,
                alternatives=[StudyDesign.COHORT, StudyDesign.BEFORE_AFTER],
                rationale=(
                    "Detection bias combined with circularity — standard RCT not valid "
                    "without endpoint repair."
                ),
            )
        return DesignRecommendation(
            primary_design=StudyDesign.RCT,
            alternatives=[StudyDesign.COHORT, StudyDesign.ITS],
            rationale=(
                "Detection bias present but manageable with independent endpoint "
                "adjudication in an RCT framework."
            ),
        )

    if claim.level in (ClaimLevel.C, ClaimLevel.D):
        return DesignRecommendation(
            primary_design=StudyDesign.RCT,
            alternatives=[StudyDesign.COHORT],
            rationale="Outcome-level or complete-chain claim — RCT is the gold standard.",
        )

    if claim.level == ClaimLevel.B:
        return DesignRecommendation(
            primary_design=StudyDesign.COHORT,
            alternatives=[StudyDesign.BEFORE_AFTER, StudyDesign.ITS],
            rationale="Process-level claim — comparative cohort or before/after design.",
        )

    if claim.level == ClaimLevel.A:
        return DesignRecommendation(
            primary_design=StudyDesign.EXPLORATORY,
            alternatives=[StudyDesign.BEFORE_AFTER],
            rationale="Mechanism-level claim — exploratory study to validate mechanism.",
        )

    return DesignRecommendation(
        primary_design=StudyDesign.COHORT,
        alternatives=[StudyDesign.BEFORE_AFTER],
        rationale="Default recommendation — comparative cohort.",
    )


# ===================================================================
# IDENTIFICATION LOGIC
# ===================================================================

_MECHANISM_KW = [
    "neurostimulat", "stimulat", "modulat", "electromagnetic",
    "receptor", "molecule", "cellular", "endorphin", "frequency",
]
_PROCESS_KW = [
    "monitoring", "triage", "screening", "alert", "detection",
    "surveillance", "remote", "telemonitor", "symptom tracking",
    "follow-up", "care pathway", "referral", "coordination",
]
_OUTCOME_KW = [
    "survival", "mortality", "hospitalization", "complication",
    "pain", "quality of life", "acuity", "progression", "recurrence",
    "functional", "morbidity", "adverse event", "disability",
]


def assess_identification(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
) -> IdentificationRequirements:
    has_circular = any(ea.causal_role == CausalRole.CIRCULAR for ea in endpoint_analyses)
    has_detection = BiasFlag.DETECTION_BIAS in bias_flags
    has_subjective_only = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    has_mediation = BiasFlag.MEDIATION_GAP in bias_flags
    text = f"{claim.text} {claim.intervention}".lower()
    has_mechanism = any(kw in text for kw in _MECHANISM_KW)

    is_device_measurement = any(kw in text for kw in [
        "monitoring", "detection", "triage", "alert", "screening",
        "sensor", "remote", "time-to-detection", "time-to-treatment",
    ])
    is_subjective_domain = any(kw in text for kw in [
        "pain", "quality of life", "fatigue", "anxiety", "well-being",
        "satisfaction", "symptom score",
    ])

    randomization = True
    blinding = has_subjective_only or is_subjective_domain
    adjudication = has_circular or has_detection or is_device_measurement
    external = has_circular or has_detection or is_device_measurement
    mediator_meas = has_mediation or has_mechanism

    if structure == CausalStructure.CIRCULAR or (is_device_measurement and not endpoint_analyses):
        strength = 0.9
    elif has_subjective_only or is_subjective_domain:
        strength = 0.7
    elif has_mediation or has_mechanism:
        strength = 0.5
    else:
        strength = 0.3

    return IdentificationRequirements(
        randomization_needed=randomization,
        blinding_needed=blinding,
        adjudication_needed=adjudication,
        external_data_needed=external,
        mediator_measurement_needed=mediator_meas,
        minimum_design_strength=strength,
    )


# ===================================================================
# TARGET DAG INFERENCE (DESIGN mode)
# ===================================================================

_MEDIATOR_KB = {
    "monitoring": ["symptom detection", "clinician alert", "treatment modification"],
    "triage": ["scan prioritization", "clinical decision", "treatment initiation"],
    "screening": ["case identification", "diagnostic confirmation", "treatment referral"],
    "alert": ["clinician notification", "clinical assessment", "treatment decision"],
    "detection": ["event identification", "clinical verification", "therapeutic action"],
    "neurostimulat": ["neural activation", "endorphin release", "pain modulation"],
    "stimulat": ["tissue activation", "biological response", "physiological effect"],
    "modulat": ["pathway modulation", "biological response", "clinical effect"],
    "remote": ["data transmission", "clinician review", "treatment adjustment"],
}

_PROHIBITED_KB = {
    "monitoring": ["device-generated alert count", "monitoring coverage rate", "time-to-detection by device"],
    "triage": ["AI-triggered time-to-treatment", "triage prioritization score", "AI detection rate"],
    "screening": ["screening detection rate by device", "device sensitivity", "device-flagged event count"],
    "alert": ["alert-triggered detection rate", "alert count", "time-to-alert"],
    "detection": ["device detection rate", "time-to-detection by device", "AI-flagged positive rate"],
    "neurostimulat": ["stimulation session count", "device activation rate"],
    "stimulat": ["stimulation delivery count", "device output metric"],
}

_OUTCOME_KB = {
    "stroke": ["90-day all-cause mortality", "modified Rankin Scale at 90 days", "ICU length of stay",
               "30-day mortality from civil registry", "recurrent stroke rate"],
    "cancer": ["overall survival", "progression-free survival", "unplanned hospitalization rate",
               "treatment modification rate", "emergency department visits"],
    "ophthalmology": ["independently assessed visual acuity", "complication rate at 12 months",
                      "treatment escalation rate", "emergency admission for vision loss"],
    "pain": ["total analgesic consumption (morphine-equivalent mg/day)",
             "6-minute walk test distance", "return-to-work rate",
             "nocturnal actigraphy sleep efficiency"],
    "cardiology": ["all-cause mortality", "hospitalization rate from insurance claims",
                   "MACE (major adverse cardiovascular events)", "functional capacity (6MWT)"],
}

_DOMAIN_MAP = {
    "ophthalmology": "ophthalmology",
    "oncology": "cancer", "lung cancer": "cancer", "cancer": "cancer",
    "neurology": "stroke", "stroke": "stroke", "emergency neurology": "stroke",
    "pain": "pain", "pain management": "pain", "chronic pain": "pain",
    "cardiology": "cardiology", "heart": "cardiology",
}


def infer_target_dag(
    claim_text: str,
    intervention: str,
    domain: str = "",
) -> TargetDAG:
    text = f"{claim_text} {intervention}".lower()

    mediators = []
    for kw, meds in _MEDIATOR_KB.items():
        if kw in text:
            mediators.extend(meds)
            break
    if not mediators:
        mediators = ["intermediate clinical process", "clinical decision"]

    prohibited = []
    for kw, proh in _PROHIBITED_KB.items():
        if kw in text:
            prohibited.extend(proh)
    if not prohibited:
        prohibited = ["device-generated measurement endpoint"]

    domain_key = _DOMAIN_MAP.get(domain.lower(), "")
    outcomes = _OUTCOME_KB.get(domain_key, [])
    if not outcomes:
        outcomes = [
            "all-cause mortality from civil registry",
            "unplanned hospitalization rate from insurance claims",
            "independently adjudicated clinical event rate",
        ]

    edges = [DAGEdge(source=intervention, target=mediators[0])]
    for i in range(len(mediators) - 1):
        edges.append(DAGEdge(source=mediators[i], target=mediators[i + 1]))
    edges.append(DAGEdge(source=mediators[-1], target=outcomes[0]))

    return TargetDAG(
        intervention=intervention,
        mediators=mediators,
        outcomes=outcomes,
        prohibited_outcomes=prohibited,
        edges=edges,
    )


# ===================================================================
# ENDPOINT FAMILY GENERATION (DESIGN mode)
# ===================================================================

def compute_endpoint_families(
    dag: TargetDAG,
    identification: IdentificationRequirements,
) -> list[EndpointFamily]:
    families = []

    hard_clinical = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in ["mortality", "rankin", "complication", "mace", "recurrent", "acuity"]
    )]
    if hard_clinical:
        families.append(EndpointFamily(
            family_name="HARD_CLINICAL",
            endpoints=hard_clinical,
            independence_from_device=0.95,
            regulatory_weight="PRIMARY",
        ))

    utilization = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in ["hospitalization", "admission", "emergency", "icu", "escalation"]
    )]
    if utilization:
        families.append(EndpointFamily(
            family_name="UTILIZATION",
            endpoints=utilization,
            independence_from_device=0.90,
            regulatory_weight="PRIMARY",
        ))

    biomarker = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in ["analgesic", "actigraphy", "walk test", "vo2", "biomarker"]
    )]
    if biomarker:
        families.append(EndpointFamily(
            family_name="BIOMARKER",
            endpoints=biomarker,
            independence_from_device=0.80,
            regulatory_weight="SECONDARY",
        ))

    survival = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in ["survival", "mortality from civil", "mortality from hospital"]
    )]
    if survival and not any(f.family_name == "HARD_CLINICAL" and any("mortality" in e.lower() for e in f.endpoints) for f in families):
        families.append(EndpointFamily(
            family_name="SURVIVAL",
            endpoints=survival,
            independence_from_device=1.0,
            regulatory_weight="PRIMARY",
        ))

    if identification.mediator_measurement_needed:
        mediator_eps = [m for m in dag.mediators if m not in ("intermediate clinical process", "clinical decision")]
        if mediator_eps:
            families.append(EndpointFamily(
                family_name="MEDIATOR",
                endpoints=mediator_eps,
                independence_from_device=0.70,
                regulatory_weight="EXPLORATORY",
            ))

    if not families:
        families.append(EndpointFamily(
            family_name="HARD_CLINICAL",
            endpoints=["independently adjudicated clinical event rate at 12 months"],
            independence_from_device=0.90,
            regulatory_weight="PRIMARY",
        ))

    return families


# ===================================================================
# DESIGN SPACE GENERATION (DESIGN mode)
# ===================================================================

_DESIGN_PROFILES = [
    {
        "type": EvidenceDesignType.INDIVIDUAL_RCT,
        "name": "Individual RCT with independent endpoint adjudication",
        "base_strength": 0.95,
        "base_biases": ["selection bias (mitigated by randomization)"],
        "base_feasibility": 0.60,
        "base_acceptability": 0.95,
        "requires_blinding": False,
        "handles_circularity": False,
    },
    {
        "type": EvidenceDesignType.PRAGMATIC_RCT,
        "name": "Pragmatic RCT with administrative outcome ascertainment",
        "base_strength": 0.85,
        "base_biases": ["performance bias (open-label)", "outcome ascertainment via routine data"],
        "base_feasibility": 0.75,
        "base_acceptability": 0.85,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.CLUSTER_RCT,
        "name": "Cluster RCT (randomization at site level)",
        "base_strength": 0.80,
        "base_biases": ["contamination risk", "cluster-level confounding"],
        "base_feasibility": 0.65,
        "base_acceptability": 0.80,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.REGISTRY_RCT,
        "name": "Registry-based RCT with embedded randomization",
        "base_strength": 0.82,
        "base_biases": ["registry data quality", "incomplete capture"],
        "base_feasibility": 0.80,
        "base_acceptability": 0.82,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.STEPPED_WEDGE,
        "name": "Stepped-wedge cluster RCT (sequential rollout)",
        "base_strength": 0.78,
        "base_biases": ["temporal confounding", "learning effect"],
        "base_feasibility": 0.70,
        "base_acceptability": 0.75,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.CONTROLLED_ITS,
        "name": "Controlled interrupted time series",
        "base_strength": 0.55,
        "base_biases": ["history bias", "maturation", "regression to mean"],
        "base_feasibility": 0.85,
        "base_acceptability": 0.55,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.TARGET_TRIAL_EMULATION,
        "name": "Target trial emulation from observational data",
        "base_strength": 0.50,
        "base_biases": ["unmeasured confounding", "immortal time bias", "selection bias"],
        "base_feasibility": 0.90,
        "base_acceptability": 0.45,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.EXTERNAL_CONTROL_COHORT,
        "name": "Single-arm study with external control cohort",
        "base_strength": 0.35,
        "base_biases": ["unmeasured confounding", "selection bias", "temporal bias"],
        "base_feasibility": 0.95,
        "base_acceptability": 0.30,
        "requires_blinding": False,
        "handles_circularity": True,
    },
]


def generate_design_space(
    claim_text: str,
    dag: TargetDAG,
    identification: IdentificationRequirements,
    endpoint_families: list[EndpointFamily],
) -> DesignSpace:
    text = f"{claim_text} {dag.intervention}".lower()
    is_emergency = any(kw in text for kw in ["emergency", "triage", "stroke", "acute"])
    is_subjective = any(kw in text for kw in ["pain", "quality of life", "fatigue", "anxiety"])
    is_device = any(kw in text for kw in ["device", "wristband", "app", "system", "monitor"])

    primary_eps = []
    for f in endpoint_families:
        if f.regulatory_weight == "PRIMARY":
            primary_eps.extend(f.endpoints)
    if not primary_eps:
        primary_eps = ["independently adjudicated clinical event rate"]

    candidates = []
    for profile in _DESIGN_PROFILES:
        strength = profile["base_strength"]
        feasibility = profile["base_feasibility"]
        acceptability = profile["base_acceptability"]
        biases = list(profile["base_biases"])

        if identification.blinding_needed and not profile["requires_blinding"]:
            if profile["type"] == EvidenceDesignType.INDIVIDUAL_RCT:
                biases.append("requires sham/blinding for subjective endpoints")
                strength += 0.0
            else:
                biases.append("perception bias (no blinding)")
                strength -= 0.05
                acceptability -= 0.05

        if identification.adjudication_needed:
            biases.append("independent adjudication committee required")

        if is_emergency and profile["type"] == EvidenceDesignType.INDIVIDUAL_RCT:
            feasibility -= 0.20
            biases.append("emergency setting complicates individual randomization")

        if is_emergency and profile["type"] in (
            EvidenceDesignType.CLUSTER_RCT, EvidenceDesignType.STEPPED_WEDGE,
        ):
            feasibility += 0.10

        if is_subjective and profile["type"] == EvidenceDesignType.INDIVIDUAL_RCT:
            biases.append("sham control recommended for subjective endpoints")

        candidates.append(DesignCandidate(
            design_type=profile["type"],
            design_name=profile["name"],
            causal_strength=round(max(0.0, min(1.0, strength)), 2),
            expected_biases=biases,
            endpoint_compatibility=primary_eps[:3],
            feasibility=round(max(0.0, min(1.0, feasibility)), 2),
            has_acceptability=round(max(0.0, min(1.0, acceptability)), 2),
        ))

    candidates.sort(key=lambda c: c.has_acceptability, reverse=True)
    return DesignSpace(candidates=candidates)


# ===================================================================
# REGULATORY MANIFOLD
# ===================================================================

def compute_regulatory_manifold(design_space: DesignSpace) -> RegulatoryManifold:
    points = []
    for c in design_space.candidates:
        identification_score = c.causal_strength
        bias_risk = round(1.0 - c.causal_strength + 0.05 * len(c.expected_biases), 2)
        bias_risk = min(1.0, max(0.0, bias_risk))
        operational_complexity = round(1.0 - c.feasibility, 2)
        regulatory_acceptability = c.has_acceptability

        points.append(ManifoldPoint(
            design=c,
            identification_score=identification_score,
            bias_risk=bias_risk,
            operational_complexity=operational_complexity,
            regulatory_acceptability=regulatory_acceptability,
        ))

    points.sort(key=lambda p: p.regulatory_acceptability, reverse=True)
    return RegulatoryManifold(points=points)
