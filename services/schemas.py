"""Pydantic models = the exact JSON shapes we expect back from Groq.

Pydantic does two jobs for us:
1. `Model.model_json_schema()` tells Groq what JSON to produce.
2. `Model.model_validate_json(text)` checks Groq's answer. Scores outside 0-100,
   wrong types or missing fields raise a ValidationError, which we handle.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Severity = Literal["low", "medium", "high"]
Score = Field(ge=0, le=100)

CATEGORIES = ["clarity", "storytelling", "business", "innovation", "technical"]


# ---------- What every judge returns (same shape for all three) ----------
class Weakness(BaseModel):
    slide_number: int = Field(description="Slide the problem is on (1-based). Must exist in the deck.")
    issue: str
    evidence: str = Field(description="What the slide actually says (or does not say) that proves the issue.")
    severity: Severity
    suggestion: str


class CategoryScores(BaseModel):
    clarity: int = Score
    storytelling: int = Score
    business: int = Score
    innovation: int = Score
    technical: int = Score


class JudgeQuestion(BaseModel):
    question: str
    reason: str = Field(description="Why a real judge would ask this, based on the slides.")
    preparation_points: list[str] = Field(description="2-3 short things the presenter should prepare to say.")


class JudgeResult(BaseModel):
    judge: str
    overall_score: int = Score
    verdict: str = Field(description="One or two sentences in the judge's voice.")
    strengths: list[str]
    weaknesses: list[Weakness]
    category_scores: CategoryScores
    judge_questions: list[JudgeQuestion]
    top_improvements: list[str]


# ---------- What the summary step returns ----------
class OverallVerdict(BaseModel):
    does_well: str
    biggest_weakness: str
    is_idea_clear: str = Field(description="Whether the idea is communicated clearly, and why.")
    next_action: str = Field(description="The single most important thing to do next.")


class TopImprovement(BaseModel):
    slide_number: int
    problem: str
    why_it_matters: str
    suggested_action: str
    severity: Severity


class SlideSummary(BaseModel):
    slide_number: int
    slide_title: str = Field(description="Title of the slide taken from its text; 'Untitled' if none.")
    summary: str = Field(description="One short sentence on what the slide says.")
    strengths: list[str]


class SummaryResult(BaseModel):
    overall_verdict: OverallVerdict
    top_improvements: list[TopImprovement] = Field(description="Up to 3 improvements, highest impact first.")
    slides: list[SlideSummary]


SlideCopy = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SlideFix(BaseModel):
    title: SlideCopy = Field(description="A concise replacement headline for the slide.")
    body: SlideCopy = Field(description="Ready-to-paste slide text with short lines and bullets where useful.")
    changes: list[SlideCopy] = Field(description="Brief explanations of the most important edits.")
    evidence_to_add: list[SlideCopy] = Field(description="Specific facts or proof to gather. Empty if none are needed.")
