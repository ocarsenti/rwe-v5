"""CAS Engine — Claim Alignment Score computation.

Evaluates whether a study's evidence is ALIGNED with the device's claim,
across three dimensions: Device (I), Population (P), Context (C).

This is NOT a quality/ICS assessment — it measures correspondence between
what was studied and what is claimed.
"""

from __future__ import annotations

from models import (
    BiasDetection,
    CASGatingResult,
    CASOutput,
    CASRisk,
    CASVerdict,
    CarePathwayMatch,
    CausalStructure,
    ContextAlignment,
    ContextMatchType,
    DeviceAlignment,
    DeviceMatchType,
    EligibilityShift,
    OrganizationDependency,
    PopulationAlignment,
    PopulationMatchType,
)


# ---------------------------------------------------------------------------
# Distance tables
# ---------------------------------------------------------------------------

_D_DEVICE = {
    DeviceMatchType.EXACT_DEVICE: 0.0,
    DeviceMatchType.SAME_FAMILY: 0.3,
    DeviceMatchType.PROXY_DEVICE: 0.7,
    DeviceMatchType.DIFFERENT_DEVICE: 1.0,
    DeviceMatchType.UNKNOWN: 0.5,
}

_D_POP = {
    PopulationMatchType.EXACT_INDICATION: 0.0,
    PopulationMatchType.NARROWER_SUBGROUP: 0.3,
    PopulationMatchType.BROADER_POPULATION: 0.5,
    PopulationMatchType.DIFFERENT_POPULATION: 1.0,
    PopulationMatchType.UNKNOWN: 0.5,
}

_D_CONTEXT = {
    ContextMatchType.SAME_HEALTHCARE_SYSTEM: 0.0,
    ContextMatchType.PARTIALLY_COMPARABLE: 0.4,
    ContextMatchType.DIFFERENT_SYSTEM: 1.0,
    ContextMatchType.UNKNOWN: 0.6,
}

# Weights
W_DEVICE = 0.40
W_POP = 0.35
W_CONTEXT = 0.25


def compute_cas_score(d_device: float, d_pop: float, d_context: float) -> float:
    return 1.0 - (W_DEVICE * d_device + W_POP * d_pop + W_CONTEXT * d_context)


def apply_device_gate(d_device: float) -> CASGatingResult:
    if d_device > 0.5:
        return CASGatingResult(
            device_gate_passed=False,
            device_gate_reason="Device mismatch prevents claim validity",
        )
    return CASGatingResult(device_gate_passed=True)


def determine_verdict(cas_score: float, gating: CASGatingResult) -> CASVerdict:
    if not gating.device_gate_passed:
        return CASVerdict.REJECTED
    if cas_score >= 0.7:
        return CASVerdict.ACCEPTABLE
    if cas_score >= 0.5:
        return CASVerdict.WEAK_EVIDENCE
    return CASVerdict.REJECTED


def identify_risks(
    device: DeviceAlignment,
    population: PopulationAlignment,
    context: ContextAlignment,
    d_device: float,
    d_pop: float,
    d_context: float,
) -> list[CASRisk]:
    risks: list[CASRisk] = []

    if d_device >= 0.7:
        risks.append(CASRisk(
            dimension="DEVICE",
            risk_level="CRITICAL",
            description=f"Study uses a different device ({device.device_description_study}) "
                        f"than the claimed device ({device.device_description_claim}). "
                        "Evidence cannot support the claim.",
        ))
    elif d_device >= 0.3:
        risks.append(CASRisk(
            dimension="DEVICE",
            risk_level="HIGH",
            description=f"Study device ({device.device_description_study}) is in the same family "
                        f"but not identical to the claimed device ({device.device_description_claim}). "
                        "Extrapolation required.",
        ))

    if d_pop >= 0.5:
        risks.append(CASRisk(
            dimension="POPULATION",
            risk_level="CRITICAL" if d_pop >= 1.0 else "HIGH",
            description=f"Study population ({population.population_description_study}) "
                        f"does not match the claimed indication ({population.population_description_claim}).",
        ))
    elif d_pop >= 0.3:
        risks.append(CASRisk(
            dimension="POPULATION",
            risk_level="MODERATE",
            description=f"Study covers a narrower subgroup ({population.subgroup_description or population.population_description_study}) "
                        f"of the claimed indication ({population.population_description_claim}).",
        ))

    if population.eligibility_shift == EligibilityShift.MAJOR:
        risks.append(CASRisk(
            dimension="POPULATION",
            risk_level="HIGH",
            description="Major eligibility shift between study criteria and claimed indication.",
        ))

    if d_context >= 0.4:
        risks.append(CASRisk(
            dimension="CONTEXT",
            risk_level="HIGH" if d_context >= 1.0 else "MODERATE",
            description=f"Study conducted in {context.study_country or 'unknown context'}, "
                        f"target deployment is {context.target_country}. "
                        "Care pathway differences may limit transposability.",
        ))

    if context.care_pathway_match == CarePathwayMatch.NO:
        risks.append(CASRisk(
            dimension="CONTEXT",
            risk_level="HIGH",
            description="Study care pathway does not match the target healthcare system pathway.",
        ))
    elif context.care_pathway_match == CarePathwayMatch.PARTIAL:
        risks.append(CASRisk(
            dimension="CONTEXT",
            risk_level="MODERATE",
            description="Study care pathway only partially matches the target healthcare system "
                        "pathway. Extrapolation may be limited.",
        ))

    if context.organization_dependency == OrganizationDependency.HIGH:
        risks.append(CASRisk(
            dimension="CONTEXT",
            risk_level="MODERATE",
            description="Device effectiveness is highly dependent on organizational setup. "
                        "Results may not transfer to different care organizations.",
        ))

    return risks


def build_regulatory_interpretation(
    device: DeviceAlignment,
    population: PopulationAlignment,
    context: ContextAlignment,
    cas_score: float,
    verdict: CASVerdict,
    gating: CASGatingResult,
    lang: str = "fr",
) -> str:
    parts: list[str] = []

    if lang == "fr":
        if not gating.device_gate_passed:
            parts.append(
                f"REJET — Le dispositif étudié ({device.device_description_study}) "
                f"ne correspond pas au dispositif revendiqué ({device.device_description_claim}). "
                "Les données ne peuvent pas soutenir la revendication."
            )
        else:
            if verdict == CASVerdict.ACCEPTABLE:
                parts.append(
                    f"Score CAS = {cas_score:.2f} — ACCEPTABLE. "
                    "L'étude est alignée avec la revendication."
                )
            elif verdict == CASVerdict.WEAK_EVIDENCE:
                parts.append(
                    f"Score CAS = {cas_score:.2f} — ÉVIDENCE FAIBLE. "
                    "Des écarts existent entre l'étude et la revendication."
                )
            else:
                parts.append(
                    f"Score CAS = {cas_score:.2f} — REJETÉ. "
                    "L'écart entre l'étude et la revendication est trop important."
                )

        match device.device_match_type:
            case DeviceMatchType.EXACT_DEVICE:
                parts.append("Dispositif : données spécifiques au dispositif évalué.")
            case DeviceMatchType.SAME_FAMILY:
                parts.append(
                    f"Dispositif : données issues d'un dispositif de la même famille "
                    f"({device.device_description_study}). Extrapolation nécessaire."
                )
            case DeviceMatchType.PROXY_DEVICE:
                parts.append(
                    f"Dispositif : données issues d'un dispositif proxy "
                    f"({device.device_description_study}). "
                    "L'extrapolation au dispositif revendiqué est questionnable."
                )
            case DeviceMatchType.DIFFERENT_DEVICE:
                parts.append("Dispositif : aucune donnée spécifique au dispositif évalué.")
            case _:
                parts.append("Dispositif : correspondance non déterminée.")

        match population.population_match_type:
            case PopulationMatchType.EXACT_INDICATION:
                parts.append("Population : la population étudiée correspond à l'indication revendiquée.")
            case PopulationMatchType.NARROWER_SUBGROUP:
                parts.append(
                    f"Population : l'étude couvre un sous-groupe "
                    f"({population.subgroup_description or population.population_description_study}) "
                    f"de l'indication revendiquée ({population.population_description_claim})."
                )
            case PopulationMatchType.BROADER_POPULATION:
                parts.append(
                    "Population : la population étudiée est plus large que l'indication revendiquée."
                )
            case PopulationMatchType.DIFFERENT_POPULATION:
                parts.append(
                    f"Population : la population étudiée ({population.population_description_study}) "
                    f"ne correspond pas à l'indication revendiquée ({population.population_description_claim})."
                )
            case _:
                parts.append("Population : correspondance non déterminée.")

        match context.context_match_type:
            case ContextMatchType.SAME_HEALTHCARE_SYSTEM:
                parts.append("Contexte : étude réalisée dans le même système de soins que le contexte cible.")
            case ContextMatchType.PARTIALLY_COMPARABLE:
                parts.append(
                    f"Contexte : étude réalisée dans un contexte partiellement comparable "
                    f"({context.study_country}). La transposabilité est limitée."
                )
            case ContextMatchType.DIFFERENT_SYSTEM:
                parts.append(
                    f"Contexte : étude réalisée dans un système de soins différent "
                    f"({context.study_country}). Les résultats ne sont pas directement transposables."
                )
            case _:
                parts.append("Contexte : transposabilité non déterminée.")

    else:
        if not gating.device_gate_passed:
            parts.append(
                f"REJECTED — Study device ({device.device_description_study}) "
                f"does not match claimed device ({device.device_description_claim}). "
                "Data cannot support the claim."
            )
        else:
            if verdict == CASVerdict.ACCEPTABLE:
                parts.append(f"CAS Score = {cas_score:.2f} — ACCEPTABLE. Study is aligned with the claim.")
            elif verdict == CASVerdict.WEAK_EVIDENCE:
                parts.append(f"CAS Score = {cas_score:.2f} — WEAK EVIDENCE. Gaps exist between study and claim.")
            else:
                parts.append(f"CAS Score = {cas_score:.2f} — REJECTED. Gap between study and claim is too large.")

        match device.device_match_type:
            case DeviceMatchType.EXACT_DEVICE:
                parts.append("Device: data specific to the evaluated device.")
            case DeviceMatchType.SAME_FAMILY:
                parts.append(f"Device: data from a same-family device ({device.device_description_study}). Extrapolation required.")
            case DeviceMatchType.PROXY_DEVICE:
                parts.append(f"Device: data from a proxy device ({device.device_description_study}). Extrapolation questionable.")
            case DeviceMatchType.DIFFERENT_DEVICE:
                parts.append("Device: no device-specific data available.")
            case _:
                parts.append("Device: match undetermined.")

        match population.population_match_type:
            case PopulationMatchType.EXACT_INDICATION:
                parts.append("Population: study population matches claimed indication.")
            case PopulationMatchType.NARROWER_SUBGROUP:
                parts.append(f"Population: study covers a subgroup ({population.subgroup_description or population.population_description_study}) of the claimed indication.")
            case PopulationMatchType.BROADER_POPULATION:
                parts.append("Population: study population is broader than claimed indication.")
            case PopulationMatchType.DIFFERENT_POPULATION:
                parts.append(f"Population: study population ({population.population_description_study}) does not match claimed indication ({population.population_description_claim}).")
            case _:
                parts.append("Population: match undetermined.")

        match context.context_match_type:
            case ContextMatchType.SAME_HEALTHCARE_SYSTEM:
                parts.append("Context: study conducted in the same healthcare system.")
            case ContextMatchType.PARTIALLY_COMPARABLE:
                parts.append(f"Context: study conducted in a partially comparable system ({context.study_country}). Limited transposability.")
            case ContextMatchType.DIFFERENT_SYSTEM:
                parts.append(f"Context: study conducted in a different healthcare system ({context.study_country}). Results not directly transferable.")
            case _:
                parts.append("Context: transposability undetermined.")

    return "\n".join(parts)


def evaluate_cas(
    claim_text: str,
    intervention: str,
    domain: str,
    device: DeviceAlignment,
    population: PopulationAlignment,
    context: ContextAlignment,
    lang: str = "fr",
) -> CASOutput:
    d_device = _D_DEVICE[device.device_match_type]
    d_pop = _D_POP[population.population_match_type]
    d_context = _D_CONTEXT[context.context_match_type]

    cas_score = compute_cas_score(d_device, d_pop, d_context)
    gating = apply_device_gate(d_device)
    verdict = determine_verdict(cas_score, gating)

    risks = identify_risks(device, population, context, d_device, d_pop, d_context)

    interpretation = build_regulatory_interpretation(
        device, population, context, cas_score, verdict, gating, lang=lang,
    )

    return CASOutput(
        claim_text=claim_text,
        intervention=intervention,
        domain=domain,
        device_alignment=device,
        population_alignment=population,
        context_alignment=context,
        d_device=d_device,
        d_population=d_pop,
        d_context=d_context,
        cas_score=cas_score,
        gating=gating,
        verdict=verdict,
        risks=risks,
        regulatory_interpretation=interpretation,
    )


# ---------------------------------------------------------------------------
# Overall verdict — combines CAS (alignment) with the epistemic core's causal
# structure and bias severity, which evaluate_cas() deliberately never sees.
#
# CAS_score/CASOutput.verdict stay exactly as before (pure alignment, unchanged,
# still covered by their own unit tests below) — evaluate_cas() measures whether
# the STUDY DATA corresponds to the CLAIM (right device/population/context), by
# design not a quality/ICS assessment (see module docstring). But nothing in the
# engine ever combined that with whether the evidence itself is causally sound
# (CIRCULAR structure) or carries a confirmed HIGH-severity bias — so a dossier
# could have a broken causal structure or a HIGH-severity bias flag and still be
# reported "CAS: ACCEPTABLE" purely because its device/population/context lined
# up. Audited against 7 real CNEDiMTS rejections in the 34-dossier corpus
# (2026-07-08): CAS alone caught 0/7. Two earlier, looser versions of this
# function were tried and rejected after re-auditing against the 27
# primo-inscription dossiers HAS actually accepted (2026-07-09, same corpus):
# (1) a lone MEDIUM-severity bias flag alone (~18% precision: 2 real rejects
# vs 9 accepted dossiers carried exactly one), and (2) a lone HIGH-severity
# flag or any ≥2 co-occurring flags without a broken causal structure
# (~17% precision: 1 real reject vs 5-9 accepted dossiers, depending on the
# exact variant) — both too noisy standalone signals in this sample, between
# them responsible for pulling 19/27 and then 8-9/27 accepted dossiers down
# from ACCEPTABLE. The only signal that held up cleanly: causal_structure
# CIRCULAR/INVALID, true in 3/3 CIRCULAR dossiers in the reject sample and in
# 0 of the 27 accepted ones (the sole CIRCULAR-and-accepted case, DURAWALK
# 7793, is a known structure-classification bug upstream of this function,
# not a genuine counterexample). So bias severity is now used only to decide
# how bad a broken structure is (REJECTED vs WEAK_EVIDENCE), never to trigger
# a downgrade on its own — trades one real reject (VIS-RX 7425, caught only
# by a lone NO_COMPARATOR) for eliminating every bias-flag-driven false
# positive on the 27 accepted dossiers.
# ---------------------------------------------------------------------------

_VERDICT_RANK = {CASVerdict.ACCEPTABLE: 0, CASVerdict.WEAK_EVIDENCE: 1, CASVerdict.REJECTED: 2}
_HIGH_SEVERITY_BIAS = {"HIGH"}


def determine_overall_verdict(
    causal_structure: CausalStructure,
    bias_flags: list[BiasDetection],
    cas_output: CASOutput | None,
) -> CASVerdict:
    """Worst-of(CAS alignment, causal structure integrity). Bias severity only
    escalates an already-broken causal structure to REJECTED — a bias flag on
    its own, of any severity or count, never downgrades alone. See module
    comment above for why."""
    cas_verdict = cas_output.verdict if cas_output is not None else CASVerdict.ACCEPTABLE

    structure_broken = causal_structure in (CausalStructure.CIRCULAR, CausalStructure.INVALID)
    has_high_bias = any(bd.severity in _HIGH_SEVERITY_BIAS for bd in bias_flags)

    if structure_broken and has_high_bias:
        causal_bias_verdict = CASVerdict.REJECTED
    elif structure_broken:
        causal_bias_verdict = CASVerdict.WEAK_EVIDENCE
    else:
        causal_bias_verdict = CASVerdict.ACCEPTABLE

    return max((cas_verdict, causal_bias_verdict), key=lambda v: _VERDICT_RANK[v])
