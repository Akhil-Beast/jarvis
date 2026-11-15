# 🚀 Deploying JARVIS 24/7 on Render

This guide provides instructions to deploy your JARVIS AI Assistant to **Render.com** as a **24/7 cloud service** accessible from any web browser, phone, or computer in the world.

---

## ⚡ Option 1: 1-Click Blueprint Deploy (Recommended)

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top right and select **Blueprint**.
3. Connect your GitHub repository (`Akhil-Beast/jarvis`).
4. Render will automatically read [`render.yaml`](./render.yaml).
5. When prompted for environment variables:
   - **`GEMINI_API_KEY`**: Paste your Google Gemini API key.
6. Click **Apply**. Render will automatically build and deploy JARVIS!

---

## 🛠️ Option 2: Manual Web Service Deploy

If you prefer to configure manually:
1. In the Render Dashboard, click **New +** -> **Web Service**.
2. Select your repository: `Akhil-Beast/jarvis`.
3. Configure the following fields:
   - **Name**: `jarvis-ai` (or your preferred name)
   - **Region**: Oregon (or nearest to you)
   - **Branch**: `master`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Under **Environment Variables**, add:
   - `GEMINI_API_KEY` = `your_gemini_api_key_here`
   - `GEMINI_MODEL` = `gemini-3.5-flash-lite`
   - `TTS_ENGINE` = `edge_tts`
   - `EDGE_TTS_VOICE` = `en-GB-RyanNeural`
   - `PYTHON_VERSION` = `3.11.9`
5. Under **Health Check Path**, enter: `/health`
6. Click **Deploy Web Service**.

---

## 🌐 Accessing Your 24/7 JARVIS

Once deployed, Render provides a public HTTPS URL (e.g., `https://jarvis-ai.onrender.com`):

- **Interactive Web HUD**: Open `https://your-service.onrender.com` in Chrome, Safari, or Edge on your phone or desktop:
  - Click the **🎤 microphone button** to speak commands directly.
  - Listen to real-time **British JARVIS neural voice** answers.
  - Watch the live **Inner Cognitive Thought banner** formulate reasoning.
- **REST API Endpoint**:
  ```bash
  curl -X POST "https://your-service.onrender.com/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "What is our current status?"}'
  ```
- **Health Check & Ping**:
  ```bash
  curl "https://your-service.onrender.com/health"
  ```

---

## ⏰ How the 24/7 Uptime Keep-Alive Works

Render's free tier ordinarily spins down web services after 15 minutes of inactivity.
JARVIS includes a **built-in background keepalive task** in [`server.py`](./server.py):
- When deployed on Render, Render automatically injects `RENDER_EXTERNAL_URL`.
- JARVIS's keep-alive worker wakes up every 10 minutes and sends a lightweight heartbeat ping to its own `/health` endpoint.
- This keeps your instance **active and awake 24/7** without entering idle sleep!

*(Optional: You can also register your `/health` URL with free uptime monitors like [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org) as an external heartbeat).*
