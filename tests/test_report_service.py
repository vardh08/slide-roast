import json
from pathlib import Path

import pytest

from services import groq_service, report_service
from services.groq_service import GroqError
from services.pdf_service import extract_slides
from tests.fakes import make_fake_call_model

DECK = Path(__file__).resolve().parent.parent / "assets" / "sample_deck_v1.pdf"


@pytest.fixture
def extraction():
    return extract_slides(DECK.read_bytes())


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setattr(report_service, "get_api_key", lambda: "test-key")


def run(monkeypatch, extraction, **kw):
    monkeypatch.setattr(groq_service, "_call_model", make_fake_call_model(**kw))
    msgs = []
    r = report_service.run_analysis("Campus Barter", "", "Hackathon Judges", "deck.pdf", extraction, progress=msgs.append)
    return r, msgs


def test_full_report(monkeypatch, extraction):
    r, msgs = run(monkeypatch, extraction)
    assert r["status"] == "complete" and not r["judge_errors"]
    # weights 100% on all categories -> overall = mean of judge scores (50+62+74)/3 = 62
    assert r["scoring"]["overall_score"] == 62.0
    assert r["scoring"]["interpretation"] == "Developing"
    assert len(r["slide_feedback"]) == 7
    assert [s["slide_number"] for s in r["slide_feedback"]] == list(range(1, 8))
    assert len(r["top_improvements"]) == 2  # slide 99 was dropped as invalid
    assert r["visual_analysis"] == "unavailable"
    assert any("finished" in m for m in msgs)
    json.dumps(r)  # must be JSON friendly for the database


def test_slide_feedback_comes_from_judges(monkeypatch, extraction):
    r, _ = run(monkeypatch, extraction)
    s2 = r["slide_feedback"][1]
    assert s2["severity"] == "high" and len(s2["weaknesses"]) == 3  # one per judge
    assert r["slide_feedback"][0]["severity"] == "none"


def test_one_judge_fails_marks_incomplete(monkeypatch, extraction):
    r, _ = run(monkeypatch, extraction, fail_judges=("professor",))
    assert r["status"] == "incomplete"
    assert r["judges"]["professor"] is None and "professor" in r["judge_errors"]
    assert r["scoring"]["overall_score"] == 62.0  # mean of 50 and 74, professor NOT counted as 0
    assert r["scoring"]["partial"]


def test_all_judges_fail(monkeypatch, extraction):
    r, _ = run(monkeypatch, extraction, fail_judges=("investor", "professor", "customer"))
    assert r["status"] == "failed" and r["scoring"] is None and r["slide_feedback"] == []


def test_summary_failure_falls_back_to_real_judge_data(monkeypatch, extraction):
    r, _ = run(monkeypatch, extraction, fail_summary=True)
    assert r["status"] == "complete" and r["summary"] is None and r["summary_error"]
    assert r["top_improvements"] and r["top_improvements"][0]["severity"] == "high"
    assert r["slide_feedback"][1]["weaknesses"]  # still populated


def test_missing_key_raises(monkeypatch, extraction):
    monkeypatch.setattr(report_service, "get_api_key", lambda: None)
    with pytest.raises(GroqError) as e:
        report_service.run_analysis("P", "", "Hackathon Judges", "d.pdf", extraction)
    assert e.value.kind == "missing_key"
