"""Test Mode 2 complet INFINITY (prothèse totale de cheville) — sans appel LLM.

Reconstruit fidèlement depuis l'avis CNEDiMTS 5980 du 10/03/2020 (primo-inscription,
SA Suffisant, ASA V). Demandeur TORNIER SAS / fabricant WRIGHT MEDICAL TECHNOLOGY.

À NE PAS CONFONDRE avec un autre dossier INFINITY (Stryker, 2024, défavorable) —
homonymie de nom de marque entre deux dispositifs différents.

Profil du dossier : aucun essai comparatif contrôlé. Le dossier repose sur 3 registres
étrangers (UK, Nouvelle-Zélande, Australie, recul max. 4 ans) et 7 études spécifiques
américaines (1 prospective non-comparative, 1 prospective sans suivi clinique, 5
rétrospectives dont 1 seule comparative — mais comparée à d'autres prothèses, jamais
à l'arthrodèse, le comparateur revendiqué par le demandeur). HAS qualifie elle-même
ces études de "faible niveau méthodologique" et relève l'hétérogénéité de la procédure
de pose (guide d'alignement PROPHECY utilisé de façon inconsistante selon les études).
Aucune donnée clinique spécifique au contexte français.

Malgré cela : SA Suffisant, ASA V — comparateur retenu = les autres prothèses de
cheville déjà remboursées (pas l'arthrodèse), et renouvellement conditionné à un
registre de suivi français.

Modélisé ici sur la source la plus robuste quantitativement : l'extraction du
registre national du Royaume-Uni (n=1468, recul 4 ans), qui documente taux de
révision et de survie de la prothèse en comparaison registre-large (non randomisée,
non concurrente) avec l'ensemble des prothèses de cheville du registre.

Sert de 2e cas de calibration "gap présent mais décision favorable", complémentaire
à FIREHAWK LIBERTY : ici le gap attendu est plus sévère (aucun comparateur concurrent
du tout, design purement observationnel) et pourtant HAS conclut quand même à un SA
Suffisant — la question testée est si le moteur retrouve un niveau de risque élevé
(cohérent avec les réserves méthodologiques que HAS formule elle-même) sans pour
autant conclure au refus, ce qui serait la bonne calibration.
"""

import sys
sys.path.insert(0, "/home/claude/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données INFINITY / registre national du Royaume-Uni (15th Annual Report, 2018)
# ---------------------------------------------------------------------------

INFINITY_JSON = {
    "acronym": "UK NJR INFINITY",
    "title": (
        "Extraction du registre national du Royaume-Uni (National Joint Registry), "
        "15th Annual Report 2018 — prothèse totale de cheville INFINITY, "
        "primo-implantations 2014-2019"
    ),
    "publication_year": 2018,
    "registration_id": None,
    "funding_type": "industry",
    "study_design": "COHORT",
    "is_randomized": False,
    "blinding_level": "open_label",
    "who_is_blinded": None,
    "allocation_concealment": False,
    "protocol_registered_before_enrollment": False,
    "has_comparator": True,
    "comparator_type": "ACTIVE",
    "comparator_description": (
        "Ensemble des prothèses totales de cheville du registre (comparaison "
        "registre-large descriptive, non randomisée, non concurrente au sens strict) "
        "— jamais l'arthrodèse, comparateur revendiqué par le demandeur"
    ),
    "n_patients": 1468,
    "age_min": None,
    "age_max": None,
    "key_inclusion_criteria": [
        "Toute prothèse INFINITY implantée et enregistrée au registre national UK 2014-2019",
    ],
    "key_exclusion_criteria": [],
    "device_studied": "INFINITY (prothèse totale de cheville, TORNIER/WRIGHT)",
    "care_setting": "hospital",
    "operator_training_required": True,
    "follow_up_months": 48.0,
    "longest_follow_up_months": 48.0,
    "dropout_rate_pct": None,
    "primary_analysis_set": "UNKNOWN",
    "sample_size_calculation_provided": False,
    "primary_endpoint_met": True,
    "study_countries": ["Royaume-Uni"],
    "key_safety_signals": [
        "Matériovigilance : 1,06% d'événements rapportés / unité vendue (cumul international jusqu'en 2018)",
        "Révisions (registre UK) : 80% (16/20) pour infection avérée ou suspectée",
        "Aucune donnée clinique spécifique disponible en contexte français",
    ],
    "endpoints": [
        {
            "name": "Taux de révision cumulé à 4 ans",
            "is_primary": True,
            "time_point": "4 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "NON_INFERIOR",
            "reached_significance": False,
        },
        {
            "name": "Taux de survie de la prothèse (Kaplan-Meier) à 4 ans",
            "is_primary": False,
            "time_point": "4 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "NON_INFERIOR",
            "reached_significance": False,
        },
        {
            "name": "Scores fonctionnels FFI / FAOS / SF-36 (études spécifiques, hors registre)",
            "is_primary": False,
            "time_point": "1-2 ans post-opératoire",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": False,
        },
    ],
    "device_alignment": {
        "device_match_type": "EXACT_DEVICE",
        "device_description_study": "INFINITY (mêmes références que la demande d'inscription)",
        "device_description_claim": "INFINITY (prothèse totale de cheville)",
        "justification": (
            "Dispositif identique à la revendication. Réserve procédurale (non liée à "
            "l'identité du dispositif) : le guide d'alignement PROPHECY, optionnel, est "
            "utilisé de façon inconsistante selon les études (24% à 88% des cas)."
        ),
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": (
            "Patients avec arthrose post-traumatique, arthrite rhumatoïde ou arthropathie "
            "dégénérative de la cheville, primo-implantation ou reprise"
        ),
        "population_description_claim": (
            "Remplacement des articulations tibio-talienne et talo-malléolaire pour "
            "arthrite rhumatoïde sévère, arthrose post-traumatique ou toute atteinte "
            "articulaire dégénérative"
        ),
        "eligibility_shift": "NONE",
        "justification": "Population du registre alignée avec l'indication revendiquée.",
    },
    "context_alignment": {
        "context_match_type": "DIFFERENT_SYSTEM",
        "study_country": "Royaume-Uni / Nouvelle-Zélande / Australie / USA",
        "target_country": "France",
        "care_pathway_match": "PARTIAL",
        "organization_dependency": "HIGH",
        "justification": (
            "HAS relève explicitement l'absence de données cliniques dans un contexte "
            "français. L'implantation est en outre réservée à des chirurgiens orthopédistes "
            "formés par compagnonnage et nécessite une pratique régulière — forte "
            "dépendance organisationnelle non documentée pour le système de santé français."
        ),
    },
    "comparator_alignment": {
        "comparator_match_type": "DIFFERENT_COMPARATOR",
        "comparator_description_claim": "Arthrodèse (comparateur revendiqué par le demandeur)",
        "comparator_description_study": (
            "Ensemble des prothèses de cheville du registre (comparaison descriptive, "
            "non concurrente) — jamais l'arthrodèse"
        ),
        "justification": (
            "HAS constate explicitement : 'Aucune étude ne compare la prothèse INFINITY "
            "à l'arthrodèse, comparateur revendiqué par le demandeur.' Faute de donnée "
            "sur ce comparateur, HAS substitue son propre comparateur retenu (les autres "
            "prothèses déjà remboursées) pour l'évaluation de l'ASA, mais la revendication "
            "d'un positionnement face à l'arthrodèse reste, elle, non étayée."
        ),
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "INFINITY est efficace dans le remplacement des articulations tibio-talienne "
        "et talo-malléolaire en 1ère intention ou en chirurgie de reprise pour les "
        "patients dont l'articulation de la cheville est endommagée par une forme "
        "sévère d'arthrite rhumatoïde, d'arthrose post-traumatique ou de toute atteinte "
        "articulaire dégénérative, en alternative à l'arthrodèse"
    ),
    intervention="INFINITY (prothèse totale de cheville)",
    domain="orthopedics",
    endpoints=[
        Endpoint(
            "Taux de révision cumulé à 4 ans",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=True,
            is_validated_surrogate=False,
            description="donnée de registre, non adjudiquée indépendamment",
        ),
        Endpoint(
            "Taux de survie de la prothèse à 4 ans",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="estimation Kaplan-Meier sur données de registre",
        ),
        Endpoint(
            "Scores fonctionnels FFI / FAOS / SF-36",
            EndpointNature.SUBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=False,
            description="questionnaires patient-rapportés, études non-comparatives",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

print("=" * 70)
print("  MODE 2 — INFINITY (prothèse de cheville) / registre UK — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(INFINITY_JSON, claim.intervention, claim.text)
print(f"  device_studied  : {study.device_studied}")
print(f"  study_design    : {study.study_design.value if study.study_design else 'None'}")
print(f"  is_randomized   : {study.is_randomized}")
print(f"  has_comparator  : {study.has_comparator}  ({study.comparator_type.value})")
print(f"  n_patients      : {study.n_patients}")
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
