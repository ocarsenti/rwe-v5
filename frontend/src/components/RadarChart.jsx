import {
  Radar,
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'

const AXIS_LABELS = {
  outcome_independence:      'Indépendance critère',
  contamination_risk:        'Risque contamination',
  randomization_strength:    'Randomisation',
  blinding_strength:         'Mise en aveugle',
  temporal_depth:            'Profondeur temporelle',
  endpoint_clinical_validity:'Validité clinique',
  data_source_independence:  'Source indépendante',
}

const AXIS_DESCRIPTIONS = {
  outcome_independence:      "Dans quelle mesure le critère principal est indépendant du dispositif évalué. Un score faible indique que le dispositif mesure sa propre performance (circularité).",
  contamination_risk:        "Risque que le groupe contrôle soit exposé indirectement à l'intervention. Un score faible signale un risque élevé de contamination.",
  randomization_strength:    "Force de la randomisation pour contrôler le biais de sélection. Faible pour les études observationnelles, élevé pour les RCT.",
  blinding_strength:         "Niveau de mise en aveugle des participants et des évaluateurs. Critique pour les critères subjectifs.",
  temporal_depth:            "Adéquation de la durée de suivi par rapport à l'histoire naturelle de la condition évaluée.",
  endpoint_clinical_validity:"Pertinence clinique directe du critère principal pour le patient — distingue les vrais outcomes des substituts.",
  data_source_independence:  "Indépendance de la source de données par rapport à l'intervention. Faible si le dispositif génère lui-même les données mesurées.",
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 max-w-xs">
      <div className="font-semibold text-gray-800 text-sm mb-1">{point.axis}</div>
      <div className="flex gap-3 mb-2">
        {payload.map((p) => (
          <span key={p.dataKey} style={{ color: p.stroke || p.fill }} className="text-sm font-bold">
            {p.name}: {p.value?.toFixed(2)}
          </span>
        ))}
      </div>
      {point.description && (
        <p className="text-xs text-gray-500 leading-relaxed border-t border-gray-100 pt-2">
          {point.description}
        </p>
      )}
    </div>
  )
}

export default function RadarChart({ coordinates, coordinatesAfter, title = 'Manifold Épistémique' }) {
  if (!coordinates) return null

  const data = Object.entries(coordinates).map(([key, value]) => {
    const point = {
      axis: AXIS_LABELS[key] || key,
      description: AXIS_DESCRIPTIONS[key] || null,
      avant: Math.round(value * 100) / 100,
      fullMark: 1,
    }
    if (coordinatesAfter && coordinatesAfter[key] !== undefined) {
      point.après = Math.round(coordinatesAfter[key] * 100) / 100
    }
    return point
  })

  const hasAfter = !!coordinatesAfter

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <RechartsRadar data={data}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: '#64748b' }} />
          <PolarRadiusAxis angle={90} domain={[0, 1]} tick={{ fontSize: 10 }} />
          <Radar
            name={hasAfter ? 'Avant correction' : 'Score'}
            dataKey="avant"
            stroke="#1e3a5f"
            fill="#1e3a5f"
            fillOpacity={hasAfter ? 0.15 : 0.25}
            strokeWidth={2}
          />
          {hasAfter && (
            <Radar
              name="Après correction"
              dataKey="après"
              stroke="#f97316"
              fill="#f97316"
              fillOpacity={0.2}
              strokeWidth={2}
              strokeDasharray="4 2"
            />
          )}
          {hasAfter && <Legend />}
          <Tooltip content={<CustomTooltip />} />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  )
}
