import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from config.settings import config
from google import genai

client = genai.Client(api_key=config.gemini_api_key)

models = ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-3.1-flash-lite', 'gemini-3.5-flash-lite', 'gemini-3.8-flash']
for m in models:
    t0 = time.time()
    try:
        r = client.models.generate_content(model=m, contents='Say hi in 3 words')
        elapsed = time.time() - t0
        print(f"{m}: {elapsed:.2f}s -> {r.text.strip()[:60]}")
    except Exception as e:
        print(f"{m}: ERROR -> {e}")
