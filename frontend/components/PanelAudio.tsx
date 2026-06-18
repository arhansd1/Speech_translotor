"use client"

// components/PanelAudio.tsx
// RHS panel: plays back the TTS audio in the target language.
// Auto-plays when new audio arrives (browsers allow autoplay after a user gesture,
// and push-to-talk counts as one). Falls back gracefully when TTS isn't supported
// for the chosen language (shows a clear message instead of a broken player).

import { useEffect, useRef, useState } from "react"

interface PanelAudioProps {
  audioUrl: string | null
  ttsAvailable: boolean
  ttsError: string | null
  targetLanguageName: string | null
}

export default function PanelAudio({
  audioUrl,
  ttsAvailable,
  ttsError,
  targetLanguageName,
}: PanelAudioProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  // Auto-play new audio as soon as it's ready
  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.play().catch(() => {
        // Autoplay can still be blocked in some browsers — user can hit play manually
      })
    }
  }, [audioUrl])

  return (
    <div className="panel-card flex-1 min-h-[280px]">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-sarvam-muted uppercase tracking-wide">
          Audio Output
        </h2>
        <span className="text-xs text-sarvam-muted">RHS</span>
      </div>

      {audioUrl && ttsAvailable ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 py-6 animate-fade-in">
          {/* Speaker icon — pulses while playing */}
          <div
            className={`w-16 h-16 rounded-full bg-sarvam-orange/20 flex items-center justify-center ${
              isPlaying ? "animate-pulse" : ""
            }`}
          >
            <svg className="w-8 h-8 text-sarvam-orange" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11 5L6 9H2v6h4l5 4V5z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" />
            </svg>
          </div>

          <audio
            ref={audioRef}
            src={audioUrl}
            controls
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            className="w-full"
          />

          <p className="text-xs text-sarvam-muted">
            Spoken in {targetLanguageName || "target language"}
          </p>
        </div>
      ) : ttsError ? (
        <div className="flex-1 flex items-center justify-center text-center text-amber-400 text-sm py-12 px-2">
          {ttsError}
        </div>
      ) : !ttsAvailable && targetLanguageName ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center gap-2 py-12 px-2">
          <span className="text-sarvam-muted text-sm">
            Audio playback isn&apos;t available for {targetLanguageName} yet.
          </span>
          <span className="text-xs text-sarvam-muted/70">Translation text is still shown in the middle panel.</span>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-sarvam-muted text-sm py-12">
          Audio will play here
        </div>
      )}
    </div>
  )
}
