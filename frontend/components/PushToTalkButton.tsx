"use client"

// components/PushToTalkButton.tsx
// Hold to record, release to send.
// Shows a live waveform (pure CSS animation driven by volumeLevel) while recording.
// Works with both mouse (desktop) and touch (mobile) events.

interface PushToTalkButtonProps {
  isRecording: boolean
  volumeLevel: number
  disabled?: boolean
  onPressStart: () => void
  onPressEnd: () => void
}

export default function PushToTalkButton({
  isRecording,
  volumeLevel,
  disabled,
  onPressStart,
  onPressEnd,
}: PushToTalkButtonProps) {
  // Scale waveform bar heights based on live volume (20–100%)
  const barHeight = (mult: number) => `${Math.max(20, volumeLevel * 100 * mult)}%`

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        // Mouse events (desktop)
        onMouseDown={(e) => { e.preventDefault(); if (!disabled) onPressStart() }}
        onMouseUp={(e) => { e.preventDefault(); onPressEnd() }}
        onMouseLeave={() => { if (isRecording) onPressEnd() }}
        // Touch events (mobile) — preventDefault stops ghost click + scroll
        onTouchStart={(e) => { e.preventDefault(); if (!disabled) onPressStart() }}
        onTouchEnd={(e) => { e.preventDefault(); onPressEnd() }}
        disabled={disabled}
        className={`
          relative w-20 h-20 rounded-full flex items-center justify-center
          transition-all duration-150 select-none touch-none
          ${isRecording
            ? "bg-red-500 scale-110 shadow-lg shadow-red-500/40"
            : "bg-sarvam-orange hover:bg-orange-600"}
          ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
        `}
      >
        {/* Pulse ring while recording */}
        {isRecording && (
          <span className="absolute inset-0 rounded-full bg-red-500 animate-pulse-ring" />
        )}

        {isRecording ? (
          // Waveform bars while recording
          <div className="relative z-10 flex items-end gap-0.5 h-8">
            <div className="waveform-bar" style={{ height: barHeight(0.8) }} />
            <div className="waveform-bar" style={{ height: barHeight(1.2) }} />
            <div className="waveform-bar" style={{ height: barHeight(1.5) }} />
            <div className="waveform-bar" style={{ height: barHeight(1.0) }} />
            <div className="waveform-bar" style={{ height: barHeight(0.7) }} />
          </div>
        ) : (
          // Mic icon (inline SVG, no icon library needed)
          <svg
            className="w-7 h-7 text-white relative z-10"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 10v1a7 7 0 01-14 0v-1M12 18v4M8 22h8" />
          </svg>
        )}
      </button>

      <p className="text-xs text-sarvam-muted">
        {isRecording ? "Recording… release to translate" : "Hold to speak"}
      </p>
    </div>
  )
}
