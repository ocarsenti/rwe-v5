"""Generate a concise LLM summary of a repair diagnostic result."""

from __future__ import annotations

import anthropic

_client: anthropic.Anthropic | None = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def generate_repair_summary(result: dict, lang: str = "fr") -> str:
    """Call Haiku to synthesize a 4-5 sentence expert summary of the repair report."""

    parse_info = result.get("_parse_info", {})
    epistemic = result.get("epistemic", {})
    manifold = epistemic.get("epistemic_manifold", {})
    bias_flags = epistemic.get("bias_flags", [])
    gaps = result.get("gaps", [])
    actions = result.get("actions", [])

    intervention = parse_info.get("intervention") or "le dispositif"
    domain = parse_info.get("domain") or ""
    claim_level = epistemic.get("claim_level") or parse_info.get("claim_level") or ""
    causal_structure = epistemic.get("causal_structure") or ""
    overall_risk = result.get("overall_risk") or ""
    is_fully_repairable = result.get("is_fully_repairable", True)
    region = manifold.get("region") or ""

    flag_names = [bf.get("flag") or bf.get("flag_key") or "" for bf in bias_flags if bf.get("flag") or bf.get("flag_key")]
    gap_descriptions = [g.get("description", "") for g in gaps[:4]]
    blocking_actions = [a.get("description", "") for a in actions if a.get("effort") in ("blocking", "high")][:3]

    if lang == "fr":
        prompt = f"""Tu es un expert en méthodologie des études cliniques pour les dispositifs médicaux (contexte HAS/CNEDiMTS).
Tu dois rédiger une synthèse concise (4 à 5 phrases maximum) du rapport de diagnostic de cohérence ci-dessous.

La synthèse doit :
- Identifier en une phrase le problème méthodologique central
- Expliquer pourquoi il bloque l'inférence causale dans ce contexte précis
- Indiquer la trajectoire de correction prioritaire (sans lister tous les gaps)
- Conclure sur la faisabilité d'une soumission (immédiate, avec ajustements, ou nouvelle étude nécessaire)
- Être rédigée en français, au style d'un rapport d'expert, sans jargon technique excessif

Données du rapport :
- Dispositif / intervention : {intervention}{(' — domaine : ' + domain) if domain else ''}
- Niveau de revendication : {claim_level}
- Structure causale détectée : {causal_structure}
- Niveau de risque global : {overall_risk}
- Position épistémique : {region}
- Réparable sans nouvelle étude : {'Oui' if is_fully_repairable else 'Non'}
- Flags épistémiques : {', '.join(flag_names) if flag_names else 'Aucun'}
- Gaps principaux :
{chr(10).join('  • ' + g for g in gap_descriptions) if gap_descriptions else '  Aucun'}
- Actions prioritaires (effort élevé / bloquant) :
{chr(10).join('  • ' + a for a in blocking_actions) if blocking_actions else '  Aucune'}

Rédige uniquement la synthèse, sans titre, sans bullet points, en prose continue."""
    else:
        prompt = f"""You are an expert in clinical study methodology for medical devices (HAS/CNEDiMTS context).
Write a concise summary (4-5 sentences max) of the coherence diagnostic report below.

The summary must:
- Identify the central methodological problem in one sentence
- Explain why it blocks causal inference in this specific context
- Indicate the priority correction path (without listing all gaps)
- Conclude on submission feasibility (immediate, with adjustments, or new study required)
- Be written in expert report style, without excessive technical jargon

Report data:
- Device / intervention: {intervention}{(' — domain: ' + domain) if domain else ''}
- Claim level: {claim_level}
- Detected causal structure: {causal_structure}
- Overall risk level: {overall_risk}
- Epistemic position: {region}
- Repairable without new study: {'Yes' if is_fully_repairable else 'No'}
- Epistemic flags: {', '.join(flag_names) if flag_names else 'None'}
- Main gaps:
{chr(10).join('  • ' + g for g in gap_descriptions) if gap_descriptions else '  None'}
- Priority actions (high effort / blocking):
{chr(10).join('  • ' + a for a in blocking_actions) if blocking_actions else '  None'}

Write only the summary, no title, no bullet points, continuous prose."""

    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
