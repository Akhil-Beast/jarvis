"""
server.py — 24/7 Cloud Web Service & API for JARVIS AI Assistant
Deployable on Render, Railway, Fly.io, or any cloud/container host.

Features:
- High-Performance FastAPI Web Server
- 24/7 Auto-KeepAlive Ping Loop (prevents Render free-tier idle spin down)
- Interactive Futuristic Web HUD (browser voice input + speaker playback)
- Streaming Neural Text-to-Speech (/api/tts via edge-tts British voice)
- Autonomous Cognitive AI Brain API (/api/chat)
- Uptime & Health Monitor (/health, /api/status)
"""
import os
import sys
import time
import asyncio
import urllib.parse
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pydantic import BaseModel

from config.settings import config
from core.safety import logger
from core.brain import brain

BASE_DIR = Path(__file__).resolve().parent
START_TIME = time.time()


# ---------------------------------------------------------------------- #
# 24/7 Keep-Alive Background Worker (Render Free Tier Sleepless Loop)   #
# ---------------------------------------------------------------------- #
async def _keep_alive_task():
    """Pings its own healthcheck endpoint every 10 minutes to stay awake 24/7."""
    render_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("HOST_URL")
    if not render_url:
        logger.info("[KeepAlive] No external URL configured; local mode active.")
        return

    target = f"{render_url.rstrip('/')}/health"
    logger.info(f"[KeepAlive] 24/7 sleepless monitor active. Pinging: {target}")

    import httpx
    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            await asyncio.sleep(600)  # Ping every 10 minutes (Render timeout is 15 min)
            try:
                resp = await client.get(target)
                logger.info(f"[KeepAlive] 24/7 heartbeat ping returned {resp.status_code}")
            except Exception as e:
                logger.debug(f"[KeepAlive] Ping notice: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: spawn background 24/7 keep-alive monitor
    task = asyncio.create_task(_keep_alive_task())
    logger.info("[Server] JARVIS Cloud Server online and ready.")
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="JARVIS AI Cloud Assistant",
    description="24/7 Autonomous Cognitive Personal AI Assistant",
    version="2.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def uptime_monitor_middleware(request: Request, call_next):
    """Guarantees all uptime monitors sending HEAD, OPTIONS, or health checks receive 200 OK."""
    if request.method == "HEAD":
        return Response(status_code=200)
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Allow": "GET, HEAD, POST, OPTIONS"})
    return await call_next(request)


# ---------------------------------------------------------------------- #
# Request & Response Models                                             #
# ---------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------- #
# Health & Status Endpoints (Accepts GET, HEAD, POST, OPTIONS)          #
# ---------------------------------------------------------------------- #
@app.api_route("/health", methods=["GET", "HEAD", "POST", "OPTIONS"])
@app.api_route("/api/ping", methods=["GET", "HEAD", "POST", "OPTIONS"])
async def health(request: Request):
    """Uptime healthcheck endpoint used by Render and external monitors."""
    if request.method == "HEAD":
        return Response(status_code=200)
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Allow": "GET, HEAD, POST, OPTIONS"})
    uptime_sec = int(time.time() - START_TIME)
    return JSONResponse({
        "status": "online",
        "service": "JARVIS Cloud Node",
        "assistant": config.assistant_name,
        "persona": "British Autonomous Cognitive AI",
        "uptime_seconds": uptime_sec,
        "uptime_formatted": f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s",
        "model": config.gemini_model,
        "mode": "24/7 Continuous"
    })


@app.api_route("/api/status", methods=["GET", "HEAD", "POST", "OPTIONS"])
async def status(request: Request):
    """Detailed system performance and host diagnostics."""
    if request.method == "HEAD":
        return Response(status_code=200)
    import psutil
    mem = psutil.virtual_memory()
    return JSONResponse({
        "assistant": config.assistant_name,
        "user": config.user_name,
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
        "cpu_usage_pct": psutil.cpu_percent(),
        "memory_usage_pct": mem.percent,
        "memory_available_mb": round(mem.available / (1024 * 1024), 1),
        "ai_model": config.gemini_model,
        "tts_voice": config.edge_tts_voice,
        "render_external_url": os.getenv("RENDER_EXTERNAL_URL", "not_set")
    })


# ---------------------------------------------------------------------- #
# Neural Text-to-Speech Streaming Endpoint                              #
# ---------------------------------------------------------------------- #
@app.get("/api/tts")
async def text_to_speech(text: str = Query(..., min_length=1, max_length=2000)):
    """Generates ultra-realistic British neural speech and streams MP3 audio."""
    import edge_tts

    # Clean conversational markdown markers
    clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
    voice = getattr(config, "edge_tts_voice", "en-GB-RyanNeural")

    try:
        comm = edge_tts.Communicate(clean_text, voice)
        chunks = []
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

        audio_bytes = b"".join(chunks)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"[Server/TTS] Speech synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS synthesis error: {str(e)}")


# ---------------------------------------------------------------------- #
# Cognitive AI Brain Chat & Execution Endpoint                          #
# ---------------------------------------------------------------------- #
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Processes natural speech or text through the autonomous Gemini cognitive brain."""
    user_text = req.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    t0 = time.time()
    try:
        # Off-thread execution to keep server completely responsive
        plan = await asyncio.to_thread(brain.plan_command, user_text)
        elapsed = time.time() - t0

        spoken = getattr(plan, "spoken_text", None) or plan.explanation or "At your service, sir."
        thought = getattr(plan, "thought", "") or "Evaluating request and situational context."

        audio_url = f"/api/tts?text={urllib.parse.quote(spoken)}"

        return {
            "status": "success",
            "command": user_text,
            "thought": thought,
            "spoken_text": spoken,
            "explanation": plan.explanation,
            "steps": plan.steps,
            "audio_url": audio_url,
            "latency_seconds": round(elapsed, 2)
        }
    except Exception as e:
        logger.error(f"[Server/Chat] Brain planning error: {e}")
        raise HTTPException(status_code=500, detail=f"Brain planning error: {str(e)}")


# ---------------------------------------------------------------------- #
# Interactive JARVIS Web HUD Interface (HTML5/Canvas/Web Speech)        #
# ---------------------------------------------------------------------- #
@app.api_route("/", methods=["GET", "HEAD", "POST", "OPTIONS"], response_class=HTMLResponse)
async def web_hud(request: Request):
    """Serves the complete futuristic JARVIS Web HUD and responds to all monitor probes."""
    if request.method == "HEAD":
        return Response(status_code=200, media_type="text/html")
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Allow": "GET, HEAD, POST, OPTIONS"})
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict) and "message" in body:
                return await chat(ChatRequest(message=body["message"]))
        except Exception:
            pass
        return Response(status_code=200, content="OK")
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JARVIS // 24/7 AI Cloud Assistant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #070b14;
            --bg-card: rgba(13, 20, 36, 0.75);
            --border-glow: #00d2ff;
            --cyan-primary: #00e5ff;
            --cyan-glow: rgba(0, 229, 255, 0.45);
            --amber-thought: #fbbf24;
            --amber-glow: rgba(251, 191, 36, 0.35);
            --text-main: #f1f5f9;
            --text-dim: #94a3b8;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Rajdhani', sans-serif;
            background-image: 
                radial-gradient(circle at 50% 20%, rgba(0, 229, 255, 0.08) 0%, transparent 60%),
                linear-gradient(to bottom, #070b14 0%, #03060c 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Bar */
        header {
            padding: 18px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0, 229, 255, 0.2);
            background: rgba(7, 11, 20, 0.85);
            backdrop-filter: blur(12px);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 24px;
            letter-spacing: 2px;
            color: #ffffff;
            text-shadow: 0 0 12px var(--cyan-glow);
        }

        .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            border: 1px solid #10b981;
            color: #10b981;
            background: rgba(16, 185, 129, 0.1);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px #10b981;
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        /* Main Container */
        main {
            flex: 1;
            max-width: 960px;
            width: 100%;
            margin: 0 auto;
            padding: 24px 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        /* Arc Reactor Core Center */
        .core-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 10px 0;
        }

        #reactorCanvas {
            width: 180px;
            height: 180px;
            filter: drop-shadow(0 0 20px var(--cyan-glow));
        }

        .core-status {
            font-family: 'Orbitron', sans-serif;
            font-size: 14px;
            letter-spacing: 2px;
            color: var(--cyan-primary);
            margin-top: 8px;
            text-shadow: 0 0 10px var(--cyan-glow);
        }

        /* Thought Banner Card */
        .thought-card {
            background: rgba(251, 191, 36, 0.05);
            border: 1px solid rgba(251, 191, 36, 0.35);
            border-left: 4px solid var(--amber-thought);
            border-radius: 8px;
            padding: 14px 18px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: #fde68a;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }

        .thought-icon {
            font-size: 18px;
        }

        /* Chat History Stream */
        .chat-stream {
            flex: 1;
            min-height: 280px;
            max-height: 380px;
            overflow-y: auto;
            background: var(--bg-card);
            border: 1px solid rgba(0, 229, 255, 0.15);
            border-radius: 12px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }

        .chat-msg {
            max-width: 82%;
            padding: 12px 16px;
            border-radius: 10px;
            font-size: 15px;
            line-height: 1.5;
            word-break: break-word;
        }

        .msg-user {
            align-self: flex-end;
            background: linear-gradient(135deg, rgba(2, 132, 199, 0.35), rgba(14, 165, 233, 0.25));
            border: 1px solid rgba(56, 189, 248, 0.4);
            color: #f8fafc;
            border-bottom-right-radius: 2px;
        }

        .msg-jarvis {
            align-self: flex-start;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.6));
            border: 1px solid rgba(0, 229, 255, 0.3);
            color: #e2e8f0;
            border-bottom-left-radius: 2px;
            box-shadow: 0 0 15px rgba(0, 229, 255, 0.08);
        }

        .msg-header {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            color: var(--cyan-primary);
            margin-bottom: 4px;
            text-transform: uppercase;
        }

        /* Control Input Bar */
        .input-bar {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .input-wrap {
            flex: 1;
            position: relative;
        }

        input[type="text"] {
            width: 100%;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(0, 229, 255, 0.35);
            color: #ffffff;
            font-family: 'Rajdhani', sans-serif;
            font-size: 17px;
            font-weight: 600;
            padding: 14px 20px;
            border-radius: 8px;
            outline: none;
            transition: all 0.2s ease;
        }

        input[type="text"]:focus {
            border-color: var(--cyan-primary);
            box-shadow: 0 0 16px var(--cyan-glow);
        }

        button {
            cursor: pointer;
            border: none;
            outline: none;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            border-radius: 8px;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-mic {
            width: 52px;
            height: 52px;
            border-radius: 50%;
            background: rgba(15, 23, 42, 0.9);
            border: 2px solid var(--cyan-primary);
            color: var(--cyan-primary);
            box-shadow: 0 0 14px var(--cyan-glow);
            font-size: 20px;
        }

        .btn-mic.listening {
            background: #ef4444;
            border-color: #ef4444;
            color: #ffffff;
            box-shadow: 0 0 24px rgba(239, 68, 68, 0.8);
            animation: pulse-mic 1s infinite alternate;
        }

        @keyframes pulse-mic {
            from { transform: scale(1); }
            to { transform: scale(1.1); }
        }

        .btn-send {
            padding: 14px 28px;
            font-size: 14px;
            letter-spacing: 1.5px;
            background: linear-gradient(135deg, #0284c7, #00e5ff);
            color: #03060c;
            box-shadow: 0 0 16px var(--cyan-glow);
        }

        .btn-send:hover {
            box-shadow: 0 0 24px var(--cyan-primary);
            transform: translateY(-1px);
        }

        /* Footer System Bar */
        footer {
            padding: 12px 28px;
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: var(--text-dim);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            background: rgba(7, 11, 20, 0.8);
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <h1>J.A.R.V.I.S.</h1>
            <span class="pill"><span class="pulse-dot"></span> 24/7 CLOUD ONLINE</span>
        </div>
        <div style="font-size: 13px; color: #94a3b8;">
            AI BRAIN: <span style="color: var(--cyan-primary); font-weight: 700;">GEMINI 3.5 FLASH-LITE</span>
        </div>
    </header>

    <main>
        <div class="core-section">
            <canvas id="reactorCanvas" width="200" height="200"></canvas>
            <div id="coreStatus" class="core-status">STANDBY // LISTENING READY</div>
        </div>

        <div id="thoughtCard" class="thought-card">
            <span class="thought-icon">🧠</span>
            <span id="thoughtText">Cognitive Inner Thought: System initialized. Standing by for voice or text directives, Sir.</span>
        </div>

        <div id="chatStream" class="chat-stream">
            <div class="chat-msg msg-jarvis">
                <div class="msg-header">JARVIS // System</div>
                Good day, Sir. I am operational 24/7 on the cloud node. How may I be of assistance?
            </div>
        </div>

        <div class="input-bar">
            <button id="btnMic" class="btn-mic" title="Voice Recognition (Click to Speak)">🎤</button>
            <div class="input-wrap">
                <input type="text" id="userInput" placeholder="Ask a question or speak a command..." autocomplete="off">
            </div>
            <button id="btnSend" class="btn-send">TRANSMIT</button>
        </div>
    </main>

    <footer>
        <div>NODE: RENDER CLOUD 24/7 // HOST: PYTHON 3.13 // VOICE: EN-GB-RYANNEURAL</div>
        <div>PRESS 🎤 TO TALK // PRESS ENTER TO TRANSMIT</div>
    </footer>

    <script>
        // --- Arc Reactor Canvas Animation ---
        const canvas = document.getElementById('reactorCanvas');
        const ctx = canvas.getContext('2d');
        let angle = 0;
        let isSpeaking = false;
        let isListening = false;

        function drawReactor() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;

            // Outer pulse ring
            ctx.beginPath();
            ctx.arc(cx, cy, 75, 0, Math.PI * 2);
            ctx.strokeStyle = isListening ? 'rgba(239, 68, 68, 0.6)' : (isSpeaking ? 'rgba(0, 229, 255, 0.8)' : 'rgba(0, 229, 255, 0.25)');
            ctx.lineWidth = 2;
            ctx.stroke();

            // Rotating segmented ring
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(angle);
            for (let i = 0; i < 12; i++) {
                ctx.beginPath();
                ctx.arc(0, 0, 60, (i * Math.PI / 6), (i * Math.PI / 6) + 0.35);
                ctx.strokeStyle = isSpeaking ? '#00e5ff' : '#0284c7';
                ctx.lineWidth = 4;
                ctx.stroke();
            }
            ctx.restore();

            // Inner core glow
            const grad = ctx.createRadialGradient(cx, cy, 5, cx, cy, 38);
            grad.addColorStop(0, '#ffffff');
            grad.addColorStop(0.5, isListening ? 'rgba(239, 68, 68, 0.8)' : 'rgba(0, 229, 255, 0.7)');
            grad.addColorStop(1, 'transparent');

            ctx.beginPath();
            ctx.arc(cx, cy, 38, 0, Math.PI * 2);
            ctx.fillStyle = grad;
            ctx.fill();

            angle += isSpeaking ? 0.04 : 0.015;
            requestAnimationFrame(drawReactor);
        }
        drawReactor();

        // --- Interaction Logic ---
        const userInput = document.getElementById('userInput');
        const btnSend = document.getElementById('btnSend');
        const btnMic = document.getElementById('btnMic');
        const chatStream = document.getElementById('chatStream');
        const thoughtText = document.getElementById('thoughtText');
        const coreStatus = document.getElementById('coreStatus');

        function appendMessage(sender, text) {
            const msg = document.createElement('div');
            msg.className = `chat-msg ${sender === 'user' ? 'msg-user' : 'msg-jarvis'}`;
            msg.innerHTML = `<div class="msg-header">${sender === 'user' ? 'YOU' : 'JARVIS'}</div>${text}`;
            chatStream.appendChild(msg);
            chatStream.scrollTop = chatStream.scrollHeight;
        }

        async function sendCommand(text) {
            if (!text || !text.trim()) return;
            const query = text.trim();
            userInput.value = '';

            appendMessage('user', query);
            coreStatus.innerText = 'THINKING // COGNITIVE REASONING';
            thoughtText.innerText = 'Formulating autonomous strategy and synthesizing response...';

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: query })
                });

                if (!res.ok) throw new Error('API server error');
                const data = await res.json();

                // Update Thought
                if (data.thought) {
                    thoughtText.innerText = data.thought;
                }

                // Append JARVIS response
                const replyText = data.spoken_text || data.explanation;
                appendMessage('jarvis', replyText);

                // Play British Neural Speech Audio
                if (data.audio_url) {
                    playVoiceAudio(data.audio_url);
                } else {
                    coreStatus.innerText = 'STANDBY // READY';
                }

            } catch (err) {
                appendMessage('jarvis', 'I encountered an error connecting to the central neural core, sir.');
                coreStatus.innerText = 'ERROR // RETRY';
            }
        }

        let currentAudio = null;
        function playVoiceAudio(url) {
            if (currentAudio) {
                currentAudio.pause();
            }
            isSpeaking = true;
            coreStatus.innerText = 'SPEAKING // TRANSMITTING AUDIO';
            currentAudio = new Audio(url);
            currentAudio.play();
            currentAudio.onended = () => {
                isSpeaking = false;
                coreStatus.innerText = 'STANDBY // READY';
            };
            currentAudio.onerror = () => {
                isSpeaking = false;
                coreStatus.innerText = 'STANDBY // READY';
            };
        }

        btnSend.addEventListener('click', () => sendCommand(userInput.value));
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendCommand(userInput.value);
        });

        // --- Web Speech API (Microphone Recognition) ---
        let recognition = null;
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRec();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                isListening = true;
                btnMic.classList.add('listening');
                coreStatus.innerText = 'LISTENING // AUDIO INPUT ACTIVE';
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                sendCommand(transcript);
            };

            recognition.onerror = () => {
                isListening = false;
                btnMic.classList.remove('listening');
                coreStatus.innerText = 'STANDBY // READY';
            };

            recognition.onend = () => {
                isListening = false;
                btnMic.classList.remove('listening');
                if (!isSpeaking) {
                    coreStatus.innerText = 'STANDBY // READY';
                }
            };

            btnMic.addEventListener('click', () => {
                if (isListening) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            });
        } else {
            btnMic.title = 'SpeechRecognition not supported in this browser. Use text input.';
            btnMic.style.opacity = '0.5';
        }
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting JARVIS server on port {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
