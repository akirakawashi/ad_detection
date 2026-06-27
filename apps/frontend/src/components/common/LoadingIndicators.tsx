export function InfinityLoader({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`infinity-loader${compact ? ' compact' : ''}`} aria-hidden>
      <svg viewBox="0 0 120 60" role="img">
        <path
          className="infinity-path infinity-path-base"
          d="M30 30 C30 11 55 11 60 30 C65 49 90 49 90 30 C90 11 65 11 60 30 C55 49 30 49 30 30"
        />
        <path
          className="infinity-path infinity-path-active"
          d="M30 30 C30 11 55 11 60 30 C65 49 90 49 90 30 C90 11 65 11 60 30 C55 49 30 49 30 30"
        />
      </svg>
    </div>
  )
}

export function AnimatedDots() {
  return (
    <span className="animated-dots" aria-hidden>
      <span />
      <span />
      <span />
    </span>
  )
}
