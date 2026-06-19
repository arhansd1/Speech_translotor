"use client"

// page.tsx — Root page.
// Renders two tabs at the top: "My Key" (uses demo Sarvam key from backend)
// and "BYOK" (user pastes their own Sarvam key, stored in localStorage only).
// Both tabs render the same TranslatorApp — only the apiKey prop differs.

import { useState, useEffect } from "react"
import TranslatorApp from "@/components/TranslatorApp"
import BYOKSettings from "@/components/BYOKSettings"
import LanguageSelector from "@/components/LanguageSelector"

type Tab = "demo" | "byok"

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("demo")
  // BYOK key from localStorage — null means not set yet
  const [byokKey, setByokKey] = useState<string | null>(null)
  const [showBYOKInput, setShowBYOKInput] = useState(false)
  const [targetLanguage, setTargetLanguage] = useState("ta-IN")

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
    <main className="min-h-screen flex flex-col bg-terminal-bg">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="h-14 border-b border-terminal-border flex items-center justify-between px-6 sticky top-0 z-10 bg-terminal-bg">
        {/* Logo and title */}
        <div className="flex items-center gap-3">
          {/* Small square orange logo mark */}
          <div className="w-8 h-8 bg-terminal-orange flex items-center justify-center font-bold text-white text-sm">
            S
          </div>
          <div className="flex flex-col">
            <span className="font-mono text-[10px] uppercase tracking-widest text-terminal-muted leading-tight">
              SARVAM · VOICE TRANSLATOR AGENT
            </span>
            <span className="font-mono text-[10px] text-terminal-secondary leading-tight">
              LangGraph + Saaras + Bulbul v2 + sarvam-m
            </span>
          </div>
        </div>

        {/* Tab switcher - minimal bordered container */}
        <div className="flex items-center border border-terminal-border">
          <button
            onClick={() => setActiveTab("demo")}
            className={`px-4 py-2 text-[11px] font-mono uppercase tracking-wider transition-colors ${
              activeTab === "demo"
                ? "bg-terminal-bright text-terminal-bg"
                : "text-terminal-muted hover:text-terminal-secondary"
            }`}
          >
            DEMO KEY
          </button>
          <button
            onClick={() => setActiveTab("byok")}
            className={`px-4 py-2 text-[11px] font-mono uppercase tracking-wider transition-colors flex items-center gap-2 ${
              activeTab === "byok"
                ? "bg-terminal-bright text-terminal-bg"
                : "text-terminal-muted hover:text-terminal-secondary"
            }`}
          >
            BYOK
            {byokKey && (
              <span className="w-1.5 h-1.5 rounded-full bg-terminal-mint" title="Key saved" />
            )}
          </button>
        </div>

        {/* Language selector with icon */}
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-terminal-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
          </svg>
          <LanguageSelector value={targetLanguage} onChange={setTargetLanguage} />
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
        <div className="mx-6 mt-4 flex items-center justify-between border border-terminal-border px-4 py-2">
          <div className="flex items-center gap-2 text-[11px] font-mono text-terminal-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-terminal-mint" />
            Using your Sarvam API key (stored locally)
          </div>
          <button
            onClick={() => setShowBYOKInput(true)}
            className="text-[10px] font-mono text-terminal-muted hover:text-terminal-bright underline"
          >
            Change key
          </button>
        </div>
      )}

      {/* ── Demo tab info banner ────────────────────────────────────────── */}
      {activeTab === "demo" && (
        <div className="mx-6 mt-4 flex items-center justify-between border border-terminal-border px-4 py-2">
          <p className="text-[11px] font-mono text-terminal-muted">
            Using the demo Sarvam key (₹100 free credits — ~20+ full sessions).
            If it runs out, switch to the <span className="text-terminal-bright">BYOK tab</span> to paste your own key.
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
          targetLanguage={targetLanguage}
          onTargetLanguageChange={setTargetLanguage}
        />
      )}
    </main>
  )
}
