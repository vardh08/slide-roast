import os, time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
model = os.getenv("GEMINI_MODEL", "(not set)")
print("Model from .env:", model, flush=True)

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
    http_options=types.HttpOptions(timeout=30_000),
)

for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
    try:
        r = client.models.generate_content(model=m, contents="Say hi in 3 words")
        print(m, "-> OK:", r.text.strip(), flush=True)
    except Exception as e:
        print(m, "-> ERROR:", str(e)[:700], flush=True)
    time.sleep(3)