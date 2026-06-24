export const CLAIM_LEVELS = {
  MECHANISM: { fr: 'Mécanisme', en: 'Mechanism' },
  PROCESS: { fr: 'Processus', en: 'Process' },
  OUTCOME: { fr: 'Résultat clinique', en: 'Clinical outcome' },
  COMPLETE_CHAIN: { fr: 'Chaîne complète', en: 'Complete chain' },
}

export const CAUSAL_STRUCTURES = {
  DIRECT: { fr: 'Directe', en: 'Direct' },
  MEDIATED: { fr: 'Médiée', en: 'Mediated' },
  CIRCULAR: { fr: 'Circulaire', en: 'Circular' },
  INVALID: { fr: 'Invalide', en: 'Invalid' },
}

export const STUDY_DESIGNS = {
  RCT: { fr: 'Essai randomisé contrôlé', en: 'Randomized controlled trial' },
  SHAM_RCT: { fr: 'RCT avec sham', en: 'Sham RCT' },
  PRAGMATIC_RCT: { fr: 'RCT pragmatique', en: 'Pragmatic RCT' },
  COHORT: { fr: 'Cohorte', en: 'Cohort' },
  ITS: { fr: 'Séries temporelles interrompues', en: 'Interrupted time series' },
  BEFORE_AFTER: { fr: 'Avant-après', en: 'Before-after' },
  MATCHED_OBSERVATIONAL: { fr: 'Observationnel apparié', en: 'Matched observational' },
  EXPLORATORY: { fr: 'Exploratoire', en: 'Exploratory' },
  NOT_IDENTIFIABLE: { fr: 'Non identifiable', en: 'Not identifiable' },
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
  INVALID: { fr: 'Invalide', en: 'Invalid' },
  FRAGILE: { fr: 'Fragile', en: 'Fragile' },
  ACCEPTABLE: { fr: 'Acceptable', en: 'Acceptable' },
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

export function label(map, key, lang) {
  return map[key]?.[lang] || key
}
