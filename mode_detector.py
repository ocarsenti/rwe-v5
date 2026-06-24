"""Mode detector — classifies user intent as REVIEW or DESIGN."""

from __future__ import annotations

from models import Mode

_REVIEW_MARKERS = [
    "protocol", "study", "publication", "endpoint", "rct",
    "observational study", "dossier", "trial", "registry",
    "existing", "submitted", "evaluated", "assessed",
    "primary endpoint", "secondary endpoint", "inclusion criteria",
]

_DESIGN_MARKERS = [
    "claim", "intended benefit", "target population",
    "desired demonstration", "unmet need", "product concept",
    "demonstrates", "should show", "aims to prove",
    "what evidence", "how to demonstrate", "generate evidence",
    "design a study", "what study", "propose a design",
]


def detect_mode(text: str) -> Mode:
    text_lower = text.lower()
    review_score = sum(1 for m in _REVIEW_MARKERS if m in text_lower)
    design_score = sum(1 for m in _DESIGN_MARKERS if m in text_lower)

    if review_score > design_score:
        return Mode.REVIEW
    if design_score > review_score:
        return Mode.DESIGN

    has_endpoints = "endpoint" in text_lower and ("name" in text_lower or "primary" in text_lower)
    if has_endpoints:
        return Mode.REVIEW

    return Mode.DESIGN
