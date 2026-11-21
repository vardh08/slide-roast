"""Renders the dashboard page headlessly with a report produced by the mocked pipeline."""
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from services import groq_service, report_service
from services.groq_service import GroqError
from services.pdf_service import extract_slides
from tests.fakes import make_fake_call_model

ROOT = Path(__file__).resolve().parent.parent
PAGE = str(ROOT / "pages" / "4_Roast_Report.py")


def build_report(monkeypatch, **kw):
    monkeypatch.setattr(report_service, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(groq_service, "_call_model", make_fake_call_model(**kw))
    extraction = extract_slides((ROOT / "assets" / "sample_deck_v1.pdf").read_bytes())
    return report_service.run_analysis("Campus Barter", "", "Hackathon Judges", "deck.pdf", extraction)


def render(report):
    at = AppTest.from_file(PAGE, default_timeout=60)
    if report is not None:
        at.session_state["report"] = report
    return at.run()


def all_html(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_empty_state():
    at = render(None)
    assert not at.exception
    assert any("No report yet" in i.value for i in at.info)


def test_complete_report_renders(monkeypatch):
    at = render(build_report(monkeypatch))
    assert not at.exception
    html = all_html(at)
    for text in ("Skeptical Investor", "Bored Professor", "Confused Customer", "Overall score",
                 "Top 3 improvements", "Slide-by-slide feedback", "Questions You Better Be Ready For", "Who pays?"):
        assert text in html, text
    assert ">62<" in html  # the ring shows the backend-calculated score
    assert not at.warning  # complete report -> no incomplete banner
    calculation = " ".join(node.proto.body for node in at.get("html"))
    assert "15.5 points toward the total" in calculation
    assert "62 / 100" in calculation
    assert "Worked example" in html and "Rounding" in html and "Needs major improvement" in calculation
    labels = [item.label for item in at.expander]
    assert any("How We Calculate Your Score" in label for label in labels)
    assert any("Full Judge Report" in label for label in labels)
    assert any("Slide 01" in label for label in labels)
    assert "## Category scores" not in html
    assert any(":red-background[**High priority**]" in label for label in labels)
    assert any(":yellow-background[**Medium priority**]" in label for label in labels)
    assert "slide-feedback-issue" in html
    assert "1 high-priority slide" in html


def test_incomplete_report_is_flagged(monkeypatch):
    at = render(build_report(monkeypatch, fail_judges=("customer",)))
    assert not at.exception
    assert any("Incomplete report" in w.value for w in at.warning)
    assert "did not complete" in all_html(at)


def test_summary_missing_is_handled(monkeypatch):
    at = render(build_report(monkeypatch, fail_summary=True))
    assert not at.exception
    assert any("AI summary is unavailable" in i.value for i in at.info)


def test_ai_text_is_html_escaped(monkeypatch):
    report = build_report(monkeypatch)
    report["judges"]["investor"]["verdict"] = "<script>alert('x')</script>"
    report["judges"]["investor"]["weaknesses"][0]["issue"] = "<img src=x onerror=alert(1)>"
    at = render(report)
    assert not at.exception
    html = all_html(at)
    assert "<script>alert" not in html and "<img src=x" not in html
    assert "&lt;script&gt;" in html


def test_empty_fields_do_not_crash(monkeypatch):
    report = build_report(monkeypatch)
    j = report["judges"]["professor"]
    j["strengths"], j["weaknesses"], j["judge_questions"], j["top_improvements"] = [], [], [], []
    report["top_improvements"] = []
    assert not render(report).exception


def test_slide_fixer_uses_selected_text_and_keeps_rewrite_across_reruns(monkeypatch):
    report = build_report(monkeypatch)
    report["slides"][0] = {"slide_number": 1, "text": "", "has_text": False}
    requests = []

    def fake_fix(system_prompt, user_prompt, schema):
        assert schema["title"] == "SlideFix"
        requests.append(json.loads(user_prompt))
        return json.dumps({
            "title": "A campus exchange in one place",
            "body": "Find and trade items with other students.",
            "changes": ["Put the main benefit in the title."],
            "evidence_to_add": ["Add a verified example of an exchange."],
        })

    monkeypatch.setattr(groq_service, "_call_model", fake_fix)
    at = render(report)
    assert at.selectbox(key="fixer_slide_number").value is None
    at.selectbox(key="fixer_slide_number").set_value(1).run()
    assert any("No readable text" in hint.value for hint in at.info)
    at.selectbox(key="fixer_slide_number").set_value(2).run()
    assert not requests
    at.button(key="generate_slide_fix").click().run()
    assert not at.exception
    assert requests[0]["slide_number"] == 2
    assert requests[0]["original_slide_text"] == report["slides"][1]["text"]
    assert {idea["issue"] for idea in requests[0]["feedback"]} >= {"investor issue"}
    assert any("A campus exchange in one place" in block.value for block in at.text_area)
    assert any("verified example" in block.value for block in at.text)
    assert any("slide-download-text" in node.proto.body for node in at.get("html"))

    at.text_area[0].set_value("Edited copy").run()
    assert at.button(key="generate_slide_fix").proto.disabled
    at.radio(key="rewrite_style").set_value("Concise").run()
    assert at.text_area[0].value == "Edited copy"
    at.selectbox(key="fixer_slide_number").set_value(3).run()
    assert not any("slide-download-text" in node.proto.body for node in at.get("html"))
    at.selectbox(key="fixer_slide_number").set_value(2).run()
    assert len(requests) == 1 and any("slide-download-text" in node.proto.body for node in at.get("html"))
    assert at.text_area[0].value == "Edited copy"
    at.checkbox[0].check().run()
    at.button(key="generate_slide_fix").click().run()
    assert len(requests) == 2 and requests[-1]["rewrite_style"].startswith("Concise:")


def test_rewrite_rejects_changed_number_or_unit(monkeypatch):
    report = build_report(monkeypatch)
    report["slides"][1]["text"] = "Latency improved to 30 ms."
    monkeypatch.setattr(groq_service, "_call_model", lambda *_: json.dumps({
        "title": "Latency", "body": "Improved to 30 kg.", "changes": [], "evidence_to_add": [],
    }))
    try:
        groq_service.generate_slide_fix(report, 2, style="Persuasive", judge_key="professor")
    except GroqError as error:
        assert error.kind == "changed_numbers"
    else:
        raise AssertionError("Changed unit accepted")


def test_slide_fixer_failure_keeps_report_available(monkeypatch):
    report = build_report(monkeypatch)

    def fail_fix(*args):
        raise GroqError("quota", "Groq quota reached.")

    monkeypatch.setattr(groq_service, "_call_model", fail_fix)
    at = render(report)
    at.selectbox(key="fixer_slide_number").set_value(2).run()
    at.button(key="generate_slide_fix").click().run()
    assert not at.exception
    assert at.error[0].value == "Groq quota reached."
    assert "AI Review" in all_html(at) and not any("slide-download-text" in node.proto.body for node in at.get("html"))

