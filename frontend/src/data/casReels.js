// ── Données des 4 analyses "Cas réel" (série LinkedIn CNEDiMTS) ──────────────
// Toutes au format "deck" complet (contexte, dispositif, étude, signaux,
// alignement avec la HAS, réparation, bilan). MAIOREGEN a une section
// supplémentaire ("raisonnement", format flow) entre signaux et alignement.

export const CAS_REELS = [
  {
    slug: 'triple-action',
    format: 'deck',
    n: '2/N',
    title: 'TRIPLE ACTION',
    subtitle: 'Articulation de cheville modulaire pour orthèse du membre inférieur',
    dossier: "Demandeur : Alianza Techniques d'Orthopédie (France) · Fabricant : Becker Orthopedic (USA)",
    verdict: { label: 'AVIS CNEDIMTS 28.01.2025 · SA INSUFFISANT', tone: 'red' },
    hook: "« Deux études de 6 et 10 patients, jamais reliées à un vrai bénéfice clinique — le moteur détecte les mêmes faiblesses méthodologiques, sans connaître l'avis de la HAS. »",
    sections: [
      {
        tag: '01 — Contexte', title: 'Ce que la CNEDiMTS évalue',
        body: "Pour qu'un dispositif médical soit remboursé en France, la CNEDiMTS (HAS) statue sur son Service Attendu : la preuve clinique apportée justifie-t-elle la prise en charge ? Un avis « Insuffisant » n'est jamais arbitraire — mais les raisons précises se noient souvent dans une méthodologie dense. Notre règle du jeu : on ne donne au moteur que les faits de protocole — design, population, résultats bruts. Jamais les conclusions de la HAS elles-mêmes. Le moteur détecte les mêmes signaux.",
      },
      {
        tag: '02 — Le dispositif', title: 'Une articulation de cheville pour corriger la marche',
        body: "Une orthèse de cheville-pied à résistance de flexion réglable, destinée à compenser un déficit du contrôle de la marche.",
        quotes: [
          { text: "Compensation de déficits fonctionnels de la marche pour des flexions plantaires (équin) ou dorsales (talus) excessives ou limitées, non fixées […] rendant la marche inefficace et fatigante", source: 'Indication revendiquée, dossier CNEDiMTS' },
        ],
      },
      {
        tag: "03 — L'étude", title: 'Deux études biomécaniques, mêmes limites',
        table: [
          ['Design', 'Non comparative, monocentrique (USA), recueil prospectif'],
          ['N', '6 puis 10 patients adultes post-AVC'],
          ['Critère', 'Cinématique et cinétique articulaire à la marche'],
          ['Comparateur', "Aucun — alors qu'une catégorie d'orthèse comparable existe"],
          ['Calcul du N', 'Non fourni'],
        ],
      },
      {
        tag: '04 — Signaux', title: 'Deux signaux HIGH, une structure causale circulaire',
        flatSignals: [
          { level: 'HIGH', label: 'NO_COMPARATOR', body: "Un comparateur était explicitement faisable (une catégorie d'orthèse concurrente est nommée dans le dossier) mais aucun n'a été utilisé." },
          { level: 'HIGH', label: 'Le critère évalue le dispositif… pas le patient', body: 'Le moteur classe cette situation comme un risque de circularité : les données démontrent que le dispositif fonctionne mécaniquement, mais pas qu\'il apporte un bénéfice clinique.' },
          { level: 'MEDIUM', label: 'Mono-centrique (gap)', body: 'Étude conduite dans un seul centre — généralisabilité non établie.' },
        ],
      },
      {
        tag: '05 — Alignement HAS', title: 'Le moteur retrouve seul les points cités par la HAS',
        alignment: [
          { has: '« Critères de jugement biomécaniques et non cliniques. »', moteur: 'CIRCULARITY_RISK — HIGH. Le critère mesure le dispositif plutôt que le bénéfice patient.' },
          { has: "« […] absence de données permettant d'apprécier l'intérêt […] »", moteur: 'CRITICAL. Risque global, non réparable.' },
        ],
        note: 'Alignement confirmé.',
      },
      {
        tag: '06 — Réparation', title: 'Comment ce dossier pourrait devenir recevable',
        repairs: [
          "Ajouter un comparateur — une orthèse de la catégorie déjà citée comme concurrente.",
          "Chutes documentées sur 12 mois et recours aux urgences liés (PMSI/SNDS) — critère clinique, pas biomécanique.",
          "Échelle de mobilité fonctionnelle standardisée (FAC, Timed Up and Go) par évaluateur indépendant.",
          "Calcul du nombre de sujets nécessaires, multicentrique.",
        ],
      },
      {
        tag: 'Bilan', title: "Un dispositif peut fonctionner parfaitement… sans démontrer qu'il améliore la vie du patient",
        body: "Cas 2/N d'une série sur des dossiers CNEDiMTS réels, rejoués fait par fait — sans jamais donner au moteur la conclusion de la HAS elle-même.",
      },
    ],
    downloadUrl: '/cas-reels/triple-action.pdf',
    viewUrl: null,
  },
  {
    slug: 'maioregen-prime',
    format: 'deck',
    n: '1/N',
    title: 'MAIOREGEN PRIME',
    subtitle: 'Substitut chondral et ostéochondral — lésions du genou',
    dossier: 'Demandeur / fabricant : Fin-Ceramica (Italie)',
    verdict: { label: 'AVIS CNEDIMTS 06.05.2025 · SA INSUFFISANT', tone: 'red' },
    hook: "« Un essai randomisé multicentrique en aveugle, sur 15 centres — et pourtant rejeté. Un essai robuste en apparence, mais dont la démonstration repose sur une analyse en sous-groupe insuffisamment documentée. »",
    sections: [
      {
        tag: '01 — Contexte', title: 'Ce que la CNEDiMTS évalue',
        body: "Pour qu'un dispositif médical soit remboursé en France, la CNEDiMTS (HAS) statue sur son Service Attendu : la preuve clinique apportée justifie-t-elle la prise en charge ? Un avis « Insuffisant » n'est jamais arbitraire — même quand l'étude sous-jacente est, sur le papier, plutôt solide. Notre règle du jeu : on ne donne au moteur que les faits de protocole — design, population, résultats bruts. Jamais les conclusions de la HAS elles-mêmes. Si le moteur retrouve seul les mêmes signaux, l'alignement est réel — pas circulaire.",
      },
      {
        tag: '02 — Le dispositif', title: 'Une matrice pour régénérer le cartilage du genou',
        body: 'Une matrice tridimensionnelle acellulaire, implantée pour combler une lésion ostéochondrale profonde du genou.',
        quotes: [
          { text: 'Lésions ostéochondrales profondes, uniques ou multiples, avec une atteinte sévère du tissu sous-chondral (Outerbridge Grade IV)', source: 'Indication revendiquée, dossier CNEDiMTS' },
        ],
      },
      {
        tag: "03 — L'étude", title: 'Étude Kon et al., 2018',
        table: [
          ['Design', 'RCT multicentrique, simple aveugle (15 centres, 9 pays)'],
          ['N', '118 patients traités, 100 analysés à 2 ans (51/49)'],
          ['Critère principal', 'Score IKDC subjectif à 24 mois'],
          ['Comparateur', 'Stimulation de la moelle osseuse (microfracture)'],
          ['Résultat global', 'Différence non significative entre les 2 groupes'],
          ['Sous-groupe', 'Lésions profondes (indication revendiquée) : +12,4 pts, significatif'],
        ],
      },
      {
        tag: '04 — Signaux', title: 'Trois signaux, à partir des seuls faits de protocole',
        flatSignals: [
          { level: 'HIGH', label: 'Significativité limitée au sous-groupe (gap)', body: "Le critère principal n'est pas significatif sur la population entière, mais l'est dans le sous-groupe correspondant exactement à l'indication — sans confirmation que cette analyse était prévue au protocole." },
          { level: 'MEDIUM', label: 'ANALYSIS_SET (gap)', body: "L'analyse porte sur les 100 patients traités et évalués, pas sur les 118 recrutés — une analyse par protocole, pas en intention de traiter." },
          { level: 'MEDIUM', label: 'Aveugle partiel (affiné)', body: "Design simple aveugle, patient aveugle à son groupe — atténue le risque d'effet d'attente, sans l'éliminer." },
        ],
      },
      {
        tag: '05 — Raisonnement', title: "Pourquoi un sous-groupe positif ne suffit pas",
        flow: ['Critère principal', 'Non significatif', "Recherche d'un effet dans un sous-groupe", 'Sous-groupe = positif', 'Pré-spécification ?', 'Incertitude méthodologique'],
        body: "« Pré-spécifier » une analyse, c'est l'avoir prévue avant de voir les résultats — dans le protocole ou le plan d'analyse statistique. Sans cette garantie écrite à l'avance, un résultat positif isolé dans un sous-groupe peut aussi bien être une découverte fortuite qu'un effet réel : c'est cette incertitude, et non la significativité elle-même, que pointe le signal HIGH.",
      },
      {
        tag: '06 — Alignement HAS', title: "À partir des seules caractéristiques de l'étude, le moteur identifie les mêmes points que ceux discutés par la HAS",
        alignment: [
          { has: "« […] non précisé si cette analyse en sous-groupe était prévue au protocole. »", moteur: 'Sous-groupe seul significatif — HIGH, pré-spécification non confirmée.' },
          { has: '« […] deux groupes […] pas complètement homogènes. »', moteur: "Gap déséquilibre de groupes à l'inclusion." },
        ],
        note: 'Alignement confirmé, point par point.',
      },
      {
        tag: '07 — Réparation', title: 'Comment ce dossier pourrait devenir recevable',
        repairs: [
          "Documenter la pré-spécification de l'analyse en sous-groupe dans le protocole ou le plan d'analyse statistique.",
          "À défaut, un test d'interaction pré-spécifié avec correction de multiplicité.",
          "Ou un essai confirmatoire dédié, restreint au sous-groupe des lésions profondes.",
          "Pré-spécifier l'intention de traiter comme analyse principale, l'analyse par protocole en sensibilité.",
        ],
        note: "L'objectif n'est pas de « rendre significatif » un résultat, mais de démontrer que l'hypothèse testée était définie avant l'analyse. Le problème n'est pas la p-value en soi, mais le risque d'interprétation a posteriori.",
      },
      {
        tag: 'Bilan', title: "Un essai robuste n'est pas toujours une démonstration robuste",
        body: "Cas 1/N d'une série sur des dossiers CNEDiMTS réels, rejoués fait par fait — sans jamais donner au moteur la conclusion de la HAS elle-même.",
      },
    ],
    downloadUrl: '/cas-reels/maioregen-prime.pdf',
    viewUrl: null,
  },
  {
    slug: 'poppins',
    format: 'deck',
    n: '5/N',
    title: 'POPPINS',
    subtitle: "Thérapie numérique de rééducation par entraînement cognitif et rythmique — dyslexie de l'enfant",
    dossier: 'BMOTION TECHNOLOGIES (France) · PECAN',
    verdict: { label: 'AVIS CNEDIMTS 23.06.2026 · AVIS FAVORABLE', tone: 'green' },
    hook: "« On a rejoué ce dossier réel, fait par fait — sans jamais lui donner la conclusion de la HAS. »",
    sections: [
      {
        tag: '01 — Contexte', title: "Un format d'avis inédit dans la série : le PECAN",
        body: "Jusqu'ici, chaque dossier de la série était une inscription LPPR classique. Le PECAN (Prise En Charge Anticipée) est différent — réservé aux dispositifs médicaux numériques, il rembourse par anticipation sur la base d'une présomption d'innovation, avant que la preuve soit complète. POPPINS CLINICAL doit encore fournir des données complémentaires sous 6 mois. Le moteur n'a aucune notion de voie réglementaire (LPPR, PECAN, LATM) — un angle mort qui ne l'a pas empêché de tourner sans accroc sur ce format inédit.",
      },
      {
        tag: '02 — Le dispositif', title: 'Un jeu vidéo thérapeutique contre la dyslexie',
        body: "Programme numérique de rééducation utilisable en autonomie par l'enfant à domicile, basé sur des jeux de langage écrit et des jeux musicaux (entraînement rythmique multimodal), sessions de 20 minutes.",
        quotes: [
          { text: "Rééducation du trouble spécifique des apprentissages avec déficit de lecture (dyslexie) par un entraînement cognitif et rythmique chez les patients âgés de 7 à 11 ans […] en complément d'une rééducation orthophonique bimensuelle.", source: 'Indication revendiquée, dossier CNEDiMTS' },
          { text: 'Étude POPPINS-02, contrôlée, randomisée, bicentrique (Paris, Poitiers), non-infériorité de POPPINS + 2 séances mensuelles d\'orthophonie vs. orthophonie hebdomadaire seule.', source: 'Étude pivot, dossier CNEDiMTS' },
        ],
      },
      {
        tag: "03 — L'étude", title: 'Étude POPPINS-02',
        table: [
          ['Design', 'Contrôlée, randomisée, non-infériorité, évaluateur indépendant en aveugle'],
          ['Centres', 'Bicentrique (Paris, Poitiers), recrutement national'],
          ['N', '306 patients randomisés (154 / 152)'],
          ['Critère principal', 'Précision de lecture EVAL2M, inclusion vs 12 semaines'],
          ['Comparateur', "1 séance hebdomadaire d'orthophonie seule"],
        ],
      },
      {
        tag: '04 — Signaux', title: 'Deux signaux, dérivés des seuls faits de protocole',
        flatSignals: [
          { level: 'HIGH', label: "Déséquilibre de groupes à l'inclusion", body: "Les deux bras diffèrent à l'inclusion sur le nombre de mots correctement lus (82,29 vs 88,53) et la vitesse de lecture (93,53 vs 97,93), en défaveur du bras expérimental." },
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
          "Restreindre la revendication à la population réellement étudiée, ou fournir une analyse de sous-groupe pré-spécifiée.",
          "Ajuster statistiquement sur les caractéristiques déséquilibrées (ANCOVA, régression multivariée, ou nouvelle randomisation stratifiée).",
          "Étendre le suivi à 24 mois pour confirmer la durabilité (registre post-commercialisation, extraction PMSI/SNDS).",
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
  {
    slug: 'infinity',
    format: 'deck',
    n: '4/N',
    title: 'INFINITY',
    subtitle: "Prothèse totale de cheville — la même trajectoire réglementaire, à cinq ans d'écart",
    dossier: 'TORNIER SAS (2020) → STRYKER FRANCE (2025) · Fabricant Wright Medical Technology (USA) · LPPR',
    verdict: { label: 'AVIS FAVORABLE ×2 (2020 & 2025)', tone: 'green' },
    hook: "« On a rejoué les deux dossiers, à cinq ans d'écart, sans jamais leur donner la conclusion de la HAS. »",
    sections: [
      {
        tag: '01 — Contexte', title: "Un dispositif, deux dossiers, cinq ans d'écart",
        body: "En 2020, la CNEDiMTS inscrit INFINITY pour la première fois — Service Attendu Suffisant, sous condition de transmettre au renouvellement les résultats d'une étude de suivi en conditions réelles françaises. En 2025, le registre national AFCP fournit ces données. Le moteur ne reçoit que les faits de protocole — jamais la conclusion, ni le fait qu'il s'agisse d'un renouvellement. Il n'a aucune notion de « renouvellement » et a rejoué les deux dossiers sans la moindre modification de code.",
      },
      {
        tag: '02 — Le dispositif', title: 'Une prothèse de cheville, deux comparateurs revendiqués',
        body: "Indication identique entre les deux dossiers, mais comparateur revendiqué différent : l'arthrodèse de cheville en 2020, les autres prothèses totales de cheville déjà prises en charge en 2025.",
      },
      {
        tag: '03 — Les études', title: "Deux registres, cinq ans d'écart",
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
          { level: 'LOW', label: 'Design', body: "Centricité de l'étude non renseignée." },
          { level: 'MEDIUM', label: 'Design', body: 'Étude comparative non randomisée — risque de biais de sélection résiduel.' },
          { level: 'MEDIUM', label: 'Endpoint', body: 'Critère principal objectif sans adjudication indépendante documentée.' },
        ],
        signals2025: [
          { level: 'FERMÉ', label: 'Comparator', body: 'Le comparateur revendiqué en 2025 correspond désormais au comparateur étudié.' },
          { level: 'LOW', label: 'Design', body: 'Centricité non renseignée — identique à 2020.' },
          { level: 'MEDIUM', label: 'Design', body: 'Non randomisée — identique à 2020.' },
          { level: 'MEDIUM', label: 'Endpoint', body: "Pas d'adjudication indépendante — identique à 2020." },
        ],
      },
      {
        tag: '05 — Alignement HAS', title: 'Un signal confirmé mot pour mot, un autre hors périmètre',
        alignment: [
          { has: "« Aucune étude ne compare la prothèse INFINITY à l'arthrodèse, comparateur revendiqué par le demandeur. » (2020)", moteur: 'Gap comparator — MEDIUM. Confirmé mot pour mot.' },
          { has: '« La principale limite de ce registre est la non-exhaustivité de la déclaration des reprises par les chirurgiens. » (2025)', moteur: "Hors périmètre du moteur par construction — il évalue le design planifié, pas le taux de perte de suivi réellement obtenu." },
        ],
      },
      {
        tag: '06 — Réparation', title: 'Ce que proposait le moteur en 2020',
        repairs: [
          "[MEDIUM] Comparator — Aligner la revendication sur le comparateur réellement étudié, ou établir une comparaison indirecte (network meta-analysis).",
          "[MEDIUM] Endpoint — Ajouter un comité d'adjudication indépendant (CEC), charte pré-spécifiée, ≥3 experts en aveugle.",
          "[LOW] Design — Documenter la centricité (donnée absente, pas une faiblesse confirmée).",
          "[MEDIUM] Design — Randomiser ou ajuster statistiquement les facteurs de confusion (score de propension, IPTW).",
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
]
