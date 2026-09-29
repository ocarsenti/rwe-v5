import gelule from '../assets/gelule.png'
import captureConnecteur from '../assets/connecteur-claude.webp'
import Wordmark from '../components/Wordmark'

// Page d'accueil d'evidenceable.com depuis le 2026-09-29 : base de précédents de la Commission de la Transparence (connecteur « Précédents HAS »).
// Pas de chiffres de volume affichés tant que la base est petite (décision du 2026-09-29).
const MAILTO = `mailto:oliviercarsenti@yahoo.fr?subject=${encodeURIComponent('Précédents HAS — demande de démonstration')}`

const SOURCES = [
  {
    titre: 'Avis publiés',
    texte: 'SMR, ASMR, ISP, comparateurs, population cible et, surtout, les motifs que la Commission a retenus pour justifier sa décision.',
  },
  {
    titre: 'Débats de séance',
    texte: 'Les transcriptions publiques découpées en arguments : ce qui a été objecté, sur quel angle, et par qui (membre, expert externe, HAS, laboratoire).',
  },
  {
    titre: 'Votes',
    texte: 'Les décomptes de chaque vote (SMR, ASMR, ISP, alignement), relus à la main dans les transcriptions.',
  },
]

const APPORTS = [
  {
    titre: 'Qui a dit quoi',
    texte: 'Un membre qui vote, un expert externe, un représentant de la HAS ou le laboratoire auditionné : le rôle est écrit dans chaque argument, sans nom.',
  },
  {
    titre: 'Rangé par classe et par thème',
    texte: 'Les arguments sont regroupés par sens à l’intérieur d’une classe ATC : une objection sur les gliptines n’est jamais mêlée à une autre classe.',
  },
  {
    titre: 'L’évolution dans le temps',
    texte: 'Séances dans l’ordre chronologique : ce qui revient à chaque dossier, ce qui a changé, et les votes qui ont suivi.',
  },
  {
    titre: 'Sourcé',
    texte: 'Chaque réponse renvoie aux transcriptions et aux avis publiés sur has-sante.fr, pour vérifier avant de s’en servir.',
  },
]

const ETAPES = [
  { n: '1', titre: 'Connecter', texte: 'Le connecteur « Précédents HAS » s’ajoute en quelques minutes à votre assistant d’IA : Claude, ou tout outil compatible avec les connecteurs MCP, le standard ouvert. Une clé propre à votre équipe.' },
  { n: '2', titre: 'Demander', texte: 'Vous continuez à travailler dans votre outil, sur vos propres documents, et vous posez vos questions comme à un collègue : « Quelles objections la Commission a-t-elle faites sur cette classe ? »' },
  { n: '3', titre: 'Lire', texte: 'Votre assistant lit le débat complet, les votes et les motifs des avis, puis répond en citant ses sources.' },
]

const CONFIDENTIALITE = [
  'Mode fermé par défaut : votre assistant n’envoie au serveur que des termes publics (une classe, une aire, un produit déjà évalué). Jamais votre dossier.',
  'Aucune IA côté serveur : de simples lectures dans une base de documents publics.',
  'Vos questions ne sont ni enregistrées ni journalisées.',
  'Intervenants anonymisés : seul leur rôle est donné.',
]

function BoutonDemo({ className = '' }) {
  return (
    <a
      href={MAILTO}
      className={`inline-flex items-center justify-center rounded-lg bg-accent px-5 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-[#146636] ${className}`}
    >
      Demander une démonstration
    </a>
  )
}

function Section({ id, surtitre, titre, children, fond = 'bg-white' }) {
  return (
    <section id={id} className={`${fond} px-4 py-16 sm:px-6 sm:py-20`}>
      <div className="mx-auto max-w-5xl">
        {surtitre && <p className="text-sm font-semibold uppercase tracking-wide text-accent">{surtitre}</p>}
        {titre && <h2 className="mt-2 text-2xl font-bold text-primary sm:text-3xl">{titre}</h2>}
        <div className="mt-8">{children}</div>
      </div>
    </section>
  )
}

export default function LandingPrecedents() {
  return (
    <div className="min-h-screen bg-surface text-gray-800">
      <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <a href="/" className="flex min-w-0 items-center gap-2">
            <img src={gelule} alt="" className="h-8 w-8 flex-shrink-0" />
            <Wordmark className="text-xl sm:text-2xl" />
          </a>
          <a
            href={MAILTO}
            className="flex-shrink-0 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-light sm:px-4"
          >
            Nous écrire
          </a>
        </div>
      </header>

      <section className="bg-primary px-4 pb-20 pt-16 text-white sm:px-6 sm:pt-24">
        <div className="mx-auto grid max-w-5xl items-center gap-10 lg:grid-cols-[1fr_minmax(0,420px)]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-accent-light">Précédents HAS · un connecteur pour votre outil d’IA</p>
            <h1 className="mt-4 text-3xl font-bold leading-tight sm:text-5xl">
              Ce que la Commission de la Transparence a dit, voté et retenu.
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-white/80">
              Les avis publiés, les débats de séance et les votes, réunis dans une base que vous interrogez depuis vos outils d&apos;IA préférés,
              sans en changer : un connecteur la branche directement sur votre assistant. Pour préparer un dossier à partir de ce que la Commission a réellement
              objecté, et non d&apos;impressions.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <BoutonDemo />
              <a
                href="#exemple"
                className="inline-flex items-center justify-center rounded-lg border border-white/30 px-5 py-3 font-semibold text-white transition-colors hover:bg-white/10"
              >
                Voir un exemple
              </a>
            </div>
          </div>
          <figure className="mx-auto w-full max-w-[420px]">
            <img
              src={captureConnecteur}
              alt="Dans Claude, le connecteur « Précédents HAS » activé dans le menu Connecteurs, et une réponse qui l'utilise."
              className="w-full rounded-xl border border-white/20 shadow-2xl"
              loading="eager"
            />
            <figcaption className="mt-3 text-center text-sm text-white/70">
              Le connecteur « Précédents HAS », activé dans Claude en un clic.
            </figcaption>
          </figure>
        </div>
      </section>

      <Section surtitre="Trois sources publiques, reliées" titre="La décision, et le débat qui l'a précédée" fond="bg-surface">
        <div className="grid gap-4 md:grid-cols-3">
          {SOURCES.map(s => (
            <div key={s.titre} className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="font-semibold text-primary">{s.titre}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{s.texte}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section surtitre="Ce que vous obtenez" titre="Des précédents exploitables, pas une pile de PDF">
        <div className="grid gap-x-10 gap-y-8 sm:grid-cols-2">
          {APPORTS.map(a => (
            <div key={a.titre} className="border-l-4 border-accent pl-4">
              <h3 className="font-semibold text-primary">{a.titre}</h3>
              <p className="mt-1 text-sm leading-relaxed text-gray-600">{a.texte}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section id="exemple" surtitre="Exemple" titre="L'évolution de la Commission sur les CAR-T" fond="bg-surface">
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div className="border-b border-gray-200 bg-gray-50 px-5 py-4 sm:px-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Question posée à Claude</p>
            <p className="mt-1 text-gray-800">
              « Nous préparons l&apos;évaluation d&apos;une thérapie cellulaire CAR-T. Comment la position de la Commission a-t-elle évolué au fil des dossiers,
              et qu&apos;est-ce que cela implique pour notre dossier ? »
            </p>
          </div>
          <div className="space-y-4 px-5 py-5 text-sm leading-relaxed text-gray-700 sm:px-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Extraits de la réponse</p>
            <p>
              « En 2018, la Commission a fait un pari sur l&apos;innovation ; en 2022, elle a exigé une démonstration comparative. »
            </p>
            <p>
              « L&apos;écart entre patients inclus et patients traités est l&apos;objection la plus constante. En 2018, un membre de la Commission estimait que les
              non-perfusés auraient dû compter comme des échecs. En 2022, un représentant HAS formulait la règle ainsi : “le traitement débute dès l&apos;aphérèse”. »
            </p>
            <p>
              « Les votes : KYMRIAH en 2018, SMR important et ASMR III (13 voix) ; CARVYKTI en 2022, alignement sur ABECMA à l&apos;unanimité, ASMR V. »
            </p>
          </div>
          <div className="border-t border-gray-200 bg-accent/5 px-5 py-4 text-sm text-gray-700 sm:px-6">
            <strong>Testé à l&apos;aveugle</strong> sur des questions ouvertes de client : chaque réponse est notée sur une grille de faits vérifiés dans les transcriptions. Sur cette question, 9,5 éléments sur 10 retrouvés, aucune erreur factuelle.
          </div>
        </div>
      </Section>

      <Section surtitre="Comment ça marche" titre="Sans changer d'outil : la base vient à votre IA">
        <ol className="grid gap-6 md:grid-cols-3">
          {ETAPES.map(e => (
            <li key={e.n} className="flex gap-4">
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-primary font-bold text-white">{e.n}</span>
              <div>
                <h3 className="font-semibold text-primary">{e.titre}</h3>
                <p className="mt-1 text-sm leading-relaxed text-gray-600">{e.texte}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section surtitre="Confidentialité" titre="Votre dossier reste chez vous" fond="bg-surface">
        <ul className="grid gap-3 sm:grid-cols-2">
          {CONFIDENTIALITE.map(t => (
            <li key={t} className="flex gap-3 rounded-lg border border-gray-200 bg-white p-4 text-sm leading-relaxed text-gray-700">
              <span className="mt-0.5 text-accent" aria-hidden="true">✓</span>
              <span>{t}</span>
            </li>
          ))}
        </ul>
        <p className="mt-6 text-sm text-muted">
          Les arguments reflètent ce qui a été dit en séance, pas nécessairement la position finale de la Commission : ce sont des précédents, pas une doctrine.
        </p>
      </Section>

      <section className="bg-primary px-4 py-16 text-center text-white sm:px-6">
        <div className="mx-auto max-w-2xl">
          <img src={gelule} alt="" className="mx-auto h-14 w-14" />
          <h2 className="mt-4 text-2xl font-bold sm:text-3xl">Voir ce que la base dit de votre classe thérapeutique</h2>
          <p className="mt-3 text-white/80">Une démonstration sur une aire ou une classe de votre choix, à partir des précédents publics.</p>
          <BoutonDemo className="mt-8" />
        </div>
      </section>

      <footer className="bg-primary px-4 pb-8 text-center text-xs text-white/50 sm:px-6">
        <p>EvidenceAble — service indépendant, non affilié à la Haute Autorité de Santé.</p>
        <p className="mt-1">Sources : avis et transcriptions de séance publiés sur has-sante.fr.</p>
      </footer>
    </div>
  )
}
