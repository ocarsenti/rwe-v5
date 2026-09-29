import { useEffect } from 'react'
import { Routes, Route, Link, useLocation, Outlet } from 'react-router-dom'
import { LangProvider, useLang } from './LangContext'
import { GuestProvider } from './guest/GuestContext'
import GuestBanner from './guest/GuestBanner'
import LandingPrecedents from './pages/LandingPrecedents'
import CasReels from './pages/CasReels'
import LandingOdysight from './pages/LandingOdysight'
import OdysightLayout from './pages/OdysightLayout'
import LandingRemedee from './pages/LandingRemedee'
import RemedeeLayout from './pages/RemedeeLayout'
import ReviewPage from './pages/ReviewPage'
import DesignPage from './pages/DesignPage'
import GoldPage from './pages/GoldPage'
import RepairPage from './pages/RepairPage'
import AdminPage from './pages/AdminPage'
import Wordmark from './components/Wordmark'

function Navbar() {
  const { pathname } = useLocation()
  const { lang, setLang } = useLang()

  const NAV_ITEMS = [
    { path: '/cas-reels', label: 'Cas réels' },
    { path: '/repair', label: 'Diag + Repair', premium: true },
  ]

  return (
    <nav className="bg-primary text-white shadow-lg sticky top-0 z-50 print:hidden">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <Link to="/" className="flex-shrink-0 bg-white rounded-md px-2.5 py-1.5 flex items-center">
          <Wordmark className="text-xl" />
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
        EvidenceAble
      </footer>
    </div>
  )
}

function VisitTracker() {
  const location = useLocation()

  useEffect(() => {
    if (location.pathname.startsWith('/admin')) return
    fetch('/api/track-visit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: location.pathname }),
    }).catch(() => {})
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'page_view', {
        page_path: location.pathname,
        page_location: window.location.href,
        page_title: document.title,
      })
    }
  }, [location.pathname])

  return null
}

export default function App() {
  return (
    <LangProvider>
      <div className="min-h-screen bg-surface">
        <VisitTracker />
        <Routes>
          <Route path="/" element={<LandingPrecedents />} />
          <Route element={<MainLayout />}>
            <Route path="/cas-reels" element={<CasReels />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/repair" element={<GuestProvider><GuestBanner /><RepairPage /></GuestProvider>} />
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
