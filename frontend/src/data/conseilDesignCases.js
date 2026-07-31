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
    principalEndpoint: "score d'anxiété m-YPAS (hétéro-évaluation, jeune enfant, ≥3 ans)",
    compatibleEndpoints: [
      "score d'anxiété CAM-S (auto-évaluation, enfant 4-10 ans, mesures répétées)",
      'score STAI-C (auto-évaluation, enfant ≥8-9 ans)',
    ],
    multiplicityNote: "S'ils sont conservés ensemble comme co-principaux, une hiérarchisation statistique pré-spécifiée est requise pour contrôler le risque alpha global — même garde-fou que celui que le mode review du moteur applique déjà aux dossiers déposés (cf. avis CNEDiMTS ENTERRA II 7254, ASA rétrogradée pour multiplicité de critères non hiérarchisés).",
    endpointFamilies: [
      { name: 'UTILIZATION', weight: 'PRIMARY', independence: 0.90, endpoints: ['taux de recours à la sédation/anesthésie générale par séance'] },
      { name: 'BIOMARKER', weight: 'SECONDARY', independence: 0.80, endpoints: ["score STAI-Y état (anxiété du parent/accompagnant)"] },
    ],
    prohibited: ['device interaction count', 'robot engagement duration', 'device-reported affect score'],
    // Sortie exacte de design_space.candidates (8/8), triée par score composite
    // (0.7×acceptabilité + 0.3×faisabilité) — chiffres et tradeoff_note non modifiés.
    designSpace: [
      { name: 'Individual RCT with independent endpoint adjudication', strength: 0.95, feasibility: 0.60, acceptability: 0.95, biases: ['selection bias (mitigated by randomization)', 'exposition non masquable (présence physique) — nécessite une évaluation en aveugle par évaluateur indépendant, pas un sham'], tradeoff: null },
      { name: 'Pragmatic RCT with administrative outcome ascertainment', strength: 0.80, feasibility: 0.75, acceptability: 0.80, biases: ['performance bias (open-label)', 'outcome ascertainment via routine data', 'perception bias (no blinding)'], tradeoff: 'gagne en faisabilité (+0.15), perd en acceptabilité HAS (-0.15)' },
      { name: 'Registry-based RCT with embedded randomization', strength: 0.77, feasibility: 0.80, acceptability: 0.77, biases: ['registry data quality', 'incomplete capture', 'perception bias (no blinding)'], tradeoff: 'gagne en faisabilité (+0.20), perd en acceptabilité HAS (-0.18)' },
      { name: 'Cluster RCT (randomization at site level)', strength: 0.75, feasibility: 0.65, acceptability: 0.75, biases: ['contamination risk', 'cluster-level confounding', 'perception bias (no blinding)'], tradeoff: 'gagne en faisabilité (+0.05), perd en acceptabilité HAS (-0.20)' },
      { name: 'Stepped-wedge cluster RCT (sequential rollout)', strength: 0.73, feasibility: 0.70, acceptability: 0.70, biases: ['temporal confounding', 'learning effect', 'perception bias (no blinding)'], tradeoff: 'gagne en faisabilité (+0.10), perd en acceptabilité HAS (-0.25)' },
      { name: 'Controlled interrupted time series', strength: 0.50, feasibility: 0.85, acceptability: 0.50, biases: ['history bias', 'maturation', 'regression to mean', 'perception bias (no blinding)'], tradeoff: 'gagne en faisabilité (+0.25), perd en acceptabilité HAS (-0.45)' },
      { name: 'Target trial emulation from observational data', strength: 0.45, feasibility: 0.90, acceptability: 0.40, biases: ['unmeasured confounding', 'immortal time bias', 'selection bias', 'perception bias (no blinding)'], tradeoff: 'gagne en faisabilité (+0.30), perd en acceptabilité HAS (-0.55)' },
      { name: 'Single-arm study with external control cohort', strength: 0.30, feasibility: 0.95, acceptability: 0.25, biases: ['unmeasured confounding', 'selection bias', 'temporal bias', 'perception bias (no blinding)'], tradeoff: 'gagne en faisabilité (+0.35), perd en acceptabilité HAS (-0.70)' },
    ],
    recommended: 'Individual RCT with independent endpoint adjudication',
    conditions: [
      "L'exposition au dispositif ne peut pas être masquée au participant (présence physique perceptible) — double aveugle classique NON FAISABLE. Recommandé à la place : évaluation en aveugle par un évaluateur indépendant (cotation vidéo différée, en insu de l'allocation).",
      "Randomisation nécessaire (comparateur : accompagnement standard sans robot)",
      "Aucune adjudication indépendante requise pour ces critères comportementaux/auto-rapportés",
    ],
    caveat: "m-YPAS est validée pour l'anxiété PRÉOPÉRATOIRE — un moment unique (induction anesthésique). Son usage en mesures répétées sur plusieurs séances de radiothérapie, comme le prévoit KOKORO, est une extrapolation hors du contexte de validation d'origine : à justifier explicitement dans le protocole, pas à supposer équivalente sans discussion.\n\nCe cas a servi à trouver et corriger, en direct, quatre vrais problèmes du moteur (29/07/2026) :\n1. La détection du besoin d'aveugle ratait les claims subjectives en français (bug de mots-clés bilingues, resté non synchronisé avec un correctif déjà fait ailleurs).\n2. Une fois corrigé, le moteur recommandait un sham/double-blind classique — infaisable pour une présence physique perceptible comme un robot. Corrigé pour recommander la vraie solution méthodologique : masquer l'ÉVALUATION du critère, pas l'exposition elle-même.\n3. Le libellé \"Design recommandé\" sonnait prescriptif ; les scores en décimales nues donnaient une fausse précision. Reformulé en \"design le plus défendable\" + catégories (Très élevée/Élevée/Modérée/Faible).\n4. Trois critères affichés à égalité en PRIMARY reproduisaient exactement le gap de multiplicité de critères que le mode review du même moteur sanctionne côté dossiers déposés (avis ENTERRA II 7254). Corrigé : un seul critère principal, les autres en alternatives validées avec la condition de hiérarchisation explicite.",
    bilan: "Premier cas de la série construit en mode conseil, pas en mode review : le moteur n'a comparé aucune sortie à un avis HAS réel, puisqu'aucun n'existe encore pour ce dispositif. Il a généré l'espace des 8 designs possibles à partir de la seule claim et du seul mécanisme d'intervention — le plus défendable : RCT individuel avec adjudication indépendante, sur un critère d'anxiété principal validé plutôt que sur une métrique d'engagement avec le robot lui-même.",
  },
]
