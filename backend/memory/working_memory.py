# memory/working_memory.py
# Working memory = last N conversation turns held in-context for the LangGraph agent.
# This is intentionally simple: a dict keyed by session_id, values are a deque of turns.
# No database, no persistence across restarts — that's the point of "working" memory.
# Long-term memory (Qdrant) will be added later per the project plan.

from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional
import time
import threading


# How many past turns the agent sees. 5 is enough for conversational context
# without bloating the LLM prompt. Increase if translations reference earlier terms.
MAX_TURNS = 5

# Sessions older than this are auto-evicted (saves RAM on Render's free 512MB)
SESSION_TTL_SECONDS = 3600  # 1 hour


@dataclass
class Turn:
    """One exchange: what the user said and what the agent produced."""
    source_text: str       # Original transcript in source language
    translated_text: str   # Final translation after agent processing
    source_lang: str       # BCP-47 detected source language
    target_lang: str       # BCP-47 target language
    timestamp: float = field(default_factory=time.time)

    def to_context_string(self) -> str:
        """
        Formats this turn for injection into the agent's system prompt.
        Keeps it compact — the agent doesn't need the full metadata.
        """
        return (
            f"[{self.source_lang}→{self.target_lang}] "
            f'"{self.source_text}" → "{self.translated_text}"'
        )


class WorkingMemory:
    """
    Thread-safe in-memory store.
    One instance lives for the lifetime of the FastAPI process.
    Sessions are identified by a UUID the frontend generates and sends
    in every request header (X-Session-ID).
    """

    def __init__(self):
        # session_id → deque of Turn objects (max MAX_TURNS)
        self._sessions: dict[str, deque[Turn]] = {}
        # session_id → last access time (for TTL eviction)
        self._last_access: dict[str, float] = {}
        self._lock = threading.Lock()

    def add_turn(self, session_id: str, turn: Turn):
        """Add a completed turn to a session's memory."""
        with self._lock:
            self._evict_stale()
            if session_id not in self._sessions:
                self._sessions[session_id] = deque(maxlen=MAX_TURNS)
            self._sessions[session_id].append(turn)
            self._last_access[session_id] = time.time()

    def get_context(self, session_id: str) -> str:
        """
        Returns a formatted string of recent turns ready to paste into
        the agent's system prompt. Empty string if no history.
        """
        with self._lock:
            turns = self._sessions.get(session_id, deque())
            if not turns:
                return ""
            lines = [t.to_context_string() for t in turns]
            return "Recent conversation:\n" + "\n".join(lines)

    def get_turns(self, session_id: str) -> list[dict]:
        """Returns turns as plain dicts (for API responses/debugging)."""
        with self._lock:
            turns = self._sessions.get(session_id, deque())
            return [asdict(t) for t in turns]

    def clear_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            self._last_access.pop(session_id, None)

    def _evict_stale(self):
        """Remove sessions not accessed within SESSION_TTL_SECONDS. Called under lock."""
        cutoff = time.time() - SESSION_TTL_SECONDS
        stale = [sid for sid, t in self._last_access.items() if t < cutoff]
        for sid in stale:
            self._sessions.pop(sid, None)
            self._last_access.pop(sid, None)

    @property
    def active_sessions(self) -> int:
        with self._lock:
            return len(self._sessions)


# Module-level singleton — imported by main.py and shared across all requests
memory = WorkingMemory()
