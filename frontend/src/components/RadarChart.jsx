import {
  Radar,
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

const AXIS_LABELS = {
  outcome_independence: 'Indépendance',
  contamination_risk: 'Risque contam.',
  randomization_strength: 'Randomisation',
  blinding_strength: 'Aveugle',
  temporal_depth: 'Prof. temporelle',
  endpoint_clinical_validity: 'Validité clinique',
  data_source_independence: 'Source indép.',
}

export default function RadarChart({ coordinates, title = 'Manifold Épistémique' }) {
  if (!coordinates) return null

  const data = Object.entries(coordinates).map(([key, value]) => ({
    axis: AXIS_LABELS[key] || key,
    value: Math.round(value * 100) / 100,
    fullMark: 1,
  }))

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <RechartsRadar data={data}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: '#64748b' }} />
          <PolarRadiusAxis angle={90} domain={[0, 1]} tick={{ fontSize: 10 }} />
          <Radar
            name="Score"
            dataKey="value"
            stroke="#1e3a5f"
            fill="#1e3a5f"
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Tooltip />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  )
}
