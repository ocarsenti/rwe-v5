"""LLM-based evidence parser — extracts study metadata and CAS alignment from raw study text.

Mode 1 (light): parse_study_with_llm() → StudyParseResult
  Takes abstract / excerpt, returns metadata + CAS alignment objects.
  Uses ~800 tokens. Low cost.

Mode 2 (full): parse_study_object_with_llm() → StudyObject
  Takes full protocol / PDF text, returns complete StudyObject with
  blinding, comparator, inclusion criteria, per-endpoint results, etc.
  Uses ~2000 tokens. Premium tier.

load_pdf(path) → str   : PDF text extractor (pdfplumber or pypdf)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic

from models import (
    CarePathwayMatch,
    ClinicalClaim,
    ComparatorFeasibility,
    ContextAlignment,
    ContextMatchType,
    DeviceAlignment,
    DeviceMatchType,
    EligibilityShift,
    OrganizationDependency,
    PopulationAlignment,
    PopulationMatchType,
    StudyDesign,
)
from study_object import (
    AnalysisSet,
    BlindingLevel,
    CareSetting,
    ComparatorType,
    FundingType,
    ResultDirection,
    StudyEndpoint,
    StudyObject,
)

_client = None

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EndpointEvidence:
    name: str
    is_validated_surrogate: bool = False
    is_feasibility_accepted_surrogate: bool = False
    is_independently_adjudicated: bool = False


@dataclass
class StudyParseResult:
    study_design: StudyDesign | None = None
    n_patients: int | None = None
    has_comparator: bool | None = None
    comparator_feasibility: ComparatorFeasibility = ComparatorFeasibility.UNKNOWN
    follow_up_months: float | None = None
    study_countries: list[str] = field(default_factory=list)
    endpoint_evidence: list[EndpointEvidence] = field(default_factory=list)
    device_alignment: DeviceAlignment | None = None
    population_alignment: PopulationAlignment | None = None
    context_alignment: ContextAlignment | None = None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Tu es un expert en évaluation clinique et réglementaire des dispositifs médicaux (CNEDiMTS/HAS).

À partir du texte d'une étude clinique (abstract, protocole, ou extrait d'avis HAS), tu dois extraire les informations structurées suivantes.

## Métadonnées de l'étude

**study_design** — type de design :
- "RCT" : essai contrôlé randomisé (inclut crossover, cluster, pragmatique)
- "SINGLE_ARM" : étude bras unique, pas de comparateur — usage générique quand on ne peut
  pas trancher entre confirmatoire et exploratoire (voir les deux options plus précises ci-dessous)
- "SINGLE_ARM_PERFORMANCE_GOAL" : étude bras unique **confirmatoire**, avec un critère de
  jugement principal comparé à un objectif de performance **pré-spécifié et documenté avant
  l'étude** (seuil de succès fixé a priori, effectif justifié par un calcul de puissance). C'est
  le design pivot classique pour les dispositifs à haut risque quand aucun comparateur de
  modalité comparable n'est disponible (ex. valve cardiaque transcathéter comparée à un seuil
  de dysfonction valvulaire documenté). Préférer cette catégorie à "EXPLORATORY" quand un
  objectif de performance chiffré et pré-enregistré est explicitement mentionné.
- "REGISTRY" : registre ou cohorte observationnelle non comparative
- "COHORT" : cohorte comparative (avec comparateur non randomisé)
- "BEFORE_AFTER" : avant/après sans groupe contrôle concurrent
- "META_ANALYSIS" : méta-analyse ou revue systématique
- "MATCHED_OBSERVATIONAL" : appariement par score de propension ou autre méthode
- "EXPLORATORY" : pilote, faisabilité, série de cas, **sans** seuil de succès pré-spécifié —
  génère des hypothèses, ne les confirme pas

**n_patients** : effectif total de l'étude (entier). null si inconnu.

**has_comparator** : true si l'étude a un groupe contrôle ou comparateur actif/inactif. false si bras unique, registre non comparatif, before/after sans contrôle concurrent. null si incertain.

**comparator_feasibility** : uniquement pertinent si has_comparator=false. Évalue si un comparateur
concurrent était raisonnablement disponible pour cette indication (pas seulement s'il existe une
alternative administrative/réglementaire) :
- "FEASIBLE" : une alternative de modalité comparable existe, un essai comparatif tête-à-tête aurait
  été faisable et éthique
- "DIFFERENT_MODALITY" : la seule alternative relève d'une prise en charge fondamentalement
  différente et plus difficile à comparer en face-à-face (ex. chirurgie invasive lourde vs.
  dispositif mini-invasif)
- "NO_ALTERNATIVE" : aucun traitement alternatif n'existe pour cette indication précise
- "UNKNOWN" : non déterminable à partir du texte

**follow_up_months** : durée de suivi principale en mois (nombre décimal). null si inconnu.

**study_countries** : liste des pays où l'étude a été conduite (ex: ["USA", "France", "Germany"]). [] si inconnu.

## Métadonnées des endpoints

Pour chaque endpoint mentionné, évaluer :
- **is_validated_surrogate** : true UNIQUEMENT si les trois conditions sont réunies simultanément :
  1. L'endpoint est reconnu comme surrogate ACCEPTABLE par une agence réglementaire (FDA, EMA, ou HAS) dans cette indication spécifique ET cette population spécifique
  2. La corrélation surrogate → outcome dur (mortalité, hospitalisation, événement cardiovasculaire majeur) a été démontrée dans des essais randomisés, pas seulement des associations observationnelles
  3. L'endpoint n'est PAS contesté par la commission d'évaluation dans le contexte de cet avis

  Exemples VALIDÉS : HbA1c dans le diabète type 1/2 (EMA/FDA), LDL-cholestérol → événements CV (FDA), charge virale HIV → mortalité (FDA).

  Exemples NON VALIDÉS malgré leur usage courant :
  - IAH dans le SAHOS (les essais CPAP n'ont pas démontré de bénéfice sur la mortalité CV)
  - VEMS dans la réduction de volume pulmonaire bronchoscopique (lien VEMS → mortalité non établi pour cette intervention)
  - Score FIQ dans la fibromyalgie, MMSE dans Alzheimer, IPSS dans la sténose urétrale
  - Tout score fonctionnel ou PRO sans validation surrogate formelle

  Par défaut : false. Ne mettre true que si l'évidence surrogate est incontestable et reconnue réglementairement.

- **is_independently_adjudicated** : true si un Comité d'Événements Cliniques (CEC) indépendant et en aveugle est explicitement mentionné pour cet endpoint. false sinon.

## Alignement dispositif/population/contexte

Comparer l'étude soumise avec le dispositif et l'indication revendiqués.

**device_alignment.device_match_type** :
- "EXACT_DEVICE" : le dispositif étudié est exactement le dispositif revendiqué
- "SAME_FAMILY" : même famille (ex: COREVALVE EVOLUT R étudié, NAVITOR revendiqué)
- "PROXY_DEVICE" : dispositif similaire mais différent (ex: autre CGM étudié, FreeStyle revendiqué)
- "DIFFERENT_DEVICE" : dispositif fondamentalement différent
- "UNKNOWN" : impossible à déterminer

**population_alignment.population_match_type** :
- "EXACT_INDICATION" : la population de l'étude correspond exactement à l'indication revendiquée
- "NARROWER_SUBGROUP" : l'étude a étudié un sous-groupe plus restreint que l'indication revendiquée
- "BROADER_POPULATION" : l'étude a étudié une population plus large que l'indication revendiquée
- "DIFFERENT_POPULATION" : population substantiellement différente
- "UNKNOWN" : impossible à déterminer

**population_alignment.eligibility_shift** :
- "NONE" : pas de décalage
- "RESTRICTIVE" : l'étude avait des critères d'inclusion plus stricts que l'indication revendiquée
- "EXPANSIVE" : l'étude avait des critères plus larges

**context_alignment.context_match_type** :
- "SAME_HEALTHCARE_SYSTEM" : étude conduite en France ou dans un pays avec système de santé équivalent (Allemagne, Pays-Bas, Suisse, Royaume-Uni)
- "PARTIALLY_COMPARABLE" : pays partiellement comparables à la France (USA, Canada, Australie, pays nordiques)
- "DIFFERENT_SYSTEM" : système de santé très différent de la France
- "UNKNOWN" : inconnu

**context_alignment.care_pathway_match** :
- "YES" : le parcours de soins de l'étude est compatible avec la France
- "PARTIAL" : partiellement compatible
- "NO" : incompatible

**context_alignment.organization_dependency** :
- "LOW" : le dispositif peut être utilisé avec l'organisation de soins française actuelle
- "MEDIUM" : nécessite des adaptations organisationnelles modérées
- "HIGH" : nécessite une réorganisation majeure des soins

Réponds UNIQUEMENT en JSON valide, sans commentaire."""

_USER_TEMPLATE = """Analyse ce texte d'étude clinique et extrais les données structurées.

**Dispositif revendiqué** : {claim_device}
**Indication revendiquée** : {claim_indication}

**Texte de l'étude** :
{study_text}

Réponds en JSON avec ce format exact :
{{
  "study_design": "RCT" | "SINGLE_ARM" | "SINGLE_ARM_PERFORMANCE_GOAL" | "REGISTRY" | "COHORT" | "BEFORE_AFTER" | "META_ANALYSIS" | "MATCHED_OBSERVATIONAL" | "EXPLORATORY",
  "n_patients": <int ou null>,
  "has_comparator": <true | false | null>,
  "comparator_feasibility": "<voir liste — uniquement si has_comparator=false>",
  "follow_up_months": <float ou null>,
  "study_countries": ["..."],
  "endpoints": [
    {{
      "name": "...",
      "is_validated_surrogate": <true | false>,
      "is_independently_adjudicated": <true | false>
    }}
  ],
  "device_alignment": {{
    "device_match_type": "EXACT_DEVICE" | "SAME_FAMILY" | "PROXY_DEVICE" | "DIFFERENT_DEVICE" | "UNKNOWN",
    "device_description_study": "...",
    "justification": "..."
  }},
  "population_alignment": {{
    "population_match_type": "EXACT_INDICATION" | "NARROWER_SUBGROUP" | "BROADER_POPULATION" | "DIFFERENT_POPULATION" | "UNKNOWN",
    "population_description_study": "...",
    "eligibility_shift": "NONE" | "RESTRICTIVE" | "EXPANSIVE",
    "justification": "..."
  }},
  "context_alignment": {{
    "context_match_type": "SAME_HEALTHCARE_SYSTEM" | "PARTIALLY_COMPARABLE" | "DIFFERENT_SYSTEM" | "UNKNOWN",
    "care_pathway_match": "YES" | "PARTIAL" | "NO",
    "organization_dependency": "LOW" | "MEDIUM" | "HIGH",
    "study_country": "...",
    "justification": "..."
  }}
}}"""


# ---------------------------------------------------------------------------
# Study design mapping
# ---------------------------------------------------------------------------

_DESIGN_MAP: dict[str, StudyDesign] = {
    "RCT": StudyDesign.RCT,
    # Generic "single-arm, no comparator" with no further distinction offered by
    # the LLM defaults to the conservative EXPLORATORY bucket. When the LLM can
    # identify a pre-specified, documented performance objective, it should
    # return "SINGLE_ARM_PERFORMANCE_GOAL" instead (see prompt).
    "SINGLE_ARM": StudyDesign.EXPLORATORY,
    "SINGLE_ARM_PERFORMANCE_GOAL": StudyDesign.SINGLE_ARM_PERFORMANCE_GOAL,
    "REGISTRY": StudyDesign.MATCHED_OBSERVATIONAL,
    "COHORT": StudyDesign.COHORT,
    "BEFORE_AFTER": StudyDesign.BEFORE_AFTER,
    "META_ANALYSIS": StudyDesign.COHORT,
    "MATCHED_OBSERVATIONAL": StudyDesign.MATCHED_OBSERVATIONAL,
    "EXPLORATORY": StudyDesign.EXPLORATORY,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAME_SYSTEM_COUNTRIES = {
    "france", "allemagne", "germany", "pays-bas", "netherlands", "suisse",
    "switzerland", "royaume-uni", "united kingdom", "uk", "belgique", "belgium",
    "italie", "italy", "espagne", "spain", "autriche", "austria",
}

def _resolve_context_match(llm_match: str, study_country: str) -> ContextMatchType:
    """Override LLM context classification when study is conducted in France or equivalent system."""
    country_lower = (study_country or "").lower().strip()
    if any(c in country_lower for c in _SAME_SYSTEM_COUNTRIES):
        return ContextMatchType.SAME_HEALTHCARE_SYSTEM
    try:
        return ContextMatchType(llm_match)
    except ValueError:
        return ContextMatchType.UNKNOWN


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def parse_study_with_llm(
    study_text: str,
    claim_device: str,
    claim_indication: str,
    lang: str = "fr",
) -> StudyParseResult:
    """Parse a study abstract/excerpt and return structured StudyParseResult."""
    client = _get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        temperature=0,
        system=_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": _USER_TEMPLATE.format(
                claim_device=claim_device,
                claim_indication=claim_indication,
                study_text=study_text,
            ),
        }],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = _repair_truncated_json(raw)
    return _parse_result(data, claim_device, claim_indication)


def _parse_result(data: dict, claim_device: str, claim_indication: str) -> StudyParseResult:
    result = StudyParseResult()

    design_str = data.get("study_design")
    if design_str:
        result.study_design = _DESIGN_MAP.get(design_str)

    result.n_patients = data.get("n_patients")
    result.has_comparator = data.get("has_comparator")
    result.comparator_feasibility = _COMPARATOR_FEASIBILITY_MAP.get(
        data.get("comparator_feasibility", "UNKNOWN"), ComparatorFeasibility.UNKNOWN
    )
    result.follow_up_months = data.get("follow_up_months")
    result.study_countries = data.get("study_countries") or []

    for ep in data.get("endpoints", []):
        result.endpoint_evidence.append(EndpointEvidence(
            name=ep.get("name", ""),
            is_validated_surrogate=ep.get("is_validated_surrogate", False),
            is_feasibility_accepted_surrogate=ep.get("is_feasibility_accepted_surrogate", False),
            is_independently_adjudicated=ep.get("is_independently_adjudicated", False),
        ))

    dev = data.get("device_alignment", {})
    if dev:
        result.device_alignment = DeviceAlignment(
            device_match_type=DeviceMatchType(dev.get("device_match_type", "UNKNOWN")),
            device_description_claim=claim_device,
            device_description_study=dev.get("device_description_study", ""),
            justification=dev.get("justification", ""),
        )

    pop = data.get("population_alignment", {})
    if pop:
        result.population_alignment = PopulationAlignment(
            population_match_type=PopulationMatchType(pop.get("population_match_type", "UNKNOWN")),
            population_description_claim=claim_indication,
            population_description_study=pop.get("population_description_study", ""),
            eligibility_shift=EligibilityShift(pop.get("eligibility_shift", "NONE")),
            justification=pop.get("justification", ""),
        )

    ctx = data.get("context_alignment", {})
    if ctx:
        study_country = ctx.get("study_country", "")
        result.context_alignment = ContextAlignment(
            context_match_type=_resolve_context_match(ctx.get("context_match_type", "UNKNOWN"), study_country),
            care_pathway_match=CarePathwayMatch(ctx.get("care_pathway_match", "PARTIAL")),
            organization_dependency=OrganizationDependency(ctx.get("organization_dependency", "MEDIUM")),
            study_country=study_country,
            target_country="France",
            justification=ctx.get("justification", ""),
        )

    return result


# ---------------------------------------------------------------------------
# Enrichment — merge StudyParseResult into an existing ClinicalClaim
# ---------------------------------------------------------------------------

def enrich_claim_with_study(
    claim: ClinicalClaim,
    result: StudyParseResult,
) -> ClinicalClaim:
    """Merge study parse result into claim in-place. Returns the same claim."""
    if result.study_design is not None:
        claim.study_design = result.study_design
    if result.n_patients is not None:
        claim.n_patients = result.n_patients
    if result.has_comparator is not None:
        claim.has_comparator = result.has_comparator
    if result.comparator_feasibility != ComparatorFeasibility.UNKNOWN:
        claim.comparator_feasibility = result.comparator_feasibility
    if result.follow_up_months is not None:
        claim.follow_up_months = result.follow_up_months
    if result.study_countries:
        claim.study_countries = result.study_countries

    # Enrich endpoint metadata by matching on name (case-insensitive substring)
    for ep_ev in result.endpoint_evidence:
        for endpoint in claim.endpoints:
            if ep_ev.name.lower() in endpoint.name.lower() or endpoint.name.lower() in ep_ev.name.lower():
                if ep_ev.is_validated_surrogate:
                    endpoint.is_validated_surrogate = True
                if ep_ev.is_independently_adjudicated:
                    endpoint.is_independently_adjudicated = True

    # Wire CAS alignment
    if result.device_alignment is not None:
        claim.device_alignment = result.device_alignment
    if result.population_alignment is not None:
        claim.population_alignment = result.population_alignment
    if result.context_alignment is not None:
        claim.context_alignment = result.context_alignment

    return claim


# ---------------------------------------------------------------------------
# Convenience: parse + enrich in one call
# ---------------------------------------------------------------------------

def analyze_study(
    study_text: str,
    claim: ClinicalClaim,
) -> tuple[ClinicalClaim, StudyParseResult]:
    """Parse study text and enrich the claim. Returns (enriched_claim, parse_result)."""
    result = parse_study_with_llm(
        study_text=study_text,
        claim_device=claim.intervention,
        claim_indication=claim.text,
    )
    enriched = enrich_claim_with_study(claim, result)
    return enriched, result


# ---------------------------------------------------------------------------
# Mode 2 — Full Study Object parser
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_FULL = """Tu es un expert en évaluation clinique et réglementaire des dispositifs médicaux (CNEDiMTS/HAS).

À partir du texte complet d'une étude clinique (protocole, article, CER), tu extrais un Study Object structuré complet.

## Règles générales
- Réponds UNIQUEMENT en JSON valide.
- null pour tout champ inconnu ou non mentionné.
- [] pour toute liste inconnue.

## study_design
- "RCT" : essai contrôlé randomisé
- "SINGLE_ARM" : bras unique sans comparateur — générique, quand on ne peut pas trancher
  entre confirmatoire et exploratoire
- "SINGLE_ARM_PERFORMANCE_GOAL" : bras unique **confirmatoire**, critère de jugement principal
  comparé à un objectif de performance **pré-spécifié et documenté avant l'étude** (seuil de
  succès fixé a priori, effectif justifié par calcul de puissance). Design pivot classique pour
  dispositifs à haut risque sans comparateur de modalité comparable disponible. Préférer cette
  catégorie à "EXPLORATORY" dès qu'un seuil de performance chiffré et pré-enregistré est
  explicitement documenté dans le texte.
- "REGISTRY" : registre observationnel
- "COHORT" : cohorte comparative non randomisée
- "BEFORE_AFTER" : avant/après sans contrôle concurrent
- "META_ANALYSIS" : méta-analyse / revue systématique
- "MATCHED_OBSERVATIONAL" : appariement (PSM ou autre)
- "EXPLORATORY" : pilote, faisabilité, série de cas, **sans** seuil de succès pré-spécifié

## blinding_level
- "OPEN_LABEL" : pas d'aveugle
- "SINGLE_BLIND" : un niveau d'aveugle
- "DOUBLE_BLIND" : patient et évaluateur en aveugle
- "SHAM_CONTROLLED" : groupe sham/comparateur simulé
- "UNKNOWN" : non précisé

## comparator_type
- "SHAM" : dispositif fictif / simulé
- "PLACEBO" : placebo médicamenteux
- "ACTIVE" : comparateur actif (autre dispositif ou médicament)
- "STANDARD_OF_CARE" : soins standard
- "BEST_AVAILABLE" : meilleure alternative disponible
- "NONE" : pas de comparateur
- "UNKNOWN" : non précisé

## comparator_feasibility
Uniquement pertinent si has_comparator=false. Évalue si un comparateur concurrent
était raisonnablement disponible pour cette indication, pas seulement s'il existe
une alternative administrative/réglementaire.
- "FEASIBLE" : une alternative de modalité comparable existe et un essai comparatif
  tête-à-tête aurait été faisable et éthique (ex. une autre prothèse posée de la
  même façon, chez la même population)
- "DIFFERENT_MODALITY" : la seule alternative identifiée relève d'une prise en
  charge fondamentalement différente et plus difficile à comparer en face-à-face
  (ex. chirurgie invasive lourde vs. dispositif mini-invasif/transcathéter) —
  cf. EDWARDS SAPIEN 3 : seule alternative = reprise chirurgicale à cœur ouvert
- "NO_ALTERNATIVE" : aucun traitement alternatif n'existe pour cette indication
  précise (dispositif premier-de-sa-catégorie)
- "UNKNOWN" : non déterminable à partir du texte

## primary_analysis_set
- "ITT" : intention-to-treat
- "mITT" : modified ITT
- "PP" : per-protocol
- "FAS" : full analysis set
- "UNKNOWN" : non précisé

## care_setting
- "INPATIENT" : hospitalisation
- "OUTPATIENT" : ambulatoire / consultation
- "HOME" : domicile
- "HYBRID" : mixte
- "UNKNOWN" : non précisé

## funding_type
- "INDUSTRY" : financement industriel
- "ACADEMIC" : financement académique / institutionnel
- "PUBLIC" : financement public (PHRC, etc.)
- "MIXED" : mixte
- "UNKNOWN" : inconnu

## result_direction (par endpoint)
- "IMPROVED" : critère amélioré vs. baseline ou comparateur
- "NOT_IMPROVED" : pas d'amélioration significative
- "MIXED" : résultats mixtes
- "UNKNOWN" : non rapporté

## is_validated_surrogate (par endpoint)
true UNIQUEMENT si les 3 conditions sont simultanément réunies :
1. Reconnaissance réglementaire formelle (FDA/EMA/HAS) dans cette indication ET cette population
2. Corrélation surrogate→outcome dur démontrée en RCT (pas seulement associations)
3. Endpoint non contesté dans cet avis
Exemples VALIDÉS : HbA1c diabète, LDL→CV (FDA), charge virale HIV.
Exemples NON VALIDÉS : IAH/SAHOS, VEMS/BLVR, FIQ, MMSE, IPSS, scores fonctionnels PRO.
Par défaut : false.

## Alignement dispositif/population/contexte
Comparer l'étude au dispositif et à l'indication revendiqués (fournis dans le message utilisateur).

device_match_type : EXACT_DEVICE | SAME_FAMILY | PROXY_DEVICE | DIFFERENT_DEVICE | UNKNOWN
population_match_type : EXACT_INDICATION | NARROWER_SUBGROUP | BROADER_POPULATION | DIFFERENT_POPULATION | UNKNOWN
eligibility_shift : NONE | MINOR | MAJOR
context_match_type : SAME_HEALTHCARE_SYSTEM | PARTIALLY_COMPARABLE | DIFFERENT_SYSTEM | UNKNOWN
care_pathway_match : YES | PARTIAL | NO
organization_dependency : LOW | MEDIUM | HIGH"""

_USER_TEMPLATE_FULL = """Analyse ce texte d'étude clinique et extrais le Study Object complet.

**Dispositif revendiqué** : {claim_device}
**Indication revendiquée** : {claim_indication}

**Texte de l'étude** :
{study_text}

Réponds en JSON avec ce format exact :
{{
  "acronym": "<acronyme de l'étude ou null>",
  "title": "<titre complet ou null>",
  "publication_year": <année ou null>,
  "registration_id": "<NCT/EudraCT ou null>",
  "funding_type": "INDUSTRY" | "ACADEMIC" | "PUBLIC" | "MIXED" | "UNKNOWN",

  "study_design": "<voir liste>",
  "is_randomized": <true | false>,
  "blinding_level": "<voir liste>",
  "who_is_blinded": ["patient", "assessor", "clinician", "statistician"],
  "allocation_concealment": <true | false | null>,
  "protocol_registered_before_enrollment": <true | false | null>,

  "has_comparator": <true | false | null>,
  "comparator_type": "<voir liste>",
  "comparator_description": "<description du comparateur ou null>",
  "comparator_feasibility": "<voir liste — uniquement si has_comparator=false>",

  "n_patients": <entier ou null>,
  "age_min": <float ou null>,
  "age_max": <float ou null>,
  "key_inclusion_criteria": ["<critère 1>", "<critère 2>", "<critère 3>"],
  "key_exclusion_criteria": ["<critère 1>", "<critère 2>", "<critère 3>"],

  "device_studied": "<nom exact du dispositif étudié>",
  "care_setting": "<voir liste>",
  "operator_training_required": <true | false | null>,

  "follow_up_months": <float ou null>,
  "longest_follow_up_months": <float ou null>,
  "dropout_rate_pct": <float ou null>,

  "endpoints": [
    {{
      "name": "<nom du critère>",
      "is_primary": <true | false>,
      "time_point": "<ex: 12 mois ou null>",
      "is_validated_surrogate": <true | false>,
      "is_independently_adjudicated": <true | false>,
      "result_direction": "IMPROVED" | "NOT_IMPROVED" | "MIXED" | "UNKNOWN",
      "reached_significance": <true | false | null>
    }}
  ],

  "primary_analysis_set": "<voir liste>",
  "sample_size_calculation_provided": <true | false>,

  "primary_endpoint_met": <true | false | null>,
  "key_safety_signals": ["<signal 1>", "<signal 2>"],
  "study_countries": ["<pays 1>", "<pays 2>"],

  "device_alignment": {{
    "device_match_type": "<voir liste>",
    "device_description_study": "<nom dispositif dans l'étude>",
    "justification": "<explication>"
  }},
  "population_alignment": {{
    "population_match_type": "<voir liste>",
    "population_description_study": "<population étudiée>",
    "eligibility_shift": "NONE" | "MINOR" | "MAJOR",
    "justification": "<explication>"
  }},
  "context_alignment": {{
    "context_match_type": "<voir liste>",
    "care_pathway_match": "YES" | "PARTIAL" | "NO",
    "organization_dependency": "LOW" | "MEDIUM" | "HIGH",
    "study_country": "<pays principal>",
    "justification": "<explication>"
  }}
}}"""


_BLINDING_MAP: dict[str, BlindingLevel] = {
    "OPEN_LABEL": BlindingLevel.OPEN_LABEL,
    "SINGLE_BLIND": BlindingLevel.SINGLE_BLIND,
    "DOUBLE_BLIND": BlindingLevel.DOUBLE_BLIND,
    "SHAM_CONTROLLED": BlindingLevel.SHAM_CONTROLLED,
    "UNKNOWN": BlindingLevel.UNKNOWN,
}

_COMPARATOR_MAP: dict[str, ComparatorType] = {
    "SHAM": ComparatorType.SHAM,
    "PLACEBO": ComparatorType.PLACEBO,
    "ACTIVE": ComparatorType.ACTIVE,
    "STANDARD_OF_CARE": ComparatorType.STANDARD_OF_CARE,
    "BEST_AVAILABLE": ComparatorType.BEST_AVAILABLE,
    "NONE": ComparatorType.NONE,
    "UNKNOWN": ComparatorType.UNKNOWN,
}

_COMPARATOR_FEASIBILITY_MAP: dict[str, ComparatorFeasibility] = {
    "FEASIBLE": ComparatorFeasibility.FEASIBLE,
    "DIFFERENT_MODALITY": ComparatorFeasibility.DIFFERENT_MODALITY,
    "NO_ALTERNATIVE": ComparatorFeasibility.NO_ALTERNATIVE,
    "UNKNOWN": ComparatorFeasibility.UNKNOWN,
}

_ANALYSIS_SET_MAP: dict[str, AnalysisSet] = {
    "ITT": AnalysisSet.ITT,
    "mITT": AnalysisSet.mITT,
    "PP": AnalysisSet.PP,
    "FAS": AnalysisSet.FAS,
    "UNKNOWN": AnalysisSet.UNKNOWN,
}

_CARE_SETTING_MAP: dict[str, CareSetting] = {
    "INPATIENT": CareSetting.INPATIENT,
    "OUTPATIENT": CareSetting.OUTPATIENT,
    "HOME": CareSetting.HOME,
    "HYBRID": CareSetting.HYBRID,
    "UNKNOWN": CareSetting.UNKNOWN,
}

_FUNDING_MAP: dict[str, FundingType] = {
    "INDUSTRY": FundingType.INDUSTRY,
    "ACADEMIC": FundingType.ACADEMIC,
    "PUBLIC": FundingType.PUBLIC,
    "MIXED": FundingType.MIXED,
    "UNKNOWN": FundingType.UNKNOWN,
}

_RESULT_DIR_MAP: dict[str, ResultDirection] = {
    "IMPROVED": ResultDirection.IMPROVED,
    "NOT_IMPROVED": ResultDirection.NOT_IMPROVED,
    "MIXED": ResultDirection.MIXED,
    "UNKNOWN": ResultDirection.UNKNOWN,
}


def _repair_truncated_json(raw: str) -> dict:
    """Best-effort recovery for a truncated LLM JSON response.

    Closes unclosed strings, arrays, and objects so json.loads can parse
    whatever was received. Returns an empty dict if recovery fails.
    """
    # Close an in-progress string if needed
    in_string = False
    escaped = False
    for ch in raw:
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        raw += '"'

    # Close all unclosed containers in reverse order
    stack = []
    in_string = False
    escaped = False
    for ch in raw:
        if escaped:
            escaped = False
            continue
        if ch == '\\' and in_string:
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch in '{[':
                stack.append('}' if ch == '{' else ']')
            elif ch in '}]':
                if stack and stack[-1] == ch:
                    stack.pop()

    raw += ''.join(reversed(stack))
    try:
        return json.loads(raw)
    except Exception:
        return {}


def parse_study_object_with_llm(
    study_text: str,
    claim_device: str,
    claim_indication: str,
) -> StudyObject:
    """Parse a full study text (protocol / article / CER) into a complete StudyObject."""
    client = _get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        temperature=0,
        system=_SYSTEM_PROMPT_FULL,
        messages=[{
            "role": "user",
            "content": _USER_TEMPLATE_FULL.format(
                claim_device=claim_device,
                claim_indication=claim_indication,
                study_text=study_text,
            ),
        }],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # LLM response was truncated — try to recover the largest valid prefix
        data = _repair_truncated_json(raw)

    return _parse_study_object_result(data, claim_device, claim_indication)


def _parse_study_object_result(
    data: dict,
    claim_device: str,
    claim_indication: str,
) -> StudyObject:
    """Map raw LLM JSON to StudyObject. No LLM call — pure data mapping."""
    obj = StudyObject()

    obj.acronym = data.get("acronym") or ""
    obj.title = data.get("title") or ""
    obj.publication_year = data.get("publication_year")
    obj.registration_id = data.get("registration_id") or ""
    obj.funding_type = _FUNDING_MAP.get(data.get("funding_type", ""), FundingType.UNKNOWN)

    design_str = data.get("study_design")
    if design_str:
        obj.study_design = _DESIGN_MAP.get(design_str)

    obj.is_randomized = bool(data.get("is_randomized", False))
    obj.blinding_level = _BLINDING_MAP.get(
        data.get("blinding_level", "UNKNOWN"), BlindingLevel.UNKNOWN
    )
    obj.who_is_blinded = data.get("who_is_blinded") or []
    obj.allocation_concealment = data.get("allocation_concealment")
    obj.protocol_registered_before_enrollment = data.get("protocol_registered_before_enrollment")

    obj.has_comparator = data.get("has_comparator")
    obj.comparator_type = _COMPARATOR_MAP.get(
        data.get("comparator_type", "UNKNOWN"), ComparatorType.UNKNOWN
    )
    obj.comparator_description = data.get("comparator_description") or ""
    obj.comparator_feasibility = _COMPARATOR_FEASIBILITY_MAP.get(
        data.get("comparator_feasibility", "UNKNOWN"), ComparatorFeasibility.UNKNOWN
    )

    obj.n_patients = data.get("n_patients")
    obj.age_min = data.get("age_min")
    obj.age_max = data.get("age_max")
    obj.key_inclusion_criteria = data.get("key_inclusion_criteria") or []
    obj.key_exclusion_criteria = data.get("key_exclusion_criteria") or []

    obj.device_studied = data.get("device_studied") or ""
    obj.care_setting = _CARE_SETTING_MAP.get(
        data.get("care_setting", "UNKNOWN"), CareSetting.UNKNOWN
    )
    obj.operator_training_required = data.get("operator_training_required")

    obj.follow_up_months = data.get("follow_up_months")
    obj.longest_follow_up_months = data.get("longest_follow_up_months")
    obj.dropout_rate_pct = data.get("dropout_rate_pct")

    for ep in data.get("endpoints", []):
        result_dir = _RESULT_DIR_MAP.get(
            ep.get("result_direction", "UNKNOWN"), ResultDirection.UNKNOWN
        )
        obj.endpoints.append(StudyEndpoint(
            name=ep.get("name", ""),
            is_primary=bool(ep.get("is_primary", False)),
            time_point=ep.get("time_point") or "",
            is_validated_surrogate=bool(ep.get("is_validated_surrogate", False)),
            is_feasibility_accepted_surrogate=bool(ep.get("is_feasibility_accepted_surrogate", False)),
            is_independently_adjudicated=bool(ep.get("is_independently_adjudicated", False)),
            result_direction=result_dir,
            reached_significance=ep.get("reached_significance"),
        ))

    obj.primary_analysis_set = _ANALYSIS_SET_MAP.get(
        data.get("primary_analysis_set", "UNKNOWN"), AnalysisSet.UNKNOWN
    )
    obj.sample_size_calculation_provided = bool(data.get("sample_size_calculation_provided", False))

    obj.study_countries = data.get("study_countries") or []
    obj.primary_endpoint_met = data.get("primary_endpoint_met")

    # Fallback: if study_countries still empty, extract from context_alignment.study_country
    if not obj.study_countries:
        ctx_raw = data.get("context_alignment", {})
        study_country_str = ctx_raw.get("study_country", "")
        if study_country_str:
            obj.study_countries = [c.strip() for c in study_country_str.replace("/", ",").split(",") if c.strip()]
    obj.key_safety_signals = data.get("key_safety_signals") or []

    # CAS alignment (same mapping as Mode 1)
    dev = data.get("device_alignment", {})
    if dev:
        obj.device_alignment = DeviceAlignment(
            device_match_type=DeviceMatchType(dev.get("device_match_type", "UNKNOWN")),
            device_description_claim=claim_device,
            device_description_study=dev.get("device_description_study", ""),
            justification=dev.get("justification", ""),
        )

    pop = data.get("population_alignment", {})
    if pop:
        obj.population_alignment = PopulationAlignment(
            population_match_type=PopulationMatchType(pop.get("population_match_type", "UNKNOWN")),
            population_description_claim=claim_indication,
            population_description_study=pop.get("population_description_study", ""),
            eligibility_shift=EligibilityShift(pop.get("eligibility_shift", "NONE")),
            justification=pop.get("justification", ""),
        )

    ctx = data.get("context_alignment", {})
    if ctx:
        study_country = ctx.get("study_country", "")
        obj.context_alignment = ContextAlignment(
            context_match_type=_resolve_context_match(ctx.get("context_match_type", "UNKNOWN"), study_country),
            care_pathway_match=CarePathwayMatch(ctx.get("care_pathway_match", "PARTIAL")),
            organization_dependency=OrganizationDependency(
                ctx.get("organization_dependency", "MEDIUM")
            ),
            study_country=study_country,
            target_country="France",
            justification=ctx.get("justification", ""),
        )

    return obj


# ---------------------------------------------------------------------------
# PDF loader
# ---------------------------------------------------------------------------

def load_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file. Requires pdfplumber or pypdf."""
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        pass

    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(pdf_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        pass

    raise ImportError(
        "PDF extraction requires pdfplumber or pypdf. "
        "Install with: pip install pdfplumber"
    )


# ---------------------------------------------------------------------------
# Mode 2 convenience: PDF → StudyObject
# ---------------------------------------------------------------------------

def analyze_pdf(
    pdf_path: str,
    claim: ClinicalClaim,
) -> tuple[ClinicalClaim, StudyObject]:
    """Load a PDF, extract full StudyObject, enrich the claim. Returns (enriched_claim, study)."""
    from study_object import enrich_claim_with_study_object

    text = load_pdf(pdf_path)
    study = parse_study_object_with_llm(
        study_text=text,
        claim_device=claim.intervention,
        claim_indication=claim.text,
    )
    enriched = enrich_claim_with_study_object(claim, study)
    return enriched, study
