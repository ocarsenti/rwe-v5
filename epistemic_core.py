"""Epistemic core — SINGLE source of truth for all causal/regulatory reasoning.

Absorbs design_engine.py. Both REVIEW and DESIGN modes use this core.

Responsibilities:
  - causal graph representation
  - identification logic
  - mediator detection
  - endpoint classification
  - bias taxonomy
  - regulatory constraints
  - design space generation
  - regulatory manifold computation
"""

from __future__ import annotations

from models import (
    BiasFlag,
    CausalRole,
    CausalStructure,
    ClaimLevel,
    ClinicalClaim,
    DAGEdge,
    DesignCandidate,
    DesignRecommendation,
    DesignSpace,
    EndpointAnalysis,
    EndpointFamily,
    EndpointNature,
    EvidenceDesignType,
    IdentificationRequirements,
    ManifoldPoint,
    RegulatoryManifold,
    StudyDesign,
    TargetDAG,
)

from claim_parser import parse_claim, classify_claim
from endpoint_classifier import classify_endpoint, classify_endpoints
from causal_graph_builder import build_causal_structure, detect_structural_issues
from bias_detector import build_bias_detections
from repair_engine import generate_repair_plan, generate_repair_plan_v2


# ===================================================================
# DESIGN RECOMMENDATION (absorbed from design_engine.py)
# ===================================================================

def recommend_design(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
) -> DesignRecommendation:
    if structure == CausalStructure.INVALID:
        return DesignRecommendation(
            primary_design=StudyDesign.NOT_IDENTIFIABLE,
            alternatives=[StudyDesign.EXPLORATORY],
            rationale="No identifiable causal estimand — exploratory study only.",
        )

    if structure == CausalStructure.CIRCULAR:
        return DesignRecommendation(
            primary_design=StudyDesign.NOT_IDENTIFIABLE,
            alternatives=[StudyDesign.BEFORE_AFTER, StudyDesign.EXPLORATORY],
            rationale=(
                "Circular causal structure blocks standard comparative designs. "
                "Repair the endpoint structure before selecting a design."
            ),
        )

    all_subjective = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    if all_subjective:
        return DesignRecommendation(
            primary_design=StudyDesign.SHAM_RCT,
            alternatives=[StudyDesign.RCT],
            rationale=(
                "All endpoints are subjective — double-blind or sham-controlled "
                "RCT required to control perception bias."
            ),
        )

    if BiasFlag.DETECTION_BIAS in bias_flags:
        if BiasFlag.CIRCULARITY_RISK in bias_flags:
            return DesignRecommendation(
                primary_design=StudyDesign.NOT_IDENTIFIABLE,
                alternatives=[StudyDesign.COHORT, StudyDesign.BEFORE_AFTER],
                rationale=(
                    "Detection bias combined with circularity — standard RCT not valid "
                    "without endpoint repair."
                ),
            )
        return DesignRecommendation(
            primary_design=StudyDesign.RCT,
            alternatives=[StudyDesign.COHORT, StudyDesign.ITS],
            rationale=(
                "Detection bias present but manageable with independent endpoint "
                "adjudication in an RCT framework."
            ),
        )

    if claim.level in (ClaimLevel.C, ClaimLevel.D):
        return DesignRecommendation(
            primary_design=StudyDesign.RCT,
            alternatives=[StudyDesign.COHORT],
            rationale="Outcome-level or complete-chain claim — RCT is the gold standard.",
        )

    if claim.level == ClaimLevel.B:
        return DesignRecommendation(
            primary_design=StudyDesign.COHORT,
            alternatives=[StudyDesign.BEFORE_AFTER, StudyDesign.ITS],
            rationale="Process-level claim — comparative cohort or before/after design.",
        )

    if claim.level == ClaimLevel.A:
        return DesignRecommendation(
            primary_design=StudyDesign.EXPLORATORY,
            alternatives=[StudyDesign.BEFORE_AFTER],
            rationale="Mechanism-level claim — exploratory study to validate mechanism.",
        )

    return DesignRecommendation(
        primary_design=StudyDesign.COHORT,
        alternatives=[StudyDesign.BEFORE_AFTER],
        rationale="Default recommendation — comparative cohort.",
    )


# ===================================================================
# IDENTIFICATION LOGIC
# ===================================================================

_MECHANISM_KW = [
    "neurostimulat", "stimulat", "modulat", "electromagnetic",
    "receptor", "molecule", "cellular", "endorphin", "frequency",
]
_PROCESS_KW = [
    "monitoring", "triage", "screening", "alert", "detection",
    "surveillance", "remote", "telemonitor", "symptom tracking",
    "follow-up", "care pathway", "referral", "coordination",
]
_OUTCOME_KW = [
    "survival", "mortality", "hospitalization", "complication",
    "pain", "quality of life", "acuity", "progression", "recurrence",
    "functional", "morbidity", "adverse event", "disability",
]


# Ajouté le 2026-07-29 (cas MammoScreen, oncologie diagnostique) : vocabulaire
# PARTAGÉ entre assess_identification() et generate_design_space() — une
# seule liste, pas deux maintenues séparément (c'est précisément le bug
# bilingue du 27/07 puis du 29/07 sur blinding_needed : deux listes du même
# concept, jamais synchronisées). Toute correction de ce vocabulaire se fait
# ici, une fois, pour les deux usages.
_DIAGNOSTIC_ACCURACY_KW = [
    "sensitivity", "specificity", "diagnostic accuracy", "detection rate",
    "sensibilité", "spécificité", "précision diagnostique", "taux de détection",
    "aide au diagnostic", "seconde lecture", "dépistage",
]

# Ajouté le 2026-07-29 (correction : la première version débloquait
# sensibilité/spécificité dès qu'une claim PARLAIT de diagnostic, sans
# vérifier qu'une référence indépendante était réellement DÉCRITE — donc une
# claim "sensibilité de 95%" sans biopsie ni histologie débloquait quand même
# le critère. Cette liste sert à vérifier la présence réelle, pas juste le
# besoin.
_REFERENCE_STANDARD_KW = [
    "biopsy", "histology", "histopathology", "gold standard", "reference standard",
    "confirmed by follow-up", "ground truth",
    "biopsie", "histologie", "histopathologie", "anatomopathologique", "anatomopathologie",
    "étalon de référence", "confirmé par suivi", "suivi clinique confirmé", "vérité terrain",
]


def assess_identification(
    claim: ClinicalClaim,
    endpoint_analyses: list[EndpointAnalysis],
    structure: CausalStructure,
    bias_flags: list[BiasFlag],
) -> IdentificationRequirements:
    has_circular = any(ea.causal_role == CausalRole.CIRCULAR for ea in endpoint_analyses)
    has_detection = BiasFlag.DETECTION_BIAS in bias_flags
    has_subjective_only = (
        endpoint_analyses
        and all(ea.nature == EndpointNature.SUBJECTIVE for ea in endpoint_analyses)
    )
    has_mediation = BiasFlag.MEDIATION_GAP in bias_flags
    text = f"{claim.text} {claim.intervention}".lower()
    has_mechanism = any(kw in text for kw in _MECHANISM_KW)

    is_device_measurement = any(kw in text for kw in [
        "monitoring", "detection", "triage", "alert", "screening",
        "sensor", "remote", "time-to-detection", "time-to-treatment",
    ])
    # Corrigé le 2026-07-29 (cas Miroki/KOKORO) : même bug bilingue déjà
    # corrigé le 2026-07-27 dans generate_design_space, mais resté non
    # synchronisé ici — cette liste, dans cette fonction séparée, n'a jamais
    # été élargie en français. Conséquence concrète observée : sur une claim
    # française "l'anxiété des enfants", blinding_needed ressortait à False,
    # alors que la même claim en anglais ("anxiety") donnait True.
    is_subjective_domain = any(kw in text for kw in [
        "pain", "quality of life", "fatigue", "anxiety", "well-being",
        "satisfaction", "symptom score",
        "douleur", "qualité de vie", "fatigue", "anxiété", "bien-être",
        "satisfaction", "score de symptômes",
    ])

    randomization = True
    blinding = has_subjective_only or is_subjective_domain
    adjudication = has_circular or has_detection or is_device_measurement
    external = has_circular or has_detection or is_device_measurement
    mediator_meas = has_mediation or has_mechanism
    is_diagnostic_claim = any(kw in text for kw in _DIAGNOSTIC_ACCURACY_KW)
    has_reference_standard = any(kw in text for kw in _REFERENCE_STANDARD_KW)

    if structure == CausalStructure.CIRCULAR or (is_device_measurement and not endpoint_analyses):
        strength = 0.9
    elif has_subjective_only or is_subjective_domain:
        strength = 0.7
    elif has_mediation or has_mechanism:
        strength = 0.5
    else:
        strength = 0.3

    return IdentificationRequirements(
        randomization_needed=randomization,
        blinding_needed=blinding,
        adjudication_needed=adjudication,
        external_data_needed=external,
        mediator_measurement_needed=mediator_meas,
        minimum_design_strength=strength,
        reference_standard_needed=is_diagnostic_claim,
        reference_standard_confirmed=is_diagnostic_claim and has_reference_standard,
    )


# ===================================================================
# TARGET DAG INFERENCE (DESIGN mode)
# ===================================================================

_MEDIATOR_KB = {
    "monitoring": ["symptom detection", "clinician alert", "treatment modification"],
    "triage": ["scan prioritization", "clinical decision", "treatment initiation"],
    "screening": ["case identification", "diagnostic confirmation", "treatment referral"],
    "alert": ["clinician notification", "clinical assessment", "treatment decision"],
    "detection": ["event identification", "clinical verification", "therapeutic action"],
    "neurostimulat": ["neural activation", "endorphin release", "pain modulation"],
    "stimulat": ["tissue activation", "biological response", "physiological effect"],
    "modulat": ["pathway modulation", "biological response", "clinical effect"],
    "remote": ["data transmission", "clinician review", "treatment adjustment"],
    # Ajouté le 2026-07-29 (cas Miroki/KOKORO) : mécanisme d'un robot/dispositif
    # de présence rassurante (companion device), distinct des mécanismes
    # biologiques/instrumentés ci-dessus.
    "compagn": ["présence rassurante", "réduction du stress anticipatoire", "coopération accrue à la procédure"],
    # Ajoutés le 2026-07-29 (test sur 4 cas fictifs oncologie, avant offre
    # publique) : "monitoring"/"remote" n'avaient pas d'équivalent français —
    # "surveillance" en couvre le mécanisme (télésurveillance, objets
    # connectés). "chirurg" et "algorithme" comblent deux mécanismes absents
    # jusqu'ici (résection chirurgicale, IA diagnostique), pas propres à
    # l'oncologie mais découverts par ce test.
    "surveillance": ["transmission de données", "revue clinique", "ajustement du traitement"],
    "chirurg": ["résection tissulaire", "modification anatomique", "effet thérapeutique"],
    "algorithme": ["analyse du signal/image", "aide à la décision clinique", "action thérapeutique du clinicien"],
    # Élargi le 2026-07-29 (cas réel MammoScreen) : "algorithme" seul ne
    # matchait pas la formulation réelle du secteur ("intelligence
    # artificielle", "IA", "aide au diagnostic").
    "intelligence artificielle": ["analyse du signal/image", "aide à la décision clinique", "action thérapeutique du clinicien"],
    "aide au diagnostic": ["analyse du signal/image", "aide à la décision clinique", "action thérapeutique du clinicien"],
    # Ajouté le 2026-07-29 (test 4 cas fictifs oncologie) : thérapie numérique
    # comportementale (app de coaching/suivi symptômes) — mécanisme déjà
    # rencontré dans le corpus réel (POPPINS, HELLOBETTER) mais jamais
    # reporté dans cette KB jusqu'ici.
    "coaching": ["autogestion des symptômes", "adhésion au traitement renforcée", "adaptation comportementale"],
}

_PROHIBITED_KB = {
    "monitoring": ["device-generated alert count", "monitoring coverage rate", "time-to-detection by device"],
    "triage": ["AI-triggered time-to-treatment", "triage prioritization score", "AI detection rate"],
    "screening": ["screening detection rate by device", "device sensitivity", "device-flagged event count"],
    "alert": ["alert-triggered detection rate", "alert count", "time-to-alert"],
    "detection": ["device detection rate", "time-to-detection by device", "AI-flagged positive rate"],
    "neurostimulat": ["stimulation session count", "device activation rate"],
    "stimulat": ["stimulation delivery count", "device output metric"],
    # Ajouté le 2026-07-29 (cas Miroki/KOKORO) : critères circulaires propres à
    # un robot compagnon — mesurer l'usage/l'engagement avec le dispositif ne
    # prouve pas une réduction d'anxiété, seulement que le dispositif a été
    # utilisé.
    "compagn": ["device interaction count", "robot engagement duration", "device-reported affect score"],
    # Ajoutés le 2026-07-29 (test sur 4 cas fictifs oncologie) : mêmes principe
    # que "compagn" — un dispositif qui fonctionne mécaniquement/transmet des
    # données/détecte quelque chose ne prouve pas de bénéfice patient.
    "surveillance": ["taux de transmission de données", "nombre d'alertes envoyées", "durée de port du dispositif"],
    "chirurg": ["taux de réalisation de la chirurgie", "durée opératoire seule", "marge chirurgicale non relue indépendamment"],
    "algorithme": ["sensibilité/spécificité de l'algorithme seule", "nombre d'images analysées", "taux de détection par l'algorithme"],
    "intelligence artificielle": ["sensibilité/spécificité de l'algorithme seule", "nombre d'images analysées", "taux de détection par l'algorithme"],
    "aide au diagnostic": ["sensibilité/spécificité de l'algorithme seule", "nombre d'images analysées", "taux de détection par l'algorithme"],
    "coaching": ["taux d'utilisation de l'application", "nombre de sessions de coaching complétées", "score d'engagement applicatif"],
}

_OUTCOME_KB = {
    "stroke": ["90-day all-cause mortality", "modified Rankin Scale at 90 days", "ICU length of stay",
               "30-day mortality from civil registry", "recurrent stroke rate"],
    "cancer": ["overall survival", "progression-free survival", "unplanned hospitalization rate",
               "treatment modification rate", "emergency department visits"],
    "ophthalmology": ["independently assessed visual acuity", "complication rate at 12 months",
                      "treatment escalation rate", "emergency admission for vision loss"],
    "pain": ["total analgesic consumption (morphine-equivalent mg/day)",
             "6-minute walk test distance", "return-to-work rate",
             "nocturnal actigraphy sleep efficiency", "score FIQ (Fibromyalgia Impact Questionnaire)"],
    "cardiology": ["all-cause mortality", "hospitalization rate from insurance claims",
                   "MACE (major adverse cardiovascular events)", "functional capacity (6MWT)",
                   "TLF — target lesion failure (adjudicated composite)"],
    # Ajoutés le 2026-07-27 (Option 1, cf. échange avec Olivier) : transcrits depuis les
    # 17 cas du corpus de calibration où le moteur a déjà validé domaine+endpoint réels
    # contre de vrais avis HAS — pas inventés. Filtrés à la main : exclus les endpoints
    # dont le CONCEPT est explicitement remis en cause par le moteur ou par HAS
    # elle-même (ex. VIS-RX "volume de contraste injecté" → surrogate_not_validated ;
    # I-STOP "auto-questionnaire non validé" → invalidité assumée dans son propre nom).
    # Les gaps adjudication_missing/endpoint_multiplicity NE disqualifient PAS un
    # endpoint ici — ce sont des lacunes de process (qui valide, comment corriger
    # l'alpha), pas des critiques du choix clinique lui-même.
    "orthopedics": ["taux de révision/reprise cumulé à N ans (registre ou étude dédiée)",
                    "taux de survie de l'implant (Kaplan-Meier)",
                    "score IKDC subjectif", "score fonctionnel spécifique validé (AOFAS, WOMAC...)"],
    "pulmonology": ["VEMS (FEV1 % prédit) — variation à 12 mois",
                    "taux d'exacerbations", "distance au test de marche de 6 minutes",
                    "qualité de vie respiratoire (SGRQ)"],
    "sleep_medicine": ["sévérité de l'insomnie (score ISI, adjudiqué/objectivé)",
                       "indice d'apnées-hypopnées (IAH) à la polysomnographie de titration",
                       "qualité du sommeil (PSQI)"],
    "gynecology": ["score de qualité de vie spécifique validé (UFS-QoL...)",
                   "réduction du volume/symptômes à imagerie indépendante"],
    "neurodegenerative": ["score MoCA (Montreal Cognitive Assessment)",
                          "score cognitif composite validé et adjudiqué"],
    # Ajouté le 2026-07-29 (cas Miroki/KOKORO, échange avec Olivier) : deux
    # claims distinctes à ne pas fusionner — anxiété de l'ENFANT (mesurée en
    # hétéro-évaluation pour les plus jeunes, auto-évaluation sinon) et
    # anxiété du PARENT (population secondaire). m-YPAS validée pour un moment
    # unique (préopératoire) — son extrapolation à des mesures répétées
    # (plusieurs séances) doit être justifiée dans le protocole, pas supposée.
    "pediatric_anxiety": [
        "score d'anxiété m-YPAS (hétéro-évaluation, jeune enfant, ≥3 ans)",
        "score d'anxiété CAM-S (auto-évaluation, enfant 4-10 ans, mesures répétées)",
        "score STAI-C (auto-évaluation, enfant ≥8-9 ans)",
        "taux de recours à la sédation/anesthésie générale par séance",
        "score STAI-Y état (anxiété du parent/accompagnant)",
    ],
}

_DOMAIN_MAP = {
    "ophthalmology": "ophthalmology",
    "oncology": "cancer", "lung cancer": "cancer", "cancer": "cancer",
    # Ajoutés le 2026-07-29 (offre publique Miroki/oncologie) : seuls les
    # termes anglais étaient reconnus — testé et confirmé le trou avant de
    # publier quoi que ce soit.
    "oncologie": "cancer", "cancérologie": "cancer", "cancer du poumon": "cancer",
    "neurology": "stroke", "stroke": "stroke", "emergency neurology": "stroke",
    "pain": "pain", "pain management": "pain", "chronic pain": "pain",
    "cardiology": "cardiology", "heart": "cardiology",
    # Ajoutés le 2026-07-27 (Option 1) — mappage des chaînes domain= réellement
    # utilisées dans les 17 cas du corpus (parfois en français, parfois libres,
    # non normalisées avant aujourd'hui — même limitation de fond que celle déjà
    # documentée pour generate_design_space : rien ne garantit qu'un futur appelant
    # utilise exactement l'une de ces chaînes).
    "orthopedics": "orthopedics", "orthopédie": "orthopedics",
    "orthopédie / rééducation fonctionnelle de la marche": "orthopedics",
    "orthopédie / réparation cartilagineuse": "orthopedics",
    "pulmonology": "pulmonology",
    "sleep_medicine": "sleep_medicine", "somnologie": "sleep_medicine",
    "psychiatrie / troubles du sommeil": "sleep_medicine",
    "gynecology": "gynecology",
    "fibromyalgie / douleur chronique": "pain",
    # Ajouté le 2026-07-29 (cas Miroki/KOKORO) :
    "pédiatrie": "pediatric_anxiety",
    "pédiatrie / anxiété procédurale": "pediatric_anxiety",
    "anxiété procédurale pédiatrique": "pediatric_anxiety",
    "radiothérapie pédiatrique": "pediatric_anxiety",
    # NON résolu : BRAINXPERT utilise domain="neurology" — exactement la même
    # chaîne que le mappage AVC existant ci-dessus, alors qu'il s'agit d'un cas
    # cognitif (score MoCA), pas d'AVC aigu. Pas de clé séparée ajoutée ici car
    # elle serait inatteignable (une seule chaîne "neurology", un seul mappage
    # possible) — nécessiterait que l'appelant distingue explicitement le
    # sous-domaine (ex. "neurology_stroke" vs "neurology_cognitive") avant qu'on
    # puisse le router correctement. La table "neurodegenerative" dans
    # _OUTCOME_KB existe déjà (score MoCA) mais reste inutilisée tant que ce
    # point n'est pas tranché.
}


def infer_target_dag(
    claim_text: str,
    intervention: str,
    domain: str = "",
) -> TargetDAG:
    text = f"{claim_text} {intervention}".lower()
    coverage_warnings = []

    mediators = []
    for kw, meds in _MEDIATOR_KB.items():
        if kw in text:
            mediators.extend(meds)
            break
    if not mediators:
        mediators = ["intermediate clinical process", "clinical decision"]
        coverage_warnings.append(
            "MÉCANISME NON RECONNU — aucun mot-clé de _MEDIATOR_KB ne correspond à "
            "cette intervention ; médiateurs génériques utilisés, à vérifier manuellement."
        )

    prohibited = []
    for kw, proh in _PROHIBITED_KB.items():
        if kw in text:
            prohibited.extend(proh)
    if not prohibited:
        prohibited = ["device-generated measurement endpoint"]
        coverage_warnings.append(
            "CRITÈRES INTERDITS NON SPÉCIFIQUES — aucun mécanisme reconnu dans "
            "_PROHIBITED_KB ; un seul interdit générique proposé, probablement incomplet."
        )

    domain_key = _DOMAIN_MAP.get(domain.lower(), "")
    outcomes = _OUTCOME_KB.get(domain_key, [])
    if not outcomes:
        outcomes = [
            "all-cause mortality from civil registry",
            "unplanned hospitalization rate from insurance claims",
            "independently adjudicated clinical event rate",
        ]
        coverage_warnings.append(
            f"DOMAINE NON RECONNU ({domain!r}) — critères génériques utilisés (mortalité, "
            "hospitalisation), sans rapport garanti avec la claim réelle. Ne pas présenter "
            "cette sortie comme calibrée avant qu'un domaine dédié soit ajouté à _OUTCOME_KB."
        )

    edges = [DAGEdge(source=intervention, target=mediators[0])]
    for i in range(len(mediators) - 1):
        edges.append(DAGEdge(source=mediators[i], target=mediators[i + 1]))
    edges.append(DAGEdge(source=mediators[-1], target=outcomes[0]))

    return TargetDAG(
        intervention=intervention,
        mediators=mediators,
        outcomes=outcomes,
        prohibited_outcomes=prohibited,
        edges=edges,
        coverage_warnings=coverage_warnings,
    )


# ===================================================================
# ENDPOINT FAMILY GENERATION (DESIGN mode)
# ===================================================================

def compute_endpoint_families(
    dag: TargetDAG,
    identification: IdentificationRequirements,
) -> list[EndpointFamily]:
    families = []

    # Ajoutés le 2026-07-27 (Option 1) : marqueurs physiologiques instrumentés
    # (VEMS, IAH) et score de sévérité de l'insomnie (ISI) reclassés ici plutôt
    # que dans BIOMARKER — ce sont, dans les vrais dossiers du corpus
    # Ajoutés le 2026-07-29 (cas Miroki/KOKORO, échange avec Olivier) : scores
    # d'anxiété procédurale pédiatrique validés (m-YPAS, CAM-S, STAI-C) —
    # reclassés ici en HARD_CLINICAL selon le même principe que score ISI
    # (sommeil) : pour un dispositif dont la revendication EST la réduction
    # de l'anxiété, l'échelle d'anxiété est le critère réglementairement
    # principal, pas un adjuvant. m-YPAS est validée pour l'anxiété
    # PRÉOPÉRATOIRE (moment unique) — son usage en mesures répétées
    # (plusieurs séances/semaines, comme en radiothérapie) est une extrapolation
    # hors du contexte de validation d'origine, à justifier explicitement dans
    # le protocole plutôt que supposée équivalente sans discussion.
    hard_clinical = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in [
            "mortality", "rankin", "complication", "mace", "recurrent", "acuity",
            "révision", "reprise", "survie de l'implant", "tlf", "target lesion failure",
            "ikdc", "aofas", "womac", "vems", "fev1", "iah", "apnées-hypopnées",
            "sévérité de l'insomnie", "score isi",
            "m-ypas", "cam-s", "stai-c",
        ]
    )]
    if hard_clinical:
        families.append(EndpointFamily(
            family_name="HARD_CLINICAL",
            endpoints=hard_clinical,
            independence_from_device=0.95,
            regulatory_weight="PRIMARY",
        ))

    # "sédation"/"anesthésie générale" ajoutés le 2026-07-29 (cas Miroki/KOKORO) :
    # taux de recours à la sédation par séance — objectif, non auto-rapporté,
    # indépendant du dispositif, même logique que hospitalisation/admission.
    utilization = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in [
            "hospitalization", "admission", "emergency", "icu", "escalation",
            "sédation", "anesthésie générale",
        ]
    )]
    if utilization:
        families.append(EndpointFamily(
            family_name="UTILIZATION",
            endpoints=utilization,
            independence_from_device=0.90,
            regulatory_weight="PRIMARY",
        ))

    # Ajoutés le 2026-07-27 (Option 1) : scores patient-rapportés de qualité de
    # vie et composites cognitifs — restent SECONDARY (adjuvants réels observés
    # dans le corpus, pas les critères principaux retenus par HAS).
    # "stai-y" ajouté le 2026-07-29 (cas Miroki/KOKORO) : anxiété du PARENT,
    # population secondaire par rapport à la claim principale (anxiété de
    # l'enfant) — reste SECONDARY même si l'instrument lui-même (STAI-Y,
    # forme adulte) est correctement validé pour cette population-là.
    biomarker = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in [
            "analgesic", "actigraphy", "walk test", "vo2", "biomarker",
            "psqi", "sgrq", "ufs-qol", "moca", "qualité de vie", "stai-y",
        ]
    )]
    if biomarker:
        families.append(EndpointFamily(
            family_name="BIOMARKER",
            endpoints=biomarker,
            independence_from_device=0.80,
            regulatory_weight="SECONDARY",
        ))

    survival = [o for o in dag.outcomes if any(
        kw in o.lower() for kw in ["survival", "mortality from civil", "mortality from hospital"]
    )]
    if survival and not any(f.family_name == "HARD_CLINICAL" and any("mortality" in e.lower() for e in f.endpoints) for f in families):
        families.append(EndpointFamily(
            family_name="SURVIVAL",
            endpoints=survival,
            independence_from_device=1.0,
            regulatory_weight="PRIMARY",
        ))

    if identification.mediator_measurement_needed:
        mediator_eps = [m for m in dag.mediators if m not in ("intermediate clinical process", "clinical decision")]
        if mediator_eps:
            families.append(EndpointFamily(
                family_name="MEDIATOR",
                endpoints=mediator_eps,
                independence_from_device=0.70,
                regulatory_weight="EXPLORATORY",
            ))

    if not families:
        families.append(EndpointFamily(
            family_name="HARD_CLINICAL",
            endpoints=["independently adjudicated clinical event rate at 12 months"],
            independence_from_device=0.90,
            regulatory_weight="PRIMARY",
        ))

    return families


# ===================================================================
# DESIGN SPACE GENERATION (DESIGN mode)
# ===================================================================

_DESIGN_PROFILES = [
    {
        "type": EvidenceDesignType.INDIVIDUAL_RCT,
        "name": "Individual RCT with independent endpoint adjudication",
        "base_strength": 0.95,
        "base_biases": ["selection bias (mitigated by randomization)"],
        "base_feasibility": 0.60,
        "base_acceptability": 0.95,
        "requires_blinding": False,
        "handles_circularity": False,
    },
    {
        "type": EvidenceDesignType.PRAGMATIC_RCT,
        "name": "Pragmatic RCT with administrative outcome ascertainment",
        "base_strength": 0.85,
        "base_biases": ["performance bias (open-label)", "outcome ascertainment via routine data"],
        "base_feasibility": 0.75,
        "base_acceptability": 0.85,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.CLUSTER_RCT,
        "name": "Cluster RCT (randomization at site level)",
        "base_strength": 0.80,
        "base_biases": ["contamination risk", "cluster-level confounding"],
        "base_feasibility": 0.65,
        "base_acceptability": 0.80,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.REGISTRY_RCT,
        "name": "Registry-based RCT with embedded randomization",
        "base_strength": 0.82,
        "base_biases": ["registry data quality", "incomplete capture"],
        "base_feasibility": 0.80,
        "base_acceptability": 0.82,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.STEPPED_WEDGE,
        "name": "Stepped-wedge cluster RCT (sequential rollout)",
        "base_strength": 0.78,
        "base_biases": ["temporal confounding", "learning effect"],
        "base_feasibility": 0.70,
        "base_acceptability": 0.75,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.CONTROLLED_ITS,
        "name": "Controlled interrupted time series",
        "base_strength": 0.55,
        "base_biases": ["history bias", "maturation", "regression to mean"],
        "base_feasibility": 0.85,
        "base_acceptability": 0.55,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.TARGET_TRIAL_EMULATION,
        "name": "Target trial emulation from observational data",
        "base_strength": 0.50,
        "base_biases": ["unmeasured confounding", "immortal time bias", "selection bias"],
        "base_feasibility": 0.90,
        "base_acceptability": 0.45,
        "requires_blinding": False,
        "handles_circularity": True,
    },
    {
        "type": EvidenceDesignType.EXTERNAL_CONTROL_COHORT,
        "name": "Single-arm study with external control cohort",
        "base_strength": 0.35,
        "base_biases": ["unmeasured confounding", "selection bias", "temporal bias"],
        "base_feasibility": 0.95,
        "base_acceptability": 0.30,
        "requires_blinding": False,
        "handles_circularity": True,
    },
]


def generate_design_space(
    claim_text: str,
    dag: TargetDAG,
    identification: IdentificationRequirements,
    endpoint_families: list[EndpointFamily],
) -> DesignSpace:
    text = f"{claim_text} {dag.intervention}".lower()

    # Élargi le 2026-07-27 : les 3 listes ne contenaient que des mots-clés anglais
    # ("emergency", "pain", "device"...) alors que les revendications réelles du
    # produit sont en français (FIREHAWK LIBERTY, INFINITY...) — aucun mot-clé ne
    # matchait jamais, donc ces 3 booléens étaient systématiquement False sur tout
    # le corpus de calibration, et le classement des designs ne variait jamais
    # selon le contenu de la revendication. Gardés bilingues (pas seulement
    # français) pour ne pas casser un usage anglophone existant éventuel.
    is_emergency = any(kw in text for kw in [
        "emergency", "triage", "stroke", "acute",
        "urgence", "urgent", "aigu", "aiguë", "accident vasculaire cérébral", "avc",
    ])
    is_subjective = any(kw in text for kw in [
        "pain", "quality of life", "fatigue", "anxiety",
        "douleur", "qualité de vie", "anxiété", "fatigue", "sommeil", "insomnie",
    ])
    is_device = any(kw in text for kw in [
        "device", "wristband", "app", "system", "monitor",
        "dispositif", "prothèse", "endoprothèse", "stent", "cathéter", "implant",
        "implantable", "chirurgie", "chirurgical",
    ])
    # Ajouté le 2026-07-29 (objection d'Olivier sur le cas Miroki) : une
    # présence physique perceptible (robot, animal, thérapeute en personne)
    # ne peut pas être masquée par un sham — contrairement à un comprimé ou,
    # parfois, une chirurgie. Le sham/double-blind n'est alors pas juste
    # "recommandé", il est infaisable ; la bonne pratique est l'évaluation en
    # aveugle du critère (évaluateur indépendant), pas le masquage de
    # l'exposition elle-même.
    is_unblindable_presence = any(kw in text for kw in [
        "robot", "compagn", "humanoïde", "humanoid",
        "thérapie assistée par l'animal", "chien d'assistance", "animal-assisted",
    ])

    primary_eps = []
    for f in endpoint_families:
        if f.regulatory_weight == "PRIMARY":
            primary_eps.extend(f.endpoints)
    if not primary_eps:
        primary_eps = ["independently adjudicated clinical event rate"]

    candidates = []
    for profile in _DESIGN_PROFILES:
        strength = profile["base_strength"]
        feasibility = profile["base_feasibility"]
        acceptability = profile["base_acceptability"]
        biases = list(profile["base_biases"])

        if identification.blinding_needed and not profile["requires_blinding"]:
            if profile["type"] == EvidenceDesignType.INDIVIDUAL_RCT:
                if is_unblindable_presence:
                    biases.append("exposition non masquable (présence physique) — nécessite une évaluation en aveugle par évaluateur indépendant, pas un sham")
                else:
                    biases.append("requires sham/blinding for subjective endpoints")
                strength += 0.0
            else:
                biases.append("perception bias (no blinding)")
                strength -= 0.05
                acceptability -= 0.05

        if identification.adjudication_needed:
            biases.append("independent adjudication committee required")

        if is_emergency and profile["type"] == EvidenceDesignType.INDIVIDUAL_RCT:
            feasibility -= 0.20
            biases.append("emergency setting complicates individual randomization")

        if is_emergency and profile["type"] in (
            EvidenceDesignType.CLUSTER_RCT, EvidenceDesignType.STEPPED_WEDGE,
        ):
            feasibility += 0.10

        if is_subjective and profile["type"] == EvidenceDesignType.INDIVIDUAL_RCT and not is_unblindable_presence:
            biases.append("sham control recommended for subjective endpoints")

        # Précédemment calculé mais jamais utilisé (code mort). Branché le
        # 2026-07-27 : un dispositif implantable/chirurgical rend le double
        # aveugle par chirurgie fictive rarement acceptable en pratique et
        # éthiquement discutable — l'RCT individuel classique perd un peu
        # d'acceptabilité pour ce motif précis, au profit d'un RCT pragmatique
        # (bras actif ouvert + adjudication indépendante), déjà la norme dans
        # les essais de dispositifs médicaux (cf. TARGET ALL COMERS, en ouvert).
        if is_device and profile["type"] == EvidenceDesignType.INDIVIDUAL_RCT:
            acceptability -= 0.05
            biases.append("double aveugle par chirurgie fictive rarement acceptable pour un dispositif implantable")
        if is_device and profile["type"] == EvidenceDesignType.PRAGMATIC_RCT:
            acceptability += 0.03
            biases.append("comparateur actif en ouvert + adjudication indépendante : norme pour les dispositifs médicaux")

        candidates.append(DesignCandidate(
            design_type=profile["type"],
            design_name=profile["name"],
            causal_strength=round(max(0.0, min(1.0, strength)), 2),
            expected_biases=biases,
            endpoint_compatibility=primary_eps[:3],
            feasibility=round(max(0.0, min(1.0, feasibility)), 2),
            has_acceptability=round(max(0.0, min(1.0, acceptability)), 2),
        ))

    # Ajouté le 2026-07-29 (cas MammoScreen) : contrairement aux 8 designs
    # ci-dessus (toujours présents, ajustés par pénalités/bonus), celui-ci
    # n'apparaît QUE pour une claim diagnostique — il ne s'agit pas d'une
    # variante d'essai comparatif, une claim thérapeutique n'a rien à en faire.
    if identification.reference_standard_needed:
        candidates.append(DesignCandidate(
            design_type=EvidenceDesignType.DIAGNOSTIC_ACCURACY_STUDY,
            design_name="Diagnostic accuracy / reader study vs. independent reference standard",
            causal_strength=0.85,
            expected_biases=["reader variability", "case-mix / spectrum bias"],
            endpoint_compatibility=[],
            feasibility=0.85,
            has_acceptability=0.90,
        ))

    # Corrigé le 2026-07-27 : le tri ne portait que sur l'acceptabilité, jamais
    # sur la faisabilité — donc même quand is_emergency faisait chuter la
    # faisabilité de l'RCT individuel de 0,20, ça ne changeait jamais son rang,
    # puisque son acceptabilité de base (0,95) restait la plus haute de la table
    # et n'était jamais elle-même pénalisée par ce mécanisme. Score composite :
    # l'acceptabilité réglementaire reste dominante (poids 0,7, c'est le signal
    # que HAS regarde en premier), la faisabilité opérationnelle pèse le reste
    # (0,3) — assez pour qu'un design difficile à réaliser puisse être doublé
    # par un design légèrement moins "idéal" sur le papier mais réalisable.
    candidates.sort(key=lambda c: 0.7 * c.has_acceptability + 0.3 * c.feasibility, reverse=True)

    # Ajouté le 2026-07-29 (retour d'Olivier, critique méthodologiste) : le
    # classement était affiché sans dire POURQUOI un design vient après un
    # autre — juste des scores nus. Génère une phrase de compromis explicite
    # par rapport au design en tête, sur les deux seuls axes qui pèsent dans
    # le tri (acceptabilité HAS, faisabilité) — jamais sur la force causale
    # seule, qui n'entre pas dans le score de classement.
    if candidates:
        best = candidates[0]
        for c in candidates[1:]:
            d_feas = c.feasibility - best.feasibility
            d_accept = c.has_acceptability - best.has_acceptability
            clauses = []
            if d_feas > 0.02:
                clauses.append(f"gagne en faisabilité (+{d_feas:.2f})")
            elif d_feas < -0.02:
                clauses.append(f"perd en faisabilité ({d_feas:.2f})")
            if d_accept < -0.02:
                clauses.append(f"perd en acceptabilité HAS ({d_accept:.2f})")
            elif d_accept > 0.02:
                clauses.append(f"gagne en acceptabilité HAS (+{d_accept:.2f})")
            if clauses:
                c.tradeoff_note = (
                    f"Par rapport à « {best.design_name} » : {', '.join(clauses)}."
                )

    return DesignSpace(candidates=candidates)


# ===================================================================
# REGULATORY MANIFOLD
# ===================================================================

def compute_regulatory_manifold(design_space: DesignSpace) -> RegulatoryManifold:
    points = []
    for c in design_space.candidates:
        identification_score = c.causal_strength
        bias_risk = round(1.0 - c.causal_strength + 0.05 * len(c.expected_biases), 2)
        bias_risk = min(1.0, max(0.0, bias_risk))
        operational_complexity = round(1.0 - c.feasibility, 2)
        regulatory_acceptability = c.has_acceptability

        points.append(ManifoldPoint(
            design=c,
            identification_score=identification_score,
            bias_risk=bias_risk,
            operational_complexity=operational_complexity,
            regulatory_acceptability=regulatory_acceptability,
        ))

    # Corrigé le 2026-07-27 (même raison que generate_design_space) : trier
    # uniquement sur regulatory_acceptability ignorait operational_complexity
    # (dérivé de la faisabilité), qui n'était donc jamais utilisé nulle part
    # pour le classement final malgré son calcul — best_point() choisissait
    # toujours l'RCT individuel, faisabilité ou pas.
    points.sort(key=lambda p: 0.7 * p.regulatory_acceptability + 0.3 * (1.0 - p.operational_complexity), reverse=True)
    return RegulatoryManifold(points=points)
