"""Main engine — unified entry point routing REVIEW and DESIGN modes.

Both modes use the SINGLE epistemic core.
"""

from __future__ import annotations

import json

from models import ClinicalClaim, DesignModeOutput, EngineOutput, GoldCaseOutput, Mode
from mode_detector import detect_mode
from epistemic_core import (
    parse_claim,
    classify_endpoints,
    build_causal_structure,
    detect_structural_issues,
    build_bias_detections,
    recommend_design,
    generate_repair_plan,
    generate_repair_plan_v2,
)
from epistemic_manifold import compute_review_position, compute_repair_delta
from regulatory_labeler import label_case
from design_mode import run_design_mode, run_design_mode_json
from cas_engine import evaluate_cas, determine_overall_verdict


# ===================================================================
# REVIEW MODE
# ===================================================================

def analyze(claim: ClinicalClaim, lang: str = "fr") -> EngineOutput:
    """REVIEW mode: analyze existing evidence."""
    claim = parse_claim(claim)
    endpoint_analyses = classify_endpoints(claim)
    structure = build_causal_structure(claim, endpoint_analyses)
    bias_flags = detect_structural_issues(claim, endpoint_analyses, structure)
    bias_detections = build_bias_detections(bias_flags, endpoint_analyses, structure)
    design = recommend_design(claim, endpoint_analyses, structure, bias_flags)

    repair_plan = generate_repair_plan(
        claim, endpoint_analyses, structure, bias_flags, bias_detections, design,
    )
    repair_plan_v2 = generate_repair_plan_v2(
        claim, endpoint_analyses, structure, bias_flags, bias_detections, design,
    )

    regulatory_readout = _build_regulatory_readout(
        claim, structure, bias_flags, design,
        repair_plan is not None, repair_plan_v2,
        lang=lang,
    )

    manifold_position = compute_review_position(
        claim, endpoint_analyses, structure, bias_flags, design.primary_design,
    )

    cas_output = None
    if (
        claim.device_alignment is not None
        and claim.population_alignment is not None
        and claim.context_alignment is not None
    ):
        cas_output = evaluate_cas(
            claim_text=claim.text,
            intervention=claim.intervention,
            domain=claim.domain,
            device=claim.device_alignment,
            population=claim.population_alignment,
            context=claim.context_alignment,
        )

    overall_verdict = determine_overall_verdict(structure, bias_detections, cas_output)

    output = EngineOutput(
        claim_level=claim.level,
        endpoint_analysis=endpoint_analyses,
        causal_structure=structure,
        bias_flags=bias_detections,
        design_recommendation=design,
        repair_plan=repair_plan,
        repair_plan_v2=repair_plan_v2,
        regulatory_readout=regulatory_readout,
        manifold_position=manifold_position,
        cas_output=cas_output,
        overall_verdict=overall_verdict,
    )

    if repair_plan_v2 and repair_plan_v2.status == "REPAIRABLE":
        repair_delta = compute_repair_delta(
            manifold_position, repair_plan_v2, claim, bias_flags,
        )
        output.repair_delta = repair_delta

    return output


def analyze_to_json(claim: ClinicalClaim) -> str:
    output = analyze(claim)
    return json.dumps(output.to_dict(), indent=2, ensure_ascii=False)


def analyze_to_gold(case_id: str, claim: ClinicalClaim) -> GoldCaseOutput:
    engine_output = analyze(claim)
    return label_case(case_id, claim, engine_output)


def analyze_to_gold_json(case_id: str, claim: ClinicalClaim) -> str:
    gold = analyze_to_gold(case_id, claim)
    return json.dumps(gold.to_dict(), indent=2, ensure_ascii=False)


# ===================================================================
# DESIGN MODE (delegates to design_mode.py, uses same epistemic core)
# ===================================================================

def design(claim_text: str, intervention: str, domain: str = "") -> DesignModeOutput:
    """DESIGN mode: generate evidence-generation pathways from a claim."""
    return run_design_mode(claim_text, intervention, domain)


def design_to_json(claim_text: str, intervention: str, domain: str = "") -> str:
    return run_design_mode_json(claim_text, intervention, domain)


# ===================================================================
# UNIFIED ENTRY POINT
# ===================================================================

def process(text: str, claim: ClinicalClaim | None = None,
            intervention: str = "", domain: str = ""):
    """Auto-detect mode and route to the appropriate pipeline."""
    mode = detect_mode(text)
    if mode == Mode.REVIEW and claim is not None:
        return analyze(claim)
    return run_design_mode(text, intervention or text, domain)


# ===================================================================
# INTERNAL
# ===================================================================

def _build_regulatory_readout(
    claim, structure, bias_flags, design, needs_repair, repair_v2,
    lang="fr",
) -> str:
    parts = []

    if lang == "fr":
        parts.append(
            f"Niveau de revendication : {claim.level.value}. "
            f"Structure causale : {structure.value}."
        )
        if bias_flags:
            flag_names = ", ".join(f.value for f in bias_flags)
            parts.append(f"Risques de biais identifiés : {flag_names}.")
        parts.append(f"Design recommandé : {design.primary_design.value}.")
        if repair_v2 and repair_v2.status == "NON_REPAIRABLE":
            parts.append(
                "NON RÉPARABLE — tous les critères de jugement dépendent "
                "structurellement du mécanisme d'action de l'intervention. "
                "Aucune inférence causale valide n'est possible avec les "
                "critères actuels. Une refonte fondamentale du cadre "
                "d'évaluation est nécessaire avant la soumission réglementaire."
            )
        elif needs_repair:
            parts.append(
                "RÉPARATION NÉCESSAIRE — le design d'étude actuel présente des "
                "problèmes structurels qui doivent être corrigés avant la "
                "soumission réglementaire."
            )
        else:
            parts.append(
                "Le design d'étude est structurellement solide pour la "
                "soumission réglementaire."
            )
    else:
        parts.append(
            f"Claim level: {claim.level.value}. "
            f"Causal structure: {structure.value}."
        )
        if bias_flags:
            flag_names = ", ".join(f.value for f in bias_flags)
            parts.append(f"Bias risks identified: {flag_names}.")
        parts.append(f"Recommended design: {design.primary_design.value}.")
        if repair_v2 and repair_v2.status == "NON_REPAIRABLE":
            parts.append(
                "NON-REPAIRABLE — all endpoints are structurally dependent on "
                "the intervention mechanism. No valid causal inference is possible "
                "under the current endpoint space. Fundamental redesign of the "
                "evaluation framework is required before regulatory submission."
            )
        elif needs_repair:
            parts.append(
                "REPAIR REQUIRED — the current study design has structural issues "
                "that must be addressed before regulatory submission."
            )
        else:
            parts.append(
                "Study design is structurally sound for regulatory submission."
            )

    return " ".join(parts)
