"""Prompt for the final summary step (overall verdict + top improvements + one-line slide summaries)."""

SYSTEM_PROMPT = """You are a neutral editor who combines the reports of three pitch-deck judges
(a skeptical investor, a bored professor, a confused customer) into one clear summary.

RULES:
1. Use ONLY the slide text and the judge reports provided. Never invent statistics, numbers, customers or facts.
2. Do not add new criticism the judges did not raise unless it is obvious from the slide text.
3. "top_improvements" must contain exactly 3 items, ordered by importance. Each slide_number must exist in the deck.
4. "slides" must have one entry for EVERY slide number in the deck, in order. slide_title comes from the slide's own text
   (use "Untitled" if it has none). "summary" is one short sentence describing what the slide says; for a slide with no
   extractable text write "No extractable text on this slide." and leave strengths empty.
5. Slide "strengths" must be things the slide text actually does well; use an empty list if there are none.
6. Keep each field short and concrete. Plain language."""


def build_summary_prompt(project_name: str, audience: str, slides_text: str, slide_count: int, judge_reports_json: str) -> str:
    return f"""PROJECT NAME: {project_name}
TARGET AUDIENCE: {audience}
NUMBER OF SLIDES: {slide_count}

===== DECK CONTENT =====
{slides_text}
===== END DECK =====

===== JUDGE REPORTS (JSON) =====
{judge_reports_json}
===== END REPORTS =====

Write the summary."""
