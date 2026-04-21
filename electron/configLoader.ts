import { readFileSync, existsSync } from 'fs'
import { join } from 'path'
import { parse } from 'smol-toml'
import type { AppConfig } from '../src/types'

/**
 * Loads application config from pyproject.toml (mirrors Python load_config()).
 * Falls back to sensible defaults if the file is missing or malformed.
 */
export function loadConfig(configPath?: string): AppConfig {
  const tomlPath = configPath ?? join(process.cwd(), 'pyproject.toml')

  const defaults: AppConfig = {
    voices: [
      'af_heart', 'af_bella', 'af_nicole', 'af_sarah', 'af_sky',
      'af_jessica', 'am_adam', 'am_michael', 'bf_emma', 'bf_isabella',
      'bm_george', 'bm_lewis',
    ],
    engine: 'kokoro',
    defaultVoice: 'af_heart',
    langCode: 'a',
    outputPath: 'audiobook.mp3',
    maxWordsPerChunk: 350,
    pauseBetweenChunksSec: 0.6,
    ffmpeg: 'ffmpeg.exe',
    ffprobe: 'ffprobe.exe',
    ffplay: 'ffplay.exe',
  }

  if (!existsSync(tomlPath)) {
    console.warn(`[config] pyproject.toml not found at ${tomlPath} — using defaults.`)
    return defaults
  }

  try {
    const raw = readFileSync(tomlPath, 'utf-8')
    const data = parse(raw) as Record<string, unknown>

    const tool = (data.tool as Record<string, unknown>) ?? {}
    const app  = (tool['pdf-to-audiobook'] as Record<string, unknown>) ?? {}
    const tts  = (app.tts as Record<string, unknown>) ?? {}
    const paths = (app.paths as Record<string, unknown>) ?? {}
    const proc  = (app.processing as Record<string, unknown>) ?? {}
    const ext   = (app.external_tools as Record<string, unknown>) ?? {}
    const drop  = (data.dropdowns as Record<string, unknown>) ?? {}

    return {
      voices:               (drop.voices as string[]) ?? defaults.voices,
      engine:               (tts.engine  as string)  ?? defaults.engine,
      defaultVoice:         (tts.voice   as string)  ?? defaults.defaultVoice,
      langCode:             (tts.lang_code as string) ?? defaults.langCode,
      outputPath:           (paths.output as string) ?? defaults.outputPath,
      maxWordsPerChunk:     (proc.max_words_per_chunk as number) ?? defaults.maxWordsPerChunk,
      pauseBetweenChunksSec:(proc.pause_between_chunks_sec as number) ?? defaults.pauseBetweenChunksSec,
      ffmpeg:               (ext.ffmpeg  as string)  ?? defaults.ffmpeg,
      ffprobe:              (ext.ffprobe as string)  ?? defaults.ffprobe,
      ffplay:               (ext.ffplay  as string)  ?? defaults.ffplay,
    }
  } catch (e) {
    console.error('[config] Failed to parse pyproject.toml:', e)
    return defaults
  }
}
