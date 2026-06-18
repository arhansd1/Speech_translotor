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
    <div className="mx-6 mt-4 bg-sarvam-panel border border-sarvam-border rounded-lg p-4 animate-fade-in">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-white mb-1.5">
            Your Sarvam API Key
          </label>
          <p className="text-xs text-sarvam-muted mb-3">
            Get a free key at{" "}
            <a
              href="https://dashboard.sarvam.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sarvam-orange underline"
            >
              dashboard.sarvam.ai
            </a>{" "}
            (₹100 free credit, no card required). Stored only in your browser — never sent to our servers.
          </p>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? "text" : "password"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="sk_live_..."
                className="w-full bg-sarvam-dark border border-sarvam-border rounded-md px-3 py-2 text-sm text-white placeholder-sarvam-muted focus:outline-none focus:border-sarvam-orange"
                onKeyDown={(e) => e.key === "Enter" && handleSave()}
              />
              <button
                type="button"
                onClick={() => setShowKey((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-sarvam-muted hover:text-white"
              >
                {showKey ? "Hide" : "Show"}
              </button>
            </div>
            <button
              onClick={handleSave}
              disabled={input.trim().length < 10}
              className="bg-sarvam-orange text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-orange-600 transition-colors"
            >
              Save
            </button>
            {currentKey && (
              <button
                onClick={onClear}
                className="border border-sarvam-border text-sarvam-muted px-3 py-2 rounded-md text-sm hover:text-white hover:border-white/40 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
