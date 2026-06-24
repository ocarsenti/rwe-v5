"""Epistemic Manifold — shared representation layer for REVIEW, DESIGN, and REPAIR.

Maps every study or design into a 7-dimensional continuous epistemic space:
  1. outcome_independence (0–1)
  2. contamination_risk (0–1, inverted: 1 = no contamination)
  3. randomization_strength (0–1)
  4. blinding_strength (0–1)
  5. temporal_depth (0–1)
  6. endpoint_clinical_validity (0–1)
  7. data_source_independence (0–1)

Designs are POINTS in this space, not categorical labels.
"""

from __future__ import annotations

from models import (
    BiasFlag,
    BiasVector,
    CausalRole,
    CausalStructure,
    ClaimLevel,
    ClinicalClaim,
    DesignCandidate,
    DesignManifoldPoint,
    DesignSpace,
    EndpointAnalysis,
    EndpointNature,
    EpistemicManifoldOutput,
    EpistemicManifoldPosition,
    EvidenceDesignType,
    IdentificationRequirements,
    ManifoldCoordinates,
    ManifoldFeasibleRegion,
    ManifoldRegion,
    RepairDirection,
    RepairManifoldDelta,
    RepairPlanV2,
    StudyDesign,
)


# ===================================================================
# REGION THRESHOLDS
# ===================================================================

_ACCEPTABLE_THRESHOLD = 0.60
_FRAGILE_THRESHOLD = 0.35


def classify_region(coords: ManifoldCoordinates) -> ManifoldRegion:
    score = coords.aggregate_score()
    if coords.outcome_independence < 0.3:
        return ManifoldRegion.INVALID
    if coords.endpoint_clinical_validity < 0.2:
        return ManifoldRegion.INVALID
    if coords.blinding_strength < 0.20 and coords.endpoint_clinical_validity < 0.40:
        if score >= _FRAGILE_THRESHOLD:
            return ManifoldRegion.FRAGILE
        return ManifoldRegion.INVALID
    if score >= _ACCEPTABLE_THRESHOLD:
        return ManifoldRegion.ACCEPTABLE
    if score >= _FRAGILE_THRESHOLD:
        return ManifoldRegion.FRAGILE
    return ManifoldRegion.INVALID


# ===================================================================
# REVIEW MODE: study → manifold position
# ===================================================================

def compute_review_position(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
    design_primary: StudyDesign,
) -> EpistemicManifoldPosition:
    coords = _study_to_coordinates(
        claim, endpoint_analyses, structure, bias_flags, design_primary,
    )
    region = classify_region(coords)
    bv = _compute_bias_vector(bias_flags, endpoint_analyses, structure)
    repairs = _compute_repair_directions(coords, region)
    status = _region_to_regulatory_status(region, bv)
    return EpistemicManifoldPosition(
        coordinates=coords,
        region=region,
        bias_vector=bv,
        repair_directions=repairs,
        regulatory_status=status,
    )


def _study_to_coordinates(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
    design_primary: StudyDesign,
) -> ManifoldCoordinates:
    text = f"{claim.text} {claim.intervention}".lower()

    primary_eps = [ea for ea in endpoint_analyses if ea.endpoint.is_primary]
    secondary_eps = [ea for ea in endpoint_analyses if not ea.endpoint.is_primary]
    if not primary_eps:
        primary_eps = endpoint_analyses

    primary_circular = any(ea.causal_role == CausalRole.CIRCULAR for ea in primary_eps)
    primary_has_detection = any(BiasFlag.DETECTION_BIAS in ea.flags for ea in primary_eps)

    # --- outcome_independence ---
    if not endpoint_analyses:
        oi = 0.2
    else:
        circular_count = sum(1 for ea in endpoint_analyses if ea.causal_role == CausalRole.CIRCULAR)
        ratio = circular_count / len(endpoint_analyses)
        oi = 1.0 - ratio
        if structure == CausalStructure.CIRCULAR:
            oi = min(oi, 0.15)

    # --- contamination_risk (inverted: 1 = clean) ---
    # Primary-endpoint-aware: secondary-only detection bias applies a reduced penalty
    cr = 1.0
    if primary_has_detection:
        cr -= 0.35
    elif BiasFlag.DETECTION_BIAS in bias_flags:
        cr -= 0.15
    if BiasFlag.CIRCULARITY_RISK in bias_flags:
        cr -= 0.35
    if BiasFlag.PROCESS_TAUTOLOGY in bias_flags:
        cr -= 0.2
    cr = max(0.0, cr)

    # --- randomization_strength ---
    # REVIEW mode: use conservative estimate based on what the endpoint
    # structure can support, not the idealized recommendation.
    # If the design is NOT_IDENTIFIABLE, it means the endpoint structure
    # blocks inference — RS reflects that reality.
    # If the design is SHAM_RCT but endpoints are all subjective with no
    # demonstrated blinding, use a discounted RS reflecting "design needed
    # but not yet validated."
    _identifiable_designs = {
        StudyDesign.RCT, StudyDesign.SHAM_RCT, StudyDesign.PRAGMATIC_RCT,
        StudyDesign.COHORT, StudyDesign.ITS, StudyDesign.BEFORE_AFTER,
        StudyDesign.MATCHED_OBSERVATIONAL,
    }
    if design_primary not in _identifiable_designs:
        rs = 0.0
    elif structure == CausalStructure.CIRCULAR:
        rs = 0.0
    else:
        rs_map = {
            StudyDesign.RCT: 0.85,
            StudyDesign.SHAM_RCT: 0.70,
            StudyDesign.PRAGMATIC_RCT: 0.70,
            StudyDesign.COHORT: 0.30,
            StudyDesign.ITS: 0.25,
            StudyDesign.BEFORE_AFTER: 0.15,
            StudyDesign.MATCHED_OBSERVATIONAL: 0.35,
        }
        rs = rs_map.get(design_primary, 0.3)

    # --- blinding_strength ---
    # REVIEW mode: reflects what IS demonstrated, not what's recommended.
    # Sham design scores lower than in DESIGN mode because REVIEW evaluates
    # the submitted evidence, where blinding quality must be proven.
    all_subjective = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    if BiasFlag.PERCEPTION_BIAS in bias_flags:
        bs = 0.10
    elif all_subjective:
        bs = 0.20
    elif design_primary in (StudyDesign.RCT, StudyDesign.PRAGMATIC_RCT):
        bs = 0.50
    elif design_primary == StudyDesign.SHAM_RCT:
        bs = 0.55
    else:
        bs = 0.30

    # --- temporal_depth ---
    if any(kw in text for kw in ["12 months", "1 year", "long-term", "survival", "mortality"]):
        td = 0.85
    elif any(kw in text for kw in ["6 months", "progression"]):
        td = 0.65
    elif any(kw in text for kw in ["90 days", "3 months"]):
        td = 0.50
    elif any(kw in text for kw in ["acute", "emergency", "immediate"]):
        td = 0.30
    else:
        td = 0.50

    # --- endpoint_clinical_validity ---
    # Primary-weighted: primary endpoints count 2x in the weighted average.
    # Hard clinical endpoints (survival, mortality) get a boost.
    if not endpoint_analyses:
        ecv = 0.20
    else:
        def _ecv_score(ea: EndpointAnalysis) -> float:
            ep_text = f"{ea.endpoint.name} {ea.endpoint.description}".lower()
            if ea.causal_role == CausalRole.CIRCULAR:
                return 0.05
            if ea.nature == EndpointNature.OBJECTIVE and ea.causal_role == CausalRole.INDEPENDENT:
                base = 0.90
            elif ea.nature == EndpointNature.OBJECTIVE:
                base = 0.70
            elif ea.nature == EndpointNature.SUBJECTIVE:
                base = 0.35
            elif ea.nature == EndpointNature.INSTRUMENTED:
                base = 0.15
            else:
                base = 0.40
            if any(kw in ep_text for kw in ["survival", "mortality", "death"]):
                base = max(base, 0.90)
            elif any(kw in ep_text for kw in ["complication", "rankin", "mace"]):
                base = max(base, 0.85)
            return base

        weighted_sum = 0.0
        weight_total = 0.0
        for ea in endpoint_analyses:
            w = 2.0 if ea.endpoint.is_primary else 1.0
            weighted_sum += _ecv_score(ea) * w
            weight_total += w
        ecv = weighted_sum / weight_total

    # --- data_source_independence ---
    # Primary-endpoint-aware: only penalize DSI when the PRIMARY endpoint
    # has detection/circularity issues.
    dsi = 0.60
    if primary_has_detection:
        dsi -= 0.25
    elif BiasFlag.DETECTION_BIAS in bias_flags:
        dsi -= 0.10
    if primary_circular:
        dsi -= 0.25
    elif BiasFlag.CIRCULARITY_RISK in bias_flags:
        dsi -= 0.10
    if any(kw in text for kw in [
        "registry", "administrative", "claims", "civil registry",
        "snds", "pmsi", "survival", "mortality", "death",
    ]):
        dsi += 0.20
    dsi = max(0.0, min(1.0, dsi))

    return ManifoldCoordinates(
        outcome_independence=max(0.0, min(1.0, oi)),
        contamination_risk=cr,
        randomization_strength=rs,
        blinding_strength=bs,
        temporal_depth=td,
        endpoint_clinical_validity=ecv,
        data_source_independence=dsi,
    )


# ===================================================================
# BIAS VECTOR
# ===================================================================

def _compute_bias_vector(
    bias_flags: list[BiasFlag],
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
) -> BiasVector:
    circ = 0.0
    if BiasFlag.CIRCULARITY_RISK in bias_flags:
        circ = 0.9
    elif structure == CausalStructure.CIRCULAR:
        circ = 0.8

    det = 0.0
    if BiasFlag.DETECTION_BIAS in bias_flags:
        det_count = sum(1 for ea in endpoint_analyses if BiasFlag.DETECTION_BIAS in ea.flags)
        det = min(1.0, 0.5 + 0.2 * det_count)

    perc = 0.0
    if BiasFlag.PERCEPTION_BIAS in bias_flags:
        perc = 0.7

    med = 0.0
    if BiasFlag.MEDIATION_GAP in bias_flags:
        med = 0.5

    taut = 0.0
    if BiasFlag.PROCESS_TAUTOLOGY in bias_flags:
        taut = 0.8

    return BiasVector(
        circularity=circ,
        detection=det,
        perception=perc,
        mediation_gap=med,
        tautology=taut,
    )


# ===================================================================
# REPAIR DIRECTIONS (manifold → improvement vectors)
# ===================================================================

_AXIS_TARGETS = {
    "outcome_independence": (0.70, "Replace device-dependent endpoints with independently ascertained outcomes"),
    "contamination_risk": (0.75, "Decouple outcome measurement from intervention mechanism"),
    "randomization_strength": (0.80, "Strengthen randomization or adopt cluster/pragmatic RCT"),
    "blinding_strength": (0.60, "Add blinding (sham control) or objective co-primary endpoints"),
    "temporal_depth": (0.60, "Extend follow-up duration or add long-term outcome"),
    "endpoint_clinical_validity": (0.70, "Replace surrogate/instrumented endpoints with hard clinical outcomes"),
    "data_source_independence": (0.65, "Use external data sources (registry, claims, civil registry) for outcome ascertainment"),
}


def _compute_repair_directions(
    coords: ManifoldCoordinates,
    region: ManifoldRegion,
) -> list[RepairDirection]:
    if region == ManifoldRegion.ACCEPTABLE:
        return []

    directions = []
    for axis, (target, action) in _AXIS_TARGETS.items():
        current = getattr(coords, axis)
        if current < target:
            delta = target - current
            directions.append(RepairDirection(
                axis=axis,
                current=current,
                target=target,
                delta=delta,
                action=action,
            ))

    directions.sort(key=lambda d: d.delta, reverse=True)
    return directions


def _region_to_regulatory_status(region: ManifoldRegion, bv: BiasVector) -> str:
    if region == ManifoldRegion.INVALID:
        if bv.circularity > 0.7:
            return "BLOCKED — circular causal structure prevents valid inference"
        if bv.tautology > 0.5:
            return "BLOCKED — tautological endpoint structure"
        return "BLOCKED — study position in invalid manifold region"
    if region == ManifoldRegion.FRAGILE:
        issues = []
        if bv.detection > 0.3:
            issues.append("detection bias")
        if bv.perception > 0.3:
            issues.append("perception bias")
        if bv.mediation_gap > 0.3:
            issues.append("mediation gap")
        detail = ", ".join(issues) if issues else "marginal coordinates"
        return f"CONDITIONAL — fragile region ({detail})"
    return "ACCEPTABLE — study position in valid manifold region"


# ===================================================================
# DESIGN MODE: candidate designs → manifold points
# ===================================================================

_DESIGN_TYPE_PROFILES: dict[EvidenceDesignType, dict[str, float]] = {
    EvidenceDesignType.INDIVIDUAL_RCT: {
        "randomization_strength": 0.95,
        "blinding_strength": 0.50,
        "temporal_depth": 0.70,
        "contamination_risk": 0.90,
    },
    EvidenceDesignType.PRAGMATIC_RCT: {
        "randomization_strength": 0.80,
        "blinding_strength": 0.30,
        "temporal_depth": 0.75,
        "contamination_risk": 0.70,
    },
    EvidenceDesignType.CLUSTER_RCT: {
        "randomization_strength": 0.75,
        "blinding_strength": 0.25,
        "temporal_depth": 0.70,
        "contamination_risk": 0.60,
    },
    EvidenceDesignType.REGISTRY_RCT: {
        "randomization_strength": 0.78,
        "blinding_strength": 0.20,
        "temporal_depth": 0.80,
        "contamination_risk": 0.65,
    },
    EvidenceDesignType.STEPPED_WEDGE: {
        "randomization_strength": 0.70,
        "blinding_strength": 0.20,
        "temporal_depth": 0.75,
        "contamination_risk": 0.55,
    },
    EvidenceDesignType.CONTROLLED_ITS: {
        "randomization_strength": 0.25,
        "blinding_strength": 0.15,
        "temporal_depth": 0.65,
        "contamination_risk": 0.50,
    },
    EvidenceDesignType.TARGET_TRIAL_EMULATION: {
        "randomization_strength": 0.20,
        "blinding_strength": 0.10,
        "temporal_depth": 0.80,
        "contamination_risk": 0.45,
    },
    EvidenceDesignType.EXTERNAL_CONTROL_COHORT: {
        "randomization_strength": 0.10,
        "blinding_strength": 0.05,
        "temporal_depth": 0.60,
        "contamination_risk": 0.35,
    },
}


def compute_design_manifold(
    design_space: DesignSpace,
    identification: IdentificationRequirements,
    claim_text: str = "",
    domain: str = "",
) -> EpistemicManifoldOutput:
    points = []
    for candidate in design_space.candidates:
        coords = _candidate_to_coordinates(candidate, identification)
        region = classify_region(coords)
        points.append(DesignManifoldPoint(
            design_name=candidate.design_name,
            design_type=candidate.design_type.value,
            coordinates=coords,
            region=region,
            regulatory_acceptability=candidate.has_acceptability,
            feasibility=candidate.feasibility,
        ))

    feasible = _compute_feasible_region(identification)

    acceptable_points = [p for p in points if p.region == ManifoldRegion.ACCEPTABLE]
    if acceptable_points:
        optimal = max(acceptable_points, key=lambda p: (
            p.coordinates.aggregate_score() + p.regulatory_acceptability
        ) / 2.0)
    elif points:
        optimal = max(points, key=lambda p: p.coordinates.aggregate_score())
    else:
        optimal = None

    return EpistemicManifoldOutput(
        design_points=points,
        feasible_region=feasible,
        optimal_design=optimal,
        recommended_design_name=optimal.design_name if optimal else "",
    )


def _candidate_to_coordinates(
    candidate: DesignCandidate,
    identification: IdentificationRequirements,
) -> ManifoldCoordinates:
    profile = _DESIGN_TYPE_PROFILES.get(candidate.design_type, {})

    has_adjudication = "adjudication" in " ".join(candidate.expected_biases).lower()
    oi = candidate.causal_strength
    if has_adjudication:
        oi = min(1.0, oi + 0.05)

    cr = profile.get("contamination_risk", 0.50)
    bias_penalty = len(candidate.expected_biases) * 0.03
    cr = max(0.0, cr - bias_penalty)

    rs = profile.get("randomization_strength", 0.30)

    bs = profile.get("blinding_strength", 0.30)
    if identification.blinding_needed:
        bs = max(0.10, bs - 0.15)

    td = profile.get("temporal_depth", 0.60)

    ecv_base = candidate.causal_strength
    ep_names = " ".join(candidate.endpoint_compatibility).lower()
    if any(kw in ep_names for kw in ["mortality", "survival", "complication"]):
        ecv = min(1.0, ecv_base + 0.10)
    elif any(kw in ep_names for kw in ["acuity", "hospitalization", "escalation"]):
        ecv = min(1.0, ecv_base + 0.05)
    else:
        ecv = ecv_base

    dsi = 0.60
    if identification.external_data_needed:
        dsi = 0.75
    if has_adjudication:
        dsi = min(1.0, dsi + 0.10)

    return ManifoldCoordinates(
        outcome_independence=max(0.0, min(1.0, oi)),
        contamination_risk=max(0.0, min(1.0, cr)),
        randomization_strength=max(0.0, min(1.0, rs)),
        blinding_strength=max(0.0, min(1.0, bs)),
        temporal_depth=max(0.0, min(1.0, td)),
        endpoint_clinical_validity=max(0.0, min(1.0, ecv)),
        data_source_independence=max(0.0, min(1.0, dsi)),
    )


def _compute_feasible_region(
    identification: IdentificationRequirements,
) -> ManifoldFeasibleRegion:
    min_oi = 0.60
    if identification.adjudication_needed:
        min_oi = 0.70

    min_rs = identification.minimum_design_strength
    min_ecv = 0.55
    max_cr = 0.40

    parts = []
    if identification.adjudication_needed:
        parts.append("independent adjudication required")
    if identification.blinding_needed:
        parts.append("blinding required")
    if identification.external_data_needed:
        parts.append("external data source required")
    desc = "; ".join(parts) if parts else "standard constraints"

    return ManifoldFeasibleRegion(
        min_outcome_independence=min_oi,
        min_randomization_strength=min_rs,
        min_endpoint_clinical_validity=min_ecv,
        max_contamination_risk=max_cr,
        description=desc,
    )


# ===================================================================
# REPAIR MODE: study → repaired study (delta in manifold)
# ===================================================================

def compute_repair_delta(
    before_position: EpistemicManifoldPosition,
    repair_plan: RepairPlanV2,
    claim: ClinicalClaim,
    bias_flags: list[BiasFlag],
) -> RepairManifoldDelta:
    before = before_position.coordinates
    after = _project_repaired_coordinates(before, repair_plan, claim, bias_flags)
    region_after = classify_region(after)

    vectors = []
    axes = [
        "outcome_independence", "contamination_risk", "randomization_strength",
        "blinding_strength", "temporal_depth", "endpoint_clinical_validity",
        "data_source_independence",
    ]
    for axis in axes:
        old_val = getattr(before, axis)
        new_val = getattr(after, axis)
        if abs(new_val - old_val) > 0.01:
            target, action = _AXIS_TARGETS.get(axis, (new_val, ""))
            vectors.append(RepairDirection(
                axis=axis,
                current=old_val,
                target=new_val,
                delta=new_val - old_val,
                action=action,
            ))

    vectors.sort(key=lambda d: abs(d.delta), reverse=True)

    return RepairManifoldDelta(
        before=before,
        after=after,
        repair_vectors=vectors,
        region_before=before_position.region,
        region_after=region_after,
    )


def _project_repaired_coordinates(
    before: ManifoldCoordinates,
    repair: RepairPlanV2,
    claim: ClinicalClaim,
    bias_flags: list[BiasFlag],
) -> ManifoldCoordinates:
    oi = before.outcome_independence
    cr = before.contamination_risk
    rs = before.randomization_strength
    bs = before.blinding_strength
    td = before.temporal_depth
    ecv = before.endpoint_clinical_validity
    dsi = before.data_source_independence

    has_gold_endpoints = any(
        r.type.value in ("HARD_CLINICAL", "SURVIVAL")
        for block in repair.endpoint_repairs
        for r in block.repairs
    )
    has_utilization = any(
        r.type.value == "UTILIZATION_INDEPENDENT"
        for block in repair.endpoint_repairs
        for r in block.repairs
    )
    has_biomarker = any(
        r.type.value == "BIOMARKER"
        for block in repair.endpoint_repairs
        for r in block.repairs
    )

    if has_gold_endpoints:
        oi = max(oi, 0.80)
        ecv = max(ecv, 0.85)
        cr = max(cr, 0.80)
    if has_utilization:
        dsi = max(dsi, 0.80)
        oi = max(oi, 0.75)
    if has_biomarker:
        ecv = max(ecv, 0.65)

    for dj in repair.recommended_designs:
        design = dj.design
        if design == StudyDesign.PRAGMATIC_RCT:
            rs = max(rs, 0.80)
            dsi = max(dsi, 0.75)
        elif design == StudyDesign.RCT:
            rs = max(rs, 0.90)
        elif design == StudyDesign.SHAM_RCT:
            rs = max(rs, 0.90)
            bs = max(bs, 0.85)
        elif design == StudyDesign.COHORT:
            rs = max(rs, 0.30)

    if BiasFlag.CIRCULARITY_RISK in bias_flags and has_gold_endpoints:
        cr = max(cr, 0.80)
    if BiasFlag.DETECTION_BIAS in bias_flags and (has_gold_endpoints or has_utilization):
        cr = max(cr, 0.75)

    return ManifoldCoordinates(
        outcome_independence=min(1.0, oi),
        contamination_risk=min(1.0, cr),
        randomization_strength=min(1.0, rs),
        blinding_strength=min(1.0, bs),
        temporal_depth=min(1.0, td),
        endpoint_clinical_validity=min(1.0, ecv),
        data_source_independence=min(1.0, dsi),
    )
