/**
 * StatusBar.tsx
 * Fixed bottom bar with a message and a global progress bar.
 * Mirrors Python's QStatusBar + QProgressBar.
 */

interface Props {
  message:  string
  progress: number  // 0–100
}

export default function StatusBar({ message, progress }: Props) {
  const pct = Math.max(0, Math.min(100, progress))

  return (
    <footer className="status-bar">
      <span className="status-bar__msg">{message}</span>
      <div className="status-bar__progress-outer">
        <div
          className="status-bar__progress-inner"
          style={{ width: `${pct}%` }}
        />
      </div>
    </footer>
  )
}
