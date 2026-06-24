const SEVERITY_COLORS = {
  HIGH: 'bg-red-100 text-red-800 border-red-200',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  LOW: 'bg-green-100 text-green-800 border-green-200',
}

const BIAS_LABELS = {
  CIRCULARITY_RISK: { fr: 'Risque de Circularité', en: 'Circularity Risk' },
  DETECTION_BIAS: { fr: 'Biais de Détection', en: 'Detection Bias' },
  PERCEPTION_BIAS: { fr: 'Biais de Perception', en: 'Perception Bias' },
  MEDIATION_GAP: { fr: 'Gap de Médiation', en: 'Mediation Gap' },
  PROCESS_TAUTOLOGY: { fr: 'Tautologie de Processus', en: 'Process Tautology' },
}

export default function BiasDisplay({ biasFlags, lang = 'fr' }) {
  if (!biasFlags || biasFlags.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-4">
        <span className="text-green-700 font-medium">
          {lang === 'fr' ? 'Aucun biais structurel détecté' : 'No structural bias detected'}
        </span>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {biasFlags.map((b, i) => (
        <div
          key={i}
          className={`rounded-xl p-4 border ${SEVERITY_COLORS[b.severity] || 'bg-gray-100 text-gray-800 border-gray-200'}`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-sm">
              {BIAS_LABELS[b.flag]?.[lang] || b.flag}
            </span>
            <span className="text-xs font-bold uppercase px-2 py-0.5 rounded-full bg-white/50">
              {b.severity}
            </span>
          </div>
          <p className="text-sm opacity-80">{b.detail}</p>
        </div>
      ))}
    </div>
  )
}
