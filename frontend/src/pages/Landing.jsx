import { Link } from 'react-router-dom'
import { useLang } from '../LangContext'
import Reveal from '../components/Reveal'
import NarrativeBeat from '../components/NarrativeBeat'
import { RulerIcon, ClipboardIcon, TargetIcon, DatabaseIcon, DocumentIcon, CogIcon, RocketIcon, XCircleIcon } from '../components/icons'
import demonstrationTriptyque from '../assets/demonstration-triptyque.png'

// ── What the engine analyzes (no framework/mechanism language on the landing) ──

const ANALYSIS_POINTS_FR = [
  'Peut-on attribuer l\'effet observé au dispositif ?',
  'Les critères de jugement permettent-ils réellement de mesurer le bénéfice revendiqué ?',
  'Les preuves produites répondent-elles à la question clinique posée ?',
]

const ANALYSIS_POINTS_EN = [
  'Can the observed effect be attributed to the device?',
  'Do the endpoints actually measure the claimed benefit?',
  'Does the evidence produced answer the clinical question being asked?',
]

// ── Why studies fail to demonstrate their claim ─────────────────────────────

const PROBLEM_CARDS_FR = [
  { Icon: RulerIcon,    title: 'Mesure non adaptée',              desc: 'Un critère influencé par le dispositif lui-même ne permet pas d\'attribuer l\'effet observé.' },
  { Icon: ClipboardIcon, title: 'Design insuffisant',             desc: 'Un design exploratoire ou sans comparateur ne permet pas d\'inférence causale.' },
  { Icon: TargetIcon,   title: 'Preuve non pertinente',           desc: 'Des données qui répondent à une question différente de celle posée.' },
  { Icon: DatabaseIcon, title: 'Plus de données ne suffisent pas', desc: 'Si la structure de la démonstration est inadéquate, ajouter des données ne corrige pas le problème.' },
]

const PROBLEM_CARDS_EN = [
  { Icon: RulerIcon,    title: 'Unsuitable measurement',    desc: 'An endpoint influenced by the device itself cannot attribute the observed effect.' },
  { Icon: ClipboardIcon, title: 'Insufficient design',      desc: 'An exploratory design or one without a comparator does not allow causal inference.' },
  { Icon: TargetIcon,   title: 'Irrelevant evidence',       desc: 'Data that answers a different question from the one being asked.' },
  { Icon: DatabaseIcon, title: 'More data is not enough',   desc: 'If the demonstration structure is inadequate, adding more data does not fix the problem.' },
]

// ── Illustrative example gaps ─────────────────────────────────────────────────

const EXAMPLE_GAPS_FR = [
  {
    label: 'Indépendance de la mesure',
    desc: 'Le critère principal est influencé par le dispositif lui-même, ce qui limite l\'interprétation causale. La fréquence des événements détectés dépend de la sensibilité du dispositif, non de l\'évolution clinique réelle.',
  },
  {
    label: 'Design',
    desc: 'Absence de comparateur. Sans contrefactuel observé, l\'amélioration ne peut être attribuée au dispositif plutôt qu\'à l\'histoire naturelle de la pathologie ou à des co-interventions.',
  },
  {
    label: 'Niveau de preuve',
    desc: 'Le design exploratoire génère des hypothèses — il ne les confirme pas. Il ne soutient pas une revendication d\'efficacité clinique.',
  },
]

const EXAMPLE_GAPS_EN = [
  {
    label: 'Independence of measurement',
    desc: 'The primary endpoint is influenced by the device itself, limiting causal interpretation. The frequency of detected events depends on the device\'s sensitivity, not on actual clinical evolution.',
  },
  {
    label: 'Design',
    desc: 'No comparator. Without an observed counterfactual, improvement cannot be attributed to the device rather than to the natural history of the disease or co-interventions.',
  },
  {
    label: 'Level of evidence',
    desc: 'An exploratory design generates hypotheses — it does not confirm them. It does not support a clinical efficacy claim.',
  },
]

// ── Component ────────────────────────────────────────────────────────────────

export default function Landing() {
  const { lang } = useLang()
  const fr = lang === 'fr'

  const analysisPoints = fr ? ANALYSIS_POINTS_FR : ANALYSIS_POINTS_EN
  const problemCards    = fr ? PROBLEM_CARDS_FR : PROBLEM_CARDS_EN
  const exampleGaps    = fr ? EXAMPLE_GAPS_FR : EXAMPLE_GAPS_EN

  return (
    <div>

      {/* ── HERO ─────────────────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-br from-primary to-primary-light text-white py-20 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(255,255,255,0.05)_0%,transparent_50%)]" />
        <div className="max-w-6xl mx-auto relative grid lg:grid-cols-2 gap-12 items-center">

          <div className="text-center lg:text-left">
            <div className="inline-block bg-white/10 rounded-full px-4 py-1.5 text-sm font-medium mb-8 backdrop-blur-sm">
              {fr
                ? 'Dispositifs médicaux · Méthodologie clinique · Accès au marché'
                : 'Medical devices · Clinical methodology · Market access'}
            </div>

            <h1 className="text-4xl md:text-5xl font-bold mb-5 leading-tight">
              {fr
                ? 'Votre étude a-t-elle été conçue pour démontrer ce que vous affirmez ?'
                : 'Was your study designed to demonstrate what you claim?'}
            </h1>

            <p className="text-lg text-white/85 mb-8 leading-relaxed">
              {fr
                ? 'EvidenceAble vous indique si votre stratégie de preuve est réellement capable de soutenir votre revendication clinique — avant d\'investir dans une étude ou de soumettre un dossier.'
                : 'EvidenceAble tells you whether your evidence strategy can actually support your clinical claim — before you invest in a study or submit a dossier.'}
            </p>

            <div className="flex items-center gap-3 justify-center lg:justify-start mb-8 flex-wrap text-sm text-white/80">
              <span className="bg-white/10 border border-white/15 rounded-lg px-3 py-2">
                {fr ? 'Revendication + données cliniques (essai, cohorte, registre, RWE)' : 'Claim + clinical data (trial, cohort, registry, RWE)'}
              </span>
              <span className="text-white/50">→</span>
              <span className="bg-white/10 border border-white/15 rounded-lg px-3 py-2">
                {fr ? 'Écarts identifiés et plan de correction' : 'Identified gaps and correction plan'}
              </span>
            </div>

            <div className="flex gap-3 justify-center lg:justify-start flex-wrap">
              <Link
                to="/repair"
                className="bg-accent hover:bg-accent/90 text-white px-6 py-3 rounded-xl font-semibold transition-colors shadow-lg shadow-accent/30"
              >
                {fr ? 'Analyser mes données →' : 'Analyse my evidence →'}
              </Link>
              <a
                href={`mailto:olivier@evidenceable.com?subject=${encodeURIComponent(fr ? 'Demande d’accès test — EvidenceAble' : 'Test access request — EvidenceAble')}`}
                className="border border-white/25 hover:bg-white/10 text-white px-6 py-3 rounded-xl font-semibold transition-colors"
              >
                {fr ? 'Demander un accès gratuit' : 'Request free access'}
              </a>
            </div>
          </div>

          <div className="bg-white rounded-3xl p-6 shadow-xl">
            <img src={demonstrationTriptyque} alt={fr ? 'Le triptyque de la démonstration clinique' : 'The clinical demonstration triptych'} className="w-full h-auto" />
          </div>
        </div>
      </section>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? "Avant d'aller plus loin, une question simple se pose."
            : 'Before going further, a simple question needs answering.'}
        </NarrativeBeat>
      </div>

      {/* ── PROBLÈME ─────────────────────────────────────────────────────────── */}
      <Reveal as="section" className="py-20 px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-primary text-center mb-6">
            {fr
              ? 'Un dossier peut être robuste — et ne pas constituer une preuve.'
              : 'A dossier can be robust — and still not constitute evidence.'}
          </h2>
          <p className="text-center text-gray-500 mb-10 leading-relaxed">
            {fr
              ? 'Dans de nombreux projets cliniques, le problème n\'est pas la qualité des données. C\'est le décalage entre ce que la source de données mesure et ce que la revendication affirme — qu\'il s\'agisse d\'un essai randomisé, d\'une cohorte observationnelle ou de données en vie réelle.'
              : 'In many clinical projects, the problem is not the quality of the data. It is the gap between what the data source measures and what the claim asserts — whether it is a randomised trial, an observational cohort or real-world data.'}
          </p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
            {problemCards.map(({ Icon, title, desc }, i) => (
              <Reveal key={i} delay={i * 80} className="bg-gray-50 border border-gray-100 rounded-xl px-5 py-6 text-center flex flex-col items-center">
                <div className="w-12 h-12 rounded-full bg-white border border-gray-100 flex items-center justify-center mb-3 shadow-sm">
                  <Icon className="w-6 h-6 text-gray-400" />
                </div>
                <div className="flex items-center gap-1.5 mb-2">
                  <XCircleIcon className="w-4 h-4 text-red-400 flex-shrink-0" />
                  <p className="text-sm font-bold text-gray-800">{title}</p>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
              </Reveal>
            ))}
          </div>

          <div className="bg-primary/5 border-2 border-primary/15 rounded-xl px-8 py-6 text-center">
            <p className="text-primary font-semibold text-lg leading-relaxed">
              {fr
                ? 'La question centrale devient : votre stratégie de preuve peut-elle réellement démontrer votre revendication clinique ?'
                : 'The central question becomes: can your evidence strategy actually demonstrate your clinical claim?'}
            </p>
          </div>
        </div>
      </Reveal>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? "C'est précisément cette question que le moteur répond, de façon systématique et traçable."
            : 'This is exactly the question the engine answers — systematically, and traceably.'}
        </NarrativeBeat>
      </div>

      {/* ── CE QUE LE MOTEUR ANALYSE ─────────────────────────────────────────── */}
      <Reveal as="section" className="py-20 px-6 bg-surface border-y border-gray-100">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-primary text-center mb-4">
            {fr ? 'Ce que le moteur analyse' : 'What the engine analyzes'}
          </h2>
          <p className="text-center text-gray-500 mb-12 max-w-xl mx-auto text-sm leading-relaxed">
            {fr
              ? 'Une étude clinique ne suffit pas — ce qui compte, c\'est sa capacité à démontrer de manière crédible le bénéfice revendiqué. Le moteur analyse automatiquement les éléments méthodologiques qui déterminent cette capacité.'
              : 'A clinical study is not enough — what matters is its ability to credibly demonstrate the claimed benefit. The engine automatically analyses the methodological elements that determine that ability.'}
          </p>

          <div className="space-y-3 mb-10">
            {analysisPoints.map((item, i) => (
              <Reveal key={i} delay={i * 80} className="flex items-start gap-4 bg-white border border-gray-100 rounded-xl px-6 py-4 shadow-sm">
                <span className="text-accent font-bold mt-0.5 flex-shrink-0 text-lg">✓</span>
                <p className="text-gray-700 text-sm leading-relaxed font-medium">{item}</p>
              </Reveal>
            ))}
          </div>

          <p className="text-center text-gray-400 text-sm max-w-2xl mx-auto italic">
            {fr
              ? 'Le moteur ne se limite pas à détecter des biais isolés — il évalue la capacité d\'une étude à soutenir une démonstration clinique.'
              : 'The engine does not just flag isolated biases — it evaluates a study\'s ability to support a clinical demonstration.'}
          </p>
        </div>
      </Reveal>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? 'Concrètement, ce moteur unique se décline en deux profondeurs d\'analyse.'
            : 'In practice, this single engine comes in two depths of analysis.'}
        </NarrativeBeat>
      </div>

      {/* ── COMMENT ÇA FONCTIONNE ────────────────────────────────────────────── */}
      <Reveal as="section" className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-primary text-center mb-4">
            {fr ? 'Comment ça fonctionne' : 'How it works'}
          </h2>
          <p className="text-center text-gray-500 text-sm mb-14 max-w-lg mx-auto font-medium">
            {fr
              ? 'Votre revendication et vos données cliniques, analysées ensemble.'
              : 'Your claim and your clinical data, analysed together.'}
          </p>

          <div className="grid md:grid-cols-3 gap-6 relative">
            {[
              {
                Icon: DocumentIcon,
                title: fr ? 'Vous fournissez' : 'You provide',
                desc: fr
                  ? 'Votre revendication et un abstract ou PDF (≤ 5 pages) d\'un essai, d\'une cohorte, d\'un registre ou d\'une étude en vie réelle.'
                  : 'Your claim and an abstract or PDF (≤ 5 pages) of a trial, cohort, registry, or real-world study.',
              },
              {
                Icon: CogIcon,
                title: fr ? 'Le moteur analyse' : 'The engine analyses',
                desc: fr
                  ? 'Il reconstruit la logique de la revendication, évalue les critères de jugement et le design d\'étude, puis identifie les écarts structurels.'
                  : 'It reconstructs the logic of the claim, evaluates the endpoints and study design, then identifies structural gaps.',
              },
              {
                Icon: ClipboardIcon,
                title: fr ? 'Vous obtenez' : 'You get',
                desc: fr
                  ? 'Un diagnostic de démonstration et un plan de correction priorisé (immédiat, amendement ou nouvelle étude).'
                  : 'A demonstration diagnostic and a prioritised correction plan (immediate, amendment, or new study).',
              },
            ].map(({ Icon, title, desc }, i) => (
              <Reveal key={i} delay={i * 100} className="bg-surface rounded-2xl border border-gray-100 p-6 relative">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg bg-accent/10 text-accent flex items-center justify-center font-bold text-sm flex-shrink-0">
                    {i + 1}
                  </div>
                  <Icon className="w-6 h-6 text-accent flex-shrink-0" />
                  <h3 className="font-bold text-gray-800">{title}</h3>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{desc}</p>
                {i < 2 && (
                  <span className="hidden md:flex absolute top-1/2 -right-4 -translate-y-1/2 w-8 h-8 items-center justify-center text-accent text-xl font-bold z-10">
                    →
                  </span>
                )}
              </Reveal>
            ))}
          </div>

          <div className="text-center mt-10">
            <Link
              to="/repair"
              className="inline-block bg-accent hover:bg-accent/90 text-white px-8 py-3 rounded-xl font-semibold transition-colors shadow-md shadow-accent/20"
            >
              {fr ? 'Analyser mes données →' : 'Analyse my evidence →'}
            </Link>
            <p className="text-xs text-gray-400 mt-3">
              {fr ? 'Diagnostic Complet + Repair — sur demande' : 'Full Diagnosis + Repair — on request'}
            </p>
          </div>
        </div>
      </Reveal>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? 'À l\'arrivée, le moteur rend un verdict de démonstration.'
            : 'In the end, the engine returns a demonstration verdict.'}
        </NarrativeBeat>
      </div>

      {/* ── VERDICT ──────────────────────────────────────────────────────────── */}
      <Reveal as="section" className="bg-surface py-14 px-6 border-y border-gray-100">
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
            {fr ? 'Diagnostic de démonstration' : 'Demonstration diagnostic'}
          </p>
          <h2 className="text-2xl font-bold text-primary mb-8">
            {fr ? 'La structure de preuve permet-elle de démontrer la revendication ?' : 'Does the evidence structure actually demonstrate the claim?'}
          </h2>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Reveal delay={0} className="flex-1"><AlignmentBadge
              color="green"
              label={fr ? 'Démonstration valide' : 'Valid demonstration'}
              sub={fr
                ? 'La structure de preuve permet une démonstration valide au niveau revendiqué. Les critères méthodologiques nécessaires sont réunis.'
                : 'The evidence structure allows a valid demonstration at the claimed level. The necessary methodological criteria are met.'}
            /></Reveal>
            <Reveal delay={80} className="flex-1"><AlignmentBadge
              color="orange"
              label={fr ? 'Démonstration partielle' : 'Partial demonstration'}
              sub={fr
                ? 'Des écarts structurels existent mais peuvent être corrigés par ajustement de design sans refonte complète.'
                : 'Structural gaps exist but can be corrected by design adjustment without a full redesign.'}
            /></Reveal>
            <Reveal delay={160} className="flex-1"><AlignmentBadge
              color="red"
              label={fr ? 'Démonstration non valide' : 'Invalid demonstration'}
              sub={fr
                ? 'Le design ou les mesures ne permettent pas une inférence causale au niveau de la revendication formulée.'
                : 'The design or measurements do not allow causal inference at the level of the formulated claim.'}
            /></Reveal>
          </div>
        </div>
      </Reveal>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? 'Voici, sur un cas concret, à quoi ressemble ce diagnostic.'
            : 'Here is what that diagnosis looks like on a concrete case.'}
        </NarrativeBeat>
      </div>

      {/* ── EXEMPLE ──────────────────────────────────────────────────────────── */}
      <Reveal as="section" className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-accent font-semibold text-sm uppercase tracking-widest mb-4">
            {fr ? 'Exemple concret' : 'Concrete example'}
          </p>
          <h2 className="text-3xl font-bold text-primary text-center mb-4">
            {fr ? 'Décalage revendication ↔ preuve' : 'Claim ↔ evidence mismatch'}
          </h2>

          <div className="text-center mb-10">
            <div className="inline-block bg-gray-50 border border-gray-200 rounded-xl px-6 py-4 max-w-xl text-left">
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">
                {fr ? 'Revendication' : 'Claim'}
              </p>
              <p className="text-sm text-gray-700 italic mb-3">
                {fr
                  ? '"Le dispositif permet une détection précoce des événements critiques et améliore la prise en charge."'
                  : '"The device enables early detection of critical events and improves patient management."'}
              </p>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wide">
                  {fr ? 'Résultat' : 'Result'}
                </span>
                <span className="bg-orange-100 text-orange-700 text-xs font-bold px-2.5 py-1 rounded-full">
                  {fr ? 'Démonstration partielle' : 'Partial demonstration'}
                </span>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Gaps */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
              <div className="bg-gray-50 border-b border-gray-100 px-5 py-3">
                <span className="font-semibold text-gray-700 text-sm">
                  {fr ? 'Analyse EvidenceAble — 3 écarts identifiés' : 'EvidenceAble analysis — 3 gaps identified'}
                </span>
              </div>
              <div className="divide-y divide-gray-50">
                {exampleGaps.map((g, i) => (
                  <Reveal key={i} delay={i * 80} className="px-5 py-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="bg-primary/10 text-primary text-xs font-bold px-2 py-0.5 rounded">
                        {fr ? `Écart ${i + 1}` : `Gap ${i + 1}`}
                      </span>
                      <span className="text-xs text-gray-400 font-semibold uppercase tracking-wide">{g.label}</span>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">{g.desc}</p>
                  </Reveal>
                ))}
              </div>
            </div>

            {/* Plan */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm flex flex-col">
              <div className="bg-accent/10 border-b border-accent/20 px-5 py-3">
                <span className="font-semibold text-accent text-sm">
                  {fr ? 'Plan de correction' : 'Correction plan'}
                </span>
              </div>
              <div className="px-5 py-5 flex-1 space-y-4">
                {(fr
                  ? [
                      { effort: '✅ Immédiat', cls: 'bg-green-50 border-green-200 text-green-700', action: 'Ajuster le type de revendication vers une performance mesurable', hint: 'La circularité disparaît si la revendication devient "sensibilité X% vs. méthode de référence". Le design existant devient cohérent.' },
                      { effort: '🔧 Amendement', cls: 'bg-orange-50 border-orange-200 text-orange-700', action: 'Introduire un comparateur pour établir un contrefactuel', hint: 'Un groupe contrôle concurrent permet d\'isoler l\'effet du dispositif de l\'histoire naturelle.' },
                      { effort: '🏗 Nouvelle étude', cls: 'bg-red-50 border-red-200 text-red-700', action: 'Reformuler les endpoints pour les rendre indépendants du dispositif', hint: 'Remplacer le critère généré par le dispositif par un outcome adjugé indépendamment.' },
                    ]
                  : [
                      { effort: '✅ Immediate', cls: 'bg-green-50 border-green-200 text-green-700', action: 'Adjust claim type to a measurable performance claim', hint: 'Circularity disappears if the claim becomes "sensitivity X% vs. reference method". The existing design becomes coherent.' },
                      { effort: '🔧 Amendment', cls: 'bg-orange-50 border-orange-200 text-orange-700', action: 'Add a comparator to establish a counterfactual', hint: 'A concurrent control group allows isolating the device effect from the natural history.' },
                      { effort: '🏗 New study', cls: 'bg-red-50 border-red-200 text-red-700', action: 'Reformulate endpoints to make them independent of the device', hint: 'Replace the device-generated endpoint with an independently adjudicated outcome.' },
                    ]
                ).map((a, i) => (
                  <Reveal key={i} delay={i * 80}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold border ${a.cls}`}>{a.effort}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-800 mb-1">{a.action}</p>
                    <p className="text-xs text-gray-400 italic border-l-2 border-gray-200 pl-3 leading-relaxed">{a.hint}</p>
                  </Reveal>
                ))}
              </div>
            </div>
          </div>

          {/* Ce que vous gagnez */}
          <div className="mt-12 bg-surface rounded-2xl border border-gray-100 p-8">
            <h3 className="text-center font-bold text-gray-800 mb-6">
              {fr ? 'Ce que vous gagnez' : 'What you gain'}
            </h3>
            <div className="grid sm:grid-cols-2 gap-5">
              {(fr
                ? [
                    { title: 'Décider avant d\'investir dans une étude', desc: 'Évitez les impasses méthodologiques coûteuses.' },
                    { title: 'Renforcer votre dossier avant soumission', desc: 'Anticipez les critiques structurelles.' },
                    { title: 'Prioriser les actions qui comptent', desc: 'Un plan clair : immédiat, amendement ou nouvelle étude.' },
                    { title: 'Gagner du temps avec les parties prenantes', desc: 'Arguments structurés et traçables.' },
                  ]
                : [
                    { title: 'Decide before investing in a study', desc: 'Avoid costly methodological dead ends.' },
                    { title: 'Strengthen your dossier before submission', desc: 'Anticipate structural critiques.' },
                    { title: 'Prioritise the actions that matter', desc: 'A clear plan: immediate, amendment, or new study.' },
                    { title: 'Save time with stakeholders', desc: 'Structured, traceable arguments.' },
                  ]
              ).map(({ title, desc }, i) => (
                <Reveal key={i} delay={i * 80} className="flex items-start gap-3">
                  <span className="text-accent font-bold mt-0.5 flex-shrink-0 text-lg">✓</span>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </Reveal>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? "Ce n'est pas un cas isolé — ce motif se retrouve à l'échelle du corpus réglementaire."
            : 'This is not an isolated case — the pattern recurs across the regulatory corpus.'}
        </NarrativeBeat>
      </div>

      {/* ── VALIDATION DU CADRE ───────────────────────────────────────────────── */}
      <Reveal as="section" className="py-20 px-6 bg-surface border-y border-gray-100">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-accent font-semibold text-sm uppercase tracking-widest mb-4">
            {fr ? 'Validation empirique' : 'Empirical validation'}
          </p>
          <h2 className="text-3xl font-bold text-primary text-center mb-4">
            {fr
              ? 'Règles confrontées à 58 avis CNEDiMTS (2022–2025)'
              : 'Rules validated against 58 CNEDiMTS opinions (2022–2025)'}
          </h2>
          <p className="text-center text-gray-500 mb-3 max-w-2xl mx-auto text-sm leading-relaxed">
            {fr
              ? 'Les règles du moteur ont été élaborées à partir de principes méthodologiques et vérifiées sur un corpus d\'avis publics (PECAN, LATM, LPPR — favorables et défavorables) pour confirmer qu\'elles capturent les motifs récurrents de critique méthodologique.'
              : 'Engine rules were built from methodological principles and verified against a corpus of public opinions (PECAN, LATM, LPPR — favorable and unfavorable) to confirm they capture recurring methodological critique patterns.'}
          </p>
          <p className="text-center text-gray-400 text-xs mb-14 italic max-w-xl mx-auto">
            {fr
              ? 'Ces règles ne constituent pas une prédiction réglementaire. Elles formalisent des principes méthodologiques observés.'
              : 'These rules do not constitute a regulatory prediction. They formalise observed methodological principles.'}
          </p>

          <div className="grid md:grid-cols-3 gap-6">
            {(fr
              ? [
                  {
                    pattern: 'Incohérence dispositif ↔ population',
                    scale: 'Majorité des dossiers',
                    detail: 'Le demandeur fournit des données issues d\'un autre dispositif, d\'une autre génération, ou d\'une population ne correspondant pas à l\'indication revendiquée.',
                    quote: 'aucune étude spécifique de TUCKY CENTER n\'a été soumise',
                    source: 'CNEDiMTS, 2023',
                  },
                  {
                    pattern: 'Dépendance des critères de jugement',
                    scale: 'Part significative des cas',
                    detail: 'Le critère principal est généré ou influencé par le dispositif évalué. L\'ascertainment de l\'outcome n\'est pas indépendant du bras de traitement.',
                    quote: 'le critère de jugement principal […] est le nombre de fois où le dispositif détecte une augmentation de la température avant le patient',
                    source: 'CNEDiMTS, 2023',
                  },
                  {
                    pattern: 'Insuffisance du design',
                    scale: 'Fraction notable des dossiers',
                    detail: 'Le design ne permet pas d\'inférence causale au niveau de la revendication. Design exploratoire pour une revendication d\'outcome, ou absence de comparateur.',
                    quote: 'cette étude porte sur une partie restreinte de l\'indication revendiquée',
                    source: 'CNEDiMTS, 2023',
                  },
                ]
              : [
                  {
                    pattern: 'Device ↔ population incoherence',
                    scale: 'Majority of dossiers',
                    detail: 'The applicant provides data from another device, another generation, or a population that does not match the claimed indication.',
                    quote: 'no specific study of TUCKY CENTER was submitted',
                    source: 'CNEDiMTS, 2023',
                  },
                  {
                    pattern: 'Endpoint dependency',
                    scale: 'Significant proportion of cases',
                    detail: 'The primary endpoint is generated or influenced by the device under evaluation. Outcome ascertainment is not independent of the treatment arm.',
                    quote: 'the primary endpoint […] is the number of times the device detects a temperature rise before the patient does',
                    source: 'CNEDiMTS, 2023',
                  },
                  {
                    pattern: 'Insufficient study design',
                    scale: 'Notable fraction of dossiers',
                    detail: 'The design does not permit causal inference at the claim level. Exploratory design for an outcome claim, or no comparator arm.',
                    quote: 'this study covers a restricted part of the claimed indication',
                    source: 'CNEDiMTS, 2023',
                  },
                ]
            ).map((item, i) => (
              <Reveal key={i} delay={i * 80} className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
                <div className="inline-block bg-primary/8 text-primary text-xs font-bold px-3 py-1 rounded-full mb-3">
                  {item.scale}
                </div>
                <h3 className="font-semibold text-gray-800 mb-2">{item.pattern}</h3>
                <p className="text-sm text-gray-600 mb-4 leading-relaxed">{item.detail}</p>
                <div className="bg-surface rounded-lg p-3 border text-xs text-gray-500 italic">
                  &laquo; {item.quote} &raquo;
                  <span className="block text-right text-gray-400 mt-1">— {item.source}</span>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Reveal>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? "Cette validation n'est pas théorique — voici comment y accéder."
            : "This validation isn't theoretical — here's how to access it."}
        </NarrativeBeat>
      </div>

      {/* ── ACCÈS — phase de test ────────────────────────────────────────────── */}
      <Reveal as="section" className="py-20 px-6 bg-white">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold text-primary text-center mb-4">
            {fr ? 'Accès' : 'Access'}
          </h2>
          <p className="text-center text-gray-500 mb-2 max-w-xl mx-auto text-sm">
            {fr
              ? 'EvidenceAble est en phase de test. Le Diagnostic Complet + Repair est gratuit, accessible sur demande avec un quota d\'analyses dédié.'
              : 'EvidenceAble is in testing phase. Full Diagnosis + Repair is free, accessible on request with a dedicated analysis quota.'}
          </p>
          <p className="text-center text-gray-400 mb-12 max-w-xl mx-auto text-xs italic">
            {fr
              ? 'Offre limitée dans le temps et en nombre de demandes.'
              : 'Limited-time offer, limited number of requests.'}
          </p>

          <Reveal className="bg-white rounded-2xl border-2 border-dashed border-accent/40 p-8 shadow-sm text-center">
            <div className="inline-block bg-accent/10 text-accent text-xs font-bold px-3 py-1.5 rounded-full mb-6">
              {fr ? 'Phase de test' : 'Testing phase'}
            </div>

            <div className="mb-8 text-left max-w-sm mx-auto">
              <div className="text-xs font-bold text-accent uppercase tracking-widest mb-3">
                {fr ? 'Diag Complet + Repair' : 'Full Diag + Repair'}
              </div>
              <ul className="space-y-2">
                {(fr
                  ? ['Analyse revendication + données cliniques', 'Détection des écarts méthodologiques par dimension', 'Plan de correction structuré et priorisé', 'Export PDF du rapport complet']
                  : ['Claim + clinical data analysis', 'Methodological gap detection by dimension', 'Structured and prioritised correction plan', 'Full report PDF export']
                ).map((item, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-700">
                    <span className="text-accent font-bold mt-0.5 flex-shrink-0">✓</span> {item}
                  </li>
                ))}
              </ul>
            </div>

            <a
              href={`mailto:olivier@evidenceable.com?subject=${encodeURIComponent(fr ? 'Demande d’accès test — EvidenceAble' : 'Test access request — EvidenceAble')}`}
              className="inline-block text-center bg-accent hover:bg-accent/90 text-white px-8 py-3 rounded-xl font-semibold transition-colors shadow-md shadow-accent/20"
            >
              {fr ? 'Demander un accès gratuit →' : 'Request free access →'}
            </a>
            <p className="text-xs text-gray-400 mt-4">olivier@evidenceable.com</p>
          </Reveal>
        </div>
      </Reveal>

      <div className="max-w-xl mx-auto px-6 py-8">
        <NarrativeBeat>
          {fr
            ? 'Reste une chose à retenir avant de commencer.'
            : 'One thing remains to keep in mind before you begin.'}
        </NarrativeBeat>
      </div>

      {/* ── CLOSING ──────────────────────────────────────────────────────────── */}
      <Reveal as="section" className="py-20 px-6 bg-gradient-to-br from-primary to-primary-light text-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">
            {fr
              ? 'La plupart des études ne sont pas incorrectes.'
              : 'Most studies are not flawed.'}
          </h2>
          <p className="text-xl text-white/85 mb-6 leading-relaxed">
            {fr
              ? 'Elles ne sont simplement pas conçues pour démontrer la revendication qu\'elles sont censées soutenir.'
              : 'They are simply not designed to demonstrate the claim they are supposed to support.'}
          </p>
          <p className="text-white/60 mb-10 max-w-xl mx-auto text-sm leading-relaxed">
            {fr
              ? 'EvidenceAble vérifie cette démonstration avant que le problème ne devienne un risque de design.'
              : 'EvidenceAble verifies that demonstration before the problem becomes a design risk.'}
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link
              to="/repair"
              className="bg-accent hover:bg-accent/90 text-white px-8 py-3.5 rounded-xl font-semibold transition-colors shadow-lg shadow-accent/30 text-left"
            >
              <span className="block">{fr ? 'Diagnostic complet + Repair' : 'Full diagnosis + Repair'}</span>
              <span className="block text-xs text-white/60 font-normal mt-0.5">
                {fr ? 'Revendication + données cliniques' : 'Claim + clinical data'}
              </span>
            </Link>
          </div>
        </div>
      </Reveal>

      {/* ── FINAL CTA BANNER ─────────────────────────────────────────────────── */}
      <Reveal as="section" className="py-10 px-6 bg-primary/5">
        <div className="max-w-5xl mx-auto bg-white rounded-2xl border border-primary/10 shadow-sm px-6 py-6 flex flex-col md:flex-row items-center gap-5 justify-between">
          <div className="flex items-center gap-4 text-center md:text-left">
            <div className="w-11 h-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
              <RocketIcon className="w-6 h-6" />
            </div>
            <div>
              <p className="font-bold text-gray-800">
                {fr
                  ? 'Ne découvrez pas les limites de votre étude devant la HAS.'
                  : "Don't discover your study's limits in front of the HAS."}
              </p>
              <p className="text-sm text-gray-500">
                {fr
                  ? 'Vérifiez la capacité de démonstration de votre stratégie, dès maintenant.'
                  : "Check your evidence strategy's demonstration capacity, right now."}
              </p>
            </div>
          </div>
          <div className="text-center flex-shrink-0">
            <Link
              to="/repair"
              className="inline-block bg-primary hover:bg-primary-light text-white px-6 py-3 rounded-xl font-semibold transition-colors"
            >
              {fr ? 'Analyser mes données →' : 'Analyse my evidence →'}
            </Link>
            <p className="text-xs text-gray-400 mt-2">
              {fr ? 'Phase de test – Accès gratuit sur demande' : 'Testing phase – Free access on request'}
            </p>
          </div>
        </div>
        <p className="text-center text-xs text-gray-400 max-w-2xl mx-auto mt-8 leading-relaxed">
          {fr
            ? 'EvidenceAble n\'analyse pas les données brutes ni les résultats statistiques. Le moteur évalue la cohérence structurelle entre la revendication, les critères de jugement et le design d\'étude.'
            : 'EvidenceAble does not analyse raw data or statistical results. The engine evaluates the structural coherence between the claim, the endpoints and the study design.'}
        </p>
      </Reveal>

    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function AlignmentBadge({ color, label, sub }) {
  const colors = {
    green:  { dot: 'bg-green-500',  text: 'text-green-700',  bg: 'bg-green-50 border-green-200' },
    orange: { dot: 'bg-orange-400', text: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
    red:    { dot: 'bg-red-500',    text: 'text-red-700',    bg: 'bg-red-50 border-red-200' },
  }[color]
  return (
    <div className={`flex items-start gap-3 rounded-xl border px-4 py-4 flex-1 ${colors.bg}`}>
      <span className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${colors.dot}`} />
      <div>
        <p className={`font-semibold text-sm ${colors.text}`}>{label}</p>
        <p className="text-xs text-gray-500 mt-1 leading-relaxed">{sub}</p>
      </div>
    </div>
  )
}
