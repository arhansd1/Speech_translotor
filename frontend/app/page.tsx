"use client"

// page.tsx — Root page.
// Renders two tabs at the top: "My Key" (uses demo Sarvam key from backend)
// and "BYOK" (user pastes their own Sarvam key, stored in localStorage only).
// Both tabs render the same TranslatorApp — only the apiKey prop differs.

import { useState, useEffect } from "react"
import TranslatorApp from "@/components/TranslatorApp"
import BYOKSettings from "@/components/BYOKSettings"

type Tab = "demo" | "byok"

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("demo")
  // BYOK key from localStorage — null means not set yet
  const [byokKey, setByokKey] = useState<string | null>(null)
  const [showBYOKInput, setShowBYOKInput] = useState(false)

  // Load BYOK key from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("sarvam_byok_key")
    if (stored) setByokKey(stored)
  }, [])

  const handleByokSave = (key: string) => {
    localStorage.setItem("sarvam_byok_key", key)
    setByokKey(key)
    setShowBYOKInput(false)
  }

  const handleByokClear = () => {
    localStorage.removeItem("sarvam_byok_key")
    setByokKey(null)
  }

  return (
    <main className="min-h-screen flex flex-col bg-sarvam-dark">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="border-b border-sarvam-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Sarvam-ish logo mark */}
          <div className="w-8 h-8 rounded-lg bg-sarvam-orange flex items-center justify-center font-bold text-white text-sm">
            S
          </div>
          <div>
            <h1 className="text-white font-semibold text-lg leading-none">Voice Translator</h1>
            <p className="text-sarvam-muted text-xs mt-0.5">Powered by Sarvam AI · 22 Indian languages</p>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1 bg-sarvam-panel border border-sarvam-border rounded-lg p-1">
          <button
            onClick={() => setActiveTab("demo")}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              activeTab === "demo"
                ? "bg-sarvam-orange text-white shadow"
                : "text-sarvam-muted hover:text-white"
            }`}
          >
            My Key
          </button>
          <button
            onClick={() => setActiveTab("byok")}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "byok"
                ? "bg-sarvam-orange text-white shadow"
                : "text-sarvam-muted hover:text-white"
            }`}
          >
            BYOK
            {byokKey && (
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" title="Key saved" />
            )}
          </button>
        </div>
      </header>

      {/* ── BYOK key input banner (shown when BYOK tab active and no key yet) ── */}
      {activeTab === "byok" && (!byokKey || showBYOKInput) && (
        <BYOKSettings
          currentKey={byokKey}
          onSave={handleByokSave}
          onClear={handleByokClear}
        />
      )}

      {/* ── BYOK key status bar (when key is set) ──────────────────────── */}
      {activeTab === "byok" && byokKey && !showBYOKInput && (
        <div className="mx-6 mt-4 flex items-center justify-between bg-green-950/40 border border-green-800/50 rounded-lg px-4 py-2.5">
          <div className="flex items-center gap-2 text-sm text-green-400">
            <span className="w-2 h-2 rounded-full bg-green-400" />
            Using your Sarvam API key (stored locally, never sent to our servers)
          </div>
          <button
            onClick={() => setShowBYOKInput(true)}
            className="text-xs text-sarvam-muted hover:text-white underline"
          >
            Change key
          </button>
        </div>
      )}

      {/* ── Demo tab info banner ────────────────────────────────────────── */}
      {activeTab === "demo" && (
        <div className="mx-6 mt-4 flex items-center justify-between bg-blue-950/30 border border-blue-800/40 rounded-lg px-4 py-2.5">
          <p className="text-sm text-blue-300">
            Using the demo Sarvam key (₹100 free credits — ~20+ full sessions).
            If it runs out, switch to the <strong>BYOK tab</strong> to paste your own key.
          </p>
        </div>
      )}

      {/* ── Main translator app ─────────────────────────────────────────── */}
      {/* Only render the translator if BYOK tab has a key set */}
      {(activeTab === "demo" || (activeTab === "byok" && byokKey)) && (
        <TranslatorApp
          // When demo: apiKey is undefined — backend uses its SARVAM_API_KEY env var
          // When BYOK: apiKey is sent in X-Sarvam-Key header from browser directly
          apiKey={activeTab === "byok" ? byokKey! : undefined}
          mode={activeTab}
        />
      )}
    </main>
  )
}
