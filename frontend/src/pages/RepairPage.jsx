import { useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLang } from '../LangContext'
import { useGuest } from '../guest/GuestContext'
import RadarChart from '../components/RadarChart'
import AccessRequestCard from '../components/AccessRequestCard'
import { CLAIM_LEVELS, CAUSAL_STRUCTURES, STUDY_DESIGNS, MANIFOLD_REGIONS, label, desc } from '../enumLabels'
import { t } from '../i18n'

const RISK_CONFIG = {
  CRITICAL: { label: 'Non aligné — inférence causale limitée', color: 'bg-red-100 text-red-800 border-red-200', dot: 'bg-red-500', bar: 'bg-red-500', width: 'w-full' },
  HIGH:     { label: 'Désalignement avec niveau de revendication', color: 'bg-orange-100 text-orange-800 border-orange-200', dot: 'bg-orange-500', bar: 'bg-orange-500', width: 'w-3/4' },
  MEDIUM:   { label: 'Ajustement de design requis',               color: 'bg-yellow-100 text-yellow-800 border-yellow-200', dot: 'bg-yellow-500', bar: 'bg-yellow-400', width: 'w-1/2' },
  LOW:      { label: 'Écart mineur',                              color: 'bg-green-100 text-green-800 border-green-200', dot: 'bg-green-500', bar: 'bg-green-500', width: 'w-1/4' },
}

const SEV_CONFIG = {
  CRITICAL: { label: 'Non aligné — inférence causale limitée',    cls: 'bg-red-100 text-red-700 border border-red-200' },
  HIGH:     { label: 'Désalignement avec niveau de revendication', cls: 'bg-orange-100 text-orange-700 border border-orange-200' },
  MEDIUM:   { label: 'Ajustement de design requis',               cls: 'bg-yellow-100 text-yellow-700 border border-yellow-200' },
  LOW:      { label: 'Écart mineur',                              cls: 'bg-green-100 text-green-700 border border-green-200' },
}

const EFFORT_CONFIG = {
  low:      { icon: '✅', label: 'Immédiat',                              cls: 'bg-green-50 border-green-200 text-green-700' },
  medium:   { icon: '🔧', label: 'Amendement',                           cls: 'bg-blue-50 border-blue-200 text-blue-700' },
  high:     { icon: '🏗',  label: 'Nouvelle étude',                      cls: 'bg-orange-50 border-orange-200 text-orange-700' },
  blocking: { icon: '↩',  label: 'Requiert reformulation ou nouvelle étude', cls: 'bg-red-50 border-red-200 text-red-700' },
}

const DIM_LABEL_FR = { device: 'Dispositif', endpoint: 'Critère', design: 'Design', population: 'Population', context: 'Contexte' }
const DIM_LABEL_EN = { device: 'Device', endpoint: 'Endpoint', design: 'Design', population: 'Population', context: 'Context' }

const FLAG_LABELS = {
  CIRCULARITY_RISK:   { fr: 'Risque de circularité',          en: 'Circularity risk' },
  DETECTION_BIAS:     { fr: 'Biais de détection',             en: 'Detection bias' },
  PERCEPTION_BIAS:    { fr: 'Biais de perception',            en: 'Perception bias' },
  MEDIATION_GAP:      { fr: 'Écart de médiation',             en: 'Mediation gap' },
  PROCESS_TAUTOLOGY:  { fr: 'Tautologie de processus',        en: 'Process tautology' },
  ADJUDICATION_RISK:  { fr: "Risque d'adjudication",          en: 'Adjudication risk' },
  SURROGATE_RISK:     { fr: 'Risque critère substitut',       en: 'Surrogate endpoint risk' },
  NO_COMPARATOR:      { fr: 'Absence de comparateur',         en: 'No comparator' },
}

const FLAG_DETAILS_FR = {
  CIRCULARITY_RISK:  "Le critère principal est généré ou influencé par le dispositif évalué. Le dispositif ne peut pas être à la fois l'intervention et l'instrument de mesure du critère principal — cela crée une affirmation causale non falsifiable.",
  DETECTION_BIAS:    "L'ascertainment de l'outcome est influencé par l'intervention. Les critères basés sur la détection (délai de détection, diagnostic déclenché par alerte, événements liés au monitoring) confondent la sensibilité du dispositif avec le bénéfice clinique.",
  PERCEPTION_BIAS:   "Tous les critères sont subjectifs (rapportés par le patient). Sans mise en aveugle ni ancrage objectif, le bénéfice perçu ne peut pas être distingué d'un effet placebo ou d'un biais d'attente.",
  MEDIATION_GAP:     "La revendication est au niveau mécanistique ou de processus, mais les critères mesurent des outcomes cliniques. La chaîne causale entre le mécanisme d'action et l'outcome mesuré n'est pas spécifiée — les étapes intermédiaires sont supposées mais non testées.",
  PROCESS_TAUTOLOGY: "Le critère de processus est l'intervention elle-même. Mesurer le processus que le dispositif réalise comme outcome est tautologique — le dispositif réussira toujours à faire ce qu'il fait.",
  ADJUDICATION_RISK: "Le critère principal est objectif mais évalué sans adjudication indépendante en aveugle (CEC). Dans un essai ouvert sur dispositif, les événements rapportés par l'investigateur sont sujets à un biais de classification.",
  SURROGATE_RISK:    "Le critère principal est un outcome médiateur (substitut) qui ne capture pas le bénéfice clinique direct pour le patient. La chaîne causale vers un critère clinique dur doit être établie indépendamment.",
  NO_COMPARATOR:     "Les données soumises ne comportent pas de groupe contrôle pour une revendication de niveau outcome (C ou D). Sans comparateur, le contrefactuel n'est pas observé — l'outcome ne peut pas être attribué à l'intervention plutôt qu'à l'histoire naturelle ou aux co-interventions.",
}

export default function RepairPage() {
  const { lang } = useLang()
  const fr = lang === 'fr'
  const [searchParams] = useSearchParams()
  const guest = useGuest()
  // guest === null → route not gated (legacy/open). Otherwise require a valid, non-exhausted token.
  const hasAccess = !guest || (guest.token && guest.quota && !guest.error && guest.quota.remaining > 0)

  const [claim, setClaim] = useState({
    text: searchParams.get('claim') || '',
    intervention: searchParams.get('intervention') || '',
    domain: searchParams.get('domain') || '',
  })
  const [pdfFile, setPdfFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState('')
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const setC = (k) => (e) => setClaim((p) => ({ ...p, [k]: e.target.value }))

  const handleFile = (file) => {
    if (!file) return
    if (file.type !== 'application/pdf') {
      setError(fr ? 'Seuls les fichiers PDF sont acceptés.' : 'Only PDF files are accepted.')
      return
    }
    if (file.size > 8 * 1024 * 1024) {
      setError(fr ? 'Fichier trop volumineux (max 8 Mo).' : 'File too large (max 8 MB).')
      return
    }
    setError(null)
    setPdfFile(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const submit = async () => {
    if (!claim.text.trim()) {
      setError(fr ? 'La revendication est obligatoire.' : 'The claim is required.')
      return
    }
    if (!pdfFile) {
      setError(fr ? 'Uploadez l\'abstract de votre étude (PDF).' : 'Upload your study abstract (PDF).')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('claim_text', claim.text)
    formData.append('intervention', claim.intervention)
    formData.append('domain', claim.domain)
    formData.append('lang', lang)
    formData.append('pdf_file', pdfFile)

    try {
      setLoadingStep(fr ? 'Extraction du PDF…' : 'Extracting PDF…')
      const guestToken = guest?.token
      const res = await fetch('/api/diagnose-premium', {
        method: 'POST',
        body: formData,
        headers: guestToken ? { 'x-guest-token': guestToken } : {},
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Erreur ${res.status}`)
      }
      setLoadingStep(fr ? 'Analyse en cours…' : 'Analyzing…')
      const data = await res.json()
      setResult(data)
      guest?.refreshQuota()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
      setLoadingStep('')
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 print:px-0 print:py-0">
      {/* Header */}
      <div className="mb-8 print:hidden">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold text-primary">
            {fr ? 'Diagnostic Complet' : 'Full Diagnostic'}
          </h1>
          <span className="bg-accent text-white text-xs font-bold px-2.5 py-1 rounded-full">{fr ? 'Sur demande' : 'On request'}</span>
        </div>
        <p className="text-gray-500 max-w-2xl">
          {fr
            ? 'Uploadez l\'abstract ou les 5 premières pages de votre étude (PDF). Le moteur extrait les données, identifie les incompatibilités structurelles avec votre revendication, et génère un plan de correction priorisé par effort.'
            : 'Upload the abstract or first 5 pages of your study (PDF). The engine extracts the data, identifies structural incompatibilities with your claim, and generates a correction plan prioritised by effort.'}
        </p>
      </div>

      {!hasAccess && (
        <AccessRequestCard
          fr={fr}
          title={fr ? 'Accès sur demande — phase de test' : 'Access on request — testing phase'}
          desc={fr
            ? 'Le Diagnostic Complet + Repair est en phase de test et accessible gratuitement sur demande. Écrivez-moi et je vous envoie un accès avec un quota d’analyses dédié.'
            : 'Full Diagnostic + Repair is in testing phase and free on request. Reach out and I’ll send you an access link with a dedicated analysis quota.'}
          subject={fr ? 'Demande d’accès test — Diag Complet + Repair' : 'Test access request — Full Diag + Repair'}
        />
      )}

      {/* Form */}
      {hasAccess && (
      <>
      <div className="print:hidden grid lg:grid-cols-2 gap-6 mb-8">
        {/* Left: Claim */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-4">
          <h2 className="font-semibold text-gray-800 flex items-center gap-2">
            <span className="w-6 h-6 bg-primary/10 text-primary rounded-lg text-sm font-bold flex items-center justify-center">1</span>
            {fr ? 'Revendication clinique' : 'Clinical claim'}
          </h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {fr ? 'Texte de la revendication *' : 'Claim text *'}
            </label>
            <textarea
              rows={5}
              value={claim.text}
              onChange={setC('text')}
              placeholder={fr
                ? 'Ex : ODYSIGHT détecte précocement les rechutes de DMLA et réduit le délai de traitement chez les patients sous anti-VEGF…'
                : 'E.g.: Our device detects early AMD relapses and reduces treatment delay in patients on anti-VEGF…'}
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {fr ? 'Dispositif' : 'Device'}
              </label>
              <input
                value={claim.intervention}
                onChange={setC('intervention')}
                placeholder="Ex : ODYSIGHT"
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {fr ? 'Domaine médical' : 'Medical domain'}
              </label>
              <input
                value={claim.domain}
                onChange={setC('domain')}
                placeholder="Ex : ophtalmologie"
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
          </div>
        </div>

        {/* Right: PDF upload */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-4">
          <h2 className="font-semibold text-gray-800 flex items-center gap-2">
            <span className="w-6 h-6 bg-accent/10 text-accent rounded-lg text-sm font-bold flex items-center justify-center">2</span>
            {fr ? 'Étude clinique (PDF)' : 'Clinical study (PDF)'}
          </h2>

          <p className="text-xs text-gray-500 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5">
            {fr
              ? 'Uploadez l\'abstract ou les 5 premières pages de votre publication / rapport d\'étude. L\'IA extrait automatiquement design, endpoints, population et résultats.'
              : 'Upload the abstract or the first 5 pages of your publication / study report. AI automatically extracts design, endpoints, population and results.'}
          </p>

          {/* Drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-accent bg-accent/5'
                : pdfFile
                ? 'border-green-400 bg-green-50'
                : 'border-gray-200 hover:border-accent/50 hover:bg-gray-50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {pdfFile ? (
              <>
                <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center mb-3">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="font-medium text-green-700 text-sm text-center">{pdfFile.name}</p>
                <p className="text-xs text-green-600 mt-1">{(pdfFile.size / 1024).toFixed(0)} Ko</p>
                <button
                  onClick={(e) => { e.stopPropagation(); setPdfFile(null) }}
                  className="mt-3 text-xs text-gray-400 hover:text-red-500 transition-colors"
                >
                  {fr ? 'Supprimer' : 'Remove'}
                </button>
              </>
            ) : (
              <>
                <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center mb-3">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-gray-600">
                  {fr ? 'Déposez votre PDF ici' : 'Drop your PDF here'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {fr ? 'ou cliquez pour parcourir' : 'or click to browse'}
                </p>
                <p className="text-xs text-gray-300 mt-2">PDF · max 8 Mo · 5 pages lues</p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Submit */}
      <div className="print:hidden flex flex-col items-center gap-3 mb-10">
        <button
          onClick={submit}
          disabled={loading || !claim.text.trim() || !pdfFile}
          className="bg-accent hover:bg-accent/90 disabled:opacity-40 text-white px-10 py-3.5 rounded-xl font-semibold text-lg transition-colors shadow-lg shadow-accent/20 flex items-center gap-3"
        >
          {loading ? (
            <>
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {loadingStep || (fr ? 'Analyse en cours…' : 'Analyzing…')}
            </>
          ) : (
            fr ? 'Générer le diagnostic complet' : 'Generate full diagnostic'
          )}
        </button>
        {loading && (
          <p className="text-xs text-gray-400">
            {fr ? 'Extraction PDF + analyse LLM + diagnostic HAS · ~15–30 secondes' : 'PDF extraction + LLM analysis + HAS diagnostic · ~15–30 seconds'}
          </p>
        )}
      </div>
      </>
      )}

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm print:hidden">
          {error}
        </div>
      )}

      {/* Results */}
      {result && !result._no_pdf && <DiagnosticResults result={result} lang={lang} />}
    </div>
  )
}

function DiagnosticResults({ result, lang }) {
  const fr = lang === 'fr'
  const risk = RISK_CONFIG[result.overall_risk] || RISK_CONFIG.MEDIUM
  const parseInfo = result._parse_info || {}
  const biasFlags = result.epistemic?.bias_flags || []
  const DIM_LABEL = fr ? DIM_LABEL_FR : DIM_LABEL_EN

  const effortOrder = { low: 0, medium: 1, high: 2, blocking: 3 }
  const sortedActions = [...(result.actions || [])].sort(
    (a, b) => (effortOrder[a.effort] ?? 9) - (effortOrder[b.effort] ?? 9)
  )
  const effortCounts = {}
  sortedActions.forEach((a) => { if (a.effort) effortCounts[a.effort] = (effortCounts[a.effort] || 0) + 1 })

  return (
    <div className="space-y-6" id="diagnostic-results">
      {/* Print header */}
      <div className="hidden print:block mb-6 border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">
          {fr ? 'Diagnostic de cohérence — Rapport complet' : 'Coherence Diagnostic — Full Report'}
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          EvidenceAble · {new Date().toLocaleDateString('fr-FR')}
        </p>
        {parseInfo.intervention && (
          <p className="text-sm mt-1">
            <span className="text-gray-500">{fr ? 'Dispositif :' : 'Device:'}</span>{' '}
            <strong>{parseInfo.intervention}</strong>
          </p>
        )}
        {parseInfo.study_acronym && (
          <p className="text-sm">
            <span className="text-gray-500">{fr ? 'Étude :' : 'Study:'}</span>{' '}
            <strong>{parseInfo.study_acronym}</strong>
            {parseInfo.study_design && ` · ${parseInfo.study_design}`}
            {parseInfo.n_patients && ` · N=${parseInfo.n_patients}`}
          </p>
        )}
      </div>

      {/* PDF parse summary */}
      {parseInfo.pdf && (
        <>
          <div className="print:hidden bg-blue-50 border border-blue-200 rounded-xl px-5 py-3 flex items-center gap-4 text-sm">
            <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
            </svg>
            <span className="text-blue-700 font-medium">{parseInfo.pdf.filename}</span>
            <span className="text-blue-500">
              {parseInfo.pdf.pages_read}{parseInfo.pdf.total_pages ? `/${parseInfo.pdf.total_pages}` : ''} {fr ? 'page(s) lue(s)' : 'page(s) read'}
              {' · '}{parseInfo.pdf.chars_extracted?.toLocaleString()} {fr ? 'caractères' : 'chars'}
            </span>
            {parseInfo.study_acronym && (
              <span className="ml-auto text-blue-600 font-semibold">
                {fr ? 'Étude :' : 'Study:'} {parseInfo.study_acronym}
                {parseInfo.n_patients ? ` · N=${parseInfo.n_patients}` : ''}
              </span>
            )}
          </div>
          {parseInfo.pdf.truncated && (
            <div className="print:hidden bg-amber-50 border border-amber-300 rounded-xl px-5 py-3 flex items-start gap-3 text-sm">
              <span className="text-amber-500 text-base flex-shrink-0">⚠</span>
              <p className="text-amber-800">
                {fr
                  ? `Votre PDF contient ${parseInfo.pdf.total_pages} pages — seules les ${parseInfo.pdf.pages_read} premières ont été analysées. Pour de meilleurs résultats, uploadez uniquement l'abstract ou les pages de méthodes/résultats.`
                  : `Your PDF has ${parseInfo.pdf.total_pages} pages — only the first ${parseInfo.pdf.pages_read} were analysed. For best results, upload only the abstract or the methods/results pages.`}
              </p>
            </div>
          )}
        </>
      )}

      {/* Summary cards */}
      {result.epistemic && (
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard
            label={fr ? 'Niveau de revendication' : 'Claim level'}
            value={label(CLAIM_LEVELS, result.epistemic.claim_level, fr ? 'fr' : 'en')}
            description={desc(CLAIM_LEVELS, result.epistemic.claim_level, fr ? 'fr' : 'en')}
          />
          <SummaryCard
            label={fr ? 'Structure causale' : 'Causal structure'}
            value={label(CAUSAL_STRUCTURES, result.epistemic.causal_structure, fr ? 'fr' : 'en')}
            description={desc(CAUSAL_STRUCTURES, result.epistemic.causal_structure, fr ? 'fr' : 'en')}
          />
          <SummaryCard
            label={fr ? 'Design recommandé' : 'Recommended design'}
            value={label(STUDY_DESIGNS, result.epistemic.design_recommendation?.primary_design, fr ? 'fr' : 'en')}
            description={desc(STUDY_DESIGNS, result.epistemic.design_recommendation?.primary_design, fr ? 'fr' : 'en')}
          />
          <SummaryCard
            label={fr ? 'Position épistémique' : 'Epistemic position'}
            value={label(MANIFOLD_REGIONS, result.epistemic.epistemic_manifold?.region, fr ? 'fr' : 'en')}
            description={desc(MANIFOLD_REGIONS, result.epistemic.epistemic_manifold?.region, fr ? 'fr' : 'en')}
          />
        </div>
      )}

      {/* Radar état actuel + position dans l'espace de preuve */}
      {result.epistemic?.epistemic_manifold?.coordinates && (
        <div className="grid md:grid-cols-2 gap-6">
          <RadarChart
            coordinates={result.epistemic.epistemic_manifold.coordinates}
            title={fr ? 'Profil épistémique actuel' : 'Current epistemic profile'}
          />
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              {fr ? 'Position dans l\'espace de preuve' : 'Position in evidence space'}
            </h3>
            <div className="space-y-3">
              <InfoRow
                label={fr ? 'Région' : 'Region'}
                value={label(MANIFOLD_REGIONS, result.epistemic.epistemic_manifold.region, fr ? 'fr' : 'en')}
                description={desc(MANIFOLD_REGIONS, result.epistemic.epistemic_manifold.region, fr ? 'fr' : 'en')}
              />
              <InfoRow
                label={fr ? 'Score agrégé' : 'Aggregate score'}
                value={result.epistemic.epistemic_manifold.aggregate_score?.toFixed(3)}
                description={fr
                  ? 'Moyenne des scores sur les 7 axes épistémiques — de 0 (très faible) à 1 (optimal).'
                  : 'Average score across 7 epistemic axes — from 0 (very low) to 1 (optimal).'}
              />
              <InfoRow
                label={fr ? 'Magnitude du biais' : 'Bias magnitude'}
                value={result.epistemic.epistemic_manifold.bias_magnitude?.toFixed(3)}
                description={fr
                  ? 'Intensité des biais structurels détectés — plus la valeur est élevée, plus les biais sont importants.'
                  : 'Intensity of detected structural biases — higher value means more significant biases.'}
              />
              {result.epistemic.epistemic_manifold.regulatory_status && (
                <InfoRow
                  label={fr ? 'Statut' : 'Status'}
                  value={result.epistemic.epistemic_manifold.regulatory_status}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Overall risk */}
      <div className={`rounded-2xl border-2 p-6 ${risk.color}`}>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className={`w-4 h-4 rounded-full flex-shrink-0 ${risk.dot}`} />
            <div>
              <div className="text-lg font-bold">
                {risk.label}
              </div>
              <div className="text-sm opacity-80">
                {result.gaps.length} {fr ? 'écart(s) identifié(s)' : 'gap(s) identified'}
                {' · '}
                {result.is_fully_repairable
                  ? (fr ? 'Compatible si ajustement' : 'Compatible with adjustment')
                  : (fr ? 'Requiert reformulation ou nouvelle étude' : 'Requires reformulation or new study')}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 print:hidden">
            {parseInfo.claim_level && (
              <span className="bg-white/70 px-3 py-1.5 rounded-lg text-sm font-medium">
                {fr ? 'Niveau' : 'Level'} {parseInfo.claim_level}
              </span>
            )}
            <button
              onClick={() => window.print()}
              className="bg-white border border-current/20 hover:bg-white/80 px-4 py-2 rounded-xl text-sm font-semibold transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export PDF
            </button>
          </div>
        </div>
        <div className="mt-4 bg-white/40 rounded-full h-2 overflow-hidden">
          <div className={`h-full rounded-full ${risk.bar} ${risk.width}`} />
        </div>
      </div>

      {/* Epistemic bias flags */}
      {biasFlags.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm px-6 py-5">
          <h3 className="font-semibold text-gray-800 mb-4 text-sm">
            {fr ? 'Analyse épistémique détaillée' : 'Detailed epistemic analysis'}
          </h3>
          <div className="space-y-3">
            {biasFlags.map((bf, i) => {
              const flagKey = bf.flag || bf.flag_key || ''
              const flagLabel = FLAG_LABELS[flagKey]?.[fr ? 'fr' : 'en'] || flagKey
              const flagDetail = fr
                ? (FLAG_DETAILS_FR[flagKey] || bf.detail || '')
                : (bf.detail || '')
              const sevCls =
                bf.severity === 'HIGH'   ? 'bg-red-50 border-red-200 text-red-700' :
                bf.severity === 'MEDIUM' ? 'bg-yellow-50 border-yellow-200 text-yellow-700' :
                'bg-blue-50 border-blue-200 text-blue-700'
              const dotCls =
                bf.severity === 'HIGH'   ? 'bg-red-500' :
                bf.severity === 'MEDIUM' ? 'bg-yellow-500' : 'bg-blue-500'
              return (
                <div key={i} className={`rounded-xl border px-4 py-3 ${sevCls}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotCls}`} />
                    <span className="text-sm font-semibold">{flagLabel}</span>
                  </div>
                  {flagDetail && (
                    <p className="text-xs leading-relaxed opacity-80 pl-4">{flagDetail}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Gaps identifiés */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm">
        <div className="px-6 pt-5 pb-4 border-b border-gray-50">
          <h2 className="font-bold text-gray-900">
            {fr ? 'Gaps identifiés' : 'Identified gaps'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {fr ? 'Écarts entre l\'étude et la revendication' : 'Gaps between study and claim'}
          </p>
        </div>
        <div className="divide-y divide-gray-50">
          {result.gaps.length === 0 ? (
            <div className="px-6 py-10 text-center">
              <div className="text-2xl mb-2">✅</div>
              <p className="text-green-700 font-medium text-sm">
                {fr ? 'Aucun gap majeur identifié' : 'No major gaps identified'}
              </p>
            </div>
          ) : (
            result.gaps.map((g, i) => {
              const sev = SEV_CONFIG[g.severity] || SEV_CONFIG.MEDIUM
              return (
                <div key={i} className="px-6 py-4">
                  <div className="flex items-start gap-3">
                    <span className={`mt-0.5 px-2 py-0.5 rounded text-xs font-bold flex-shrink-0 ${sev.cls}`}>
                      {sev.label}
                    </span>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                        {DIM_LABEL[g.dimension] || g.dimension}
                      </div>
                      <p className="text-sm text-gray-800 leading-snug">{g.description}</p>
                      {g.has_critique && (
                        <p className="mt-2 text-xs text-gray-500 italic leading-relaxed border-l-2 border-gray-200 pl-3">
                          {g.has_critique}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Effort summary */}
      {sortedActions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 px-6 py-4 flex items-center gap-4 flex-wrap">
          <span className="text-sm font-semibold text-gray-700">
            {fr ? 'Plan de correction :' : 'Correction plan:'}
          </span>
          {Object.entries(effortCounts).map(([eff, n]) => {
            const cfg = EFFORT_CONFIG[eff]
            return (
              <span key={eff} className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border ${cfg.cls}`}>
                {cfg.icon} {n}× {cfg.label}
              </span>
            )
          })}
          {!result.is_fully_repairable && (
            <span className="ml-auto text-xs text-gray-400">
              {fr ? 'Nouvelle étude nécessaire' : 'New study required'}
            </span>
          )}
        </div>
      )}

      {/* Plan de correction détaillé */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm">
        <div className="px-6 pt-5 pb-4 border-b border-gray-50">
          <h2 className="font-bold text-gray-900">
            {fr ? 'Plan de correction' : 'Correction plan'}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {fr ? 'Classé par effort croissant' : 'Sorted by ascending effort'}
          </p>
        </div>
        <div className="divide-y divide-gray-50">
          {sortedActions.length === 0 ? (
            <div className="px-6 py-10 text-center text-gray-400 text-sm">
              {fr ? 'Aucune correction requise' : 'No corrections required'}
            </div>
          ) : (
            sortedActions.map((a, i) => {
              const eff = EFFORT_CONFIG[a.effort] || EFFORT_CONFIG.medium
              const sev = SEV_CONFIG[a.gap_severity] || SEV_CONFIG.MEDIUM
              return (
                <div key={i} className="px-6 py-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border ${eff.cls}`}>
                      {eff.icon} {eff.label}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${sev.cls}`}>
                      {sev.label}
                    </span>
                    <span className="text-xs text-gray-400 uppercase tracking-wide">
                      {DIM_LABEL[a.gap_dimension] || a.gap_dimension}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-gray-800 mb-1">{a.description}</p>
                  {a.specific_suggestion && (
                    <p className="text-xs text-gray-500 leading-relaxed border-l-2 border-gray-100 pl-3 mt-2">
                      {a.specific_suggestion}
                    </p>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Radar avant/après + position projetée */}
      {result.epistemic?.epistemic_manifold?.coordinates && (
        <div className="space-y-6">
          <RadarChart
            coordinates={result.epistemic.epistemic_manifold.coordinates}
            coordinatesAfter={result.epistemic.repair_manifold_delta?.after}
            title={fr
              ? 'Profil épistémique — avant / après correction'
              : 'Epistemic profile — before / after correction'}
          />
          {result.epistemic.repair_manifold_delta?.after && (
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">
                {fr ? 'Position projetée après correction' : 'Projected position after correction'}
              </h3>
              <div className="space-y-3">
                <InfoRow
                  label={fr ? 'Région actuelle' : 'Current region'}
                  value={label(MANIFOLD_REGIONS, result.epistemic.epistemic_manifold.region, fr ? 'fr' : 'en')}
                />
                <InfoRow
                  label={fr ? 'Région projetée' : 'Projected region'}
                  value={label(MANIFOLD_REGIONS, result.epistemic.repair_manifold_delta.region_after, fr ? 'fr' : 'en')}
                />
                <InfoRow
                  label={fr ? 'Score actuel' : 'Current score'}
                  value={result.epistemic.epistemic_manifold.aggregate_score?.toFixed(3)}
                />
                {result.epistemic.repair_manifold_delta.after && (
                  <InfoRow
                    label={fr ? 'Score projeté' : 'Projected score'}
                    value={
                      Object.values(result.epistemic.repair_manifold_delta.after).length > 0
                        ? (Object.values(result.epistemic.repair_manifold_delta.after).reduce((a, b) => a + b, 0) /
                           Object.values(result.epistemic.repair_manifold_delta.after).length).toFixed(3)
                        : '—'
                    }
                  />
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Synthèse LLM */}
      {result.llm_summary && (
        <div className="bg-gradient-to-br from-primary/5 to-blue-50 rounded-2xl border border-primary/10 px-6 py-5">
          <h3 className="font-semibold text-gray-800 text-sm mb-3">
            {fr ? 'Synthèse du rapport' : 'Report summary'}
          </h3>
          <p className="text-sm text-gray-700 leading-relaxed">{result.llm_summary}</p>
        </div>
      )}
    </div>
  )
}


function SummaryCard({ label, value, description }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 flex flex-col gap-2">
      <div className="text-xs text-gray-500 uppercase tracking-wider">{label}</div>
      <div className="text-lg font-bold text-primary leading-tight">{value || '—'}</div>
      {description && (
        <p className="text-xs text-gray-400 leading-relaxed">{description}</p>
      )}
    </div>
  )
}

function InfoRow({ label, value, description }) {
  return (
    <div className="py-2 border-b border-gray-50 last:border-0">
      <div className="flex justify-between items-baseline gap-4">
        <span className="text-xs text-gray-500 uppercase tracking-wide flex-shrink-0">{label}</span>
        <span className="text-sm font-medium text-gray-800 text-right">{value || '—'}</span>
      </div>
      {description && (
        <p className="text-xs text-gray-400 leading-relaxed mt-1">{description}</p>
      )}
    </div>
  )
}
