"""FastAPI backend for RWE-v5 epistemic engine."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import io

from typing import Optional
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    CarePathwayMatch,
    CausalRole,
    ClinicalClaim,
    ContextAlignment,
    ContextMatchType,
    DeviceAlignment,
    DeviceMatchType,
    EligibilityShift,
    Endpoint,
    EndpointNature,
    OrganizationDependency,
    PopulationAlignment,
    PopulationMatchType,
)
from engine import analyze, design
from cas_engine import evaluate_cas
from llm_cas_parser import parse_cas_smart
from gold_dataset import process_all_cases, generate_gold_dataset, ALL_CASES
from llm_claim_parser import parse_claim_smart
from translations import translate_engine_output
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from llm_evidence_parser import (
    _parse_study_object_result,
    parse_study_object_with_llm,
)
from gap_repair_engine import repair_comparison
from llm_repair_summary import generate_repair_summary
from guest_router import guest_router, admin_router
from guest_store import verify_token, consume_token


_MAX_PDF_PAGES = 5
_MAX_PDF_BYTES = 8 * 1024 * 1024  # 8 MB


def _extract_pdf_bytes(content: bytes, max_pages: int = _MAX_PDF_PAGES) -> tuple[str, int, int]:
    """Extract text from PDF bytes (pdfplumber). Returns (text, pages_read, total_pages)."""
    import pdfplumber  # type: ignore
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        total_pages = len(pdf.pages)
        pages = pdf.pages[:max_pages]
        if not pages:
            raise ValueError("PDF vide ou illisible")
        text = "\n\n".join(p.extract_text() or "" for p in pages)
    if not text.strip():
        raise ValueError("Impossible d'extraire le texte — PDF scanné ou protégé")
    return text.strip(), len(pages), total_pages


def _build_gap_response(report, repair, claim, epistemic):
    """Shared serializer for gap + repair results."""
    return {
        "overall_risk": report.overall_risk.value,
        "is_fully_repairable": repair.is_fully_repairable,
        "repair_summary": repair.repair_summary,
        "gaps": [
            {
                "dimension": g.dimension,
                "severity": g.severity,
                "description": g.description,
                "has_critique": str(g.has_critique) if g.has_critique else None,
            }
            for g in report.gaps
        ],
        "actions": [
            {
                "gap_dimension": a.gap_dimension,
                "gap_severity": a.gap_severity,
                "repair_type": a.repair_type.value if a.repair_type else None,
                "description": a.description,
                "specific_suggestion": a.specific_suggestion,
                "effort": a.effort.value if a.effort else None,
                "removes_risk": a.removes_risk or [],
            }
            for a in repair.actions
        ],
    }

app = FastAPI(title="RWE-v5 Epistemic Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guest_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


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


# ===================================================================
# CAS (Claim Alignment Score) — Module 3
# ===================================================================

class DeviceAlignmentInput(BaseModel):
    device_match_type: str
    device_description_claim: str
    device_description_study: str
    justification: str = ""


class PopulationAlignmentInput(BaseModel):
    population_match_type: str
    population_description_claim: str
    population_description_study: str
    subgroup_description: str = ""
    eligibility_shift: str = "NONE"
    justification: str = ""


class ContextAlignmentInput(BaseModel):
    context_match_type: str
    care_pathway_match: str
    organization_dependency: str
    study_country: str = ""
    target_country: str = "France"
    justification: str = ""


class CASRequest(BaseModel):
    claim_text: str
    intervention: str
    domain: str = ""
    device: DeviceAlignmentInput
    population: PopulationAlignmentInput
    context: ContextAlignmentInput
    lang: str = "fr"


@app.post("/api/cas")
def cas_endpoint(req: CASRequest):
    """Evaluate Claim Alignment Score for a study."""
    device = DeviceAlignment(
        device_match_type=DeviceMatchType(req.device.device_match_type),
        device_description_claim=req.device.device_description_claim,
        device_description_study=req.device.device_description_study,
        justification=req.device.justification,
    )
    population = PopulationAlignment(
        population_match_type=PopulationMatchType(req.population.population_match_type),
        population_description_claim=req.population.population_description_claim,
        population_description_study=req.population.population_description_study,
        subgroup_description=req.population.subgroup_description,
        eligibility_shift=EligibilityShift(req.population.eligibility_shift),
        justification=req.population.justification,
    )
    context = ContextAlignment(
        context_match_type=ContextMatchType(req.context.context_match_type),
        care_pathway_match=CarePathwayMatch(req.context.care_pathway_match),
        organization_dependency=OrganizationDependency(req.context.organization_dependency),
        study_country=req.context.study_country,
        target_country=req.context.target_country,
        justification=req.context.justification,
    )

    result = evaluate_cas(
        claim_text=req.claim_text,
        intervention=req.intervention,
        domain=req.domain,
        device=device,
        population=population,
        context=context,
        lang=req.lang,
    )
    return result.to_dict()


class SmartCASRequest(BaseModel):
    claim_text: str
    study_text: str
    lang: str = "fr"


@app.post("/api/smart-cas")
def smart_cas_endpoint(req: SmartCASRequest):
    """Parse claim + study with LLM, then evaluate CAS."""
    parsed = parse_cas_smart(req.claim_text, req.study_text, lang=req.lang)
    if parsed is None:
        return {"error": "LLM parsing failed", "status": "error"}

    da = parsed.get("device_alignment", {})
    pa = parsed.get("population_alignment", {})
    ca = parsed.get("context_alignment", {})

    device = DeviceAlignment(
        device_match_type=DeviceMatchType(da.get("device_match_type", "UNKNOWN")),
        device_description_claim=da.get("device_description_claim", ""),
        device_description_study=da.get("device_description_study", ""),
        justification=da.get("justification", ""),
    )
    population = PopulationAlignment(
        population_match_type=PopulationMatchType(pa.get("population_match_type", "UNKNOWN")),
        population_description_claim=pa.get("population_description_claim", ""),
        population_description_study=pa.get("population_description_study", ""),
        subgroup_description=pa.get("subgroup_description", ""),
        eligibility_shift=EligibilityShift(pa.get("eligibility_shift", "NONE")),
        justification=pa.get("justification", ""),
    )
    context = ContextAlignment(
        context_match_type=ContextMatchType(ca.get("context_match_type", "UNKNOWN")),
        care_pathway_match=CarePathwayMatch(ca.get("care_pathway_match", "UNKNOWN")),
        organization_dependency=OrganizationDependency(ca.get("organization_dependency", "LOW")),
        study_country=ca.get("study_country", ""),
        target_country=ca.get("target_country", "France"),
        justification=ca.get("justification", ""),
    )

    claim_parsed = parsed.get("claim_parsed", {})
    intervention = claim_parsed.get("device_name", "")
    domain = claim_parsed.get("domain", "")

    result = evaluate_cas(
        claim_text=req.claim_text,
        intervention=intervention,
        domain=domain,
        device=device,
        population=population,
        context=context,
        lang=req.lang,
    )

    output = result.to_dict()
    output["_parse_info"] = {
        "claim_parsed": claim_parsed,
        "study_parsed": parsed.get("study_parsed", {}),
    }
    return output


# ===================================================================
# DIAGNOSE-REPAIR — Mode Premium
# ===================================================================

class DiagnoseRepairRequest(BaseModel):
    claim_text: str
    intervention: str = ""
    domain: str = ""
    endpoints_text: str = ""
    study_design: str = "SINGLE_ARM"
    n_patients: int | None = None
    follow_up_months: float | None = None
    has_comparator: bool = False
    primary_endpoint_name: str = ""
    primary_endpoint_type: str = "OBJECTIVE"
    device_match_type: str = "EXACT_DEVICE"
    lang: str = "fr"


@app.post("/api/diagnose-repair")
def diagnose_repair_endpoint(req: DiagnoseRepairRequest):
    """Full diagnostic + repair pipeline: claim + study → gaps + repair plan."""
    full_text = req.claim_text
    if req.intervention:
        full_text += f"\nIntervention: {req.intervention}"
    if req.domain:
        full_text += f"\nDomaine: {req.domain}"
    if req.endpoints_text:
        full_text += f"\nEndpoints: {req.endpoints_text}"

    claim = parse_claim_smart(full_text, lang=req.lang)
    if req.intervention and not claim.intervention:
        claim.intervention = req.intervention
    if req.domain and not claim.domain:
        claim.domain = req.domain

    is_randomized = req.study_design == "RCT"
    blinding = "DOUBLE_BLIND" if is_randomized else "OPEN_LABEL"

    study_json: dict = {
        "acronym": "Étude soumise",
        "study_design": req.study_design,
        "is_randomized": is_randomized,
        "blinding_level": blinding,
        "has_comparator": req.has_comparator,
        "n_patients": req.n_patients,
        "follow_up_months": req.follow_up_months,
        "longest_follow_up_months": req.follow_up_months,
        "study_countries": ["France"],
        "key_safety_signals": [],
        "endpoints": (
            [
                {
                    "name": req.primary_endpoint_name,
                    "is_primary": True,
                    "is_validated_surrogate": False,
                    "is_independently_adjudicated": False,
                    "result_direction": "SUPERIOR",
                    "reached_significance": True,
                }
            ]
            if req.primary_endpoint_name
            else []
        ),
        "device_alignment": {
            "device_match_type": req.device_match_type,
            "device_description_study": claim.intervention or req.intervention,
            "device_description_claim": claim.intervention or req.intervention,
            "justification": "",
        },
        "population_alignment": {
            "population_match_type": "EXACT_INDICATION",
            "population_description_study": "",
            "population_description_claim": "",
            "eligibility_shift": "NONE",
            "justification": "",
        },
        "context_alignment": {
            "context_match_type": "SAME_HEALTHCARE_SYSTEM",
            "study_country": "France",
            "target_country": "France",
            "care_pathway_match": "YES",
            "organization_dependency": "LOW",
            "justification": "",
        },
    }

    study = _parse_study_object_result(study_json, claim.intervention, claim.text)
    enrich_claim_with_study_object(claim, study)
    epistemic = analyze(claim, lang=req.lang)
    epistemic_dict = translate_engine_output(epistemic.to_dict(), lang=req.lang)
    report = compare_claim_to_study(claim, study, epistemic_output=epistemic)
    repair = repair_comparison(report, claim, epistemic_output=epistemic)

    gaps = [
        {
            "dimension": g.dimension,
            "severity": g.severity,
            "description": g.description,
            "has_critique": str(g.has_critique) if g.has_critique else None,
        }
        for g in report.gaps
    ]

    actions = [
        {
            "gap_dimension": a.gap_dimension,
            "gap_severity": a.gap_severity,
            "repair_type": a.repair_type.value if a.repair_type else None,
            "description": a.description,
            "specific_suggestion": a.specific_suggestion,
            "effort": a.effort.value if a.effort else None,
            "removes_risk": a.removes_risk or [],
        }
        for a in repair.actions
    ]

    return {
        "epistemic": epistemic_dict,
        "overall_risk": report.overall_risk.value,
        "is_fully_repairable": repair.is_fully_repairable,
        "repair_summary": repair.repair_summary,
        "gaps": gaps,
        "actions": actions,
        "_parse_info": {
            "intervention": claim.intervention,
            "domain": claim.domain,
            "claim_level": claim.level.value if claim.level else None,
            "endpoints": [
                {
                    "name": ep.name,
                    "nature": ep.nature.value,
                    "causal_role": ep.causal_role.value,
                    "is_primary": ep.is_primary,
                }
                for ep in claim.endpoints
            ],
        },
    }


# ===================================================================
# DIAGNOSE-PREMIUM — PDF upload + full diagnostic + repair
# ===================================================================

@app.post("/api/diagnose-premium")
async def diagnose_premium_endpoint(
    claim_text: str = Form(""),
    intervention: str = Form(""),
    domain: str = Form(""),
    lang: str = Form("fr"),
    pdf_file: UploadFile = File(None),
    x_guest_token: Optional[str] = Header(None),
):
    """Premium endpoint: PDF abstract → full StudyObject → gaps + repair plan."""
    # Guest token quota check
    if x_guest_token:
        ok, reason, _ = verify_token(x_guest_token)
        if not ok:
            raise HTTPException(status_code=403, detail=reason)

    # 1. Parse claim text → ClinicalClaim
    full_text = claim_text.strip()
    if intervention.strip():
        full_text = f"Intervention: {intervention}. " + full_text
    if domain.strip():
        full_text = full_text + f" Domaine: {domain}."
    claim = parse_claim_smart(full_text, lang=lang)
    if intervention.strip() and not claim.intervention:
        claim.intervention = intervention.strip()
    if domain.strip() and not claim.domain:
        claim.domain = domain.strip()

    # 2. Extract PDF + parse into StudyObject via LLM
    pdf_info: dict = {}
    if pdf_file and pdf_file.filename:
        content = await pdf_file.read()
        if len(content) > _MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF trop volumineux (max 8 Mo)")
        try:
            pdf_text, pages_read, total_pages = _extract_pdf_bytes(content, max_pages=_MAX_PDF_PAGES)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        study = parse_study_object_with_llm(
            study_text=pdf_text,
            claim_device=intervention or claim_text[:80],
            claim_indication=claim_text,
        )

        pdf_info = {
            "filename": pdf_file.filename,
            "pages_read": pages_read,
            "total_pages": total_pages,
            "truncated": total_pages > _MAX_PDF_PAGES,
            "chars_extracted": len(pdf_text),
        }
    else:
        # No PDF — return early with just epistemic analysis
        epistemic = analyze(claim, lang=lang)
        epistemic_dict = translate_engine_output(epistemic.to_dict(), lang=lang)
        epistemic_dict["_parse_info"] = {
            "intervention": claim.intervention,
            "domain": claim.domain,
            "claim_level": claim.level.value if claim.level else None,
        }
        epistemic_dict["_no_pdf"] = True
        return epistemic_dict

    # 3. Enrich claim + run full pipeline
    enrich_claim_with_study_object(claim, study)
    epistemic = analyze(claim, lang=lang)
    epistemic_dict = translate_engine_output(epistemic.to_dict(), lang=lang)
    report = compare_claim_to_study(claim, study, epistemic_output=epistemic)
    repair = repair_comparison(report, claim, epistemic_output=epistemic)

    result = _build_gap_response(report, repair, claim, epistemic)
    result["epistemic"] = epistemic_dict
    result["_parse_info"] = {
        "intervention": claim.intervention,
        "domain": claim.domain,
        "claim_level": claim.level.value if claim.level else None,
        "study_acronym": study.acronym or "",
        "study_design": study.study_design.value if study.study_design else None,
        "n_patients": study.n_patients,
        "pdf": pdf_info,
        "endpoints": [
            {
                "name": ep.name,
                "nature": ep.nature.value,
                "causal_role": ep.causal_role.value,
                "is_primary": ep.is_primary,
            }
            for ep in claim.endpoints
        ],
    }
    try:
        result["llm_summary"] = generate_repair_summary(result, lang=lang)
    except Exception:
        result["llm_summary"] = None

    if x_guest_token:
        consume_token(x_guest_token)

    return result
