"""FastAPI backend for RWE-v5 epistemic engine."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    CausalRole,
    ClinicalClaim,
    Endpoint,
    EndpointNature,
)
from engine import analyze, design
from gold_dataset import process_all_cases, generate_gold_dataset, ALL_CASES
from llm_claim_parser import parse_claim_smart
from translations import translate_engine_output

app = FastAPI(title="RWE-v5 Epistemic Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EndpointInput(BaseModel):
    name: str
    nature: str  # OBJECTIVE, SUBJECTIVE, INSTRUMENTED
    causal_role: str  # INDEPENDENT, MEDIATED, CIRCULAR
    is_primary: bool = False
    description: str = ""


class ReviewRequest(BaseModel):
    text: str
    intervention: str
    endpoints: list[EndpointInput]
    domain: str = ""


class ParseRequest(BaseModel):
    text: str


class DesignRequest(BaseModel):
    claim_text: str
    intervention: str
    domain: str = ""


def _to_domain_endpoint(ep: EndpointInput) -> Endpoint:
    return Endpoint(
        name=ep.name,
        nature=EndpointNature(ep.nature),
        causal_role=CausalRole(ep.causal_role),
        is_primary=ep.is_primary,
        description=ep.description,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "RWE-v5"}


@app.post("/api/parse-claim")
def parse_claim_endpoint(req: ParseRequest):
    """Parse free-text clinical claim using LLM and return structured data."""
    claim = parse_claim_smart(req.text)
    return {
        "text": claim.text,
        "intervention": claim.intervention,
        "domain": claim.domain,
        "claim_level": claim.level.value if claim.level else None,
        "endpoints": [
            {
                "name": ep.name,
                "nature": ep.nature.value,
                "causal_role": ep.causal_role.value,
                "is_primary": ep.is_primary,
                "description": ep.description,
            }
            for ep in claim.endpoints
        ],
    }


@app.post("/api/review")
def review_endpoint(req: ReviewRequest):
    claim = ClinicalClaim(
        text=req.text,
        intervention=req.intervention,
        endpoints=[_to_domain_endpoint(ep) for ep in req.endpoints],
        domain=req.domain,
    )
    result = analyze(claim)
    return result.to_dict()


class SmartReviewRequest(BaseModel):
    text: str
    intervention: str = ""
    domain: str = ""
    endpoints_text: str = ""
    lang: str = "fr"


@app.post("/api/smart-review")
def smart_review_endpoint(req: SmartReviewRequest):
    """Parse free-text fields with LLM, then run the full review analysis."""
    full_text = req.text
    if req.intervention:
        full_text += f"\nIntervention: {req.intervention}"
    if req.domain:
        full_text += f"\nDomaine: {req.domain}"
    if req.endpoints_text:
        full_text += f"\nEndpoints: {req.endpoints_text}"

    parsed = parse_claim_smart(full_text, lang=req.lang)

    if req.intervention and not parsed.intervention:
        parsed.intervention = req.intervention
    if req.domain and not parsed.domain:
        parsed.domain = req.domain

    result = analyze(parsed, lang=req.lang)

    parse_info = {
        "intervention": parsed.intervention,
        "domain": parsed.domain,
        "claim_level": parsed.level.value if parsed.level else None,
        "endpoints": [
            {
                "name": ep.name,
                "nature": ep.nature.value,
                "causal_role": ep.causal_role.value,
                "is_primary": ep.is_primary,
                "description": ep.description,
            }
            for ep in parsed.endpoints
        ],
    }

    output = result.to_dict()
    output = translate_engine_output(output, lang=req.lang)
    output["_parse_info"] = parse_info
    return output


@app.post("/api/design")
def design_endpoint(req: DesignRequest):
    result = design(req.claim_text, req.intervention, req.domain)
    return result.to_dict()


class SmartDesignRequest(BaseModel):
    text: str
    intervention: str = ""
    domain: str = ""
    lang: str = "fr"


@app.post("/api/smart-design")
def smart_design_endpoint(req: SmartDesignRequest):
    """Parse free-text with LLM, then run design mode."""
    full_text = req.text
    if req.intervention:
        full_text += f"\nIntervention: {req.intervention}"
    if req.domain:
        full_text += f"\nDomaine: {req.domain}"

    parsed = parse_claim_smart(full_text, lang=req.lang)

    intervention = req.intervention or parsed.intervention or req.text
    domain = req.domain or parsed.domain or ""

    result = design(parsed.text, intervention, domain)

    output = result.to_dict()
    output["_parse_info"] = {
        "intervention": parsed.intervention,
        "domain": parsed.domain,
        "claim_level": parsed.level.value if parsed.level else None,
    }
    return output


@app.get("/api/gold-cases")
def gold_cases():
    cases = process_all_cases()
    return [c.to_dict() for c in cases]


@app.get("/api/gold-dataset")
def gold_dataset():
    rows = generate_gold_dataset()
    return [r.to_dict() for r in rows]


@app.get("/api/gold-claims")
def gold_claims():
    """Return the raw claim data for each gold case (for pre-filling forms)."""
    results = []
    for case_fn in ALL_CASES:
        case_id, claim = case_fn()
        results.append({
            "case_id": case_id,
            "text": claim.text,
            "intervention": claim.intervention,
            "domain": claim.domain,
            "endpoints": [
                {
                    "name": ep.name,
                    "nature": ep.nature.value,
                    "causal_role": ep.causal_role.value,
                    "is_primary": ep.is_primary,
                    "description": ep.description,
                }
                for ep in claim.endpoints
            ],
        })
    return results
