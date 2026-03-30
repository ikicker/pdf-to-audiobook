// ─── Queue & Job Types ───────────────────────────────────────────────────────

export type JobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'error'

export interface QueueJob {
  id: string
  inputFile: string
  outputFile: string
  voice: string
  status: JobStatus
  progress: number          // 0-100
  errorMessage?: string
  createdAt: number
}

// ─── Config ──────────────────────────────────────────────────────────────────

export interface AppConfig {
  voices: string[]
  engine: string
  defaultVoice: string
  langCode: string
  outputPath: string
  maxWordsPerChunk: number
  pauseBetweenChunksSec: number
  ffmpeg: string
  ffprobe: string
  ffplay: string
}

// ─── IPC Channel Payloads ────────────────────────────────────────────────────

export interface DialogOpenFileResult {
  canceled: boolean
  filePaths: string[]
}

export interface DialogSaveFileResult {
  canceled: boolean
  filePath?: string
}

export interface DialogOpenDirResult {
  canceled: boolean
  filePaths: string[]
}

export interface ConversionStartPayload {
  jobId: string
  inputFile: string
  outputFile: string
  voice: string
}

export interface ConversionProgressPayload {
  jobId: string
  progress: number
  message?: string
}

export interface ConversionCompletePayload {
  jobId: string
}

export interface ConversionErrorPayload {
  jobId: string
  message: string
}

export interface BatchConversionStartPayload {
  jobId: string
  inputFolder: string
  outputFolder: string
  voice: string
}

// ─── IPC API exposed via contextBridge ───────────────────────────────────────

export interface ElectronAPI {
  // Config
  loadConfig: () => Promise<AppConfig>

  // File dialogs
  dialogOpenFile: (filter?: string) => Promise<DialogOpenFileResult>
  dialogSaveFile: (filter?: string) => Promise<DialogSaveFileResult>
  dialogOpenDir: () => Promise<DialogOpenDirResult>

  // Queue
  queueAdd: (inputFile: string, outputFile: string, voice: string) => Promise<QueueJob>
  queueGetAll: () => Promise<QueueJob[]>
  queueRemove: (jobId: string) => Promise<void>
  queueClear: () => Promise<void>

  // Conversion (direct — not queued)
  conversionStart: (payload: ConversionStartPayload) => Promise<void>
  conversionStartBatch: (payload: BatchConversionStartPayload) => Promise<void>

  // Conversion events (main → renderer)
  onConversionProgress: (cb: (payload: ConversionProgressPayload) => void) => () => void
  onConversionComplete: (cb: (payload: ConversionCompletePayload) => void) => () => void
  onConversionError: (cb: (payload: ConversionErrorPayload) => void) => () => void
  onQueueChanged: (cb: (jobs: QueueJob[]) => void) => () => void

  // Audio playback
  playFile: (filePath: string) => Promise<void>
  openPath: (filePath: string) => Promise<void>

  // Platform
  platform: NodeJS.Platform
}

declare global {
  interface Window {
    electron: ElectronAPI
  }
}
