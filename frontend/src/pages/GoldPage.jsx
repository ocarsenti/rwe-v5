import { useState, useEffect } from 'react'
import { useLang } from '../LangContext'
import { t } from '../i18n'
import { REGULATORY_STATUS, ISSUE_TYPES, ENDPOINT_STATUS, REGULATORY_STRENGTH, REPAIR_EP_TYPES, label } from '../enumLabels'

const STATUS_COLORS = {
  ACCEPTABLE_PRIMARY_WITH_CONDITIONS: 'bg-green-100 text-green-800',
  ACCEPTABLE_SECONDARY_ONLY: 'bg-blue-100 text-blue-800',
  ACCEPTABLE_WITH_REDESIGN: 'bg-yellow-100 text-yellow-800',
  INVALID_AS_PRIMARY_ENDPOINT_ONLY: 'bg-red-100 text-red-800',
  REJECTED_UNLESS_EXTERNAL_VALIDATION: 'bg-red-200 text-red-900',
}

const CASE_NAMES = {
  CASE_ODYSIGHT: { name: 'OdySight', domain: { fr: 'Ophtalmologie', en: 'Ophthalmology' }, icon: '👁️' },
  CASE_MOOVCARE: { name: 'Moovcare', domain: { fr: 'Oncologie', en: 'Oncology' }, icon: '🫁' },
  CASE_REMEDEE: { name: 'Remedee', domain: { fr: 'Douleur chronique', en: 'Chronic pain' }, icon: '⌚' },
  CASE_AI_TRIAGE_AVC: { name: 'AI Triage AVC', domain: { fr: 'Neurologie urgence', en: 'Emergency neurology' }, icon: '🧠' },
}

export default function GoldPage() {
  const { lang } = useLang()
  const [cases, setCases] = useState([])
  const [dataset, setDataset] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeCase, setActiveCase] = useState(null)
  const [tab, setTab] = useState('cases')

  useEffect(() => {
    Promise.all([
      fetch('/api/gold-cases').then((r) => r.json()),
      fetch('/api/gold-dataset').then((r) => r.json()),
    ])
      .then(([c, d]) => {
        setCases(c)
        setDataset(d)
        if (c.length > 0) setActiveCase(c[0].case_id)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary">{t('gold_title', lang)}</h1>
        <p className="text-gray-500 mt-2">{t('gold_desc', lang)}</p>
      </div>

      <div className="flex gap-2 mb-8">
        <button
          onClick={() => setTab('cases')}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
            tab === 'cases' ? 'bg-primary text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
          }`}
        >{t('gold_tab_cases', lang)}</button>
        <button
          onClick={() => setTab('table')}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
            tab === 'table' ? 'bg-primary text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
          }`}
        >{t('gold_tab_table', lang)}</button>
      </div>

      {tab === 'cases' ? (
        <>
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            {cases.map((c) => {
              const meta = CASE_NAMES[c.case_id] || { name: c.case_id, domain: { fr: '', en: '' }, icon: '📄' }
              return (
                <button
                  key={c.case_id}
                  onClick={() => setActiveCase(c.case_id)}
                  className={`p-4 rounded-2xl text-left transition-all ${
                    activeCase === c.case_id
                      ? 'bg-primary text-white shadow-lg scale-[1.02]'
                      : 'bg-white text-gray-700 border border-gray-100 hover:shadow-md'
                  }`}
                >
                  <div className="text-2xl mb-2">{meta.icon}</div>
                  <div className="font-bold">{meta.name}</div>
                  <div className={`text-sm ${activeCase === c.case_id ? 'text-white/70' : 'text-gray-500'}`}>
                    {meta.domain[lang]}
                  </div>
                </button>
              )
            })}
          </div>
          {activeCase && <CaseDetail data={cases.find((c) => c.case_id === activeCase)} lang={lang} />}
        </>
      ) : (
        <DatasetTable data={dataset} lang={lang} />
      )}
    </div>
  )
}

function CaseDetail({ data, lang }) {
  if (!data) return null
  const meta = CASE_NAMES[data.case_id] || {}

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">{meta.name || data.case_id}</h2>
            <p className="text-gray-500 text-sm mt-1">{data.device_context?.name} &mdash; {data.device_context?.domain}</p>
          </div>
          <span className={`px-4 py-2 rounded-xl text-sm font-semibold ${STATUS_COLORS[data.final_regulatory_status] || 'bg-gray-100'}`}>
            {label(REGULATORY_STATUS, data.final_regulatory_status, lang)}
          </span>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('gold_causal_graph', lang)}</h3>
          <p className="text-gray-600 text-sm mb-3">{data.causal_graph?.summary}</p>
          {data.causal_graph?.mediators?.length > 0 && (
            <div className="mb-2">
              <span className="text-xs text-gray-500 uppercase">{t('gold_mediators', lang)}</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {data.causal_graph.mediators.map((m, i) => (
                  <span key={i} className="bg-yellow-50 text-yellow-800 rounded-lg px-2 py-0.5 text-xs">{m}</span>
                ))}
              </div>
            </div>
          )}
          {data.causal_graph?.measurement_influence_paths?.length > 0 && (
            <div>
              <span className="text-xs text-gray-500 uppercase">{t('gold_influence', lang)}</span>
              <div className="space-y-1 mt-1">
                {data.causal_graph.measurement_influence_paths.map((p, i) => (
                  <div key={i} className="text-xs text-red-600 bg-red-50 rounded-lg px-2 py-1">{p}</div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('gold_issue', lang)}</h3>
          <div className="bg-surface rounded-xl p-4 border border-gray-100">
            <div className="text-sm font-medium text-gray-800">{label(ISSUE_TYPES, data.issue_detection?.primary_issue_type, lang)}</div>
            <div className="mt-2">
              <span className="text-xs text-gray-500">{t('gold_severity', lang)}</span>
              <div className="w-full h-3 bg-gray-200 rounded-full mt-1 overflow-hidden">
                <div className={`h-full rounded-full ${data.issue_detection?.severity_score > 0.7 ? 'bg-red-500' : 'bg-yellow-500'}`}
                  style={{ width: `${(data.issue_detection?.severity_score || 0) * 100}%` }} />
              </div>
              <div className="text-xs text-gray-500 mt-1">{(data.issue_detection?.severity_score * 100).toFixed(0)}%</div>
            </div>
          </div>
        </div>
      </div>

      {data.endpoint_analyses?.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">{t('gold_ep_analysis', lang)}</h3>
          <div className="space-y-4">
            {data.endpoint_analyses.map((ea, i) => (
              <div key={i} className="bg-surface rounded-xl p-4 border border-gray-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-800">{ea.original_endpoint?.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    ea.original_endpoint?.status === 'ACCEPTABLE' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>{label(ENDPOINT_STATUS, ea.original_endpoint?.status, lang)}</span>
                </div>
                <p className="text-xs text-gray-500 mb-3">{ea.original_endpoint?.failure_mode}</p>
                {ea.repair_endpoints?.length > 0 && (
                  <div>
                    <span className="text-xs text-gray-500 uppercase">{t('gold_repair_eps', lang)}</span>
                    <div className="grid sm:grid-cols-2 gap-2 mt-1">
                      {ea.repair_endpoints.map((r, j) => (
                        <div key={j} className="bg-white rounded-lg p-2 border border-gray-100 text-sm">
                          <div className="font-medium text-gray-700">{r.endpoint_name}</div>
                          <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>{label(REPAIR_EP_TYPES, r.type, lang)}</span><span>{label(REGULATORY_STRENGTH, r.regulatory_strength, lang)}</span>
                          </div>
                          <div className="w-full h-1.5 bg-gray-200 rounded-full mt-1 overflow-hidden">
                            <div className="h-full bg-green-500 rounded-full" style={{ width: `${r.robustness_score * 100}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-gradient-to-br from-primary to-primary-light text-white rounded-2xl p-6">
        <h3 className="text-lg font-semibold mb-3">{t('gold_has_interp', lang)}</h3>
        <p className="text-white/90 text-sm leading-relaxed">{data.has_interpretation}</p>
      </div>
    </div>
  )
}

function DatasetTable({ data, lang }) {
  if (!data || data.length === 0) return null

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left">
              <th className="px-4 py-3 font-medium text-gray-600">{t('gold_col_device', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600">{t('gold_col_original', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600">{t('gold_col_failure', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600 text-center">{t('gold_col_severity', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600">{t('gold_col_primary', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600">{t('gold_col_design', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600">{t('gold_col_best', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600">{t('gold_col_risk', lang)}</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-t border-gray-50 hover:bg-gray-50/50">
                <td className="px-4 py-3 font-medium">{row.device}</td>
                <td className="px-4 py-3 text-gray-600">{row.original_endpoint}</td>
                <td className="px-4 py-3"><span className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded-full">{row.failure_type}</span></td>
                <td className="px-4 py-3 text-center">
                  <div className="w-12 h-2 bg-gray-200 rounded-full overflow-hidden mx-auto">
                    <div className={`h-full rounded-full ${row.severity > 0.7 ? 'bg-red-500' : 'bg-yellow-500'}`} style={{ width: `${row.severity * 100}%` }} />
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">{row.acceptable_primary}</td>
                <td className="px-4 py-3 text-gray-600 text-xs">{row.required_design}</td>
                <td className="px-4 py-3 text-gray-600 text-xs">{row.best_repair_endpoint}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    row.regulatory_risk_level === 'high' ? 'bg-red-100 text-red-700'
                      : row.regulatory_risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                  }`}>{row.regulatory_risk_level}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
