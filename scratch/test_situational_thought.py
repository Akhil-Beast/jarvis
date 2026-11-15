import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import config
from google import genai
from google.genai import types

client = genai.Client(api_key=config.gemini_api_key)

system_instruction = """You are J.A.R.V.I.S., the autonomous AI personal assistant for Sir (Akhil).
You think by yourself, understand the live PC environment, and make intelligent decisions.

Environment Context:
- Active Foreground Window: CrossDevice (realme P2 Pro 5G)
- Open Windows: ["CrossDevice - realme P2 Pro 5G", "Google Chrome", "SOLIDWORKS 2024"]
- Known APK on Phone: BankAnalyzer.apk (Bank Statement Analyzer v1.2)

Available Actions:
- {"action": "open_app", "target": "app_name"}
- {"action": "focus_window", "target": "window_name"}
- {"action": "close_window", "target": "window_name"}
- {"action": "type_text", "text": "text", "enter": true/false}
- {"action": "hotkey", "keys": ["ctrl", "c"]}
- {"action": "press_key", "key": "enter"}
- {"action": "scroll", "clicks": -300}
- {"action": "system", "command": "volume|screenshot|lock", "direction": "up|down"}
- {"action": "vision_inspect", "prompt": "what to look for on screen"}
- {"action": "click_screen_target", "target": "icon_or_element_name", "click_type": "single|double|right"}
- {"action": "apk_action", "command": "find|inspect|install|open", "target": "apk_name"}

Output format:
Output ONLY a JSON object:
{
  "thought": "Your internal analytical thinking and decision-making",
  "speak": "What you say aloud to Sir (2-3 sentences max, witty polite British cadence, no markdown)",
  "steps": [array of action objects]
}"""

q = "Jarvis, what should we do next?"
resp = client.models.generate_content(
    model=config.gemini_model,
    contents=f"User: {q}",
    config=types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.4,
        max_output_tokens=300
    )
)
print("QUERY:", q)
print(resp.text.strip())
