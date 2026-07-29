import { useState } from 'react'
import { CAS_REELS } from '../data/casReels'

// ── Petits composants d'UI ────────────────────────────────────────────────────

function VerdictBadge({ verdict }) {
  const tones = {
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    red: 'bg-red-50 text-red-700 border-red-200',
  }
  return (
    <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full border ${tones[verdict.tone]}`}>
      {verdict.label}
    </span>
  )
}

function StatusMark({ status }) {
  const map = {
    hit: { icon: '✓', className: 'bg-emerald-100 text-emerald-700' },
    miss: { icon: '✕', className: 'bg-red-100 text-red-600' },
    partial: { icon: '≈', className: 'bg-amber-100 text-amber-700' },
  }
  const { icon, className } = map[status]
  return (
    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-sm font-bold flex-shrink-0 ${className}`}>
      {icon}
    </span>
  )
}

function SignalLevelTag({ level }) {
  const colors = {
    HIGH: 'bg-red-100 text-red-700',
    MEDIUM: 'bg-amber-100 text-amber-700',
    MODERATE: 'bg-amber-100 text-amber-700',
    LOW: 'bg-slate-100 text-slate-600',
    'FERMÉ': 'bg-emerald-100 text-emerald-700',
  }
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full tracking-wide ${colors[level] || 'bg-slate-100 text-slate-600'}`}>
      {level}
    </span>
  )
}

// ── Détail : format "grid" (DIZG DBM, WALRUS) ────────────────────────────────

function GridDetail({ cas }) {
  return (
    <div className="space-y-6">
      <p className="text-gray-600 leading-relaxed">{cas.volume}</p>

      <div className="space-y-3">
        {cas.mechanisms.map((m) => (
          <div key={m.code} className="border border-gray-100 rounded-xl p-4 bg-surface">
            <div className="flex items-center gap-2 mb-2">
              <StatusMark status={m.status} />
              <span className="text-xs font-mono text-gray-400">{m.code}</span>
              <span className="font-semibold text-gray-800 text-sm">{m.label}</span>
            </div>
            <div className="grid sm:grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-[10px] font-bold text-primary/60 tracking-wide mb-1">MOTEUR</p>
                <p className="text-gray-600 leading-relaxed">{m.moteur}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-primary/60 tracking-wide mb-1">HAS</p>
                <p className="text-gray-600 leading-relaxed italic">{m.has}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 italic">{cas.outOfScope}</p>

      <div className="bg-primary/5 border border-primary/10 rounded-xl p-4">
        <p className="text-sm text-gray-700 leading-relaxed">{cas.outcome}</p>
      </div>
    </div>
  )
}

// ── Détail : format "deck" (INFINITY, POPPINS) ───────────────────────────────

function DeckSection({ section }) {
  return (
    <div className="border-t border-gray-100 pt-6 first:border-t-0 first:pt-0">
      <p className="text-[11px] font-bold text-accent tracking-wide mb-1">{section.tag}</p>
      <h4 className="font-semibold text-gray-800 mb-3">{section.title}</h4>

      {section.body && !section.flow && <p className="text-sm text-gray-600 leading-relaxed mb-3">{section.body}</p>}

      {section.quotes && (
        <div className="space-y-2 mb-2">
          {section.quotes.map((q, i) => (
            <div key={i} className="bg-surface border-l-2 border-accent/40 rounded-r-lg p-3 text-sm">
              <p className="text-gray-600 italic leading-relaxed">« {q.text} »</p>
              <p className="text-[10px] text-gray-400 mt-1 uppercase tracking-wide">{q.source}</p>
            </div>
          ))}
        </div>
      )}

      {section.flow && (
        <div className="space-y-1.5 mb-4">
          {section.flow.map((step, i) => {
            const isLast = i === section.flow.length - 1
            return (
              <div key={i}>
                <div className={`rounded-lg px-4 py-2.5 text-sm text-center ${
                  isLast ? 'bg-red-50 text-red-700 font-semibold border border-red-200' : 'bg-surface text-gray-600'
                }`}>
                  {step}
                </div>
                {!isLast && <div className="text-center text-gray-300 text-xs py-0.5">↓</div>}
              </div>
            )
          })}
        </div>
      )}
      {section.body && section.flow && <p className="text-sm text-gray-600 leading-relaxed">{section.body}</p>}

      {section.table && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <tbody>
              {section.table.map((row, i) => (
                <tr key={i} className={i === 0 ? 'font-semibold text-gray-700' : 'text-gray-600'}>
                  {row.map((cell, j) => (
                    <td key={j} className="border-t border-gray-100 py-2 pr-4 align-top">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {section.flatSignals && (
        <div className="space-y-2">
          {section.flatSignals.map((s, i) => (
            <div key={i} className="bg-surface rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <SignalLevelTag level={s.level} />
                <span className="text-sm font-medium text-gray-800">{s.label}</span>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      )}

      {section.signals2020 && (
        <div className="grid sm:grid-cols-2 gap-4">
          {['2020', '2025'].map((year, idx) => (
            <div key={year}>
              <p className="text-xs font-bold text-gray-500 mb-2">{year}</p>
              <div className="space-y-2">
                {(idx === 0 ? section.signals2020 : section.signals2025).map((s, i) => (
                  <div key={i} className="bg-surface rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <SignalLevelTag level={s.level} />
                      <span className="text-xs font-medium text-gray-800">{s.label}</span>
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed">{s.body}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {section.alignment && (
        <div className="space-y-3">
          {section.alignment.map((a, i) => (
            <div key={i} className="grid sm:grid-cols-2 gap-3 text-sm">
              <div className="bg-surface rounded-lg p-3">
                <p className="text-[10px] font-bold text-gray-400 tracking-wide mb-1">HAS, AVIS RÉEL</p>
                <p className="text-gray-600 italic leading-relaxed">{a.has}</p>
              </div>
              <div className="bg-accent/5 rounded-lg p-3">
                <p className="text-[10px] font-bold text-accent tracking-wide mb-1">MOTEUR</p>
                <p className="text-gray-600 leading-relaxed">{a.moteur}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {section.repairs && (
        <ul className="space-y-2 list-none">
          {section.repairs.map((r, i) => (
            <li key={i} className="text-sm text-gray-600 leading-relaxed flex gap-2">
              <span className="text-accent font-bold flex-shrink-0">{String(i + 1).padStart(2, '0')}</span>
              {r}
            </li>
          ))}
        </ul>
      )}
      {section.note && <p className="text-xs text-gray-400 italic mt-3">{section.note}</p>}
    </div>
  )
}

function DeckDetail({ cas }) {
  return <div className="space-y-6">{cas.sections.map((s, i) => <DeckSection key={i} section={s} />)}</div>
}

// ── Card ──────────────────────────────────────────────────────────────────────

function CaseCard({ cas, expanded, onToggle }) {
  return (
    <div className={`bg-white rounded-2xl border border-gray-100 shadow-sm transition-all ${expanded ? 'md:col-span-2' : ''}`}>
      <div className="p-6">
        <div className="flex items-start justify-between gap-3 mb-3">
          <span className="text-xs font-bold text-gray-400">CAS RÉEL · {cas.n}</span>
          <VerdictBadge verdict={cas.verdict} />
        </div>
        <h3 className="text-2xl font-bold text-primary mb-1">{cas.title}</h3>
        <p className="text-sm text-gray-500 mb-3 leading-relaxed">{cas.subtitle}</p>
        <p className="text-xs text-gray-400 mb-4">{cas.dossier}</p>

        <div className="bg-surface rounded-lg p-3 mb-5">
          <p className="text-sm text-gray-600 italic leading-relaxed">{cas.hook}</p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={onToggle}
            className="bg-primary hover:bg-primary-light text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors"
          >
            {expanded ? 'Réduire' : "Voir l'analyse"}
          </button>
          {cas.downloadUrl && (
            <a
              href={cas.downloadUrl}
              download
              className="bg-accent/10 hover:bg-accent/20 text-accent px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors"
            >
              ↓ Télécharger le PDF
            </a>
          )}
          {cas.viewUrl && (
            <a
              href={cas.viewUrl}
              target="_blank"
              rel="noreferrer"
              className="bg-accent/10 hover:bg-accent/20 text-accent px-5 py-2.5 rounded-xl font-semibold text-sm transition-colors"
            >
              ↗ Voir le post original
            </a>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 p-6 bg-surface/50 rounded-b-2xl">
          {cas.format === 'grid' ? <GridDetail cas={cas} /> : <DeckDetail cas={cas} />}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CasReels() {
  const [openSlug, setOpenSlug] = useState(null)

  return (
    <div>
      {/* HERO */}
      <section className="bg-gradient-to-br from-primary to-primary-light text-white py-20 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(255,255,255,0.05)_0%,transparent_50%)]" />
        <div className="max-w-3xl mx-auto text-center relative">
          <div className="inline-block bg-white/10 rounded-full px-4 py-1.5 text-sm font-medium mb-8 backdrop-blur-sm">
            Série CNEDiMTS · Dossiers publics rejoués par le moteur
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-5 leading-tight">
            Cas réels
          </h1>
          <p className="text-lg text-white/85 leading-relaxed max-w-2xl mx-auto">
            {CAS_REELS.length} dossiers CNEDiMTS publics, rejoués fait par fait par le moteur —
            sans jamais lui donner la conclusion de la HAS. Le résultat est comparé,
            mécanisme par mécanisme, à l'avis réel.
          </p>
        </div>
      </section>

      {/* GRID */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-6">
          {CAS_REELS.map((cas) => (
            <CaseCard
              key={cas.slug}
              cas={cas}
              expanded={openSlug === cas.slug}
              onToggle={() => setOpenSlug(openSlug === cas.slug ? null : cas.slug)}
            />
          ))}
        </div>
      </section>

      {/* CLOSING */}
      <section className="py-16 px-6 bg-gradient-to-br from-primary to-primary-light text-white">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-bold mb-3">D'autres dossiers, avec la même grille.</h2>
          <p className="text-white/70 text-sm">La série continue — nouveaux cas ajoutés au fil de l'eau.</p>
        </div>
      </section>
    </div>
  )
}
