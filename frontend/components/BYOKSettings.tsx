"use client"

// components/BYOKSettings.tsx
// Single input field for the user's own Sarvam API key.
// Stored ONLY in localStorage (handled by parent page.tsx) — never sent to our backend,
// only attached directly from the browser to backend requests as X-Sarvam-Key header,
// which the backend forwards straight to Sarvam. We never persist it server-side.

import { useState } from "react"

interface BYOKSettingsProps {
  currentKey: string | null
  onSave: (key: string) => void
  onClear: () => void
}

export default function BYOKSettings({ currentKey, onSave, onClear }: BYOKSettingsProps) {
  const [input, setInput] = useState(currentKey || "")
  const [showKey, setShowKey] = useState(false)

  const handleSave = () => {
    const trimmed = input.trim()
    if (trimmed.length < 10) return // basic sanity check, Sarvam keys are longer
    onSave(trimmed)
  }

  return (
    <div className="mx-6 mt-4 border border-terminal-border p-4 animate-fade-in">
      <div className="flex flex-col gap-3">
        <label className="label-mono">YOUR SARVAM API KEY</label>
        <p className="text-[11px] font-mono text-terminal-muted">
          Get a free key at{" "}
          <a
            href="https://dashboard.sarvam.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="text-terminal-orange underline"
          >
            dashboard.sarvam.ai
          </a>{" "}
          (₹100 free credit, no card required). Stored only in your browser.
        </p>

        <div className="flex gap-2 mt-2">
          <div className="relative flex-1">
            <input
              type={showKey ? "text" : "password"}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="sk_live_..."
              className="w-full bg-terminal-panel border border-terminal-border px-3 py-2 text-[11px] font-mono text-terminal-bright placeholder-terminal-muted focus:outline-none focus:border-terminal-orange"
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
            />
            <button
              type="button"
              onClick={() => setShowKey((s) => !s)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-mono text-terminal-muted hover:text-terminal-bright"
            >
              {showKey ? "HIDE" : "SHOW"}
            </button>
          </div>
          <button
            onClick={handleSave}
            disabled={input.trim().length < 10}
            className="bg-terminal-orange text-terminal-bg px-4 py-2 text-[11px] font-mono uppercase tracking-wider disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
          >
            Save
          </button>
          {currentKey && (
            <button
              onClick={onClear}
              className="border border-terminal-border text-terminal-muted px-3 py-2 text-[11px] font-mono uppercase tracking-wider hover:text-terminal-bright hover:border-terminal-bright transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
