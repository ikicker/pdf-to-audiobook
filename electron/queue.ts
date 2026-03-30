/**
 * queue.ts
 * Node.js port of Queue.py and QueueService.py.
 *
 * Jobs are persisted on disk inside a `queue/` folder (one file per job,
 * named by job ID) so they survive app restarts — mirroring the Python
 * file-per-job approach.
 */

import { mkdirSync, readdirSync, readFileSync, writeFileSync, unlinkSync, existsSync } from 'fs'
import { join } from 'path'
import { randomUUID } from 'crypto'
import type { QueueJob, JobStatus } from '../src/types'

const QUEUE_DIR = join(process.cwd(), 'queue')

function ensureQueueDir(): void {
  if (!existsSync(QUEUE_DIR)) mkdirSync(QUEUE_DIR, { recursive: true })
}

function jobPath(jobId: string): string {
  return join(QUEUE_DIR, `${jobId}.json`)
}

// ─── Public API ──────────────────────────────────────────────────────────────

/** Persist a new job and return it. */
export function addJob(inputFile: string, outputFile: string, voice: string, id?: string): QueueJob {
  ensureQueueDir()

  const job: QueueJob = {
    id: id || randomUUID(), // Use the provided ID, or generate a new one
    inputFile,
    outputFile,
    voice,
    status: 'pending',
    progress: 0,
    createdAt: Date.now(),
  }

  writeFileSync(jobPath(job.id), JSON.stringify(job, null, 2), 'utf-8')
  return job
}

/** Read all persisted jobs, sorted oldest-first. */
export function getAllJobs(): QueueJob[] {
  ensureQueueDir()

  const files = readdirSync(QUEUE_DIR).filter(f => f.endsWith('.json'))
  return files
    .map(f => {
      try { return JSON.parse(readFileSync(join(QUEUE_DIR, f), 'utf-8')) as QueueJob }
      catch { return null }
    })
    .filter(Boolean)
    .sort((a, b) => (a!.createdAt - b!.createdAt)) as QueueJob[]
}

/** Update a job's fields and re-persist. */
export function updateJob(jobId: string, patch: Partial<QueueJob>): QueueJob | null {
  const path = jobPath(jobId)
  if (!existsSync(path)) return null

  const job: QueueJob = { ...JSON.parse(readFileSync(path, 'utf-8')), ...patch }
  writeFileSync(path, JSON.stringify(job, null, 2), 'utf-8')
  return job
}

/** Remove a job from the queue (mirrors remove_from_queue). */
export function removeJob(jobId: string): void {
  const path = jobPath(jobId)
  if (existsSync(path)) unlinkSync(path)
}

/** Remove all jobs. */
export function clearQueue(): void {
  ensureQueueDir()
  readdirSync(QUEUE_DIR)
    .filter(f => f.endsWith('.json'))
    .forEach(f => unlinkSync(join(QUEUE_DIR, f)))
}

/** Return the next pending job (FIFO), or null if the queue is empty. */
export function nextPendingJob(): QueueJob | null {
  return getAllJobs().find(j => j.status === 'pending') ?? null
}

/** Convenience: mark a job as running. */
export function markRunning(jobId: string): QueueJob | null {
  return updateJob(jobId, { status: 'running' as JobStatus, progress: 0 })
}

/** Convenience: mark a job as completed. */
export function markCompleted(jobId: string): QueueJob | null {
  return updateJob(jobId, { status: 'completed' as JobStatus, progress: 100 })
}

/** Convenience: mark a job as errored. */
export function markError(jobId: string, message: string): QueueJob | null {
  return updateJob(jobId, { status: 'error' as JobStatus, errorMessage: message })
}
