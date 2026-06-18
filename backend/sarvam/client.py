# sarvam/client.py
# Single client for all Sarvam API calls.
# Every route in main.py and every agent tool goes through this — never raw httpx calls elsewhere.
# This makes it trivial to swap API keys (demo vs BYOK) at request time.

import httpx
import logging
from typing import Optional
from .languages import get_speaker, tts_supported

logger = logging.getLogger(__name__)

SARVAM_BASE = "https://api.sarvam.ai"

# How long to wait for Sarvam before giving up (seconds).
# STT+Translate on a 30-second clip realistically takes 2–4s; 30s is generous.
TIMEOUT = 30.0


class SarvamError(Exception):
    """Raised when Sarvam API returns a non-2xx response or network fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class SarvamClient:
    """
    Thin async wrapper around Sarvam's REST API.
    Pass api_key at construction time — this lets us swap between
    the demo key (stored in backend env) and the user's BYOK key
    (sent in the request header from the frontend) without any globals.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise SarvamError("No Sarvam API key provided")
        self.api_key = api_key
        # Shared async client — reused across calls within one request lifecycle.
        # Caller is responsible for closing (or use as async context manager).
        self._client = httpx.AsyncClient(
            base_url=SARVAM_BASE,
            headers={
                "api-subscription-key": self.api_key,
                "Accept": "application/json",
            },
            timeout=TIMEOUT,
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ─────────────────────────────────────────────
    # 1. Language Identification
    # Endpoint: POST /text-lid
    # Cost: ₹3.5 per 10K characters — essentially free
    # Input: plain text (the transcript from STT)
    # Output: detected BCP-47 language code + confidence score
    # ─────────────────────────────────────────────
    async def detect_language(self, text: str) -> dict:
        """
        Returns:
            {
                "language_code": "hi-IN",
                "confidence": 0.97
            }
        Raises SarvamError on failure.
        """
        if not text.strip():
            return {"language_code": "hi-IN", "confidence": 0.0}

        try:
            resp = await self._client.post(
                "/text-lid",
                json={"input": text},
            )
            _raise_for_status(resp)
            data = resp.json()
            return {
                "language_code": data.get("language_code", "unknown"),
                "confidence": data.get("confidence", 0.0),
            }
        except httpx.TimeoutException:
            raise SarvamError("Language detection timed out")
        except httpx.NetworkError as e:
            raise SarvamError(f"Network error during language detection: {e}")

    # ─────────────────────────────────────────────
    # 2. STT + Translation (combined single call)
    # Endpoint: POST /speech-to-text-translate
    # Cost: ₹30 per hour of audio
    # Why combined: saves one extra round-trip vs calling STT then translate separately.
    # Input: audio file bytes (wav/mp3/webm), target language code
    # Output: transcript in source language + translation in target language
    # ─────────────────────────────────────────────
    async def stt_and_translate(
        self,
        audio_bytes: bytes,
        audio_filename: str,          # e.g. "recording.webm" — Sarvam uses extension for format
        target_language_code: str,    # BCP-47 e.g. "ta-IN"
        source_language_code: Optional[str] = None,  # None = auto-detect
    ) -> dict:
        """
        Returns:
            {
                "transcript": "यह एक परीक्षण है",
                "translation": "This is a test",
                "source_language": "hi-IN"
            }
        Raises SarvamError on failure.
        """
        try:
            # Sarvam's combined endpoint takes multipart form data
            files = {"file": (audio_filename, audio_bytes, _mime_for(audio_filename))}
            data = {
                "target_language_code": target_language_code,
                "model": "saaras:v2",         # Saarika v2 — best quality for STT
                "with_timestamps": "false",    # We don't need word-level timestamps
                "with_diarization": "false",   # Single speaker
            }
            if source_language_code:
                data["language_code"] = source_language_code

            resp = await self._client.post(
                "/speech-to-text-translate",
                files=files,
                data=data,
            )
            _raise_for_status(resp)
            result = resp.json()

            return {
                "transcript": result.get("transcript", ""),
                "translation": result.get("translation", ""),
                "source_language": result.get("language_code", source_language_code or "unknown"),
            }
        except httpx.TimeoutException:
            raise SarvamError("STT+Translate timed out — audio may be too long")
        except httpx.NetworkError as e:
            raise SarvamError(f"Network error during STT+Translate: {e}")

    # ─────────────────────────────────────────────
    # 3. Text-to-Speech (Bulbul v2)
    # Endpoint: POST /text-to-speech
    # Cost: ₹15 per 10K characters (v2 is half the price of v3)
    # Input: translated text + target language code
    # Output: base64-encoded audio (WAV) or bytes depending on response format
    # ─────────────────────────────────────────────
    async def text_to_speech(
        self,
        text: str,
        language_code: str,
        speaker: Optional[str] = None,
    ) -> bytes:
        """
        Returns raw audio bytes (WAV format).
        Raises SarvamError if language has no TTS support or on API failure.
        """
        if not tts_supported(language_code):
            raise SarvamError(
                f"TTS not supported for {language_code} in Bulbul v2. "
                "Translation is still available but audio playback is disabled."
            )

        if not speaker:
            speaker = get_speaker(language_code)

        try:
            resp = await self._client.post(
                "/text-to-speech",
                json={
                    "inputs": [text],
                    "target_language_code": language_code,
                    "speaker": speaker,
                    "model": "bulbul:v2",       # v2 = ₹15/10K chars, quality fine for demo
                    "pace": 1.0,                # Normal speed
                    "loudness": 1.0,
                    "enable_preprocessing": True,  # Handles numbers, abbreviations etc.
                },
            )
            _raise_for_status(resp)
            result = resp.json()

            # Sarvam returns base64-encoded WAV in audios[0]
            import base64
            audio_b64 = result["audios"][0]
            return base64.b64decode(audio_b64)

        except httpx.TimeoutException:
            raise SarvamError("TTS timed out")
        except httpx.NetworkError as e:
            raise SarvamError(f"Network error during TTS: {e}")
        except (KeyError, IndexError) as e:
            raise SarvamError(f"Unexpected TTS response format: {e}")

    # ─────────────────────────────────────────────
    # 4. Transliteration
    # Endpoint: POST /transliterate
    # Converts script without changing meaning: "नमस्ते" → "Namaste"
    # Used by the MCP transliterate tool
    # ─────────────────────────────────────────────
    async def transliterate(
        self,
        text: str,
        source_language_code: str,
        target_language_code: str = "en-IN",   # Default: Romanize
    ) -> str:
        """Returns transliterated string. Raises SarvamError on failure."""
        try:
            resp = await self._client.post(
                "/transliterate",
                json={
                    "input": text,
                    "source_language_code": source_language_code,
                    "target_language_code": target_language_code,
                    "numerals_format": "international",
                },
            )
            _raise_for_status(resp)
            return resp.json().get("transliterated_text", text)
        except httpx.TimeoutException:
            raise SarvamError("Transliteration timed out")
        except httpx.NetworkError as e:
            raise SarvamError(f"Network error during transliteration: {e}")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _raise_for_status(resp: httpx.Response):
    """Converts Sarvam HTTP errors into SarvamError with the response body."""
    if resp.status_code >= 400:
        try:
            body = resp.json()
            msg = body.get("message") or body.get("error") or str(body)
        except Exception:
            msg = resp.text
        raise SarvamError(
            f"Sarvam API error {resp.status_code}: {msg}",
            status_code=resp.status_code,
        )

def _mime_for(filename: str) -> str:
    """Returns the MIME type Sarvam expects based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "wav":  "audio/wav",
        "mp3":  "audio/mpeg",
        "webm": "audio/webm",
        "ogg":  "audio/ogg",
        "m4a":  "audio/mp4",
        "flac": "audio/flac",
    }.get(ext, "audio/wav")
