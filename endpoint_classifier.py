"""Endpoint classifier — assigns nature and causal role to endpoints."""

from __future__ import annotations

import logging
import re

from models import (
    BiasFlag,
    CausalRole,
    ClinicalClaim,
    Endpoint,
    EndpointAnalysis,
    EndpointNature,
)

# Première utilisation de `logging` dans ce codebase (2026-07-18) — choix
# volontaire de la bibliothèque standard plutôt qu'un mécanisme maison,
# pour rester intégrable sans configuration supplémentaire dans n'importe
# quel pipeline (stdout, fichier, service de logs...).
logger = logging.getLogger(__name__)


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
    # NB (2026-07-22, cas AXOMOVE) : "télésurveillance"/"surveillance" ont été
    # RETIRÉS de cette liste. Ce sont des mots de CANAL DE TRANSMISSION (le
    # dossier appartient à la catégorie réglementaire "télésurveillance"), pas
    # des marqueurs de MÉCANISME DE GÉNÉRATION de la valeur — contrairement à
    # "capteur"/"automatisé"/"algorithme" qui, eux, désignent bien le dispositif
    # comme producteur de la mesure. Avec ces deux mots dans la liste, un simple
    # questionnaire auto-rapporté par le patient (PROM) était classé INSTRUMENTED/
    # CIRCULAR dès qu'il était transmis via une plateforme de télésurveillance —
    # ce qui est systématique dans TOUT dossier LATM télésurveillance, quel que
    # soit l'endpoint. Testé : un PROM identique classé SUBJECTIVE/INDEPENDENT
    # quand décrit via "l'application" devenait INSTRUMENTED/CIRCULAR simplement
    # en le décrivant via "l'opérateur de télésurveillance" — aucun changement
    # de contenu clinique, seul le mot de canal changeait. Un vrai endpoint
    # capté par capteur reste couvert par "capteur"/"automatisé"/"algorithme".
    "délai jusqu'à détection", "alerte", "généré par le dispositif",
    "capteur", "automatisé",
    "généré par ia", "algorithme", "signalé par l'application",
    "connecté", "biomarqueur numérique", "délai jusqu'au traitement",
]

SUBJECTIVE_MARKERS = [
    # English
    "pain", "qol", "quality of life", "satisfaction", "anxiety",
    "depression", "fatigue", "well-being", "comfort", "patient-reported",
    "self-reported", "perception", "symptom score", "questionnaire",
    "self-administered questionnaire", "patient-administered",
    # French. "échelle" est plus large que les autres marqueurs (une échelle
    # peut aussi être clinicien-rapportée) — ajouté le 2026-07-18 car les
    # échelles patient les plus courantes du domaine (EVA, PSQI, HAD, FIQ)
    # sont presque toujours qualifiées d'"échelle" dans les descriptions
    # d'étude ; compromis assumé plutôt qu'une couverture nulle pour ces
    # instruments (cf. le cas FIQ/FIBROREM qui a motivé cet ajout).
    "douleur", "qualité de vie", "satisfaction", "anxiété",
    "dépression", "fatigue", "bien-être", "confort", "auto-rapporté",
    "auto-évalué", "auto-déclaré", "perception", "score de symptômes",
    "questionnaire", "auto-questionnaire", "échelle",
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
    """Compile a marker into a word-boundary regex (avoids false positives like "lab" in "label").

    Trailing 's' is optional (2026-07-22, cas AXOMOVE) so that a singular marker
    like "alerte" also matches the plural "alertes" as it appears verbatim in
    real HAS avis text (e.g. "peuvent faire l'objet d'alertes") — without this,
    DETECTION_BIAS silently failed to fire on any endpoint description phrased
    in the plural, which is the common case in French regulatory prose.
    """
    return re.compile(rf"\b{re.escape(marker)}s?\b")


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
        _log_nature_disagreement(endpoint, EndpointNature.INSTRUMENTED, marker)
        return EndpointNature.INSTRUMENTED, f"matched INSTRUMENTED marker '{marker}'"

    marker = _first_marker_match(SUBJECTIVE_MARKERS, text)
    if marker:
        _log_nature_disagreement(endpoint, EndpointNature.SUBJECTIVE, marker)
        return EndpointNature.SUBJECTIVE, f"matched SUBJECTIVE marker '{marker}'"

    marker = _first_marker_match(OBJECTIVE_MARKERS, text)
    if marker:
        _log_nature_disagreement(endpoint, EndpointNature.OBJECTIVE, marker)
        return EndpointNature.OBJECTIVE, f"matched OBJECTIVE marker '{marker}'"

    return endpoint.nature, "no marker matched; defaulted to endpoint.nature"


def _log_nature_disagreement(
    endpoint: Endpoint, marker_nature: EndpointNature, marker: str
) -> None:
    """Journalise silencieusement (WARNING, jamais bloquant) quand le
    verdict par mots-clés diffère de la nature déjà posée sur l'endpoint
    (LLM, JSON, ou toute autre source amont). Ajouté le 2026-07-18 suite au
    cas FIQ/FIBROREM, où ce désaccord serait passé inaperçu : le mot-clé
    écrasait silencieusement l'autre source, sans aucune trace.

    Ne tranche PAS qui a raison — les deux sources peuvent se tromper (le
    mot-clé n'écrase pas nécessairement une extraction LLM : endpoint.nature
    peut lui-même déjà être le résultat d'un fallback par mots-clés côté
    llm_evidence_parser.py quand le JSON source ne précisait rien). Sert
    uniquement à mesurer la fréquence réelle des désaccords sur des vrais
    dossiers, pour décider s'il faut enrichir le vocabulaire ou construire
    un mécanisme plus élaboré — pas pour bloquer ou solliciter qui que ce
    soit à l'exécution.
    """
    if endpoint.nature != marker_nature:
        logger.warning(
            "endpoint_classifier: nature disagreement on endpoint %r — "
            "pre-set nature=%s vs marker-derived nature=%s (marker matched: %r)",
            endpoint.name, endpoint.nature.value, marker_nature.value, marker,
        )


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
