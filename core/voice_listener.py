import threading
import time
import numpy as np
import speech_recognition as sr
from config.settings import config
from core.safety import logger, safety

class VoiceListener:
    """Continuous microphone listener with RMS energy metering and wake-word parsing."""

    def __init__(self, on_transcript=None, on_level=None, on_state_change=None):
        self.on_transcript = on_transcript
        self.on_level = on_level
        self.on_state_change = on_state_change
        
        self.is_active = False          # Master ON/OFF toggle
        self.is_listening_speech = False # Currently actively hearing speech
        self._running = False
        self._thread = None
        self._recognizer = sr.Recognizer()
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.energy_threshold = config.audio_energy_threshold

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("[VoiceListener] Audio background worker started.")

    def stop(self):
        self._running = False

    def toggle(self) -> bool:
        """Toggle master assistant listening state."""
        self.is_active = not self.is_active
        logger.info(f"[VoiceListener] Assistant Active State toggled to: {self.is_active}")
        if self.on_state_change:
            self.on_state_change(self.is_active)
        return self.is_active

    def set_active(self, active: bool):
        self.is_active = active
        if self.on_state_change:
            self.on_state_change(self.is_active)

    def _listen_loop(self):
        while self._running:
            mic = None
            try:
                mic = sr.Microphone()
            except Exception as e:
                logger.error(f"[VoiceListener] Microphone initialization failed: {e}. Retrying in 3s...")
                time.sleep(3.0)
                continue

            try:
                with mic as source:
                    try:
                        self._recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    except Exception as e:
                        logger.warning(f"[VoiceListener] Ambient noise calibration warning: {e}")

                    while self._running:
                        if not self.is_active:
                            time.sleep(0.1)
                            if self.on_level:
                                self.on_level(0.0)
                            continue

                        if safety.is_aborted:
                            time.sleep(0.1)
                            continue

                        try:
                            # Capture phrase with short timeout
                            audio = self._recognizer.listen(source, timeout=1.5, phrase_time_limit=10.0)
                            
                            # Calculate approximate energy for UI feedback
                            raw_data = audio.get_raw_data()
                            if raw_data:
                                samples = np.frombuffer(raw_data, dtype=np.int16)
                                rms = float(np.sqrt(np.mean(samples.astype(np.float32)**2)))
                                normalized_level = min(1.0, rms / 3000.0)
                                if self.on_level:
                                    self.on_level(normalized_level)

                            # Transcribe
                            text = self._recognize(audio)
                            if text and text.strip():
                                logger.info(f"[VoiceListener] Transcribed: '{text}'")
                                self._process_recognized_text(text.strip())

                        except sr.WaitTimeoutError:
                            if self.on_level:
                                self.on_level(0.0)
                            continue
                        except Exception as e:
                            # Ignore transient audio capture errors
                            time.sleep(0.05)
            except Exception as e:
                logger.error(f"[VoiceListener] Microphone stream error: {e}. Reinitializing in 2s...")
                time.sleep(2.0)

    def _recognize(self, audio) -> str:
        """Perform speech to text."""
        try:
            # Free cloud STT with zero setup
            return self._recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.warning(f"[VoiceListener] Google STT unavailable ({e}), trying Windows SAPI/Sphinx fallback.")
            try:
                return self._recognizer.recognize_sphinx(audio)
            except Exception:
                return ""

    def _process_recognized_text(self, text: str):
        text_lower = text.lower()
        wake1 = config.wake_word.lower()
        wake2 = config.wake_word_secondary.lower()

        command = text
        is_triggered = False

        if wake1 in text_lower:
            idx = text_lower.find(wake1) + len(wake1)
            command = text[idx:].strip()
            is_triggered = True
        elif wake2 in text_lower:
            idx = text_lower.find(wake2) + len(wake2)
            command = text[idx:].strip()
            is_triggered = True
        elif config.continuous_listening:
            # When active and continuous listening is enabled, any phrase is treated as a command
            is_triggered = True

        # Clean leading punctuation
        command = command.lstrip(",.:; ")

        if is_triggered and command and self.on_transcript:
            self.on_transcript(command)
