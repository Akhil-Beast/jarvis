import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from config.settings import config
from google import genai
from google.genai import types

client = genai.Client(api_key=config.gemini_api_key)
t0 = time.time()
print("Testing thinking_level='low'...")
resp = client.models.generate_content(
    model=config.gemini_model,
    contents="Convert command to JSON action array. Command: 'open chrome'. Format: [{\"action\": \"open_app\", \"target\": \"chrome\"}]",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="low"),
        temperature=0.0
    )
)
print(f"Done in {time.time()-t0:.2f}s!")
print("Response:", resp.text)
