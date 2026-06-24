import { useState, useEffect } from 'react'
import { useLang } from '../LangContext'
import { t } from '../i18n'
import RadarChart from '../components/RadarChart'
import BiasDisplay from '../components/BiasDisplay'

export default function ReviewPage() {
  const { lang } = useLang()
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
      .then(setGoldClaims)
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
            <div><span className="font-medium block text-blue-500">{t('parse_level', lang)}</span>{parseInfo.claim_level || '—'}</div>
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

      {result && <ReviewResults data={result} lang={lang} />}
    </div>
  )
}

function ReviewResults({ data, lang }) {
  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <SummaryCard label={t('res_claim_level', lang)} value={data.claim_level} />
        <SummaryCard label={t('res_causal_structure', lang)} value={data.causal_structure} />
        <SummaryCard label={t('res_design_rec', lang)} value={data.design_recommendation?.primary_design} />
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('res_regulatory', lang)}</h3>
        <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-line">{data.regulatory_readout}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('res_bias', lang)}</h3>
          <BiasDisplay biasFlags={data.bias_flags} lang={lang} />
        </div>
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('res_endpoints', lang)}</h3>
          <div className="space-y-3">
            {data.endpoint_analysis?.map((ea, i) => (
              <div key={i} className="bg-surface rounded-xl p-3 border border-gray-100">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm text-gray-800">{ea.name}</span>
                  <span className="text-xs text-gray-500">{ea.nature} / {ea.causal_role}</span>
                </div>
                {ea.flags?.length > 0 && (
                  <div className="flex gap-1 mt-2">
                    {ea.flags.map((f, j) => (
                      <span key={j} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">{f}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {data.epistemic_manifold && (
        <div className="grid md:grid-cols-2 gap-6">
          <RadarChart coordinates={data.epistemic_manifold.coordinates} title={t('res_manifold', lang)} />
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('res_position', lang)}</h3>
            <div className="space-y-3">
              <InfoRow label={t('res_region', lang)} value={data.epistemic_manifold.region} />
              <InfoRow label={t('res_agg_score', lang)} value={data.epistemic_manifold.aggregate_score?.toFixed(3)} />
              <InfoRow label={t('res_bias_mag', lang)} value={data.epistemic_manifold.bias_magnitude?.toFixed(3)} />
              <InfoRow label={t('res_reg_status', lang)} value={data.epistemic_manifold.regulatory_status} />
            </div>
            {data.epistemic_manifold.repair_directions?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">{t('res_repair_dirs', lang)}</h4>
                {data.epistemic_manifold.repair_directions.map((r, i) => (
                  <div key={i} className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">{r.axis}</span>: {r.current?.toFixed(2)} &rarr; {r.target?.toFixed(2)} ({r.action})
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {data.repair_engine && data.repair_engine.status !== 'NO_REPAIR_NEEDED' && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            {t('res_repair_engine', lang)}
            <span className={`ml-3 text-sm px-3 py-1 rounded-full ${
              data.repair_engine.status === 'REPAIRABLE' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
            }`}>{data.repair_engine.status}</span>
          </h3>
          <p className="text-gray-600 text-sm mb-4">{data.repair_engine.problem_summary}</p>
          {data.repair_engine.endpoint_repairs?.map((er, i) => (
            <div key={i} className="bg-surface rounded-xl p-4 mb-3 border border-gray-100">
              <div className="font-medium text-sm text-gray-800 mb-1">{er.original_endpoint} &mdash; {er.failure_reason}</div>
              <div className="space-y-1">
                {er.repairs?.map((r, j) => (
                  <div key={j} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-success">&#10003;</span>
                    <span><strong>{r.endpoint}</strong> ({r.type}) &mdash; {r.why_valid}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {data.repair_manifold_delta && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            {t('res_repair_delta', lang)}: {data.repair_manifold_delta.region_before} &rarr; {data.repair_manifold_delta.region_after}
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            <RadarChart coordinates={data.repair_manifold_delta.before} title={t('res_before', lang)} />
            <RadarChart coordinates={data.repair_manifold_delta.after} title={t('res_after', lang)} />
          </div>
        </div>
      )}
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
