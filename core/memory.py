"""
core/memory.py — Conversation Memory & Session Persistence

Maintains a rolling window of recent exchanges so the AI brain can reference
prior commands and answers.  History is automatically saved to disk between
sessions.
"""
import json
import threading
from pathlib import Path
from core.safety import logger

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = BASE_DIR / "memory"
SESSION_FILE = MEMORY_DIR / "session.json"


class ConversationMemory:
    """Thread-safe conversation history with disk persistence.

    Each entry is a dict:
        {"role": "user" | "assistant", "content": str}
    """

    def __init__(self, max_history: int = 20):
        self._max = max_history
        self._lock = threading.Lock()
        self._history: list[dict] = []
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #
    def add(self, role: str, content: str):
        """Add a user or assistant message to history."""
        if not content or not content.strip():
            return
        with self._lock:
            self._history.append({"role": role, "content": content.strip()})
            # Trim to rolling window
            if len(self._history) > self._max:
                self._history = self._history[-self._max:]
        self._save()

    def get_context_string(self, max_turns: int = 10) -> str:
        """Return recent history formatted for injection into a system prompt."""
        with self._lock:
            recent = self._history[-max_turns * 2:]  # user+assistant pairs
        if not recent:
            return ""
        lines = []
        for entry in recent:
            role = "User" if entry["role"] == "user" else "JARVIS"
            lines.append(f"{role}: {entry['content']}")
        return "\n".join(lines)

    def get_history_for_gemini(self, max_turns: int = 6) -> list[dict]:
        """Return history list formatted for Gemini contents (role/parts)."""
        with self._lock:
            recent = self._history[-max_turns * 2:]
        result = []
        for entry in recent:
            # Gemini uses "user" / "model" roles
            gemini_role = "user" if entry["role"] == "user" else "model"
            result.append({"role": gemini_role, "parts": [{"text": entry["content"]}]})
        return result

    def clear(self):
        with self._lock:
            self._history.clear()
        self._save()
        logger.info("[Memory] Conversation history cleared.")

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #
    def _save(self):
        try:
            with self._lock:
                data = list(self._history)
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[Memory] Save failed: {e}")

    def _load(self):
        if not SESSION_FILE.exists():
            return
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self._history = data[-self._max:]
            logger.info(f"[Memory] Loaded {len(self._history)} previous exchanges from session.json.")
        except Exception as e:
            logger.warning(f"[Memory] Load failed: {e}")


# Singleton
memory = ConversationMemory()
