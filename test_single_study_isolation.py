"""Teste l'hypothèse : une étude UNIQUE et isolée donnée au vrai pipeline LLM
(parse_study_object_with_llm_consensus) produit-elle une sortie comparable à
test_hellobetter_insomnie_repair.py (reconstruction manuelle, champs fixés à la main) ?

Texte ci-dessous : uniquement la description de Behrendt et al. 2020 (GET.ON Recovery),
telle que rapportée dans le tableau de l'avis CNEDiMTS HELLOBETTER Insomnie (23/07/2024) —
pas le document HAS complet, pas les 3 autres études, pas les recommandations. Isolation
volontaire pour tester si le bundling multi-études est bien la cause de la divergence
observée sur les 4 PDF complets.
"""

import sys, json
sys.path.insert(0, "/home/claude/rwe-v5")

from llm_evidence_parser import parse_study_object_with_llm_consensus
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze
from study_object import enrich_claim_with_study_object, compare_claim_to_study
from gap_repair_engine import repair_comparison

STUDY_TEXT = """
Behrendt et al. 2020 — GET.ON Recovery

Objectif : Évaluer l'efficacité d'une TCC-i numérique (déclarée comme étant GET.ON
Regeneration par le demandeur) chez des enseignants allemands manifestant un intérêt
pour l'étude (absence de critère d'inclusion sur l'existence d'une insomnie ou de
critères de sévérité de l'insomnie, information non retrouvée dans la publication).

Méthode : Étude prospective contrôlée (versus liste d'attente) randomisée 1:1, en
ouvert. Étude réalisée en Allemagne. Sans accompagnement.

Critères d'inclusion : âge ≥ 18 ans, actifs manifestant un intérêt pour l'étude,
accès à internet.
Critères de non-inclusion : idées suicidaires.
L'utilisation d'hypnotiques était autorisée. Il était demandé aux participants de ne
pas modifier leur traitement pendant la réalisation de l'étude.

Critère de jugement principal : score ISI (Insomnia Severity Index), questionnaire
d'auto-évaluation en 7 questions évaluant la nature de l'insomnie, la satisfaction du
sommeil, le fonctionnement au quotidien et l'anxiété par rapport aux troubles du
sommeil (auto-questionnaire, pas de confirmation clinique du diagnostic d'insomnie).

Calcul du nombre de sujets nécessaires : taille d'effet moyenne sur score ISI (d Cohen)
= 0,40, α bilatéral = 5%, (1-β) = 80% → 200 patients.
Recrutement : période non retrouvée dans la publication.
Analyse en ITT, gestion des données manquantes par imputation multiples.

Résultats :
177 participants randomisés (GET.ON n=88, liste d'attente n=89).
Age moyen : 46,1 ± 9,5 ans (GET.ON) vs 46,7 ± 9,7 ans (liste d'attente).
Femmes : 59/88 (67%) vs 57/89 (64%).

Observation : module 1 complété par n=71 (81%), module 5 complété par n=39 (44%),
tous les modules complétés par n=35 (40%) — 3,4 modules réalisés en moyenne ± 2,3.

À 8 semaines, analyse en ITT :
Sévérité de l'insomnie (ISI) : GET.ON 10,03 ± 0,48 vs liste d'attente 14,40 ± 0,48.
d Cohen (différence entre les deux bras sur l'évolution entre l'inclusion et 8
semaines) = 0,97, IC95% [0,66 ; 1,28], p<0,001.

À 6 mois, analyse en ITT (uniquement disponible pour le groupe GET.ON) :
Sévérité de l'insomnie (ISI) : GET.ON 10,30 ± 0,45 vs liste d'attente 13,93 ± 0,45.
d Cohen = 0,86 IC95% [0,55 ; 1,17] p<0,001.

Absence de contrôle actif (liste d'attente uniquement).
Aucune information sur les traitements hypnotiques pris à l'inclusion et durant le
suivi dans chaque bras — biais de confusion potentiel non contrôlé.
Absence de confirmation clinique du diagnostic d'insomnie chronique.
"""

print("=" * 70)
print("  Pipeline LLM réel — étude ISOLÉE (Behrendt et al. 2020 uniquement)")
print("=" * 70)

study, unstable_fields = parse_study_object_with_llm_consensus(
    study_text=STUDY_TEXT,
    claim_device="HELLOBETTER Insomnie",
    claim_indication="Insomnie chronique chez l'adulte",
)

print(f"\nmultiple_studies_detected : {study.multiple_studies_detected}")
print(f"unstable_fields           : {unstable_fields}")
print(f"device_studied            : {study.device_studied}")
print(f"study_design              : {study.study_design.value if study.study_design else None}")
print(f"is_randomized             : {study.is_randomized}")
print(f"comparator_type           : {study.comparator_type.value}")
print(f"n_patients                : {study.n_patients}")
print(f"device_alignment          : {study.device_alignment.device_match_type.value if study.device_alignment else None}")
print(f"population_alignment      : {study.population_alignment.population_match_type.value if study.population_alignment else None} (eligibility_shift={study.population_alignment.eligibility_shift.value if study.population_alignment else None})")
print(f"context_alignment         : {study.context_alignment.context_match_type.value if study.context_alignment else None}")
print(f"comparator_alignment      : {study.comparator_alignment.comparator_match_type.value if study.comparator_alignment else None}")
for e in study.endpoints:
    print(f"  endpoint: [{'PRIMARY' if e.is_primary else 'secondary'}] {e.name} — nature={e.nature.value}")

claim = ClinicalClaim(
    text="HELLOBETTER Insomnie réduit les symptômes d'insomnie chronique chez l'adulte",
    intervention="HELLOBETTER Insomnie",
    domain="sleep_medicine",
    endpoints=[Endpoint("placeholder", EndpointNature.SUBJECTIVE, CausalRole.INDEPENDENT, is_primary=True)],
)
enrich_claim_with_study_object(claim, study)
output = analyze(claim)
report = compare_claim_to_study(claim, study, epistemic_output=output)
repair = repair_comparison(report, claim, epistemic_output=output)

print(f"\noverall_risk : {report.overall_risk.value}")
print("gaps:")
for g in report.gaps:
    print(f"  [{g.severity}] {g.dimension.upper()} — {g.description[:100]}")
print("bias_flags:")
for bf in output.bias_flags:
    print(f"  [{bf.severity}] {bf.flag.value}")
