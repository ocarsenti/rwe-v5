"""Test live Mode 2 — StudyObject complet sur ODYSIGHT."""

import sys, json
sys.path.insert(0, "/home/olive/rwe-v5")

from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from llm_evidence_parser import parse_study_object_with_llm
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison, GapRepairEffort

ODYSIGHT_TEXT = """
Données soumises pour ODYSIGHT (avis LATM indéterminé)

ODYSIGHT est une application mobile de télésurveillance de l'acuité visuelle pour patients
atteints de maculopathies chroniques (DMLA exsudative, œdème maculaire diabétique).

L'application teste l'acuité visuelle via un algorithme (test du tumbling E). Un second algorithme
surveille la courbe d'acuité et génère une pré-alerte en cas de diminution détectée. Le patient
confirme sur un second test, puis l'équipe médicale est alertée.

Études spécifiques soumises :

1. TIL-001 et TIL-002 : études prospectives de performance comparant l'algorithme de détection
   d'ODYSIGHT aux méthodes standardisées (ETDRS). Pas de comparateur clinique randomisé.
   Objectif : valider les performances de l'algorithme, pas l'impact clinique.

2. TIL-003 : étude rétrospective, multicentrique, mono bras, réalisée en ouvert.
   Objectif principal : évaluer l'impact d'ODYSIGHT dans la prise en charge des patients
   atteints de maculopathies. Critère de jugement : délai de détection de la baisse d'acuité
   visuelle par l'application (mesuré par l'application elle-même).
   Effectif : non précisé. Pas de groupe contrôle. Pays : France.

3. Études non spécifiques :
   - Chew et al. (FORESEEHOME) : RCT multicentrique, 1520 patients, 1,4 ans de suivi.
     Dispositif différent (FORESEEHOME ≠ ODYSIGHT). Critère : délai de conversion DMLA
     exsudative, acuité visuelle à la conversion.
   - Mathai et al. : étude rétrospective non comparative, 2123 patients, FORESEEHOME.
   - Gross et al. : étude monocentrique appariée, 288 patients, ALLEYE (encore différent).

Aucune étude contrôlée randomisée spécifique à ODYSIGHT.
Critère de jugement principal de TIL-003 = délai de détection par l'application elle-même (circulaire).
Pas de données sur l'acuité visuelle finale, la perte visuelle, ou la mortalité.
"""

claim = ClinicalClaim(
    text="ODYSIGHT détecte précocement les rechutes de DMLA et réduit le délai de traitement chez les patients sous anti-VEGF",
    intervention="ODYSIGHT application de monitoring visuel",
    domain="ophthalmology",
    endpoints=[
        Endpoint("délai de détection rechute DMLA par l'application", EndpointNature.INSTRUMENTED,
                 CausalRole.CIRCULAR, is_primary=True,
                 description="time-to-detection by device algorithm — alert-triggered"),
        Endpoint("acuité visuelle finale", EndpointNature.OBJECTIVE,
                 CausalRole.INDEPENDENT, is_primary=False,
                 description="final visual acuity — not measured in TIL-003"),
    ]
)

print("=" * 70)
print("  MODE 2 — ODYSIGHT / TIL-003 — StudyObject complet")
print("=" * 70)

print("\n[1] Extraction StudyObject avec LLM...")
study = parse_study_object_with_llm(
    study_text=ODYSIGHT_TEXT,
    claim_device=claim.intervention,
    claim_indication=claim.text,
)

print(f"\n  Identité")
print(f"    acronym          : {study.acronym}")
print(f"    publication_year : {study.publication_year}")
print(f"    registration_id  : {study.registration_id}")
print(f"    funding_type     : {study.funding_type.value}")

print(f"\n  Design")
print(f"    study_design     : {study.study_design.value if study.study_design else 'None'}")
print(f"    is_randomized    : {study.is_randomized}")
print(f"    blinding_level   : {study.blinding_level.value}")
print(f"    who_is_blinded   : {study.who_is_blinded}")
print(f"    alloc_concealment: {study.allocation_concealment}")
print(f"    pre_registered   : {study.protocol_registered_before_enrollment}")

print(f"\n  Comparateur")
print(f"    has_comparator   : {study.has_comparator}")
print(f"    comparator_type  : {study.comparator_type.value}")
print(f"    comparator_desc  : {study.comparator_description}")

print(f"\n  Population")
print(f"    n_patients       : {study.n_patients}")
print(f"    age_min / max    : {study.age_min} / {study.age_max}")
if study.key_inclusion_criteria:
    print(f"    inclusions       : {study.key_inclusion_criteria[:3]}")
if study.key_exclusion_criteria:
    print(f"    exclusions       : {study.key_exclusion_criteria[:3]}")

print(f"\n  Intervention")
print(f"    device_studied   : {study.device_studied}")
print(f"    care_setting     : {study.care_setting.value}")

print(f"\n  Suivi")
print(f"    follow_up_months : {study.follow_up_months}")
print(f"    longest_fu       : {study.longest_follow_up_months}")
print(f"    dropout_rate_pct : {study.dropout_rate_pct}")

print(f"\n  Statistiques")
print(f"    analysis_set     : {study.primary_analysis_set.value}")
print(f"    sample_size_calc : {study.sample_size_calculation_provided}")
print(f"    primary_ep_met   : {study.primary_endpoint_met}")
print(f"    countries        : {study.study_countries}")

if study.endpoints:
    print(f"\n  Endpoints ({len(study.endpoints)}) :")
    for ep in study.endpoints:
        print(f"    · [{('PRIMARY' if ep.is_primary else 'SECONDARY')}] {ep.name}")
        print(f"        time_point      = {ep.time_point}")
        print(f"        validated_surr  = {ep.is_validated_surrogate}")
        print(f"        adjudicated     = {ep.is_independently_adjudicated}")
        print(f"        result_dir      = {ep.result_direction.value}")
        print(f"        significance    = {ep.reached_significance}")

if study.key_safety_signals:
    print(f"\n  Safety signals : {study.key_safety_signals}")

if study.device_alignment:
    d = study.device_alignment
    print(f"\n  Device alignment : {d.device_match_type.value}")
    print(f"    study device   : {d.device_description_study}")
    print(f"    justification  : {d.justification}")

if study.population_alignment:
    p = study.population_alignment
    print(f"\n  Pop alignment    : {p.population_match_type.value}")
    print(f"    study pop      : {p.population_description_study}")
    print(f"    elig_shift     : {p.eligibility_shift.value}")

if study.context_alignment:
    c = study.context_alignment
    print(f"\n  Context alignment: {c.context_match_type.value} — {c.study_country} → France")
    print(f"    care_pathway   : {c.care_pathway_match.value}")
    print(f"    org_dependency : {c.organization_dependency.value}")

print("\n" + "─" * 70)
print("[2] Enrichissement claim + analyse épistémique...")

enrich_claim_with_study_object(claim, study)
output = analyze(claim)

print(f"  Structure causale  : {output.causal_structure.value}")
print(f"  Design recommandé  : {output.design_recommendation.primary_design.value}")

if output.bias_flags:
    print("  BiasFlags :")
    for bd in output.bias_flags:
        print(f"    [{bd.severity}] {bd.flag.value}")
else:
    print("  BiasFlags : aucun")

if output.cas_output:
    cas = output.cas_output
    print(f"  CAS score  : {cas.cas_score:.2f}  →  {cas.verdict.value}")

print("\n" + "─" * 70)
print("[3] ComparisonReport — Claim ↔ Study...")

report = compare_claim_to_study(claim, study, epistemic_output=output)

print(f"\n  Overall risk : {report.overall_risk.value}")

if report.gaps:
    print(f"\n  Gaps ({len(report.gaps)}) :")
    for g in report.gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:90]}")
else:
    print("  Gaps : aucun")

print(f"\n  Critiques HAS simulées :")
for c in report.has_critique_simulation:
    print(f"    · {c[:120]}")

if report.repair_priority:
    print(f"\n  Repair priority :")
    for i, p in enumerate(report.repair_priority, 1):
        print(f"    {i}. {p[:100]}")

print("\n" + "=" * 70)
print("[4] REPAIR — actions de réparation concrètes")
print("=" * 70)

repair_plan = repair_comparison(report, claim, epistemic_output=output)

print(f"\n  Fully repairable : {repair_plan.is_fully_repairable}")
print(f"  Summary : {repair_plan.repair_summary}")

if repair_plan.non_repairable_gaps:
    print(f"\n  ⛔ Gaps non réparables sans nouvelle étude :")
    for g in repair_plan.non_repairable_gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:80]}")

_effort_label = {
    GapRepairEffort.LOW: "✅ IMMÉDIAT",
    GapRepairEffort.MEDIUM: "🔧 AMENDEMENT",
    GapRepairEffort.HIGH: "🏗  NOUVELLE ÉTUDE",
    GapRepairEffort.BLOCKING: "🚫 BLOQUANT",
}

if repair_plan.actions:
    print(f"\n  Actions ({len(repair_plan.actions)}) triées par effort croissant :")
    for i, a in enumerate(repair_plan.actions, 1):
        label = _effort_label.get(a.effort, a.effort.value)
        print(f"\n  [{i}] {label} — [{a.gap_severity}] {a.gap_dimension.upper()}")
        print(f"       Type    : {a.repair_type.value}")
        print(f"       Action  : {a.description}")
        print(f"       Détail  : {a.specific_suggestion[:200]}")
        if a.removes_risk:
            print(f"       Élimine : {', '.join(a.removes_risk)}")
