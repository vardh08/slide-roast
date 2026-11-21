"""Exercise the Groq adapter without sending any data to a live API."""
import json

import groq
import httpx
import pytest
import streamlit as st

from services import groq_service
from services.groq_service import GroqError
from services.schemas import JudgeResult
from tests.fakes import fake_judge_json
from utils.helpers import get_api_key


@pytest.fixture(autouse=True)
def fresh_model(monkeypatch):
    from threading import Event

    monkeypatch.setattr(groq_service, "_model_retired", Event())


def status_error(status, code=None):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    body = {"error": {"code": code}} if code else None
    return groq.APIStatusError("test provider message", response=httpx.Response(status, request=request), body=body)


def test_sdk_sends_original_prompts_and_json_schema_in_one_text_request(monkeypatch):
    requests = []
    settings = []
    original_client = groq.Groq

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"index": 0, "message": {"role": "assistant", "content": fake_judge_json("investor")}}],
        })

    def client_factory(**kwargs):
        settings.append(kwargs)
        return original_client(http_client=httpx.Client(transport=httpx.MockTransport(respond)), **kwargs)

    monkeypatch.setattr(groq, "Groq", client_factory)
    monkeypatch.setattr(groq_service, "get_api_key", lambda: "mock-key")
    slides = [{"slide_number": n, "text": word, "has_text": True} for n, word in enumerate(("First", "Second"), 1)]
    result = groq_service.run_judge("investor", "Project", "", "Investors", slides)

    assert result["judge"] == "investor"
    assert settings == [{"api_key": "mock-key", "timeout": 30, "max_retries": 0}]
    assert len(requests) == 1
    request = requests[0]
    assert request["model"] == groq_service.MODEL
    assert request["response_format"] == {"type": "json_object"}
    user_message = request["messages"][1]["content"]
    assert all(word in user_message for word in ("First", "Second", "JSON", "JudgeResult"))


def test_timeout_and_invalid_json_share_the_two_retry_budget(monkeypatch):
    attempts, waits = [], []

    def fail(*args):
        attempts.append(args)
        if len(attempts) == 1:
            raise groq.APITimeoutError(request=httpx.Request("POST", "https://api.groq.com"))
        return "{}"

    monkeypatch.setattr(groq_service, "_call_model", fail)
    monkeypatch.setattr(groq_service, "_sleep", waits.append)
    with pytest.raises(GroqError, match="expected format"):
        groq_service.generate_structured("Judge", "Slides", JudgeResult)
    assert len(attempts) == 3 and waits == [1, 2]
    assert "corrected JSON" in attempts[-1][1]


def test_retired_model_switches_to_replacement_and_reuses_it(monkeypatch):
    calls = []

    def respond(*args, model_name=None):
        calls.append(model_name)
        if not model_name:
            raise status_error(400, "model_decommissioned")
        return fake_judge_json("investor")

    monkeypatch.setattr(groq_service, "_call_model", respond)
    for _ in range(2):
        result = groq_service.generate_structured("Judge", "Deck", JudgeResult)
        assert result.category_scores.clarity >= 0
    assert calls == [None, groq_service.REPLACEMENT_MODEL, groq_service.REPLACEMENT_MODEL]


def test_missing_key_fails_before_client_creation(monkeypatch):
    monkeypatch.setattr(groq_service, "get_api_key", lambda: None)
    with pytest.raises(GroqError, match="GROQ_API_KEY"):
        groq_service.generate_structured("Judge", "Deck", JudgeResult)


def test_key_uses_environment_then_streamlit_secrets(monkeypatch):
    monkeypatch.setattr(st, "secrets", {"GROQ_API_KEY": "mock-hosted-key"})
    monkeypatch.setenv("GROQ_API_KEY", " mock-local-key ")
    assert get_api_key() == "mock-local-key"
    monkeypatch.delenv("GROQ_API_KEY")
    assert get_api_key() == "mock-hosted-key"


def test_unknown_model_is_actionable(monkeypatch):
    def fail(*args):
        raise status_error(404)

    monkeypatch.setattr(groq_service, "_call_model", fail)
    with pytest.raises(GroqError, match="Check MODEL"):
        groq_service.generate_structured("Judge", "Deck", JudgeResult)


@pytest.mark.parametrize("status,expected", [
    (400, "bad_request"), (408, "server"), (409, "server"),
    (422, "bad_request"), (500, "server"), (503, "server"),
])
def test_status_errors_stop_at_the_shared_attempt_limit(monkeypatch, status, expected):
    calls = []

    def fail(*args):
        calls.append(args)
        raise status_error(status)

    monkeypatch.setattr(groq_service, "_call_model", fail)
    with pytest.raises(GroqError) as exc:
        groq_service.generate_structured("Judge", "Deck", JudgeResult)
    assert exc.value.kind == expected
    assert len(calls) == (3 if expected == "server" else 1)


@pytest.mark.parametrize("error_type,status", [
    (groq.AuthenticationError, 401), (groq.PermissionDeniedError, 403),
])
def test_credential_errors_do_not_retry_or_disclose_provider_details(monkeypatch, error_type, status):
    calls = []

    def fail(*args):
        calls.append(args)
        response = status_error(status).response
        raise error_type("sensitive provider response", response=response, body=None)

    monkeypatch.setattr(groq_service, "_call_model", fail)
    with pytest.raises(GroqError, match="GROQ_API_KEY") as exc:
        groq_service.generate_structured("Judge", "Deck", JudgeResult)
    assert exc.value.kind == "invalid_key"
    assert "sensitive" not in exc.value.user_message and len(calls) == 1


def test_judge_rejects_invalid_scores_and_filters_invalid_slide_numbers(monkeypatch):
    slides = [{"slide_number": 2, "text": "Only visible slide", "has_text": True}]
    invalid = json.loads(fake_judge_json("investor"))
    invalid["overall_score"] = 101
    valid = json.loads(fake_judge_json("investor"))
    valid["weaknesses"].append({**valid["weaknesses"][0], "slide_number": 99})
    responses = iter([json.dumps(invalid), json.dumps(valid)])
    monkeypatch.setattr(groq_service, "_call_model", lambda *args: next(responses))
    review = groq_service.run_judge("investor", "Project", "", "Investors", slides)
    assert review["overall_score"] <= 100
    assert all(issue["slide_number"] == 2 for issue in review["weaknesses"])
