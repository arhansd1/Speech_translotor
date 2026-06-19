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
    <div className="panel-card flex-1 min-h-[320px]">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          Detected Language
        </h2>
        <span className="text-xs text-slate-500 font-medium">LHS</span>
      </div>

      {detectedLanguage ? (
        <div className="flex flex-col gap-4 animate-fade-in">
          <div className="flex items-center gap-3">
            <span className="text-3xl font-bold text-white tracking-tight">
              {languageName || detectedLanguage}
            </span>
            {confidence > 0 && (
              <span className="text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800/50 px-3 py-1 rounded-full font-medium">
                {Math.round(confidence * 100)}% confident
              </span>
            )}
          </div>
          <code className="text-xs text-slate-500 font-mono">{detectedLanguage}</code>

          {transcript && (
            <div className="mt-3 pt-4 border-t border-slate-700/50">
              <p className="text-xs text-slate-400 mb-2 font-medium">Original speech:</p>
              <p className="text-sm text-white/90 translation-scroll leading-relaxed">{transcript}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm py-16">
          Speak to detect language
        </div>
      )}
    </div>
  )
}
