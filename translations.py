"""Static FR translations for engine output text — no LLM cost."""

RATIONALE_MAP = {
    "No identifiable causal estimand — exploratory study only.":
        "Pas d'estimand causal identifiable — étude exploratoire uniquement.",
    "Circular causal structure blocks standard comparative designs. Repair the endpoint structure before selecting a design.":
        "La structure causale circulaire bloque les designs comparatifs standards. Il faut réparer la structure des critères avant de choisir un design.",
    "All endpoints are subjective — double-blind or sham-controlled RCT required to control perception bias.":
        "Tous les critères sont subjectifs — un essai randomisé en double aveugle ou avec sham est nécessaire pour contrôler le biais de perception.",
    "Detection bias combined with circularity — standard RCT not valid without endpoint repair.":
        "Biais de détection combiné à la circularité — un essai randomisé standard n'est pas valide sans réparation des critères.",
    "Detection bias present but manageable with independent endpoint adjudication in an RCT framework.":
        "Biais de détection présent mais gérable avec une adjudication indépendante des critères dans un cadre d'essai randomisé.",
    "Outcome-level or complete-chain claim — RCT is the gold standard.":
        "Revendication de niveau résultat clinique ou chaîne complète — l'essai randomisé contrôlé est le gold standard.",
    "Process-level claim — comparative cohort or before/after design.":
        "Revendication de niveau processus — cohorte comparative ou design avant/après.",
    "Mechanism-level claim — exploratory study to validate mechanism.":
        "Revendication de niveau mécanisme — étude exploratoire pour valider le mécanisme.",
    "Default recommendation — comparative cohort.":
        "Recommandation par défaut — cohorte comparative.",
}

BIAS_DETAIL_MAP = {
    "Endpoint is measured by the device under evaluation — causal circularity.":
        "Le critère est mesuré par le dispositif évalué — circularité causale.",
    "Device changes detection timing — acceleration bias.":
        "Le dispositif modifie le moment de la détection — biais d'accélération.",
    "Subjective endpoint susceptible to perception/placebo bias in open-label design.":
        "Critère subjectif susceptible de biais de perception/placebo dans un design en ouvert.",
    "Mediation gap — intervention effect requires unmeasured intermediate steps.":
        "Gap de médiation — l'effet de l'intervention nécessite des étapes intermédiaires non mesurées.",
    "Process endpoint is tautologically linked to intervention mechanism.":
        "Le critère de processus est tautologiquement lié au mécanisme d'intervention.",
    "Primary endpoint is generated or influenced by the device under evaluation. The device cannot be both the intervention and the measurement instrument for the primary outcome — this creates an unfalsifiable causal claim.":
        "Le critère principal est généré ou influencé par le dispositif évalué. Le dispositif ne peut pas être à la fois l'intervention et l'instrument de mesure du résultat principal — cela crée une revendication causale infalsifiable.",
    "The process endpoint is the intervention itself. Measuring the process that the device performs as an outcome is tautological — the device will always 'succeed' at doing what it does.":
        "Le critère de processus est l'intervention elle-même. Mesurer le processus que le dispositif exécute comme résultat est tautologique — le dispositif \"réussira\" toujours à faire ce qu'il fait.",
}

REPAIR_TEXT_MAP = {
    "All endpoints are structurally dependent on the device mechanism — no independent measurement possible.":
        "Tous les critères dépendent structurellement du mécanisme du dispositif — aucune mesure indépendante possible.",
    "no causal inference possible under current design space":
        "aucune inférence causale possible dans l'espace de design actuel",
    "Mortality is the hardest clinical endpoint. Ascertainment via civil registry is completely independent of monitoring device.":
        "La mortalité est le critère clinique le plus dur. La vérification via le registre civil est totalement indépendante du dispositif de monitoring.",
    "ED visits are recorded in hospital information systems independent of the monitoring device. Captures downstream clinical events.":
        "Les passages aux urgences sont enregistrés dans les systèmes d'information hospitaliers indépendamment du dispositif. Capture les événements cliniques en aval.",
    "Central imaging review by radiologists blinded to treatment arm ensures progression assessment is independent of monitoring device.":
        "La relecture centralisée des images par des radiologues en aveugle du bras de traitement garantit une évaluation de la progression indépendante du dispositif.",
    "Clinical events adjudicated by independent committee blinded to treatment arm. Decouples outcome from device mechanism.":
        "Événements cliniques adjudiqués par un comité indépendant en aveugle du bras de traitement. Découple le résultat du mécanisme du dispositif.",
    "Hardest clinical endpoint, ascertained from official records independent of any device.":
        "Critère clinique le plus dur, vérifié à partir des registres officiels indépendamment de tout dispositif.",
    "Hospital admissions from administrative data are independent of the device.":
        "Les hospitalisations issues des données administratives sont indépendantes du dispositif.",
}

MANIFOLD_STATUS_MAP = {
    "REGULATORY_RISK: study design has structural weaknesses":
        "RISQUE RÉGLEMENTAIRE : le design d'étude présente des faiblesses structurelles",
    "ACCEPTABLE: study design meets minimum regulatory requirements":
        "ACCEPTABLE : le design d'étude répond aux exigences réglementaires minimales",
    "FRAGILE: study design is borderline — minor issues could cause rejection":
        "FRAGILE : le design d'étude est à la limite — des problèmes mineurs pourraient causer un rejet",
    "BLOCKED — circular causal structure prevents valid inference":
        "BLOQUÉ — la structure causale circulaire empêche toute inférence valide",
}

ACTION_MAP = {
    "Strengthen randomization or adopt cluster/pragmatic RCT":
        "Renforcer la randomisation ou adopter un essai randomisé en cluster/pragmatique",
    "Replace device-dependent endpoints with independently ascertained outcomes":
        "Remplacer les critères dépendants du dispositif par des résultats vérifiés de manière indépendante",
    "Replace surrogate/instrumented endpoints with hard clinical outcomes":
        "Remplacer les critères de substitution/instrumentés par des résultats cliniques durs",
    "Use external data sources (registry, claims, civil registry) for outcome ascertainment":
        "Utiliser des sources de données externes (registre, SNDS, registre civil) pour la vérification des résultats",
    "Decouple outcome measurement from intervention mechanism":
        "Découpler la mesure des résultats du mécanisme d'intervention",
    "Add blinding (sham control) or objective co-primary endpoints":
        "Ajouter l'aveugle (sham) ou des co-critères primaires objectifs",
    "Extend follow-up duration or add long-term outcome":
        "Prolonger la durée de suivi ou ajouter un résultat à long terme",
}


FAILURE_PATTERNS = [
    ("is structurally circular:", "est structurellement circulaire :"),
    ("generates or influences the measurement used as endpoint", "génère ou influence la mesure utilisée comme critère"),
    ("The device cannot be both the intervention and the measurement instrument", "Le dispositif ne peut pas être à la fois l'intervention et l'instrument de mesure"),
    ("outcome ascertainment is not independent of treatment arm assignment", "la vérification du résultat n'est pas indépendante de l'attribution du bras de traitement"),
    ("Any difference observed may reflect device sensitivity, not clinical benefit", "Toute différence observée peut refléter la sensibilité du dispositif, pas un bénéfice clinique"),
    ("is subject to detection acceleration:", "est sujet à l'accélération de détection :"),
    ("changes when/how the outcome is detected", "modifie quand/comment le résultat est détecté"),
    ("is patient-reported and susceptible to", "est rapporté par le patient et susceptible de"),
    ("expectation/placebo bias in open-label design", "biais d'attente/placebo dans un design en ouvert"),
    ("Study design has:", "Le design d'étude présente :"),
    ("circular causal structure", "structure causale circulaire"),
    ("endpoint circularity", "circularité des critères"),
    ("process tautology", "tautologie de processus"),
    ("detection bias", "biais de détection"),
    ("mediation gap", "gap de médiation"),
    ("perception bias", "biais de perception"),
]


def translate_text(text: str, mapping: dict) -> str:
    """Exact match translation from a mapping dict."""
    return mapping.get(text, text)


def translate_text_patterns(text: str) -> str:
    """Pattern-based translation for dynamic text containing variable parts."""
    result = text
    for en, fr in FAILURE_PATTERNS:
        result = result.replace(en, fr)
    return result


def translate_engine_output(output_dict: dict, lang: str = "fr") -> dict:
    """Translate all text fields in engine output dict. No LLM, pure dict lookup."""
    if lang == "en":
        return output_dict

    if "design_recommendation" in output_dict:
        dr = output_dict["design_recommendation"]
        if "rationale" in dr:
            dr["rationale"] = translate_text(dr["rationale"], RATIONALE_MAP)

    for bf in output_dict.get("bias_flags", []):
        if "detail" in bf:
            bf["detail"] = translate_text(bf["detail"], BIAS_DETAIL_MAP)

    re = output_dict.get("repair_engine", {})
    if "problem_summary" in re:
        re["problem_summary"] = translate_text_patterns(re["problem_summary"])
    if "implication" in re:
        re["implication"] = translate_text(re["implication"], REPAIR_TEXT_MAP)

    for er in re.get("endpoint_repairs", []):
        if "failure_reason" in er:
            er["failure_reason"] = translate_text_patterns(er["failure_reason"])
        for r in er.get("repairs", []):
            if "why_valid" in r:
                r["why_valid"] = translate_text(r["why_valid"], REPAIR_TEXT_MAP)

    manifold = output_dict.get("epistemic_manifold", {})
    if "regulatory_status" in manifold:
        manifold["regulatory_status"] = translate_text(
            manifold["regulatory_status"], MANIFOLD_STATUS_MAP,
        )
    for rd in manifold.get("repair_directions", []):
        if "action" in rd:
            rd["action"] = translate_text(rd["action"], ACTION_MAP)

    return output_dict
