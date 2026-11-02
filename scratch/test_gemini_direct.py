import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from google import genai
from google.genai import types
from config.settings import config

client = genai.Client(api_key=config.gemini_api_key)
t0 = time.time()
print(f"Calling model {config.gemini_model} with thinking_budget=0...")
resp = client.models.generate_content(
    model=config.gemini_model,
    contents="Convert command to JSON action array. Command: 'open chrome'. Format: [{\"action\": \"open_app\", \"target\": \"chrome\"}]",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.1
    )
)
print(f"Completed in {time.time()-t0:.2f}s:")
print(resp.text)
