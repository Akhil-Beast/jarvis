import threading
import time
import numpy as np
import speech_recognition as sr
from config.settings import config
from core.safety import logger, safety


class VoiceListener:
    """Continuous microphone listener with RMS energy metering and wake-word parsing.

    Fallback: if mic_device_index = -99, runs in TEXT INPUT mode — reads
    commands from stdin (for debugging without a working microphone).
    """

    TEXT_MODE_DEVICE = -99   # Magic value to enable text-input fallback

    def __init__(self, on_transcript=None, on_level=None, on_state_change=None):
        self.on_transcript = on_transcript
        self.on_level = on_level
        self.on_state_change = on_state_change

        self.is_active = False           # Master ON/OFF toggle
        self.is_listening_speech = False # Currently actively hearing speech
        self._running = False
        self._thread = None
        self._recognizer = sr.Recognizer()
        # Use fixed threshold unless explicitly set to dynamic
        self._recognizer.dynamic_energy_threshold = config.dynamic_energy_threshold
        self._recognizer.energy_threshold = config.audio_energy_threshold
        # Fast endpointing: decrease silence wait time from default 0.8s/0.5s to 0.5s/0.3s
        self._recognizer.pause_threshold = 0.5
        self._recognizer.non_speaking_duration = 0.3
        logger.info(f"[VoiceListener] energy_threshold={config.audio_energy_threshold} "
                    f"dynamic={config.dynamic_energy_threshold} "
                    f"device_index={config.mic_device_index}")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #
    def start(self):
        self._running = True
        if config.mic_device_index == self.TEXT_MODE_DEVICE:
            self._thread = threading.Thread(target=self._text_input_loop, daemon=True)
            logger.info("[VoiceListener] Starting in TEXT INPUT mode (no microphone).")
        else:
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            logger.info("[VoiceListener] Starting audio background worker.")
        self._thread.start()

    def stop(self):
        self._running = False

    def toggle(self) -> bool:
        """Toggle master assistant listening state."""
        self.is_active = not self.is_active
        logger.info(f"[VoiceListener] Active={self.is_active}")
        if self.on_state_change:
            self.on_state_change(self.is_active)
        return self.is_active

    def set_active(self, active: bool):
        self.is_active = active
        if self.on_state_change:
            self.on_state_change(self.is_active)

    # ------------------------------------------------------------------ #
    # Text-input fallback loop (no mic required)                           #
    # ------------------------------------------------------------------ #
    def _text_input_loop(self):
        import sys
        print("\n[JARVIS TEXT MODE] Type a command and press Enter (or 'quit' to exit):")
        while self._running:
            if not self.is_active:
                time.sleep(0.2)
                continue
            try:
                line = input(">>> ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line.lower() == "quit":
                self._running = False
                break
            logger.info(f"[VoiceListener/Text] Input: '{line}'")
            self._process_recognized_text(line)

    # ------------------------------------------------------------------ #
    # Main audio loop                                                      #
    # ------------------------------------------------------------------ #
    def _listen_loop(self):
        device_index = config.mic_device_index if config.mic_device_index >= 0 else None
        while self._running:
            mic = None
            try:
                mic = sr.Microphone(device_index=device_index, sample_rate=16000)
            except Exception as e:
                logger.error(f"[VoiceListener] Microphone init failed (device={device_index}): {e}. Retrying in 3s…")
                time.sleep(3.0)
                continue

            try:
                with mic as source:
                    # Only do ambient calibration if dynamic threshold is ON
                    if config.dynamic_energy_threshold:
                        try:
                            self._recognizer.adjust_for_ambient_noise(source, duration=0.8)
                            logger.info(f"[VoiceListener] Calibrated threshold: {self._recognizer.energy_threshold:.1f}")
                        except Exception as e:
                            logger.warning(f"[VoiceListener] Ambient calibration warning: {e}")
                    else:
                        logger.info(f"[VoiceListener] Fixed threshold: {self._recognizer.energy_threshold}")

                    while self._running:
                        if not self.is_active:
                            time.sleep(0.1)
                            if self.on_level:
                                self.on_level(0.0)
                            continue

                        if safety.is_aborted:
                            time.sleep(0.1)
                            continue

                        # Avoid acoustic echo feedback: if JARVIS is currently speaking, don't transcribe
                        from core.tts_engine import tts
                        if tts.is_speaking:
                            time.sleep(0.1)
                            if self.on_level:
                                self.on_level(0.0)
                            continue

                        try:
                            audio = self._recognizer.listen(
                                source,
                                timeout=1.5,
                                phrase_time_limit=10.0
                            )

                            # Energy / RMS for UI waveform
                            raw_data = audio.get_raw_data()
                            if raw_data:
                                samples = np.frombuffer(raw_data, dtype=np.int16)
                                rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
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
                            logger.debug(f"[VoiceListener] Listen error (transient): {e}")
                            time.sleep(0.05)

            except Exception as e:
                logger.error(f"[VoiceListener] Microphone stream error: {e}. Reinitializing in 2s…")
                time.sleep(2.0)

    # ------------------------------------------------------------------ #
    # Speech-to-Text                                                       #
    # ------------------------------------------------------------------ #
    def _recognize(self, audio) -> str:
        """Perform speech to text — Google online first, SAPI5/Sphinx offline fallback."""
        try:
            return self._recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.warning(f"[VoiceListener] Google STT unavailable ({e}), trying offline fallback.")
            try:
                return self._recognizer.recognize_sphinx(audio)
            except Exception:
                return ""

    # ------------------------------------------------------------------ #
    # Wake-word parsing and command dispatch                               #
    # ------------------------------------------------------------------ #
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
            is_triggered = True

        # Clean leading punctuation
        command = command.lstrip(",.:; ")

        if is_triggered and command and self.on_transcript:
            self.on_transcript(command)
