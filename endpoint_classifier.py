"""Endpoint classifier — assigns nature and causal role to endpoints."""

from __future__ import annotations

import re

from models import (
    BiasFlag,
    CausalRole,
    ClinicalClaim,
    Endpoint,
    EndpointAnalysis,
    EndpointNature,
)


HARD_CLINICAL_MARKERS = [
    # English
    "mortality", "survival", "death", "hospitalization", "readmission",
    "stroke", "myocardial infarction", "heart failure", "amputation",
    "fracture", "complication", "adverse event", "infection", "recurrence",
    "treatment escalation", "major adverse", "all-cause",
    # French
    "mortalité", "survie", "décès", "hospitalisation", "réhospitalisation",
    "avc", "infarctus", "insuffisance cardiaque", "amputation",
    "fracture", "complication", "événement indésirable", "infection",
    "récidive", "récurrence", "escalade thérapeutique",
]

# Seuls endpoints dont l'adjudication est triviale (mort = binaire, pas d'interprétation).
# Toute autre issue objective (hospitalisation, AVC, complication, PFS...) requiert jugement.
ALL_CAUSE_DEATH_MARKERS = [
    "all-cause mortality", "all-cause death", "overall mortality",
    "mortalité toutes causes", "décès toutes causes", "toutes causes de décès",
]

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


def _marker_pattern(marker: str) -> re.Pattern[str]:
    """Compile a marker into a word-boundary regex (avoids false positives like "lab" in "label")."""
    return re.compile(rf"\b{re.escape(marker)}\b")


def _any_marker(markers: list[str], text: str) -> bool:
    return any(_marker_pattern(marker).search(text) for marker in markers)


def _match_nature(endpoint: Endpoint) -> EndpointNature:
    """Determine endpoint nature from name + description."""
    text = f"{endpoint.name} {endpoint.description}".lower()

    if _any_marker(INSTRUMENTED_MARKERS, text):
        return EndpointNature.INSTRUMENTED

    if _any_marker(SUBJECTIVE_MARKERS, text):
        return EndpointNature.SUBJECTIVE

    if _any_marker(OBJECTIVE_MARKERS, text):
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
    if _any_marker(detection_markers, text):
        flags.append(BiasFlag.DETECTION_BIAS)

    is_hard_clinical = _any_marker(HARD_CLINICAL_MARKERS, text)
    if (
        role == CausalRole.MEDIATED
        and endpoint.is_primary
        and not endpoint.is_validated_surrogate
        and not is_hard_clinical
        and nature != EndpointNature.SUBJECTIVE  # PROs are not surrogates — bias = PERCEPTION_BIAS
    ):
        flags.append(BiasFlag.SURROGATE_RISK)

    is_all_cause_death = _any_marker(ALL_CAUSE_DEATH_MARKERS, text)
    if (
        nature == EndpointNature.OBJECTIVE
        and role == CausalRole.INDEPENDENT
        and endpoint.is_primary
        and not endpoint.is_independently_adjudicated
        and not is_all_cause_death
    ):
        flags.append(BiasFlag.ADJUDICATION_RISK)

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
