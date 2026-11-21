"""LIVE check against the real Gemini API (uses your key from .env, never prints it).

Run from the project folder:
    python -m tests.live_check

It runs the full pipeline on assets/sample_deck_v1.pdf and prints what really came back.
This uses a little of your free quota (4 API calls).
"""
from pathlib import Path

from services.gemini_service import GeminiError
from services.pdf_service import extract_slides
from services.report_service import run_analysis

DECK = Path(__file__).resolve().parent.parent / "assets" / "sample_deck_v1.pdf"


def main():
    extraction = extract_slides(DECK.read_bytes())
    print(f"Extracted {extraction['page_count']} slides. Calling Gemini...\n")
    try:
        report = run_analysis(
            "Campus Barter", "", "Hackathon Judges", DECK.name, extraction, progress=lambda m: print("  ", m)
        )
    except GeminiError as exc:
        print("\nFAILED:", exc.kind, "-", exc.user_message)
        return

    print("\nStatus:", report["status"])
    for key, err in report["judge_errors"].items():
        print(f"  {key} FAILED: {err}")
    for key, r in report["judges"].items():
        if r:
            print(f"  {key:10s} score={r['overall_score']:3d} weaknesses={len(r['weaknesses'])} "
                  f"questions={len(r['judge_questions'])} dropped={r['dropped_weaknesses']}")
            print(f"             verdict: {r['verdict']}")
    if report["scoring"]:
        print("\n" + report["scoring"]["method"])
        print("Interpretation:", report["scoring"]["interpretation"])
    print("\nSummary step:", "OK" if report["summary"] else f"FAILED ({report['summary_error']})")
    for imp in report["top_improvements"]:
        print(f"  Slide {imp['slide_number']} [{imp['severity']}] {imp['problem']}")


if __name__ == "__main__":
    main()
