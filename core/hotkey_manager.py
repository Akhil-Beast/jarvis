import threading
from pynput import keyboard
from config.settings import config
from core.safety import logger, safety

class HotkeyManager:
    """Manages system-wide global keyboard shortcuts."""

    def __init__(self, toggle_callback=None, stop_callback=None):
        self.toggle_callback = toggle_callback
        self.stop_callback = stop_callback
        self._listener = None
        self._thread = None

    def start(self):
        hotkeys = {
            config.hotkey_toggle: self._on_toggle,
            config.hotkey_stop: self._on_stop
        }
        try:
            self._listener = keyboard.GlobalHotKeys(hotkeys)
            self._listener.daemon = True
            self._listener.start()
            logger.info(f"[Hotkey] Registered: Toggle={config.hotkey_toggle}, Stop={config.hotkey_stop}")
        except Exception as e:
            logger.error(f"[Hotkey] Failed to register global hotkeys: {e}")

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_toggle(self):
        logger.info("[Hotkey] Global Toggle shortcut pressed.")
        if self.toggle_callback:
            self.toggle_callback()

    def _on_stop(self):
        logger.warning("[Hotkey] Global EMERGENCY STOP pressed (Escape).")
        safety.trigger_emergency_stop()
        if self.stop_callback:
            self.stop_callback()
