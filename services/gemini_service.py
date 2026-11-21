"""Gemini service: the ONLY file that talks to the Gemini API.

Main functions
    run_judge(...)        -> dict   one judge's validated report (raises GeminiError on failure)
    generate_summary(...) -> dict   overall verdict + top improvements + slide summaries
    generate_slide_fix(...) -> dict replacement copy and editing notes for a selected slide

How a call works
    1. Build the client from the API key (never printed or logged).
    2. Ask Gemini for JSON that matches a Pydantic model.
    3. Validate the JSON with that model. If it is invalid, retry ONCE, telling Gemini what was wrong.
    4. Retry temporary problems (overloaded server, network blip, rate limit) with a growing delay.
    5. Convert every failure into a GeminiError with a friendly message (never a stack trace).

Tests replace `_call_model` with a fake, so no API key is needed to test everything else.
"""
import json
import re
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from prompts.judges import JUDGES
from prompts.slide_fixer_prompt import SYSTEM_PROMPT as SLIDE_FIXER_SYSTEM_PROMPT
from prompts.summary_prompt import SYSTEM_PROMPT as SUMMARY_SYSTEM_PROMPT
from prompts.summary_prompt import build_summary_prompt
from prompts.common import build_user_prompt
from services.pdf_service import slides_to_prompt_text
from services.schemas import JudgeResult, SlideFix, SummaryResult
from utils.helpers import get_api_key, get_model_name

REQUEST_TIMEOUT_MS = 90_000  # 90 seconds per request
OVERLOAD_RETRY_DELAYS = (5, 15, 30)
TEMPERATURE = 0.6


class GeminiError(Exception):
    """A problem we can explain to the user. `kind` lets the UI react to the type of problem."""

    def __init__(self, kind: str, user_message: str):
        super().__init__(user_message)
        self.kind = kind
        self.user_message = user_message


# ---------------------------------------------------------------- error handling
def _classify(exc: Exception) -> tuple[str, bool, str]:
    """Turn any exception into (kind, is_retryable, friendly_message). Never includes secrets."""
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        text = (getattr(exc, "message", "") or "").lower()
        if code in (401, 403) or (code == 400 and "api key" in text):
            return "invalid_key", False, "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."
        if code == 404:
            return "model_not_found", False, (
                f"The model '{get_model_name()}' was not found. Set GEMINI_MODEL in .env to a model "
                "listed at ai.google.dev/gemini-api/docs/models."
            )
        if code == 429:
            return "quota", True, "Gemini rate limit or quota reached. Wait a minute and try again, or check your quota."
        if code is not None and code >= 500:
            return "server", True, "Gemini is temporarily overloaded. Please try again in a moment."
        return "bad_request", False, "Gemini could not process this request. Try a shorter deck or try again."
    # The SDK's HTTP library changed names across versions (httpx / httpx2), so we match on class names
    # instead of importing it. This works with any version.
    names = {c.__name__ for c in type(exc).__mro__}
    if isinstance(exc, TimeoutError) or any("Timeout" in n for n in names):
        return "timeout", True, "The request to Gemini timed out. Please try again."
    if isinstance(exc, (ConnectionError, OSError)) or names & {"TransportError", "NetworkError", "ConnectError", "ConnectionError"}:
        return "network", True, "Could not reach Gemini. Check your internet connection and try again."
    return "unknown", False, "Something unexpected went wrong while contacting Gemini."


def _sleep(seconds: float) -> None:  # separate function so tests can skip waiting
    time.sleep(seconds)


# ---------------------------------------------------------------- the single API call
def _call_model(system_prompt: str, user_prompt: str, schema: dict, *, model_name: str | None = None,
                image_png: bytes | None = None) -> str:
    """Send one request to Gemini and return the raw JSON text. Raises GeminiError('missing_key') if no key."""
    api_key = get_api_key()
    if not api_key:
        raise GeminiError("missing_key", "No Gemini API key found. Add GEMINI_API_KEY to your .env file.")
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))
    response = client.models.generate_content(
        model=model_name or get_model_name(),
        contents=[user_prompt, types.Part.from_bytes(data=image_png, mime_type="image/png")] if image_png else user_prompt,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "response_json_schema": schema,
            "temperature": TEMPERATURE,
        },
    )
    return response.text or ""


def generate_structured(system_prompt: str, user_prompt: str, model_cls: type[BaseModel],
                        *, image_png: bytes | None = None) -> BaseModel:
    """Call Gemini and return a validated `model_cls` object, or raise GeminiError."""
    schema = model_cls.model_json_schema()
    prompt = user_prompt
    transient_failures = 0
    invalid_json_retried = False
    fallback_model = None

    while True:
        try:
            options = {"model_name": fallback_model} if fallback_model else {}
            if image_png:
                options["image_png"] = image_png
            raw = _call_model(system_prompt, prompt, schema, **options)
        except GeminiError:
            raise
        except Exception as exc:  # classify everything the SDK/network can throw
            kind, retryable, message = _classify(exc)
            delays = OVERLOAD_RETRY_DELAYS if kind == "server" else (2, 4)
            if not fallback_model and retryable and transient_failures < len(delays):
                _sleep(delays[transient_failures])
                transient_failures += 1
                continue
            if kind == "server" and not fallback_model:
                primary = get_model_name()
                fallback_model = "gemini-3.5-flash-lite" if primary == "gemini-3.8-flash" else "gemini-3.8-flash"
                continue
            if fallback_model and kind in {"server", "quota", "model_not_found"}:
                message = "Gemini could not complete the request on either model. Please try again later."
            raise GeminiError(kind, message) from None

        try:
            return model_cls.model_validate_json(raw)
        except (ValidationError, ValueError) as exc:
            if invalid_json_retried:
                raise GeminiError(
                    "invalid_response", "The AI returned an answer in the wrong format twice. Please try again."
                ) from None
            invalid_json_retried = True
            problem = str(exc)[:600]
            prompt = (
                f"{user_prompt}\n\nYour previous answer was rejected because it did not match the required "
                f"JSON format:\n{problem}\nReturn corrected JSON only."
            )


# ---------------------------------------------------------------- the judges
def run_judge(judge_key: str, project_name: str, description: str, audience: str, slides: list[dict]) -> dict:
    """Run ONE judge. Returns a plain dict (JSON-friendly). Raises GeminiError on failure."""
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
    """Prepare the AI review and improvement ideas. Raises GeminiError on failure."""
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
        raise GeminiError("unreadable_slide", "Choose a slide with extractable text to generate a rewrite.")

    if style not in REWRITE_STYLES or (judge_key is not None and judge_key not in JUDGES):
        raise GeminiError("invalid_rewrite_options", "Choose a valid rewrite style and judge.")
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
        raise GeminiError("changed_numbers", "The rewrite changed or omitted a number or unit. Please try again.")
    return rewrite.model_dump()
