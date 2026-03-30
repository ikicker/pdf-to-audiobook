/**
 * QueuePanel.tsx
 * Shows all jobs persisted in the queue/ folder.
 * Mirrors the queue management from Queue.py / QueueService.py.
 */

import type { QueueJob } from '../types'
import type { JobRuntime } from '../App'

interface Props {
  jobs:       QueueJob[]
  jobRuntime: Record<string, JobRuntime>
  onRemove:   (jobId: string) => void
  onClear:    () => void
}

const STATUS_LABELS: Record<string, string> = {
  pending:   'Pending',
  running:   'Running',
  completed: 'Done',
  error:     'Error',
}

function baseName(p: string) {
  return p.replace(/\\/g, '/').split('/').at(-1) ?? p
}

export default function QueuePanel({ jobs, jobRuntime, onRemove, onClear }: Props) {
  return (
    <div className="queue-panel" style={{ marginTop: 16 }}>
      <div className="queue-panel__header">
        <span className="queue-panel__title">
          Queue
          {jobs.length > 0 && (
            <span style={{ marginLeft: 8, color: 'var(--amber)', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
              {jobs.length}
            </span>
          )}
        </span>
        {jobs.length > 0 && (
          <button
            className="btn btn--ghost"
            style={{ fontSize: 10, padding: '2px 8px' }}
            onClick={onClear}
          >
            Clear all
          </button>
        )}
      </div>

      <div className="queue-panel__body">
        {jobs.length === 0 ? (
          <div className="queue-empty">No jobs queued</div>
        ) : (
          jobs.map(job => {
            const rt    = jobRuntime[job.id]
            const pct   = rt?.progress ?? (job.status === 'completed' ? 100 : 0)
            const label = STATUS_LABELS[job.status] ?? job.status

            const chipClass =
              job.status === 'pending'   ? 'status-chip status-chip--pending'   :
              job.status === 'running'   ? 'status-chip status-chip--running'   :
              job.status === 'completed' ? 'status-chip status-chip--completed' :
                                          'status-chip status-chip--error'

            return (
              <div key={job.id} className="queue-row">
                {/* Input */}
                <span className="queue-row__path" title={job.inputFile}>
                  {baseName(job.inputFile)}
                </span>

                {/* Output */}
                <span className="queue-row__path" title={job.outputFile}>
                  {baseName(job.outputFile)}
                </span>

                {/* Progress bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div className="progress-bar-outer" style={{ flex: 1 }}>
                    <div
                      className={`progress-bar-inner${
                        job.status === 'completed' ? ' progress-bar-inner--complete' :
                        job.status === 'error'     ? ' progress-bar-inner--error'    :
                        job.status === 'running'   ? ' pulse'                        : ''
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="progress-pct">{pct > 0 ? `${pct}%` : ''}</span>
                </div>

		{/* Status chip */}
                <span className={chipClass}>{label}</span>

                {/* Actions (Play & Remove) */}
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    className="btn btn--ghost"
                    disabled={job.status !== 'completed'}
                    onClick={() => window.electron.playFile(job.outputFile)}
                    title={job.status === 'completed' ? "Play audio" : "Waiting for conversion to finish..."}
                    style={{ fontSize: 10, padding: '4px 8px' }}
                  >
                    ♪
                  </button>
                  <button
                    className="btn btn--danger"
                    onClick={() => onRemove(job.id)}
                    title="Remove from queue"
                    style={{ fontSize: 10, padding: '4px 8px' }}
                  >
                    ✕
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
