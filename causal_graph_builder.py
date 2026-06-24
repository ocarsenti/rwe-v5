"""Causal graph builder — determines causal structure from claim + endpoints."""

from __future__ import annotations

from models import (
    BiasFlag,
    CausalRole,
    CausalStructure,
    ClaimLevel,
    ClinicalClaim,
    EndpointAnalysis,
    EndpointNature,
)


def build_causal_structure(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
) -> CausalStructure:
    """Determine the overall causal structure of the study design."""

    has_circular = any(
        ea.causal_role == CausalRole.CIRCULAR for ea in endpoint_analyses
    )
    has_mediated = any(
        ea.causal_role == CausalRole.MEDIATED for ea in endpoint_analyses
    )

    primary_endpoints = [ea for ea in endpoint_analyses if ea.endpoint.is_primary]
    primary_circular = any(
        ea.causal_role == CausalRole.CIRCULAR for ea in primary_endpoints
    )

    if primary_circular:
        return CausalStructure.CIRCULAR

    if has_circular:
        all_circular = all(
            ea.causal_role == CausalRole.CIRCULAR for ea in endpoint_analyses
        )
        if all_circular:
            return CausalStructure.CIRCULAR
        return CausalStructure.MEDIATED

    if not endpoint_analyses:
        return CausalStructure.INVALID

    if claim.level == ClaimLevel.D:
        return CausalStructure.MEDIATED

    if has_mediated:
        return CausalStructure.MEDIATED

    if _has_mediation_gap(claim, endpoint_analyses):
        return CausalStructure.MEDIATED

    return CausalStructure.DIRECT


def _has_mediation_gap(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
) -> bool:
    """Check if there's a gap between claim level and endpoint level."""
    if claim.level in (ClaimLevel.A, ClaimLevel.B):
        has_outcome_endpoint = any(
            ea.nature == EndpointNature.OBJECTIVE for ea in endpoint_analyses
        )
        if has_outcome_endpoint:
            return True
    return False


def detect_structural_issues(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
) -> list[BiasFlag]:
    """Detect structural bias flags from the causal graph."""
    flags = set()

    for ea in endpoint_analyses:
        flags.update(ea.flags)

    if claim.level in (ClaimLevel.A, ClaimLevel.B):
        has_outcome = any(
            ea.nature == EndpointNature.OBJECTIVE for ea in endpoint_analyses
        )
        if has_outcome:
            flags.add(BiasFlag.MEDIATION_GAP)

    if claim.level == ClaimLevel.D:
        has_process_endpoint = any(
            ea.nature == EndpointNature.OBJECTIVE and ea.causal_role == CausalRole.MEDIATED
            for ea in endpoint_analyses
        )
        if not has_process_endpoint:
            flags.add(BiasFlag.MEDIATION_GAP)

    all_subjective = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    if all_subjective:
        flags.add(BiasFlag.PERCEPTION_BIAS)

    claim_text = f"{claim.text} {claim.intervention}".lower()
    intervention_is_process = any(
        kw in claim_text
        for kw in ["monitoring", "triage", "screening", "alert", "detection"]
    )
    if intervention_is_process and claim.level == ClaimLevel.B:
        process_endpoints = [
            ea for ea in endpoint_analyses
            if ea.nature == EndpointNature.INSTRUMENTED
        ]
        if process_endpoints:
            flags.add(BiasFlag.PROCESS_TAUTOLOGY)

    return list(flags)
