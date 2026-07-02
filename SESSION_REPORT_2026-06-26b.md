# Session Report — 2026-06-26b

## Objectif de la session

Extension de RWE-v5 vers un **Mode 2 (Repair, premium)** : analyse épistémique complète depuis un PDF ou texte d'étude, avec extraction structurée (StudyObject) et rapport Claim ↔ Étude (ComparisonReport).

---

## Nouveaux fichiers

### `study_object.py` (~370 lignes)

Représentation complète d'une étude clinique et moteur de comparaison Claim ↔ Étude.

**Nouveaux enums (8) :**
- `BlindingLevel`: OPEN_LABEL / SINGLE_BLIND / DOUBLE_BLIND / SHAM_CONTROLLED / UNKNOWN
- `ComparatorType`: SHAM / PLACEBO / ACTIVE / STANDARD_OF_CARE / BEST_AVAILABLE / NONE / UNKNOWN
- `AnalysisSet`: ITT / PP / MODIFIED_ITT / FULL_ANALYSIS_SET / UNKNOWN
- `CareSetting`: HOSPITAL / OUTPATIENT / HOME / MIXED / UNKNOWN
- `ResultDirection`: SUPERIOR / NON_INFERIOR / EQUIVALENT / INFERIOR / NOT_REPORTED
- `FundingType`: INDUSTRY / PUBLIC / MIXED / UNKNOWN
- `OverallRisk`: CRITICAL / HIGH / MEDIUM / LOW
- `GapDimension`: DEVICE / POPULATION / CONTEXT / DESIGN / ENDPOINT

**`StudyObject` dataclass — champs complets :**
```
Identité  : acronym, title, publication_year, registration_id, funding_type
Design    : study_design, is_randomized, blinding_level, who_is_blinded,
            allocation_concealment, protocol_registered_before_enrollment
Comparateur: has_comparator, comparator_type, comparator_description
Population : n_patients, age_min, age_max, key_inclusion_criteria,
             key_exclusion_criteria
Intervention: device_studied, care_setting, operator_training_required
Suivi     : follow_up_months, longest_follow_up_months, dropout_rate_pct
Endpoints : list[StudyEndpoint] (name, is_primary, time_point,
            is_validated_surrogate, is_independently_adjudicated,
            result_direction, reached_significance)
Stats     : primary_analysis_set, sample_size_calculation_provided
Contexte  : study_countries
Résultats : primary_endpoint_met, key_safety_signals
CAS       : device_alignment, population_alignment, context_alignment
```

**`compare_claim_to_study(claim, study, epistemic_output=None) → ComparisonReport`**

5 dimensions de gap :

| Dimension | Règles |
|---|---|
| DEVICE | match_type DIFFERENT_DEVICE → CRITICAL; SAME_FAMILY → MEDIUM |
| POPULATION | age hors range claim → MEDIUM; indication différente → HIGH |
| CONTEXT | context_match LOW + claim D → HIGH |
| DESIGN | no comparator C/D → HIGH; open_label + subjectif → HIGH; exploratory C/D → CRITICAL; non-RCT comparatif C → MEDIUM; suivi < 6 mois D → MEDIUM |
| ENDPOINT | CIRCULARITY_RISK → CRITICAL; SURROGATE_RISK → HIGH; DETECTION_BIAS → HIGH; pas adjudication quand attendu → MEDIUM |

**Overall risk :** CRITICAL si ≥1 gap CRITICAL ou ≥2 gaps HIGH; HIGH si 1 gap HIGH; MEDIUM si ≥1 MEDIUM; LOW sinon.

**`enrich_claim_with_study_object(claim, study) → ClinicalClaim`**
Copie device_alignment / population_alignment / context_alignment depuis StudyObject vers ClinicalClaim pour branchement CAS.

### `test_study_object_live.py`

Runner live Mode 2 configuré sur ODYSIGHT / TIL-003.

---

## Fichiers modifiés

### `llm_evidence_parser.py`

**Ajouts Mode 2 :**
- Mapping dicts : `_BLINDING_MAP`, `_COMPARATOR_MAP`, `_ANALYSIS_SET_MAP`, `_CARE_SETTING_MAP`, `_FUNDING_MAP`, `_RESULT_DIR_MAP`
- `_SYSTEM_PROMPT_FULL` : prompt système complet avec règle stricte `is_validated_surrogate` (3 conditions simultanées + contre-exemples : IAH/SAHOS, VEMS/BLVR, FIQ, MMSE, IPSS)
- `_USER_TEMPLATE_FULL` : schéma JSON avec champ `study_countries: ["<pays 1>", "<pays 2>"]` explicite
- `parse_study_object_with_llm(study_text, claim_device, claim_indication) → StudyObject` (Haiku, max_tokens=2000)
- `_parse_study_object_result(data, claim_device, claim_indication) → StudyObject` (mapping pur, sans LLM)
- `load_pdf(pdf_path) → str` (pdfplumber en priorité, pypdf en fallback, ImportError si aucun)
- `analyze_pdf(pdf_path, claim) → tuple[ClinicalClaim, StudyObject]`

### `test_suite.py`

- Import étendu : `DeviceAlignment`, `PopulationAlignment`, `ContextAlignment`
- Nouvelle classe `TestStudyObject` (16 tests)

---

## Bugs corrigés

### 1. `study_countries` toujours vide

**Cause :** Le LLM peuplait `context_alignment.study_country` (string) mais pas `study_countries` (liste).

**Correction double :**
1. Prompt `_USER_TEMPLATE_FULL` : champ `study_countries` rendu explicite avec exemple `["<pays 1>", "<pays 2>"]`
2. Fallback dans `_parse_study_object_result()` :
   ```python
   if not obj.study_countries:
       ctx_raw = data.get("context_alignment", {})
       study_country_str = ctx_raw.get("study_country", "")
       if study_country_str:
           obj.study_countries = [c.strip() for c in study_country_str.replace("/", ",").split(",") if c.strip()]
   ```

### 2. `test_compare_open_label_subjective_primary_high` échouait

**Cause :** Condition `study.comparator_type != ComparatorType.SHAM` ne se déclenchait pas car le helper de test utilisait `SHAM` par défaut.

**Correction :** Condition simplifiée en `study.blinding_level not in (BlindingLevel.DOUBLE_BLIND, BlindingLevel.SHAM_CONTROLLED)` — plus correcte sémantiquement (évalue le masquage, pas le comparateur).

---

## Tests live Mode 2 — 6 cas CNEDiMTS

### INSPIRE IV / étude EFFECT
- Population : INSPIRE II + IV mélangés → `SAME_FAMILY` (gap MEDIUM)
- Endpoint principal : IAH (index apnée-hypopnée) — `SURROGATE_RISK` (IAH non validé comme surrogate HAS en SAHOS) → gap HIGH
- Suivi effectif : 0,5 mois → gap MEDIUM design (C/D claim)
- CAS : 0.78 → ACCEPTABLE
- **Overall : HIGH**

### BRAINXPERT / étude BENEFIC
- Dispositif dans l'étude : CAPTEX 355 ≠ BRAINXPERT → `DIFFERENT_DEVICE` → gap CRITICAL
- CAS : REJECTED (device différent)
- **Overall : CRITICAL**

### FIBROREM / étude FIBREPIK
- Dispositif : génération antérieure → `SAME_FAMILY` (gap MEDIUM)
- Design : OPEN_LABEL + critère subjectif principal → gap HIGH (PERCEPTION_BIAS)
- Recommandation : SHAM_RCT
- **Overall : CRITICAL** (≥2 HIGH)

### ZEPHYR / étude LIBERATE
- Dispositif : correspondance exacte → `EXACT_DEVICE` (pas de gap device)
- Endpoint : VEMS — `SURROGATE_RISK` (VEMS non validé pour BPCO/BLVR HAS) → gap HIGH
- Signal sécurité : pneumothorax 26,6%
- CAS : 0.90 → ACCEPTABLE
- **Overall : HIGH**

### PRESAGE CARE
- Design : EXPLORATOIRE, mono-bras → gap CRITICAL (claim C/D)
- BiasFlags : CIRCULARITY_RISK + DETECTION_BIAS + NOT_IDENTIFIABLE
- CAS : 1.00 (France→France, même dispositif) — **orthogonal à l'épistémique**
- **Overall : CRITICAL**

### ODYSIGHT / TIL-003
- Design : EXPLORATOIRE, rétrospectif, mono-bras → gap CRITICAL
- 4 BiasFlags : CIRCULARITY_RISK + DETECTION_BIAS + PROCESS_TAUTOLOGY + MEDIATION_GAP
- NOT_IDENTIFIABLE (pas de comparateur, pas d'identification causale possible)
- CAS : 1.00 (France→France, même dispositif) — **orthogonal à l'épistémique**
- **Overall : CRITICAL**

---

## Observation clé : orthogonalité CAS / épistémique

PRESAGE CARE et ODYSIGHT ont toutes deux CAS = 1.00 (contexte parfait) mais risk CRITICAL.
Le CAS mesure la **transposabilité** (dispositif / population / contexte), pas la **validité épistémique** de l'étude. Ces deux moteurs sont correctement indépendants.

---

## Architecture produit confirmée

```
MODE 1 — DIAGNOSE (gratuit)
  Input  : ClinicalClaim (texte + dispositif + endpoints)
  Engine : epistemic_core.py → analyze()
  Output : BiasFlags + design recommendation
  Coût   : ~0 (pas d'appel LLM pour le core)

MODE 2 — REPAIR (premium)
  Input  : ClinicalClaim + texte étude (ou PDF)
  Step 1 : parse_study_object_with_llm() → StudyObject  [Haiku, ~0.05€]
  Step 2 : enrich_claim_with_study_object() → ClinicalClaim enrichi
  Step 3 : analyze() → epistemic output + CAS
  Step 4 : compare_claim_to_study() → ComparisonReport
  Output : 5 dimensions de gap + overall risk + critiques HAS + repair priority
```

---

## Couverture MF CNEDiMTS

| MF | Description | Couverture |
|---|---|---|
| MF_A | Causalité, design | ✅ CausalStructure + CIRCULARITY + NO_COMPARATOR + ComparisonReport.design |
| MF_B | Mesure de l'effet | ✅ EndpointNature + SURROGATE/DETECTION/PERCEPTION/ADJUDICATION_RISK |
| MF_C | Puissance statistique | ❌ Nécessite N + NSN calculation (non implémenté) |
| MF_D | Pertinence de l'évidence | ✅ CAS engine + ComparisonReport device/population/context |
| MF_E | Fiabilité du corpus | ❌ Hors scope |

---

## État final

- **453 tests** (453 passant, 1 pré-existant en échec : `test_severity_ordering` MOOVCARE via substring "alerte")
- Nouveaux fichiers : `study_object.py`, `test_study_object_live.py`
- Mode 2 complet et validé sur 6 abstracts CNEDiMTS réels

---

## Travaux reportés

- **Extension médicaments** : DomainProfile + MoleculeAlignment + BiasFlags spécifiques (DOSE_SELECTION_BIAS, ACTIVE_COMPARATOR_MISSING, ENRICHMENT_BIAS, DURATION_INADEQUACY). Même moteur, gating par domain_type. Manifold réglementaire → SMR/ASMR.
- **MF_C** : implémentation calcul puissance (N observé vs N calculé, NSN).
