import queue
import threading
import requests
from config.settings import config
from core.safety import logger, safety
from core.omnivoice_engine import omnivoice_engine


class TTSEngine:
    """Thread-safe Text-to-Speech Engine supporting SAPI5 (offline) & ElevenLabs.

    Maintains a persistent pyttsx3 engine instance (created once) with a
    thread lock so it is never re-initialised per utterance, eliminating the
    lag and instability that caused the previous per-call init pattern.
    """

    def __init__(self):
        self._speech_queue = queue.Queue()
        self._is_speaking = False
        self._callbacks = []

        # Persistent SAPI5 engine — initialised once, locked for each utterance
        self._sapi5_engine = None
        self._sapi5_lock = threading.Lock()
        self._init_sapi5()

        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ #
    # SAPI5 engine lifecycle                                               #
    # ------------------------------------------------------------------ #
    def _init_sapi5(self):
        """Create the persistent pyttsx3 engine. Called once at startup."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", config.speech_rate)
            engine.setProperty("volume", config.speech_volume)
            voices = engine.getProperty("voices")
            if voices and 0 <= config.sapi5_voice_index < len(voices):
                engine.setProperty("voice", voices[config.sapi5_voice_index].id)
            self._sapi5_engine = engine
            logger.info("[TTS] Persistent SAPI5 engine initialised.")
        except Exception as e:
            logger.warning(f"[TTS] SAPI5 init failed: {e}. Will retry per utterance.")
            self._sapi5_engine = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #
    def register_state_callback(self, callback):
        """Callback format: callback(is_speaking: bool)"""
        self._callbacks.append(callback)

    def _notify(self, is_speaking: bool):
        self._is_speaking = is_speaking
        for cb in self._callbacks:
            try:
                cb(is_speaking)
            except Exception as e:
                logger.error(f"[TTS] Callback error: {e}")

    def speak(self, text: str, interrupt: bool = False):
        if not text or not text.strip():
            return
        if interrupt:
            self.stop()
        self._speech_queue.put(text.strip())

    def stop(self):
        """Clear queued speech."""
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
            except queue.Empty:
                break

    def _worker_loop(self):
        while True:
            text = self._speech_queue.get()
            if safety.is_aborted:
                self._speech_queue.task_done()
                continue

            self._notify(True)
            try:
                if config.tts_engine == "elevenlabs" and config.elevenlabs_api_key:
                    self._speak_elevenlabs(text)
                elif config.tts_engine == "omnivoice" and omnivoice_engine.is_available:
                    self._speak_omnivoice(text)
                else:
                    self._speak_sapi5(text)
            except Exception as e:
                logger.error(f"[TTS] Speech error: {e}")
                # Fallback to SAPI5
                try:
                    self._speak_sapi5(text)
                except Exception as fe:
                    logger.error(f"[TTS] SAPI5 fallback also failed: {fe}")
            finally:
                self._notify(False)
                self._speech_queue.task_done()

    def _speak_sapi5(self, text: str):
        """Speak via persistent pyttsx3 engine with thread lock."""
        with self._sapi5_lock:
            if self._sapi5_engine is None:
                self._init_sapi5()
            if self._sapi5_engine is None:
                logger.error("[TTS] No SAPI5 engine available.")
                return
            try:
                self._sapi5_engine.say(text)
                self._sapi5_engine.runAndWait()
            except Exception as e:
                logger.warning(f"[TTS] SAPI5 utterance error ({e}), reinitialising engine.")
                # Engine may be in a bad state — rebuild it
                try:
                    self._sapi5_engine.stop()
                except Exception:
                    pass
                self._sapi5_engine = None
                self._init_sapi5()
                # Retry once after reinit
                if self._sapi5_engine:
                    try:
                        self._sapi5_engine.say(text)
                        self._sapi5_engine.runAndWait()
                    except Exception:
                        pass

    def _speak_omnivoice(self, text: str):
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            if omnivoice_engine.synthesize_to_file(text, wav_path):
                import subprocess
                subprocess.run(["powershell", "-c", f'(New-Object Media.SoundPlayer "{wav_path}").PlaySync()'], check=False)
            else:
                self._speak_sapi5(text)
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass

    def _speak_elevenlabs(self, text: str):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.elevenlabs_voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": config.elevenlabs_api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        resp = requests.post(url, json=data, headers=headers, timeout=10)
        if resp.status_code == 200:
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(resp.content)
                tmp_path = f.name
            import subprocess
            subprocess.run(["powershell", "-c", f'(New-Object Media.SoundPlayer "{tmp_path}").PlaySync()'], check=False)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        else:
            logger.warning(f"ElevenLabs TTS failed ({resp.status_code}): {resp.text}, falling back to SAPI5")
            self._speak_sapi5(text)


tts = TTSEngine()
