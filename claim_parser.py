"""Claim parser — classifies clinical claims into epistemic levels."""

from __future__ import annotations

import re

from models import ClaimLevel, ClinicalClaim


# French terms included alongside English ones — this product's real market is
# France/HAS-CNEDiMTS, so claim text is routinely French. Without them, a French
# outcome claim that also mentions its mechanism (a common sponsor phrasing —
# "le dispositif stimule X, soulageant Y") matched only on MECHANISM_KEYWORDS
# and silently fell through to ClaimLevel.A instead of C/D, suppressing every
# C/D-gated bias flag and gap downstream (cf. FIBROREM case, 2026-07-12).
MECHANISM_KEYWORDS = [
    "mechanism", "mécanisme", "biolog", "receptor", "récepteur",
    "stimulat", "stimul", "modulat", "neurostimulat", "endorphin",
    "endorphine", "molecule", "moléculaire", "cellular", "cellulaire",
    "tissue", "tissulaire", "electromagnetic", "électromagnétique",
    "frequency", "fréquence", "wavelength", "longueur d'onde", "absorption",
]

PROCESS_KEYWORDS = [
    "workflow", "pathway", "parcours de soins", "parcours de santé",
    "triage", "referral", "orientation", "adressage", "care pathway",
    "monitoring", "monitorage", "télésurveillance", "télémonitorage",
    "alert", "alerte", "screening", "dépistage", "detection", "détection",
    "surveillance", "follow-up", "suivi", "scheduling", "coordination",
    "telemonitoring", "remote monitoring", "symptom tracking",
]

OUTCOME_KEYWORDS = [
    "survival", "survie", "mortality", "mortalité", "hospitalization",
    "hospitalisation", "complication", "pain", "douleur",
    "quality of life", "qualité de vie", "qol", "acuity", "progression",
    "recurrence", "récidive", "readmission", "réadmission", "functional",
    "fonctionnel", "disability", "handicap", "incapacité", "morbidity",
    "morbidité", "adverse event", "événement indésirable", "effet indésirable",
    "infection rate", "taux d'infection", "symptôme", "soulagement",
]


def _has_keywords(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def classify_claim(claim: ClinicalClaim) -> ClaimLevel:
    """Classify a clinical claim into its epistemic level."""
    combined = f"{claim.text} {claim.intervention} {claim.domain}".lower()

    mech_score = _has_keywords(combined, MECHANISM_KEYWORDS)
    proc_score = _has_keywords(combined, PROCESS_KEYWORDS)
    out_score = _has_keywords(combined, OUTCOME_KEYWORDS)

    has_mechanism = mech_score > 0
    has_process = proc_score > 0
    has_outcome = out_score > 0

    if has_mechanism and has_outcome:
        return ClaimLevel.D
    if has_mechanism and has_process:
        return ClaimLevel.D
    if has_process and has_outcome:
        return ClaimLevel.D
    if has_mechanism:
        return ClaimLevel.A
    if has_process:
        return ClaimLevel.B
    if has_outcome:
        return ClaimLevel.C

    if claim.endpoints:
        natures = {ep.nature.value for ep in claim.endpoints}
        if "OBJECTIVE" in natures:
            return ClaimLevel.C
        if "SUBJECTIVE" in natures:
            return ClaimLevel.C

    return ClaimLevel.B


def parse_claim(claim: ClinicalClaim) -> ClinicalClaim:
    """Parse and enrich a clinical claim with its level.

    Only classifies when level is unset — an explicit level (set by the caller,
    or already derived upstream by a more reliable classifier such as the LLM-based
    parse_claim_with_llm) must not be silently overwritten by this keyword heuristic.
    """
    if claim.level is None:
        claim.level = classify_claim(claim)
    return claim
