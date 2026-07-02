import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useLang } from '../LangContext'
import { t } from '../i18n'
import { CLAIM_LEVELS, MANIFOLD_REGIONS, label } from '../enumLabels'
import RadarChart from '../components/RadarChart'
import DesignTable from '../components/DesignTable'

const EXAMPLES_DATA = [
  {
    fr: { label: 'Monitoring ophtalmique', text: "Notre dispositif de monitoring visuel à distance améliore le suivi de la dégénérescence maculaire en détectant plus tôt les dégradations de l'acuité visuelle." },
    en: { label: 'Ophthalmic monitoring', text: "Our remote visual monitoring device improves macular degeneration follow-up by detecting visual acuity degradation earlier." },
  },
  {
    fr: { label: 'Suivi oncologique', text: "Notre application de suivi des symptômes en oncologie améliore la survie des patients grâce à la détection précoce des rechutes par alertes automatiques aux médecins." },
    en: { label: 'Oncology follow-up', text: "Our oncology symptom tracking app improves patient survival through early relapse detection via automatic physician alerts." },
  },
  {
    fr: { label: 'Neurostimulation douleur', text: "Notre bracelet de neurostimulation par ondes millimétriques réduit la douleur chronique en déclenchant la libération d'endorphines." },
    en: { label: 'Pain neurostimulation', text: "Our millimeter-wave neurostimulation wristband reduces chronic pain by triggering endorphin release." },
  },
]

export default function DesignPage() {
  const { lang } = useLang()
  const location = useLocation()
  const [form, setForm] = useState({ text: '', intervention: '', domain: '' })
  const [result, setResult] = useState(null)
  const [parseInfo, setParseInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [fromCAS, setFromCAS] = useState(false)

  useEffect(() => {
    if (location.state?.fromCAS) {
      const s = location.state
      setForm({
        text: s.claim_text || '',
        intervention: s.intervention || '',
        domain: s.domain || '',
      })
      setFromCAS(true)
    }
  }, [location.state])

  const examples = EXAMPLES_DATA.map((e) => e[lang])

  const loadExample = (ex) => {
    setForm({ text: ex.text, intervention: '', domain: '' })
    setResult(null)
    setParseInfo(null)
  }

  const submit = async () => {
    setLoading(true)
    setError(null)
    setParseInfo(null)
    try {
      const res = await fetch('/api/smart-design', {
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
        <h1 className="text-3xl font-bold text-accent">{t('design_title', lang)}</h1>
        <p className="text-gray-500 mt-2">{t('design_desc', lang)}</p>
      </div>

      {fromCAS && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-800 text-sm font-medium">
            {lang === 'fr'
              ? 'Le CAS a identifié un problème d\'alignement étude ↔ revendication. Utilisez le mode DESIGN pour concevoir une stratégie d\'évidence qui corrige ces écarts.'
              : 'CAS identified a study ↔ claim alignment issue. Use DESIGN mode to build an evidence strategy that addresses these gaps.'}
          </p>
        </div>
      )}

      <div className="mb-6 flex flex-wrap gap-2">
        <span className="text-sm text-gray-500 self-center mr-2">{t('examples_label', lang)}</span>
        {examples.map((ex, i) => (
          <button
            key={i}
            onClick={() => loadExample(ex)}
            className="px-3 py-1.5 text-sm bg-accent/10 text-accent rounded-lg hover:bg-accent/20 transition-colors"
          >
            {ex.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-8">
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('field_claim', lang)}</label>
            <textarea
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              rows={4}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              placeholder={t('field_design_claim_placeholder', lang)}
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
                className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
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
                className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder={t('field_domain_placeholder', lang)}
              />
            </div>
          </div>
        </div>
        <div className="mt-6 flex items-center gap-4">
          <button
            onClick={submit}
            disabled={loading || !form.text.trim()}
            className="bg-accent hover:bg-accent-light disabled:opacity-50 text-white px-8 py-3 rounded-xl font-semibold transition-colors flex items-center gap-2"
          >
            {loading ? (
              <><span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />{t('btn_generating', lang)}</>
            ) : t('btn_generate', lang)}
          </button>
          <span className="text-xs text-gray-400">{t('ai_hint_design', lang)}</span>
        </div>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">{error}</div>}

      {parseInfo && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-6">
          <h4 className="text-sm font-semibold text-orange-800 mb-2">{t('parse_title', lang)}</h4>
          <div className="grid sm:grid-cols-3 gap-3 text-xs text-orange-700">
            <div><span className="font-medium block text-orange-500">{t('parse_intervention', lang)}</span>{parseInfo.intervention || '—'}</div>
            <div><span className="font-medium block text-orange-500">{t('parse_domain', lang)}</span>{parseInfo.domain || '—'}</div>
            <div><span className="font-medium block text-orange-500">{t('parse_level', lang)}</span>{label(CLAIM_LEVELS, parseInfo.claim_level, lang)}</div>
          </div>
        </div>
      )}

      {result && <DesignResults data={result} lang={lang} />}
    </div>
  )
}

function DesignResults({ data, lang }) {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('res_id_conditions', lang)}</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <ConditionBadge label={t('res_randomization', lang)} active={data.identification?.randomization_needed} lang={lang} />
          <ConditionBadge label={t('res_blinding', lang)} active={data.identification?.blinding_needed} lang={lang} />
          <ConditionBadge label={t('res_adjudication', lang)} active={data.identification?.adjudication_needed} lang={lang} />
          <ConditionBadge label={t('res_ext_data', lang)} active={data.identification?.external_data_needed} lang={lang} />
          <ConditionBadge label={t('res_mediator_meas', lang)} active={data.identification?.mediator_measurement_needed} lang={lang} />
          <div className="bg-surface rounded-xl p-3 border border-gray-100">
            <div className="text-xs text-gray-500">{t('res_min_strength', lang)}</div>
            <div className="text-lg font-bold text-primary">{data.identification?.minimum_design_strength?.toFixed(2)}</div>
          </div>
        </div>
      </div>

      {data.target_dag && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('res_causal_target', lang)}</h3>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <div className="text-xs text-gray-500 uppercase mb-2">{t('res_intervention', lang)}</div>
              <div className="bg-primary/10 text-primary rounded-xl px-4 py-2 text-sm font-medium">{data.target_dag.intervention}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase mb-2">{t('res_mediators', lang)}</div>
              <div className="space-y-1">
                {data.target_dag.mediators?.map((m, i) => (
                  <div key={i} className="bg-yellow-50 text-yellow-800 rounded-lg px-3 py-1.5 text-sm">{m}</div>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase mb-2">{t('res_outcomes', lang)}</div>
              <div className="space-y-1">
                {data.target_dag.outcomes?.map((o, i) => (
                  <div key={i} className="bg-green-50 text-green-800 rounded-lg px-3 py-1.5 text-sm">{o}</div>
                ))}
              </div>
            </div>
          </div>
          {data.target_dag.prohibited_outcomes?.length > 0 && (
            <div className="mt-4">
              <div className="text-xs text-gray-500 uppercase mb-2">{t('res_prohibited', lang)}</div>
              <div className="flex flex-wrap gap-1">
                {data.target_dag.prohibited_outcomes.map((p, i) => (
                  <span key={i} className="bg-red-50 text-red-700 rounded-lg px-3 py-1 text-sm">{p}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {data.endpoint_families?.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('res_ep_families', lang)}</h3>
          <div className="grid md:grid-cols-2 gap-4">
            {data.endpoint_families.map((f, i) => (
              <div key={i} className="bg-surface rounded-xl p-4 border border-gray-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm text-gray-800">{f.family_name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    f.regulatory_weight === 'PRIMARY' ? 'bg-green-100 text-green-700'
                      : f.regulatory_weight === 'SECONDARY' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                  }`}>{f.regulatory_weight}</span>
                </div>
                <div className="text-xs text-gray-500 mb-2">{t('res_independence', lang)}: {(f.independence_from_device * 100).toFixed(0)}%</div>
                <div className="flex flex-wrap gap-1">
                  {f.endpoints?.map((ep, j) => (
                    <span key={j} className="bg-white text-gray-700 rounded-md px-2 py-0.5 text-xs border">{ep}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <DesignTable manifoldPoints={data.regulatory_manifold?.points} lang={lang} />

      {data.epistemic_manifold?.optimal_design && (
        <div className="grid md:grid-cols-2 gap-6">
          <RadarChart
            coordinates={data.epistemic_manifold.optimal_design.coordinates}
            title={`${t('res_optimal_design', lang)}: ${data.epistemic_manifold.recommended_design_name}`}
          />
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('res_feasible', lang)}</h3>
            {data.epistemic_manifold.feasible_region && (
              <div className="space-y-2 text-sm">
                <InfoRow label={`${t('res_independence', lang)} outcome min.`} value={data.epistemic_manifold.feasible_region.min_outcome_independence} />
                <InfoRow label={`${t('res_randomization', lang)} min.`} value={data.epistemic_manifold.feasible_region.min_randomization_strength} />
                <p className="text-gray-500 mt-3 text-xs">{data.epistemic_manifold.feasible_region.description}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {data.regulatory_strategy && (
        <div className="bg-gradient-to-br from-primary to-primary-light text-white rounded-2xl p-6">
          <h3 className="text-lg font-semibold mb-3">{t('res_reg_strategy', lang)}</h3>
          <pre className="text-sm text-white/90 whitespace-pre-wrap font-sans leading-relaxed">{data.regulatory_strategy}</pre>
        </div>
      )}
    </div>
  )
}

function ConditionBadge({ label, active, lang }) {
  return (
    <div className={`rounded-xl p-3 border text-sm ${active ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-green-700'}`}>
      <span className="font-medium">{active ? t('res_required', lang) : t('res_not_required', lang)}</span>
      <div className="text-xs mt-0.5 opacity-70">{label}</div>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between"><span className="text-gray-500">{label}</span><span className="font-medium text-gray-800">{value}</span></div>
  )
}
