"""Upload page: what happens when the user presses Start Roasting."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from services import gemini_service, report_service
from tests.fakes import make_fake_call_model

ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")  # run from the main app so st.switch_page works like in the real app


def prepare_upload():
    at = AppTest.from_file(APP, default_timeout=60)
    at.switch_page("pages/1_Upload.py")
    at.run()
    at.file_uploader[0].set_value(("deck.pdf", (ROOT / "assets/sample_deck_v1.pdf").read_bytes(), "application/pdf"))
    at.text_input[0].set_value("Campus Barter")
    return at.run()


def start_button(at):
    return next(button for button in at.button if button.label == "Roast My Deck ↗")


def start(monkeypatch, key, judge="customer"):
    monkeypatch.setattr(report_service, "get_api_key", lambda: key)
    at = prepare_upload()
    at.radio(key="judge_personality").set_value(judge).run()
    return start_button(at).click().run()


def test_valid_upload_waits_for_personality():
    at = prepare_upload()
    assert at.radio(key="judge_personality").value is None
    assert start_button(at).proto.disabled


def test_upload_requires_project_name_before_submission():
    at = prepare_upload()
    at.radio(key="judge_personality").set_value("professor")
    at.text_input[0].set_value("   ").run()
    assert start_button(at).proto.disabled
    assert any("Please enter a project name" in tip.value for tip in at.caption)

    at.text_input[0].set_value("Campus Barter").run()
    assert not start_button(at).proto.disabled


def test_start_without_key_shows_friendly_error(monkeypatch):
    at = start(monkeypatch, None)
    assert not at.exception
    assert any("No Gemini API key" in e.value for e in at.error)


def test_start_uses_only_selected_judge_and_generates_ai_review(monkeypatch):
    fake_model = make_fake_call_model()
    calls = []

    def track_calls(system_prompt, user_prompt, schema):
        calls.append(schema["title"])
        return fake_model(system_prompt, user_prompt, schema)

    monkeypatch.setattr(gemini_service, "_call_model", track_calls)
    at = start(monkeypatch, "test-key")
    assert not at.exception
    report = at.session_state["report"]
    assert calls == ["JudgeResult", "SummaryResult"]
    assert report["status"] == "complete" and list(report["judges"]) == ["customer"]
    assert report["scoring"]["overall_score"] == 74.0 and not report["scoring"]["partial"]
    assert report["summary"] and report["top_improvements"]

    at.switch_page("pages/4_Roast_Report.py").run()
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "Confused Customer" in html and "AI Review" in html
    assert "Skeptical Investor" not in html and "Bored Professor" not in html


def test_start_when_selected_judge_fails_shows_error(monkeypatch):
    monkeypatch.setattr(gemini_service, "_call_model", make_fake_call_model(fail_judges=("customer",)))
    at = start(monkeypatch, "test-key")
    assert not at.exception
    assert len(at.error) == 1 and "Confused Customer" in at.error[0].value
    assert "report" not in at.session_state


def test_sticky_nav_does_not_wrap_the_hero():
    at = AppTest.from_file(APP).run()
    blocks = [node.proto.body for node in at.get("html")]
    nav = next(block for block in blocks if 'id="landing-nav"' in block)
    hero = next(block for block in blocks if '<section class="hero"' in block)
    assert nav != hero


@pytest.mark.parametrize("judge", ["investor", "professor", "customer"])
def test_landing_upload_can_reopen_report_from_history(monkeypatch, judge):
    monkeypatch.setattr(report_service, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(gemini_service, "_call_model", make_fake_call_model())
    at = AppTest.from_file(APP).run()
    assert any("tough love." in str(node.proto) for node in at.get("html"))
    at.file_uploader[0].set_value(("deck.pdf", (ROOT / "assets/sample_deck_v1.pdf").read_bytes(), "application/pdf"))
    at.text_input[0].set_value("Campus Barter")
    at.radio(key="judge_personality").set_value(judge)
    at.run()
    start_button(at).click().run()
    assert not at.exception
    assert list(at.session_state["report"]["judges"]) == [judge]

    at.switch_page("pages/2_Report_History.py").run()
    assert not at.exception and len(at.session_state["report_history"]) == 1
    at.button(key="view_past_roast_0").click().run()
    at.switch_page("pages/4_Roast_Report.py").run()
    assert not at.exception and at.selectbox(key="fixer_slide_number")
