import { useState, useEffect, useCallback } from 'react'
import type { AppConfig, QueueJob, ConversionProgressPayload } from './types'
import SingleFileTab from './components/SingleFileTab'
import BatchTab from './components/BatchTab'
import QueuePanel from './components/QueuePanel'
import StatusBar from './components/StatusBar'

type TabId = 'single' | 'batch'

// Per-job runtime state (progress + messages) — kept in renderer memory only
export interface JobRuntime {
  progress: number
  message: string
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('single')
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [jobs, setJobs] = useState<QueueJob[]>([])
  const [jobRuntime, setJobRuntime] = useState<Record<string, JobRuntime>>({})
  const [statusMsg, setStatusMsg] = useState('Ready')
  const [globalProgress, setGlobalProgress] = useState(0)

  // ── Load config on mount ───────────────────────────────────────────────────
  useEffect(() => {
    window.electron.loadConfig().then(setConfig)
    window.electron.queueGetAll().then(setJobs)
  }, [])

  // ── IPC event subscriptions ────────────────────────────────────────────────
  useEffect(() => {
    const offProgress = window.electron.onConversionProgress(
      (payload: ConversionProgressPayload) => {
        const { jobId, progress, message } = payload
        if (progress >= 0) setGlobalProgress(progress)
        if (message) setStatusMsg(message)

        setJobRuntime(prev => ({
          ...prev,
          [jobId]: {
            progress: progress >= 0 ? progress : (prev[jobId]?.progress ?? 0),
            message:  message ?? prev[jobId]?.message ?? '',
          },
        }))
      },
    )

    const offComplete = window.electron.onConversionComplete(({ jobId }) => {
      setStatusMsg(`✓ Conversion complete`)
      setGlobalProgress(100)
      setJobRuntime(prev => ({ ...prev, [jobId]: { progress: 100, message: 'Done' } }))
      window.electron.queueGetAll().then(setJobs)
    })

    const offError = window.electron.onConversionError(({ jobId, message }) => {
      setStatusMsg(`✗ Error: ${message}`)
      setJobRuntime(prev => ({
        ...prev,
        [jobId]: { progress: 0, message: `Error: ${message}` },
      }))
      window.electron.queueGetAll().then(setJobs)
    })

    const offQueue = window.electron.onQueueChanged(setJobs)

    return () => { offProgress(); offComplete(); offError(); offQueue() }
  }, [])

  // ── Helpers passed down to tabs ────────────────────────────────────────────
  const refreshJobs = useCallback(() => {
    window.electron.queueGetAll().then(setJobs)
  }, [])

  const setStatus = useCallback((msg: string) => setStatusMsg(msg), [])
  const setProgress = useCallback((pct: number) => setGlobalProgress(pct), [])

  if (!config) {
    return (
      <div className="app" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          Loading config…
        </span>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Title bar */}
      <header className="title-bar">
        <span className="title-bar__logo">🎧</span>
        <span className="title-bar__name">PDF to Audiobook</span>
        <div className="title-bar__sep" />
        <span className="title-bar__label">Kokoro TTS · {config.engine.toUpperCase()}</span>
      </header>

      {/* Tab bar */}
      <nav className="tab-bar">
        <button
          className={`tab ${activeTab === 'single' ? 'tab--active' : ''}`}
          onClick={() => setActiveTab('single')}
        >
          Single File
        </button>
        <button
          className={`tab ${activeTab === 'batch' ? 'tab--active' : ''}`}
          onClick={() => setActiveTab('batch')}
        >
          Batch
        </button>
      </nav>

      {/* Main content */}
      <div className="content">
        {activeTab === 'single' && (
          <SingleFileTab
            config={config}
            jobRuntime={jobRuntime}
            onStatus={setStatus}
            onProgress={setProgress}
            onJobsChanged={refreshJobs}
          />
        )}
        {activeTab === 'batch' && (
          <BatchTab
            config={config}
            jobRuntime={jobRuntime}
            onStatus={setStatus}
            onProgress={setProgress}
            onJobsChanged={refreshJobs}
          />
        )}

        {/* Queue panel — visible on both tabs */}
        <QueuePanel
          jobs={jobs}
          jobRuntime={jobRuntime}
          onRemove={(id) => {
            window.electron.queueRemove(id).then(refreshJobs)
          }}
          onClear={() => window.electron.queueClear().then(refreshJobs)}
        />
      </div>

      {/* Status bar */}
      <StatusBar message={statusMsg} progress={globalProgress} />
    </div>
  )
}
