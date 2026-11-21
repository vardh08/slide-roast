"""Fake Groq responses for tests. These are TEST DATA only; the app never uses them."""
import json


def fake_judge_json(key: str, score: int = 60, slide: int = 2, bad_slide: int | None = None) -> str:
    weaknesses = [
        {"slide_number": slide, "issue": f"{key} issue", "evidence": "The slide does not mention revenue.",
         "severity": "high", "suggestion": "Add it."},
        {"slide_number": 3, "issue": "Jargon", "evidence": "Says 'synergistic paradigm'.",
         "severity": "medium", "suggestion": "Use plain words."},
    ]
    if bad_slide:
        weaknesses.append({"slide_number": bad_slide, "issue": "ghost", "evidence": "x", "severity": "low", "suggestion": "y"})
    return json.dumps(
        {
            "judge": "WRONG-LABEL",  # the service must overwrite this
            "overall_score": score,
            "verdict": f"{key} verdict",
            "strengths": ["Clear problem"],
            "weaknesses": weaknesses,
            "category_scores": {"clarity": score, "storytelling": score, "business": score, "innovation": score, "technical": score},
            "judge_questions": [{"question": "Who pays?", "reason": "No revenue slide.", "preparation_points": ["Name a payer"]}],
            "top_improvements": ["Add revenue model"],
        }
    )


def fake_summary_json(slide_count: int = 7) -> str:
    return json.dumps(
        {
            "overall_verdict": {
                "does_well": "Simple problem statement.",
                "biggest_weakness": "No revenue model.",
                "is_idea_clear": "Mostly, apart from slide 3.",
                "next_action": "Add who pays.",
            },
            "top_improvements": [
                {"slide_number": 2, "problem": "No revenue", "why_it_matters": "Judges ask who pays.", "suggested_action": "Add a slide.", "severity": "high"},
                {"slide_number": 3, "problem": "Jargon", "why_it_matters": "Confuses readers.", "suggested_action": "Simplify.", "severity": "medium"},
                {"slide_number": 99, "problem": "ghost slide", "why_it_matters": "x", "suggested_action": "y", "severity": "low"},
            ],
            "slides": [
                {"slide_number": n, "slide_title": f"Title {n}", "summary": f"Slide {n} says things.", "strengths": []}
                for n in range(1, slide_count + 1)
            ],
        }
    )


def make_fake_call_model(scores=None, fail_judges=(), fail_summary=False, bad_slide=None):
    """Returns a replacement for groq_service._call_model. Decides what to answer from the system prompt."""
    from services.groq_service import GroqError

    scores = scores or {"investor": 50, "professor": 62, "customer": 74}

    def fake(system_prompt, user_prompt, schema):
        for key in ("investor", "professor", "customer"):
            if f'Your judge key is "{key}"' in system_prompt:
                if key in fail_judges:
                    raise GroqError("server", "Groq is temporarily overloaded.")
                return fake_judge_json(key, scores[key], bad_slide=bad_slide)
        if fail_summary:
            raise GroqError("server", "Groq is temporarily overloaded.")
        return fake_summary_json()

    return fake
