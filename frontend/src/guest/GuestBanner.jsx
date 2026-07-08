import { useGuest } from './GuestContext'
import { useLang } from '../LangContext'

export default function GuestBanner() {
  const { quota, error } = useGuest() || {}
  const { lang } = useLang()
  const fr = lang === 'fr'

  if (error) {
    const msg = {
      token_invalid:   fr ? 'Lien d\'accès invalide.'        : 'Invalid access link.',
      token_expired:   fr ? 'Accès expiré.'                  : 'Access expired.',
      token_disabled:  fr ? 'Accès désactivé.'               : 'Access disabled.',
      quota_exhausted: fr ? 'Quota d\'analyses épuisé.'      : 'Analysis quota exhausted.',
      token_required:  fr ? 'Accès sur demande.'             : 'Access on request.',
    }[error] || (fr ? 'Erreur d\'accès.' : 'Access error.')
    return (
      <div className="bg-red-50 border-b border-red-200 px-6 py-2 text-sm text-red-700 text-center print:hidden">
        ⚠ {msg}
      </div>
    )
  }

  if (!quota) return null

  const pct = Math.round((quota.remaining / quota.quota) * 100)
  const color = pct > 50 ? 'bg-green-500' : pct > 20 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="bg-primary/5 border-b border-primary/10 px-6 py-2 flex items-center justify-between text-xs text-gray-600 print:hidden">
      <span>
        {fr ? 'Accès démo' : 'Demo access'} — <strong>{quota.name}</strong>
      </span>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div className="w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
          </div>
          <span className="font-medium">
            {quota.remaining}/{quota.quota} {fr ? 'analyses restantes' : 'analyses remaining'}
          </span>
        </div>
        <span className="text-gray-400">
          {fr ? 'Expire le' : 'Expires'} {new Date(quota.expires).toLocaleDateString('fr-FR')}
        </span>
      </div>
    </div>
  )
}
