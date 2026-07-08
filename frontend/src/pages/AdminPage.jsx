import { useState, useEffect } from 'react'

const ADMIN_SECRET = 'rwe-admin-2024'

const BASE = import.meta.env.BASE_URL.replace(/\/$/, '')
const SURFACE_PATHS = {
  main: `${BASE}/repair`,
  odysight: `${BASE}/odysight`,
  remedee: `${BASE}/remedee`,
}
const SURFACE_LABELS = {
  main: 'Site principal',
  odysight: 'Odysight',
  remedee: 'Remedee',
}

function api(path, opts = {}) {
  return fetch(path, {
    headers: { 'x-admin-secret': ADMIN_SECRET, 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  }).then((r) => r.json())
}

export default function AdminPage() {
  const [authed, setAuthed] = useState(false)
  const [pwd, setPwd] = useState('')
  const [guests, setGuests] = useState([])
  const [analytics, setAnalytics] = useState([])
  const [visitStats, setVisitStats] = useState(null)
  const [tab, setTab] = useState('guests')
  const [form, setForm] = useState({ name: '', email: '', quota: 10, days_valid: 30, note: '' })
  const [surface, setSurface] = useState('main')
  const [rowSurface, setRowSurface] = useState({})
  const [created, setCreated] = useState(null)
  const [loading, setLoading] = useState(false)

  const login = () => {
    if (pwd === ADMIN_SECRET) setAuthed(true)
    else alert('Mot de passe incorrect')
  }

  const load = () => {
    api('/api/admin/guests').then(setGuests)
    api('/api/admin/analytics').then(setAnalytics)
    api('/api/admin/visit-stats').then(setVisitStats)
  }

  useEffect(() => { if (authed) load() }, [authed])

  const createGuest = async () => {
    setLoading(true)
    const g = await api('/api/admin/guest', {
      method: 'POST',
      body: JSON.stringify({ ...form, quota: Number(form.quota), days_valid: Number(form.days_valid) }),
    })
    setCreated({ ...g, surface })
    setForm({ name: '', email: '', quota: 10, days_valid: 30, note: '' })
    load()
    setLoading(false)
  }

  const toggle = async (token, active) => {
    await api(`/api/admin/guest/${token}?active=${active}`, { method: 'PATCH' })
    load()
  }

  const adjustQuota = async (token, delta) => {
    await api(`/api/admin/guest/${token}/quota?delta=${delta}`, { method: 'PATCH' })
    load()
  }

  const demoUrl = (token, surf = 'main') => `${window.location.origin}${SURFACE_PATHS[surf] || SURFACE_PATHS.main}?token=${token}`

  const copyLink = (token, surf = 'main') => {
    const url = demoUrl(token, surf)
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => alert('Lien copié !')).catch(() => fallbackCopy(url))
    } else {
      fallbackCopy(url)
    }
  }

  const fallbackCopy = (text) => {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    alert('Lien copié !')
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 w-full max-w-sm">
          <h1 className="text-xl font-bold text-gray-900 mb-6">Admin EvidenceAble</h1>
          <input
            type="password"
            value={pwd}
            onChange={(e) => setPwd(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && login()}
            placeholder="Mot de passe"
            className="w-full border border-gray-200 rounded-xl px-4 py-2 mb-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            onClick={login}
            className="w-full bg-primary text-white rounded-xl py-2 text-sm font-semibold hover:bg-primary/90"
          >
            Connexion
          </button>
        </div>
      </div>
    )
  }

  const usageByToken = analytics.filter((e) => e.event === 'used').reduce((acc, e) => {
    acc[e.token] = (acc[e.token] || 0) + 1
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Admin EvidenceAble</h1>
          <div className="flex gap-2">
            {['guests', 'create', 'visits', 'analytics'].map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  tab === t ? 'bg-primary text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
                }`}
              >
                {{ guests: 'Accès', create: 'Créer', visits: 'Visites', analytics: 'Analytics' }[t]}
              </button>
            ))}
          </div>
        </div>

        {tab === 'guests' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  {['Nom', 'Email', 'Token', 'Quota', 'Utilisé', 'Restant', 'Expire', 'Statut', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wide font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {guests.length === 0 && (
                  <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Aucun accès créé</td></tr>
                )}
                {guests.map((g) => {
                  const expired = new Date(g.expires) < new Date()
                  const exhausted = g.used >= g.quota
                  const remaining = Math.max(0, g.quota - g.used)
                  return (
                    <tr key={g.token} className={!g.active ? 'opacity-50' : ''}>
                      <td className="px-4 py-3 font-medium">{g.name}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{g.email || '—'}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-400">{g.token}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => adjustQuota(g.token, -1)}
                            disabled={g.quota <= g.used}
                            className="w-6 h-6 rounded border border-gray-200 text-gray-500 hover:bg-gray-100 disabled:opacity-30 text-sm leading-none"
                          >−</button>
                          <span className="w-6 text-center font-medium">{g.quota}</span>
                          <button
                            onClick={() => adjustQuota(g.token, 1)}
                            className="w-6 h-6 rounded border border-gray-200 text-gray-500 hover:bg-gray-100 text-sm leading-none"
                          >+</button>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500">{g.used}</td>
                      <td className="px-4 py-3">
                        <span className={`font-semibold ${remaining === 0 ? 'text-red-600' : remaining <= 2 ? 'text-orange-500' : 'text-green-600'}`}>
                          {remaining}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        <span className={expired ? 'text-red-600' : ''}>{new Date(g.expires).toLocaleDateString('fr-FR')}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          !g.active ? 'bg-gray-100 text-gray-500' :
                          expired || exhausted ? 'bg-red-100 text-red-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {!g.active ? 'Désactivé' : expired ? 'Expiré' : exhausted ? 'Épuisé' : 'Actif'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <select
                            value={rowSurface[g.token] || 'main'}
                            onChange={(e) => setRowSurface({ ...rowSurface, [g.token]: e.target.value })}
                            className="text-xs border border-gray-200 rounded px-1 py-0.5 text-gray-600"
                          >
                            {Object.entries(SURFACE_LABELS).map(([key, label]) => (
                              <option key={key} value={key}>{label}</option>
                            ))}
                          </select>
                          <button
                            onClick={() => copyLink(g.token, rowSurface[g.token] || 'main')}
                            className="text-primary text-xs font-medium hover:underline"
                          >
                            Copier lien
                          </button>
                          <span className="text-gray-200">|</span>
                          <button
                            onClick={() => toggle(g.token, !g.active)}
                            className="text-xs text-gray-400 hover:text-gray-700"
                          >
                            {g.active ? 'Désactiver' : 'Activer'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'create' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 max-w-lg">
            <h2 className="font-semibold text-gray-900 mb-5">Créer un accès démo</h2>
            <div className="space-y-4">
              {[
                { key: 'name', label: 'Nom / Organisation', placeholder: 'Tilak Healthcare' },
                { key: 'email', label: 'Email (optionnel)', placeholder: 'ceo@tilak.io' },
                { key: 'note', label: 'Note (optionnelle)', placeholder: 'CEO demo Odysight' },
              ].map(({ key, label, placeholder }) => (
                <div key={key}>
                  <label className="block text-xs text-gray-500 mb-1">{label}</label>
                  <input
                    value={form[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    placeholder={placeholder}
                    className="w-full border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
              ))}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Quota d'analyses</label>
                  <input
                    type="number" min={1} max={100}
                    value={form.quota}
                    onChange={(e) => setForm({ ...form, quota: e.target.value })}
                    className="w-full border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Validité (jours)</label>
                  <input
                    type="number" min={1} max={365}
                    value={form.days_valid}
                    onChange={(e) => setForm({ ...form, days_valid: e.target.value })}
                    className="w-full border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Destination du lien</label>
                <select
                  value={surface}
                  onChange={(e) => setSurface(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                >
                  {Object.entries(SURFACE_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={createGuest}
                disabled={!form.name || loading}
                className="w-full bg-primary text-white rounded-xl py-2.5 text-sm font-semibold hover:bg-primary/90 disabled:opacity-50"
              >
                {loading ? 'Création...' : 'Créer l\'accès'}
              </button>
            </div>

            {created && (
              <div className="mt-6 bg-green-50 border border-green-200 rounded-xl p-4">
                <p className="text-sm font-semibold text-green-800 mb-2">Accès créé — {created.name}</p>
                <p className="text-xs text-gray-500 mb-1">Token : <code className="font-mono">{created.token}</code></p>
                <p className="text-xs text-gray-500 mb-1">Destination : {SURFACE_LABELS[created.surface] || SURFACE_LABELS.main}</p>
                <div className="flex items-center gap-2 mt-2">
                  <input
                    readOnly
                    value={demoUrl(created.token, created.surface)}
                    className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 font-mono bg-white"
                  />
                  <button
                    onClick={() => copyLink(created.token, created.surface)}
                    className="text-xs bg-primary text-white px-3 py-1.5 rounded-lg hover:bg-primary/90"
                  >
                    Copier
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'visits' && (
          <div className="space-y-6">
            {!visitStats ? (
              <div className="text-gray-400 text-sm">Chargement…</div>
            ) : (
              <>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                    <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Vues totales</div>
                    <div className="text-3xl font-bold text-gray-900">{visitStats.total}</div>
                  </div>
                  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                    <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Aujourd'hui</div>
                    <div className="text-3xl font-bold text-gray-900">{visitStats.today}</div>
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-50">
                    <h2 className="font-semibold text-gray-900">Vues par page</h2>
                  </div>
                  <div className="divide-y divide-gray-50">
                    {Object.entries(visitStats.by_path).map(([path, count]) => (
                      <div key={path} className="px-6 py-3 flex items-center justify-between text-sm">
                        <span className="font-mono text-gray-600">{path}</span>
                        <span className="font-bold text-gray-900">{count}</span>
                      </div>
                    ))}
                    {Object.keys(visitStats.by_path).length === 0 && (
                      <div className="px-6 py-8 text-center text-gray-400 text-sm">Aucune vue enregistrée</div>
                    )}
                  </div>
                </div>

                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                  <h2 className="font-semibold text-gray-900 mb-4">14 derniers jours</h2>
                  {visitStats.by_day.length === 0 ? (
                    <div className="text-center text-gray-400 text-sm py-4">Aucune donnée</div>
                  ) : (
                    <div className="flex items-end gap-2 h-32">
                      {visitStats.by_day.map(({ date, count }) => {
                        const max = Math.max(...visitStats.by_day.map((d) => d.count), 1)
                        return (
                          <div key={date} className="flex-1 flex flex-col items-center gap-1">
                            <div
                              className="w-full bg-accent/70 rounded-t"
                              style={{ height: `${Math.max(4, (count / max) * 96)}px` }}
                              title={`${date} : ${count}`}
                            />
                            <span className="text-[9px] text-gray-400 rotate-0">{date.slice(5)}</span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-400 italic">
                  Compteur de vues de page (pas de visiteurs uniques) — chaque navigation compte, y compris les rechargements.
                </p>
              </>
            )}
          </div>
        )}

        {tab === 'analytics' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-50">
              <h2 className="font-semibold text-gray-900">Journal d'utilisation</h2>
              <p className="text-xs text-gray-400 mt-0.5">{analytics.length} événements enregistrés</p>
            </div>
            <div className="divide-y divide-gray-50 max-h-[60vh] overflow-y-auto">
              {[...analytics].reverse().map((e, i) => (
                <div key={i} className="px-6 py-3 flex items-center gap-4 text-xs">
                  <span className="text-gray-400 font-mono w-40 flex-shrink-0">{new Date(e.ts).toLocaleString('fr-FR')}</span>
                  <span className={`px-2 py-0.5 rounded font-medium ${
                    e.event === 'used' ? 'bg-blue-50 text-blue-700' :
                    e.event === 'created' ? 'bg-green-50 text-green-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{e.event}</span>
                  <span className="font-mono text-gray-400">{e.token}</span>
                  {e.name && <span className="text-gray-600">{e.name}</span>}
                  {e.used !== undefined && <span className="text-gray-500">{e.used}/{e.quota}</span>}
                </div>
              ))}
              {analytics.length === 0 && (
                <div className="px-6 py-8 text-center text-gray-400">Aucune activité</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
