import { Link } from 'react-router-dom'
import { useLang } from '../LangContext'
import { t } from '../i18n'

const ICONS = ['🔬', '🛡️', '📐', '🔧', '📋', '🎯']

export default function Landing() {
  const { lang } = useLang()

  const features = [1, 2, 3, 4, 5, 6].map((n) => {
    const [title, desc] = t(`feat_${n}`, lang)
    return { icon: ICONS[n - 1], title, desc }
  })

  const problems = [
    { title: t('why_1_title', lang), text: t('why_1_text', lang) },
    { title: t('why_2_title', lang), text: t('why_2_text', lang) },
    { title: t('why_3_title', lang), text: t('why_3_text', lang) },
  ]

  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-primary to-primary-light text-white py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block bg-white/10 rounded-full px-4 py-1 text-sm font-medium mb-6 backdrop-blur-sm">
            {t('hero_badge', lang)}
          </div>
          <h1 className="text-5xl font-bold mb-3 leading-tight">
            <span className="text-accent">Epi</span>Strat
          </h1>
          <p className="text-base text-white/50 mb-6 tracking-wide">
            {t('hero_subtitle', lang)}
          </p>
          <p className="text-xl text-white/80 mb-4 max-w-3xl mx-auto">
            {t('hero_desc', lang)}
          </p>
          <p className="text-lg text-white/60 mb-10 max-w-2xl mx-auto">
            {t('hero_tagline', lang)}
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link
              to="/review"
              className="bg-accent hover:bg-accent-light text-white px-8 py-3 rounded-xl font-semibold text-lg transition-colors shadow-lg"
            >
              {t('hero_cta_review', lang)}
            </Link>
            <Link
              to="/design"
              className="bg-white/10 hover:bg-white/20 text-white px-8 py-3 rounded-xl font-semibold text-lg transition-colors backdrop-blur-sm border border-white/20"
            >
              {t('hero_cta_design', lang)}
            </Link>
          </div>
        </div>
      </section>

      {/* Why */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-primary text-center mb-12">
            {t('why_title', lang)}
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {problems.map((p, i) => (
              <div key={i} className="bg-surface rounded-2xl p-6 border border-gray-100">
                <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary font-bold mb-4">
                  {i + 1}
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">{p.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{p.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Two modes */}
      <section className="py-16 px-6 bg-surface">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-primary text-center mb-12">
            {t('two_modes_title', lang)}
          </h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
              <div className="text-4xl mb-4">🔍</div>
              <h3 className="text-2xl font-bold text-primary mb-3">REVIEW</h3>
              <p className="text-gray-500 text-sm font-medium mb-4">{t('review_subtitle', lang)}</p>
              <ul className="text-gray-600 text-sm space-y-2 text-left">
                {t('review_items', lang).map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-success font-bold">&#10003;</span> {item}
                  </li>
                ))}
              </ul>
              <Link
                to="/review"
                className="mt-6 inline-block bg-primary hover:bg-primary-light text-white px-6 py-2.5 rounded-xl font-medium transition-colors"
              >
                {t('review_cta', lang)}
              </Link>
            </div>
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
              <div className="text-4xl mb-4">🏗️</div>
              <h3 className="text-2xl font-bold text-accent mb-3">DESIGN</h3>
              <p className="text-gray-500 text-sm font-medium mb-4">{t('design_subtitle', lang)}</p>
              <ul className="text-gray-600 text-sm space-y-2 text-left">
                {t('design_items', lang).map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-accent font-bold">&#10003;</span> {item}
                  </li>
                ))}
              </ul>
              <Link
                to="/design"
                className="mt-6 inline-block bg-accent hover:bg-accent-light text-white px-6 py-2.5 rounded-xl font-medium transition-colors"
              >
                {t('design_cta', lang)}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-primary text-center mb-12">
            {t('features_title', lang)}
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div key={i} className="bg-surface rounded-2xl p-6 border border-gray-100 hover:shadow-md transition-shadow">
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">{f.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Gold teaser */}
      <section className="py-16 px-6 bg-gradient-to-br from-primary to-primary-light text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">{t('gold_teaser_title', lang)}</h2>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { name: 'OdySight', domain: lang === 'fr' ? 'Ophtalmologie' : 'Ophthalmology', issue: t('case_odysight', lang) },
              { name: 'Moovcare', domain: lang === 'fr' ? 'Oncologie' : 'Oncology', issue: t('case_moovcare', lang) },
              { name: 'Remedee', domain: lang === 'fr' ? 'Douleur' : 'Pain', issue: t('case_remedee', lang) },
              { name: 'AI Triage AVC', domain: lang === 'fr' ? 'Neurologie urgence' : 'Emergency neurology', issue: t('case_aitriage', lang) },
            ].map((c, i) => (
              <div key={i} className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                <div className="font-bold text-lg">{c.name}</div>
                <div className="text-white/60 text-sm">{c.domain}</div>
                <div className="text-accent text-xs mt-2">{c.issue}</div>
              </div>
            ))}
          </div>
          <Link
            to="/gold"
            className="bg-white text-primary hover:bg-gray-100 px-8 py-3 rounded-xl font-semibold transition-colors"
          >
            {t('gold_teaser_cta', lang)}
          </Link>
        </div>
      </section>
    </div>
  )
}
