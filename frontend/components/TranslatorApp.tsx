"use client"

// components/TranslatorApp.tsx
// The main translator UI: language selector, push-to-talk button, status bar,
// and the 3 panels (detected language / translation / audio).
// Receives apiKey as a prop — undefined in demo mode, a string in BYOK mode.
// Manages session_id (persisted in sessionStorage so working memory survives reloads
// within the same browser tab, but resets on a fresh tab — matches "working memory" semantics).

import { useState, useEffect, useCallback, useRef } from "react"
import { useAudioRecorder } from "@/hooks/useAudioRecorder"
import { translateAudio, base64ToAudioUrl, fetchLanguages, Language } from "@/lib/api"
import LanguageSelector from "./LanguageSelector"
import PushToTalkButton from "./PushToTalkButton"
import StatusBar, { PipelineStage } from "./StatusBar"
import PanelDetected from "./PanelDetected"
import PanelTranslation from "./PanelTranslation"
import PanelAudio from "./PanelAudio"

interface TranslatorAppProps {
  apiKey?: string          // undefined = demo mode, string = BYOK mode
  mode: "demo" | "byok"
}

function getOrCreateSessionId(mode: string): string {
  const key = `sarvam_session_${mode}`
  if (typeof window === "undefined") return ""
  let sid = sessionStorage.getItem(key)
  if (!sid) {
    sid = crypto.randomUUID()
    sessionStorage.setItem(key, sid)
  }
  return sid
}

export default function TranslatorApp({ apiKey, mode }: TranslatorAppProps) {
  const { isRecording, volumeLevel, startRecording, stopRecording, error: micError } = useAudioRecorder()

  const [targetLanguage, setTargetLanguage] = useState("ta-IN") // Default: Tamil
  const [languages, setLanguages] = useState<Language[]>([])
  const [stage, setStage] = useState<PipelineStage>("idle")
  const [sessionId, setSessionId] = useState("")

  // Result state
  const [transcript, setTranscript] = useState<string | null>(null)
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null)
  const [detectionConfidence, setDetectionConfidence] = useState(0)
  const [rawTranslation, setRawTranslation] = useState<string | null>(null)
  const [finalTranslation, setFinalTranslation] = useState<string | null>(null)
  const [agentReasoning, setAgentReasoning] = useState<string | null>(null)
  const [glossaryUsed, setGlossaryUsed] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [ttsAvailable, setTtsAvailable] = useState(true)
  const [ttsError, setTtsError] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Each tab (demo/byok) gets its own session — matches the two-tab architecture
  useEffect(() => {
    setSessionId(getOrCreateSessionId(mode))
  }, [mode])

  useEffect(() => {
    fetchLanguages().then(setLanguages).catch(() => {})
  }, [])

  const targetLangObj = languages.find((l) => l.code === targetLanguage)

  // Revoke old audio URL when a new one is created (avoid memory leak)
  const prevAudioUrl = useRef<string | null>(null)
  useEffect(() => {
    return () => {
      if (prevAudioUrl.current) URL.revokeObjectURL(prevAudioUrl.current)
    }
  }, [])

  const handlePressEnd = useCallback(async () => {
    const blob = await stopRecording()
    if (!blob || blob.size === 0) return

    setStage("uploading")
    setErrorMessage(null)
    // Clear previous results so old data doesn't linger during processing
    setTranscript(null)
    setDetectedLanguage(null)
    setFinalTranslation(null)
    setRawTranslation(null)
    setAudioUrl(null)
    setTtsError(null)

    try {
      // We can't get true per-step server events without SSE/websockets, so we
      // advance the status bar optimistically based on expected timing —
      // this is the "perceived latency" trick from the project plan.
      setStage("transcribing")
      const resultPromise = translateAudio(blob, targetLanguage, sessionId, apiKey)

      // Advance UI stages while the single request is in flight
      const t1 = setTimeout(() => setStage("translating"), 900)
      const t2 = setTimeout(() => setStage("speaking"), 1900)

      const result = await resultPromise
      clearTimeout(t1)
      clearTimeout(t2)

      setTranscript(result.transcript)
      setDetectedLanguage(result.detected_language)
      setDetectionConfidence(result.detection_confidence)
      setRawTranslation(result.raw_translation)
      setFinalTranslation(result.final_translation)
      setAgentReasoning(result.agent_reasoning)
      setGlossaryUsed(result.glossary_used)
      setTtsAvailable(result.tts_available)
      setTtsError(result.tts_error)

      if (result.audio_base64) {
        if (prevAudioUrl.current) URL.revokeObjectURL(prevAudioUrl.current)
        const url = base64ToAudioUrl(result.audio_base64, result.audio_format)
        prevAudioUrl.current = url
        setAudioUrl(url)
      }

      setStage("done")
      setTimeout(() => setStage("idle"), 1500)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Translation failed"
      setErrorMessage(msg)
      setStage("error")
      setTimeout(() => setStage("idle"), 4000)
    }
  }, [stopRecording, targetLanguage, sessionId, apiKey])

  return (
    <div className="flex-1 flex flex-col gap-6 px-6 py-6 max-w-6xl mx-auto w-full">
      {/* Controls row */}
      <div className="flex items-center justify-between gap-6 bg-sarvam-panel border border-sarvam-border rounded-xl p-4">
        <div className="w-56">
          <LanguageSelector value={targetLanguage} onChange={setTargetLanguage} />
        </div>

        <PushToTalkButton
          isRecording={isRecording}
          volumeLevel={volumeLevel}
          disabled={stage !== "idle" && stage !== "error"}
          onPressStart={startRecording}
          onPressEnd={handlePressEnd}
        />

        {/* Spacer to balance layout */}
        <div className="w-56" />
      </div>

      {micError && (
        <div className="text-center text-sm text-red-400 bg-red-950/30 border border-red-800/40 rounded-lg px-4 py-2">
          {micError}
        </div>
      )}

      <StatusBar stage={stage} errorMessage={errorMessage} />

      {/* Three panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PanelDetected
          detectedLanguage={detectedLanguage}
          confidence={detectionConfidence}
          transcript={transcript}
          languageName={languages.find((l) => l.code === detectedLanguage)?.name || null}
        />
        <PanelTranslation
          translatedText={finalTranslation}
          rawTranslation={rawTranslation}
          agentReasoning={agentReasoning}
          glossaryUsed={glossaryUsed}
          isProcessing={stage === "uploading" || stage === "transcribing" || stage === "translating"}
        />
        <PanelAudio
          audioUrl={audioUrl}
          ttsAvailable={ttsAvailable}
          ttsError={ttsError}
          targetLanguageName={targetLangObj?.name || null}
        />
      </div>
    </div>
  )
}
