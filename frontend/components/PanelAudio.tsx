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
    <div className="w-full max-w-md">
      {audioUrl && ttsAvailable ? (
        <div className="border border-terminal-border flex items-center">
          {/* Play/pause button */}
          <button
            onClick={() => {
              if (audioRef.current) {
                if (isPlaying) {
                  audioRef.current.pause()
                } else {
                  audioRef.current.play()
                }
              }
            }}
            className="w-10 h-10 flex items-center justify-center border-r border-terminal-border hover:bg-terminal-panel transition-colors"
          >
            {isPlaying ? (
              <svg className="w-4 h-4 text-terminal-bright" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="4" width="4" height="16" />
                <rect x="14" y="4" width="4" height="16" />
              </svg>
            ) : (
              <svg className="w-4 h-4 text-terminal-bright" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Status label */}
          <span className="flex-1 px-4 text-[11px] font-mono text-terminal-muted">
            {isPlaying ? "PLAYING..." : "READY"}
          </span>

          {/* Waveform indicator */}
          <div className="flex items-center gap-0.5 px-3">
            <div className={`w-1 h-3 ${isPlaying ? 'bg-terminal-orange animate-pulse' : 'bg-terminal-muted'}`} />
            <div className={`w-1 h-5 ${isPlaying ? 'bg-terminal-orange animate-pulse' : 'bg-terminal-muted'}`} style={{ animationDelay: '0.1s' }} />
            <div className={`w-1 h-4 ${isPlaying ? 'bg-terminal-orange animate-pulse' : 'bg-terminal-muted'}`} style={{ animationDelay: '0.2s' }} />
            <div className={`w-1 h-6 ${isPlaying ? 'bg-terminal-orange animate-pulse' : 'bg-terminal-muted'}`} style={{ animationDelay: '0.3s' }} />
            <div className={`w-1 h-3 ${isPlaying ? 'bg-terminal-orange animate-pulse' : 'bg-terminal-muted'}`} style={{ animationDelay: '0.4s' }} />
          </div>

          {/* Hidden audio element */}
          <audio
            ref={audioRef}
            src={audioUrl}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            className="hidden"
          />
        </div>
      ) : ttsError ? (
        <div className="border border-terminal-border px-4 py-3 text-[11px] font-mono text-terminal-orange">
          {ttsError}
        </div>
      ) : !ttsAvailable && targetLanguageName ? (
        <div className="border border-terminal-border px-4 py-3 text-[11px] font-mono text-terminal-muted">
          Audio not available for {targetLanguageName}
        </div>
      ) : (
        <div className="border border-terminal-border px-4 py-3 text-[11px] font-mono text-terminal-muted">
          WAITING FOR SYNTHESIS
        </div>
      )}
    </div>
  )
}
