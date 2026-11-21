"""Text-only Groq chat completions and validation for Slide Roast."""
import json
import re
import time
from threading import Event

import groq
from pydantic import BaseModel, ValidationError

from prompts.common import build_user_prompt
from prompts.judges import JUDGES
from prompts.slide_fixer_prompt import SYSTEM_PROMPT as SLIDE_FIXER_SYSTEM_PROMPT
from prompts.summary_prompt import SYSTEM_PROMPT as SUMMARY_SYSTEM_PROMPT
from prompts.summary_prompt import build_summary_prompt
from services.pdf_service import slides_to_prompt_text
from services.schemas import JudgeResult, SlideFix, SummaryResult
from utils.helpers import get_api_key

MODEL = "openai/gpt-oss-120b"
REPLACEMENT_MODEL = "openai/gpt-oss-120b"  # Groq's replacement for the retired default.
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 2
RATE_LIMIT_MESSAGE = "Rate limit reached. Wait a minute and try again."
_model_retired = Event()


class GroqError(Exception):
    """A provider or validation failure with a safe, user-facing message."""

    def __init__(self, kind: str, user_message: str):
        super().__init__(user_message)
        self.kind = kind
        self.user_message = user_message


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _call_model(system_prompt: str, user_prompt: str, schema: dict, *, model_name: str | None = None) -> str:
    api_key = get_api_key()
    if not api_key:
        raise GroqError("missing_key", "No Groq API key found. Add GROQ_API_KEY to your .env file or Streamlit Secrets.")
    instructions = f"{user_prompt}\n\nReturn one JSON object that matches this schema:\n{json.dumps(schema, separators=(',', ':'))}"
    with groq.Groq(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0) as client:
        response = client.chat.completions.create(
            model=model_name or MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": instructions},
            ],
            response_format={"type": "json_object"},
            temperature=0.6,
        )
    return (response.choices[0].message.content or "") if response.choices else ""


def generate_structured(system_prompt: str, user_prompt: str, model_cls: type[BaseModel]) -> BaseModel:
    """Validate JSON locally, sharing one retry budget across all failure modes."""
    schema = model_cls.model_json_schema()
    prompt = user_prompt
    replacement = _model_retired.is_set()
    for attempt in range(MAX_RETRIES + 1):
        options = {"model_name": REPLACEMENT_MODEL} if replacement else {}
        retryable = False
        try:
            raw = _call_model(system_prompt, prompt, schema, **options)
            return model_cls.model_validate_json(raw)
        except groq.RateLimitError:
            raise GroqError("quota", RATE_LIMIT_MESSAGE) from None
        except (groq.AuthenticationError, groq.PermissionDeniedError):
            raise GroqError("invalid_key", "Groq denied access. Check GROQ_API_KEY and its project permissions.") from None
        except groq.APITimeoutError:
            error = GroqError("timeout", "The request to Groq timed out. Please try again.")
            retryable = True
        except groq.APIConnectionError:
            error = GroqError("network", "Could not reach Groq. Check your connection and try again.")
            retryable = True
        except groq.APIStatusError as exc:
            body = exc.body
            if isinstance(body, dict) and isinstance(body.get("error"), dict):
                body = body["error"]
            code = body.get("code") if isinstance(body, dict) else None
            if code == "model_decommissioned":
                error = GroqError("model_not_found", "The configured Groq model is retired. Update MODEL in services/groq_service.py.")
                if not replacement and attempt < MAX_RETRIES:
                    replacement = True
                    _model_retired.set()
                    continue
            elif exc.status_code == 404:
                error = GroqError("model_not_found", "The configured Groq model was not found. Check MODEL in services/groq_service.py.")
            elif exc.status_code >= 500 or exc.status_code in (408, 409):
                error = GroqError("server", "Groq is temporarily unavailable. Please try again in a moment.")
                retryable = True
            elif code == "json_validate_failed":
                error = GroqError("invalid_response", "Groq did not return valid JSON. Please try again.")
                retryable = True
            else:
                error = GroqError("bad_request", "Groq could not process this request. Try a shorter deck or try again.")
        except (ValidationError, groq.APIResponseValidationError):
            error = GroqError("invalid_response", "The AI response did not match the expected format. Please try again.")
            prompt = f"{user_prompt}\n\nReturn corrected JSON with all required fields and valid values."
            retryable = True

        if not retryable or attempt == MAX_RETRIES:
            raise error from None
        _sleep(2 ** attempt)

    raise AssertionError("Unreachable retry limit")


# ---------------------------------------------------------------- the judges
def run_judge(judge_key: str, project_name: str, description: str, audience: str, slides: list[dict]) -> dict:
    """Run ONE judge. Returns a plain dict (JSON-friendly). Raises GroqError on failure."""
    judge = JUDGES[judge_key]
    valid_numbers = {s["slide_number"] for s in slides}
    user_prompt = build_user_prompt(
        project_name, description, audience, slides_to_prompt_text(slides), len(slides)
    )
    result: JudgeResult = generate_structured(judge["system_prompt"], user_prompt, JudgeResult)

    data = result.model_dump()
    data["judge"] = judge_key  # never trust the model to label itself correctly

    # Drop criticism that points to slides that do not exist (never show invalid references).
    kept = [w for w in data["weaknesses"] if w["slide_number"] in valid_numbers]
    data["dropped_weaknesses"] = len(data["weaknesses"]) - len(kept)
    data["weaknesses"] = kept
    return data


# ---------------------------------------------------------------- the summary
def generate_summary(project_name: str, audience: str, slides: list[dict], judge_results: dict[str, dict]) -> dict:
    """Prepare the AI review and improvement ideas. Raises GroqError on failure."""
    valid_numbers = {s["slide_number"] for s in slides}
    readable_numbers = {s["slide_number"] for s in slides if s["has_text"]}
    # Send only what the editor needs (keeps the prompt small).
    compact = {
        key: {
            "verdict": r["verdict"],
            "strengths": r["strengths"],
            "weaknesses": [
                {k: w[k] for k in ("slide_number", "issue", "severity")} for w in r["weaknesses"]
            ],
            "top_improvements": r["top_improvements"],
        }
        for key, r in judge_results.items()
    }
    prompt = build_summary_prompt(
        project_name, audience, slides_to_prompt_text(slides), len(slides), json.dumps(compact, indent=1)
    )
    result: SummaryResult = generate_structured(SUMMARY_SYSTEM_PROMPT, prompt, SummaryResult)
    data = result.model_dump()
    data["top_improvements"] = [i for i in data["top_improvements"] if i["slide_number"] in readable_numbers][:3]
    data["slides"] = [s for s in data["slides"] if s["slide_number"] in valid_numbers]
    return data


_NUMBER = re.compile(
    r"(?<!\w)(?:[$€£₹]\s*)?[+−-]?\d+(?:[.,:/]\d+)*(?:\s*(?:%|‰|°[CF]|"
    r"(?:USD|EUR|GBP|INR|million|billion|trillion|km|cm|mm|kg|mg|ml|GB|MB|ms|kWh|Mbps)\b))?",
    re.IGNORECASE,
)
REWRITE_STYLES = {
    "Professional": "Polished, clear, grammatically sound presentation copy.",
    "Concise": "Remove repetition and shorten sentences while keeping essential information.",
    "Persuasive": "Clarify the value and strengthen the argument using only the available evidence.",
}
_REWRITE_LENSES = {
    "investor": "Clarify the business model, value proposition and available evidence.",
    "professor": "Prioritize logical structure, precise terminology and evidence.",
    "customer": "Use everyday language and clarify the problem and practical benefits.",
}


def generate_slide_fix(report: dict, slide_number: int, *, style: str = "Professional",
                       judge_key: str | None = None) -> dict:
    """Rewrite a readable slide using its original copy and the report's feedback."""
    slide = next((s for s in report.get("slides", []) if s["slide_number"] == slide_number), None)
    if slide is None or not slide["has_text"] or not slide["text"].strip():
        raise GroqError("unreadable_slide", "Choose a slide with extractable text to generate a rewrite.")

    if style not in REWRITE_STYLES or (judge_key is not None and judge_key not in JUDGES):
        raise GroqError("invalid_rewrite_options", "Choose a valid rewrite style and judge.")
    improvements = [
        {"issue": idea["problem"], "suggestion": idea["suggested_action"]}
        for idea in report.get("top_improvements", [])
        if idea["slide_number"] == slide_number
    ]
    for feedback in report.get("slide_feedback", []):
        if feedback["slide_number"] == slide_number:
            if judge_key is not None:
                improvements = []
            improvements.extend({"issue": w["issue"], "suggestion": w["suggestion"]} for w in feedback["weaknesses"]
                                if judge_key is None or w.get("judge") == judge_key)
            break

    prompt = json.dumps({
        "project_name": report["project_name"],
        "project_description": report.get("description", ""),
        "target_audience": report["audience"],
        "rewrite_style": f"{style}: {REWRITE_STYLES[style]}",
        "judge_perspective": (f"{JUDGES[judge_key]['name']}: {_REWRITE_LENSES[judge_key]}" if judge_key else None),
        "slide_number": slide_number,
        "original_slide_text": slide["text"],
        "feedback": improvements,
    }, ensure_ascii=False, indent=2)
    rewrite = generate_structured(SLIDE_FIXER_SYSTEM_PROMPT, prompt, SlideFix)
    original_numbers = set(_NUMBER.findall(slide["text"]))
    improved_numbers = set(_NUMBER.findall(f"{rewrite.title}\n{rewrite.body}"))
    if original_numbers != improved_numbers:
        raise GroqError("changed_numbers", "The rewrite changed or omitted a number or unit. Please try again.")
    return rewrite.model_dump()
