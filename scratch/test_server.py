"""
scratch/test_server.py
Unit test for JARVIS FastAPI 24/7 Cloud Server
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_endpoints():
    print("Testing /health endpoint...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("Health response:", resp.json())

    print("\nTesting /api/status endpoint...")
    resp = client.get("/api/status")
    assert resp.status_code == 200, f"Status failed: {resp.text}"
    print("Status response:", resp.json())

    print("\nTesting / (Web HUD) endpoint...")
    resp = client.get("/")
    assert resp.status_code == 200, f"Web HUD failed: {resp.text}"
    assert "JARVIS" in resp.text
    print("Web HUD rendered successfully!")

    print("\nTesting /api/chat endpoint...")
    resp = client.post("/api/chat", json={"message": "What is the capital of France?"})
    assert resp.status_code == 200, f"Chat failed: {resp.text}"
    data = resp.json()
    print("Chat response:")
    print("  Thought:", data.get("thought"))
    print("  Spoken:", data.get("spoken_text"))
    print("  Latency:", data.get("latency_seconds"), "s")

    print("\nTesting /api/tts audio endpoint...")
    resp = client.get("/api/tts?text=Test+audio")
    assert resp.status_code == 200, f"TTS failed: {resp.text}"
    assert resp.headers["content-type"] == "audio/mpeg"
    print(f"TTS generated {len(resp.content)} bytes of audio/mpeg successfully!")

    print("\nALL SERVER TESTS PASSED!")

if __name__ == "__main__":
    test_endpoints()
