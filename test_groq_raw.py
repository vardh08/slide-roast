"""Opt-in live Groq smoke test. Sends a short synthetic prompt."""
from pydantic import BaseModel

from services.groq_service import GroqError, generate_structured


class Message(BaseModel):
    greeting: str


if __name__ == "__main__":
    try:
        result = generate_structured("You return JSON.", "Return a one-word greeting.", Message)
    except GroqError as exc:
        raise SystemExit(exc.user_message) from None
    print(result.greeting)
