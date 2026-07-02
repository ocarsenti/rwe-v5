"""Bias detector — generates detailed bias detections from flags."""

from __future__ import annotations

from models import (
    BiasDetection,
    BiasFlag,
    CausalStructure,
    EndpointAnalysis,
)


BIAS_DETAILS: dict[BiasFlag, dict] = {
    BiasFlag.CIRCULARITY_RISK: {
        "severity": "HIGH",
        "detail": (
            "Primary endpoint is generated or influenced by the device under evaluation. "
            "The device cannot be both the intervention and the measurement instrument "
            "for the primary outcome — this creates an unfalsifiable causal claim."
        ),
    },
    BiasFlag.DETECTION_BIAS: {
        "severity": "HIGH",
        "detail": (
            "Outcome ascertainment is influenced by the intervention. "
            "Detection-based endpoints (time-to-detection, alert-triggered diagnosis, "
            "monitoring-driven events) conflate device sensitivity with clinical benefit."
        ),
    },
    BiasFlag.PERCEPTION_BIAS: {
        "severity": "MEDIUM",
        "detail": (
            "All endpoints are subjective (patient-reported). Without blinding or "
            "objective anchoring, perceived benefit cannot be separated from placebo "
            "effect or expectation bias."
        ),
    },
    BiasFlag.MEDIATION_GAP: {
        "severity": "MEDIUM",
        "detail": (
            "Claim is at mechanism or process level but endpoints measure clinical "
            "outcomes. The causal chain between intervention mechanism and measured "
            "outcome is not fully specified — intermediate steps are assumed but untested."
        ),
    },
    BiasFlag.PROCESS_TAUTOLOGY: {
        "severity": "HIGH",
        "detail": (
            "The process endpoint is the intervention itself. Measuring the process "
            "that the device performs as an outcome is tautological — the device will "
            "always 'succeed' at doing what it does."
        ),
    },
    BiasFlag.ADJUDICATION_RISK: {
        "severity": "MEDIUM",
        "detail": (
            "Primary endpoint is objective but assessed without independent blind "
            "adjudication (Clinical Events Committee). In an open-label device trial, "
            "investigator-reported events (hospitalization, stroke, complications, PFS) "
            "are subject to classification bias — the same clinical presentation may be "
            "coded differently across treatment arms. Set is_independently_adjudicated=True "
            "when a blinded CEC is documented in the protocol."
        ),
    },
    BiasFlag.SURROGATE_RISK: {
        "severity": "HIGH",
        "detail": (
            "Primary endpoint is a mediated (surrogate) outcome that does not capture "
            "direct clinical benefit for the patient. The causal chain from this surrogate "
            "to a hard clinical endpoint must be independently established. If not validated "
            "in this indication and population, the surrogate cannot substitute for a "
            "patient-relevant outcome — set is_validated_surrogate=True on the endpoint "
            "to suppress this flag when the surrogate is accepted in the literature."
        ),
    },
    BiasFlag.NO_COMPARATOR: {
        "severity": "HIGH",
        "detail": (
            "The submitted evidence lacks a control group for an outcome-level claim "
            "(ClaimLevel C or D). Without a comparator, the counterfactual is unobserved — "
            "the observed outcome cannot be attributed to the intervention rather than "
            "natural history, regression to the mean, or concomitant treatments. "
            "A randomised or matched comparator arm is required for causal attribution. "
            "This flag is suppressed when comparator_feasibility is DIFFERENT_MODALITY or "
            "NO_ALTERNATIVE — a single-arm design compared to a documented performance "
            "objective is acceptable when no comparable-modality alternative exists."
        ),
    },
}


def build_bias_detections(
    flags: list[BiasFlag],
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
) -> list[BiasDetection]:
    """Build detailed bias detection objects from flags."""
    seen = set()
    detections = []

    for flag in flags:
        if flag in seen:
            continue
        seen.add(flag)

        info = BIAS_DETAILS.get(flag)
        if info:
            detections.append(
                BiasDetection(
                    flag=flag,
                    severity=info["severity"],
                    detail=info["detail"],
                )
            )

    if structure == CausalStructure.CIRCULAR and BiasFlag.CIRCULARITY_RISK not in seen:
        info = BIAS_DETAILS[BiasFlag.CIRCULARITY_RISK]
        detections.append(
            BiasDetection(
                flag=BiasFlag.CIRCULARITY_RISK,
                severity=info["severity"],
                detail=info["detail"],
            )
        )

    return detections
