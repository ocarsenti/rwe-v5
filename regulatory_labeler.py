"""Regulatory labeler — transforms binary verdicts into nuanced CNEDiMTS-style assessments.

Implements the Gold Dataset Regulatory Labeling Framework:
  - No binary "RCT valid/invalid" — only endpoint-level conditional assessments
  - Every judgment is design-dependent and conditional
  - Preserves conditional validity pathways
  - Never rejects an entire RCT, only endpoints or endpoint positioning
"""

from __future__ import annotations

from models import (
    BiasFlag,
    BiasThreshold,
    CausalGraphSummary,
    CausalRole,
    CausalStructure,
    ClinicalClaim,
    DesignTypeRequired,
    DeviceContext,
    EndpointAnalysis,
    EndpointGoldAnalysis,
    EndpointNature,
    EndpointRepairKind,
    EndpointStatus,
    EngineOutput,
    FinalRegulatoryStatus,
    GoldCaseOutput,
    GoldDatasetRow,
    IssueDetection,
    IssueType,
    OriginalEndpointAssessment,
    RegulatoryConditions,
    RegulatoryStrength,
    RepairEndpointGold,
    RepairEndpointType,
    RepairPlanV2,
)


# ===================================================================
# ISSUE TYPE DETECTION
# ===================================================================

def _classify_issue_type(
    engine_output: EngineOutput,
    claim: ClinicalClaim,
) -> IssueType:
    flags = {bd.flag for bd in engine_output.bias_flags}
    claim_text = f"{claim.text} {claim.intervention}".lower()

    has_circular = any(
        ea.causal_role == CausalRole.CIRCULAR
        for ea in engine_output.endpoint_analysis
    )
    has_detection = BiasFlag.DETECTION_BIAS in flags

    if has_circular and has_detection:
        is_triage = any(kw in claim_text for kw in ["triage", "prioriti"])
        if is_triage:
            return IssueType.DETECTION_ACCELERATION
        return IssueType.MEASUREMENT_CIRCULARITY

    if has_circular:
        return IssueType.MEASUREMENT_CIRCULARITY

    if has_detection and has_circular:
        return IssueType.DETECTION_ACCELERATION

    if BiasFlag.PERCEPTION_BIAS in flags:
        return IssueType.SUBJECTIVE_ENDPOINT_BIAS

    if BiasFlag.MEDIATION_GAP in flags:
        return IssueType.CARE_PATHWAY_BIAS

    if BiasFlag.PROCESS_TAUTOLOGY in flags:
        return IssueType.CARE_PATHWAY_BIAS

    return IssueType.CARE_PATHWAY_BIAS


def _compute_severity(engine_output: EngineOutput) -> float:
    if engine_output.repair_plan_v2:
        return engine_output.repair_plan_v2.failure_diagnosis.severity
    if not engine_output.bias_flags:
        return 0.0
    max_sev = 0.0
    for bd in engine_output.bias_flags:
        if bd.severity == "HIGH":
            max_sev = max(max_sev, 0.8)
        elif bd.severity == "MEDIUM":
            max_sev = max(max_sev, 0.5)
        else:
            max_sev = max(max_sev, 0.3)
    return max_sev


# ===================================================================
# ENDPOINT STATUS ASSESSMENT
# ===================================================================

def _assess_endpoint_status(
    ea: EndpointAnalysis,
    engine_output: EngineOutput,
) -> EndpointStatus:
    flags = {bd.flag for bd in engine_output.bias_flags}

    if ea.causal_role == CausalRole.CIRCULAR:
        if ea.endpoint.is_primary:
            return EndpointStatus.INVALID_UNLESS_REDEFINED
        return EndpointStatus.INVALID_AS_PRIMARY_ONLY

    if BiasFlag.DETECTION_BIAS in ea.flags:
        if ea.endpoint.is_primary:
            return EndpointStatus.INVALID_AS_PRIMARY_ONLY
        return EndpointStatus.ACCEPTABLE_WITH_CONDITIONS

    if ea.nature == EndpointNature.SUBJECTIVE:
        all_subjective = all(
            ep_a.nature == EndpointNature.SUBJECTIVE
            for ep_a in engine_output.endpoint_analysis
        )
        if all_subjective:
            return EndpointStatus.ACCEPTABLE_WITH_CONDITIONS
        if ea.endpoint.is_primary:
            return EndpointStatus.ACCEPTABLE_WITH_CONDITIONS
        return EndpointStatus.ACCEPTABLE_WITH_CONDITIONS

    if ea.nature == EndpointNature.OBJECTIVE and ea.causal_role == CausalRole.INDEPENDENT:
        return EndpointStatus.ACCEPTABLE

    if ea.causal_role == CausalRole.MEDIATED:
        if BiasFlag.MEDIATION_GAP in flags:
            return EndpointStatus.ACCEPTABLE_WITH_CONDITIONS
        return EndpointStatus.ACCEPTABLE

    return EndpointStatus.ACCEPTABLE_WITH_CONDITIONS


def _build_failure_mode(
    ea: EndpointAnalysis,
    status: EndpointStatus,
    claim: ClinicalClaim,
) -> str:
    if status == EndpointStatus.ACCEPTABLE:
        return "No causal failure detected. Endpoint is independently ascertained."

    if ea.causal_role == CausalRole.CIRCULAR:
        return (
            f"'{ea.endpoint.name}' is causally entangled with {claim.intervention}: "
            f"the device generates or influences the measurement used as endpoint. "
            f"Outcome ascertainment cannot be separated from treatment arm assignment. "
            f"This is not a trial-level rejection — the endpoint must be repositioned "
            f"or replaced with an independently ascertained outcome."
        )

    if BiasFlag.DETECTION_BIAS in ea.flags:
        return (
            f"'{ea.endpoint.name}' is subject to detection acceleration: "
            f"{claim.intervention} changes when/how the outcome is detected, "
            f"not whether the underlying clinical event occurs. "
            f"Acceptable as secondary endpoint with independent adjudication."
        )

    if ea.nature == EndpointNature.SUBJECTIVE:
        return (
            f"'{ea.endpoint.name}' is patient-reported and susceptible to "
            f"expectation/placebo bias in open-label design. "
            f"Acceptable as primary only with blinding (sham control) "
            f"or as secondary endpoint anchored by an objective co-primary."
        )

    if ea.causal_role == CausalRole.MEDIATED:
        return (
            f"'{ea.endpoint.name}' requires intermediate causal steps between "
            f"{claim.intervention} and the measured outcome. "
            f"The mediation chain must be specified and measured to validate "
            f"the endpoint's sensitivity to the intervention."
        )

    return (
        f"'{ea.endpoint.name}' has conditional acceptability depending on "
        f"study design controls and endpoint positioning."
    )


# ===================================================================
# REPAIR ENDPOINT CONVERSION
# ===================================================================

_KIND_TO_GOLD_TYPE = {
    EndpointRepairKind.HARD_CLINICAL: RepairEndpointType.HARD_CLINICAL,
    EndpointRepairKind.SOFT_CLINICAL: RepairEndpointType.HARD_CLINICAL,
    EndpointRepairKind.UTILIZATION_INDEPENDENT: RepairEndpointType.UTILIZATION,
    EndpointRepairKind.SURVIVAL: RepairEndpointType.SURVIVAL,
    EndpointRepairKind.BIOMARKER: RepairEndpointType.BIOMARKER,
}

_KIND_TO_ROBUSTNESS = {
    EndpointRepairKind.SURVIVAL: 0.95,
    EndpointRepairKind.HARD_CLINICAL: 0.85,
    EndpointRepairKind.UTILIZATION_INDEPENDENT: 0.80,
    EndpointRepairKind.SOFT_CLINICAL: 0.65,
    EndpointRepairKind.BIOMARKER: 0.60,
}


def _convert_repair_endpoints(
    engine_output: EngineOutput,
    ea: EndpointAnalysis,
) -> list[RepairEndpointGold]:
    v2 = engine_output.repair_plan_v2
    if not v2:
        return []

    repairs = []
    for block in v2.endpoint_repairs:
        if block.original_endpoint.lower() != ea.endpoint.name.lower():
            if not (block.original_endpoint.startswith("[") and ea.endpoint.is_primary):
                continue

        for r in block.repairs:
            gold_type = _KIND_TO_GOLD_TYPE.get(r.type, RepairEndpointType.HARD_CLINICAL)
            robustness = _KIND_TO_ROBUSTNESS.get(r.type, 0.5)

            if r.causal_role == "PRIMARY":
                strength = RegulatoryStrength.PRIMARY_CANDIDATE
            elif r.causal_role == "SECONDARY":
                strength = RegulatoryStrength.SECONDARY_ONLY
            else:
                strength = RegulatoryStrength.EXPLORATORY

            repairs.append(RepairEndpointGold(
                endpoint_name=r.endpoint,
                type=gold_type,
                robustness_score=robustness,
                regulatory_strength=strength,
            ))

    return repairs


# ===================================================================
# REGULATORY CONDITIONS
# ===================================================================

def _build_regulatory_conditions(
    engine_output: EngineOutput,
    claim: ClinicalClaim,
) -> list[RegulatoryConditions]:
    flags = {bd.flag for bd in engine_output.bias_flags}
    conditions = []

    has_circular = any(
        ea.causal_role == CausalRole.CIRCULAR
        for ea in engine_output.endpoint_analysis
    )
    has_subjective_only = (
        engine_output.endpoint_analysis
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in engine_output.endpoint_analysis)
    )

    if has_circular or BiasFlag.DETECTION_BIAS in flags:
        conditions.append(RegulatoryConditions(
            blinding_required=False,
            independent_adjudication_required=True,
            external_data_source_required=True,
            endpoint_repositioning="SECONDARY",
            design_type_required=DesignTypeRequired.PRAGMATIC_RCT,
            acceptable_bias_threshold=BiasThreshold.LOW,
        ))
        conditions.append(RegulatoryConditions(
            blinding_required=False,
            independent_adjudication_required=True,
            external_data_source_required=True,
            endpoint_repositioning="PRIMARY",
            design_type_required=DesignTypeRequired.REGISTRY_RCT,
            acceptable_bias_threshold=BiasThreshold.LOW,
        ))

    if has_subjective_only:
        conditions.append(RegulatoryConditions(
            blinding_required=True,
            independent_adjudication_required=False,
            external_data_source_required=False,
            endpoint_repositioning="PRIMARY",
            design_type_required=DesignTypeRequired.RCT,
            acceptable_bias_threshold=BiasThreshold.LOW,
        ))
        conditions.append(RegulatoryConditions(
            blinding_required=False,
            independent_adjudication_required=True,
            external_data_source_required=True,
            endpoint_repositioning="SECONDARY",
            design_type_required=DesignTypeRequired.PRAGMATIC_RCT,
            acceptable_bias_threshold=BiasThreshold.MEDIUM,
        ))

    if BiasFlag.MEDIATION_GAP in flags and not conditions:
        conditions.append(RegulatoryConditions(
            blinding_required=False,
            independent_adjudication_required=True,
            external_data_source_required=False,
            endpoint_repositioning="PRIMARY",
            design_type_required=DesignTypeRequired.RCT,
            acceptable_bias_threshold=BiasThreshold.MEDIUM,
        ))

    if not conditions:
        conditions.append(RegulatoryConditions(
            blinding_required=False,
            independent_adjudication_required=False,
            external_data_source_required=False,
            endpoint_repositioning="PRIMARY",
            design_type_required=DesignTypeRequired.RCT,
            acceptable_bias_threshold=BiasThreshold.LOW,
        ))

    return conditions


# ===================================================================
# CAUSAL GRAPH SUMMARY
# ===================================================================

def _build_causal_graph_summary(
    engine_output: EngineOutput,
    claim: ClinicalClaim,
) -> CausalGraphSummary:
    mediators = []
    influence_paths = []

    if engine_output.repair_plan_v2:
        for step in engine_output.repair_plan_v2.causal_chain:
            if step.role == "MEDIATOR":
                mediators.append(step.node)

    for ea in engine_output.endpoint_analysis:
        if ea.causal_role == CausalRole.CIRCULAR:
            influence_paths.append(
                f"{claim.intervention} → {ea.endpoint.name} (circular: device generates measurement)"
            )
        elif ea.causal_role == CausalRole.MEDIATED:
            influence_paths.append(
                f"{claim.intervention} → [mediator] → {ea.endpoint.name} (mediated chain)"
            )

    if not influence_paths:
        for ea in engine_output.endpoint_analysis:
            influence_paths.append(
                f"{claim.intervention} → {ea.endpoint.name} (direct)"
            )

    structure = engine_output.causal_structure.value
    summary = (
        f"Causal structure: {structure}. "
        f"Intervention: {claim.intervention}. "
        f"Endpoints: {', '.join(ea.endpoint.name for ea in engine_output.endpoint_analysis)}."
    )

    return CausalGraphSummary(
        summary=summary,
        mediators=mediators,
        measurement_influence_paths=influence_paths,
    )


# ===================================================================
# HAS / CNEDiMTS INTERPRETATION
# ===================================================================

_HAS_TEMPLATES = {
    IssueType.MEASUREMENT_CIRCULARITY: (
        "La Commission relève que le critère de jugement principal ({endpoint}) "
        "est structurellement lié au dispositif évalué. L'évaluation de l'effet "
        "clinique nécessite un critère indépendant du mécanisme d'action du dispositif. "
        "La Commission recommande le repositionnement de ce critère en critère secondaire "
        "et l'adoption d'un critère clinique dur, adjudiqué de manière indépendante, "
        "comme critère principal."
    ),
    IssueType.DETECTION_ACCELERATION: (
        "La Commission note que le critère principal ({endpoint}) mesure "
        "l'accélération de la détection plutôt qu'un bénéfice clinique en soi. "
        "L'amélioration du temps de détection n'est acceptable comme critère "
        "que si elle s'accompagne d'un critère de résultat clinique indépendant "
        "(mortalité, morbidité, score fonctionnel validé). La Commission demande "
        "l'ajout d'un critère clinique dur en co-primary."
    ),
    IssueType.SUBJECTIVE_ENDPOINT_BIAS: (
        "La Commission observe que l'ensemble des critères de jugement sont "
        "des mesures rapportées par le patient ({endpoint}), sans ancrage objectif. "
        "En l'absence de procédure d'aveugle (contrôle sham), les résultats "
        "ne peuvent être distingués d'un effet placebo. La Commission recommande "
        "soit un design en double aveugle avec sham, soit l'ajout d'un critère "
        "objectif co-primaire (consommation d'antalgiques, test fonctionnel validé)."
    ),
    IssueType.CARE_PATHWAY_BIAS: (
        "La Commission relève un gap de médiation entre le mécanisme d'action "
        "allégué et les critères de jugement mesurés. Le lien causal entre "
        "{intervention} et {endpoint} n'est pas entièrement spécifié. "
        "La Commission recommande l'ajout de critères intermédiaires validant "
        "chaque étape de la chaîne causale, ou la reformulation de la revendication "
        "au niveau du critère effectivement mesuré."
    ),
}


def _generate_has_interpretation(
    issue_type: IssueType,
    claim: ClinicalClaim,
    engine_output: EngineOutput,
) -> str:
    primary_eps = [
        ea.endpoint.name for ea in engine_output.endpoint_analysis
        if ea.endpoint.is_primary
    ]
    endpoint_str = primary_eps[0] if primary_eps else "critère principal"

    template = _HAS_TEMPLATES.get(issue_type, _HAS_TEMPLATES[IssueType.CARE_PATHWAY_BIAS])
    return template.format(
        endpoint=endpoint_str,
        intervention=claim.intervention,
    )


# ===================================================================
# FINAL REGULATORY STATUS
# ===================================================================

def _determine_final_status(
    severity: float,
    issue_type: IssueType,
    engine_output: EngineOutput,
) -> FinalRegulatoryStatus:
    has_circular_primary = any(
        ea.causal_role == CausalRole.CIRCULAR and ea.endpoint.is_primary
        for ea in engine_output.endpoint_analysis
    )
    all_circular = (
        engine_output.endpoint_analysis
        and all(ea.causal_role == CausalRole.CIRCULAR for ea in engine_output.endpoint_analysis)
    )

    v2 = engine_output.repair_plan_v2
    has_repairs = v2 and v2.endpoint_repairs

    if all_circular and v2 and v2.status == "NON_REPAIRABLE":
        return FinalRegulatoryStatus.REJECTED_UNLESS_EXTERNAL_VALIDATION

    if has_circular_primary and severity >= 0.8:
        if has_repairs:
            return FinalRegulatoryStatus.INVALID_AS_PRIMARY_ENDPOINT_ONLY
        return FinalRegulatoryStatus.REJECTED_UNLESS_EXTERNAL_VALIDATION

    if issue_type == IssueType.SUBJECTIVE_ENDPOINT_BIAS:
        if severity >= 0.6:
            return FinalRegulatoryStatus.ACCEPTABLE_WITH_REDESIGN
        return FinalRegulatoryStatus.ACCEPTABLE_SECONDARY_ONLY

    if severity >= 0.7:
        if has_repairs:
            return FinalRegulatoryStatus.ACCEPTABLE_WITH_REDESIGN
        return FinalRegulatoryStatus.INVALID_AS_PRIMARY_ENDPOINT_ONLY

    if severity >= 0.4:
        return FinalRegulatoryStatus.ACCEPTABLE_PRIMARY_WITH_CONDITIONS

    return FinalRegulatoryStatus.ACCEPTABLE_PRIMARY_WITH_CONDITIONS


# ===================================================================
# GOLD DATASET ROW
# ===================================================================

def _build_gold_row(
    case: GoldCaseOutput,
    endpoint_analysis: EndpointGoldAnalysis,
) -> GoldDatasetRow:
    status = endpoint_analysis.original_endpoint.status

    if status == EndpointStatus.ACCEPTABLE:
        acceptable_primary = "yes"
    elif status == EndpointStatus.ACCEPTABLE_WITH_CONDITIONS:
        acceptable_primary = "conditional"
    else:
        acceptable_primary = "no"

    severity = case.issue_detection.severity_score
    if severity >= 0.7:
        risk_level = "high"
    elif severity >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"

    best_repair = ""
    if endpoint_analysis.repair_endpoints:
        primary_candidates = [
            r for r in endpoint_analysis.repair_endpoints
            if r.regulatory_strength == RegulatoryStrength.PRIMARY_CANDIDATE
        ]
        if primary_candidates:
            best = max(primary_candidates, key=lambda r: r.robustness_score)
            best_repair = best.endpoint_name
        else:
            best = max(endpoint_analysis.repair_endpoints, key=lambda r: r.robustness_score)
            best_repair = best.endpoint_name

    conditions = case.regulatory_conditions
    if conditions:
        required_design = conditions[0].design_type_required.value
    else:
        required_design = "RCT"

    return GoldDatasetRow(
        device=case.device_context.name,
        original_endpoint=endpoint_analysis.original_endpoint.name,
        failure_type=case.issue_detection.primary_issue_type.value,
        severity=severity,
        acceptable_primary=acceptable_primary,
        required_design=required_design,
        best_repair_endpoint=best_repair,
        regulatory_risk_level=risk_level,
    )


# ===================================================================
# MAIN ENTRY POINT
# ===================================================================

def label_case(
    case_id: str,
    claim: ClinicalClaim,
    engine_output: EngineOutput,
) -> GoldCaseOutput:
    issue_type = _classify_issue_type(engine_output, claim)
    severity = _compute_severity(engine_output)

    device_context = DeviceContext(
        name=claim.intervention,
        domain=claim.domain,
        intervention_type=_infer_intervention_type(claim),
    )

    causal_graph = _build_causal_graph_summary(engine_output, claim)
    issue_detection = IssueDetection(primary_issue_type=issue_type, severity_score=severity)

    endpoint_analyses = []
    for ea in engine_output.endpoint_analysis:
        status = _assess_endpoint_status(ea, engine_output)
        failure_mode = _build_failure_mode(ea, status, claim)
        original = OriginalEndpointAssessment(
            name=ea.endpoint.name, status=status, failure_mode=failure_mode,
        )
        repairs = _convert_repair_endpoints(engine_output, ea)
        endpoint_analyses.append(EndpointGoldAnalysis(
            original_endpoint=original,
            repair_endpoints=repairs,
        ))

    regulatory_conditions = _build_regulatory_conditions(engine_output, claim)
    has_interpretation = _generate_has_interpretation(issue_type, claim, engine_output)
    final_status = _determine_final_status(severity, issue_type, engine_output)

    return GoldCaseOutput(
        case_id=case_id,
        device_context=device_context,
        causal_graph=causal_graph,
        issue_detection=issue_detection,
        endpoint_analyses=endpoint_analyses,
        regulatory_conditions=regulatory_conditions,
        has_interpretation=has_interpretation,
        final_regulatory_status=final_status,
    )


def build_gold_dataset_rows(cases: list[GoldCaseOutput]) -> list[GoldDatasetRow]:
    rows = []
    for case in cases:
        for ea in case.endpoint_analyses:
            rows.append(_build_gold_row(case, ea))
    return rows


def _infer_intervention_type(claim: ClinicalClaim) -> str:
    text = f"{claim.text} {claim.intervention}".lower()
    if any(kw in text for kw in ["monitoring", "remote", "telemonitor"]):
        return "MONITORING_DEVICE"
    if any(kw in text for kw in ["triage", "prioriti", "screening"]):
        return "TRIAGE_SYSTEM"
    if any(kw in text for kw in ["stimulat", "neurostimulat"]):
        return "THERAPEUTIC_DEVICE"
    if any(kw in text for kw in ["alert", "detection"]):
        return "DETECTION_DEVICE"
    return "MEDICAL_DEVICE"
