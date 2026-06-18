// hooks/useAudioRecorder.ts
// Wraps the browser MediaRecorder API.
// Call startRecording() on button mousedown/touchstart.
// Call stopRecording() on mouseup/touchend — returns a Blob.
// Exposes isRecording and volumeLevel (0–1) for the waveform animation.

import { useRef, useState, useCallback } from "react"

interface UseAudioRecorderReturn {
  isRecording: boolean
  volumeLevel: number          // 0–1, updates ~20x/sec while recording
  startRecording: () => Promise<void>
  stopRecording: () => Promise<Blob | null>
  error: string | null
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [volumeLevel, setVolumeLevel] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animFrameRef = useRef<number | null>(null)

  const startRecording = useCallback(async () => {
    setError(null)
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,   // Sarvam STT prefers 16kHz
          channelCount: 1,     // Mono
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      streamRef.current = stream

      // Set up Web Audio API analyser for waveform visualization
      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      // Volume polling loop — drives waveform bars in PushToTalkButton
      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const pollVolume = () => {
        analyser.getByteFrequencyData(dataArray)
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        setVolumeLevel(avg / 255)
        animFrameRef.current = requestAnimationFrame(pollVolume)
      }
      pollVolume()

      // Choose best supported format
      const mimeType = getSupportedMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.start(100)  // Collect chunks every 100ms
      mediaRecorderRef.current = recorder
      setIsRecording(true)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(`Microphone access denied: ${msg}`)
    }
  }, [])

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current
      if (!recorder || recorder.state === "inactive") {
        resolve(null)
        return
      }

      // Cancel volume animation
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      setVolumeLevel(0)

      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm"
        const blob = new Blob(chunksRef.current, { type: mimeType })
        chunksRef.current = []

        // Stop all tracks to release mic indicator in browser
        streamRef.current?.getTracks().forEach((t) => t.stop())

        setIsRecording(false)
        resolve(blob)
      }

      recorder.stop()
    })
  }, [])

  return { isRecording, volumeLevel, startRecording, stopRecording, error }
}

// Returns the best audio MIME type the browser supports.
// Prefer webm/opus (smallest), fall back to mp4, then wav.
function getSupportedMimeType(): string | null {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ]
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t
  }
  return null
}
