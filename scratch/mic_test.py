"""
mic_test.py — Tests each input device for real signal level.
Run: d:\jarvis\venv\Scripts\python.exe d:\jarvis\scratch\mic_test.py
"""
import pyaudio
import numpy as np
import time

DEVICES_TO_TEST = [1, 12, 20, 28]   # Intel array, Intel 2ch, Realtek, Virtual array
SAMPLE_RATE = 16000
CHUNK = 1024
DURATION = 3  # seconds per device

pa = pyaudio.PyAudio()

for idx in DEVICES_TO_TEST:
    try:
        info = pa.get_device_info_by_index(idx)
        name = info['name']
        ch = min(info['maxInputChannels'], 1)   # force mono
        rate = SAMPLE_RATE
        print(f"\n--- Testing device [{idx}]: {name} ---")
        print(f"    Opening: ch={ch}, rate={rate}")
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=ch,
            rate=rate,
            input=True,
            input_device_index=idx,
            frames_per_buffer=CHUNK
        )
        print(f"    Recording {DURATION}s — speak now...")
        frames = []
        for _ in range(int(rate / CHUNK * DURATION)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        raw = b''.join(frames)
        samples = np.frombuffer(raw, dtype=np.int16)
        rms = float(np.sqrt(np.mean(samples.astype(float)**2)))
        peak = int(np.max(np.abs(samples)))
        print(f"    RMS={rms:.1f}  Peak={peak}")
        if rms > 200:
            print(f"    ✅ GOOD SIGNAL — use device_index={idx}")
        elif rms > 50:
            print(f"    ⚠️  WEAK SIGNAL — marginal, may work")
        else:
            print(f"    ❌ NEAR-ZERO — muted or wrong device")
    except Exception as e:
        print(f"    ❌ Failed: {e}")

pa.terminate()
print("\nDone. Set the best device_index in settings.")
