import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
print("Key loaded:", bool(key), flush=True)

client = genai.Client(
    api_key=key,
    http_options=types.HttpOptions(timeout=30_000),  # 30 seconds
)

for model in ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro-preview"]:
    print("Trying", model, "...", flush=True)
    try:
        r = client.models.generate_content(model=model, contents="Say hi in 3 words")
        print(model, "-> OK:", r.text.strip(), flush=True)
    except Exception as e:
        print(model, "-> ERROR:", type(e).__name__, "|", str(e)[:300], flush=True)