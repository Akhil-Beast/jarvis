import queue
import threading
import time
import requests
from config.settings import config
from core.safety import logger, safety

class TTSEngine:
    """Thread-safe Text-to-Speech Engine supporting SAPI5 (offline) & ElevenLabs."""

    def __init__(self):
        self._speech_queue = queue.Queue()
        self._is_speaking = False
        self._callbacks = []
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

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
                else:
                    self._speak_sapi5(text)
            except Exception as e:
                logger.error(f"[TTS] Speech error: {e}")
                # Fallback to SAPI5
                try:
                    self._speak_sapi5(text)
                except Exception:
                    pass
            finally:
                self._notify(False)
                self._speech_queue.task_done()

    def _speak_sapi5(self, text: str):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", config.speech_rate)
        engine.setProperty("volume", config.speech_volume)
        
        voices = engine.getProperty("voices")
        if voices and 0 <= config.sapi5_voice_index < len(voices):
            engine.setProperty("voice", voices[config.sapi5_voice_index].id)
            
        engine.say(text)
        engine.runAndWait()
        del engine

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
            
            # Play mp3 on Windows using sounddevice / winsound or Windows Media
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
