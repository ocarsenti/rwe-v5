"""Test Mode 2 complet HELLOBETTER Insomnie (thérapie numérique / DTx) — sans appel LLM.

Reconstruit fidèlement depuis l'avis CNEDiMTS du 23/07/2024 (prise en charge anticipée
d'un dispositif médical numérique, art. L.162-1-23 du CSS — AVIS DÉFAVORABLE).
Demandeur/fabricant GET.ON Institut für Online Gesundheitstrainings GmbH (Allemagne).

Premier cas DTx du corpus — catégorie de dispositif totalement différente de tout ce qui
a été testé jusqu'ici (stents, prothèses, cathéters). Voie réglementaire différente aussi :
la prise en charge anticipée des DMN (art. L.162-1-23 CSS) n'évalue que 2 conditions —
marquage CE dans l'indication (1°) et présomption d'innovation clinique/organisationnelle
(2°) — pas le couple SR/ASR classique de la LPPR. Le champ ClinicalClaim/StudyObject du
moteur ne distingue pas cette voie (cf. constat déjà fait : aucun champ "type de demande"
dans le code), donc ce cas teste aussi si le moteur reste pertinent hors LPPR.

Aucune donnée spécifique à la version V1 d'HELLOBETTER Insomnie n'est fournie. Le dossier
s'appuie sur 4 RCT portant sur des générations antérieures (GET.ON Recovery, GET.ON
Regeneration, StudiCare Sleep-e). HAS juge "raisonnable" l'extrapolation depuis GET.ON
Recovery/Regeneration (composants intégrés à HELLOBETTER) mais PAS depuis StudiCare
Sleep-e (structure trop différente, peu décrite) — un même dossier, deux jugements
d'extrapolation opposés selon l'étude source, bon test de la granularité device_alignment.

Modélisé ici sur l'étude la plus complète et la mieux décrite parmi les 4 retenues :
Behrendt et al. 2020 (GET.ON Recovery, RCT vs liste d'attente, n=177, enseignants
allemands en souffrance liée au travail).

Faiblesses relevées explicitement par HAS, indépendamment de l'absence de donnée
spécifique : absence de contrôle actif (liste d'attente uniquement), absence de
confirmation clinique du diagnostic d'insomnie chronique (auto-déclaration + seuil ISI
comme proxy), absence d'information sur les traitements hypnotiques concomitants
("biais de confusion majeur"), population d'étude restreinte (enseignants en stress
professionnel) non représentative de la population générale visée par l'indication.
"""

import sys
sys.path.insert(0, "/home/claude/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données HELLOBETTER Insomnie / étude Behrendt et al. 2020 (GET.ON Recovery)
# ---------------------------------------------------------------------------

HELLOBETTER_JSON = {
    "acronym": "Behrendt et al. 2020 — GET.ON Recovery",
    "title": (
        "Efficacy of a self-help web-based recovery training in improving sleep in "
        "workers: randomized controlled trial in the general working population "
        "(RCT GET.ON Recovery vs liste d'attente, enseignants allemands en stress "
        "professionnel)"
    ),
    "publication_year": 2020,
    "registration_id": None,
    "funding_type": "ACADEMIC",
    "study_design": "RCT",
    "is_randomized": True,
    "blinding_level": "open_label",
    "who_is_blinded": None,
    "allocation_concealment": True,
    "protocol_registered_before_enrollment": True,
    "has_comparator": True,
    # HAS le formule explicitement dans ses commentaires sur les 4 études retenues :
    # "Absence de contrôle actif" — la liste d'attente n'est pas traitée comme un
    # comparateur actif comparable à une prise en charge de référence.
    "comparator_type": "NONE",
    "comparator_description": (
        "Liste d'attente (absence de contrôle actif selon la caractérisation de HAS) — "
        "sans accompagnement"
    ),
    "n_patients": 177,
    "age_min": 18,
    "age_max": None,
    "key_inclusion_criteria": [
        "Âge ≥ 18 ans, enseignants",
        "Symptômes d'insomnie auto-rapportés (score ISI ≥ 15) — pas de confirmation clinique",
        "Rumination liée au travail objectivée par un score ≥ 15 sur la sous-échelle d'irritation cognitive",
        "Accès à internet",
    ],
    "key_exclusion_criteria": [
        "Idées suicidaires",
    ],
    "device_studied": "GET.ON Recovery (6 modules, sans accompagnement) — génération antérieure à HELLOBETTER Insomnie",
    "care_setting": "HOME",
    "operator_training_required": False,
    "follow_up_months": 1.5,  # 8 semaines
    "longest_follow_up_months": 6.0,
    # Ebert/Thiart/Behrendt rapportent tous une attrition majeure ; Behrendt : 40,6%
    # d'arrêts de traitement dans le bras GET.ON à 8 semaines.
    "dropout_rate_pct": 40.6,
    "primary_analysis_set": "UNKNOWN",
    "sample_size_calculation_provided": True,  # d Cohen 0,50, α=5%, puissance 80% → n=128 cible (128 randomisés ici, proche mais étude sœur Ebert et al. exactement à la cible)
    "primary_endpoint_met": True,
    "study_countries": ["Allemagne"],
    "key_safety_signals": [
        "Absence d'information sur les traitements hypnotiques pris à l'inclusion et durant "
        "le suivi — HAS : 'biais de confusion majeur'",
        "Absence de confirmation clinique du diagnostic d'insomnie chronique — limite "
        "commune identifiée par HAS à toutes les études du dossier",
        "40,6% d'arrêts de traitement dans le bras GET.ON à 8 semaines (données manquantes "
        "nombreuses, biais d'attrition selon HAS)",
    ],
    "concomitant_treatments_present": True,
    "concomitant_treatments_controlled": False,
    "concomitant_treatments_description": (
        "Traitements hypnotiques autorisés durant l'étude, sans description ni suivi de "
        "leur usage ou de leur évolution de posologie dans chaque bras — HAS : 'biais de "
        "confusion majeur'"
    ),
    "endpoints": [
        {
            "name": "Sévérité de l'insomnie (score ISI) à 8 semaines vs liste d'attente",
            "is_primary": True,
            "time_point": "8 semaines",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "IMPROVED",
            "reached_significance": True,
            "nature": "SUBJECTIVE",
        },
        {
            "name": "Récupération pendant le sommeil à 8 semaines",
            "is_primary": False,
            "time_point": "8 semaines",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "IMPROVED",
            "reached_significance": None,
            "nature": "SUBJECTIVE",
        },
    ],
    "device_alignment": {
        "device_match_type": "SAME_FAMILY",
        "device_description_study": "GET.ON Recovery (composants principaux intégrés à HELLOBETTER Insomnie selon HAS)",
        "device_description_claim": "HELLOBETTER Insomnie V1 (8 modules, avec accompagnement)",
        "justification": (
            "HAS juge 'raisonnable' l'extrapolation depuis GET.ON Recovery/Regeneration "
            "(composantes de TCC-i identiques, modules similaires), à la différence de "
            "StudiCare Sleep-e jugée trop peu décrite pour extrapoler. Différences notables "
            "cependant : HELLOBETTER ajoute l'accompagnement (absent dans GET.ON Recovery), "
            "2 modules supplémentaires (contrôle du stimulus, relaxation), et aucune donnée "
            "spécifique à la version V1 réellement commercialisée."
        ),
    },
    "population_alignment": {
        "population_match_type": "NARROWER_SUBGROUP",
        "population_description_study": (
            "Enseignants allemands en souffrance liée au travail, symptômes d'insomnie "
            "auto-rapportés (score ISI ≥ 15 comme proxy, sans confirmation clinique du "
            "diagnostic)"
        ),
        "population_description_claim": (
            "Adultes avec insomnie chronique diagnostiquée cliniquement (CIM-11 7A00), "
            "population générale, sans restriction professionnelle"
        ),
        "eligibility_shift": "MAJOR",
        "justification": (
            "HAS relève explicitement, comme 'limite majeure commune à toutes ces études', "
            "l'absence de diagnostic clinique confirmé d'insomnie chronique — le seuil ISI "
            "auto-rapporté sert de proxy, sans confirmation par un professionnel. La "
            "population étudiée (enseignants en stress professionnel) est en outre plus "
            "étroite que la population générale visée par l'indication revendiquée."
        ),
    },
    "context_alignment": {
        "context_match_type": "PARTIALLY_COMPARABLE",
        "study_country": "Allemagne",
        "target_country": "France",
        "care_pathway_match": "PARTIAL",
        "organization_dependency": "LOW",
        "justification": (
            "Intervention numérique délivrée à domicile, moins dépendante de "
            "l'infrastructure de soins locale qu'un dispositif implantable — mais contenu "
            "et outils validés en allemand, langue et contexte culturel non transposés "
            "explicitement au contexte français."
        ),
    },
    "comparator_alignment": {
        "comparator_match_type": "DIFFERENT_COMPARATOR",
        "comparator_description_claim": (
            "TCC-i de référence (présentielle ou numérique) ou, a minima, prise en charge "
            "usuelle de l'insomnie chronique — les recommandations de pratique clinique "
            "positionnent les TCC-i en 1ère ligne, quelle que soit leur modalité"
        ),
        "comparator_description_study": (
            "Liste d'attente (absence de contrôle actif) — et, pour l'étude CLINSLEEP en "
            "cours, un programme d'éducation du sommeil en ligne non plus utilisé en "
            "routine en France"
        ),
        "justification": (
            "HAS relève explicitement, à propos du comparateur de l'étude CLINSLEEP en "
            "cours : 'Le comparateur n'est donc pas le traitement de référence ni dans "
            "l'indication revendiquée [...] ni dans l'indication de l'étude' — et 'un outil "
            "en ligne qui n'est pas utilisé en routine en France'. Le même constat "
            "s'applique en creux aux 4 études rétrospectivement retenues, dont le seul "
            "comparateur est une liste d'attente sans prise en charge active."
        ),
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "HELLOBETTER Insomnie réduit les symptômes d'insomnie chronique chez l'adulte "
        "et présente un bénéfice clinique et organisationnel innovant par rapport à la "
        "prise en charge usuelle de l'insomnie chronique"
    ),
    intervention="HELLOBETTER Insomnie (thérapie cognitivo-comportementale numérique de l'insomnie)",
    domain="sleep_medicine",
    endpoints=[
        Endpoint(
            "Sévérité de l'insomnie (score ISI) à 8 semaines",
            EndpointNature.SUBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=True,
            is_validated_surrogate=False,
            description="questionnaire auto-évalué (ISI), étude ouverte, pas d'aveugle possible",
        ),
        Endpoint(
            "Récupération pendant le sommeil à 8 semaines",
            EndpointNature.SUBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=False,
            description="questionnaire auto-évalué, critère secondaire",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

print("=" * 70)
print("  MODE 2 — HELLOBETTER Insomnie / Behrendt et al. 2020 — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(HELLOBETTER_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  is_randomized   : {study.is_randomized}")
print(f"  has_comparator  : {study.has_comparator}  ({study.comparator_type.value})")
print(f"  n_patients      : {study.n_patients}")
print(f"  dropout_rate_pct: {study.dropout_rate_pct}%")
print(f"  follow_up       : {study.follow_up_months} mois")
print(f"  countries       : {study.study_countries}")
print(f"  safety signals  : {len(study.key_safety_signals)}")
for s in study.key_safety_signals:
    print(f"    ⚠  {s}")
print(f"  endpoints       :")
for e in study.endpoints:
    tag = "PRIMARY" if e.is_primary else "SECONDARY"
    print(f"    [{tag}] {e.name} — validated_surrogate={e.is_validated_surrogate}")

print("\n" + "─" * 70)
print("[2] Enrichissement claim + analyse épistémique...")
enrich_claim_with_study_object(claim, study)
output = analyze(claim)

print(f"  Claim level       : {output.claim_level.value}")
print(f"  Causal structure  : {output.causal_structure.value}")
print(f"  Design recommandé : {output.design_recommendation.primary_design.value}")
if output.bias_flags:
    print("  BiasFlags :")
    for bd in output.bias_flags:
        print(f"    [{bd.severity}] {bd.flag.value} — {bd.detail[:75]}")
else:
    print("  BiasFlags : aucun")

if output.cas_output:
    cas = output.cas_output
    print(f"  CAS : {cas.cas_score:.2f} → {cas.verdict.value}")

print("\n" + "─" * 70)
print("[3] ComparisonReport — Claim ↔ Study...")
report = compare_claim_to_study(claim, study, epistemic_output=output)

print(f"  Overall risk : {report.overall_risk.value}")
if report.gaps:
    print(f"  Gaps ({len(report.gaps)}) :")
    for g in report.gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:90]}")
else:
    print("  Gaps : aucun")

print("\n" + "=" * 70)
print("[4]  BOUTON REPAIR  — actions de réparation concrètes")
print("=" * 70)

repair_plan = repair_comparison(report, claim, epistemic_output=output)

print(f"\n  Fully repairable : {repair_plan.is_fully_repairable}")
print(f"  Résumé : {repair_plan.repair_summary}")

_effort_label = {
    GapRepairEffort.LOW:      "✅ IMMÉDIAT      ",
    GapRepairEffort.MEDIUM:   "🔧 AMENDEMENT   ",
    GapRepairEffort.HIGH:     "🏗  NOUVELLE ÉTUDE",
    GapRepairEffort.BLOCKING: "🚫 BLOQUANT     ",
}

if repair_plan.non_repairable_gaps:
    print(f"\n  Gaps non réparables sans nouvelle étude :")
    for g in repair_plan.non_repairable_gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:80]}")

if repair_plan.actions:
    print(f"\n  Actions ({len(repair_plan.actions)}) — triées par effort croissant :\n")
    for i, a in enumerate(repair_plan.actions, 1):
        label = _effort_label.get(a.effort, a.effort.value)
        print(f"  ── Action {i} ──────────────────────────────────────────────────────")
        print(f"  {label}  [{a.gap_severity}] {a.gap_dimension.upper()}")
        print(f"  Type    : {a.repair_type.value}")
        print(f"  Action  : {a.description}")
        lines = [a.specific_suggestion[j:j+90] for j in range(0, len(a.specific_suggestion), 90)]
        print(f"  Détail  : {lines[0]}")
        for line in lines[1:]:
            print(f"            {line}")
        if a.removes_risk:
            print(f"  Élimine : {', '.join(a.removes_risk)}")
        print()
else:
    print("\n  Aucune action de réparation nécessaire.")
