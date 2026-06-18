"use client"

// components/PanelDetected.tsx
// LHS panel: shows the auto-detected source language + confidence + raw transcript.

interface PanelDetectedProps {
  detectedLanguage: string | null
  confidence: number
  transcript: string | null
  languageName: string | null
}

export default function PanelDetected({
  detectedLanguage,
  confidence,
  transcript,
  languageName,
}: PanelDetectedProps) {
  return (
    <div className="panel-card flex-1 min-h-[280px]">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-sarvam-muted uppercase tracking-wide">
          Detected Language
        </h2>
        <span className="text-xs text-sarvam-muted">LHS</span>
      </div>

      {detectedLanguage ? (
        <div className="flex flex-col gap-3 animate-fade-in">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-white">
              {languageName || detectedLanguage}
            </span>
            {confidence > 0 && (
              <span className="text-xs text-green-400 bg-green-950/40 px-2 py-0.5 rounded-full">
                {Math.round(confidence * 100)}% confident
              </span>
            )}
          </div>
          <code className="text-xs text-sarvam-muted">{detectedLanguage}</code>

          {transcript && (
            <div className="mt-2 pt-3 border-t border-sarvam-border">
              <p className="text-xs text-sarvam-muted mb-1">Original speech:</p>
              <p className="text-sm text-white/90 translation-scroll">{transcript}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-sarvam-muted text-sm py-12">
          Speak to detect language
        </div>
      )}
    </div>
  )
}
