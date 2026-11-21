"""Report pipeline: runs the whole analysis and returns ONE plain dict (the "report").

    extraction (from pdf_service) --> selected judges --> scoring --> AI review --> report dict

The report dict is JSON-friendly so Phase 5 can save it straight into SQLite.

Honesty rules
    * If a judge fails, its entry is None and the report is marked "incomplete". No fake scores.
    * If the summary step fails, we say so and build the slide feedback only from the judges' real criticism.
    * Visual analysis is not implemented, so the report says "unavailable".
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from prompts.judges import JUDGES
from services import groq_service, scoring_service
from services.groq_service import GroqError
from utils.helpers import get_api_key

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:80]
    return "Untitled"


def _build_slide_feedback(slides: list[dict], judges: dict, summary: dict | None) -> list[dict]:
    """One entry per slide. Weaknesses come ONLY from the judges' real criticism."""
    summary_by_slide = {s["slide_number"]: s for s in (summary or {}).get("slides", [])}
    feedback = []
    for slide in slides:
        n = slide["slide_number"]
        weaknesses = []
        for key, result in judges.items():
            if not result:
                continue
            for w in result["weaknesses"]:
                if w["slide_number"] == n:
                    weaknesses.append({**w, "judge": key})
        weaknesses.sort(key=lambda w: -SEVERITY_RANK[w["severity"]])
        s = summary_by_slide.get(n)
        feedback.append(
            {
                "slide_number": n,
                "slide_title": (s["slide_title"] if s else _first_line(slide["text"])),
                "summary": s["summary"] if s else "",
                "strengths": s["strengths"] if s else [],
                "weaknesses": weaknesses,
                "severity": weaknesses[0]["severity"] if weaknesses else "none",
                "has_text": slide["has_text"],
            }
        )
    return feedback


def _fallback_top_improvements(judges: dict, slides: list[dict]) -> list[dict]:
    """If the summary call failed: take the most severe REAL judge weaknesses (one per slide)."""
    readable_numbers = {s["slide_number"] for s in slides if s["has_text"]}
    items = [
        w for result in judges.values() for w in result["weaknesses"]
        if w["slide_number"] in readable_numbers
    ]
    items.sort(key=lambda w: -SEVERITY_RANK[w["severity"]])
    seen, top = set(), []
    for w in items:
        if w["slide_number"] in seen:
            continue
        seen.add(w["slide_number"])
        top.append(
            {
                "slide_number": w["slide_number"],
                "problem": w["issue"],
                "why_it_matters": w["evidence"],
                "suggested_action": w["suggestion"],
                "severity": w["severity"],
            }
        )
        if len(top) == 3:
            break
    return top


def run_analysis(
    project_name: str,
    description: str,
    audience: str,
    filename: str,
    extraction: dict,
    progress=None,
    *,
    judge_key: str | None = None,
) -> dict:
    """Run the full analysis. `progress(message)` is called from the main thread so Streamlit can show updates.

    Pass a judge key to run only that judge. Omit it to retain the panel behavior for existing callers.
    Raises GroqError ONLY for problems that make the whole run pointless (e.g. no API key).
    """
    if judge_key is not None and judge_key not in JUDGES:
        raise ValueError(f"Unknown judge: {judge_key}")
    if not get_api_key():
        raise GroqError("missing_key", "No Groq API key found. Add GROQ_API_KEY to your .env file or Streamlit Secrets.")

    notify = progress or (lambda message: None)
    slides = extraction["slides"]
    judge_keys = (judge_key,) if judge_key is not None else tuple(JUDGES)
    judges: dict[str, dict | None] = dict.fromkeys(judge_keys)
    judge_errors: dict[str, str] = {}

    notify(f"{JUDGES[judge_key]['name']} is reading your deck…" if judge_key else "The judges are reading your deck…")
    with ThreadPoolExecutor(max_workers=len(judge_keys)) as pool:
        futures = {
            pool.submit(groq_service.run_judge, key, project_name, description, audience, slides): key
            for key in judge_keys
        }
        for future in as_completed(futures):
            key = futures[future]
            name = JUDGES[key]["name"]
            try:
                judges[key] = future.result()
                notify(f"✅ {name} has finished.")
            except GroqError as exc:
                judge_errors[key] = exc.user_message
                notify(f"⚠️ {name} failed: {exc.user_message}")
            except Exception:  # never leak a stack trace
                judge_errors[key] = "Something unexpected went wrong with this judge."
                notify(f"⚠️ {name} failed.")

    succeeded = {k: v for k, v in judges.items() if v}
    status = "complete" if len(succeeded) == len(judges) else ("incomplete" if succeeded else "failed")

    report = {
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_name": project_name,
        "description": description,
        "audience": audience,
        "filename": filename,
        "page_count": extraction["page_count"],
        "slides": slides,  # kept so the slide fixer can use the original text
        "warnings": list(extraction.get("warnings", [])),
        "judges": judges,
        "judge_errors": judge_errors,
        "scoring": None,
        "summary": None,
        "summary_error": None,
        "top_improvements": [],
        "slide_feedback": [],
        "visual_analysis": "unavailable",  # we only analyse extracted text
    }
    if not succeeded:
        return report

    report["scoring"] = scoring_service.calculate(succeeded, expected_judges=len(judges))

    notify("Preparing the AI review and improvement ideas…")
    summary = None
    try:
        summary = groq_service.generate_summary(project_name, audience, slides, succeeded)
    except GroqError as exc:
        report["summary_error"] = exc.user_message
    except Exception:
        report["summary_error"] = "The summary step failed unexpectedly."

    report["summary"] = summary
    report["top_improvements"] = (summary or {}).get("top_improvements") or _fallback_top_improvements(succeeded, slides)
    report["slide_feedback"] = _build_slide_feedback(slides, judges, summary)
    return report
