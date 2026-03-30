/**
 * ProgressCell.tsx
 * Shows a thin progress bar + percentage + optional status message.
 */

interface Props {
  progress:   number   // 0–100
  message:    string
  isRunning:  boolean
  isComplete: boolean
}

export default function ProgressCell({ progress, message, isRunning, isComplete }: Props) {
  const barClass = isComplete
    ? 'progress-bar-inner progress-bar-inner--complete'
    : isRunning
      ? 'progress-bar-inner pulse'
      : 'progress-bar-inner'

  const pct = Math.max(0, Math.min(100, progress))

  return (
    <div>
      <div className="progress-wrap">
        <div className="progress-bar-outer">
          <div className={barClass} style={{ width: `${pct}%` }} />
        </div>
        <span className="progress-pct">
          {pct > 0 ? `${pct}%` : ''}
        </span>
      </div>
      {message && (
        <div
          style={{
            marginTop: 2,
            fontSize: 9,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: 160,
          }}
          title={message}
        >
          {message}
        </div>
      )}
    </div>
  )
}
