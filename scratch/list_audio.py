import pyaudio, numpy as np

pa = pyaudio.PyAudio()
print("=== Available Input Devices ===")
for i in range(pa.get_device_count()):
    d = pa.get_device_info_by_index(i)
    if d['maxInputChannels'] > 0:
        print(f"[{i}] {d['name']} | ch={d['maxInputChannels']} | rate={int(d['defaultSampleRate'])}")
pa.terminate()
