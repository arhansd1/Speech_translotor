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
      <label className="block text-xs text-sarvam-muted mb-1">Translate to</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="w-full bg-sarvam-panel border border-sarvam-border rounded-lg px-3 py-2.5 text-white text-sm appearance-none cursor-pointer focus:outline-none focus:border-sarvam-orange disabled:opacity-50"
      >
        {loading && <option>Loading languages…</option>}
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.name} {!lang.tts_supported ? "(text only)" : ""}
          </option>
        ))}
      </select>

      {selected && !selected.tts_supported && (
        <p className="text-[11px] text-amber-400 mt-1">
          Audio playback not available for {selected.name} yet — translation text only.
        </p>
      )}
    </div>
  )
}
