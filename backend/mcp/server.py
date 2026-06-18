# mcp/server.py
# MCP (Model Context Protocol) tool server.
# Exposes 3 tools the LangGraph agent can call during translation processing.
# Mounted at /mcp on the main FastAPI app (not a separate service).
#
# Each tool endpoint:
#   - Has a well-defined JSON schema (the agent uses this to decide when to call it)
#   - Returns structured JSON
#   - Has proper error responses (agent can retry on 5xx, not on 4xx)
#   - Is idempotent (calling it twice with the same input returns the same output)

import os
import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional

from sarvam.client import SarvamClient, SarvamError
from .glossary_lookup import lookup_term, list_domains

logger = logging.getLogger(__name__)

# MCP router — mounted at /mcp in main.py
mcp_router = APIRouter(prefix="/mcp", tags=["MCP Tools"])


# ─────────────────────────────────────────────
# Tool schema endpoint — agent fetches this to know what tools exist
# ─────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "detect_language",
        "description": (
            "Identifies the language of a given text string. "
            "Use this when the source language is unknown or you want to verify "
            "that the detected language matches expectations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text whose language should be detected",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "transliterate",
        "description": (
            "Converts text between scripts without changing meaning. "
            "For example, converts Hindi written in Devanagari script to Roman script. "
            "Useful when the target audience can understand the language but not read the script."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to transliterate",
                },
                "source_language_code": {
                    "type": "string",
                    "description": "BCP-47 code of the input text's language (e.g. 'hi-IN')",
                },
                "target_language_code": {
                    "type": "string",
                    "description": "BCP-47 code for target script (default: 'en-IN' for Romanization)",
                    "default": "en-IN",
                },
            },
            "required": ["text", "source_language_code"],
        },
    },
    {
        "name": "glossary_lookup",
        "description": (
            "Looks up domain-specific terms (medical, legal, technical, financial) "
            "and returns their precise definition and preferred translation in the target language. "
            "Use this when the translated text contains terminology that might be imprecise."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "The English term to look up",
                },
                "target_language_code": {
                    "type": "string",
                    "description": "BCP-47 code for the desired translation hint (e.g. 'ta-IN')",
                },
            },
            "required": ["term"],
        },
    },
]


@mcp_router.get("/tools")
async def list_tools():
    """Returns all available MCP tool schemas. Agent calls this on startup."""
    return {"tools": TOOL_SCHEMAS}


# ─────────────────────────────────────────────
# Tool 1: Detect Language
# ─────────────────────────────────────────────

class DetectLanguageRequest(BaseModel):
    text: str = Field(..., description="Text to identify language of")


@mcp_router.post("/tools/detect_language")
async def detect_language(
    req: DetectLanguageRequest,
    x_api_key: Optional[str] = Header(None, alias="X-Sarvam-Key"),
):
    """
    Wraps Sarvam Language ID API.
    Returns detected language code and confidence score.
    """
    api_key = x_api_key or os.environ.get("SARVAM_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No Sarvam API key provided")

    try:
        async with SarvamClient(api_key) as client:
            result = await client.detect_language(req.text)
        return {"success": True, **result}
    except SarvamError as e:
        # 4xx from Sarvam → don't retry (bad key, bad input)
        if e.status_code and e.status_code < 500:
            raise HTTPException(status_code=400, detail=str(e))
        # 5xx → agent can retry
        raise HTTPException(status_code=502, detail=str(e))


# ─────────────────────────────────────────────
# Tool 2: Transliterate
# ─────────────────────────────────────────────

class TransliterateRequest(BaseModel):
    text: str = Field(..., description="Text to transliterate")
    source_language_code: str = Field(..., description="BCP-47 source language")
    target_language_code: str = Field("en-IN", description="BCP-47 target script")


@mcp_router.post("/tools/transliterate")
async def transliterate(
    req: TransliterateRequest,
    x_api_key: Optional[str] = Header(None, alias="X-Sarvam-Key"),
):
    """
    Converts script without translating meaning.
    Idempotent: same input always produces same output.
    """
    api_key = x_api_key or os.environ.get("SARVAM_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No Sarvam API key provided")

    try:
        async with SarvamClient(api_key) as client:
            result = await client.transliterate(
                text=req.text,
                source_language_code=req.source_language_code,
                target_language_code=req.target_language_code,
            )
        return {"success": True, "transliterated_text": result}
    except SarvamError as e:
        if e.status_code and e.status_code < 500:
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=502, detail=str(e))


# ─────────────────────────────────────────────
# Tool 3: Glossary Lookup
# ─────────────────────────────────────────────

class GlossaryRequest(BaseModel):
    term: str = Field(..., description="English term to look up")
    target_language_code: Optional[str] = Field(
        None, description="BCP-47 code for translation hint"
    )


@mcp_router.post("/tools/glossary_lookup")
async def glossary_lookup(req: GlossaryRequest):
    """
    Looks up domain-specific terms. No API call — local dict (Qdrant later).
    Always returns 200; check 'found' field in response to see if term exists.
    """
    result = lookup_term(
        term=req.term,
        target_language_code=req.target_language_code,
    )
    return {"success": True, **result}


@mcp_router.get("/tools/glossary_lookup/domains")
async def glossary_domains():
    """Returns available glossary domains. Useful for UI badges."""
    return {"domains": list_domains()}
