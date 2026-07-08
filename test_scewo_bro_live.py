"""Test live Mode 2 — SCEWO BRO / avis CNEDiMTS 7425 (avril 2024).

Vérifie si le pipeline actuel (post-fix commit 1d1d457) détecte correctement le
vrai motif HAS pour ce dossier : données cliniques appartenant à un AUTRE
dispositif (TOPCHAIR-S), non extrapolables à SCEWO BRO — donc un gap
device_alignment / DIFFERENT_DEVICE, pas un gap NO_COMPARATOR.

Texte source : /home/olive/cnedimts_analysis/data/raw_opinions_v2/7425.txt
(verbatim, avis HAS avril 2024)
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from llm_evidence_parser import parse_study_object_with_llm
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison

SCEWO_TEXT = """
Demandeur / Fabricant : SCEWO (Suisse)
Référence commerciale unique : SCEWO BRO — Fauteuil roulant électrique monte-marches.

Indications revendiquées : personnes ayant perdu la capacité de marcher et/ou de monter des
escaliers (tétraplégie/paraplégie, sclérose en plaques, paralysie cérébrale, dystrophie musculaire,
faiblesse générale des jambes).
Comparateur revendiqué : TOPCHAIR-S (fauteuil roulant électrique monte-marches).
ASA revendiquée : niveau III (amélioration modérée).

Le SCEWO BRO est équipé de deux capteurs positionnés à l'arrière et fonctionne par
auto-équilibrage gyroscopique sur 2 roues, contrairement au TOPCHAIR-S qui est un appareil sur
4 roues. Le SCEWO BRO possède des fonctionnalités additionnelles (mode lift, mode passager de
voiture, mode télécommande).

Données analysées par la Commission :
Données non spécifiques : une étude monocentrique, prospective, comparative, randomisée en
cross-over, portant sur 25 patients, relative à TOPCHAIR-S (fauteuil roulant électrique, comparé au
fauteuil STORM3), analysée dans l'avis d'inscription relatif à TOPCHAIR-S du 11 juillet 2007. Patients
inclus : tétraplégie fonctionnelle. Objectif : comparer les performances de TOPCHAIR-S et STORM3,
et évaluer la fonction monte-marches de TOPCHAIR-S. Franchissement d'une marche de 20 cm réalisé
avec succès et sans aide par 23 patients sur 25.

Données spécifiques à SCEWO BRO : aucune donnée fournie. Une étude d'opinion réalisée sur 6
patients (durée max 8 mois, retours d'expérience) n'est pas une étude clinique protocolisée et n'a pas
été retenue par la Commission.

Une comparaison technique (non clinique) a été fournie comparant SCEWO BRO et TOPCHAIR-S :
malgré des similitudes, les deux dispositifs diffèrent sur plusieurs points (configuration 2 roues vs 4
roues, mode lift additionnel pour SCEWO BRO).

Conclusion de la Commission : « La Commission regrette l'absence de données cliniques spécifiques
à SCEWO BRO. De plus, elle considère que les données fournies à l'appui de la demande ne sont pas
extrapolables au dispositif SCEWO BRO. Compte tenu de ces éléments, la Commission considère que
l'intérêt thérapeutique de SCEWO BRO ne peut être établi. »
Service attendu (SA) : Insuffisant.
"""

claim = ClinicalClaim(
    text=(
        "SCEWO BRO permet aux personnes tétraplégiques ou paraplégiques de franchir des "
        "escaliers et de se déplacer de manière autonome dans la vie quotidienne, avec une "
        "amélioration modérée du service attendu (ASA III) par rapport à TOPCHAIR-S"
    ),
    intervention="SCEWO BRO (fauteuil roulant électrique monte-marches)",
    domain="assistive_devices",
    endpoints=[
        Endpoint("franchissement autonome d'escaliers/marches", EndpointNature.OBJECTIVE,
                 CausalRole.INDEPENDENT, is_primary=True,
                 description="stair-climbing success rate — device performance outcome"),
    ],
)

print("=" * 70)
print("  MODE 2 — SCEWO BRO / avis CNEDiMTS 7425 — StudyObject complet")
print("=" * 70)

print("\n[1] Extraction StudyObject avec LLM...")
study = parse_study_object_with_llm(
    study_text=SCEWO_TEXT,
    claim_device=claim.intervention,
    claim_indication=claim.text,
)

print(f"\n  Comparateur")
print(f"    has_comparator   : {study.has_comparator}")
print(f"    comparator_type  : {study.comparator_type.value}")
print(f"    comparator_desc  : {study.comparator_description}")

print(f"\n  Intervention")
print(f"    device_studied   : {study.device_studied}")

if study.device_alignment:
    d = study.device_alignment
    print(f"\n  Device alignment : {d.device_match_type.value}")
    print(f"    study device   : {d.device_description_study}")
    print(f"    justification  : {d.justification}")
else:
    print("\n  Device alignment : None (LLM n'a pas rempli ce champ)")

print(f"\n  Statistiques")
print(f"    primary_ep_met   : {study.primary_endpoint_met}")

if study.endpoints:
    print(f"\n  Endpoints ({len(study.endpoints)}) :")
    for ep in study.endpoints:
        print(f"    · [{('PRIMARY' if ep.is_primary else 'SECONDARY')}] {ep.name}")
        print(f"        result_dir      = {ep.result_direction.value}")
        print(f"        significance    = {ep.reached_significance}")

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
else:
    print("  CAS output : None")

print("\n" + "─" * 70)
print("[3] ComparisonReport — Claim ↔ Study...")

report = compare_claim_to_study(claim, study, epistemic_output=output)

print(f"\n  Overall risk : {report.overall_risk.value}")

if report.gaps:
    print(f"\n  Gaps ({len(report.gaps)}) :")
    for g in report.gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:120]}")
else:
    print("  Gaps : aucun")

print(f"\n  Critiques HAS simulées :")
for c in report.has_critique_simulation:
    print(f"    · {c[:150]}")

if report.repair_priority:
    print(f"\n  Repair priority :")
    for i, p in enumerate(report.repair_priority, 1):
        print(f"    {i}. {p[:120]}")

print("\n" + "=" * 70)
print("[4] REPAIR — actions de réparation concrètes")
print("=" * 70)

repair_plan = repair_comparison(report, claim, epistemic_output=output)

print(f"\n  Fully repairable : {repair_plan.is_fully_repairable}")
print(f"  Summary : {repair_plan.repair_summary}")

if repair_plan.non_repairable_gaps:
    print(f"\n  Gaps non réparables sans nouvelle étude :")
    for g in repair_plan.non_repairable_gaps:
        print(f"    [{g.severity}] {g.dimension.upper()} — {g.description[:100]}")
