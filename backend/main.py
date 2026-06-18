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
from fastapi import FastAPI, File, Form, UploadFile, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from sarvam.client import SarvamClient, SarvamError
from sarvam.languages import languages_as_dict
from agent.graph import run_agent
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
    # Pre-compile the LangGraph graph so first request isn't slow
    from agent.graph import get_graph
    get_graph()
    logger.info("LangGraph agent compiled and ready")

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
    1. STT + Translate (single Sarvam API call)
    2. Language ID on transcript
    3. LangGraph agent (quality check → optional glossary → optional LLM refine)
    4. TTS (Bulbul v2)
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

    async with SarvamClient(api_key) as client:
        # ── Step 1: STT + Translate ──────────────────────────────────────────
        try:
            stt_result = await client.stt_and_translate(
                audio_bytes=audio_bytes,
                audio_filename=filename,
                target_language_code=target_language,
            )
        except SarvamError as e:
            raise HTTPException(status_code=502, detail=f"STT+Translate failed: {e}")

        transcript = stt_result["transcript"]
        raw_translation = stt_result["translation"]
        source_language = stt_result["source_language"]

        # ── Step 2: Language ID (runs on transcript text) ────────────────────
        try:
            lang_id_result = await client.detect_language(transcript)
            detected_language = lang_id_result["language_code"]
            detection_confidence = lang_id_result["confidence"]
        except SarvamError:
            # Non-fatal — fall back to STT's detected language
            detected_language = source_language
            detection_confidence = 0.0

        # ── Step 3: LangGraph agent ──────────────────────────────────────────
        session_context = memory.get_context(sid)
        agent_result = await run_agent(
            raw_translation=raw_translation,
            transcript=transcript,
            source_language=source_language,
            target_language=target_language,
            session_context=session_context,
            api_key=api_key,
        )
        final_translation = agent_result["final_translation"]

        # ── Step 4: TTS ──────────────────────────────────────────────────────
        audio_bytes_out = None
        tts_error = None
        from sarvam.languages import tts_supported
        if tts_supported(target_language):
            try:
                audio_bytes_out = await client.text_to_speech(
                    text=final_translation,
                    language_code=target_language,
                )
            except SarvamError as e:
                tts_error = str(e)
                logger.warning(f"TTS failed (non-fatal): {e}")

    # ── Step 5: Update working memory ────────────────────────────────────────
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
        "agent_reasoning": agent_result.get("agent_reasoning", ""),
        "glossary_used": agent_result.get("glossary_used", False),
        "tts_error": tts_error,
    }

    response = JSONResponse(content=response_body)
    response.headers["X-Agent-Reasoning"] = agent_result.get("agent_reasoning", "")[:500]
    response.headers["X-Session-ID"] = sid
    return response


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

    async with SarvamClient(api_key) as client:
        # Translate
        try:
            resp = await client._client.post(
                "/translate",
                json={
                    "input": req.text,
                    "source_language_code": req.source_language,
                    "target_language_code": req.target_language,
                    "model": "mayura:v1",
                    "enable_preprocessing": True,
                },
            )
            if resp.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Translate failed: {resp.text}")
            raw_translation = resp.json().get("translated_text", "")
        except SarvamError as e:
            raise HTTPException(status_code=502, detail=str(e))

        # Agent
        session_context = memory.get_context(sid)
        agent_result = await run_agent(
            raw_translation=raw_translation,
            transcript=req.text,
            source_language=req.source_language,
            target_language=req.target_language,
            session_context=session_context,
            api_key=api_key,
        )
        final_translation = agent_result["final_translation"]

        # TTS
        import base64
        from sarvam.languages import tts_supported
        audio_b64 = None
        if tts_supported(req.target_language):
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
        "agent_reasoning": agent_result.get("agent_reasoning", ""),
        "glossary_used": agent_result.get("glossary_used", False),
    }


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
