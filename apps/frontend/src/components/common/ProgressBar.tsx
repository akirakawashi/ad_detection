interface ProgressBarProps {
  progress: number
  label: string
  animated?: boolean
}

export function ProgressBar({
  progress,
  label,
  animated = false,
}: ProgressBarProps) {
  return (
    <div className={`progress-block${animated ? ' animated' : ''}`}>
      <div>
        <span>{label}</span>
        <strong>{progress}%</strong>
      </div>
      <div className="progress-track">
        <span style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}
