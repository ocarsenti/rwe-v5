# Série LinkedIn — Cas réels (moteur vs avis HAS)

Nouvelle série, distincte de la série "5 posts" (analyse agrégée sur 100 avis).
Ici : un dossier CNEDiMTS réel par post, on montre ce que le moteur sort à partir de la seule
revendication clinique (sans avoir vu l'avis), puis on compare au texte réel de l'avis HAS.
Toutes les citations sont vérifiées mot pour mot dans `data/raw_opinions_v2/` et `data/posts/*.json`
(pipeline `has_vs_moteur.py`).

## Règles éditoriales (fixes, à appliquer à chaque post de la série)

1. **Montrer les deux cas de figure** au fil de la série — les fois où le moteur retrouve
   exactement ce que dit la HAS, et les fois où il rate ou se trompe de mécanisme. Ne pas ne
   montrer que les succès.
2. **Uniquement des primo-inscriptions** ("Demande d'inscription", pas "Demande de
   renouvellement d'inscription") — une primo-inscription est le cas d'usage produit réel
   (avant soumission), contrairement à un renouvellement qui a un historique d'inscription
   différent. Sur les 34 dossiers déjà passés dans `has_vs_moteur.py`, 31 sont des
   primo-inscriptions et exploitables ; 3 sont des renouvellements et à exclure (MENTOR 7137,
   CHORUS 7543, SONNET 2 7554 — dossiers pilotes, motif vérifié dans
   `data/sampling_v2/sample_100.json`).
3. **Template fixe, toujours le même** (voir `linkedin_case1_7943_share.html` comme référence) :
   - Bandeau dispositif : nom, type, code dossier + date d'avis, badge décision HAS, description
     factuelle en 2 lignes (paraphrase neutre de l'indication retenue, pas la revendication
     légale brute).
   - Grille à 3 lignes fixes MF_A (identification causale) / MF_B (mesure de l'effet) / MF_D
     (pertinence de l'évidence) — jamais MF_C (puissance statistique) ni MF_E (fiabilité du
     corpus), qui sont hors périmètre du moteur par construction. Chaque ligne : ce que sort le
     moteur, citation vérifiée de l'avis HAS, verdict (Confirmé / Manqué / Partiel).
   - Texte à copier (caption LinkedIn) séparé de l'image (le bandeau + la grille, à capturer en
     screenshot) — LinkedIn ne rend pas de HTML/tableaux dans le corps du post.

## 31 dossiers primo-inscription disponibles (code — dispositif)

7182 WALRUS · 7254 ENTERRA II · 7276 ACCESS SOCKET TRANS FEMORAL · 7282 MAIOREGEN PRIME ·
7425 SCEWO BRO · 7457 DERIVO 2 · 7492 FORA 6 DUO/FORA 6 · 7534 IMPLANTS OSSEUX 3DI PEEK ·
7594 FRED X · 7620 TRIPLE ACTION · 7714 URGOFIT · 7717 CONTROL-IQ · 7722 NEOVIS TOTAL MULTI ·
7776 INSPIRE IV UAS · 7781 SOMNIO · 7793 DURAWALK · 7851 AVEIR · 7873 SAPIEN 3/ALTERRA ·
7880 SPACEOAR VUE · 7920 MON BANDÔ · 7922 PARS X3 · 7936 E-PILOT P15 · 7943 DIZG DBM ·
7947 FLEX-SYMES · 7969 ASSERT-IQ EL+ · 7990 NUCLEUS NEXA CI1022 · 8011 ISOLIS · 8122 HYLO DUAL
PLUS · 8123 BROADWAY 8 · 8145 VIS-RX · 8197 SURMATELAS RGO SOINS

Exclus (renouvellement, ne pas utiliser) : 7137 MENTOR, 7543 CHORUS, 7554 SONNET 2.

---

## CAS 1/N — DIZG DBM (dossier 7943, primo-inscription, avis du 3 mars 2026)

**[IMAGE : bandeau dispositif + grille à 3 lignes MF_A/MF_B/MF_D — capture de
`linkedin_case1_7943_share.html`]**

**Texte à copier (caption) :**

Nouveau format cette semaine : un dossier réel, et une grille de lecture fixe — toujours la
même — pour comparer ce que sort notre moteur à ce que dit vraiment la HAS. On ne compare que
sur les mécanismes que le moteur revendique de couvrir (identification causale, mesure de
l'effet, pertinence de l'évidence) — jamais sur ceux qu'il ne couvre pas.

Le dossier : DIZG DBM, une allogreffe osseuse déminéralisée utilisée pour combler des pertes de
substance osseuse en chirurgie orthopédique, oncologie, neurochirurgie, stomatologie et
maxillo-faciale. Le moteur reçoit uniquement la revendication clinique — jamais l'avis, jamais
la conclusion.

Résultat sur les 3 mécanismes couverts : 1 confirmé mot pour mot, 1 manqué par le moteur, et sur
le troisième (pertinence de l'évidence) le moteur confirme désormais aussi le caractère
monocentrique en plus du risque population déjà détecté en interne — toujours pas assez fort à
lui seul pour faire bouger le verdict global. Le détail en image.

Le dossier a finalement été accepté par la HAS (Service Attendu Suffisant, Amélioration niveau
V) : ce n'était pas un motif de rejet, seulement des limites méthodologiques parmi d'autres
relevées par la commission.

1/N — la suite de la série : d'autres dossiers, avec la même grille, dans les deux sens.

#DispositifsMédicaux #HAS #CNEDiMTS #AccèsAuMarché #RWE #MedTech

**Détail de la grille (dans l'image, pas dans le texte copié) :**

| Mécanisme | Ce que sort le moteur | Ce que dit l'avis HAS | Verdict |
|---|---|---|---|
| MF_A identification causale | Structure causale directe — rien détecté sur ce point (le monocentrisme est repris plus bas, côté MF_D/CAS) | « caractère monocentrique » | Manqué |
| MF_B mesure de l'effet | ADJUDICATION_RISK — absence d'évaluation en aveugle | « absence d'information sur le caractère aveugle ou ouvert de l'étude (au moins pour le patient) » | Confirmé |
| MF_D pertinence de l'évidence | CAS_CONTEXT confirmé (étude jugée monocentrique) ; reste muet sur le risque d'alignement population, verdict global reste "acceptable" (0,9) | « caractère monocentrique » + « Les données cliniques disponibles ne permettent pas la comparaison de DIZG DBM avec les autres allogreffes […] » | Partiel |

MF_C (puissance statistique) et MF_E (fiabilité du corpus) : hors périmètre du moteur, absents
de la grille par construction.

**Mise à jour 2026-07-10 (nouveau moteur, commit `055bfab`)** : re-exécution de `has_vs_moteur.py`
(2 runs, stables) après le nouveau seuil `care_pathway_match == PARTIAL` dans `cas_engine.py`
(auparavant seul l'extrême `NO` déclenchait un risque CONTEXT). Résultat : `CAS_CONTEXT` fire
désormais sur ce dossier et confirme textuellement « monocentrique » — absent des 5 runs
archivés précédents (07-08/07-09). Le signal reste rattaché à MF_D (CAS engine), pas à MF_A
(structure causale), d'où le déclassement de la ligne MF_A en "rien détecté sur ce point" plutôt
qu'un vrai correctif de ce mécanisme-là.

**Mise à jour 2026-07-11 (indication_matches_ce_marking + fix du vote consensus des endpoints)** :
re-exécution de `has_vs_moteur.py` après les mêmes correctifs que pour WALRUS (voir plus bas,
rwe-v5 commit `97c354b` / cnedimts_analysis commit `2bbeeee`). Contrairement à WALRUS, ce dossier
n'est pas affecté sur le fond : `indication_matches_ce_marking=True` (le texte ne mentionne aucun
usage hors périmètre du marquage CE pour ce dispositif), et tous les autres signaux restent
identiques au run du 07-10 (structure DIRECT, CAS_CONTEXT confirmé, CAS_POPULATION non confirmé,
ADJUDICATION_RISK confirmé, tendance LOW). Le vote consensus des endpoints ne relève ici qu'une
instabilité mineure de libellé (`device_studied`, `endpoints[].result_direction`), sans effet sur
`causal_role` ni sur l'ensemble des endpoints primaires — ce dossier n'avait pas de cas limite
comparable à celui de WALRUS. Grille et texte inchangés.

---

## CAS 2/N — WALRUS (dossier 7182, primo-inscription, avis du 23 avril 2024)

**[IMAGE : bandeau dispositif + bandeau verdict global + grille MF_A/MF_B/MF_D — capture de
`linkedin_case2_7182_share.html`]**

Choisi comme "cas d'école" : contrairement à DIZG DBM (cas 1, résultat mitigé au niveau
mécanisme), ici la **tendance de risque méthodologique** du moteur (HIGH) matche directement la
vraie décision HAS (SA Insuffisant) — portée par la structure causale CIRCULAR, pas par un flag
isolé. Bon exemple pédagogique de pourquoi la tendance combine structure + sévérité des biais
plutôt que de reposer sur un seul flag (cf. `assess_methodological_risk`, renommage du
2026-07-10 qui remplace l'ancien `overall_verdict`/`ACCEPTABLE`-`REJECTED`, [[project_rwe_v5]]).

**Texte à copier (caption) :**

Un cas un peu plus « d'école » cette semaine, dans la même série : un dossier où c'est la
structure causale elle-même qui est en cause — pas juste un biais isolé parmi d'autres.

Le dossier : WALRUS, un cathéter-guide à ballonnet utilisé en thrombectomie mécanique lors de la
prise en charge des AVC ischémiques à la phase aiguë. Le moteur reçoit uniquement la
revendication clinique — jamais l'avis, jamais la conclusion.

Le moteur classe la structure causale circulaire : les études soumises ne permettent pas
d'identifier proprement l'effet du dispositif. Sa tendance de risque méthodologique : HIGH —
cohérente avec la décision réelle de la HAS (Service Attendu Insuffisant).

Le détail mécanisme par mécanisme est plus nuancé : un des biais individuels (le risque de
critère de substitution) ne se retrouve pas clairement dans le texte de l'avis. En revanche, sur
la pertinence de l'évidence, le moteur confirme désormais pleinement deux signaux distincts : le
caractère monocentrique de l'étude retenue, et l'usage hors périmètre du marquage CE (artère
vertébrale) que la HAS cite explicitement — un signal que le moteur ratait jusqu'ici. C'est
précisément pour ça que la tendance de risque ne repose jamais sur un seul flag isolé : elle
regarde d'abord si la structure elle-même tient debout.

2/N — toujours la même grille, sur un nouveau dossier.

#DispositifsMédicaux #HAS #CNEDiMTS #AccèsAuMarché #RWE #MedTech

**Détail de la grille (dans l'image, pas dans le texte copié) :**

| Mécanisme | Ce que sort le moteur | Ce que dit l'avis HAS | Verdict |
|---|---|---|---|
| MF_A identification causale | Structure causale CIRCULAIRE — effet non identifiable | « Huit des quinze études retenues sont des études rétrospectives et aucune n'était contrôlée randomisée. » | Confirmé |
| MF_B mesure de l'effet | SURROGATE_RISK détecté | aucune critique isolée et vérifiable sur ce point précis dans le texte de l'avis | Non confirmé |
| MF_D pertinence de l'évidence | CAS_CONTEXT confirmé (étude monocentrique) + CAS_CE_MARKING confirmé (usage hors périmètre du marquage CE) | « étude monocentrique à collecte rétrospective des données avec des critères de jugement non hiérarchisés » + « [...] l'utilisation du cathéter dans l'artère vertébrale ne correspond pas à l'indication du marquage CE. » | Confirmé |

MF_C/MF_E : hors périmètre, absents de la grille. Bandeau "Tendance de risque méthodologique du
moteur = Décision réelle HAS" en tête d'image, avant la grille de détail — élément visuel qui
n'existait pas dans le template du cas 1, à garder pour les cas futurs où la tendance globale
(pas seulement un mécanisme isolé) matche la décision réelle.

**Mise à jour 2026-07-10 (nouveau moteur)** : re-exécution de `has_vs_moteur.py` (2 runs) après
le rename `overall_verdict`→`methodological_risk` (commit `eb64620`) et le nouveau seuil
`care_pathway_match == PARTIAL` (commit `055bfab`). Contrairement à DIZG DBM, le signal
`CAS_CONTEXT`/monocentrique n'est pas nouveau pour ce dossier : il était déjà présent dans 4/5
runs archivés depuis le 07-08 — la ligne MF_D du post original ("Manqué", "aucune alerte forte")
était donc déjà factuellement inexacte avant même le changement de moteur d'aujourd'hui, corrigée
ici. Les bias flags (SURROGATE_RISK/CIRCULARITY_RISK/ADJUDICATION_RISK, CAS 0,9) restent conformes
à l'historique une fois l'instabilité LLM d'un run isolé écartée (voir [[project_rwe_v5]]).

**Mise à jour 2026-07-11 (indication_matches_ce_marking + fix du vote consensus des endpoints)** :
ajout d'un champ `indication_matches_ce_marking` sur `StudyObject`, câblé dans `cas_engine.py`
comme risque additif `CAS_CE_MARKING` (n'affecte pas `cas_score`/verdict, cf. calibration auditée
dans `assess_methodological_risk`) — rwe-v5 commit `97c354b`. `has_vs_moteur.py` bascule sur
`parse_study_object_with_llm_consensus()` (cnedimts_analysis commit `2bbeeee`) au lieu de l'appel
simple, ce qui a mis au jour un bug corrigé dans le même commit rwe-v5 : `_majority_vote()` votait
sur la liste `endpoints` entière comme un bloc atomique, donc le "correctif consensus" existant ne
stabilisait en réalité jamais `causal_role`. Sur ce dossier précis, l'endpoint primaire de Cortez
et al. (« succès technique de la navigation ») s'est révélé un vrai cas limite : 4/7 vs 3/7 entre
CIRCULAR et INDEPENDENT sur des appels identiques avec l'ancien prompt/vote. Avec la définition
CIRCULAR élargie (couvre désormais la performance procédurale d'un dispositif — le dispositif
réussit sa propre tâche mécanique conçue — pas seulement la détection) et le vote endpoint-par-
endpoint corrigé (alignement par `is_primary` + similarité de nom, endpoints minoritaires
exclus), 5/5 essais (n_calls=3) et 3/3 (n_calls=7) convergent sur CIRCULAR, cohérent avec les 6/6
runs archivés avant ce fix. Le champ `causal_role` de cet endpoint reste listé dans
`unstable_fields` (désaccord résiduel par appel individuel), mais le résultat consensus est
désormais stable — signal affiché dans le post lui-même plutôt que masqué. Résultat : `CAS_CE_MARKING`
confirme désormais textuellement (« marquage ce ») le point que le moteur ratait jusqu'ici, et
`causal_structure`/`overall_verdict` restent CIRCULAR/HIGH de façon reproductible plutôt que de
dépendre du hasard d'un seul appel LLM.

---

## Candidats pour la suite (non rédigés)

- **VIS-RX (8145)** — vrai rejet HAS, moteur alarmé mais sur le mauvais mécanisme exact (circularité
  au lieu de pertinence clinique du critère de jugement + mismatch population) — bon candidat pour
  un post "cas où on se trompe", cohérent avec la règle éditoriale n°1 ci-dessus.
- **TRIPLE ACTION (7620)** — rejet HAS, 2 confirmations textuelles (NO_COMPARATOR + CAS_CONTEXT),
  fait partie des "5 trop indulgents" documentés — vérifier sa `methodological_risk` avant de
  l'utiliser (structure DIRECT, donc probablement encore LOW/MODERATE malgré le rejet réel — bon
  candidat pour illustrer une vraie limite actuelle, pas un cas d'école).
