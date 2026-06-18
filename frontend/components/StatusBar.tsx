"use client"

// components/StatusBar.tsx
// Shows "Transcribing… → Translating… → Speaking…" between recording and final result.
// This is the perceived-latency trick from the project plan: even though the full
// pipeline takes 3-4s, showing discrete steps makes it feel faster and more transparent.

export type PipelineStage =
  | "idle"
  | "uploading"
  | "transcribing"
  | "translating"
  | "speaking"
  | "done"
  | "error"

interface StatusBarProps {
  stage: PipelineStage
  errorMessage?: string | null
}

const STAGE_LABELS: Record<PipelineStage, string> = {
  idle: "Ready — hold the button to speak",
  uploading: "Uploading audio…",
  transcribing: "Transcribing speech…",
  translating: "Translating…",
  speaking: "Generating speech…",
  done: "Done",
  error: "Something went wrong",
}

const STAGE_ORDER: PipelineStage[] = ["uploading", "transcribing", "translating", "speaking", "done"]

export default function StatusBar({ stage, errorMessage }: StatusBarProps) {
  if (stage === "idle") {
    return (
      <div className="text-center text-sm text-sarvam-muted py-2">
        {STAGE_LABELS.idle}
      </div>
    )
  }

  if (stage === "error") {
    return (
      <div className="text-center text-sm text-red-400 py-2 bg-red-950/30 rounded-lg border border-red-800/40 px-4">
        {errorMessage || STAGE_LABELS.error}
      </div>
    )
  }

  const currentIndex = STAGE_ORDER.indexOf(stage)

  return (
    <div className="flex items-center justify-center gap-2 py-2">
      {STAGE_ORDER.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div className="flex flex-col items-center gap-1">
            <div
              className={`w-2 h-2 rounded-full transition-colors ${
                i < currentIndex
                  ? "bg-green-400"
                  : i === currentIndex
                  ? "bg-sarvam-orange animate-pulse"
                  : "bg-sarvam-border"
              }`}
            />
          </div>
          {i < STAGE_ORDER.length - 1 && (
            <div className={`w-8 h-px ${i < currentIndex ? "bg-green-400" : "bg-sarvam-border"}`} />
          )}
        </div>
      ))}
      <span className="ml-3 text-sm text-white">{STAGE_LABELS[stage]}</span>
    </div>
  )
}
