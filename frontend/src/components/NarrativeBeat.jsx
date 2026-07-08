import Reveal from './Reveal'

export default function NarrativeBeat({ children, delay = 0, className = '' }) {
  return (
    <Reveal delay={delay} className={`flex items-start gap-3 ${className}`}>
      <span className="text-accent text-base leading-none flex-shrink-0 mt-0.5">→</span>
      <p className="text-sm text-gray-500 italic leading-relaxed">{children}</p>
    </Reveal>
  )
}
