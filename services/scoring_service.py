"""Scoring engine. All score math happens HERE (backend), never in the UI.

INPUT : dict of successful judge results, e.g. {"investor": {...}, "professor": {...}}
        (each has "overall_score" and "category_scores" with 5 numbers 0-100)
OUTPUT: dict with overall_score, category_scores, interpretation, and a plain-English method.

Formula:
    Overall = Clarity*0.25 + Storytelling*0.20 + Business*0.25 + Innovation*0.20 + Technical*0.10
Category scores are the AVERAGE across the judges that produced a valid value.
Missing values are NEVER treated as 0: they are skipped, and we say so in `notes`.
"""
from services.schemas import CATEGORIES

WEIGHTS = {"clarity": 0.25, "storytelling": 0.20, "business": 0.25, "innovation": 0.20, "technical": 0.10}
LABELS = {
    "clarity": "Clarity",
    "storytelling": "Storytelling",
    "business": "Business viability",
    "innovation": "Innovation",
    "technical": "Technical feasibility",
}

BANDS = [  # (upper bound exclusive, label)
    (40, "Critical"),
    (60, "Needs major improvement"),
    (75, "Developing"),
    (90, "Strong"),
    (101, "Excellent"),
]
INTERPRETATION_NOTE = "Score bands are a product interpretation of this deck's communication, not a prediction of real-world success."


def interpret(score: float | None) -> str:
    if score is None:
        return "Not available"
    for upper, label in BANDS:
        if score < upper:
            return label
    return "Excellent"


def _valid(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100


def calculate(judge_results: dict[str, dict], expected_judges: int = 3) -> dict:
    notes: list[str] = []
    per_category: dict[str, list[float]] = {c: [] for c in CATEGORIES}

    for key, result in judge_results.items():
        scores = (result or {}).get("category_scores") or {}
        for cat in CATEGORIES:
            value = scores.get(cat)
            if _valid(value):
                per_category[cat].append(float(value))
            else:
                notes.append(f"{key}: missing or invalid '{cat}' score was skipped (not counted as 0).")

    category_scores = {
        cat: round(sum(vals) / len(vals), 1) if vals else None for cat, vals in per_category.items()
    }
    available = [c for c in CATEGORIES if category_scores[c] is not None]

    if not available:
        return {
            "overall_score": None,
            "category_scores": category_scores,
            "interpretation": "Not available",
            "judges_used": list(judge_results),
            "judge_scores": {},
            "weights": WEIGHTS,
            "method": "No valid scores were available, so no overall score could be calculated.",
            "notes": notes,
            "partial": True,
            "note": INTERPRETATION_NOTE,
        }

    weight_sum = sum(WEIGHTS[c] for c in available)  # equals 1.0 when all five categories exist
    overall = sum(category_scores[c] * WEIGHTS[c] for c in available) / weight_sum
    overall = round(overall, 1)

    if len(available) < len(CATEGORIES):
        missing = ", ".join(LABELS[c] for c in CATEGORIES if c not in available)
        notes.append(f"No valid score for: {missing}. The remaining weights were rescaled to add up to 100%.")
    if len(judge_results) < expected_judges:
        notes.append(
            f"Only {len(judge_results)} of {expected_judges} judges completed, so this score is based on incomplete data."
        )

    lines = []
    for c in available:
        pct = round(WEIGHTS[c] / weight_sum * 100)
        lines.append(f"{LABELS[c]}: {category_scores[c]} × {pct}% = {category_scores[c] * WEIGHTS[c] / weight_sum:.1f}")
    category_method = (
        "Each category uses the selected judge's score. "
        if expected_judges == 1 else "Each category is the average of the judges' scores for it. "
    )
    method = (
        category_method
        + "Overall = Clarity×25% + Storytelling×20% + Business×25% + Innovation×20% + Technical×10%.\n"
        + "\n".join(lines)
        + f"\nOverall = {overall}"
    )

    judge_scores = {
        k: r["overall_score"] for k, r in judge_results.items() if _valid((r or {}).get("overall_score"))
    }
    return {
        "overall_score": overall,
        "category_scores": category_scores,
        "interpretation": interpret(overall),
        "judges_used": list(judge_results),
        "judge_scores": judge_scores,
        "weights": WEIGHTS,
        "method": method,
        "notes": notes,
        "partial": bool(notes),
        "note": INTERPRETATION_NOTE,
    }
