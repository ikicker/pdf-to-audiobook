/**
 * main.ts — Electron main process
 *
 * Responsibilities:
 *  • Create the BrowserWindow
 *  • Register all IPC handlers (file dialogs, queue, conversion, audio)
 *  • Spawn Python (PDF_to_Audiobook.py) as a child process for conversions
 *  • Broadcast progress / completion events back to the renderer
 */

import {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  shell,
  IpcMainInvokeEvent,
} from 'electron'
import { join, dirname, basename, extname } from 'path'
import { spawn, ChildProcess } from 'child_process'
import { readdirSync } from 'fs'
import { fileURLToPath } from 'url'

import { loadConfig } from './configLoader'
import {
  addJob,
  getAllJobs,
  removeJob,
  clearQueue,
  updateJob,
  markRunning,
  markCompleted,
  markError,
  nextPendingJob,
} from './queue'
import type {
  ConversionStartPayload,
  ConversionErrorPayload,
  BatchConversionStartPayload,
} from '../src/types'

// ─── Resolve __dirname in ESM ─────────────────────────────────────────────────
const __filename = fileURLToPath(import.meta.url)
const __dirname  = dirname(__filename)

// ─── Active conversion processes (jobId → ChildProcess) ──────────────────────
const activeProcesses = new Map<string, ChildProcess>()

// ─── Window factory ──────────────────────────────────────────────────────────
function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1100,
    height: 700,
    minWidth: 800,
    minHeight: 560,
    backgroundColor: '#0e0e0f',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  if (process.env.NODE_ENV === 'development' || process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL!)
    win.webContents.openDevTools({ mode: 'detach' })
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return win
}

// ─── App lifecycle ────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  const mainWin = createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })

  // ─── Background Queue Worker ────────────────────────────────────────────────
  let isProcessingQueue = false

  async function processQueue() {
    if (isProcessingQueue) return
    isProcessingQueue = true

    try {
      while (true) {
        const job = nextPendingJob()
        if (!job) break // No more pending jobs, sleep worker

        await new Promise<void>((resolve) => {
          spawnConversion(
            job.id,
            job.inputFile,
            job.outputFile,
            job.voice,
            mainWin,
            () => resolve(), // On success, resolve to move to next job
            () => resolve()  // On error, resolve anyway so the queue doesn't stall completely
          )
        })
      }
    } finally {
      isProcessingQueue = false
    }
  }

  // ── Config ─────────────────────────────────────────────────────────────────
  ipcMain.handle('config:load', () => loadConfig())

  // ── File Dialogs ───────────────────────────────────────────────────────────
  ipcMain.handle('dialog:openFile', async (_e: IpcMainInvokeEvent, filter?: string) => {
    const filters =
      filter === 'pdf'
        ?[{ name: 'PDF Files', extensions: ['pdf'] }]
        : [
            { name: 'Audio Files', extensions:['mp3', 'wav'] },
            { name: 'All Files',   extensions: ['*'] },
          ]
    return dialog.showOpenDialog(mainWin, { properties: ['openFile'], filters })
  })

  ipcMain.handle('dialog:saveFile', async (_e: IpcMainInvokeEvent, filter?: string) => {
    const filters =
      filter === 'audio'
        ?[{ name: 'Audio Files', extensions: ['mp3', 'wav'] }]
        : [{ name: 'All Files', extensions:['*'] }]
    return dialog.showSaveDialog(mainWin, { filters })
  })

  ipcMain.handle('dialog:openDir', async () => {
    return dialog.showOpenDialog(mainWin, { properties: ['openDirectory'] })
  })

  // ── Queue ──────────────────────────────────────────────────────────────────
  ipcMain.handle('queue:add', (_e, inputFile: string, outputFile: string, voice: string) => {
    const job = addJob(inputFile, outputFile, voice)
    mainWin.webContents.send('queue:changed', getAllJobs())
    processQueue() // Wake up worker
    return job
  })

  ipcMain.handle('queue:getAll', () => getAllJobs())

  ipcMain.handle('queue:remove', (_e, jobId: string) => {
    removeJob(jobId)
    mainWin.webContents.send('queue:changed', getAllJobs())
  })

  ipcMain.handle('queue:clear', () => {
    clearQueue()
    mainWin.webContents.send('queue:changed',[])
  })

  // ── Conversion (single file) ───────────────────────────────────────────────
  ipcMain.handle('conversion:start', async (_e, payload: ConversionStartPayload) => {
    const { jobId, inputFile, outputFile, voice } = payload

    // Add to queue using the React UI's specific jobId so the table row updates
    addJob(inputFile, outputFile, voice, jobId)
    mainWin.webContents.send('queue:changed', getAllJobs())

    // Wake up worker
    processQueue()
  })

  // ── Conversion (batch — folder of PDFs) ───────────────────────────────────
  ipcMain.handle('conversion:startBatch', async (_e, payload: BatchConversionStartPayload) => {
    const { jobId, inputFolder, outputFolder, voice } = payload

    let pdfFiles: string[]
    try {
      pdfFiles = readdirSync(inputFolder).filter(f => f.toLowerCase().endsWith('.pdf'))
    } catch {
      mainWin.webContents.send('conversion:error', {
        jobId,
        message: `Cannot read folder: ${inputFolder}`,
      } satisfies ConversionErrorPayload)
      return
    }

    if (pdfFiles.length === 0) {
      mainWin.webContents.send('conversion:error', {
        jobId,
        message: 'No PDF files found in the selected folder.',
      } satisfies ConversionErrorPayload)
      return
    }

    // Add each file to the queue
    for (let i = 0; i < pdfFiles.length; i++) {
      const pdfName = pdfFiles[i]
      const inputFile  = join(inputFolder, pdfName)
      const baseName   = basename(pdfName, extname(pdfName))
      const outputFile = join(outputFolder, `${baseName}.mp3`)

      // Append _i to the batch job ID so each file in the batch has a unique ID in the queue
      addJob(inputFile, outputFile, voice, `${jobId}_${i}`)
    }

    mainWin.webContents.send('queue:changed', getAllJobs())

    // Kick off the queue
    processQueue()

    // Fake the batch task progress for the UI (so the main UI row says complete)
    mainWin.webContents.send('conversion:progress', { jobId, progress: 100, message: `Queued ${pdfFiles.length} files.` })
    mainWin.webContents.send('conversion:complete', { jobId })
  })

  // ── Audio playback ─────────────────────────────────────────────────────────
  ipcMain.handle('file:play', async (_e, filePath: string) => {
    const cfg = loadConfig()
    if (cfg.ffplay) {
      spawn(cfg.ffplay, ['-autoexit', '-i', filePath], { detached: true })
    } else {
      await shell.openPath(filePath)
    }
  })

  ipcMain.handle('file:open', async (_e, filePath: string) => {
    await shell.openPath(filePath)
  })

})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// ─── Helper: spawn Python conversion process ──────────────────────────────────
function spawnConversion(
  jobId: string,
  inputFile: string,
  outputFile: string,
  voice: string,
  win: BrowserWindow,
  onSuccess?: () => void,
  onError?: (err: string) => void,
): void {
  // Determine Python executable — support venv or system Python
  const pythonExe =
    process.platform === 'win32'
      ? join(process.cwd(), 'audiobook_env', 'Scripts', 'python.exe')
      : join(process.cwd(), 'audiobook_env', 'bin', 'python')

  const scriptPath = join(process.cwd(), 'PDF_to_Audiobook.py')

  const args =[scriptPath, inputFile, outputFile, '--voice', voice]

  markRunning(jobId)
  win.webContents.send('conversion:progress', { jobId, progress: 0, message: 'Starting…' })
  win.webContents.send('queue:changed', getAllJobs())

  let stderrBuf = ''

  const child = spawn(pythonExe, args, {
    cwd: process.cwd(),
    stdio:['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,               // Keep all existing environment variables
      PYTHONIOENCODING: 'utf-8',    // Force Python to output in UTF-8 so emojis don't crash it!
    }
  })

  activeProcesses.set(jobId, child)

  // Parse stdout for tqdm-style progress lines
  child.stdout?.on('data', (chunk: Buffer) => {
    const lines = chunk.toString().split('\n')
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue

      // Parse percentage from lines like "Generating:  34%|████..."
      const pctMatch = trimmed.match(/(\d+)%\|/)
      if (pctMatch) {
        const progress = parseInt(pctMatch[1], 10)
        updateJob(jobId, { progress })
        win.webContents.send('conversion:progress', { jobId, progress })
        continue
      }

      // Forward other stdout lines as status messages
      win.webContents.send('conversion:progress', { jobId, progress: -1, message: trimmed })
    }
  })

  child.stderr?.on('data', (chunk: Buffer) => {
    stderrBuf += chunk.toString()
  })

  child.on('close', (code) => {
    activeProcesses.delete(jobId)

    if (code === 0) {
      markCompleted(jobId)
      win.webContents.send('conversion:progress', { jobId, progress: 100 })
      win.webContents.send('conversion:complete',  { jobId })
      win.webContents.send('queue:changed', getAllJobs())
      onSuccess?.()
    } else {
      const errMsg = stderrBuf.trim() || `Process exited with code ${code}`

      console.error(pythonExe, args, stderrBuf.trim(), '\n=== PYTHON CRASHED ===\n', errMsg, '\n======================\n')

      markError(jobId, errMsg)
      win.webContents.send('conversion:error', { jobId, message: errMsg })
      win.webContents.send('queue:changed', getAllJobs())
      onError?.(errMsg)
    }
  })

  child.on('error', (err) => {
    activeProcesses.delete(jobId)
    const message = `Failed to start Python: ${err.message}\n\nMake sure ${pythonExe} exists and PDF_to_Audiobook.py is present.`
    markError(jobId, message)
    win.webContents.send('conversion:error', { jobId, message })
    win.webContents.send('queue:changed', getAllJobs())
    onError?.(message)
  })
}
