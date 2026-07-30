// ── Cas "conseil design" — distinct de la série "Cas réel" (review) ──────────
// Ici il n'y a pas d'avis HAS à comparer : le moteur intervient AVANT le
// dépôt, sur une claim et un mécanisme d'intervention, pour challenger le
// design d'étude avant que les données existent. Sortie brute et réelle de
// design_mode.run_design_mode(), non éditée à la main.

export const CONSEIL_DESIGN_CASES = [
  {
    slug: 'miroki-kokoro',
    title: 'MIROKI',
    subtitle: "Robot compagnon humanoïde en radiothérapie pédiatrique — étude KOKORO, SIRIC Montpellier Cancer / ICM Montpellier",
    status: { label: 'PRÉ-DOSSIER · AUCUN AVIS CNEDIMTS DÉPOSÉ', tone: 'blue' },
    hook: "« Une observation n'est pas une preuve. » — avant même le premier patient inclus dans KOKORO, qu'est-ce que le moteur challengerait sur le design de l'étude ?",
    claimText: "Miroki réduit l'anxiété des enfants pendant les séances de radiothérapie pédiatrique",
    intervention: 'Robot compagnon humanoïde Miroki en salle de radiothérapie',
    mediators: ['présence rassurante', 'réduction du stress anticipatoire', 'coopération accrue à la procédure'],
    endpointFamilies: [
      {
        name: 'HARD_CLINICAL', weight: 'PRIMARY', independence: 0.95,
        endpoints: [
          "score d'anxiété m-YPAS (hétéro-évaluation, jeune enfant, ≥3 ans)",
          "score d'anxiété CAM-S (auto-évaluation, enfant 4-10 ans, mesures répétées)",
          'score STAI-C (auto-évaluation, enfant ≥8-9 ans)',
        ],
      },
      {
        name: 'UTILIZATION', weight: 'PRIMARY', independence: 0.90,
        endpoints: ['taux de recours à la sédation/anesthésie générale par séance'],
      },
      {
        name: 'BIOMARKER', weight: 'SECONDARY', independence: 0.80,
        endpoints: ["score STAI-Y état (anxiété du parent/accompagnant)"],
      },
    ],
    prohibited: ['device interaction count', 'robot engagement duration', 'device-reported affect score'],
    designSpace: [
      { name: 'Individual RCT with independent endpoint adjudication', strength: 0.95, feasibility: 0.60, acceptability: 0.95, biases: ['selection bias (mitigated by randomization)', 'sham control recommended for subjective endpoints'] },
      { name: 'Pragmatic RCT with administrative outcome ascertainment', strength: 0.85, feasibility: 0.75, acceptability: 0.85, biases: ['performance bias (open-label)', 'outcome ascertainment via routine data'] },
      { name: 'Registry-based RCT with embedded randomization', strength: 0.82, feasibility: 0.80, acceptability: 0.82, biases: ['registry data quality', 'incomplete capture'] },
      { name: 'Cluster RCT (randomization at site level)', strength: 0.80, feasibility: 0.65, acceptability: 0.80, biases: ['contamination risk', 'cluster-level confounding'] },
      { name: 'Stepped-wedge cluster RCT (sequential rollout)', strength: 0.78, feasibility: 0.70, acceptability: 0.75, biases: ['temporal confounding', 'learning effect'] },
      { name: 'Controlled interrupted time series', strength: 0.55, feasibility: 0.85, acceptability: 0.55, biases: ['history bias', 'maturation', 'regression to mean'] },
      { name: 'Target trial emulation from observational data', strength: 0.50, feasibility: 0.90, acceptability: 0.45, biases: ['unmeasured confounding', 'immortal time bias', 'selection bias'] },
      { name: 'Single-arm study with external control cohort', strength: 0.35, feasibility: 0.95, acceptability: 0.30, biases: ['unmeasured confounding', 'selection bias', 'temporal bias'] },
    ],
    recommended: 'Individual RCT with independent endpoint adjudication',
    conditions: [
      "Randomisation nécessaire (comparateur : accompagnement standard sans robot)",
      "Contrôle sham/comparateur recommandé pour des critères subjectifs (m-YPAS, CAM-S, STAI-C)",
      "Aucune adjudication indépendante requise pour ces critères comportementaux/auto-rapportés",
    ],
    caveat: "m-YPAS est validée pour l'anxiété PRÉOPÉRATOIRE — un moment unique (induction anesthésique). Son usage en mesures répétées sur plusieurs séances de radiothérapie, comme le prévoit KOKORO, est une extrapolation hors du contexte de validation d'origine : à justifier explicitement dans le protocole, pas à supposer équivalente sans discussion.",
    bilan: "Premier cas de la série construit en mode conseil, pas en mode review : le moteur n'a comparé aucune sortie à un avis HAS réel, puisqu'aucun n'existe encore pour ce dispositif. Il a généré l'espace des designs possibles à partir de la seule claim et du seul mécanisme d'intervention — recommandation la plus forte : RCT individuel avec adjudication indépendante des critères, sur des échelles d'anxiété validées plutôt que sur des métriques d'engagement avec le robot lui-même.",
  },
]
