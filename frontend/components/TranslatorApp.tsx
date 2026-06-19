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
import PushToTalkButton from "./PushToTalkButton"
import PanelAudio from "./PanelAudio"

type PipelineStage =
  | "idle"
  | "uploading"
  | "transcribing"
  | "translating"
  | "speaking"
  | "done"
  | "error"

interface TranslatorAppProps {
  apiKey?: string          // undefined = demo mode, string = BYOK mode
  mode: "demo" | "byok"
  targetLanguage: string
  onTargetLanguageChange: (lang: string) => void
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

export default function TranslatorApp({ apiKey, mode, targetLanguage, onTargetLanguageChange }: TranslatorAppProps) {
  const { isRecording, volumeLevel, startRecording, stopRecording, error: micError } = useAudioRecorder()

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
  const [showReasoning, setShowReasoning] = useState(false)
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
    <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Two-column split layout */}
      <div className="flex-1 flex border-l border-terminal-border">
        {/* Left panel - SOURCE */}
        <div className="flex-1 flex flex-col border-r border-terminal-border">
          {/* Top row with label and badge */}
          <div className="flex items-center justify-between px-6 py-3 border-b border-terminal-border">
            <span className="label-mono">01 · SOURCE</span>
            <span className={`px-3 py-1 text-[10px] font-mono uppercase tracking-wider border ${
              detectedLanguage 
                ? "border-terminal-orange text-terminal-orange" 
                : "border-terminal-muted text-terminal-muted"
            }`}>
              DETECTED · {detectedLanguage || "—"}
            </span>
          </div>

          {/* Center - mic button */}
          <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6">
            <PushToTalkButton
              isRecording={isRecording}
              volumeLevel={volumeLevel}
              disabled={stage !== "idle" && stage !== "error"}
              onPressStart={startRecording}
              onPressEnd={handlePressEnd}
            />

            {/* Status line */}
            {stage !== "idle" && stage !== "error" && (
              <span className="text-[11px] font-mono text-terminal-orange uppercase tracking-wider">
                {stage === "uploading" && "UPLOADING..."}
                {stage === "transcribing" && "TRANSCRIBING..."}
                {stage === "translating" && "TRANSLATING..."}
                {stage === "speaking" && "GENERATING SPEECH..."}
                {stage === "done" && "DONE"}
              </span>
            )}
          </div>

          {/* Bottom - transcript */}
          <div className="border-t border-terminal-border px-6 py-4">
            <span className="label-mono block mb-2">TRANSCRIPT ({detectedLanguage || "—"})</span>
            {transcript ? (
              <p className="body-text text-terminal-bright">
                {transcript}
              </p>
            ) : (
              <p className="body-text text-terminal-muted">
                Hold the mic and speak...
              </p>
            )}
          </div>
        </div>

        {/* Right panel - TARGET */}
        <div className="flex-1 flex flex-col">
          {/* Top row with label and badge */}
          <div className="flex items-center justify-between px-6 py-3 border-b border-terminal-border">
            <span className="label-mono">02 · TARGET · {targetLanguage}</span>
            <span className={`px-3 py-1 text-[10px] font-mono uppercase tracking-wider border ${
              stage === "idle" || stage === "error"
                ? "border-terminal-muted text-terminal-muted"
                : stage === "done"
                ? "border-terminal-mint text-terminal-mint"
                : "border-terminal-orange text-terminal-orange"
            }`}>
              {stage === "idle" && "IDLE"}
              {stage === "uploading" && "UPLOADING"}
              {stage === "transcribing" && "TRANSCRIBING"}
              {stage === "translating" && "TRANSLATING"}
              {stage === "speaking" && "SPEAKING"}
              {stage === "done" && "DONE"}
              {stage === "error" && "ERROR"}
            </span>
          </div>

          {/* Center - audio player */}
          <div className="flex-1 flex flex-col items-center justify-center px-6">
            <PanelAudio
              audioUrl={audioUrl}
              ttsAvailable={ttsAvailable}
              ttsError={ttsError}
              targetLanguageName={targetLangObj?.name || null}
            />
          </div>

          {/* Bottom - translation */}
          <div className="border-t border-terminal-border px-6 py-4">
            <span className="label-mono block mb-2">TRANSLATION</span>
            {finalTranslation ? (
              <p className="body-text text-terminal-bright">
                {finalTranslation}
              </p>
            ) : (
              <p className="body-text text-terminal-muted">
                Translation will appear here...
              </p>
            )}
            
            {/* Agent reasoning and badges */}
            {(agentReasoning || glossaryUsed) && (
              <div className="mt-3 pt-3 border-t border-terminal-border flex flex-wrap items-center gap-2">
                {glossaryUsed && (
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-1 border border-terminal-orange text-terminal-orange">
                    Glossary applied
                  </span>
                )}
                {agentReasoning && (
                  <button
                    onClick={() => setShowReasoning(prev => !prev)}
                    className="text-[10px] font-mono text-terminal-muted hover:text-terminal-bright underline"
                  >
                    {showReasoning ? "Hide" : "Show"} agent trace
                  </button>
                )}
              </div>
            )}

            {/* Agent reasoning content */}
            {showReasoning && agentReasoning && (
              <div className="mt-3 p-3 border border-terminal-border bg-terminal-panel">
                <p className="text-[11px] font-mono text-terminal-secondary leading-relaxed">
                  {agentReasoning}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Error message overlay */}
      {micError && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 text-[11px] font-mono text-terminal-orange border border-terminal-border px-4 py-2 bg-terminal-panel">
          {micError}
        </div>
      )}

      {errorMessage && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 text-[11px] font-mono text-terminal-orange border border-terminal-border px-4 py-2 bg-terminal-panel">
          {errorMessage}
        </div>
      )}
    </div>
  )
}
