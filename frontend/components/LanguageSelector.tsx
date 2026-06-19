"use client"

// components/LanguageSelector.tsx
// Dropdown for choosing the target output language.
// Fetches the 22-language list from the backend /languages route.
// Shows a small "no audio" badge next to languages Bulbul v2 TTS doesn't support yet.

import { useEffect, useState } from "react"
import { fetchLanguages, Language } from "@/lib/api"

interface LanguageSelectorProps {
  value: string
  onChange: (code: string) => void
}

export default function LanguageSelector({ value, onChange }: LanguageSelectorProps) {
  const [languages, setLanguages] = useState<Language[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLanguages()
      .then(setLanguages)
      .catch(() => {
        // Fallback list if backend is unreachable — keeps UI usable
        setLanguages([
          { code: "hi-IN", name: "Hindi", script: "Devanagari", tts_supported: true },
          { code: "ta-IN", name: "Tamil", script: "Tamil", tts_supported: true },
          { code: "en-IN", name: "English", script: "Latin", tts_supported: true },
        ])
      })
      .finally(() => setLoading(false))
  }, [])

  const selected = languages.find((l) => l.code === value)

  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="bg-transparent border border-terminal-border px-3 py-1.5 text-[11px] font-mono text-terminal-bright appearance-none cursor-pointer focus:outline-none focus:border-terminal-orange disabled:opacity-50 pr-8"
      >
        {loading && <option>Loading languages…</option>}
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code} className="bg-terminal-panel text-terminal-body">
            {lang.name} {!lang.tts_supported ? "(text only)" : ""}
          </option>
        ))}
      </select>

      {/* Custom chevron */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
        <svg className="w-3 h-3 text-terminal-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  )
}
