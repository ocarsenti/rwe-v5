"""Test Mode 2 complet INFINITY (prothèse totale de cheville) — RENOUVELLEMENT 2025 —
sans appel LLM.

Reconstruit fidèlement depuis l'avis CNEDiMTS 7744 du 25/02/2025 (renouvellement
d'inscription, SR Suffisant, ASR V). Demandeur STRYKER FRANCE / fabricant WRIGHT
MEDICAL TECHNOLOGY.

Suite directe de test_infinity_ankle_repair.py (avis primo-inscription 5980, 2020).
Entre les deux, un avis intermédiaire (7333, 13/02/2024, modification des conditions
d'inscription) a été SA INSUFFISANT faute de toute donnée spécifique aux nouvelles
références (modification du procédé de fabrication) — non modélisé ici, mais notable :
la trajectoire réelle n'est pas monotone (Suffisant → Insuffisant → Suffisant).

Ce dossier de renouvellement répond enfin à la demande de 2020 (étude de suivi
spécifique en conditions réelles) via le registre national français des Prothèses
totales de cheville (AFCP), qui documente pour la première fois des données
FRANÇAISES spécifiques au dispositif INFINITY — contrairement au dossier 2020, qui
ne s'appuyait que sur des registres étrangers (UK/NZ/Australie) et reposait sur un
device_alignment SAME_FAMILY malgré un contexte DIFFERENT_SYSTEM.

Attendu : les gaps DEVICE et CONTEXT du cas 2020 devraient se résoudre (données
françaises, dispositif identique). Mais une faiblesse nouvelle et sévère apparaît,
que HAS documente elle-même noir sur blanc comme "principale limite" : sur 467
implantations INFINITY sélectionnées dans le registre, seules 169 (34,3%) ont des
données de suivi à 2 ans — soit ~66% de perte de suivi / défaut de déclaration par
les chirurgiens. Le champ StudyObject.dropout_rate_pct existe déjà dans le moteur
mais n'est actuellement consommé par AUCUNE règle de gap ni de bias_flag — ce cas
teste si cet angle mort se confirme.
"""

import sys
sys.path.insert(0, "/home/claude/rwe-v5")

from llm_evidence_parser import _parse_study_object_result
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

# ---------------------------------------------------------------------------
# Données INFINITY / registre national français des Prothèses totales de
# cheville (AFCP), rapport 2024, sous-cohorte spécifique INFINITY
# ---------------------------------------------------------------------------

INFINITY_RENEWAL_JSON = {
    "acronym": "AFCP French TAR Registry — INFINITY",
    "title": (
        "Registre national des Prothèses totales de cheville de l'AFCP (rapport 2024) — "
        "sous-cohorte spécifique INFINITY, implantations juin 2012 - juin 2024"
    ),
    "publication_year": 2024,
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
        "Ensemble des prothèses totales de cheville du registre français "
        "(comparaison descriptive, non randomisée, non concurrente)"
    ),
    "n_patients": 467,
    "age_min": 29,
    "age_max": 91,
    "key_inclusion_criteria": [
        "Prothèse INFINITY implantée et enregistrée au registre national AFCP, juin 2012-juin 2024",
    ],
    "key_exclusion_criteria": [],
    "device_studied": "INFINITY (prothèse totale de cheville, mêmes références que la demande)",
    "care_setting": "hospital",
    "operator_training_required": True,
    "follow_up_months": 24.0,
    "longest_follow_up_months": 24.0,
    # 467 sélectionnées, mais données de suivi à 2 ans disponibles pour seulement
    # 169 (34,3%) — HAS le documente explicitement comme "principale limite".
    "dropout_rate_pct": 63.8,  # (467-169)/467 = 63.8%
    "primary_analysis_set": "UNKNOWN",
    "sample_size_calculation_provided": False,
    "primary_endpoint_met": True,
    "study_countries": ["France"],
    "key_safety_signals": [
        "Matériovigilance France 2019-2023 : 2 événements (descellement)",
        "Matériovigilance Europe 2019-2023 : 135 événements (douleur n=31, descellement n=22, reprise n=21, infection n=18)",
        "Causes de reprise (registre global, toutes prothèses) : douleur 63,3%, raideur 21,7%, "
        "géodes/lyse 17,8%, infection 17,4%, migration 15,9%",
        "Non-exhaustivité de la déclaration des reprises par les chirurgiens (défaut de "
        "renseignement des visites de suivi) — limite explicitement identifiée par HAS",
    ],
    "endpoints": [
        {
            "name": "Taux de survie sans reprise à 2 ans (Kaplan-Meier)",
            "is_primary": True,
            "time_point": "2 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "NON_INFERIOR",
            "reached_significance": False,
        },
        {
            "name": "Taux de reprise chirurgicale à 2 ans",
            "is_primary": False,
            "time_point": "2 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "NON_INFERIOR",
            "reached_significance": False,
        },
        {
            "name": "Score de douleur AOFAS (pré- vs post-opératoire)",
            "is_primary": False,
            "time_point": "2 ans",
            "is_validated_surrogate": False,
            "is_independently_adjudicated": False,
            "result_direction": "SUPERIOR",
            "reached_significance": False,
        },
    ],
    "device_alignment": {
        "device_match_type": "EXACT_DEVICE",
        "device_description_study": "INFINITY (références identiques à la demande de renouvellement)",
        "device_description_claim": "INFINITY (prothèse totale de cheville)",
        "justification": (
            "Données spécifiques au dispositif exact faisant l'objet de la demande — "
            "contrairement au dossier de primo-inscription 2020, entièrement fondé sur des "
            "registres étrangers, ou au dossier intermédiaire 2024 (SA Insuffisant), où "
            "aucune donnée spécifique aux nouvelles références n'était disponible."
        ),
    },
    "population_alignment": {
        "population_match_type": "EXACT_INDICATION",
        "population_description_study": (
            "Patients avec arthrose post-traumatique (39%), arthrose sur laxité (26,1%), "
            "arthrose primitive (17,3%), arthropathie inflammatoire (6,4%), douleur AOFAS "
            "sévère/permanente pour 79,9% des patients avant pose"
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
        "context_match_type": "SAME_HEALTHCARE_SYSTEM",
        "study_country": "France",
        "target_country": "France",
        "care_pathway_match": "YES",
        "organization_dependency": "HIGH",
        "justification": (
            "Registre français — résout le gap de contexte du dossier 2020 (registres "
            "étrangers uniquement). La dépendance organisationnelle (formation chirurgien "
            "par compagnonnage, pratique régulière requise) reste HIGH mais est désormais "
            "documentée dans le système de santé cible lui-même."
        ),
    },
    "comparator_alignment": {
        "comparator_match_type": "EXACT_COMPARATOR",
        "comparator_description_claim": (
            "Les autres prothèses totales de cheville déjà prises en charge dans les "
            "indications retenues (comparateur revendiqué par le demandeur — contrairement "
            "au dossier 2020, où le comparateur revendiqué était l'arthrodèse)"
        ),
        "comparator_description_study": (
            "Ensemble des prothèses totales de cheville du registre français"
        ),
        "justification": (
            "Le comparateur revendiqué dans ce dossier de renouvellement est explicitement "
            "'les autres prothèses totales de cheville' (§1.4.2), et non plus l'arthrodèse "
            "comme en 2020 — le comparateur étudié correspond donc formellement au "
            "comparateur revendiqué, même si la comparaison reste descriptive et non "
            "randomisée (cf. gap DESIGN)."
        ),
    },
}

# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

claim = ClinicalClaim(
    text=(
        "INFINITY est efficace et sûr dans le remplacement des articulations "
        "tibio-talienne et talo-malléolaire en 1ère intention ou en chirurgie de "
        "reprise pour les patients dont l'articulation de la cheville est "
        "endommagée par une forme sévère d'arthrite rhumatoïde, d'arthrose "
        "post-traumatique ou de toute atteinte articulaire dégénérative, par "
        "rapport aux autres prothèses totales de cheville déjà remboursées"
    ),
    intervention="INFINITY (prothèse totale de cheville)",
    domain="orthopedics",
    endpoints=[
        Endpoint(
            "Taux de survie sans reprise à 2 ans",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=True,
            is_validated_surrogate=False,
            description="donnée de registre français, non adjudiquée indépendamment",
        ),
        Endpoint(
            "Taux de reprise chirurgicale à 2 ans",
            EndpointNature.OBJECTIVE,
            CausalRole.INDEPENDENT,
            is_primary=False,
            description="registre français, déclaration chirurgien non exhaustive (HAS)",
        ),
        Endpoint(
            "Score de douleur AOFAS pré- vs post-opératoire",
            EndpointNature.SUBJECTIVE,
            CausalRole.MEDIATED,
            is_primary=False,
            description="questionnaire patient-rapporté, non comparatif",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

print("=" * 70)
print("  MODE 2 — INFINITY / renouvellement 2025 / registre AFCP France — pipeline complet (sans LLM)")
print("=" * 70)

print("\n[1] Construction StudyObject...")
study = _parse_study_object_result(INFINITY_RENEWAL_JSON, claim.intervention, claim.text)
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
