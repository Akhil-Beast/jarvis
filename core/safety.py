import logging
import threading
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "jarvis.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("JarvisSafety")

class SafetyManager:
    """Manages emergency stop states, destructive command validation, and logging."""

    DESTRUCTIVE_KEYWORDS = [
        "delete file", "delete folder", "remove directory", "format drive",
        "rmdir", "del /f", "shutdown", "restart pc", "reboot",
        "reg delete", "kill process", "uninstall"
    ]

    def __init__(self):
        self._abort_event = threading.Event()
        self._confirmation_callback = None

    def trigger_emergency_stop(self):
        """Immediately halts all active automation threads."""
        logger.warning("EMERGENCY STOP TRIGGERED!")
        self._abort_event.set()

    def reset_abort(self):
        """Reset emergency stop state for new commands."""
        self._abort_event.clear()

    @property
    def is_aborted(self) -> bool:
        return self._abort_event.is_set()

    def set_confirmation_handler(self, callback):
        """Register a callback for prompting the user (e.g. GUI dialog)."""
        self._confirmation_callback = callback

    def check_is_destructive(self, command_text: str) -> bool:
        cmd_lower = command_text.lower()
        return any(kw in cmd_lower for kw in self.DESTRUCTIVE_KEYWORDS)

    def request_confirmation(self, action_description: str) -> bool:
        """Ask user confirmation before executing potentially dangerous actions."""
        logger.warning(f"Safety check required for action: {action_description}")
        if self._confirmation_callback:
            return self._confirmation_callback(action_description)
        # Default fallback: reject if unattended
        return False

    def log_action(self, action_type: str, details: str, status: str = "SUCCESS"):
        logger.info(f"ACTION [{status}] [{action_type}]: {details}")

safety = SafetyManager()
