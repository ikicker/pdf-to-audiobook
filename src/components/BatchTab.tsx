/**
 * BatchTab.tsx
 * Mirrors Python's BatchConversionTable.
 *
 * Each row converts an entire folder of PDFs → a target folder.
 */

import { useState } from 'react'
import type { AppConfig } from '../types'
import type { JobRuntime } from '../App'
import PathInput from './PathInput'
import ProgressCell from './ProgressCell'

interface BatchRow {
  id:           string
  inputFolder:  string
  outputFolder: string
  voice:        string
  jobId:        string | null
  isRunning:    boolean
}

interface Props {
  config:        AppConfig
  jobRuntime:    Record<string, JobRuntime>
  onStatus:      (msg: string) => void
  onProgress:    (pct: number) => void
  onJobsChanged: () => void
}

function makeRow(defaultVoice: string): BatchRow {
  return {
    id: crypto.randomUUID(),
    inputFolder:  '',
    outputFolder: '',
    voice:        defaultVoice,
    jobId:        null,
    isRunning:    false,
  }
}

export default function BatchTab({ config, jobRuntime, onStatus, onJobsChanged }: Props) {
  const [rows, setRows] = useState<BatchRow[]>([makeRow(config.defaultVoice)])

  const updateRow = (id: string, patch: Partial<BatchRow>) =>
    setRows(prev => prev.map(r => (r.id === id ? { ...r, ...patch } : r)))

  const removeRow = (id: string) =>
    setRows(prev => prev.filter(r => r.id !== id))

  const addRow = () =>
    setRows(prev => [...prev, makeRow(config.defaultVoice)])

  const canLaunch = (r: BatchRow) =>
    !!r.inputFolder && !!r.outputFolder && !!r.voice && !r.isRunning

  const launch = async (row: BatchRow) => {
    const jobId = crypto.randomUUID()
    updateRow(row.id, { jobId, isRunning: true })
    onStatus(`Batch converting ${row.inputFolder.split(/[\\/]/).at(-1)}…`)

    try {
      await window.electron.conversionStartBatch({
        jobId,
        inputFolder:  row.inputFolder,
        outputFolder: row.outputFolder,
        voice:        row.voice,
      })
    } catch (err) {
      updateRow(row.id, { isRunning: false })
      onStatus(`Error: ${err}`)
      return
    }

    const offComplete = window.electron.onConversionComplete(({ jobId: jid }) => {
      if (jid === jobId) { updateRow(row.id, { isRunning: false }); offComplete() }
    })
    const offError = window.electron.onConversionError(({ jobId: jid }) => {
      if (jid === jobId) { updateRow(row.id, { isRunning: false }); offError() }
    })

    onJobsChanged()
  }

  const openFolder = (row: BatchRow) => {
    if (row.outputFolder) window.electron.openPath(row.outputFolder)
  }

  return (
    <div className="fade-in">
      <table className="conversion-table">
        <thead>
          <tr>
            <th style={{ width: '28%' }}>Input Folder</th>
            <th style={{ width: '13%' }}>Voice</th>
            <th style={{ width: '28%' }}>Output Folder</th>
            <th style={{ width: '16%' }}>Progress</th>
            <th style={{ width: '10%' }}>Actions</th>
            <th style={{ width: '5%'  }} />
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const rt = row.jobId ? jobRuntime[row.jobId] : null
            const isComplete = !!(row.jobId && (jobRuntime[row.jobId]?.progress ?? 0) >= 100)

            return (
              <tr key={row.id}>
                {/* Input folder */}
                <td>
                  <PathInput
                    mode="directory"
                    value={row.inputFolder}
                    placeholder="Select input folder…"
                    onChange={v => updateRow(row.id, { inputFolder: v })}
                  />
                </td>

                {/* Voice */}
                <td>
                  <select
                    className="voice-select"
                    value={row.voice}
                    onChange={e => updateRow(row.id, { voice: e.target.value })}
                    disabled={row.isRunning}
                  >
                    {config.voices.map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </td>

                {/* Output folder */}
                <td>
                  <PathInput
                    mode="directory"
                    value={row.outputFolder}
                    placeholder="Select output folder…"
                    onChange={v => updateRow(row.id, { outputFolder: v })}
                  />
                </td>

                {/* Progress */}
                <td>
                  <ProgressCell
                    progress={rt?.progress ?? 0}
                    message={rt?.message ?? ''}
                    isRunning={row.isRunning}
                    isComplete={isComplete}
                  />
                </td>

                {/* Actions */}
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button
                      className="btn btn--primary"
                      disabled={!canLaunch(row)}
                      onClick={() => launch(row)}
                      title="Launch batch"
                    >
                      {row.isRunning ? '…' : '▶ All'}
                    </button>
                    <button
                      className="btn btn--ghost"
                      disabled={!isComplete}
                      onClick={() => openFolder(row)}
                      title="Open output folder"
                    >
                      📂
                    </button>
                  </div>
                </td>

                {/* Remove */}
                <td>
                  <button
                    className="btn btn--danger"
                    onClick={() => removeRow(row.id)}
                    title="Remove row"
                  >
                    ✕
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="add-row-area">
        <button className="btn btn--add" onClick={addRow} title="Add row">＋</button>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Add batch</span>
      </div>
    </div>
  )
}
