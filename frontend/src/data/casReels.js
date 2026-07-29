// ── Données des 4 analyses "Cas réel" (série LinkedIn CNEDiMTS) ──────────────
// Deux formats de contenu :
//  - "grid"  : carte mécanisme-par-mécanisme compacte (DIZG DBM, WALRUS)
//  - "deck"  : deck complet en 8 sections (INFINITY, POPPINS)

export const CAS_REELS = [
  {
    slug: 'dizg-dbm',
    format: 'grid',
    n: '1/N',
    title: 'DIZG DBM',
    subtitle: 'Allogreffe osseuse déminéralisée — chirurgie orthopédique, oncologie, neurochirurgie',
    dossier: 'Dossier 7943 · Avis du 3 mars 2026',
    verdict: { label: 'SA Suffisant · ASA V', tone: 'green' },
    hook: "Sur les 3 mécanismes couverts par le moteur : 1 confirmé mot pour mot, 1 manqué, 1 partiellement confirmé — jamais assez seul pour faire bouger le verdict global.",
    volume: '≈ 39 000 interventions/an en France utilisent ce type d\'allogreffe',
    mechanisms: [
      {
        code: 'MF_A', label: 'Identification causale', status: 'miss',
        moteur: "Structure causale directe — rien détecté sur ce point (le monocentrisme est repris plus bas, côté MF_D/CAS)",
        has: '« caractère monocentrique »',
      },
      {
        code: 'MF_B', label: "Mesure de l'effet", status: 'hit',
        moteur: 'ADJUDICATION_RISK — absence d\'évaluation en aveugle',
        has: '« absence d\'information sur le caractère aveugle ou ouvert de l\'étude (au moins pour le patient) »',
      },
      {
        code: 'MF_D', label: "Pertinence de l'évidence", status: 'partial',
        moteur: 'CAS_CONTEXT confirmé — étude jugée monocentrique. Risque d\'alignement population généré en interne, verdict global reste « acceptable » (0,9)',
        has: '« caractère monocentrique » · « Les données cliniques disponibles ne permettent pas la comparaison de DIZG DBM avec les autres allogreffes […] »',
      },
    ],
    outOfScope: "MF_C (puissance statistique) et MF_E (fiabilité du corpus) sont hors périmètre du moteur par construction — volontairement absents de cette grille.",
    outcome: "Le dossier a finalement été accepté par la HAS (Service Attendu Suffisant, Amélioration niveau V) : ce n'était pas un motif de rejet, seulement des limites méthodologiques parmi d'autres relevées par la commission.",
    downloadUrl: null,
    viewUrl: '/cas-reels/dizg-dbm.html',
  },
  {
    slug: 'walrus',
    format: 'grid',
    n: '2/N',
    title: 'WALRUS',
    subtitle: 'Cathéter-guide à ballonnet (thrombectomie) — AVC ischémiques à la phase aiguë',
    dossier: 'Dossier 7182 · Avis du 23 avril 2024',
    verdict: { label: 'SA Insuffisant', tone: 'red' },
    hook: "Le moteur classe la structure causale circulaire — les études soumises ne permettent pas d'identifier proprement l'effet du dispositif. Tendance de risque HIGH, cohérente avec le SA Insuffisant réel de la HAS.",
    volume: 'Cathéter-guide à ballonnet utilisé lors de la prise en charge des AVC ischémiques à la phase aiguë',
    mechanisms: [
      {
        code: 'MF_A', label: 'Identification causale', status: 'hit',
        moteur: 'Structure causale CIRCULAIRE — effet non identifiable',
        has: '« Huit des quinze études retenues sont des études rétrospectives et aucune n\'était contrôlée randomisée. »',
      },
      {
        code: 'MF_B', label: "Mesure de l'effet", status: 'miss',
        moteur: 'SURROGATE_RISK détecté',
        has: 'aucune critique isolée et vérifiable sur ce point précis dans le texte de l\'avis',
      },
      {
        code: 'MF_D', label: "Pertinence de l'évidence", status: 'hit',
        moteur: 'CAS_CONTEXT confirmé (étude monocentrique) + CAS_CE_MARKING confirmé (usage hors périmètre du marquage CE)',
        has: '« étude monocentrique à collecte rétrospective des données avec des critères de jugement non hiérarchisés » + « […] l\'utilisation du cathéter dans l\'artère vertébrale ne correspond pas à l\'indication du marquage CE. »',
      },
    ],
    outOfScope: "MF_C (puissance statistique) et MF_E (fiabilité du corpus) sont hors périmètre du moteur par construction — volontairement absents de cette grille.",
    outcome: "Un cas plus « d'école » : ici c'est la structure causale elle-même qui est en cause — pas juste un biais isolé parmi d'autres. La tendance de risque du moteur ne repose jamais sur un seul flag isolé : elle regarde d'abord si la structure elle-même tient debout.",
    downloadUrl: null,
    viewUrl: '/cas-reels/walrus.html',
  },
  {
    slug: 'infinity',
    format: 'deck',
    n: '4/N',
    title: 'INFINITY',
    subtitle: 'Prothèse totale de cheville — la même trajectoire réglementaire, à cinq ans d\'écart',
    dossier: 'TORNIER SAS (2020) → STRYKER FRANCE (2025) · Fabricant Wright Medical Technology (USA) · LPPR',
    verdict: { label: 'AVIS FAVORABLE ×2 (2020 & 2025)', tone: 'green' },
    hook: "« On a rejoué les deux dossiers, à cinq ans d'écart, sans jamais leur donner la conclusion de la HAS. »",
    sections: [
      {
        tag: '01 — Contexte', title: 'Un dispositif, deux dossiers, cinq ans d\'écart',
        body: "En 2020, la CNEDiMTS inscrit INFINITY pour la première fois — Service Attendu Suffisant, sous condition de transmettre au renouvellement les résultats d'une étude de suivi en conditions réelles françaises. En 2025, le registre national AFCP fournit ces données. Le moteur ne reçoit que les faits de protocole — jamais la conclusion, ni le fait qu'il s'agisse d'un renouvellement. Il n'a aucune notion de « renouvellement » et a rejoué les deux dossiers sans la moindre modification de code.",
      },
      {
        tag: '02 — Le dispositif', title: 'Une prothèse de cheville, deux comparateurs revendiqués',
        body: "Indication identique entre les deux dossiers, mais comparateur revendiqué différent : l'arthrodèse de cheville en 2020, les autres prothèses totales de cheville déjà prises en charge en 2025.",
      },
      {
        tag: '03 — Les études', title: 'Deux registres, cinq ans d\'écart',
        table: [
          ['', '2020 · Registre national UK', '2025 · Registre national AFCP (France)'],
          ['Design', 'Cohorte de registre, non randomisée', 'Cohorte de registre, non randomisée'],
          ['N', '1 468 implantations INFINITY', '467 sélectionnées (658 posées, 169 suivies à 2 ans)'],
          ['Critère principal', 'Taux de révision cumulé à 4 ans', 'Taux de survie sans reprise à 2 ans (Kaplan-Meier)'],
          ['Comparateur étudié', 'Ensemble des prothèses du registre (descriptif)', 'Ensemble des prothèses du registre français (descriptif)'],
        ],
      },
      {
        tag: '04 — Signaux', title: 'Un signal se referme, trois restent identiques',
        signals2020: [
          { level: 'MEDIUM', label: 'Comparator', body: 'Comparateur étudié (autres prothèses du registre) ≠ comparateur revendiqué (arthrodèse).' },
          { level: 'LOW', label: 'Design', body: 'Centricité de l\'étude non renseignée.' },
          { level: 'MEDIUM', label: 'Design', body: 'Étude comparative non randomisée — risque de biais de sélection résiduel.' },
          { level: 'MEDIUM', label: 'Endpoint', body: 'Critère principal objectif sans adjudication indépendante documentée.' },
        ],
        signals2025: [
          { level: 'FERMÉ', label: 'Comparator', body: 'Le comparateur revendiqué en 2025 correspond désormais au comparateur étudié.' },
          { level: 'LOW', label: 'Design', body: 'Centricité non renseignée — identique à 2020.' },
          { level: 'MEDIUM', label: 'Design', body: 'Non randomisée — identique à 2020.' },
          { level: 'MEDIUM', label: 'Endpoint', body: 'Pas d\'adjudication indépendante — identique à 2020.' },
        ],
      },
      {
        tag: '05 — Alignement HAS', title: 'Un signal confirmé mot pour mot, un autre hors périmètre',
        alignment: [
          { has: '« Aucune étude ne compare la prothèse INFINITY à l\'arthrodèse, comparateur revendiqué par le demandeur. » (2020)', moteur: 'Gap comparator — MEDIUM. Confirmé mot pour mot.' },
          { has: '« La principale limite de ce registre est la non-exhaustivité de la déclaration des reprises par les chirurgiens. » (2025)', moteur: 'Hors périmètre du moteur par construction — il évalue le design planifié, pas le taux de perte de suivi réellement obtenu.' },
        ],
      },
      {
        tag: '06 — Réparation', title: 'Ce que proposait le moteur en 2020',
        repairs: [
          '[MEDIUM] Comparator — Aligner la revendication sur le comparateur réellement étudié, ou établir une comparaison indirecte (network meta-analysis).',
          '[MEDIUM] Endpoint — Ajouter un comité d\'adjudication indépendant (CEC), charte pré-spécifiée, ≥3 experts en aveugle.',
          '[LOW] Design — Documenter la centricité (donnée absente, pas une faiblesse confirmée).',
          '[MEDIUM] Design — Randomiser ou ajuster statistiquement les facteurs de confusion (score de propension, IPTW).',
        ],
        note: "Cinq ans plus tard, le dossier 2025 aura réglé l'action 01 (comparateur aligné). Les actions 02, 03 et 04 réapparaissent à l'identique dans le renouvellement.",
      },
      {
        tag: 'Bilan', title: 'Une trajectoire suivie sans jamais avoir la notion de trajectoire',
        body: "Premier cas de la série à suivre le même dispositif à deux moments réglementaires distincts, à cinq ans d'écart : le moteur n'a aucune notion de renouvellement, ni de dossier précédent, ni de condition posée en 2020 — et pourtant les deux analyses, strictement indépendantes, racontent la même histoire que la vraie trajectoire réglementaire.",
      },
    ],
    downloadUrl: '/cas-reels/infinity.pdf',
    viewUrl: null,
  },
  {
    slug: 'poppins',
    format: 'deck',
    n: '5/N',
    title: 'POPPINS',
    subtitle: 'Thérapie numérique de rééducation par entraînement cognitif et rythmique — dyslexie de l\'enfant',
    dossier: 'BMOTION TECHNOLOGIES (France) · PECAN',
    verdict: { label: 'AVIS CNEDIMTS 23.06.2026 · AVIS FAVORABLE', tone: 'green' },
    hook: "« On a rejoué ce dossier réel, fait par fait — sans jamais lui donner la conclusion de la HAS. »",
    sections: [
      {
        tag: '01 — Contexte', title: 'Un format d\'avis inédit dans la série : le PECAN',
        body: "Jusqu'ici, chaque dossier de la série était une inscription LPPR classique. Le PECAN (Prise En Charge Anticipée) est différent — réservé aux dispositifs médicaux numériques, il rembourse par anticipation sur la base d'une présomption d'innovation, avant que la preuve soit complète. POPPINS CLINICAL doit encore fournir des données complémentaires sous 6 mois. Le moteur n'a aucune notion de voie réglementaire (LPPR, PECAN, LATM) — un angle mort qui ne l'a pas empêché de tourner sans accroc sur ce format inédit.",
      },
      {
        tag: '02 — Le dispositif', title: 'Un jeu vidéo thérapeutique contre la dyslexie',
        body: "Programme numérique de rééducation utilisable en autonomie par l'enfant à domicile, basé sur des jeux de langage écrit et des jeux musicaux (entraînement rythmique multimodal), sessions de 20 minutes.",
        quotes: [
          { text: 'Rééducation du trouble spécifique des apprentissages avec déficit de lecture (dyslexie) par un entraînement cognitif et rythmique chez les patients âgés de 7 à 11 ans […] en complément d\'une rééducation orthophonique bimensuelle.', source: 'Indication revendiquée, dossier CNEDiMTS' },
          { text: 'Étude POPPINS-02, contrôlée, randomisée, bicentrique (Paris, Poitiers), non-infériorité de POPPINS + 2 séances mensuelles d\'orthophonie vs. orthophonie hebdomadaire seule.', source: 'Étude pivot, dossier CNEDiMTS' },
        ],
      },
      {
        tag: '03 — L\'étude', title: 'Étude POPPINS-02',
        table: [
          ['Design', 'Contrôlée, randomisée, non-infériorité, évaluateur indépendant en aveugle'],
          ['Centres', 'Bicentrique (Paris, Poitiers), recrutement national'],
          ['N', '306 patients randomisés (154 / 152)'],
          ['Critère principal', 'Précision de lecture EVAL2M, inclusion vs 12 semaines'],
          ['Comparateur', '1 séance hebdomadaire d\'orthophonie seule'],
        ],
      },
      {
        tag: '04 — Signaux', title: 'Deux signaux, dérivés des seuls faits de protocole',
        flatSignals: [
          { level: 'HIGH', label: 'Déséquilibre de groupes à l\'inclusion', body: 'Les deux bras diffèrent à l\'inclusion sur le nombre de mots correctement lus (82,29 vs 88,53) et la vitesse de lecture (93,53 vs 97,93), en défaveur du bras expérimental.' },
          { level: 'MODERATE', label: 'CAS_POPULATION — sous-groupe protocolaire restrictif', body: 'Le protocole exclut des enfants pourtant couverts par la revendication (TSA, déficit intellectuel documenté, suivi orthophonique hebdomadaire >2 ans).' },
        ],
      },
      {
        tag: '05 — Alignement HAS', title: 'Un signal confirmé mot pour mot, un autre qui rate sa cible',
        alignment: [
          { has: '« Déséquilibre entre les groupes en ce qui concerne le nombre de mots correctement lus en 2 minutes et la vitesse de lecture. »', moteur: 'Gap design — HIGH. Confirmé mot pour mot.' },
          { has: '« Il paraît une sous-représentation des catégories socio-professionnelles basses. »', moteur: 'Hors périmètre du moteur par construction — donnée démographique jamais reçue ni analysée par le moteur.' },
        ],
      },
      {
        tag: '06 — Réparation', title: 'Ce que propose réellement le moteur',
        repairs: [
          '[LOW] Restreindre la revendication à la population réellement étudiée, ou fournir une analyse de sous-groupe pré-spécifiée.',
          '[MEDIUM] Ajuster statistiquement sur les caractéristiques déséquilibrées (ANCOVA, régression multivariée, ou nouvelle randomisation stratifiée).',
          '[MEDIUM] Étendre le suivi à 24 mois pour confirmer la durabilité (registre post-commercialisation, extraction PMSI/SNDS).',
        ],
        note: "Le moteur ne propose rien sur la sous-représentation socio-professionnelle — cohérent avec le fait que ce mécanisme est hors de son périmètre.",
      },
      {
        tag: 'Bilan', title: 'Un moteur agnostique à la voie réglementaire',
        body: "Premier PECAN de la série : le moteur n'a aucune notion de voie réglementaire (LPPR/PECAN/LATM) et a tourné sur ce format inédit sans adaptation — un signal confirmé mot pour mot, un autre qui rate le bon mécanisme.",
      },
    ],
    downloadUrl: '/cas-reels/poppins.pdf',
    viewUrl: null,
  },
]
