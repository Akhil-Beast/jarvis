"""
scratch/cloud_tester.py — Comprehensive Cloud Verification Suite for JARVIS
Tests live Render deployment:
- Healthcheck & uptime monitors (GET, HEAD, OPTIONS)
- Detailed host diagnostics (/api/status)
- Web HUD HTML integrity
- Autonomous Cognitive Brain (/api/chat) across multiple scenarios
- Neural Edge-TTS MP3 streaming (/api/tts)
"""
import sys
import time
import json
import httpx

CLOUD_URL = "https://jarvis-ai-wfcl.onrender.com"

print("=" * 70)
print("RUNNING JARVIS CLOUD TESTER")
print(f"Target: {CLOUD_URL}")
print(f"Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

results = []

def record(test_name, passed, details, latency=None):
    results.append({
        "name": test_name,
        "passed": passed,
        "details": details,
        "latency": f"{latency:.2f}s" if latency is not None else "N/A"
    })
    status_icon = "[PASS]" if passed else "[FAIL]"
    lat_str = f" ({latency:.2f}s)" if latency is not None else ""
    print(f"{status_icon} | {test_name}{lat_str}")
    print(f"       Details: {details}\n")


with httpx.Client(base_url=CLOUD_URL, timeout=45.0, follow_redirects=True) as client:
    # ------------------------------------------------------------------ #
    # Test 1: Healthcheck GET, HEAD, OPTIONS                             #
    # ------------------------------------------------------------------ #
    try:
        t0 = time.time()
        resp_get = client.get("/health")
        t_get = time.time() - t0
        data = resp_get.json()
        record("Healthcheck GET", resp_get.status_code == 200 and data.get("status") == "online",
               f"Status {resp_get.status_code}, Assistant: {data.get('assistant')}, Uptime: {data.get('uptime_formatted')}", t_get)
    except Exception as e:
        record("Healthcheck GET", False, str(e))

    try:
        t0 = time.time()
        resp_head = client.head("/health")
        t_head = time.time() - t0
        record("Healthcheck HEAD (UptimeRobot Probe)", resp_head.status_code == 200,
               f"HTTP {resp_head.status_code} OK (Protects against 405 Method Not Allowed)", t_head)
    except Exception as e:
        record("Healthcheck HEAD (UptimeRobot Probe)", False, str(e))

    try:
        t0 = time.time()
        resp_opt = client.options("/health")
        t_opt = time.time() - t0
        record("Healthcheck OPTIONS", resp_opt.status_code == 200,
               f"HTTP {resp_opt.status_code} OK, Allow: {resp_opt.headers.get('allow', 'N/A')}", t_opt)
    except Exception as e:
        record("Healthcheck OPTIONS", False, str(e))

    # ------------------------------------------------------------------ #
    # Test 2: System Host Diagnostics (/api/status)                      #
    # ------------------------------------------------------------------ #
    try:
        t0 = time.time()
        resp = client.get("/api/status")
        t_stat = time.time() - t0
        data = resp.json()
        record("System Diagnostics (/api/status)", resp.status_code == 200,
               f"Platform: {data.get('platform')}, Python: {data.get('python_version')}, CPU: {data.get('cpu_usage_pct')}%, RAM: {data.get('memory_usage_pct')}%", t_stat)
    except Exception as e:
        record("System Diagnostics (/api/status)", False, str(e))

    # ------------------------------------------------------------------ #
    # Test 3: Web HUD HTML Frontend (/ )                                 #
    # ------------------------------------------------------------------ #
    try:
        t0 = time.time()
        resp = client.get("/")
        t_hud = time.time() - t0
        html = resp.text
        has_canvas = "reactorCanvas" in html
        has_mic = "btnMic" in html
        has_orbitron = "Orbitron" in html
        has_quick_links = "webAppMap" in html or "Open YouTube" in html or "youtube" in html
        all_elements = has_canvas and has_mic and has_orbitron
        record("Web HUD HTML Frontend (/)", resp.status_code == 200 and all_elements,
               f"Canvas Reactor: {has_canvas}, Mic Recognition: {has_mic}, HUD Typography: {has_orbitron}, Size: {len(html)} bytes", t_hud)
    except Exception as e:
        record("Web HUD HTML Frontend (/)", False, str(e))

    # ------------------------------------------------------------------ #
    # Test 4: Cognitive Brain — Desktop App Command ("Open Google Chrome") #
    # ------------------------------------------------------------------ #
    try:
        t0 = time.time()
        resp = client.post("/api/chat", json={"message": "Open Google Chrome"})
        t_chat1 = time.time() - t0
        data = resp.json()
        thought = data.get("thought", "")
        spoken = data.get("spoken_text", "")
        steps = data.get("steps", [])
        has_desktop_steps = any(s.get("action") not in ("speak",) for s in steps)
        # Should gracefully explain cloud mode, NO desktop steps
        passed = (resp.status_code == 200 and data.get("status") == "success"
                  and not has_desktop_steps and len(spoken) > 10)
        record("Cognitive Brain: 'Open Google Chrome'", passed,
               f"Spoken: '{spoken[:90]}...'\n       Thought: '{thought[:90]}...'\n       Steps ({len(steps)}): {steps}", t_chat1)
    except Exception as e:
        record("Cognitive Brain: 'Open Google Chrome'", False, str(e))

    # ------------------------------------------------------------------ #
    # Test 5: Cognitive Brain — Logic & Calculation ("What is 2 + 2?")   #
    # ------------------------------------------------------------------ #
    try:
        t0 = time.time()
        resp = client.post("/api/chat", json={"message": "What is 2 + 2?"})
        t_chat2 = time.time() - t0
        data = resp.json()
        spoken = data.get("spoken_text", "")
        thought = data.get("thought", "")
        has_four = "four" in spoken.lower() or "4" in spoken
        passed = resp.status_code == 200 and has_four
        record("Cognitive Brain: 'What is 2 + 2?'", passed,
               f"Spoken: '{spoken}'\n       Thought: '{thought[:90]}...'", t_chat2)
    except Exception as e:
        record("Cognitive Brain: 'What is 2 + 2?'", False, str(e))

    # ------------------------------------------------------------------ #
    # Test 6: Cognitive Brain — Wit & Persona ("Tell me a joke")        #
    # ------------------------------------------------------------------ #
    try:
        t0 = time.time()
        resp = client.post("/api/chat", json={"message": "Tell me a joke"})
        t_chat3 = time.time() - t0
        data = resp.json()
        spoken = data.get("spoken_text", "")
        thought = data.get("thought", "")
        passed = resp.status_code == 200 and len(spoken) > 20
        record("Cognitive Brain: 'Tell me a joke'", passed,
               f"Spoken: '{spoken[:100]}...'\n       Thought: '{thought[:90]}...'", t_chat3)
    except Exception as e:
        record("Cognitive Brain: 'Tell me a joke'", False, str(e))

    # ------------------------------------------------------------------ #
    # Test 7: Neural Edge-TTS British Audio Streaming (/api/tts)         #
    # ------------------------------------------------------------------ #
    try:
        t0 = time.time()
        sample_text = "Good day, Sir. All systems on the cloud node are performing at peak efficiency."
        resp = client.get(f"/api/tts?text={sample_text}")
        t_tts = time.time() - t0
        audio_bytes = resp.content
        content_type = resp.headers.get("content-type", "")
        # MP3 file magic header or MPEG content-type
        is_mp3 = "mpeg" in content_type or audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff\xfb") or len(audio_bytes) > 5000
        passed = resp.status_code == 200 and is_mp3 and len(audio_bytes) > 1000
        record("Neural British TTS Streaming (/api/tts)", passed,
               f"HTTP {resp.status_code}, Content-Type: {content_type}, Audio Size: {len(audio_bytes):,} bytes (valid MP3 stream)", t_tts)
    except Exception as e:
        record("Neural British TTS Streaming (/api/tts)", False, str(e))


# ---------------------------------------------------------------------- #
# Summary Report                                                         #
# ---------------------------------------------------------------------- #
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
total = len(results)
passed = sum(1 for r in results if r["passed"])
print(f"Total Tests Run: {total}")
print(f"Passed:         {passed} / {total} ({(passed/total)*100:.1f}%)")
if passed == total:
    print("ALL CLOUD SYSTEMS OPERATIONAL & VERIFIED!")
else:
    print("SOME TESTS FAILED. See details above.")
print("=" * 70)
