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
    <div className="panel-card flex-1 min-h-[280px]">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-sarvam-muted uppercase tracking-wide">
          Translation
        </h2>
        <span className="text-xs text-sarvam-muted">Middle</span>
      </div>

      {isProcessing && !translatedText && (
        <div className="flex-1 flex items-center justify-center gap-1.5 py-12">
          <span className="w-2 h-2 bg-sarvam-orange rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-2 h-2 bg-sarvam-orange rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-2 h-2 bg-sarvam-orange rounded-full animate-bounce" />
        </div>
      )}

      {translatedText ? (
        <div className="flex flex-col gap-3 animate-fade-in">
          <p className="translation-scroll text-white font-medium">
            {words.slice(0, visibleWords).join(" ")}
            {visibleWords < words.length && <span className="opacity-50">▋</span>}
          </p>

          <div className="flex flex-wrap items-center gap-2 mt-1 pt-3 border-t border-sarvam-border">
            {wasRefined && (
              <span className="text-[11px] text-purple-300 bg-purple-950/40 px-2 py-0.5 rounded-full">
                Agent-refined
              </span>
            )}
            {glossaryUsed && (
              <span className="text-[11px] text-amber-300 bg-amber-950/40 px-2 py-0.5 rounded-full">
                Glossary applied
              </span>
            )}
            {agentReasoning && (
              <button
                onClick={() => setShowReasoning((s) => !s)}
                className="text-[11px] text-sarvam-muted underline hover:text-white ml-auto"
              >
                {showReasoning ? "Hide" : "Show"} agent trace
              </button>
            )}
          </div>

          {showReasoning && agentReasoning && (
            <p className="text-[11px] text-sarvam-muted font-mono bg-sarvam-dark rounded-md p-2 border border-sarvam-border">
              {agentReasoning}
            </p>
          )}
        </div>
      ) : (
        !isProcessing && (
          <div className="flex-1 flex items-center justify-center text-sarvam-muted text-sm py-12">
            Translation will appear here
          </div>
        )
      )}
    </div>
  )
}
