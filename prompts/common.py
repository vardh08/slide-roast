"""Text shared by all three judge prompts (rules + how we show the deck to the judge)."""

# These rules are appended to EVERY judge's system prompt.
GROUNDING_RULES = """
STRICT RULES (apply to everything you write):
1. Base every criticism and every strength ONLY on the slide text you are given.
2. NEVER invent statistics, customer numbers, market sizes, revenue figures, competitors, or evidence.
   If a number is not in the slides, do not quote or imply one.
3. If something important is missing from the deck, say plainly that it is missing. Do not guess what the team meant.
4. Every weakness must cite a real slide_number from the deck. The "evidence" field must describe what that slide
   actually says, or state that the slide does not mention the topic.
5. Slides marked [NO EXTRACTABLE TEXT ON THIS SLIDE] could not be read. Do not judge their content or visuals.
6. You only see extracted TEXT. You cannot see layout, colors, images or fonts, so make NO claims about visual design.
7. Be blunt and specific, never cruel. Criticize the deck, not the people.
8. Scores are integers from 0 to 100. Use the full range; do not give everyone 70-85. An unclear or missing area should score low.
9. Give 2-4 strengths, 3-6 weaknesses, 3-5 judge_questions and 3 top_improvements.
10. Your "judge" field must be exactly the judge key you are told to use.
11. Your opening line is personality flavor only. Start your "verdict" in your own voice, but base it on the slides.

SCORING CATEGORIES (all judges fill all five, from YOUR perspective):
- clarity: is the idea and message easy to understand?
- storytelling: does the deck flow as a convincing story (problem -> solution -> proof -> ask)?
- business: is there a believable answer to who benefits / pays and why it is sustainable?
- innovation: is it meaningfully different from alternatives?
- technical: is the approach realistic and explained well enough?
If the deck says nothing about a category, give a LOW score and say so in a weakness.
""".strip()


def build_user_prompt(project_name: str, description: str, audience: str, slides_text: str, slide_count: int) -> str:
    """The message that is identical for all judges: the project info plus the extracted slides."""
    desc = description.strip() or "(none provided)"
    return f"""Evaluate this pitch deck.

PROJECT NAME: {project_name}
PROJECT DESCRIPTION (from the presenter): {desc}
TARGET AUDIENCE: {audience}
NUMBER OF SLIDES: {slide_count} (valid slide_number values are 1 to {slide_count})
VISUAL ANALYSIS: unavailable (text only)

Judge it for the target audience above.

===== DECK CONTENT (extracted text) =====
{slides_text}
===== END OF DECK ====="""
