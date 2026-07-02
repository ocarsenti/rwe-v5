export const CLAIM_LEVELS = {
  MECHANISM: { fr: 'Mécanisme', en: 'Mechanism', desc_fr: 'Le dispositif revendique un effet au niveau mécanistique — le niveau de preuve requis est le plus bas.', desc_en: 'The device claims a mechanistic effect — the lowest burden of proof.' },
  PROCESS: { fr: 'Processus', en: 'Process', desc_fr: 'Le dispositif revendique une amélioration de processus ou d\'usage, sans preuve d\'impact clinique direct.', desc_en: 'Claims a process or usage improvement without direct clinical impact.' },
  OUTCOME: { fr: 'Résultat clinique', en: 'Clinical outcome', desc_fr: 'Revendication d\'un résultat clinique mesurable — niveau de preuve élevé requis.', desc_en: 'Claims a measurable clinical outcome — high burden of proof.' },
  COMPLETE_CHAIN: { fr: 'Chaîne complète', en: 'Complete chain', desc_fr: 'Revendication de la chaîne causale complète mécanisme → outcome clinique — niveau de preuve maximal.', desc_en: 'Claims the full causal chain from mechanism to clinical outcome — maximum burden of proof.' },
}

export const CAUSAL_STRUCTURES = {
  DIRECT: { fr: 'Directe', en: 'Direct', desc_fr: 'Relation directe entre le dispositif et l\'outcome — structure causale testable par un design classique.', desc_en: 'Direct device-to-outcome relationship — testable with standard designs.' },
  MEDIATED: { fr: 'Médiée', en: 'Mediated', desc_fr: 'L\'effet passe par un médiateur intermédiaire — la chaîne causale doit être documentée.', desc_en: 'Effect passes through an intermediate mediator — causal chain must be documented.' },
  CIRCULAR: { fr: 'Circulaire', en: 'Circular', desc_fr: 'Le dispositif influence sa propre mesure de performance. L\'inférence causale est compromise sans reformulation du critère principal.', desc_en: 'The device influences its own performance measurement. Causal inference is compromised without redefining the primary endpoint.' },
  INVALID: { fr: 'Invalide', en: 'Invalid', desc_fr: 'La structure causale ne permet pas de tester la revendication telle qu\'elle est formulée.', desc_en: 'The causal structure cannot support the claim as stated.' },
}

export const STUDY_DESIGNS = {
  RCT: { fr: 'Essai randomisé contrôlé', en: 'Randomized controlled trial', desc_fr: 'Gold standard pour les revendications d\'efficacité clinique.', desc_en: 'Gold standard for clinical efficacy claims.' },
  SHAM_RCT: { fr: 'RCT avec sham', en: 'Sham RCT', desc_fr: 'RCT avec procédure simulée — requis pour contrôler l\'effet placebo sur les critères subjectifs.', desc_en: 'RCT with sham procedure — required to control for placebo on subjective endpoints.' },
  PRAGMATIC_RCT: { fr: 'RCT pragmatique', en: 'Pragmatic RCT', desc_fr: 'RCT en conditions réelles de soin — pour évaluer la généralisabilité de l\'effet.', desc_en: 'Real-world RCT — to assess generalizability of the effect.' },
  COHORT: { fr: 'Cohorte', en: 'Cohort', desc_fr: 'Étude observationnelle de cohorte — acceptable pour certains effets à long terme si le biais est contrôlé.', desc_en: 'Observational cohort study — acceptable for some long-term effects if bias is controlled.' },
  ITS: { fr: 'Séries temporelles interrompues', en: 'Interrupted time series', desc_fr: 'Pour les interventions introduites à un moment précis dans une population.', desc_en: 'For interventions introduced at a specific time point in a population.' },
  BEFORE_AFTER: { fr: 'Avant-après', en: 'Before-after', desc_fr: 'Comparaison avant/après sans contrôle — niveau de preuve limité.', desc_en: 'Before/after comparison without control — limited evidence level.' },
  MATCHED_OBSERVATIONAL: { fr: 'Observationnel apparié', en: 'Matched observational', desc_fr: 'Alternative au RCT si non faisable — appariement pour réduire le biais de sélection.', desc_en: 'Alternative to RCT when not feasible — matching to reduce selection bias.' },
  EXPLORATORY: { fr: 'Exploratoire', en: 'Exploratory', desc_fr: 'Design de génération d\'hypothèses — ne permet pas d\'inférence causale.', desc_en: 'Hypothesis-generating design — does not allow causal inference.' },
  NOT_IDENTIFIABLE: { fr: 'Non identifiable', en: 'Not identifiable', desc_fr: 'Aucun design standard ne peut tester la revendication telle qu\'elle est formulée — reformulation nécessaire.', desc_en: 'No standard design can test the claim as stated — reformulation required.' },
}

export const ENDPOINT_NATURES = {
  OBJECTIVE: { fr: 'Objectif', en: 'Objective' },
  SUBJECTIVE: { fr: 'Subjectif', en: 'Subjective' },
  INSTRUMENTED: { fr: 'Instrumenté', en: 'Instrumented' },
}

export const CAUSAL_ROLES = {
  INDEPENDENT: { fr: 'Indépendant', en: 'Independent' },
  MEDIATED: { fr: 'Médié', en: 'Mediated' },
  CIRCULAR: { fr: 'Circulaire', en: 'Circular' },
}

export const BIAS_FLAGS = {
  CIRCULARITY_RISK: { fr: 'Risque de circularité', en: 'Circularity risk' },
  DETECTION_BIAS: { fr: 'Biais de détection', en: 'Detection bias' },
  PERCEPTION_BIAS: { fr: 'Biais de perception', en: 'Perception bias' },
  MEDIATION_GAP: { fr: 'Gap de médiation', en: 'Mediation gap' },
  PROCESS_TAUTOLOGY: { fr: 'Tautologie de processus', en: 'Process tautology' },
}

export const MANIFOLD_REGIONS = {
  INVALID: { fr: 'Inférence non valide', en: 'Invalid inference', desc_fr: 'L\'étude ne peut pas supporter d\'inférence causale en l\'état — une restructuration est nécessaire.', desc_en: 'The study cannot support causal inference as structured — restructuring is required.' },
  FRAGILE: { fr: 'Fragile', en: 'Fragile', desc_fr: 'L\'inférence causale est possible mais avec des limitations importantes à documenter.', desc_en: 'Causal inference is possible but with important limitations to document.' },
  ACCEPTABLE: { fr: 'Acceptable', en: 'Acceptable', desc_fr: 'La structure de preuve est compatible avec la revendication formulée.', desc_en: 'The evidence structure is compatible with the stated claim.' },
}

export const REPAIR_STATUS = {
  REPAIRABLE: { fr: 'Réparable', en: 'Repairable' },
  NON_REPAIRABLE: { fr: 'Non réparable', en: 'Non repairable' },
  NO_REPAIR_NEEDED: { fr: 'Aucune réparation nécessaire', en: 'No repair needed' },
}

export const REGULATORY_STATUS = {
  ACCEPTABLE_PRIMARY_WITH_CONDITIONS: { fr: 'Acceptable en primaire (avec conditions)', en: 'Acceptable as primary (with conditions)' },
  ACCEPTABLE_SECONDARY_ONLY: { fr: 'Acceptable en secondaire uniquement', en: 'Acceptable as secondary only' },
  ACCEPTABLE_WITH_REDESIGN: { fr: 'Acceptable avec refonte', en: 'Acceptable with redesign' },
  INVALID_AS_PRIMARY_ENDPOINT_ONLY: { fr: 'Invalide en critère primaire seul', en: 'Invalid as primary endpoint only' },
  REJECTED_UNLESS_EXTERNAL_VALIDATION: { fr: 'Rejeté sauf validation externe', en: 'Rejected unless external validation' },
}

export const ISSUE_TYPES = {
  MEASUREMENT_CIRCULARITY: { fr: 'Circularité de mesure', en: 'Measurement circularity' },
  CARE_PATHWAY_BIAS: { fr: 'Biais de parcours de soins', en: 'Care pathway bias' },
  DETECTION_ACCELERATION: { fr: 'Accélération de détection', en: 'Detection acceleration' },
  SUBJECTIVE_ENDPOINT_BIAS: { fr: 'Biais d\'endpoint subjectif', en: 'Subjective endpoint bias' },
}

export const ENDPOINT_STATUS = {
  ACCEPTABLE: { fr: 'Acceptable', en: 'Acceptable' },
  ACCEPTABLE_WITH_CONDITIONS: { fr: 'Acceptable avec conditions', en: 'Acceptable with conditions' },
  INVALID_AS_PRIMARY_ONLY: { fr: 'Invalide en primaire seul', en: 'Invalid as primary only' },
  INVALID_UNLESS_REDEFINED: { fr: 'Invalide sauf redéfinition', en: 'Invalid unless redefined' },
}

export const REGULATORY_STRENGTH = {
  PRIMARY_CANDIDATE: { fr: 'Candidat primaire', en: 'Primary candidate' },
  SECONDARY_ONLY: { fr: 'Secondaire uniquement', en: 'Secondary only' },
  EXPLORATORY: { fr: 'Exploratoire', en: 'Exploratory' },
}

export const REPAIR_EP_TYPES = {
  HARD_CLINICAL: { fr: 'Clinique dur', en: 'Hard clinical' },
  SOFT_CLINICAL: { fr: 'Clinique souple', en: 'Soft clinical' },
  UTILIZATION: { fr: 'Utilisation', en: 'Utilization' },
  BIOMARKER: { fr: 'Biomarqueur', en: 'Biomarker' },
  PROM: { fr: 'PROM', en: 'PROM' },
  SURVIVAL: { fr: 'Survie', en: 'Survival' },
}

export const DEVICE_MATCH_TYPES = {
  EXACT_DEVICE: { fr: 'Dispositif identique', en: 'Exact device' },
  SAME_FAMILY: { fr: 'Même famille', en: 'Same family' },
  PROXY_DEVICE: { fr: 'Dispositif proxy', en: 'Proxy device' },
  DIFFERENT_DEVICE: { fr: 'Dispositif différent', en: 'Different device' },
  UNKNOWN: { fr: 'Inconnu', en: 'Unknown' },
}

export const POPULATION_MATCH_TYPES = {
  EXACT_INDICATION: { fr: 'Indication exacte', en: 'Exact indication' },
  NARROWER_SUBGROUP: { fr: 'Sous-groupe', en: 'Narrower subgroup' },
  BROADER_POPULATION: { fr: 'Population plus large', en: 'Broader population' },
  DIFFERENT_POPULATION: { fr: 'Population différente', en: 'Different population' },
  UNKNOWN: { fr: 'Inconnu', en: 'Unknown' },
}

export const CONTEXT_MATCH_TYPES = {
  SAME_HEALTHCARE_SYSTEM: { fr: 'Même système de soins', en: 'Same healthcare system' },
  PARTIALLY_COMPARABLE: { fr: 'Partiellement comparable', en: 'Partially comparable' },
  DIFFERENT_SYSTEM: { fr: 'Système différent', en: 'Different system' },
  UNKNOWN: { fr: 'Inconnu', en: 'Unknown' },
}

export const CARE_PATHWAY_MATCHES = {
  YES: { fr: 'Oui', en: 'Yes' },
  PARTIAL: { fr: 'Partiel', en: 'Partial' },
  NO: { fr: 'Non', en: 'No' },
  UNKNOWN: { fr: 'Inconnu', en: 'Unknown' },
}

export const ELIGIBILITY_SHIFTS = {
  NONE: { fr: 'Aucun', en: 'None' },
  MINOR: { fr: 'Mineur', en: 'Minor' },
  MAJOR: { fr: 'Majeur', en: 'Major' },
}

export const ORGANIZATION_DEPENDENCIES = {
  LOW: { fr: 'Faible', en: 'Low' },
  MEDIUM: { fr: 'Moyenne', en: 'Medium' },
  HIGH: { fr: 'Élevée', en: 'High' },
}

export const CAS_VERDICTS = {
  ACCEPTABLE: { fr: 'Cohérent', en: 'Coherent' },
  WEAK_EVIDENCE: { fr: 'Partiellement cohérent', en: 'Partially coherent' },
  REJECTED: { fr: 'Non cohérent', en: 'Not coherent' },
}

export function label(map, key, lang) {
  return map[key]?.[lang] || key
}

export function desc(map, key, lang) {
  return map[key]?.[lang === 'fr' ? 'desc_fr' : 'desc_en'] || null
}
