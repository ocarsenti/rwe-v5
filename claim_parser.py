"""Claim parser — classifies clinical claims into epistemic levels."""

from __future__ import annotations

import re

from models import ClaimLevel, ClinicalClaim


MECHANISM_KEYWORDS = [
    "mechanism", "biolog", "receptor", "stimulat", "modulat",
    "neurostimulat", "endorphin", "molecule", "cellular", "tissue",
    "electromagnetic", "frequency", "wavelength", "absorption",
]

PROCESS_KEYWORDS = [
    "workflow", "pathway", "triage", "referral", "care pathway",
    "monitoring", "alert", "screening", "detection", "surveillance",
    "follow-up", "scheduling", "coordination", "telemonitoring",
    "remote monitoring", "symptom tracking",
]

OUTCOME_KEYWORDS = [
    "survival", "mortality", "hospitalization", "complication",
    "pain", "quality of life", "qol", "acuity", "progression",
    "recurrence", "readmission", "functional", "disability",
    "morbidity", "adverse event", "infection rate",
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
    """Parse and enrich a clinical claim with its level."""
    claim.level = classify_claim(claim)
    return claim
