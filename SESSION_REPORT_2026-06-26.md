# Session Report — 2026-06-26

## Résumé

Session de développement sur RWE-v5. 4 axes principaux : câblage CAS, couche evidence LLM, corrections de bugs, validation sur 15 avis CNEDiMTS.

---

## 1. Câblage CAS → Epistemic Core

**Fichiers modifiés** : `engine.py`, `models.py`

- Ajout de `cas_output: Optional[CASOutput] = None` à `EngineOutput`
- Mise à jour de `EngineOutput.to_dict()` pour inclure le bloc CAS
- Ajout dans `ClinicalClaim` des champs d'alignement :
  - `device_alignment`, `population_alignment`, `context_alignment`
  - `study_design`, `n_patients`, `has_comparator`, `follow_up_months`, `study_countries`
- Dans `engine.analyze()` : appel conditionnel de `evaluate_cas()` si les 3 objets alignment sont présents

**Logique** : CAS ne s'exécute que si les 3 alignements (device/population/context) sont disponibles sur le claim — sinon `cas_output=None`. Cela évite les faux REJECTED sur des claims sans étude fournie.

---

## 2. Nouveau BiasFlag : `NO_COMPARATOR`

**Fichiers modifiés** : `models.py`, `causal_graph_builder.py`, `bias_detector.py`

- Sévérité : HIGH
- Se déclenche si `claim.has_comparator is False` ET `claim.level in (C, D)`
- Ne se déclenche PAS pour les niveaux A/B (mécanisme/processus ne requièrent pas de comparateur)
- Détail biologique dans `BIAS_DETAILS` : le counterfactuel non observé = impossible d'attribuer l'outcome à l'intervention vs. histoire naturelle

---

## 3. Couche Evidence : `llm_evidence_parser.py` (nouveau fichier)

**Problème adressé** : T01 (pas de comparateur) et T09 (alignement dispositif) sont impossibles à détecter sans lire l'étude. La saisie manuelle est inutile — l'utilisateur n'a pas ces données formatées.

**Solution** : LLM (claude-haiku-4-5-20251001) lit le texte brut de l'étude et extrait automatiquement :
- Métadonnées : design, N, comparateur, suivi en mois, pays
- Endpoints : is_validated_surrogate, is_independently_adjudicated
- Alignements CAS : DeviceAlignment, PopulationAlignment, ContextAlignment

**API** :
```python
result = parse_study_with_llm(text, claim_device, claim_indication)
claim = enrich_claim_with_study(claim, result)
# ou en une ligne :
claim, result = analyze_study(study_text, claim)
```

**Règle `is_validated_surrogate` — stricte** : 3 conditions simultanées requises :
1. Acceptation réglementaire formelle (FDA/EMA/HAS) dans cette indication précise
2. Chaîne surrogate→outcome démontrée en RCT
3. Non contesté dans cet avis

Contreexemples explicites dans le prompt : IAH/SAHOS, VEMS/BLVR, FIQ, MMSE, IPSS.

---

## 4. Bug Fix : SURROGATE_RISK sur ZEPHYR

**Fichier modifié** : `endpoint_classifier.py` (ligne ~111)

**Bug** : `HARD_CLINICAL_MARKERS` vérifié sur `endpoint.name + endpoint.description`. La description "surrogate for dyspnea and hospitalization" contenait "hospitalization" → `is_hard_clinical=True` → SURROGATE_RISK supprimé à tort.

**Fix** : vérification sur `endpoint.name` uniquement.
```python
# Avant (bug)
text = f"{endpoint.name} {endpoint.description}".lower()
# Après (fix)
name_text = endpoint.name.lower()
```

---

## 5. PERCEPTION_BIAS — décision de gap

**OPTILUME** : critique HAS = "pas de sham". PERCEPTION_BIAS (tous endpoints subjectifs) ne correspond pas — c'est une contrainte de design (ouvert vs. aveugle), pas un biais de perception au sens de la règle existante.

**Décision** : ne pas modifier la règle PERCEPTION_BIAS. L'OPTILUME est un gap architectural (nécessiterait un nouveau flag `OPEN_LABEL_SUBJECTIVE_PRIMARY`). Tentative de fix revertée car elle brisait `test_mixed_endpoints_no_perception_bias`.

---

## 6. Tests live sur abstracts CNEDiMTS

Testés via `test_evidence_parser_live.py` sur 6 études réelles :

| Avis | Résultat | Note |
|---|---|---|
| INSPIRE IV / EFFECT | `has_comparator=True`, IAH non surrogate validé | ✅ strict |
| ZEPHYR / LIBERATE | `has_comparator=True`, VEMS non surrogate validé | ✅ strict |
| FIBROREM / FIBREPIK | `has_comparator=False`, FIQ non surrogate validé | ✅ |
| BRAINXPERT / BENEFIC | `DIFFERENT_DEVICE` (CAPTEX 355) → CAS REJECTED | ✅ T09 détecté |
| PRESAGE CARE | CIRCULAR + DETECTION_BIAS, CAS score=1.00 | ✅ orthogonalité correcte |
| ODYSIGHT | CIRCULAR + PROCESS_TAUTOLOGY, CAS score=1.00 | ✅ orthogonalité correcte |

**Note clé PRESAGE CARE / ODYSIGHT** : CAS = 1.00 (France→France, device exact) mais drapeaux épistémiques catastrophiques. C'est correct — CAS mesure l'alignement étude↔claim, pas la validité causale.

---

## 7. Validation 15 avis CNEDiMTS

**Fichier** : `run_cnedimts_comparison.py`

**Score : 10/15** (après corrections de bugs)

**3 manques architecturaux** (non-bugs) :
- **OPTILUME** : pas de sham = contrainte de design, pas modélisé
- **CUREETY** : T09 (alignement CAS) = evidence layer non fournie dans le script de comparaison
- **INCEPTIV** : T01 (pas de comparateur) = evidence layer non fournie

---

## 8. Tests

**437 tests passing**, 1 échec pré-existant :

`TestGoldDatasetCrossCase.test_severity_ordering` — MOOVCARE severity=0.8 (PROCESS_TAUTOLOGY via "alerte" dans "délai de modification du traitement") > REMEDEE severity=0.6. Non corrigé — changerait la définition du gold case.

**Nouveaux test classes** :
- `TestCASWiring` (10 tests)
- `TestNoComparator` (9 tests)
- `TestEvidenceParserMapping` (12 tests) — sans appel LLM
- `TestEnrichClaim` (7 tests)

---

## 9. Coverage vs. taxonomie CNEDiMTS 5-MF

| MF | Couverture |
|---|---|
| MF_A (causalité, design) | ✅ CIRCULARITY/DETECTION/NO_COMPARATOR |
| MF_B (mesure effet) | ✅ SURROGATE/ADJUDICATION/PERCEPTION_RISK |
| MF_C (puissance statistique) | ❌ nécessite N + calcul NSN |
| MF_D (pertinence évidence) | ✅ CAS engine |
| MF_E (fiabilité corpus) | ❌ hors périmètre |

---

## Fichiers modifiés / créés

| Fichier | Statut | Contenu |
|---|---|---|
| `models.py` | Modifié | NO_COMPARATOR, ClinicalClaim champs alignment+study, EngineOutput.cas_output |
| `engine.py` | Modifié | import evaluate_cas, appel conditionnel CAS |
| `endpoint_classifier.py` | Modifié | name_text = endpoint.name.lower() (Bug 1 fix) |
| `causal_graph_builder.py` | Modifié | NO_COMPARATOR detection |
| `bias_detector.py` | Modifié | BIAS_DETAILS[NO_COMPARATOR] |
| `llm_evidence_parser.py` | **Nouveau** | Evidence layer LLM |
| `run_cnedimts_comparison.py` | **Nouveau** | 15-avis comparison runner |
| `test_evidence_parser_live.py` | **Nouveau** | Live tests sur abstracts réels |
| `test_suite.py` | Modifié | +38 tests (4 nouvelles classes) |
