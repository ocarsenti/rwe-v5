import { t } from '../i18n'

export default function DesignTable({ manifoldPoints, lang = 'fr' }) {
  if (!manifoldPoints || manifoldPoints.length === 0) return null

  const sorted = [...manifoldPoints].sort(
    (a, b) => b.regulatory_acceptability - a.regulatory_acceptability,
  )

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800">{t('res_reg_manifold', lang)}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left">
              <th className="px-4 py-3 font-medium text-gray-600">{t('res_design_col', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600 text-center">{t('res_identification', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600 text-center">{t('res_bias_risk', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600 text-center">{t('res_complexity', lang)}</th>
              <th className="px-4 py-3 font-medium text-gray-600 text-center">{t('res_has_accept', lang)}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p, i) => (
              <tr key={i} className={`border-t border-gray-50 ${i === 0 ? 'bg-green-50' : ''}`}>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-800">{p.design}</div>
                  <div className="text-xs text-gray-500">{p.design_type}</div>
                </td>
                <td className="px-4 py-3 text-center"><ScoreBar value={p.identification_score} color="blue" /></td>
                <td className="px-4 py-3 text-center"><ScoreBar value={p.bias_risk} color="red" inverted /></td>
                <td className="px-4 py-3 text-center"><ScoreBar value={p.operational_complexity} color="yellow" inverted /></td>
                <td className="px-4 py-3 text-center"><ScoreBar value={p.regulatory_acceptability} color="green" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ScoreBar({ value, color, inverted = false }) {
  const pct = Math.round(value * 100)
  const colors = { blue: 'bg-blue-500', red: 'bg-red-500', yellow: 'bg-yellow-500', green: 'bg-green-500' }
  return (
    <div className="flex items-center gap-2 justify-center">
      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${colors[color]}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-mono ${inverted && pct > 60 ? 'text-red-600' : 'text-gray-600'}`}>{pct}%</span>
    </div>
  )
}
