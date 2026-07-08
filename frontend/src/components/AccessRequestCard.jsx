export default function AccessRequestCard({ fr, title, desc, subject }) {
  const mailto = `mailto:olivier@evidenceable.com?subject=${encodeURIComponent(subject)}`

  return (
    <div className="print:hidden bg-white rounded-2xl border-2 border-dashed border-accent/30 p-8 mb-10 text-center max-w-2xl mx-auto">
      <div className="w-12 h-12 bg-accent/10 rounded-xl flex items-center justify-center mx-auto mb-4">
        <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9" />
        </svg>
      </div>
      <h2 className="text-xl font-bold text-primary mb-2">{title}</h2>
      <p className="text-gray-500 text-sm leading-relaxed mb-6 max-w-md mx-auto">{desc}</p>
      <a
        href={mailto}
        className="inline-flex items-center gap-2 bg-accent hover:bg-accent/90 text-white px-6 py-3 rounded-xl font-semibold text-sm transition-colors shadow-lg shadow-accent/20"
      >
        {fr ? 'Demander un accès gratuit' : 'Request free access'}
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
        </svg>
      </a>
      <p className="text-xs text-gray-400 mt-4">olivier@evidenceable.com</p>
      <p className="text-xs text-gray-300 mt-3 italic">
        {fr
          ? 'Offre limitée dans le temps et en nombre de demandes.'
          : 'Limited-time offer, limited number of requests.'}
      </p>
    </div>
  )
}
