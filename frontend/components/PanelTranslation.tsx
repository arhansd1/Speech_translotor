"use client"

// components/PanelTranslation.tsx
// Middle panel: shows the translated text.
// "Chunks" per the original plan means we reveal the text progressively
// (word-by-word fade-in) rather than literal separate network chunks —
// this gives the same perceived feel without needing server-side streaming,
// since the agent's final output text arrives as one JSON response.

import { useEffect, useState } from "react"

interface PanelTranslationProps {
  translatedText: string | null
  rawTranslation: string | null
  agentReasoning: string | null
  glossaryUsed: boolean
  isProcessing: boolean
}

export default function PanelTranslation({
  translatedText,
  rawTranslation,
  agentReasoning,
  glossaryUsed,
  isProcessing,
}: PanelTranslationProps) {
  const [visibleWords, setVisibleWords] = useState(0)
  const [showReasoning, setShowReasoning] = useState(false)

  // Reveal words progressively when new translation arrives
  useEffect(() => {
    if (!translatedText) {
      setVisibleWords(0)
      return
    }
    setVisibleWords(0)
    const words = translatedText.split(" ")
    let i = 0
    const interval = setInterval(() => {
      i += 1
      setVisibleWords(i)
      if (i >= words.length) clearInterval(interval)
    }, 60) // ~60ms per word — feels like streaming, finishes fast
    return () => clearInterval(interval)
  }, [translatedText])

  const words = translatedText?.split(" ") || []
  const wasRefined = translatedText && rawTranslation && translatedText !== rawTranslation

  return (
    <div className="panel-card flex-1 min-h-[320px]">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          Translation
        </h2>
        <span className="text-xs text-slate-500 font-medium">Middle</span>
      </div>

      {isProcessing && !translatedText && (
        <div className="flex-1 flex items-center justify-center gap-2 py-16">
          <span className="w-2.5 h-2.5 bg-orange-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-2.5 h-2.5 bg-orange-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-2.5 h-2.5 bg-orange-500 rounded-full animate-bounce" />
        </div>
      )}

      {translatedText ? (
        <div className="flex flex-col gap-4 animate-fade-in">
          <p className="translation-scroll text-white font-semibold text-lg leading-relaxed">
            {words.slice(0, visibleWords).join(" ")}
            {visibleWords < words.length && <span className="opacity-50">▋</span>}
          </p>

          <div className="flex flex-wrap items-center gap-2 mt-1 pt-4 border-t border-slate-700/50">
            {wasRefined && (
              <span className="text-[11px] text-purple-300 bg-purple-950/40 border border-purple-800/50 px-3 py-1 rounded-full font-medium">
                Agent-refined
              </span>
            )}
            {glossaryUsed && (
              <span className="text-[11px] text-amber-300 bg-amber-950/40 border border-amber-800/50 px-3 py-1 rounded-full font-medium">
                Glossary applied
              </span>
            )}
            {agentReasoning && (
              <button
                onClick={() => setShowReasoning((s) => !s)}
                className="text-[11px] text-slate-400 underline hover:text-white ml-auto transition-colors"
              >
                {showReasoning ? "Hide" : "Show"} agent trace
              </button>
            )}
          </div>

          {showReasoning && agentReasoning && (
            <p className="text-[11px] text-slate-400 font-mono bg-slate-900/50 rounded-lg p-3 border border-slate-700/50 leading-relaxed">
              {agentReasoning}
            </p>
          )}
        </div>
      ) : (
        !isProcessing && (
          <div className="flex-1 flex items-center justify-center text-slate-500 text-sm py-16">
            Translation will appear here
          </div>
        )
      )}
    </div>
  )
}
