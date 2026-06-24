import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { LangProvider, useLang } from './LangContext'
import { t } from './i18n'
import Landing from './pages/Landing'
import ReviewPage from './pages/ReviewPage'
import DesignPage from './pages/DesignPage'
import GoldPage from './pages/GoldPage'

function Navbar() {
  const { pathname } = useLocation()
  const { lang, setLang } = useLang()

  const NAV_ITEMS = [
    { path: '/', label: t('nav_home', lang) },
    { path: '/review', label: t('nav_review', lang) },
    { path: '/design', label: t('nav_design', lang) },
    { path: '/gold', label: t('nav_gold', lang) },
  ]

  return (
    <nav className="bg-primary text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold tracking-tight">
          <span className="text-accent">Epi</span>Strat
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {NAV_ITEMS.map(({ path, label }) => (
              <Link
                key={path}
                to={path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  pathname === path
                    ? 'bg-white/20 text-white'
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="flex bg-white/10 rounded-lg overflow-hidden ml-2">
            <button
              onClick={() => setLang('fr')}
              className={`px-2.5 py-1.5 text-xs font-bold transition-colors ${
                lang === 'fr' ? 'bg-accent text-white' : 'text-white/60 hover:text-white'
              }`}
            >
              FR
            </button>
            <button
              onClick={() => setLang('en')}
              className={`px-2.5 py-1.5 text-xs font-bold transition-colors ${
                lang === 'en' ? 'bg-accent text-white' : 'text-white/60 hover:text-white'
              }`}
            >
              EN
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <LangProvider>
      <div className="min-h-screen bg-surface">
        <Navbar />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/design" element={<DesignPage />} />
          <Route path="/gold" element={<GoldPage />} />
        </Routes>
        <footer className="bg-primary text-white/60 text-center py-6 text-sm mt-auto">
          EpiStrat
        </footer>
      </div>
    </LangProvider>
  )
}
