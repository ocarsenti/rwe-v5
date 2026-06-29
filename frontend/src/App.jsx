import { Routes, Route, Link, useLocation, Outlet } from 'react-router-dom'
import { LangProvider, useLang } from './LangContext'
import { GuestProvider } from './guest/GuestContext'
import Landing from './pages/Landing'
import LandingOdysight from './pages/LandingOdysight'
import OdysightLayout from './pages/OdysightLayout'
import LandingRemedee from './pages/LandingRemedee'
import RemedeeLayout from './pages/RemedeeLayout'
import ReviewPage from './pages/ReviewPage'
import DesignPage from './pages/DesignPage'
import GoldPage from './pages/GoldPage'
import RepairPage from './pages/RepairPage'
import AdminPage from './pages/AdminPage'

function Navbar() {
  const { pathname } = useLocation()
  const { lang, setLang } = useLang()

  const NAV_ITEMS = [
    { path: '/', label: lang === 'fr' ? 'Accueil' : 'Home' },
    { path: '/review', label: lang === 'fr' ? 'Diagnostic' : 'Diagnostic' },
    { path: '/repair', label: lang === 'fr' ? 'Diag. Complet' : 'Full Diag.', premium: true },
    { path: '/design', label: 'Design' },
    { path: '/gold', label: lang === 'fr' ? 'Cas référence' : 'Reference cases' },
  ]

  return (
    <nav className="bg-primary text-white shadow-lg sticky top-0 z-50 print:hidden">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold tracking-tight flex-shrink-0">
          <span className="text-accent">Epi</span>Strat
        </Link>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {NAV_ITEMS.map(({ path, label, premium }) => (
              <Link
                key={path}
                to={path}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                  pathname === path
                    ? 'bg-white/20 text-white'
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`}
              >
                {label}
                {premium && (
                  <span className="bg-accent text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">
                    P
                  </span>
                )}
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
  )
}

function MainLayout() {
  return (
    <div className="min-h-screen bg-surface">
      <Navbar />
      <Outlet />
      <footer className="bg-primary text-white/60 text-center py-6 text-sm mt-auto print:hidden">
        EpiStrat
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <LangProvider>
      <div className="min-h-screen bg-surface">
        <Routes>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/repair" element={<RepairPage />} />
            <Route path="/design" element={<DesignPage />} />
            <Route path="/gold" element={<GoldPage />} />
          </Route>
          <Route path="/odysight" element={<GuestProvider><OdysightLayout /></GuestProvider>}>
            <Route index element={<LandingOdysight />} />
            <Route path="review" element={<ReviewPage filterCases={['CASE_ODYSIGHT']} repairPath="/odysight/repair" />} />
            <Route path="repair" element={<RepairPage />} />
          </Route>
          <Route path="/remedee" element={<GuestProvider><RemedeeLayout /></GuestProvider>}>
            <Route index element={<LandingRemedee />} />
            <Route path="review" element={<ReviewPage filterCases={['CASE_REMEDEE']} repairPath="/remedee/repair" />} />
            <Route path="repair" element={<RepairPage />} />
          </Route>
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </div>
    </LangProvider>
  )
}
