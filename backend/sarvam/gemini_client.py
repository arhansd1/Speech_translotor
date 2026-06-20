# sarvam/gemini_client.py
# Thin client for Google Gemini's text generation API, used here purely as a
# translation engine: transcript (any language) -> translated text (any target language).
#
# Why Gemini instead of Sarvam's own /translate endpoint:
# - Sarvam's /translate (mayura:v1 / sarvam-translate:v1) supports a fixed list of
#   ~11-22 Indian languages with a 1000-2000 character cap per request.
# - Gemini 2.5 Flash handles any language pair, longer text, and is free on the
#   standard API tier — and avoids depending on Sarvam for the one step that was
#   silently failing (the combined speech-to-text-translate endpoint).
#
# This client is intentionally tiny: one job, one function.

import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
# gemini-2.0-flash was retired March 31 2026 and fully shut down June 1 2026.
# gemini-2.5-flash-lite is the current lightweight/free-tier model — fast and
# cheap, which matters here since translation is a simple, low-reasoning task.
GEMINI_MODEL = "gemini-2.5-flash-lite"

TIMEOUT = 20.0


class GeminiError(Exception):
    """Raised when the Gemini API returns a non-2xx response or network fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# Human-readable language names for clearer prompts to Gemini.
# Keys match the BCP-47-ish codes used throughout this project (sarvam/languages.py).
_LANGUAGE_NAMES = {
    "hi-IN": "Hindi", "bn-IN": "Bengali", "te-IN": "Telugu", "mr-IN": "Marathi",
    "ta-IN": "Tamil", "gu-IN": "Gujarati", "kn-IN": "Kannada", "ml-IN": "Malayalam",
    "pa-IN": "Punjabi", "or-IN": "Odia", "ur-IN": "Urdu", "as-IN": "Assamese",
    "mai-IN": "Maithili", "sat-IN": "Santali", "ks-IN": "Kashmiri", "ne-IN": "Nepali",
    "sd-IN": "Sindhi", "doi-IN": "Dogri", "kok-IN": "Konkani", "mni-IN": "Manipuri",
    "brx-IN": "Bodo", "sa-IN": "Sanskrit", "en-IN": "English",
}


def _lang_name(code: str) -> str:
    return _LANGUAGE_NAMES.get(code, code)


async def translate_with_gemini(
    text: str,
    source_language_code: str,
    target_language_code: str,
    api_key: Optional[str] = None,
) -> str:
    """
    Translates text from source_language_code to target_language_code using Gemini.
    Returns the translated text only (no extra commentary).
    Raises GeminiError on failure — caller should catch this and decide on fallback.

    api_key: if None, reads GEMINI_API_KEY from the environment. Pass explicitly
             if you ever want a BYOK-style override (not currently exposed to the frontend).
    """
    if not text or not text.strip():
        return ""

    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if not key:
        raise GeminiError("No Gemini API key configured (set GEMINI_API_KEY or GOOGLE_API_KEY in .env)")

    source_name = _lang_name(source_language_code)
    target_name = _lang_name(target_language_code)

    # Same-language short-circuit — saves a call and avoids Gemini "translating"
    # English to English with unwanted rephrasing.
    if source_language_code == target_language_code:
        return text

    prompt = (
        f"Translate the following {source_name} text into {target_name}. "
        f"Return ONLY the translated text, with no explanation, no quotes, "
        f"and no preamble.\n\n"
        f"Text to translate:\n{text}"
    )

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{GEMINI_BASE}/models/{GEMINI_MODEL}:generateContent",
                headers={
                    "x-goog-api-key": key,
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [
                        {"role": "user", "parts": [{"text": prompt}]}
                    ],
                    "generationConfig": {
                        "temperature": 0.2,   # Low temperature — translation should be deterministic
                        "maxOutputTokens": 1024,
                    },
                },
            )

            if resp.status_code >= 400:
                try:
                    err_body = resp.json()
                    msg = err_body.get("error", {}).get("message", resp.text)
                except Exception:
                    msg = resp.text
                raise GeminiError(f"Gemini API error {resp.status_code}: {msg}", resp.status_code)

            data = resp.json()

            # Defensive parsing: Gemini can return candidates with no parts
            # (e.g. blocked by safety filters) — never let a KeyError/IndexError
            # crash the request; always degrade to an empty string the caller can handle.
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("Gemini returned no candidates (possibly safety-filtered)")
                return ""

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                logger.warning("Gemini candidate has no content parts")
                return ""

            translated = (parts[0].get("text") or "").strip()
            return translated

    except httpx.TimeoutException:
        raise GeminiError("Gemini translation request timed out")
    except httpx.NetworkError as e:
        raise GeminiError(f"Network error calling Gemini: {e}")