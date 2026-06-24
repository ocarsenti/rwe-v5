"""Design mode — generates all plausible evidence-generation pathways from a claim.

Workflow (strict order, no shortcut):
  1. Infer latent causal question
  2. Build target DAG
  3. Identify required/measurable mediators
  4. Identify acceptable/prohibited outcomes
  5. Compute identification requirements
  6. Generate candidate endpoint families
  7. Generate candidate study designs (full design space)
  8. Rank designs
  9. Compute regulatory manifold
  10. Produce regulatory strategy
"""

from __future__ import annotations

import json

from models import (
    CausalRole,
    ClinicalClaim,
    DesignModeOutput,
    Endpoint,
    EndpointNature,
)
from epistemic_core import (
    parse_claim,
    classify_endpoints,
    build_causal_structure,
    detect_structural_issues,
    assess_identification,
    infer_target_dag,
    compute_endpoint_families,
    generate_design_space,
    compute_regulatory_manifold,
)
from epistemic_manifold import compute_design_manifold


def _build_synthetic_claim(claim_text: str, intervention: str, domain: str) -> ClinicalClaim:
    return ClinicalClaim(
        text=claim_text,
        intervention=intervention,
        endpoints=[],
        domain=domain,
    )


def _build_regulatory_strategy(output: DesignModeOutput) -> str:
    best = output.regulatory_manifold.best_point()
    dag = output.target_dag
    ident = output.identification

    parts = [
        f"Stratégie réglementaire recommandée pour : \"{output.claim_text}\".",
        f"",
        f"Design optimal : {best.design.design_name} "
        f"(acceptabilité HAS = {best.regulatory_acceptability:.2f}, "
        f"risque biais = {best.bias_risk:.2f}).",
    ]

    if ident.blinding_needed:
        parts.append("CONDITION : aveugle (sham/double-blind) requis pour les critères subjectifs.")
    if ident.adjudication_needed:
        parts.append("CONDITION : adjudication indépendante requise pour les critères principaux.")
    if ident.external_data_needed:
        parts.append("CONDITION : source de données externe requise (registre civil, SNDS, PMSI).")
    if ident.mediator_measurement_needed:
        measured = [m for m in dag.mediators if m not in ("intermediate clinical process", "clinical decision")]
        if measured:
            parts.append(f"CONDITION : mesure des médiateurs requise ({', '.join(measured[:2])}).")

    if dag.prohibited_outcomes:
        parts.append(f"CRITÈRES INTERDITS : {', '.join(dag.prohibited_outcomes[:3])}.")

    primary_families = [f for f in output.endpoint_families if f.regulatory_weight == "PRIMARY"]
    if primary_families:
        top_eps = primary_families[0].endpoints[:2]
        parts.append(f"CRITÈRES PRIMAIRES RECOMMANDÉS : {', '.join(top_eps)}.")

    return "\n".join(parts)


def run_design_mode(
    claim_text: str,
    intervention: str,
    domain: str = "",
) -> DesignModeOutput:
    synthetic = _build_synthetic_claim(claim_text, intervention, domain)
    parsed = parse_claim(synthetic)

    dag = infer_target_dag(claim_text, intervention, domain)

    ep_analyses = classify_endpoints(parsed)
    structure = build_causal_structure(parsed, ep_analyses)
    bias_flags = detect_structural_issues(parsed, ep_analyses, structure)
    identification = assess_identification(parsed, ep_analyses, structure, bias_flags)

    endpoint_families = compute_endpoint_families(dag, identification)
    design_space = generate_design_space(claim_text, dag, identification, endpoint_families)
    manifold = compute_regulatory_manifold(design_space)

    epistemic = compute_design_manifold(
        design_space, identification, claim_text, domain,
    )

    output = DesignModeOutput(
        mode="DESIGN",
        claim_text=claim_text,
        intervention=intervention,
        domain=domain,
        target_dag=dag,
        identification=identification,
        endpoint_families=endpoint_families,
        design_space=design_space,
        regulatory_manifold=manifold,
        regulatory_strategy="",
        epistemic_manifold=epistemic,
    )
    output.regulatory_strategy = _build_regulatory_strategy(output)

    return output


def run_design_mode_json(
    claim_text: str,
    intervention: str,
    domain: str = "",
) -> str:
    output = run_design_mode(claim_text, intervention, domain)
    return json.dumps(output.to_dict(), indent=2, ensure_ascii=False)
