# main.py
# FastAPI application — the single entry point for all backend routes.
# Mounted on Render free tier. Self-ping cron keeps the server warm (avoids 60s cold starts).
#
# Routes:
#   GET  /health            → uptime check (also pinged by cron)
#   GET  /languages         → list of all 22 supported languages
#   POST /translate         → full pipeline: audio → STT → agent → TTS
#   POST /translate/text    → text-only pipeline (skips STT, useful for testing)
#   GET  /session/{id}      → returns working memory for a session
#   POST /eval              → runs the full 20-case eval suite
#   GET  /mcp/tools         → lists available MCP tool schemas
#   POST /mcp/tools/*       → individual MCP tool endpoints

import os
import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

# CRITICAL: must run before anything reads os.environ (resolve_api_key, CORS origins, etc.)
# Without this, .env is invisible to the process and SARVAM_API_KEY is always "".
load_dotenv()

from sarvam.client import SarvamClient, SarvamError
from sarvam.gemini_client import translate_with_gemini, GeminiError
from sarvam.languages import languages_as_dict
from memory.working_memory import memory, Turn
from mcp.server import mcp_router
from evals.run_evals import run_full_eval

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Startup / shutdown
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    logger.info("Starting Sarvam Voice Translator backend")

    # Start self-ping cron (keeps Render free tier warm)
    ping_task = asyncio.create_task(_self_ping_loop())

    yield  # Server runs here

    ping_task.cancel()
    logger.info("Backend shutting down")


async def _self_ping_loop():
    """
    Pings /health every 10 minutes to prevent Render from sleeping the instance.
    Render free tier sleeps after 15 minutes of inactivity.
    This runs as a background asyncio task for the lifetime of the process.
    """
    await asyncio.sleep(30)  # Wait 30s after startup before first ping
    while True:
        try:
            port = os.environ.get("PORT", "8000")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"http://localhost:{port}/health")
                logger.debug(f"Self-ping: {resp.status_code}")
        except Exception as e:
            logger.debug(f"Self-ping failed (OK if starting): {e}")
        await asyncio.sleep(600)  # 10 minutes


# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────

app = FastAPI(
    title="Sarvam Voice Translator Agent",
    version="1.0.0",
    description="Voice translation agent built on Sarvam APIs + LangGraph",
    lifespan=lifespan,
)

# CORS — allow the Vercel frontend and localhost dev server
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    os.environ.get("FRONTEND_URL", "https://sarvam-voice-translator.vercel.app"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Agent-Reasoning", "X-Session-ID"],
)

# Mount MCP router
app.include_router(mcp_router)


# ─────────────────────────────────────────────
# Helper: resolve API key
# Priority: X-Sarvam-Key header (BYOK) > SARVAM_API_KEY env var (demo key)
# ─────────────────────────────────────────────

def resolve_api_key(byok_header: Optional[str]) -> str:
    key = byok_header or os.environ.get("SARVAM_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=400,
            detail="No Sarvam API key. Set SARVAM_API_KEY env var or pass X-Sarvam-Key header.",
        )
    return key


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    """Uptime check. Also used by self-ping cron and Render health checks."""
    return {
        "status": "ok",
        "active_sessions": memory.active_sessions,
        "timestamp": time.time(),
    }


@app.get("/languages")
async def get_languages():
    """
    Returns all 22 supported languages with TTS support flags.
    Frontend uses this to build the target language dropdown.
    """
    return {"languages": languages_as_dict()}


# ─────────────────────────────────────────────
# Main pipeline: Audio → STT+Translate → Agent → TTS
# ─────────────────────────────────────────────

@app.post("/translate")
async def translate_audio(
    audio: UploadFile = File(..., description="Audio recording (webm/wav/mp3)"),
    target_language: str = Form(..., description="BCP-47 target language e.g. ta-IN"),
    session_id: Optional[str] = Form(None, description="Session UUID for working memory"),
    x_sarvam_key: Optional[str] = Header(None, alias="X-Sarvam-Key"),
):
    """
    Full pipeline endpoint.
    1. Speech-to-Text — Sarvam (transcribes in whatever language was spoken)
    2. Language ID on transcript — Sarvam
    3. Translation — Gemini (transcript -> target language, any language pair)
    4. TTS — Sarvam Bulbul v2
    5. Update working memory

    Returns JSON with text fields + base64 audio (or null if TTS not supported).
    Sets X-Agent-Reasoning response header for debug panel.
    """
    api_key = resolve_api_key(x_sarvam_key)
    sid = session_id or str(uuid.uuid4())

    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Filename determines MIME type the Sarvam client sends
    filename = audio.filename or "recording.webm"

    # Everything below is wrapped in one try/except. Without this, any exception
    # NOT already caught as SarvamError/HTTPException (e.g. a bug inside run_agent,
    # a KeyError, an httpx error type we didn't anticipate) propagates uncaught.
    # In dev mode with --reload, an uncaught exception inside an `async with` block
    # can tear the connection down before uvicorn writes any response at all —
    # which is exactly what shows up in the browser as net::ERR_EMPTY_RESPONSE.
    try:
        async with SarvamClient(api_key) as client:
            # ── Step 1: Speech-to-Text (transcription only, NOT translation) ──
            try:
                stt_result = await client.speech_to_text(
                    audio_bytes=audio_bytes,
                    audio_filename=filename,
                )
            except SarvamError as e:
                raise HTTPException(status_code=502, detail=f"Speech-to-text failed: {e}")

            transcript = stt_result["transcript"]
            source_language = stt_result["source_language"]

            if not transcript or not transcript.strip():
                raise HTTPException(
                    status_code=422,
                    detail="No speech detected in the recording — please try again and speak clearly.",
                )

            # ── Step 2: Language ID (runs on transcript text) ────────────────
            try:
                lang_id_result = await client.detect_language(transcript)
                detected_language = lang_id_result["language_code"]
                detection_confidence = lang_id_result["confidence"]
            except SarvamError:
                # Non-fatal — fall back to STT's detected language
                detected_language = source_language
                detection_confidence = 0.0

            # ── Step 3: Translation via Gemini ────────────────────────────────
            # Sarvam's /speech-to-text-translate can ONLY output English, and its
            # /translate endpoint has a limited language list + character caps.
            # Gemini handles any source -> any target language pair reliably.
            raw_translation = ""
            translation_error = None
            try:
                raw_translation = await translate_with_gemini(
                    text=transcript,
                    source_language_code=detected_language or source_language,
                    target_language_code=target_language,
                )
            except GeminiError as e:
                translation_error = str(e)
                logger.error(f"Gemini translation failed: {e}")

            final_translation = raw_translation
            agent_reasoning = "Translated via Gemini" if raw_translation else "Translation failed"
            glossary_used = False

            # ── Step 4: TTS ────────────────────────────────────────────────────
            audio_bytes_out = None
            tts_error = translation_error
            from sarvam.languages import tts_supported
            if not final_translation or not final_translation.strip():
                tts_error = tts_error or "No translated text returned — nothing to synthesize"
            elif tts_supported(target_language):
                try:
                    audio_bytes_out = await client.text_to_speech(
                        text=final_translation,
                        language_code=target_language,
                    )
                except SarvamError as e:
                    tts_error = str(e)
                    logger.warning(f"TTS failed (non-fatal): {e}")

        # ── Step 5: Update working memory ──────────────────────────────────────
        memory.add_turn(sid, Turn(
            source_text=transcript,
            translated_text=final_translation,
            source_lang=source_language,
            target_lang=target_language,
        ))

        # ── Response ──────────────────────────────────────────────────────────────
        import base64
        response_body = {
            "session_id": sid,
            "transcript": transcript,
            "raw_translation": raw_translation,
            "final_translation": final_translation,
            "detected_language": detected_language,
            "detection_confidence": detection_confidence,
            "source_language": source_language,
            "target_language": target_language,
            "tts_available": audio_bytes_out is not None,
            "audio_base64": base64.b64encode(audio_bytes_out).decode() if audio_bytes_out else None,
            "audio_format": "wav",
            "agent_reasoning": agent_reasoning,
            "glossary_used": glossary_used,
            "tts_error": tts_error,
        }

        response = JSONResponse(content=response_body)
        # HTTP header VALUES must be Latin-1/ASCII only (per the HTTP spec).
        # agent_reasoning can contain the original transcript text (Hindi, Tamil, etc.)
        # which is NOT ASCII — setting it directly as a header crashes uvicorn mid-response
        # (RuntimeError: Invalid HTTP header value), which is exactly what produced
        # net::ERR_EMPTY_RESPONSE on the frontend. Strip to ASCII-safe characters only;
        # the full Unicode text is still available in the JSON body's agent_reasoning field.
        safe_reasoning = agent_reasoning.encode("ascii", errors="ignore").decode("ascii")[:500]
        response.headers["X-Agent-Reasoning"] = safe_reasoning
        response.headers["X-Session-ID"] = sid
        return response

    except HTTPException:
        # Already a clean, intentional error response — let FastAPI handle it as-is
        raise
    except Exception as e:
        # Catch-all: log full traceback server-side, return clean JSON to the client
        # instead of letting the connection die with no response at all.
        logger.error(f"Unhandled error in /translate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")



# ─────────────────────────────────────────────
# Text-only pipeline (for testing without audio)
# ─────────────────────────────────────────────

class TextTranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str
    session_id: Optional[str] = None


@app.post("/translate/text")
async def translate_text(
    req: TextTranslateRequest,
    x_sarvam_key: Optional[str] = Header(None, alias="X-Sarvam-Key"),
):
    """
    Skips STT — takes raw text and runs it through translate → agent → TTS.
    Used by the eval suite and for manual testing via curl/Postman.
    """
    api_key = resolve_api_key(x_sarvam_key)
    sid = req.session_id or str(uuid.uuid4())

    try:
        async with SarvamClient(api_key) as client:
            # Translate via Gemini (same engine as the audio pipeline, for consistency)
            try:
                raw_translation = await translate_with_gemini(
                    text=req.text,
                    source_language_code=req.source_language,
                    target_language_code=req.target_language,
                )
            except GeminiError as e:
                raise HTTPException(status_code=502, detail=f"Translation failed: {e}")

            final_translation = raw_translation
            agent_reasoning = "Translated via Gemini" if raw_translation else "Translation failed"
            glossary_used = False

            # TTS
            import base64
            from sarvam.languages import tts_supported
            audio_b64 = None
            if final_translation and final_translation.strip() and tts_supported(req.target_language):
                try:
                    audio_bytes = await client.text_to_speech(final_translation, req.target_language)
                    audio_b64 = base64.b64encode(audio_bytes).decode()
                except SarvamError:
                    pass

        memory.add_turn(sid, Turn(
            source_text=req.text,
            translated_text=final_translation,
            source_lang=req.source_language,
            target_lang=req.target_language,
        ))

        return {
            "session_id": sid,
            "input_text": req.text,
            "raw_translation": raw_translation,
            "final_translation": final_translation,
            "tts_available": audio_b64 is not None,
            "audio_base64": audio_b64,
            "agent_reasoning": agent_reasoning,
            "glossary_used": glossary_used,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in /translate/text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")



# ─────────────────────────────────────────────
# Session memory
# ─────────────────────────────────────────────

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Returns the working memory turns for a session. Used by debug panel."""
    return {
        "session_id": session_id,
        "turns": memory.get_turns(session_id),
    }

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    memory.clear_session(session_id)
    return {"cleared": True}


# ─────────────────────────────────────────────
# Eval suite
# ─────────────────────────────────────────────

@app.post("/eval")
async def run_eval(
    x_sarvam_key: Optional[str] = Header(None, alias="X-Sarvam-Key"),
):
    """
    Runs the full 20-case eval suite.
    Takes ~60–90 seconds. Returns composite score (BLEU + LLM judge).
    The composite_score_pct field is what you quote in the cover email.
    """
    api_key = resolve_api_key(x_sarvam_key)
    logger.info("Eval suite triggered via /eval endpoint")
    result = await run_full_eval(api_key)
    return result