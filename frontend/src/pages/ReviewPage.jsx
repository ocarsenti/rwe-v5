import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLang } from '../LangContext'
import { t } from '../i18n'
import { CLAIM_LEVELS, CAUSAL_STRUCTURES, STUDY_DESIGNS, ENDPOINT_NATURES, CAUSAL_ROLES, MANIFOLD_REGIONS, label } from '../enumLabels'
import RadarChart from '../components/RadarChart'

export default function ReviewPage({ filterCases = null, repairPath = '/repair' }) {
  const { lang } = useLang()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    text: '',
    intervention: '',
    domain: '',
    endpoints_text: '',
  })
  const [result, setResult] = useState(null)
  const [parseInfo, setParseInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [goldClaims, setGoldClaims] = useState([])

  useEffect(() => {
    fetch('/api/gold-claims')
      .then((r) => r.json())
      .then((data) => setGoldClaims(filterCases ? data.filter((c) => filterCases.includes(c.case_id)) : data))
      .catch(() => {})
  }, [])

  const loadGoldCase = (caseId) => {
    const c = goldClaims.find((g) => g.case_id === caseId)
    if (c) {
      setForm({
        text: c.text,
        intervention: c.intervention,
        domain: c.domain,
        endpoints_text: c.endpoints.map((e) => `${e.name}: ${e.description}`).join('\n'),
      })
      setResult(null)
      setParseInfo(null)
    }
  }

  const submit = async () => {
    setLoading(true)
    setError(null)
    setParseInfo(null)
    try {
      const res = await fetch('/api/smart-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, lang }),
      })
      if (!res.ok) throw new Error(`${lang === 'fr' ? 'Erreur' : 'Error'} ${res.status}`)
      const data = await res.json()
      if (data._parse_info) setParseInfo(data._parse_info)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary">{t('review_title', lang)}</h1>
        <p className="text-gray-500 mt-2">{t('review_desc', lang)}</p>
      </div>

      {goldClaims.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          <span className="text-sm text-gray-500 self-center mr-2">{t('ref_cases_label', lang)}</span>
          {goldClaims.map((c) => (
            <button
              key={c.case_id}
              onClick={() => loadGoldCase(c.case_id)}
              className="px-3 py-1.5 text-sm bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors"
            >
              {c.case_id.replace('CASE_', '')}
            </button>
          ))}
        </div>
      )}

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-8">
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('field_claim', lang)}</label>
            <textarea
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              rows={4}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              placeholder={t('field_claim_placeholder', lang)}
            />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('field_intervention', lang)}
                <span className="text-gray-400 font-normal ml-1">{t('field_optional', lang)}</span>
              </label>
              <input
                value={form.intervention}
                onChange={(e) => setForm({ ...form, intervention: e.target.value })}
                className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                placeholder={t('field_intervention_placeholder', lang)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('field_domain', lang)}
                <span className="text-gray-400 font-normal ml-1">{t('field_optional', lang)}</span>
              </label>
              <input
                value={form.domain}
                onChange={(e) => setForm({ ...form, domain: e.target.value })}
                className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                placeholder={t('field_domain_placeholder', lang)}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('field_endpoints', lang)}
              <span className="text-gray-400 font-normal ml-1">{t('field_endpoints_hint', lang)}</span>
            </label>
            <textarea
              value={form.endpoints_text}
              onChange={(e) => setForm({ ...form, endpoints_text: e.target.value })}
              rows={3}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              placeholder={t('field_endpoints_placeholder', lang)}
            />
          </div>
        </div>
        <div className="mt-6 flex items-center gap-4">
          <button
            onClick={submit}
            disabled={loading || !form.text.trim()}
            className="bg-primary hover:bg-primary-light disabled:opacity-50 text-white px-8 py-3 rounded-xl font-semibold transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                {t('btn_analyzing', lang)}
              </>
            ) : (
              t('btn_analyze', lang)
            )}
          </button>
          <span className="text-xs text-gray-400">{t('ai_hint_review', lang)}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">{error}</div>
      )}

      {parseInfo && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
          <h4 className="text-sm font-semibold text-blue-800 mb-2">{t('parse_title', lang)}</h4>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs text-blue-700">
            <div><span className="font-medium block text-blue-500">{t('parse_intervention', lang)}</span>{parseInfo.intervention || '—'}</div>
            <div><span className="font-medium block text-blue-500">{t('parse_domain', lang)}</span>{parseInfo.domain || '—'}</div>
            <div><span className="font-medium block text-blue-500">{t('parse_level', lang)}</span>{label(CLAIM_LEVELS, parseInfo.claim_level, lang)}</div>
            <div><span className="font-medium block text-blue-500">{t('parse_endpoints_count', lang)}</span>{parseInfo.endpoints?.length || 0}</div>
          </div>
          {parseInfo.endpoints?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {parseInfo.endpoints.map((ep, i) => (
                <span key={i} className="bg-blue-100 text-blue-800 rounded-lg px-2 py-0.5 text-xs">{ep.name}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {result && <ReviewResults data={result} lang={lang} onUpgrade={() => navigate(repairPath)} />}
    </div>
  )
}

function ReviewResults({ data, lang, onUpgrade }) {
  const fr = lang === 'fr'

  const biasFlags = data.bias_flags || []
  const criticalCount = biasFlags.filter(f => f.severity === 'HIGH').length
  const mediumCount = biasFlags.filter(f => f.severity === 'MEDIUM').length
  const totalIssues = biasFlags.length

  const repairEngine = data.repair_engine
  const estimatedActions = repairEngine?.endpoint_repairs?.reduce(
    (acc, er) => acc + (er.repairs?.length || 0), 0
  ) ?? null
  const isRepairable = repairEngine?.status === 'REPAIRABLE'

  const riskLevel =
    criticalCount >= 2 ? 'CRITIQUE' :
    criticalCount >= 1 ? 'ÉLEVÉ' :
    mediumCount >= 2 ? 'MOYEN' : 'FAIBLE'

  const RISK_CONFIG = {
    CRITIQUE: { label: fr ? 'Non aligné — inférence causale limitée'    : 'Non-aligned — limited causal inference',        color: 'bg-red-100 text-red-800 border-red-200',    dot: 'bg-red-500' },
    ÉLEVÉ:    { label: fr ? 'Désalignement avec niveau de revendication' : 'Misalignment with claim level',                 color: 'bg-orange-100 text-orange-800 border-orange-200', dot: 'bg-orange-500' },
    MOYEN:    { label: fr ? 'Ajustement de design requis'                : 'Design adjustment required',                    color: 'bg-yellow-100 text-yellow-800 border-yellow-200', dot: 'bg-yellow-500' },
    FAIBLE:   { label: fr ? 'Écart mineur'                               : 'Minor gap',                                     color: 'bg-green-100 text-green-800 border-green-200',  dot: 'bg-green-500' },
  }
  const risk = RISK_CONFIG[riskLevel]

  const fullReadout = data.regulatory_readout || ''
  const sentences = fullReadout.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 10)
  const visibleReadout = sentences.slice(0, 2).join(' ')
  const blurredReadout = sentences.slice(2, 5).join(' ')
  const hasMoreReadout = sentences.length > 2

  return (
    <div className="space-y-6">

      {/* 4 summary cards */}
      <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard label={t('res_claim_level', lang)} value={label(CLAIM_LEVELS, data.claim_level, lang)} />
        <SummaryCard label={t('res_causal_structure', lang)} value={label(CAUSAL_STRUCTURES, data.causal_structure, lang)} />
        <SummaryCard label={t('res_design_rec', lang)} value={label(STUDY_DESIGNS, data.design_recommendation?.primary_design, lang)} />
        <div className={`rounded-2xl p-5 border ${risk.color}`}>
          <div className="text-xs uppercase tracking-wider mb-2 opacity-60">
            {fr ? 'Cohérence structurale' : 'Structural coherence'}
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full flex-shrink-0 ${risk.dot}`} />
            <div className="text-xl font-bold">{risk.label}</div>
          </div>
        </div>
      </div>

      {/* Regulatory readout — truncated + blurred remainder */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('res_regulatory', lang)}</h3>
        <p className="text-gray-600 text-sm leading-relaxed">{visibleReadout}</p>
        {hasMoreReadout && (
          <div className="relative mt-3">
            <p className="text-gray-400 text-sm leading-relaxed blur-sm select-none pointer-events-none">
              {blurredReadout}
            </p>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="bg-white/90 text-primary text-xs font-semibold px-4 py-1.5 rounded-full border border-primary/20 shadow-sm">
                {fr ? '🔒 Analyse complète dans le Diagnostic Complet' : '🔒 Full analysis in Full Diagnostic'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Issues detected — count + severity dots only */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">
          {fr ? 'Écarts détectés' : 'Gaps detected'}
        </h3>
        {totalIssues === 0 ? (
          <p className="text-green-700 text-sm font-medium">
            {fr ? 'Aucun problème majeur détecté.' : 'No major issues detected.'}
          </p>
        ) : (
          <div className="space-y-3">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-gray-900">{totalIssues}</span>
              <span className="text-gray-500 text-sm">
                {fr
                  ? `problème${totalIssues > 1 ? 's' : ''} identifié${totalIssues > 1 ? 's' : ''}${criticalCount > 0 ? ` · ${criticalCount} critique${criticalCount > 1 ? 's' : ''}` : ''}`
                  : `issue${totalIssues > 1 ? 's' : ''} identified${criticalCount > 0 ? ` · ${criticalCount} critical` : ''}`}
              </span>
            </div>
            <div className="flex gap-1.5 flex-wrap">
              {biasFlags.map((bf, i) => (
                <div
                  key={i}
                  title={fr ? 'Détail disponible dans le Diagnostic Complet' : 'Detail available in Full Diagnostic'}
                  className={`w-4 h-4 rounded-full cursor-default ${
                    bf.severity === 'HIGH' ? 'bg-red-500' :
                    bf.severity === 'MEDIUM' ? 'bg-yellow-500' : 'bg-blue-400'
                  }`}
                />
              ))}
            </div>
            <p className="text-xs text-gray-400 italic">
              {fr
                ? 'Le détail de chaque problème est disponible dans le Diagnostic Complet.'
                : 'Details of each issue are available in the Full Diagnostic.'}
            </p>
          </div>
        )}
      </div>

      {/* Endpoints — names + classification only, no flags */}
      {data.endpoint_analysis?.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('res_endpoints', lang)}</h3>
          <div className="space-y-2">
            {data.endpoint_analysis.map((ea, i) => (
              <div key={i} className="flex items-center justify-between bg-surface rounded-xl px-4 py-3 border border-gray-100">
                <span className="font-medium text-sm text-gray-800">{ea.name}</span>
                <span className="text-xs text-gray-400">
                  {label(ENDPOINT_NATURES, ea.nature, lang)} / {label(CAUSAL_ROLES, ea.causal_role, lang)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Epistemic radar — chart + position only, no repair directions */}
      {data.epistemic_manifold && (
        <div className="grid md:grid-cols-2 gap-6">
          <RadarChart coordinates={data.epistemic_manifold.coordinates} title={t('res_manifold', lang)} />
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('res_position', lang)}</h3>
            <div className="space-y-3">
              <InfoRow label={t('res_region', lang)} value={label(MANIFOLD_REGIONS, data.epistemic_manifold.region, lang)} />
              <InfoRow label={t('res_agg_score', lang)} value={data.epistemic_manifold.aggregate_score?.toFixed(3)} />
              <InfoRow label={t('res_bias_mag', lang)} value={data.epistemic_manifold.bias_magnitude?.toFixed(3)} />
              <InfoRow label={t('res_reg_status', lang)} value={data.epistemic_manifold.regulatory_status} />
            </div>
          </div>
        </div>
      )}

      {/* Premium teaser */}
      <div className="bg-gradient-to-br from-accent/5 to-primary/5 rounded-2xl border-2 border-dashed border-accent/30 p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-accent/10 rounded-xl flex items-center justify-center flex-shrink-0 mt-1">
            <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="font-bold text-gray-900 text-lg">
                {fr ? 'Diagnostic Complet disponible' : 'Full Diagnostic available'}
              </h3>
              <span className="bg-accent text-white text-xs font-bold px-2.5 py-1 rounded-full">Premium</span>
            </div>

            <div className="grid sm:grid-cols-3 gap-3 mb-4">
              {totalIssues > 0 && (
                <div className="bg-white rounded-xl p-3 border border-gray-100 text-center">
                  <div className="text-2xl font-bold text-gray-900">{totalIssues}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {fr ? 'gaps à analyser' : 'gaps to analyze'}
                  </div>
                </div>
              )}
              {estimatedActions !== null && estimatedActions > 0 && (
                <div className="bg-white rounded-xl p-3 border border-gray-100 text-center">
                  <div className="text-2xl font-bold text-gray-900">{estimatedActions}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {fr ? 'actions de correction' : 'correction actions'}
                  </div>
                </div>
              )}
              <div className="bg-white rounded-xl p-3 border border-gray-100 text-center">
                <div className={`text-sm font-bold ${isRepairable ? 'text-emerald-700' : 'text-orange-700'}`}>
                  {isRepairable
                    ? (fr ? 'Réparable' : 'Repairable')
                    : (fr ? 'Étude requise' : 'Study needed')}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {fr ? 'sans nouvelle étude' : 'without new study'}
                </div>
              </div>
            </div>

            <p className="text-sm text-gray-600 mb-4">
              {fr
                ? "Uploadez l'abstract de votre étude (PDF) pour identifier les incompatibilités structurelles entre votre étude et votre revendication, et obtenir un plan de correction priorisé par effort."
                : "Upload your study abstract (PDF) to identify structural incompatibilities between your study and claim, and get a correction plan prioritised by effort."}
            </p>

            <button
              onClick={onUpgrade}
              className="inline-flex items-center gap-2 bg-accent hover:bg-accent/90 text-white px-6 py-2.5 rounded-xl font-semibold text-sm transition-colors shadow-lg shadow-accent/20"
            >
              {fr ? 'Générer le Diagnostic Complet' : 'Generate Full Diagnostic'}
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>
        </div>
      </div>

    </div>
  )
}

function SummaryCard({ label, value }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-xl font-bold text-primary">{value || '—'}</div>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-800">{value}</span>
    </div>
  )
}
