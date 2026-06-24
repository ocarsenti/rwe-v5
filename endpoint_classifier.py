"""Endpoint classifier — assigns nature and causal role to endpoints."""

from __future__ import annotations

from models import (
    BiasFlag,
    CausalRole,
    ClinicalClaim,
    Endpoint,
    EndpointAnalysis,
    EndpointNature,
)


INSTRUMENTED_MARKERS = [
    "time-to-detection", "alert", "device-generated", "monitoring",
    "sensor", "automated", "ai-generated", "algorithm", "app-reported",
    "connected", "digital biomarker", "time-to-treatment",
]

SUBJECTIVE_MARKERS = [
    "pain", "qol", "quality of life", "satisfaction", "anxiety",
    "depression", "fatigue", "well-being", "comfort", "patient-reported",
    "self-reported", "perception", "symptom score",
]

OBJECTIVE_MARKERS = [
    "mortality", "survival", "hospitalization", "complication",
    "lab", "biomarker", "hba1c", "blood pressure", "bmi",
    "recurrence", "readmission", "injection", "acuity",
    "functional outcome", "treatment escalation", "adverse event",
    "infection", "analgesic consumption",
]


def _match_nature(endpoint: Endpoint) -> EndpointNature:
    """Determine endpoint nature from name + description."""
    text = f"{endpoint.name} {endpoint.description}".lower()

    for marker in INSTRUMENTED_MARKERS:
        if marker in text:
            return EndpointNature.INSTRUMENTED

    for marker in SUBJECTIVE_MARKERS:
        if marker in text:
            return EndpointNature.SUBJECTIVE

    for marker in OBJECTIVE_MARKERS:
        if marker in text:
            return EndpointNature.OBJECTIVE

    return endpoint.nature


def _match_causal_role(endpoint: Endpoint, nature: EndpointNature) -> CausalRole:
    """Determine causal role from nature and endpoint metadata.

    Respects explicitly provided non-default causal roles (MEDIATED, CIRCULAR).
    Only overrides to CIRCULAR when the user left the default (INDEPENDENT)
    and the nature is INSTRUMENTED.
    """
    if endpoint.causal_role == CausalRole.CIRCULAR:
        return CausalRole.CIRCULAR

    if endpoint.causal_role == CausalRole.MEDIATED:
        return CausalRole.MEDIATED

    if nature == EndpointNature.INSTRUMENTED:
        return CausalRole.CIRCULAR

    return CausalRole.INDEPENDENT


def _detect_endpoint_flags(
    endpoint: Endpoint, nature: EndpointNature, role: CausalRole
) -> list[BiasFlag]:
    """Detect bias flags specific to this endpoint."""
    flags = []
    text = f"{endpoint.name} {endpoint.description}".lower()

    if role == CausalRole.CIRCULAR and endpoint.is_primary:
        flags.append(BiasFlag.CIRCULARITY_RISK)

    detection_markers = [
        "time-to-detection", "alert-based", "monitoring-triggered",
        "detection", "time-to-treatment",
    ]
    if any(m in text for m in detection_markers):
        flags.append(BiasFlag.DETECTION_BIAS)

    return flags


def classify_endpoint(endpoint: Endpoint) -> EndpointAnalysis:
    """Classify a single endpoint."""
    nature = _match_nature(endpoint)
    role = _match_causal_role(endpoint, nature)
    flags = _detect_endpoint_flags(endpoint, nature, role)
    return EndpointAnalysis(
        endpoint=endpoint,
        nature=nature,
        causal_role=role,
        flags=flags,
    )


def classify_endpoints(claim: ClinicalClaim) -> list[EndpointAnalysis]:
    """Classify all endpoints in a claim."""
    return [classify_endpoint(ep) for ep in claim.endpoints]
