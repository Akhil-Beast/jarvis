import asyncio
import os
import queue
import tempfile
import threading
import time
import requests
import pygame

from config.settings import config
from core.safety import logger, safety
from core.omnivoice_engine import omnivoice_engine


class TTSEngine:
    """Thread-safe Text-to-Speech Engine.

    Supports:
    1. Edge-TTS (Default): Ultra-realistic British neural voice ('en-GB-RyanNeural') via pygame.mixer
    2. ElevenLabs: Premium cloud voice
    3. SAPI5 (Offline fallback): Windows native David/Zira
    """

    def __init__(self):
        self._speech_queue = queue.Queue()
        self._is_speaking = False
        self._callbacks = []

        # Initialize pygame.mixer for zero-latency audio playback
        try:
            pygame.mixer.init()
            self._mixer_ready = True
        except Exception as e:
            logger.warning(f"[TTS] pygame.mixer init warning: {e}")
            self._mixer_ready = False

        # Persistent SAPI5 engine as offline fallback
        self._sapi5_engine = None
        self._sapi5_lock = threading.Lock()
        self._init_sapi5()

        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ #
    # SAPI5 engine lifecycle (Offline fallback)                           #
    # ------------------------------------------------------------------ #
    def _init_sapi5(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", config.speech_rate)
            engine.setProperty("volume", config.speech_volume)
            voices = engine.getProperty("voices")
            if voices and 0 <= config.sapi5_voice_index < len(voices):
                engine.setProperty("voice", voices[config.sapi5_voice_index].id)
            self._sapi5_engine = engine
            logger.info("[TTS] Persistent SAPI5 fallback engine initialised.")
        except Exception as e:
            logger.warning(f"[TTS] SAPI5 init failed: {e}")
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
        """Immediately stop currently playing audio and clear queued speech."""
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
            except queue.Empty:
                break
        if self._mixer_ready:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        with self._sapi5_lock:
            if self._sapi5_engine:
                try:
                    self._sapi5_engine.stop()
                except Exception:
                    pass

    # ------------------------------------------------------------------ #
    # Worker Loop                                                          #
    # ------------------------------------------------------------------ #
    def _worker_loop(self):
        while True:
            text = self._speech_queue.get()
            if safety.is_aborted:
                self._speech_queue.task_done()
                continue

            self._notify(True)
            try:
                engine_choice = getattr(config, "tts_engine", "edge_tts")
                if engine_choice == "elevenlabs" and config.elevenlabs_api_key:
                    self._speak_elevenlabs(text)
                elif engine_choice == "omnivoice" and omnivoice_engine.is_available:
                    self._speak_omnivoice(text)
                elif engine_choice == "edge_tts":
                    self._speak_edge_tts(text)
                else:
                    self._speak_sapi5(text)
            except Exception as e:
                logger.error(f"[TTS] Speech synthesis error: {e}. Falling back to SAPI5.")
                try:
                    self._speak_sapi5(text)
                except Exception as fe:
                    logger.error(f"[TTS] SAPI5 fallback also failed: {fe}")
            finally:
                self._notify(False)
                self._speech_queue.task_done()

    # ------------------------------------------------------------------ #
    # Edge-TTS Neural Voice (British JARVIS Persona)                     #
    # ------------------------------------------------------------------ #
    def _speak_edge_tts(self, text: str):
        import edge_tts

        # Clean conversational text of markdown markers
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
        voice = getattr(config, "edge_tts_voice", "en-GB-RyanNeural")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name

        async def _synthesize():
            comm = edge_tts.Communicate(clean_text, voice)
            await comm.save(tmp_path)

        try:
            asyncio.run(_synthesize())

            if self._mixer_ready:
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if safety.is_aborted:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.04)
            else:
                self._speak_sapi5(text)
        except Exception as e:
            logger.warning(f"[TTS] Edge-TTS failed: {e}. Retrying via SAPI5.")
            self._speak_sapi5(text)
        finally:
            if self._mixer_ready:
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # SAPI5 Native Windows Voice                                         #
    # ------------------------------------------------------------------ #
    def _speak_sapi5(self, text: str):
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
                try:
                    self._sapi5_engine.stop()
                except Exception:
                    pass
                self._sapi5_engine = None
                self._init_sapi5()
                if self._sapi5_engine:
                    try:
                        self._sapi5_engine.say(text)
                        self._sapi5_engine.runAndWait()
                    except Exception:
                        pass

    # ------------------------------------------------------------------ #
    # ElevenLabs / OmniVoice Fallbacks                                    #
    # ------------------------------------------------------------------ #
    def _speak_omnivoice(self, text: str):
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
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(resp.content)
                tmp_path = f.name
            try:
                if self._mixer_ready:
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        if safety.is_aborted:
                            pygame.mixer.music.stop()
                            break
                        time.sleep(0.04)
            finally:
                try:
                    pygame.mixer.music.unload()
                    os.remove(tmp_path)
                except Exception:
                    pass
        else:
            logger.warning(f"[TTS] ElevenLabs failed ({resp.status_code}), falling back to Edge-TTS")
            self._speak_edge_tts(text)


tts = TTSEngine()
