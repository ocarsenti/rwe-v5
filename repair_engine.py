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
            "endpoint": "independently adjudicated complication rate at 12 months",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Complication occurrence is assessed by independent clinical "
                         "adjudication committee, not by the device. Decouples measurement "
                         "from intervention.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "treatment escalation rate verified by independent chart review",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Treatment decisions are documented in medical records independently "
                         "of device output. Captures downstream clinical impact without "
                         "device-generated data.",
            "risk_reduction": ["removes circularity"],
        },
        {
            "endpoint": "emergency admission records from external hospital database "
                        "(not triggered by device alert)",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Hospital admission is recorded in administrative databases "
                         "independent of the device. Outcome ascertainment is fully "
                         "decoupled from intervention mechanism.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
    ],
    "alert": [
        {
            "endpoint": "unplanned hospitalization rate from national health insurance claims",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Claims-based hospitalization data is collected independently of "
                         "the alerting device. No device influence on ascertainment.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "confirmed clinical event rate adjudicated by blinded endpoint committee",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Independent adjudication committee reviews events without knowledge "
                         "of device arm assignment. Eliminates device influence on outcome.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "30-day all-cause mortality from civil registry",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "Mortality is ascertained from civil registry data, completely "
                         "independent of device operation or alert generation.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
    ],
    "monitoring": [
        {
            "endpoint": "all-cause mortality at 12 months from civil registry",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "Mortality is the hardest clinical endpoint. Ascertainment via "
                         "civil registry is completely independent of monitoring device.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "unplanned emergency department visits from hospital administrative data",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "ED visits are recorded in hospital information systems independent "
                         "of the monitoring device. Captures downstream clinical events.",
            "risk_reduction": ["removes circularity"],
        },
        {
            "endpoint": "disease progression confirmed by independent imaging review "
                        "(blinded central reading)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Central imaging review by radiologists blinded to treatment arm "
                         "ensures progression assessment is independent of monitoring device.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
    ],
    "detection": [
        {
            "endpoint": "confirmed diagnosis rate by independent pathology/imaging review",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Diagnosis confirmation by independent pathologist or radiologist "
                         "not using device output. Eliminates detection-ascertainment loop.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "time-to-treatment initiation documented in prescriber records",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Treatment initiation is a clinical decision documented in "
                         "prescriber records. Partial device dependence if alert triggers "
                         "action, but the decision itself is clinician-driven.",
            "risk_reduction": ["removes circularity"],
        },
        {
            "endpoint": "clinical complication rate at 6 months (independently adjudicated)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Complications are clinical events assessed independently of "
                         "the detection mechanism. Downstream outcome validates that "
                         "earlier detection translates to clinical benefit.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
    ],
    "time-to-treatment": [
        {
            "endpoint": "90-day all-cause mortality from hospital discharge records",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "Mortality is ascertained from discharge/death records "
                         "independent of the triage system. Validates that faster triage "
                         "translates to survival benefit.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "functional outcome at 90 days (modified Rankin Scale, blinded assessor)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "mRS assessed by neurologist blinded to treatment arm. Standard "
                         "stroke outcome measure independent of triage mechanism.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "ICU length of stay from hospital administrative records",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "ICU duration is documented in hospital information systems "
                         "independently of the AI triage output. Captures resource "
                         "utilization downstream of clinical decisions.",
            "risk_reduction": ["removes circularity"],
        },
    ],
    "screening": [
        {
            "endpoint": "stage at diagnosis from cancer registry data",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "PRIMARY",
            "why_valid": "Cancer staging from registry data is determined by pathology "
                         "and imaging, independent of the screening method used.",
            "risk_reduction": ["removes detection bias"],
        },
        {
            "endpoint": "disease-specific mortality at 5 years from civil registry",
            "type": EndpointRepairKind.SURVIVAL,
            "causal_role": "PRIMARY",
            "why_valid": "Cause-specific mortality from registry data. Independent of "
                         "screening mechanism.",
            "risk_reduction": ["removes circularity", "removes detection bias"],
        },
        {
            "endpoint": "interval cancer rate (cancers diagnosed between screening rounds)",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Interval cancers are diagnosed through standard clinical pathways, "
                         "not through the screening device itself.",
            "risk_reduction": ["removes detection bias"],
        },
    ],
}

SUBJECTIVE_REPAIRS: dict[str, list[dict]] = {
    "pain": [
        {
            "endpoint": "total analgesic consumption in morphine-equivalent mg/day over 12 weeks",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "PRIMARY",
            "why_valid": "Medication consumption is objectively recorded in pharmacy records. "
                         "Reduced analgesic use is an objective proxy for pain reduction not "
                         "subject to placebo response.",
            "risk_reduction": ["removes perception bias", "provides objective anchoring"],
        },
        {
            "endpoint": "6-minute walk test distance in meters at 3 and 6 months",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Standardized functional test measured by blinded assessor. "
                         "Physical performance is less susceptible to placebo than "
                         "self-reported pain scales.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "return-to-work rate at 6 months from employment records",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "Employment status is objectively verifiable from employer/insurance "
                         "records. Captures functional impact of pain reduction in daily life.",
            "risk_reduction": ["removes perception bias", "provides objective anchoring"],
        },
        {
            "endpoint": "nocturnal actigraphy sleep efficiency percentage over 4 weeks",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "SECONDARY",
            "why_valid": "Wrist actigraphy provides objective, continuous sleep measurement. "
                         "Pain-related sleep disturbance improvement is an objective correlate "
                         "of analgesic effect.",
            "risk_reduction": ["removes perception bias"],
        },
    ],
    "quality of life": [
        {
            "endpoint": "all-cause hospitalization rate at 12 months from insurance claims",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Hospitalization from administrative data is objective and not "
                         "influenced by patient perception. Major QoL events that require "
                         "hospitalization are clinically significant.",
            "risk_reduction": ["removes perception bias", "provides objective anchoring"],
        },
        {
            "endpoint": "Functional Independence Measure (FIM) score by blinded assessor",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "FIM is assessed by trained, blinded evaluator. Covers motor and "
                         "cognitive domains with standardized scoring less susceptible to "
                         "patient expectation bias.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "number of days alive and out of hospital at 12 months",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Composite endpoint from administrative records capturing both "
                         "survival and freedom from hospitalization. Fully objective.",
            "risk_reduction": ["removes perception bias", "provides objective anchoring"],
        },
    ],
    "qol": [
        {
            "endpoint": "all-cause hospitalization rate at 12 months from insurance claims",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Administrative outcome not influenced by patient perception.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "days alive and out of hospital at 12 months",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Composite objective endpoint from administrative records.",
            "risk_reduction": ["removes perception bias", "provides objective anchoring"],
        },
        {
            "endpoint": "Functional Independence Measure by blinded assessor",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Standardized assessor-rated functional measure.",
            "risk_reduction": ["removes perception bias"],
        },
    ],
    "satisfaction": [
        {
            "endpoint": "treatment adherence rate from pharmacy dispensing records",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "SECONDARY",
            "why_valid": "Adherence measured by pharmacy records is objective. "
                         "Continued use is a revealed-preference proxy for satisfaction.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "treatment discontinuation rate at 6 months",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Discontinuation is a binary objective event. "
                         "Patients who are genuinely dissatisfied stop treatment.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "healthcare utilization in the 12 months post-intervention "
                        "from insurance claims",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "Administrative data capturing whether patients seek additional "
                         "care. Objective proxy for unmet needs.",
            "risk_reduction": ["removes perception bias"],
        },
    ],
    "fatigue": [
        {
            "endpoint": "daily step count from validated accelerometer over 4 weeks",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "SECONDARY",
            "why_valid": "Accelerometry provides continuous objective measurement of "
                         "physical activity. Less susceptible to reporting bias than "
                         "fatigue questionnaires.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "cardiopulmonary exercise test VO2max at baseline and 3 months",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "VO2max is an objective physiological measure of exercise capacity. "
                         "Standard assessment by blinded technician.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "days of work absence over 6 months from employer records",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "Work absence is objectively documented. Captures functional "
                         "impact of fatigue on daily activities.",
            "risk_reduction": ["removes perception bias", "provides objective anchoring"],
        },
    ],
    "symptom score": [
        {
            "endpoint": "unplanned hospitalization rate from administrative data",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "PRIMARY",
            "why_valid": "Hospitalization from administrative records. Symptom deterioration "
                         "leading to hospitalization is an objective downstream event.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "treatment modification rate from prescriber records",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "SECONDARY",
            "why_valid": "Treatment changes documented by prescribers reflect clinically "
                         "significant symptom changes, not patient perception alone.",
            "risk_reduction": ["removes perception bias"],
        },
        {
            "endpoint": "emergency department visit rate from hospital information system",
            "type": EndpointRepairKind.UTILIZATION_INDEPENDENT,
            "causal_role": "SECONDARY",
            "why_valid": "ED visits are objective events captured in hospital systems. "
                         "Symptom crises leading to ED visits are clinically meaningful.",
            "risk_reduction": ["removes perception bias"],
        },
    ],
}

MEDIATION_INTERMEDIATES: dict[str, list[dict]] = {
    "neurostimulat": [
        {
            "endpoint": "serum beta-endorphin level at 2h and 4h post-stimulation (ELISA)",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "MEDIATOR",
            "why_valid": "Direct biochemical measurement of the claimed mechanism. "
                         "If neurostimulation claims endorphin release, endorphin levels "
                         "must be measured to validate the causal chain.",
            "risk_reduction": ["fills mediation gap"],
        },
        {
            "endpoint": "quantitative sensory testing (thermal pain threshold) by blinded assessor",
            "type": EndpointRepairKind.HARD_CLINICAL,
            "causal_role": "MEDIATOR",
            "why_valid": "Objective psychophysical measure of pain processing. Bridges "
                         "mechanism (endorphin release) to outcome (pain reduction) with "
                         "an independent, non-subjective measurement.",
            "risk_reduction": ["fills mediation gap", "provides objective anchoring"],
        },
    ],
    "stimulat": [
        {
            "endpoint": "target biomarker level change from baseline (assay-specific)",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "MEDIATOR",
            "why_valid": "Direct biological measurement of the claimed stimulation effect.",
            "risk_reduction": ["fills mediation gap"],
        },
    ],
    "modulat": [
        {
            "endpoint": "target pathway activation biomarker (serum/tissue)",
            "type": EndpointRepairKind.BIOMARKER,
            "causal_role": "MEDIATOR",
            "why_valid": "Biological marker of pathway modulation validates the causal "
                         "mechanism before outcome measurement.",
            "risk_reduction": ["fills mediation gap"],
        },
    ],
    "monitoring": [
        {
            "endpoint": "time from symptom onset to clinician-initiated treatment change",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "MEDIATOR",
            "why_valid": "Treatment change is the clinical action that mediates between "
                         "monitoring (process) and survival (outcome). Clinician decision "
                         "is the critical link.",
            "risk_reduction": ["fills mediation gap"],
        },
    ],
    "triage": [
        {
            "endpoint": "door-to-needle time documented in emergency department records",
            "type": EndpointRepairKind.SOFT_CLINICAL,
            "causal_role": "MEDIATOR",
            "why_valid": "Process time from ED records (not from AI system) bridges "
                         "triage prioritization to clinical outcome.",
            "risk_reduction": ["fills mediation gap"],
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
