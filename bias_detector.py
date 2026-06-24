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
