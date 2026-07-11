"""LLM-based evidence parser — extracts study metadata and CAS alignment from raw study text.

Mode 1 (light): parse_study_with_llm() → StudyParseResult
  Takes abstract / excerpt, returns metadata + CAS alignment objects.
  Uses ~800 tokens. Low cost.

Mode 2 (full): parse_study_object_with_llm() → StudyObject
  Takes full protocol / PDF text, returns complete StudyObject with
  blinding, comparator, inclusion criteria, per-endpoint results, etc.
  Uses ~2000 tokens. Premium tier.
  parse_study_object_with_llm_consensus() runs it n_calls times in parallel and
  majority-votes per field — use this one in production, single-call is not stable
  run-to-run even at temperature=0.

load_pdf(path) → str   : PDF text extractor (pdfplumber or pypdf)
"""

from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import anthropic

from models import (
    CarePathwayMatch,
    CausalRole,
    ClinicalClaim,
    ComparatorFeasibility,
    ContextAlignment,
    ContextMatchType,
    DeviceAlignment,
    DeviceMatchType,
    EligibilityShift,
    EndpointNature,
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
- "EXTERNAL_CONTROL_COHORT" : étude bras unique dont le critère de jugement principal est
  comparé aux résultats d'une cohorte de contrôle externe (historique, registre, ou tirée
  de la littérature) — un comparateur réel existe (has_comparator=true), mais il n'est ni
  concurrent ni randomisé. Distinct de "SINGLE_ARM_PERFORMANCE_GOAL" (comparaison à un
  seuil numérique fixe, pas à une cohorte de patients) et de "REGISTRY" (aucune comparaison
  formelle revendiquée).
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
  "study_design": "RCT" | "SINGLE_ARM" | "SINGLE_ARM_PERFORMANCE_GOAL" | "EXTERNAL_CONTROL_COHORT" | "REGISTRY" | "COHORT" | "BEFORE_AFTER" | "META_ANALYSIS" | "MATCHED_OBSERVATIONAL" | "EXPLORATORY",
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
    "EXTERNAL_CONTROL_COHORT": StudyDesign.EXTERNAL_CONTROL_COHORT,
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

## multiple_studies_detected
true si le texte décrit **plusieurs études cliniques distinctes** du dispositif revendiqué
(auteurs/années différents, ou populations/designs clairement séparés) plutôt qu'une seule
étude. Ne compte pas comme une deuxième étude : une méta-analyse qui regroupe les mêmes
données, ou une simple mention en référence sans description propre. Si true, remplis quand
même le Study Object avec la première étude clairement décrite (ne cherche PAS à deviner
laquelle est la plus pertinente ni à fusionner les études entre elles) et liste les études
identifiées dans "other_studies_mentioned" (ex: "Nishi et al. 2023", "Quimby et al. 2025") —
c'est à l'utilisateur de préciser ensuite laquelle est l'étude pivot, pas au modèle de trancher.

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
- "EXTERNAL_CONTROL_COHORT" : bras unique comparé aux résultats d'une cohorte de contrôle
  externe (historique, registre, ou littérature) — comparateur réel (has_comparator=true),
  mais ni concurrent ni randomisé. Distinct de "SINGLE_ARM_PERFORMANCE_GOAL" (seuil
  numérique fixe, pas une cohorte de patients) et de "REGISTRY" (aucune comparaison
  formelle revendiquée).
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

## concomitant_treatments_present / concomitant_treatments_controlled
Pertinent quand l'indication admet des traitements concomitants standards (ex. hypnotiques
dans l'apnée du sommeil, antalgiques dans la douleur chronique) qui pourraient eux-mêmes
expliquer l'effet observé.
- **concomitant_treatments_present** : true si l'étude mentionne explicitement que des
  patients recevaient un traitement concomitant pertinent pour l'indication pendant l'étude.
  false si le protocole les exclut explicitement ou si l'indication n'a pas de traitement
  concomitant pertinent plausible. null si non déterminable.
- **concomitant_treatments_controlled** : pertinent uniquement si present=true. true si ces
  traitements sont documentés ET stables/exclus par critère d'éligibilité/ajustés
  statistiquement (covariable, stratification, sensibilité). false si mentionnés mais non
  contrôlés dans l'analyse. null si non déterminable.
- **concomitant_treatments_description** : brève description textuelle si pertinent, sinon "".

## endpoint_hierarchy_prespecified
Pertinent uniquement si plusieurs endpoints sont marqués is_primary=true. true si une
procédure de contrôle de la multiplicité (hiérarchisation séquentielle, gatekeeping,
répartition alpha) est explicitement documentée dans le plan d'analyse statistique. false ou
null sinon.

## performance_goal_clinically_justified
Pertinent uniquement si study_design="SINGLE_ARM_PERFORMANCE_GOAL". true si le texte
justifie explicitement le seuil de succès retenu (référence à une donnée historique, un
consensus clinique, ou un critère réglementaire documenté). false ou null si le seuil est
mentionné sans justification clinique de sa valeur.

## indication_matches_ce_marking
Ce champ porte UNIQUEMENT sur le marquage CE réglementaire du dispositif — ne le confonds
PAS avec le champ population/eligibility_shift, qui compare déjà la population étudiée à
l'indication REVENDIQUÉE par le demandeur. Ici, la seule question est : la population ou le
site anatomique étudié sort-il du périmètre du MARQUAGE CE ?

- true : le texte précise le périmètre du marquage CE (indication, population ou site
  anatomique couvert) ET la population/l'usage étudié y reste.
- false : le texte mentionne EXPLICITEMENT le marquage CE (ou une notion équivalente —
  autorisation, indication réglementaire du dispositif) ET indique qu'une partie de la
  population étudiée ou de l'usage du dispositif (ex : un site anatomique) en sort. Il faut
  une phrase du texte qui parle du statut réglementaire/marquage du dispositif lui-même, pas
  seulement des critères d'inclusion/exclusion de l'étude.
- null : le texte ne mentionne jamais le marquage CE ou le périmètre réglementaire du
  dispositif — y compris quand l'étude a des critères d'inclusion/exclusion restrictifs ou une
  population plus étroite que l'indication revendiquée. Une population d'étude plus étroite
  que la revendication n'est PAS en soi un indice de non-conformité au marquage CE : c'est un
  fait clinique (déjà capté par population/eligibility_shift), pas un fait réglementaire. En
  l'absence de toute mention explicite du marquage CE dans le texte, la réponse est null, même
  si tu soupçonnes une non-conformité.

Exemple positif (false) : un avis précise que le dispositif est marqué CE pour l'usage
intracrânien, et que l'étude soumise inclut aussi des patients traités en artère vertébrale,
explicitement identifiée dans le texte comme hors du périmètre du marquage CE (cf. WALRUS
7182).
Exemple négatif (null, pas false) : une étude exclut les "lésions complexes" de ses critères
d'inclusion alors que l'indication revendiquée cible spécifiquement les lésions complexes,
mais le texte ne dit rien du marquage CE du dispositif — répondre null, pas false, même si la
population étudiée ne correspond pas à la revendication (cf. VIS-RX 8145 / étude Nishi).

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

## nature (par endpoint)
- "OBJECTIVE" : mesure indépendante de l'observateur (mortalité, hospitalisations, biomarqueurs)
- "SUBJECTIVE" : dépend du patient/observateur (douleur, qualité de vie, satisfaction, scores
  auto-rapportés comme l'ISI ou l'EVA)
- "INSTRUMENTED" : mesuré par le dispositif lui-même (temps de détection, alertes générées)

## causal_role (par endpoint)
- "INDEPENDENT" : critère clinique dur, atteint directement (mortalité, hospitalisation,
  complication, échec du dispositif) — même si biologiquement médié, c'est un critère
  patient-pertinent accepté comme tel, pas un marqueur intermédiaire
- "MEDIATED" : marqueur intermédiaire/de substitution qui n'est PAS lui-même le bénéfice
  clinique final (biomarqueur, score physiologique, critère composite non validé) — la chaîne
  causale vers un bénéfice clinique dur reste à démontrer
- "CIRCULAR" : couvre DEUX variantes du même piège — le dispositif est à la fois l'intervention
  et l'instrument de sa propre évaluation :
  1. Détection : l'endpoint EST ce que le dispositif mesure/détecte lui-même (ex : nombre
     d'alertes générées par un dispositif de surveillance).
  2. Performance procédurale : l'endpoint mesure si le dispositif a réussi à accomplir sa
     propre tâche mécanique/procédurale conçue (ex : succès technique de la navigation, du
     déploiement ou du positionnement d'un cathéter/d'une prothèse), plutôt qu'un bénéfice
     clinique indépendant pour le patient. Exemple : « succès technique de la navigation du
     cathéter jusqu'au vaisseau cible » est CIRCULAR, pas INDEPENDENT — il mesure si le
     dispositif a rempli sa fonction mécanique, pas un bénéfice patient direct (à distinguer
     de la reperfusion effective, d'un score fonctionnel ou de la mortalité, qui restent
     INDEPENDENT même s'ils sont obtenus grâce au dispositif).
IMPORTANT : ne classe MEDIATED que les marqueurs de substitution au sens strict. Un critère
clinique dur ou un score fonctionnel/qualité de vie validé dans l'indication reste INDEPENDENT
même s'il dépend biologiquement du mécanisme d'action — MEDIATED n'est pas un synonyme de
"non direct", c'est réservé aux vrais critères intermédiaires.

## value_fixed_by_protocol (par endpoint)
Pertinent uniquement pour un critère de jugement comparatif (l'étude compare le dispositif à un
comparateur sur ce critère précis). true si la valeur du critère dans le bras du dispositif
évalué est fixée à l'avance par le protocole (un paramètre de design, pas une mesure), pendant
que la valeur du comparateur est réellement mesurée — ce qui rend toute "supériorité" sur ce
critère tautologique par construction, indépendamment du dispositif. false sinon (valeur
réellement mesurée dans les deux bras, ou critère non comparatif). Exemple : volume de produit
de contraste injecté fixé à 5 mL par protocole dans le bras du cathéter évalué, mesuré librement
dans le bras du cathéter comparateur (avis CNEDiMTS VIS-RX 8145, étude Nishi et al. 2023).

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
- "EXACT_DEVICE" : le dispositif étudié est exactement le dispositif revendiqué
- "SAME_FAMILY" : même famille (ex: COREVALVE EVOLUT R étudié, NAVITOR revendiqué)
- "PROXY_DEVICE" : dispositif similaire mais différent (ex: autre CGM étudié, FreeStyle revendiqué)
- "DIFFERENT_DEVICE" : dispositif fondamentalement différent
IMPORTANT — cohérence avec justification : si la preuve clinique déterminante (l'étude
pivot citée pour l'efficacité) porte en réalité sur un dispositif différent du dispositif
nommément revendiqué — même si un dispositif "identique" est mentionné ailleurs dans le
texte — classe EXACT_DEVICE est interdit ; utilise PROXY_DEVICE ou SAME_FAMILY selon le
degré de similarité, et explique ce transfert de preuve dans la justification (ex: SCEWO
BRO revendiqué, preuve clinique pivot = TOPCHAIR-S, dispositif différent → PROXY_DEVICE,
pas EXACT_DEVICE).
population_match_type : EXACT_INDICATION | NARROWER_SUBGROUP | BROADER_POPULATION | DIFFERENT_POPULATION | UNKNOWN
eligibility_shift : NONE | MINOR | MAJOR
context_match_type : SAME_HEALTHCARE_SYSTEM | PARTIALLY_COMPARABLE | DIFFERENT_SYSTEM | UNKNOWN
care_pathway_match : YES | PARTIAL | NO
organization_dependency : LOW | MEDIUM | HIGH

## Citations de vérification (champs critiques)
Ces champs pilotent directement la détection de biais et le score CAS — pour chacun,
fournis en plus, dans l'objet "citations", une citation VERBATIM (copiée mot pour mot
depuis le texte source, sans reformulation ni troncature par "...") qui justifie
littéralement la valeur retenue :
- has_comparator, is_randomized, comparator_type
- primary_endpoint_met, key_safety_signals
- device_alignment.device_match_type, population_alignment.eligibility_shift
- pour chaque endpoint : result_direction (via "result_citation") et
  reached_significance (via "significance_citation")

Si aucune phrase du texte source ne justifie littéralement la valeur retenue, laisse
la citation correspondante vide ("") plutôt que d'inventer une citation approximative
ou paraphrasée — une citation vide ou introuvable fera que le champ est ignoré côté
applicatif (traité comme non déterminé) plutôt que silencieusement fait confiance."""

_USER_TEMPLATE_FULL = """Analyse ce texte d'étude clinique et extrais le Study Object complet.

**Dispositif revendiqué** : {claim_device}
**Indication revendiquée** : {claim_indication}

**Texte de l'étude** :
{study_text}

Réponds en JSON avec ce format exact :
{{
  "multiple_studies_detected": <true | false>,
  "other_studies_mentioned": ["<étude 1, ex: Nishi et al. 2023>", "<étude 2>"],

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

  "concomitant_treatments_present": <true | false | null>,
  "concomitant_treatments_controlled": <true | false | null>,
  "concomitant_treatments_description": "<description ou \"\">",
  "performance_goal_clinically_justified": <true | false | null>,
  "indication_matches_ce_marking": <true | false | null>,

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
      "nature": "OBJECTIVE" | "SUBJECTIVE" | "INSTRUMENTED",
      "causal_role": "INDEPENDENT" | "MEDIATED" | "CIRCULAR",
      "is_validated_surrogate": <true | false>,
      "is_independently_adjudicated": <true | false>,
      "result_direction": "IMPROVED" | "NOT_IMPROVED" | "MIXED" | "UNKNOWN",
      "reached_significance": <true | false | null>,
      "value_fixed_by_protocol": <true | false>,
      "result_citation": "<citation verbatim justifiant result_direction, ou \"\">",
      "significance_citation": "<citation verbatim justifiant reached_significance, ou \"\">"
    }}
  ],
  "endpoint_hierarchy_prespecified": <true | false | null>,

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
  }},

  "citations": {{
    "has_comparator_citation": "<citation verbatim ou \"\">",
    "is_randomized_citation": "<citation verbatim ou \"\">",
    "comparator_type_citation": "<citation verbatim ou \"\">",
    "primary_endpoint_met_citation": "<citation verbatim ou \"\">",
    "key_safety_signals_citation": "<citation verbatim ou \"\">",
    "device_match_type_citation": "<citation verbatim ou \"\">",
    "eligibility_shift_citation": "<citation verbatim ou \"\">"
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

_NATURE_MAP: dict[str, EndpointNature] = {
    "OBJECTIVE": EndpointNature.OBJECTIVE,
    "SUBJECTIVE": EndpointNature.SUBJECTIVE,
    "INSTRUMENTED": EndpointNature.INSTRUMENTED,
}

_CAUSAL_ROLE_MAP: dict[str, CausalRole] = {
    "INDEPENDENT": CausalRole.INDEPENDENT,
    "MEDIATED": CausalRole.MEDIATED,
    "CIRCULAR": CausalRole.CIRCULAR,
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


def _normalize_citation_text(text: str) -> str:
    """Same normalization has_vs_moteur.py's extract_verbatim_quote() applies before
    substring-checking a citation: join PDF line-wrap hyphenation, fold typographic
    apostrophes, collapse whitespace, and case-fold — so trivial extraction artifacts
    don't cause a genuine verbatim quote to fail verification."""
    text = re.sub(r"-\s*\n\s*", "", text)
    text = text.replace("’", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def _citation_verified(citation: str | None, source_text: str) -> bool:
    """A citation is trusted only if it is non-empty and a verbatim (whitespace/
    hyphenation-normalized) substring of the source study text — the same
    anti-fabrication check has_vs_moteur.py already applies to the HAS critique
    quote, extended here to the extracted study fields that most directly drive
    bias-flag/CAS scoring."""
    if not citation or not citation.strip():
        return False
    return _normalize_citation_text(citation) in _normalize_citation_text(source_text)


def _apply_citation_verification(obj: StudyObject, data: dict, study_text: str | None) -> None:
    """Reset the highest-impact extracted fields to a conservative safe default when
    the LLM's own supporting citation for that field can't be verified as a verbatim
    excerpt of study_text, and record which fields were rejected on
    obj.citation_rejected_fields. Covers comparator/randomization, primary endpoint
    result, safety signals, and device/population CAS alignment (see
    _SYSTEM_PROMPT_FULL's "Citations de vérification" section for the paired prompt
    instructions). No-op when study_text isn't available — manual form entry and
    hand-written test fixtures have no source text to verify a citation against."""
    if not study_text:
        return

    citations = data.get("citations") or {}
    rejected = obj.citation_rejected_fields

    def verified(key: str) -> bool:
        return _citation_verified(citations.get(key), study_text)

    if obj.has_comparator is not None and not verified("has_comparator_citation"):
        rejected.append("has_comparator")
        obj.has_comparator = None

    if obj.is_randomized and not verified("is_randomized_citation"):
        rejected.append("is_randomized")
        obj.is_randomized = False

    if obj.comparator_type != ComparatorType.UNKNOWN and not verified("comparator_type_citation"):
        rejected.append("comparator_type")
        obj.comparator_type = ComparatorType.UNKNOWN

    if obj.primary_endpoint_met is not None and not verified("primary_endpoint_met_citation"):
        rejected.append("primary_endpoint_met")
        obj.primary_endpoint_met = None

    if obj.key_safety_signals and not verified("key_safety_signals_citation"):
        rejected.append("key_safety_signals")
        obj.key_safety_signals = []

    if (obj.device_alignment is not None
            and obj.device_alignment.device_match_type != DeviceMatchType.UNKNOWN
            and not verified("device_match_type_citation")):
        rejected.append("device_alignment.device_match_type")
        obj.device_alignment.device_match_type = DeviceMatchType.UNKNOWN

    if (obj.population_alignment is not None
            and obj.population_alignment.eligibility_shift != EligibilityShift.NONE
            and not verified("eligibility_shift_citation")):
        rejected.append("population_alignment.eligibility_shift")
        obj.population_alignment.eligibility_shift = EligibilityShift.NONE

    raw_endpoints = data.get("endpoints") or []
    for i, ep in enumerate(obj.endpoints):
        raw = raw_endpoints[i] if i < len(raw_endpoints) else {}
        if ep.result_direction != ResultDirection.UNKNOWN and not _citation_verified(
            raw.get("result_citation"), study_text
        ):
            rejected.append(f"endpoints[{i}].result_direction")
            ep.result_direction = ResultDirection.UNKNOWN
        if ep.reached_significance is not None and not _citation_verified(
            raw.get("significance_citation"), study_text
        ):
            rejected.append(f"endpoints[{i}].reached_significance")
            ep.reached_significance = None


def _call_llm_for_study_object_raw(
    study_text: str,
    claim_device: str,
    claim_indication: str,
) -> dict:
    """Single LLM call → raw parsed JSON dict. No mapping to StudyObject. Thread-safe
    (each call gets its own response; the shared client is a plain HTTP wrapper)."""
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
        return json.loads(raw)
    except json.JSONDecodeError:
        # LLM response was truncated — try to recover the largest valid prefix
        return _repair_truncated_json(raw)


def parse_study_object_with_llm(
    study_text: str,
    claim_device: str,
    claim_indication: str,
    return_raw: bool = False,
) -> StudyObject | tuple[StudyObject, dict]:
    """Parse a full study text (protocol / article / CER) into a complete StudyObject.

    Single LLM call — subject to run-to-run instability even at temperature=0 (GPU
    batching makes floating-point results non-associative, and the Anthropic API has
    no `seed` param to force determinism; see project_rwe_v5 memory). For
    production-facing analyses where stability matters, prefer
    parse_study_object_with_llm_consensus() instead.

    If return_raw=True, also returns the raw parsed LLM JSON (dict) alongside the
    StudyObject — useful for archiving to detect that instability across runs.
    """
    data = _call_llm_for_study_object_raw(study_text, claim_device, claim_indication)
    study = _parse_study_object_result(data, claim_device, claim_indication, study_text=study_text)
    if return_raw:
        return study, data
    return study


# Leaf key names whose wording naturally varies between LLM calls without indicating
# judgment instability (free-text justification/description fields). Excluded from the
# unstable_fields report so it only flags fields that actually drive downstream logic
# (device_match_type, is_randomized, endpoints[].nature, etc.).
_FREE_TEXT_LEAF_KEYS = {
    "justification", "title", "device_description_study", "population_description_study",
    "comparator_description", "concomitant_treatments_description", "study_country", "name",
}

# Below this similarity ratio (difflib, on lowercased/stripped endpoint names), two
# endpoints from different runs are never considered "the same" endpoint even if
# is_primary agrees — avoids merging unrelated endpoints that happen to share
# primariness (e.g. mortality and vascular injury are both often primary safety/
# efficacy endpoints, but are not the same endpoint).
_ENDPOINT_NAME_MATCH_THRESHOLD = 0.55


def _endpoint_name_similarity(a: dict, b: dict) -> float:
    name_a = (a.get("name") or "").strip().lower()
    name_b = (b.get("name") or "").strip().lower()
    if not name_a or not name_b:
        return 0.0
    return difflib.SequenceMatcher(None, name_a, name_b).ratio()


def _align_endpoint_clusters(endpoint_lists: list[list[dict]]) -> list[list[dict]]:
    """Cluster endpoint dicts sampled from N parallel LLM parses of the SAME study into
    groups that plausibly represent "the same" endpoint, greedily, by is_primary
    agreement + fuzzy name similarity (see _ENDPOINT_NAME_MATCH_THRESHOLD).

    This exists because endpoint identity is not stable enough across calls to align
    by list position or exact name match (wording is paraphrased call to call, and —
    more importantly — which endpoints even get marked is_primary can itself differ
    between calls on genuinely ambiguous studies, e.g. avis CNEDiMTS WALRUS 7182 where
    7 identical calls found anywhere from 2 to 8 "primary" endpoints). Each cluster is
    later field-voted independently by _majority_vote; clusters that only a minority
    of calls produced are dropped by the caller rather than treated as consensus.
    """
    clusters: list[list[dict]] = []
    for endpoints in endpoint_lists:
        for ep in endpoints:
            if not isinstance(ep, dict):
                continue
            best_cluster = None
            best_score = 0.0
            for cluster in clusters:
                rep = cluster[0]
                if bool(rep.get("is_primary")) != bool(ep.get("is_primary")):
                    continue
                score = _endpoint_name_similarity(rep, ep)
                if score > best_score:
                    best_score = score
                    best_cluster = cluster
            if best_cluster is not None and best_score >= _ENDPOINT_NAME_MATCH_THRESHOLD:
                best_cluster.append(ep)
            else:
                clusters.append([ep])
    return clusters


def _vote_endpoints(endpoint_lists: list[list[dict]], path: str, unstable_paths: list[str]) -> list[dict]:
    """Majority-vote the `endpoints` list field-by-field per endpoint, instead of
    treating the whole list as one atomic blob (see _majority_vote's general docstring
    for why that's the default for other list fields). An endpoint only survives into
    the consensus result if a strict majority of the n_calls parses agree it exists
    (as a cluster from _align_endpoint_clusters) — anything short of that is dropped
    and flagged via `{path}.primary_endpoint_set` in unstable_paths, since a minority
    endpoint reflects real disagreement on the primary-endpoint set itself, not just
    wording noise on a field within an agreed-upon endpoint.
    """
    n_calls = len(endpoint_lists)
    clusters = _align_endpoint_clusters(endpoint_lists)
    majority_threshold = n_calls / 2

    consensus_endpoints = []
    dropped_minority = False
    for cluster in clusters:
        if len(cluster) > majority_threshold:
            consensus_endpoints.append(_majority_vote(cluster, f"{path}[]", unstable_paths))
        else:
            dropped_minority = True
    if dropped_minority:
        unstable_paths.append(f"{path}.primary_endpoint_set")
    return consensus_endpoints


def _majority_vote(values: list, path: str, unstable_paths: list[str]):
    """Recursively merge N raw LLM JSON parses (same shape, sampled at the same dotted
    path) into a single consensus value via per-leaf majority vote.

    Dicts are recursed into key-by-key. The `endpoints` list is special-cased via
    _vote_endpoints (see there for why list position/exact wording isn't a reliable
    alignment key for endpoints specifically). Every other list field is treated as an
    atomic unit and voted on directly — same rationale, but without a per-item
    alignment heuristic built for it (e.g. `who_is_blinded`, `study_countries`).
    Appends the dotted path to unstable_paths whenever the N values didn't unanimously
    agree, unless the leaf is a known free-text field (see _FREE_TEXT_LEAF_KEYS).
    """
    if all(isinstance(v, dict) for v in values):
        keys: set[str] = set()
        for v in values:
            keys.update(v.keys())
        result = {}
        for k in keys:
            sub_values = [v.get(k) for v in values]
            sub_path = f"{path}.{k}" if path else k
            if k == "endpoints" and all(sv is None or isinstance(sv, list) for sv in sub_values):
                result[k] = _vote_endpoints([sv or [] for sv in sub_values], sub_path, unstable_paths)
            else:
                result[k] = _majority_vote(sub_values, sub_path, unstable_paths)
        return result

    canonical = [json.dumps(v, sort_keys=True, ensure_ascii=False) for v in values]
    counts = Counter(canonical)
    winner, winner_count = counts.most_common(1)[0]
    leaf_key = path.rsplit(".", 1)[-1] if path else path
    is_free_text = leaf_key in _FREE_TEXT_LEAF_KEYS or leaf_key.endswith("_citation")
    if winner_count < len(values) and not is_free_text:
        unstable_paths.append(path)
    return values[canonical.index(winner)]


def parse_study_object_with_llm_consensus(
    study_text: str,
    claim_device: str,
    claim_indication: str,
    n_calls: int = 3,
) -> tuple[StudyObject, list[str]]:
    """Run n_calls parallel LLM parses of the same study and merge them via per-field
    majority vote — the production fix for temperature=0 instability (see
    parse_study_object_with_llm's docstring for why a single call isn't enough).

    Returns (consensus StudyObject, unstable_fields): unstable_fields lists the dotted
    JSON field paths where the n_calls parses did not unanimously agree (excluding
    free-text wording) — surface these to the caller as "needs manual review" rather
    than silently trusting whichever value won 2-1.
    """
    _get_client()  # initialize before spawning threads, avoid a lazy-init race
    with ThreadPoolExecutor(max_workers=n_calls) as pool:
        futures = [
            pool.submit(_call_llm_for_study_object_raw, study_text, claim_device, claim_indication)
            for _ in range(n_calls)
        ]
        raw_results = [f.result() for f in futures]

    unstable_fields: list[str] = []
    consensus_data = _majority_vote(raw_results, "", unstable_fields)
    study = _parse_study_object_result(consensus_data, claim_device, claim_indication, study_text=study_text)
    return study, unstable_fields


def _parse_study_object_result(
    data: dict,
    claim_device: str,
    claim_indication: str,
    study_text: str | None = None,
) -> StudyObject:
    """Map raw LLM JSON to StudyObject. No LLM call — pure data mapping."""
    obj = StudyObject()

    obj.multiple_studies_detected = bool(data.get("multiple_studies_detected", False))
    obj.other_studies_mentioned = data.get("other_studies_mentioned") or []

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

    obj.concomitant_treatments_present = data.get("concomitant_treatments_present")
    obj.concomitant_treatments_controlled = data.get("concomitant_treatments_controlled")
    obj.concomitant_treatments_description = data.get("concomitant_treatments_description") or ""
    obj.performance_goal_clinically_justified = data.get("performance_goal_clinically_justified")
    obj.indication_matches_ce_marking = data.get("indication_matches_ce_marking")

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
            nature=_NATURE_MAP.get(ep.get("nature", "OBJECTIVE"), EndpointNature.OBJECTIVE),
            causal_role=_CAUSAL_ROLE_MAP.get(ep.get("causal_role", "INDEPENDENT"), CausalRole.INDEPENDENT),
            value_fixed_by_protocol=bool(ep.get("value_fixed_by_protocol", False)),
        ))

    obj.endpoint_hierarchy_prespecified = data.get("endpoint_hierarchy_prespecified")

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

    _apply_citation_verification(obj, data, study_text)

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
