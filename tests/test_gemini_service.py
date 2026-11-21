import json

import pytest
from google.genai import errors as genai_errors

from services import gemini_service
from services.gemini_service import GeminiError, run_judge
from services.schemas import JudgeResult
from tests.fakes import fake_judge_json, make_fake_call_model

SLIDES = [{"slide_number": n, "text": f"Slide {n} text is long enough", "has_text": True} for n in range(1, 8)]


def call(monkeypatch, fake, key="investor"):
    monkeypatch.setattr(gemini_service, "_call_model", fake)
    return run_judge(key, "Proj", "", "Hackathon Judges", SLIDES)


def test_judge_ok_and_label_overwritten(monkeypatch):
    r = call(monkeypatch, make_fake_call_model())
    assert r["judge"] == "investor"  # model said WRONG-LABEL
    assert r["overall_score"] == 50


def test_three_judges_are_different(monkeypatch):
    monkeypatch.setattr(gemini_service, "_call_model", make_fake_call_model())
    scores = {k: run_judge(k, "P", "", "A", SLIDES)["overall_score"] for k in ("investor", "professor", "customer")}
    assert len(set(scores.values())) == 3


def test_each_judge_has_own_system_prompt():
    from prompts.judges import JUDGES

    prompts = [j["system_prompt"] for j in JUDGES.values()]
    assert len(set(prompts)) == 3
    assert "I'm not here to appreciate your idea" in JUDGES["investor"]["system_prompt"]
    assert "hundreds of presentations" in JUDGES["professor"]["system_prompt"]
    assert "I don't care how complicated" in JUDGES["customer"]["system_prompt"]


def test_nonexistent_slide_dropped(monkeypatch):
    def fake(s, u, schema):
        return fake_judge_json("investor", bad_slide=42)

    r = call(monkeypatch, fake)
    assert r["dropped_weaknesses"] == 1
    assert all(w["slide_number"] <= 7 for w in r["weaknesses"])


def test_invalid_json_retried_once_then_ok(monkeypatch):
    calls = []

    def fake(s, u, schema):
        calls.append(u)
        return "not json at all" if len(calls) == 1 else fake_judge_json("investor")

    r = call(monkeypatch, fake)
    assert r["overall_score"] == 60
    assert len(calls) == 2 and "rejected" in calls[1]


def test_invalid_json_twice_fails(monkeypatch):
    with pytest.raises(GeminiError) as e:
        call(monkeypatch, lambda s, u, schema: "{bad")
    assert e.value.kind == "invalid_response"


def test_score_out_of_range_rejected(monkeypatch):
    bad = json.loads(fake_judge_json("investor"))
    bad["overall_score"] = 150
    with pytest.raises(GeminiError) as e:
        call(monkeypatch, lambda s, u, schema: json.dumps(bad))
    assert e.value.kind == "invalid_response"


def test_missing_field_rejected(monkeypatch):
    bad = json.loads(fake_judge_json("investor"))
    del bad["verdict"]
    with pytest.raises(GeminiError):
        call(monkeypatch, lambda s, u, schema: json.dumps(bad))


def test_empty_response_handled(monkeypatch):
    with pytest.raises(GeminiError):
        call(monkeypatch, lambda s, u, schema: "")


class ReadTimeout(Exception):  # stands in for the HTTP library's timeout error
    pass


class ConnectError(Exception):  # stands in for the HTTP library's connection error
    pass


def api_error(code, msg="x"):
    cls = genai_errors.ClientError if code < 500 else genai_errors.ServerError
    return cls(code, {"error": {"message": msg, "status": "X"}})


@pytest.mark.parametrize(
    "exc,kind",
    [
        (api_error(401, "bad"), "invalid_key"),
        (api_error(400, "API key not valid. Please pass a valid API key."), "invalid_key"),
        (api_error(404, "model missing"), "model_not_found"),
        (api_error(429, "quota"), "quota"),
        (api_error(503, "overloaded"), "server"),
        (api_error(400, "something else"), "bad_request"),
        (ReadTimeout("t"), "timeout"),
        (ConnectError("c"), "network"),
        (TimeoutError("t"), "timeout"),
        (ConnectionError("c"), "network"),
    ],
)
def test_error_kinds(monkeypatch, exc, kind):
    def fake(s, u, schema, *, model_name=None):
        raise exc

    with pytest.raises(GeminiError) as e:
        call(monkeypatch, fake)
    assert e.value.kind == kind
    assert "Traceback" not in e.value.user_message


def test_transient_error_retried_then_succeeds(monkeypatch):
    n = {"c": 0}

    def fake(s, u, schema):
        n["c"] += 1
        if n["c"] < 3:
            raise api_error(503)
        return fake_judge_json("investor")

    assert call(monkeypatch, fake)["overall_score"] == 60
    assert n["c"] == 3


def test_transient_error_gives_up(monkeypatch):
    n = {"c": 0}
    delays = []
    monkeypatch.setattr(gemini_service, "_sleep", delays.append)

    def fake(s, u, schema, *, model_name=None):
        n["c"] += 1
        raise api_error(503)

    with pytest.raises(GeminiError):
        call(monkeypatch, fake)
    assert n["c"] == 5
    assert delays == [5, 15, 30]


def test_overloaded_primary_can_use_fallback(monkeypatch):
    monkeypatch.setattr(gemini_service, "get_model_name", lambda: "gemini-3.5-flash-lite")

    def fake(s, u, schema, *, model_name=None):
        if model_name is None:
            raise api_error(503)
        assert model_name == "gemini-3.8-flash"
        return fake_judge_json("investor")

    assert call(monkeypatch, fake)["overall_score"] == 60


def test_invalid_key_not_retried(monkeypatch):
    n = {"c": 0}

    def fake(s, u, schema):
        n["c"] += 1
        raise api_error(401)

    with pytest.raises(GeminiError):
        call(monkeypatch, fake)
    assert n["c"] == 1


def test_missing_api_key(monkeypatch):
    monkeypatch.setattr(gemini_service, "get_api_key", lambda: None)
    with pytest.raises(GeminiError) as e:
        gemini_service._call_model("s", "u", {})
    assert e.value.kind == "missing_key"


def test_schema_is_json_serialisable():
    json.dumps(JudgeResult.model_json_schema())
