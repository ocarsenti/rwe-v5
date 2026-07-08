import { Outlet, Link, useLocation } from 'react-router-dom'
import { useLang } from '../LangContext'
import GuestBanner from '../guest/GuestBanner'
import evidenceableWordmark from '../assets/evidenceable-wordmark-compact.png'

export default function RemedeeLayout() {
  const { pathname } = useLocation()
  const { lang, setLang } = useLang()

  const NAV_ITEMS = [
    { path: '/remedee', label: lang === 'fr' ? 'Accueil' : 'Home' },
    { path: '/remedee/review', label: lang === 'fr' ? 'Diag. rapide' : 'Quick Diag.' },
    { path: '/remedee/repair', label: 'Diag + Repair' },
  ]

  return (
    <>
      <nav className="bg-primary text-white shadow-lg sticky top-0 z-50 print:hidden">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/remedee" className="flex-shrink-0 bg-white rounded-md px-2.5 py-1.5 flex items-center">
            <img src={evidenceableWordmark} alt="EvidenceAble" className="h-7 w-auto" />
          </Link>
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {NAV_ITEMS.map(({ path, label }) => (
                <Link
                  key={path}
                  to={path}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                    pathname === path
                      ? 'bg-white/20 text-white'
                      : 'text-white/70 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {label}
                </Link>
              ))}
            </div>
            <div className="flex bg-white/10 rounded-lg overflow-hidden ml-1 flex-shrink-0">
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
      <GuestBanner />
      <Outlet />
      <footer className="bg-primary text-white/60 text-center py-6 text-sm mt-auto print:hidden">
        EvidenceAble
      </footer>
    </>
  )
}
