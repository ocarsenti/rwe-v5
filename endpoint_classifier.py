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

# Surrogates dont la validation clinique/réglementaire est établie de longue date
# dans leur indication usuelle (ex. HbA1c pour le diabète, LDL-C et pression
# artérielle pour le risque cardiovasculaire). Ne suppriment PAS SURROGATE_RISK —
# la validation reste conditionnée à endpoint.is_validated_surrogate — mais servent
# à enrichir le message (cf. study_object._endpoint_gaps) pour orienter le reviewer
# vers ce flag manuel plutôt que de le laisser deviner.
KNOWN_VALIDATED_SURROGATE_MARKERS = [
    "hba1c", "ldl-c", "ldl cholesterol", "ldl cholestérol",
    "blood pressure", "pression artérielle",
    "hémoglobine glyquée", "hemoglobine glyquee",
]

INSTRUMENTED_MARKERS = [
    # English
    "time-to-detection", "alert", "device-generated", "monitoring",
    "sensor", "automated", "ai-generated", "algorithm", "app-reported",
    "connected", "digital biomarker", "time-to-treatment",
    # French
    "délai jusqu'à détection", "alerte", "généré par le dispositif",
    "télésurveillance", "surveillance", "capteur", "automatisé",
    "généré par ia", "algorithme", "signalé par l'application",
    "connecté", "biomarqueur numérique", "délai jusqu'au traitement",
]

SUBJECTIVE_MARKERS = [
    # English
    "pain", "qol", "quality of life", "satisfaction", "anxiety",
    "depression", "fatigue", "well-being", "comfort", "patient-reported",
    "self-reported", "perception", "symptom score",
    # French
    "douleur", "qualité de vie", "satisfaction", "anxiété",
    "dépression", "fatigue", "bien-être", "confort", "auto-rapporté",
    "auto-évalué", "auto-déclaré", "perception", "score de symptômes",
]

OBJECTIVE_MARKERS = [
    # English
    "mortality", "survival", "hospitalization", "complication",
    "lab", "biomarker", "hba1c", "blood pressure", "bmi",
    "recurrence", "readmission", "injection", "acuity",
    "functional outcome", "treatment escalation", "adverse event",
    "infection", "analgesic consumption",
    # French
    "mortalité", "survie", "hospitalisation", "complication",
    "biomarqueur", "hémoglobine glyquée", "pression artérielle", "imc",
    "récidive", "récurrence", "réhospitalisation", "injection", "acuité",
    "résultat fonctionnel", "escalade thérapeutique", "événement indésirable",
    "infection", "consommation d'analgésiques",
]


def _marker_pattern(marker: str) -> re.Pattern[str]:
    """Compile a marker into a word-boundary regex (avoids false positives like "lab" in "label")."""
    return re.compile(rf"\b{re.escape(marker)}\b")


def _first_marker_match(markers: list[str], text: str) -> str | None:
    """Return the first marker (in list order) that matches text, or None."""
    for marker in markers:
        if _marker_pattern(marker).search(text):
            return marker
    return None


def _any_marker(markers: list[str], text: str) -> bool:
    return _first_marker_match(markers, text) is not None


def is_known_validated_surrogate(endpoint: Endpoint) -> bool:
    """Whether the endpoint name/description matches a well-established surrogate
    (HbA1c, LDL-C, blood pressure...). Informational only — does not suppress
    SURROGATE_RISK, which still requires endpoint.is_validated_surrogate."""
    text = f"{endpoint.name} {endpoint.description}".lower()
    return _any_marker(KNOWN_VALIDATED_SURROGATE_MARKERS, text)


def _match_nature(endpoint: Endpoint) -> tuple[EndpointNature, str]:
    """Determine endpoint nature from name + description.

    Returns (nature, reason) where reason names the exact marker that decided
    it, for decision traceability.
    """
    text = f"{endpoint.name} {endpoint.description}".lower()

    # INSTRUMENTED checked first: it flags a collection-method concern (the
    # endpoint is captured via a device/algorithm/monitoring tied to the
    # intervention), which _match_causal_role escalates to CausalRole.CIRCULAR
    # (detection/surveillance bias). That causal-validity risk applies
    # regardless of whether the underlying content is subjective or objective
    # (e.g. "digital biomarker" also matches OBJECTIVE's "biomarker"), so it
    # must win over the content-based SUBJECTIVE/OBJECTIVE classification.
    marker = _first_marker_match(INSTRUMENTED_MARKERS, text)
    if marker:
        return EndpointNature.INSTRUMENTED, f"matched INSTRUMENTED marker '{marker}'"

    marker = _first_marker_match(SUBJECTIVE_MARKERS, text)
    if marker:
        return EndpointNature.SUBJECTIVE, f"matched SUBJECTIVE marker '{marker}'"

    marker = _first_marker_match(OBJECTIVE_MARKERS, text)
    if marker:
        return EndpointNature.OBJECTIVE, f"matched OBJECTIVE marker '{marker}'"

    return endpoint.nature, "no marker matched; defaulted to endpoint.nature"


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
    endpoint: Endpoint, nature: EndpointNature, nature_reason: str, role: CausalRole
) -> tuple[list[BiasFlag], dict[BiasFlag, str]]:
    """Detect bias flags specific to this endpoint.

    Returns (flags, reasons) where reasons[flag] names the exact marker (or
    the role/attribute state, when no single marker is responsible) that
    triggered that flag, for decision traceability.
    """
    flags: list[BiasFlag] = []
    reasons: dict[BiasFlag, str] = {}
    text = f"{endpoint.name} {endpoint.description}".lower()

    if role == CausalRole.CIRCULAR and endpoint.is_primary:
        flags.append(BiasFlag.CIRCULARITY_RISK)
        if endpoint.causal_role == CausalRole.CIRCULAR:
            reasons[BiasFlag.CIRCULARITY_RISK] = "causal_role=CIRCULAR (explicit on endpoint)"
        else:
            reasons[BiasFlag.CIRCULARITY_RISK] = (
                f"causal_role=CIRCULAR via nature=INSTRUMENTED ({nature_reason})"
            )

    # DETECTION_BIAS is checked independently of role/nature (unlike the flags
    # below): it flags an ascertainment-mechanism concern (how the outcome is
    # measured), which is orthogonal to CIRCULARITY_RISK/SURROGATE_RISK (what
    # the endpoint's causal role means). It can therefore co-fire with either —
    # this is intentional, not a duplicate: an endpoint can simultaneously be
    # detected via a device-tied mechanism AND be an unvalidated surrogate.
    # (Downstream, both land as HIGH severity gaps; be aware this can push
    # _compute_overall_risk to CRITICAL off a single endpoint's dual labeling.)
    detection_markers = [
        # English
        "time-to-detection", "alert-based", "monitoring-triggered",
        "detection", "time-to-treatment",
        # French
        "délai jusqu'à détection", "déclenché par alerte", "alerte",
        "déclenché par surveillance", "détection", "délai jusqu'au traitement",
    ]
    marker = _first_marker_match(detection_markers, text)
    if marker:
        flags.append(BiasFlag.DETECTION_BIAS)
        reasons[BiasFlag.DETECTION_BIAS] = f"matched detection marker '{marker}'"

    hard_clinical_marker = _first_marker_match(HARD_CLINICAL_MARKERS, text)
    is_hard_clinical = hard_clinical_marker is not None
    if (
        role == CausalRole.MEDIATED
        and endpoint.is_primary
        and not endpoint.is_validated_surrogate
        and not is_hard_clinical
        and nature != EndpointNature.SUBJECTIVE  # PROs are not surrogates — bias = PERCEPTION_BIAS
    ):
        flags.append(BiasFlag.SURROGATE_RISK)
        reasons[BiasFlag.SURROGATE_RISK] = (
            "causal_role=MEDIATED (explicit on endpoint), is_primary=True, "
            f"is_validated_surrogate=False, no HARD_CLINICAL_MARKERS match, "
            f"nature={nature.value} ({nature_reason})"
        )

    if endpoint.is_primary and endpoint.value_fixed_by_protocol:
        flags.append(BiasFlag.PROTOCOL_FIXED_ENDPOINT)
        reasons[BiasFlag.PROTOCOL_FIXED_ENDPOINT] = (
            "is_primary=True, value_fixed_by_protocol=True — endpoint value in the "
            "evaluated device's arm is a protocol parameter, not a measured outcome"
        )

    all_cause_marker = _first_marker_match(ALL_CAUSE_DEATH_MARKERS, text)
    is_all_cause_death = all_cause_marker is not None
    if (
        nature == EndpointNature.OBJECTIVE
        and role == CausalRole.INDEPENDENT
        and endpoint.is_primary
        and not endpoint.is_independently_adjudicated
        and not is_all_cause_death
    ):
        flags.append(BiasFlag.ADJUDICATION_RISK)
        reasons[BiasFlag.ADJUDICATION_RISK] = (
            f"nature=OBJECTIVE ({nature_reason}), causal_role=INDEPENDENT, is_primary=True, "
            "is_independently_adjudicated=False, no ALL_CAUSE_DEATH_MARKERS match"
        )

    return flags, reasons


def classify_endpoint(endpoint: Endpoint) -> EndpointAnalysis:
    """Classify a single endpoint."""
    nature, nature_reason = _match_nature(endpoint)
    role = _match_causal_role(endpoint, nature)
    flags, flag_reasons = _detect_endpoint_flags(endpoint, nature, nature_reason, role)
    return EndpointAnalysis(
        endpoint=endpoint,
        nature=nature,
        causal_role=role,
        flags=flags,
        nature_reason=nature_reason,
        flag_reasons=flag_reasons,
    )


def classify_endpoints(claim: ClinicalClaim) -> list[EndpointAnalysis]:
    """Classify all endpoints in a claim."""
    return [classify_endpoint(ep) for ep in claim.endpoints]
