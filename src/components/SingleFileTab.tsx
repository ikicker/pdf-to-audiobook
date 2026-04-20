/**
 * SingleFileTab.tsx
 * Mirrors Python's SingleFileConversionTable.
 *
 * Each row = one PDF → audio conversion.
 * Conversion is dispatched to the main process via IPC, which spawns Python.
 */

import { useState, useId } from 'react'
import type { AppConfig } from '../types'
import type { JobRuntime } from '../App'
import PathInput from './PathInput'
import ProgressCell from './ProgressCell'

interface RowState {
  id: string
  inputFile:  string
  outputFile: string
  voice:      string
  jobId:      string | null   // null = not started
  isRunning:  boolean
}

interface Props {
  config:        AppConfig
  jobRuntime:    Record<string, JobRuntime>
  onStatus:      (msg: string) => void
  onProgress:    (pct: number) => void
  onJobsChanged: () => void
}

function makeRow(defaultVoice: string): RowState {
  return {
    id: crypto.randomUUID(),
    inputFile:  '',
    outputFile: '',
    voice:      defaultVoice,
    jobId:      null,
    isRunning:  false,
  }
}

export default function SingleFileTab({ config, jobRuntime, onStatus, onJobsChanged }: Props) {
  const [rows, setRows] = useState<RowState[]>([makeRow(config.defaultVoice)])

  const updateRow = (id: string, patch: Partial<RowState>) =>
    setRows(prev => prev.map(r => (r.id === id ? { ...r, ...patch } : r)))

  const removeRow = (id: string) =>
    setRows(prev => prev.filter(r => r.id !== id))

  const addRow = () =>
    setRows(prev => [...prev, makeRow(config.defaultVoice)])

  const canLaunch = (r: RowState) =>
    !!r.inputFile && !!r.outputFile && !!r.voice // && !r.isRunning

  const launch = async (row: RowState) => {
    const jobId = crypto.randomUUID()
    updateRow(row.id, { jobId, isRunning: true })
    onStatus(`Converting ${row.inputFile.split(/[\\/]/).at(-1)}…`)

    try {
      await window.electron.conversionStart({
        jobId,
        inputFile:  row.inputFile,
        outputFile: row.outputFile,
        voice:      row.voice,
      })
    } catch (err) {
      updateRow(row.id, { isRunning: false })
      onStatus(`Error: ${err}`)
      return
    }

    // conversionComplete / conversionError arrive via IPC events in App.tsx.
    // We listen here just to reset isRunning on that specific row.
    const offComplete = window.electron.onConversionComplete(({ jobId: jid }) => {
      if (jid === jobId) { updateRow(row.id, { isRunning: false }); offComplete() }
    })
    const offError = window.electron.onConversionError(({ jobId: jid }) => {
      if (jid === jobId) { updateRow(row.id, { isRunning: false }); offError() }
    })

    onJobsChanged()
  }

  const play = (row: RowState) => {
    if (row.outputFile) window.electron.playFile(row.outputFile)
  }

  const completedJobId = (row: RowState) =>
    row.jobId && (jobRuntime[row.jobId]?.progress ?? 0) >= 100 ? row.jobId : null

  return (
    <div className="fade-in">
      <table className="conversion-table">
        <thead>
          <tr>
            <th style={{ width: '28%' }}>Input PDF</th>
            <th style={{ width: '13%' }}>Voice</th>
            <th style={{ width: '28%' }}>Output File</th>
            <th style={{ width: '16%' }}>Progress</th>
            <th style={{ width: '8%'  }}>Actions</th>
            <th style={{ width: '5%'  }} />
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            const rt = row.jobId ? jobRuntime[row.jobId] : null
            const isComplete = !!completedJobId(row)

            return (
              <tr key={row.id}>
                {/* Input PDF */}
                <td>
                  <PathInput
                    mode="file-open-pdf"
                    value={row.inputFile}
                    placeholder="Select PDF…"
                    onChange={v => updateRow(row.id, { inputFile: v })}
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

                {/* Output file */}
                <td>
                  <PathInput
                    mode="file-save-audio"
                    value={row.outputFile}
                    placeholder="Save as…"
                    onChange={v => updateRow(row.id, { outputFile: v })}
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
                      title="Start conversion"
                    >
                      {row.isRunning ? '…' : '▶'}
                    </button>
                    <button
                      className="btn btn--ghost"
                      disabled={!isComplete}
                      onClick={() => play(row)}
                      title="Play output"
                    >
                      ♪
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

      {/* Add row */}
      <div className="add-row-area">
        <button className="btn btn--add" onClick={addRow} title="Add row">＋</button>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Add conversion</span>
      </div>
    </div>
  )
}
