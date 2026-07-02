import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useLang } from '../LangContext'
import { t } from '../i18n'
import {
  DEVICE_MATCH_TYPES,
  POPULATION_MATCH_TYPES,
  CONTEXT_MATCH_TYPES,
  CARE_PATHWAY_MATCHES,
  ELIGIBILITY_SHIFTS,
  ORGANIZATION_DEPENDENCIES,
  CAS_VERDICTS,
  label,
} from '../enumLabels'

const EXAMPLES = {
  fr: [
    {
      label: 'PRESAGE CARE',
      claim: "Télésurveillance médicale prédictive et préventive des hospitalisations non programmées d'une personne âgée de 65 ans et plus, fragile, atteinte d'une ou plusieurs pathologies chroniques. Dispositif : PRESAGE CARE v1.3.",
      study: "Étude observationnelle monocentrique sur PRESAGE CARE dans un EHPAD français. Population : patients avec dépendance légère à modérée (GIR 3-4). L'algorithme évalué est une version antérieure (v1.0). 200 patients inclus. VPP de 9.4% et sensibilité de 36%. L'organisation de la télésurveillance dans l'étude est différente de celle proposée par le demandeur.",
    },
    {
      label: 'INCEPTIV',
      claim: "Neurostimulation médullaire à boucle fermée INCEPTIV (Medtronic) pour le traitement de la douleur chronique réfractaire. Revendication : réduction de la douleur supérieure à la neurostimulation conventionnelle.",
      study: "Étude EVOKE (Saluda Medical) : essai randomisé contrôlé comparant la neurostimulation à boucle fermée EVOKE vs boucle ouverte chez 134 patients douleur chronique. Étude menée aux USA et en Australie. EVOKE n'est pas pris en charge en France.",
    },
    {
      label: 'TUCKY CENTER',
      claim: "Télésurveillance des patients sous chimiothérapie, en suivi post-opératoire bariatrique, et des femmes enceintes hypertendues. Dispositif : TUCKY CENTER (e-TakesCare).",
      study: "Aucune étude spécifique de TUCKY CENTER n'a été soumise. Le demandeur fournit des études sur d'autres dispositifs de télésurveillance : McGillion et al. (2021) sur la chirurgie urgente chez l'adulte, études non spécifiques en oncologie pédiatrique.",
    },
  ],
  en: [
    {
      label: 'PRESAGE CARE',
      claim: "Predictive and preventive remote monitoring of unplanned hospitalizations in frail elderly patients aged 65+. Device: PRESAGE CARE v1.3.",
      study: "Single-center observational study on PRESAGE CARE in a French nursing home. Population: patients with mild to moderate dependency (GIR 3-4). Algorithm evaluated is a prior version (v1.0). 200 patients. PPV 9.4%, sensitivity 36%. The telemonitoring organization in the study differs from the applicant's proposal.",
    },
    {
      label: 'INCEPTIV',
      claim: "Closed-loop spinal cord stimulation INCEPTIV (Medtronic) for refractory chronic pain. Claim: superior pain reduction vs conventional stimulation.",
      study: "EVOKE trial (Saluda Medical): RCT comparing closed-loop EVOKE vs open-loop stimulation in 134 chronic pain patients. Study conducted in USA and Australia. EVOKE is not reimbursed in France.",
    },
    {
      label: 'TUCKY CENTER',
      claim: "Remote monitoring of chemotherapy patients, post-bariatric surgery follow-up, and hypertensive pregnant women. Device: TUCKY CENTER.",
      study: "No specific TUCKY CENTER study submitted. Applicant provides studies on other telemonitoring devices: McGillion et al. (2021) on urgent surgery in adults, non-specific studies in pediatric oncology.",
    },
  ],
}

export default function CASPage() {
  const { lang } = useLang()
  const location = useLocation()
  const navigate = useNavigate()
  const [claimText, setClaimText] = useState('')
  const [studyText, setStudyText] = useState('')
  const [result, setResult] = useState(null)
  const [parseInfo, setParseInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (location.state?.claim_text) {
      setClaimText(location.state.claim_text)
    }
  }, [location.state])

  const loadExample = (ex) => {
    setClaimText(ex.claim)
    setStudyText(ex.study)
    setResult(null)
    setParseInfo(null)
    setError(null)
  }

  const submit = async () => {
    setLoading(true)
    setError(null)
    setParseInfo(null)
    setResult(null)
    try {
      const res = await fetch('/api/smart-cas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claim_text: claimText, study_text: studyText, lang }),
      })
      if (!res.ok) throw new Error(`${lang === 'fr' ? 'Erreur' : 'Error'} ${res.status}`)
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      if (data._parse_info) setParseInfo(data._parse_info)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const examples = EXAMPLES[lang] || EXAMPLES.fr

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="bg-emerald-100 text-emerald-700 text-xs font-bold px-2.5 py-1 rounded-full">
            {lang === 'fr' ? 'ÉTAPE 1' : 'STEP 1'}
          </span>
          <h1 className="text-3xl font-bold text-emerald-700">{t('cas_title', lang)}</h1>
        </div>
        <p className="text-gray-500 mt-2">{t('cas_desc', lang)}</p>
      </div>

      {/* Examples */}
      <div className="mb-6 flex flex-wrap gap-2">
        <span className="text-sm text-gray-500 self-center mr-2">
          {lang === 'fr' ? 'Cas réels CNEDiMTS :' : 'Real CNEDiMTS cases:'}
        </span>
        {examples.map((ex, i) => (
          <button
            key={i}
            onClick={() => loadExample(ex)}
            className="px-3 py-1.5 text-sm bg-emerald-50 text-emerald-700 rounded-lg hover:bg-emerald-100 transition-colors border border-emerald-200"
          >
            {ex.label}
          </button>
        ))}
      </div>

      {/* Input form */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* CLAIM */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border-2 border-emerald-200">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center text-emerald-700 font-bold text-sm">C</div>
            <div>
              <h3 className="font-semibold text-gray-800">
                {lang === 'fr' ? 'Revendication (Claim)' : 'Claim'}
              </h3>
              <p className="text-xs text-gray-500">
                {lang === 'fr'
                  ? 'Ce que vous voulez démontrer. Quel dispositif, pour qui, quel bénéfice.'
                  : 'What you want to demonstrate. Which device, for whom, what benefit.'}
              </p>
            </div>
          </div>
          <textarea
            value={claimText}
            onChange={(e) => setClaimText(e.target.value)}
            rows={8}
            className="input-cas"
            placeholder={lang === 'fr'
              ? "Ex : Notre dispositif PRESAGE CARE v1.3 permet la télésurveillance prédictive des hospitalisations non programmées chez les personnes âgées fragiles de 65 ans et plus, atteintes d'une ou plusieurs pathologies chroniques..."
              : "E.g.: Our device PRESAGE CARE v1.3 enables predictive remote monitoring of unplanned hospitalizations in frail elderly patients aged 65+..."}
          />
        </div>

        {/* STUDY */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border-2 border-blue-200">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center text-blue-700 font-bold text-sm">S</div>
            <div>
              <h3 className="font-semibold text-gray-800">
                {lang === 'fr' ? 'Étude clinique fournie' : 'Clinical study provided'}
              </h3>
              <p className="text-xs text-gray-500">
                {lang === 'fr'
                  ? 'L\'étude que vous soumettez comme preuve. Quel dispositif testé, quelle population, où, quel design.'
                  : 'The study you submit as evidence. Which device tested, what population, where, what design.'}
              </p>
            </div>
          </div>
          <textarea
            value={studyText}
            onChange={(e) => setStudyText(e.target.value)}
            rows={8}
            className="input-cas"
            style={{ borderColor: '#bfdbfe', boxShadow: 'none' }}
            onFocus={(e) => { e.target.style.borderColor = '#3b82f6'; e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.15)' }}
            onBlur={(e) => { e.target.style.borderColor = '#bfdbfe'; e.target.style.boxShadow = 'none' }}
            placeholder={lang === 'fr'
              ? "Ex : Étude observationnelle monocentrique menée en France sur 200 patients en EHPAD. Dispositif testé : PRESAGE CARE v1.0 (version antérieure). Population : patients avec dépendance légère à modérée (GIR 3-4). VPP 9.4%, sensibilité 36%..."
              : "E.g.: Single-center observational study in France on 200 nursing home patients. Device tested: PRESAGE CARE v1.0 (prior version). Population: patients with mild to moderate dependency. PPV 9.4%, sensitivity 36%..."}
          />
        </div>
      </div>

      {/* Submit */}
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={submit}
          disabled={loading || !claimText.trim() || !studyText.trim()}
          className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-8 py-3 rounded-xl font-semibold transition-colors flex items-center gap-2"
        >
          {loading ? (
            <>
              <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
              {t('btn_evaluating_cas', lang)}
            </>
          ) : t('btn_evaluate_cas', lang)}
        </button>
        <span className="text-xs text-gray-400">
          {lang === 'fr'
            ? 'L\'IA analyse la correspondance entre votre claim et votre étude'
            : 'The AI analyzes the match between your claim and your study'}
        </span>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">{error}</div>
      )}

      {/* Parse info */}
      {parseInfo && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-6">
          <h4 className="text-sm font-semibold text-emerald-800 mb-3">
            {lang === 'fr' ? 'Interprétation IA' : 'AI Interpretation'}
          </h4>
          <div className="grid md:grid-cols-2 gap-4">
            {parseInfo.claim_parsed && (
              <div className="bg-white rounded-lg p-3 border border-emerald-100">
                <div className="text-xs font-bold text-emerald-600 uppercase mb-2">
                  {lang === 'fr' ? 'Claim compris' : 'Claim understood'}
                </div>
                <div className="space-y-1 text-xs text-gray-600">
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Dispositif' : 'Device'}:</span> {parseInfo.claim_parsed.device_name || '—'}</div>
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Population' : 'Population'}:</span> {parseInfo.claim_parsed.target_population || '—'}</div>
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Bénéfice' : 'Benefit'}:</span> {parseInfo.claim_parsed.intended_benefit || '—'}</div>
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Domaine' : 'Domain'}:</span> {parseInfo.claim_parsed.domain || '—'}</div>
                </div>
              </div>
            )}
            {parseInfo.study_parsed && (
              <div className="bg-white rounded-lg p-3 border border-blue-100">
                <div className="text-xs font-bold text-blue-600 uppercase mb-2">
                  {lang === 'fr' ? 'Étude comprise' : 'Study understood'}
                </div>
                <div className="space-y-1 text-xs text-gray-600">
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Dispositif' : 'Device'}:</span> {parseInfo.study_parsed.device_name || '—'}</div>
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Population' : 'Population'}:</span> {parseInfo.study_parsed.study_population || '—'}</div>
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Pays' : 'Country'}:</span> {parseInfo.study_parsed.study_country || '—'}</div>
                  <div><span className="font-medium text-gray-500">{lang === 'fr' ? 'Design' : 'Design'}:</span> {parseInfo.study_parsed.study_design_brief || '—'}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {result && !result.error && (
        <>
          <CASResults data={result} lang={lang} />

          {/* Next step */}
          <div className="mt-8 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              {lang === 'fr' ? 'Étape suivante' : 'Next step'}
            </h3>
            {result.verdict === 'REJECTED' ? (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <p className="text-red-800 font-medium mb-2">
                  {lang === 'fr'
                    ? 'L\'alignement étude / revendication est insuffisant.'
                    : 'Study / claim alignment is insufficient.'}
                </p>
                <p className="text-red-700 text-sm">
                  {lang === 'fr'
                    ? 'Évaluer la qualité méthodologique (REVIEW) n\'a pas de sens tant que les données ne portent pas sur le bon dispositif, la bonne population ou le bon contexte. Utilisez le mode DESIGN pour concevoir une stratégie d\'évidence alignée.'
                    : 'Evaluating methodological quality (REVIEW) is not meaningful while the data does not cover the right device, population, or context. Use DESIGN mode to build an aligned evidence strategy.'}
                </p>
                <button
                  onClick={() => navigate('/design', { state: { fromCAS: true, claim_text: claimText, intervention: result.intervention, domain: result.domain } })}
                  className="mt-4 bg-accent hover:bg-accent-light text-white px-6 py-2.5 rounded-xl font-medium transition-colors"
                >
                  {lang === 'fr' ? 'Concevoir une stratégie (DESIGN)' : 'Design a strategy (DESIGN)'}
                </button>
              </div>
            ) : (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <p className="text-emerald-800 text-sm mb-4">
                  {result.verdict === 'ACCEPTABLE'
                    ? (lang === 'fr'
                        ? 'L\'alignement est acceptable. Passez à l\'étape 2 pour évaluer la qualité méthodologique.'
                        : 'Alignment is acceptable. Proceed to step 2 to evaluate methodological quality.')
                    : (lang === 'fr'
                        ? 'L\'alignement est faible mais pas bloquant. Passez au REVIEW en tenant compte des risques identifiés.'
                        : 'Alignment is weak but not blocking. Proceed to REVIEW while considering identified risks.')}
                </p>
                <button
                  onClick={() => navigate('/review', { state: { fromCAS: true, claim_text: claimText, intervention: result.intervention, domain: result.domain, cas_verdict: result.verdict, cas_score: result.scores?.cas_score } })}
                  className="bg-primary hover:bg-primary-light text-white px-6 py-2.5 rounded-xl font-medium transition-colors flex items-center gap-2"
                >
                  {lang === 'fr' ? 'Passer au REVIEW (étape 2)' : 'Proceed to REVIEW (step 2)'}
                  <span>&rarr;</span>
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function CASResults({ data, lang }) {
  const scores = data.scores || {}
  const verdictColor = {
    ACCEPTABLE: 'bg-green-100 text-green-800 border-green-200',
    WEAK_EVIDENCE: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    REJECTED: 'bg-red-100 text-red-800 border-red-200',
  }[data.verdict] || 'bg-gray-100 text-gray-800'

  const gateColor = data.gating?.device_gate_passed
    ? 'bg-green-100 text-green-800'
    : 'bg-red-100 text-red-800'

  return (
    <div className="space-y-6">
      {/* Score cards */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 text-center">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t('cas_res_score', lang)}</div>
          <div className="text-4xl font-bold text-emerald-700">{scores.cas_score?.toFixed(2)}</div>
        </div>
        <div className={`rounded-2xl p-5 shadow-sm border text-center ${verdictColor}`}>
          <div className="text-xs uppercase tracking-wider mb-1 opacity-70">{t('cas_res_verdict', lang)}</div>
          <div className="text-2xl font-bold">{label(CAS_VERDICTS, data.verdict, lang)}</div>
        </div>
        <div className={`rounded-2xl p-5 shadow-sm border text-center ${gateColor}`}>
          <div className="text-xs uppercase tracking-wider mb-1 opacity-70">{t('cas_res_device_gate', lang)}</div>
          <div className="text-2xl font-bold">
            {data.gating?.device_gate_passed ? t('cas_res_gate_passed', lang) : t('cas_res_gate_failed', lang)}
          </div>
          {data.gating?.device_gate_reason && (
            <div className="text-xs mt-1 opacity-70">{data.gating.device_gate_reason}</div>
          )}
        </div>
      </div>

      {/* Alignment detail cards */}
      <div className="grid md:grid-cols-3 gap-4">
        <AlignmentCard
          title={lang === 'fr' ? 'Dispositif' : 'Device'}
          color="emerald"
          matchType={label(DEVICE_MATCH_TYPES, data.device_alignment?.device_match_type, lang)}
          distance={scores.d_device}
          weight="40%"
          claimVal={data.device_alignment?.device_description_claim}
          studyVal={data.device_alignment?.device_description_study}
          justification={data.device_alignment?.justification}
          lang={lang}
        />
        <AlignmentCard
          title="Population"
          color="violet"
          matchType={label(POPULATION_MATCH_TYPES, data.population_alignment?.population_match_type, lang)}
          distance={scores.d_population}
          weight="35%"
          claimVal={data.population_alignment?.population_description_claim}
          studyVal={data.population_alignment?.population_description_study}
          justification={data.population_alignment?.justification}
          lang={lang}
        />
        <AlignmentCard
          title={lang === 'fr' ? 'Contexte' : 'Context'}
          color="amber"
          matchType={label(CONTEXT_MATCH_TYPES, data.context_alignment?.context_match_type, lang)}
          distance={scores.d_context}
          weight="25%"
          claimVal={data.context_alignment?.target_country || 'France'}
          studyVal={data.context_alignment?.study_country}
          justification={data.context_alignment?.justification}
          lang={lang}
        />
      </div>

      {/* Risks */}
      {data.risks?.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('cas_res_risks', lang)}</h3>
          <div className="space-y-3">
            {data.risks.map((r, i) => (
              <div key={i} className={`rounded-xl p-4 border ${
                r.risk_level === 'CRITICAL' ? 'bg-red-50 border-red-200'
                : r.risk_level === 'HIGH' ? 'bg-orange-50 border-orange-200'
                : 'bg-yellow-50 border-yellow-200'
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    r.risk_level === 'CRITICAL' ? 'bg-red-200 text-red-800'
                    : r.risk_level === 'HIGH' ? 'bg-orange-200 text-orange-800'
                    : 'bg-yellow-200 text-yellow-800'
                  }`}>{r.risk_level}</span>
                  <span className="text-sm font-medium text-gray-700">{r.dimension}</span>
                </div>
                <p className="text-sm text-gray-600">{r.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Regulatory interpretation */}
      <div className="bg-gradient-to-br from-emerald-700 to-emerald-900 text-white rounded-2xl p-6">
        <h3 className="text-lg font-semibold mb-3">{t('cas_res_interpretation', lang)}</h3>
        <pre className="text-sm text-white/90 whitespace-pre-wrap font-sans leading-relaxed">
          {data.regulatory_interpretation}
        </pre>
      </div>
    </div>
  )
}

function AlignmentCard({ title, color, matchType, distance, weight, claimVal, studyVal, justification, lang }) {
  const dist = distance || 0
  const barColor = dist <= 0.1 ? 'bg-green-500' : dist <= 0.4 ? 'bg-yellow-500' : dist <= 0.7 ? 'bg-orange-500' : 'bg-red-500'
  const borderColor = {
    emerald: 'border-l-emerald-500',
    violet: 'border-l-violet-500',
    amber: 'border-l-amber-500',
  }[color] || 'border-l-gray-500'

  return (
    <div className={`bg-white rounded-2xl p-5 shadow-sm border border-gray-100 border-l-4 ${borderColor}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-gray-800">{title}</h4>
        <span className="text-xs text-gray-400">{weight}</span>
      </div>
      <div className="text-sm font-medium text-gray-700 mb-2">{matchType}</div>
      <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
        <div className={`h-2 rounded-full transition-all ${barColor}`} style={{ width: `${Math.max(dist * 100, 3)}%` }} />
      </div>
      <div className="space-y-2 text-xs">
        <div>
          <span className="text-emerald-600 font-medium">Claim:</span>
          <span className="text-gray-600 ml-1">{claimVal || '—'}</span>
        </div>
        <div>
          <span className="text-blue-600 font-medium">{lang === 'fr' ? 'Étude' : 'Study'}:</span>
          <span className="text-gray-600 ml-1">{studyVal || '—'}</span>
        </div>
        {justification && (
          <div className="text-gray-500 italic pt-1 border-t border-gray-100">{justification}</div>
        )}
      </div>
    </div>
  )
}
