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


# Ajouté le 2026-07-29 (objection d'Olivier sur le cas Miroki) : une
# intervention à présence physique perceptible (robot, animal, thérapeute en
# personne...) ne peut pas être masquée au participant — contrairement à un
# comprimé (placebo) ou parfois une chirurgie (sham surgery). Le moteur
# affichait "aveugle/double-blind requis" sans cette distinction, ce qui est
# techniquement vrai (l'endpoint est subjectif) mais donne une consigne
# infaisable pour ce type de dispositif. La bonne pratique méthodologique
# dans ce cas n'est pas d'abandonner l'aveugle, mais de le déplacer : masquer
# non pas l'EXPOSITION (impossible) mais l'ÉVALUATION du critère (cotation
# vidéo différée par un évaluateur indépendant, en insu de l'allocation) —
# c'est la solution standard des essais de robotique/thérapie assistée par
# l'animal, où le participant ne peut structurellement pas être aveuglé.
_UNBLINDABLE_PRESENCE_KW = [
    "robot", "compagn", "humanoïde", "humanoid",
    "thérapie assistée par l'animal", "chien d'assistance", "animal-assisted",
]


def _score_label(score: float) -> str:
    """Catégorise un score continu — évite une fausse précision en décimales
    non justifiable (retour d'Olivier, critique méthodologiste 2026-07-29)."""
    if score >= 0.85:
        return "Très élevée"
    if score >= 0.65:
        return "Élevée"
    if score >= 0.45:
        return "Modérée"
    return "Faible"


def _build_regulatory_strategy(output: DesignModeOutput) -> str:
    best = output.regulatory_manifold.best_point()
    dag = output.target_dag
    ident = output.identification
    text = f"{output.claim_text} {output.intervention}".lower()
    is_unblindable_presence = any(kw in text for kw in _UNBLINDABLE_PRESENCE_KW)

    # Reformulé le 2026-07-29 (retour d'Olivier) : "Design recommandé" sonne
    # prescriptif, comme si le moteur imposait une étude. Un méthodologiste
    # parlerait de défendabilité au regard des contraintes identifiées, pas
    # d'une prescription. Scores affichés en catégories (avec la valeur brute
    # entre parenthèses pour qui veut la retrouver), pas en décimales nues.
    parts = [
        f"Design le plus défendable, au regard de la claim et des contraintes "
        f"identifiées, pour : \"{output.claim_text}\".",
        f"",
    ]

    # Ajouté le 2026-07-29 (retour d'Olivier sur la facturation client avant
    # vérification de couverture KB) : affiché EN PREMIER, avant le design —
    # un repli générique invisible est le problème qu'on vient de découvrir
    # sur Miroki (mortalité toutes causes affichée avec 0.95 de confiance).
    if dag.coverage_warnings:
        parts.append("⚠️ COUVERTURE KB INCOMPLÈTE SUR CE CAS :")
        for w in dag.coverage_warnings:
            parts.append(f"  - {w}")
        parts.append("")

    parts.append(
        f"{best.design.design_name} — acceptabilité HAS {_score_label(best.regulatory_acceptability)} "
        f"({best.regulatory_acceptability:.2f}), risque de biais {_score_label(best.bias_risk)} "
        f"(indice {best.bias_risk:.2f})."
    )

    if ident.blinding_needed and is_unblindable_presence:
        parts.append(
            "CONDITION : l'exposition au dispositif ne peut pas être masquée au "
            "participant (présence physique perceptible) — double aveugle classique "
            "NON FAISABLE. Recommandé à la place : évaluation en aveugle par un "
            "évaluateur indépendant (ex. cotation vidéo différée des échelles "
            "comportementales, en insu de l'allocation)."
        )
    elif ident.blinding_needed:
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

    # Reformulé le 2026-07-29 (retour d'Olivier) : afficher plusieurs critères
    # comme également PRIMARY reproduit exactement le gap "endpoint_multiplicity"
    # que le mode REVIEW du même moteur sanctionne côté dossiers déposés (cf.
    # avis CNEDiMTS ENTERRA II 7254, ASA rétrogradée pour ce motif précis) —
    # incohérence entre les deux modes, pas un simple choix de formulation.
    # Un seul critère principal ; les autres deviennent des alternatives
    # validées, avec la condition de hiérarchisation explicite s'ils sont
    # conservés ensemble.
    primary_families = [f for f in output.endpoint_families if f.regulatory_weight == "PRIMARY"]
    all_primary_eps = [e for f in primary_families for e in f.endpoints]
    if all_primary_eps:
        principal, *compatible = all_primary_eps
        parts.append(f"CRITÈRE PRINCIPAL RECOMMANDÉ : {principal}.")
        if compatible:
            parts.append(
                f"CRITÈRES VALIDÉS COMPATIBLES (alternatives au principal, pas des "
                f"co-principaux) : {', '.join(compatible[:2])}. S'ils sont conservés "
                f"ensemble comme co-principaux, une hiérarchisation statistique "
                f"pré-spécifiée est requise pour contrôler le risque alpha global."
            )

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
    bias_flags, _bias_reasons = detect_structural_issues(parsed, ep_analyses, structure)
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
