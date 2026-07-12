"""Causal graph builder — determines causal structure from claim + endpoints."""

from __future__ import annotations

from models import (
    BiasFlag,
    CausalRole,
    CausalStructure,
    ClaimLevel,
    ClinicalClaim,
    ComparatorFeasibility,
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
) -> tuple[list[BiasFlag], dict[BiasFlag, str]]:
    """Detect structural bias flags from the causal graph.

    Returns (flags, reasons): `reasons` maps each flag to a case-specific,
    human-checkable justification grounded in this dossier's actual field
    values — never the flag-type-level generic text from BIAS_DETAILS. For
    flags inherited from endpoint-level analysis, this is `ea.flag_reasons`
    (already computed by endpoint_classifier.py but previously dropped here,
    since `flags.update(ea.flags)` only kept the bare enum). For flags added
    directly at the structural level below, the reason is built here from the
    same claim/endpoint data that triggered the flag.
    """
    flags = set()
    reasons: dict[BiasFlag, str] = {}

    for ea in endpoint_analyses:
        flags.update(ea.flags)
        for f, r in ea.flag_reasons.items():
            # An endpoint-level flag can recur across several endpoints; keep
            # the first reason encountered rather than overwrite silently, so
            # the surfaced justification always traces back to one concrete
            # endpoint the reader can check against the source study.
            reasons.setdefault(f, r)

    if claim.level in (ClaimLevel.A, ClaimLevel.B):
        outcome_endpoints = [
            ea.endpoint.name for ea in endpoint_analyses
            if ea.nature == EndpointNature.OBJECTIVE
        ]
        if outcome_endpoints:
            flags.add(BiasFlag.MEDIATION_GAP)
            reasons[BiasFlag.MEDIATION_GAP] = (
                f"claim.level={claim.level.value} (mechanism/process-level claim), "
                f"but {len(outcome_endpoints)} endpoint(s) measure objective clinical "
                f"outcome(s) directly: {outcome_endpoints[:3]}"
            )

    if claim.level == ClaimLevel.D:
        has_process_endpoint = any(
            ea.nature == EndpointNature.OBJECTIVE and ea.causal_role == CausalRole.MEDIATED
            for ea in endpoint_analyses
        )
        if not has_process_endpoint:
            flags.add(BiasFlag.MEDIATION_GAP)
            reasons[BiasFlag.MEDIATION_GAP] = (
                f"claim.level=D (complete-chain outcome claim) but no endpoint has "
                f"nature=OBJECTIVE and causal_role=MEDIATED — no intermediate process "
                f"step linking mechanism to outcome is measured in this evidence base"
            )

    all_subjective = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    if all_subjective:
        flags.add(BiasFlag.PERCEPTION_BIAS)
        reasons[BiasFlag.PERCEPTION_BIAS] = (
            f"all {len(endpoint_analyses)} endpoint(s) have nature=SUBJECTIVE "
            f"(patient-reported) — none is OBJECTIVE or INSTRUMENTED"
        )

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
            matched_kw = next(
                kw for kw in ["monitoring", "triage", "screening", "alert", "detection"]
                if kw in claim_text
            )
            reasons[BiasFlag.PROCESS_TAUTOLOGY] = (
                f"intervention text matches process keyword '{matched_kw}', "
                f"claim.level=B, and {len(process_endpoints)} endpoint(s) have "
                f"nature=INSTRUMENTED — the device's own process is the endpoint"
            )

    if (
        claim.has_comparator is False
        and claim.level in (ClaimLevel.C, ClaimLevel.D)
        and claim.comparator_feasibility != ComparatorFeasibility.DIFFERENT_MODALITY
        and claim.comparator_feasibility != ComparatorFeasibility.NO_ALTERNATIVE
    ):
        flags.add(BiasFlag.NO_COMPARATOR)
        reasons[BiasFlag.NO_COMPARATOR] = (
            f"claim.has_comparator=False, claim.level={claim.level.value} "
            f"(outcome-level), comparator_feasibility={claim.comparator_feasibility.value} "
            f"(neither DIFFERENT_MODALITY nor NO_ALTERNATIVE, so a comparator was expected)"
        )

    return list(flags), reasons
