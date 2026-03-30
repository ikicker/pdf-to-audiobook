/**
 * preload.ts — Electron preload script
 *
 * Exposes a typed, secure API to the renderer via contextBridge.
 * The renderer accesses everything through window.electron.
 */

import { contextBridge, ipcRenderer } from 'electron'
import type {
  AppConfig,
  QueueJob,
  ConversionStartPayload,
  BatchConversionStartPayload,
  ConversionProgressPayload,
  ConversionCompletePayload,
  ConversionErrorPayload,
  ElectronAPI,
} from '../src/types'

const api: ElectronAPI = {
  // ── Config ──────────────────────────────────────────────────────────────────
  loadConfig: (): Promise<AppConfig> =>
    ipcRenderer.invoke('config:load'),

  // ── Dialogs ─────────────────────────────────────────────────────────────────
  dialogOpenFile: (filter?: string) =>
    ipcRenderer.invoke('dialog:openFile', filter),

  dialogSaveFile: (filter?: string) =>
    ipcRenderer.invoke('dialog:saveFile', filter),

  dialogOpenDir: () =>
    ipcRenderer.invoke('dialog:openDir'),

  // ── Queue ───────────────────────────────────────────────────────────────────
  queueAdd: (inputFile: string, outputFile: string, voice: string): Promise<QueueJob> =>
    ipcRenderer.invoke('queue:add', inputFile, outputFile, voice),

  queueGetAll: (): Promise<QueueJob[]> =>
    ipcRenderer.invoke('queue:getAll'),

  queueRemove: (jobId: string): Promise<void> =>
    ipcRenderer.invoke('queue:remove', jobId),

  queueClear: (): Promise<void> =>
    ipcRenderer.invoke('queue:clear'),

  // ── Conversion ──────────────────────────────────────────────────────────────
  conversionStart: (payload: ConversionStartPayload): Promise<void> =>
    ipcRenderer.invoke('conversion:start', payload),

  conversionStartBatch: (payload: BatchConversionStartPayload): Promise<void> =>
    ipcRenderer.invoke('conversion:startBatch', payload),

  // ── Event listeners (main → renderer) ───────────────────────────────────────
  onConversionProgress: (cb) => {
    const handler = (_e: Electron.IpcRendererEvent, payload: ConversionProgressPayload) =>
      cb(payload)
    ipcRenderer.on('conversion:progress', handler)
    return () => ipcRenderer.off('conversion:progress', handler)
  },

  onConversionComplete: (cb) => {
    const handler = (_e: Electron.IpcRendererEvent, payload: ConversionCompletePayload) =>
      cb(payload)
    ipcRenderer.on('conversion:complete', handler)
    return () => ipcRenderer.off('conversion:complete', handler)
  },

  onConversionError: (cb) => {
    const handler = (_e: Electron.IpcRendererEvent, payload: ConversionErrorPayload) =>
      cb(payload)
    ipcRenderer.on('conversion:error', handler)
    return () => ipcRenderer.off('conversion:error', handler)
  },

  onQueueChanged: (cb) => {
    const handler = (_e: Electron.IpcRendererEvent, jobs: QueueJob[]) => cb(jobs)
    ipcRenderer.on('queue:changed', handler)
    return () => ipcRenderer.off('queue:changed', handler)
  },

  // ── Audio / File ops ────────────────────────────────────────────────────────
  playFile: (filePath: string): Promise<void> =>
    ipcRenderer.invoke('file:play', filePath),

  openPath: (filePath: string): Promise<void> =>
    ipcRenderer.invoke('file:open', filePath),

  // ── Platform info ────────────────────────────────────────────────────────────
  platform: process.platform,
}

contextBridge.exposeInMainWorld('electron', api)
