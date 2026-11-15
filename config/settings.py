import json
import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field

# Auto-load .env file from project root (safe — never overwrites existing env vars)
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            if _k.strip() and not os.environ.get(_k.strip()):
                os.environ[_k.strip()] = _v.strip()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.json"

class AppConfig(BaseModel):
    # Triggers & Hotkeys
    wake_word: str = "hey assistant"
    wake_word_secondary: str = "jarvis"
    hotkey_toggle: str = "<ctrl>+<alt>+<space>"
    hotkey_stop: str = "<esc>"
    continuous_listening: bool = True

    # AI Brain
    ai_provider: str = "auto"  # "auto", "gemini", "openai", "anthropic", "local_rules"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    openai_model: str = "gpt-4o"

    # Voice / TTS
    tts_engine: str = "sapi5"  # "sapi5" (offline Windows) or "elevenlabs"
    speech_rate: int = 190     # Words per minute
    speech_volume: float = 1.0 # 0.0 to 1.0
    sapi5_voice_index: int = 0
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "pNInz6obpgDQGcFmaJgB"  # British voice (Adam)

    # Audio / Microphone
    mic_device_index: int = -1          # -1 = system default; set to specific index from mic_test.py
    dynamic_energy_threshold: bool = False  # False = use fixed threshold (more reliable)
    audio_energy_threshold: int = 300   # Lower = more sensitive; raise if false triggers occur

    # Behavior & Safety
    require_confirmation_for_destructive: bool = True
    start_with_windows: bool = False
    minimize_to_tray_on_close: bool = True

    # User Profile
    user_name: str = "Sir"
    assistant_name: str = "JARVIS"

class SettingsManager:
    def __init__(self):
        self.config_path = CONFIG_FILE
        self.config = self.load()

    def load(self) -> AppConfig:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    cfg = AppConfig(**data)
                    # Fill any blank keys from environment (e.g. if .env has newer key)
                    if not cfg.gemini_api_key:
                        cfg.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
                    if not cfg.openai_api_key:
                        cfg.openai_api_key = os.getenv("OPENAI_API_KEY", "")
                    if not cfg.elevenlabs_api_key:
                        cfg.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "")
                    return cfg
            except Exception as e:
                print(f"[Settings] Failed to parse config.json, using defaults: {e}")
        
        cfg = AppConfig()
        # Fall back to env variables if available
        cfg.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        cfg.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        cfg.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        cfg.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "")
        self.save(cfg)
        return cfg

    def save(self, config: AppConfig | None = None):
        if config is not None:
            self.config = config
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config.model_dump(), f, indent=4)

    def set_start_with_windows(self, enable: bool):
        """Register/unregister application in Windows Run registry key."""
        if sys.platform != "win32":
            return
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "JarvisVoiceAssistant"
        executable = sys.executable
        script = str(BASE_DIR / "main.py")
        cmd = f'"{executable}" "{script}" --minimized'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self.config.start_with_windows = enable
            self.save()
        except Exception as e:
            print(f"[Settings] Error modifying Windows startup registry: {e}")

settings_manager = SettingsManager()
config = settings_manager.config
