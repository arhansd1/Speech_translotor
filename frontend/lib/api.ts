// lib/api.ts
// Typed wrappers around every backend route.
// All fetch calls go through here — never raw fetch() in components.
// apiKey: undefined = demo mode (backend uses its env key)
//         string    = BYOK mode (sent in X-Sarvam-Key header)

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

export interface Language {
  code: string
  name: string
  script: string
  tts_supported: boolean
}

export interface TranslateResult {
  session_id: string
  transcript: string
  raw_translation: string
  final_translation: string
  detected_language: string
  detection_confidence: number
  source_language: string
  target_language: string
  tts_available: boolean
  audio_base64: string | null
  audio_format: string
  agent_reasoning: string
  glossary_used: boolean
  tts_error: string | null
}

export interface TextTranslateResult {
  session_id: string
  input_text: string
  raw_translation: string
  final_translation: string
  tts_available: boolean
  audio_base64: string | null
  agent_reasoning: string
  glossary_used: boolean
}

// Build headers — adds X-Sarvam-Key only if apiKey is provided (BYOK mode)
function headers(apiKey?: string): HeadersInit {
  const h: Record<string, string> = {}
  if (apiKey) h["X-Sarvam-Key"] = apiKey
  return h
}

// ── Fetch all supported languages ──────────────────────────────────────────
export async function fetchLanguages(): Promise<Language[]> {
  const resp = await fetch(`${BACKEND}/languages`)
  if (!resp.ok) throw new Error("Failed to fetch languages")
  const data = await resp.json()
  return data.languages as Language[]
}

// ── Translate audio (main pipeline) ────────────────────────────────────────
export async function translateAudio(
  audioBlob: Blob,
  targetLanguage: string,
  sessionId: string,
  apiKey?: string,
): Promise<TranslateResult> {
  const form = new FormData()
  form.append("audio", audioBlob, "recording.webm")
  form.append("target_language", targetLanguage)
  form.append("session_id", sessionId)

  const resp = await fetch(`${BACKEND}/translate`, {
    method: "POST",
    headers: headers(apiKey),
    body: form,
  })

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || "Translation failed")
  }

  return resp.json() as Promise<TranslateResult>
}

// ── Translate text (for testing without audio) ─────────────────────────────
export async function translateText(
  text: string,
  sourceLang: string,
  targetLang: string,
  sessionId: string,
  apiKey?: string,
): Promise<TextTranslateResult> {
  const resp = await fetch(`${BACKEND}/translate/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers(apiKey) },
    body: JSON.stringify({
      text,
      source_language: sourceLang,
      target_language: targetLang,
      session_id: sessionId,
    }),
  })

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || "Text translation failed")
  }

  return resp.json() as Promise<TextTranslateResult>
}

// ── Health check ───────────────────────────────────────────────────────────
export async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${BACKEND}/health`, { cache: "no-store" })
    return resp.ok
  } catch {
    return false
  }
}

// ── Decode base64 audio to playable URL ────────────────────────────────────
export function base64ToAudioUrl(b64: string, format = "wav"): string {
  const binary = atob(b64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  const blob = new Blob([bytes], { type: `audio/${format}` })
  return URL.createObjectURL(blob)
}
