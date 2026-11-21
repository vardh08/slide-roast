"""Check the user's rate-limit message without using API quota."""
import groq
import httpx
import pytest

from services import groq_service
from services.schemas import JudgeResult


def test_groq_rate_limit_message(monkeypatch):
    requests = []
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"))

    def rate_limit(*args, **kwargs):
        requests.append((args, kwargs))
        raise groq.RateLimitError("internal test message", response=response, body=None)

    monkeypatch.setattr(groq_service, "_call_model", rate_limit)
    with pytest.raises(groq_service.GroqError, match="^Rate limit reached. Wait a minute and try again\\.$"):
        groq_service.generate_structured("Judge", "Test deck", JudgeResult)
    assert len(requests) == 1
