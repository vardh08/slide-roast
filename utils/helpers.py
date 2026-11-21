"""Small helper functions used across the app."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")  # reads .env if it exists; silently skips otherwise

MAX_FILE_MB = 10
MAX_PAGES = 15
AUDIENCES = [
    "Hackathon Judges",
    "Startup Investors",
    "University Professors",
    "Recruiters",
    "General Audience",
]
DEFAULT_MODEL = "gemini-3.8-flash"


def get_api_key() -> str | None:
    """Look for the Gemini key in environment variables first, then Streamlit secrets.

    The key is never printed or shown in the UI.
    """
    key = os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key.strip() != "your_api_key_here":
        return key.strip()
    try:
        import streamlit as st

        secret = st.secrets.get("GEMINI_API_KEY")
        if secret:
            return str(secret).strip()
    except Exception:
        pass
    return None


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def human_size(num_bytes: int) -> str:
    """12345678 -> '11.8 MB'."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def esc(value) -> str:
    """HTML-escape any text before putting it inside an HTML card (AI output is never trusted as HTML)."""
    import html

    return html.escape("" if value is None else str(value))
