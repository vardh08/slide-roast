"""Roast Report dashboard. Reads the report dict from st.session_state["report"].

Shows the selected judge's feedback, the AI review, and an on-demand slide fixer.
"""
import re

import streamlit as st

from prompts.judges import JUDGES
from services.schemas import CATEGORIES
from services.scoring_service import BANDS, LABELS, WEIGHTS
from utils.helpers import esc
from utils.slide_fixer_view import render_slide_fixer
from utils.styles import card, score_markup

SEV_ORDER = {"high": 3, "medium": 2, "low": 1, "none": 0}


def pill(severity: str) -> str:
    label = "No issues flagged" if severity == "none" else severity.title()
    return f"<span class='sr-pill sr-sev-{esc(severity)}'>{esc(label)}</span>"


def score_ring(score: float | None) -> str:
    """Render the shared score indicator."""
    if score is None:
        return "<div class='sr-muted'>No score</div>"
    return score_markup(score)


def first_sentence(text: str) -> str:
    """Keep the preview short and leave the full source wording in the disclosure."""
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip(), maxsplit=1)[0]


def score_rows(scores: dict, weights: dict) -> list[tuple[str, float, float]]:
    active_weight = sum(weights[k] for k in CATEGORIES if scores.get(k) is not None and k in weights)
    rows = []
    inputs = []
    for key in CATEGORIES:
        value = scores.get(key)
        if value is None or key not in weights or not active_weight:
            score, progress, detail = "Unavailable", "", "Excluded from the total"
        else:
            score = f"{value:g} / 100"
            share = weights[key] / active_weight
            inputs.append((key, value, share))
            points = f"{value * share:.1f}".rstrip("0").rstrip(".")
            percent = f"{share * 100:.1f}".rstrip("0").rstrip(".")
            detail = f"<b>{percent}%</b> weight · <b>{points} points toward the total</b>"
            progress = (
                f'<div class="review-score-track" role="meter" aria-label="{esc(LABELS[key])} score" '
                f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{value:g}">'
                f'<div style="width:{value:g}%"></div></div>'
            )
        rows.append(
            f'<div class="review-score-row"><div class="review-score-label"><strong>{esc(LABELS[key])}</strong>'
            f'<span>{score}</span></div>{progress}<small>{detail}</small></div>'
        )
    st.html(f'<div class="review-score-list">{"".join(rows)}</div>')
    return inputs


def feedback_area(heading: str, items: list[str], *, emphasis: str = "") -> None:
    points = "".join(f"<li>{esc(item)}</li>" for item in items)
    st.markdown(f'<div class="review-feedback {emphasis}"><h3>{heading}</h3><ul>{points}</ul></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ load report
report = st.session_state.get("report")
if not report:
    st.title("Roast Report")
    st.info("No report yet. Upload a deck to get roasted.")
    if st.button("Roast My Deck", type="primary"):
        st.switch_page("pages/1_Upload.py")
    st.stop()

scoring = report.get("scoring") or {}
judges = report["judges"]
selected_judges = {key: meta for key, meta in JUDGES.items() if key in judges}
single_judge = len(selected_judges) == 1
overall = scoring.get("overall_score")

st.title("Your Roast Report")
st.write("Here's what your pitch deck needs to improve.")
st.subheader(report["project_name"])
judge_names = ", ".join(meta["name"] for meta in selected_judges.values())
st.caption(
    f"{report['filename']} · {judge_names} · {report['created_at'][:10]} · "
    f"{report['page_count']} slides · {report['audience']}"
)
st.caption("Evaluated from extracted slide text.")

if report["status"] != "complete":
    missing = [JUDGES[k]["name"] for k, v in judges.items() if not v]
    st.warning(
        "**Incomplete report.** These judges did not finish: " + ", ".join(missing)
        + ". Their scores are NOT included, and nothing was made up in their place."
    )
    for key, message in report["judge_errors"].items():
        st.caption(f"{JUDGES[key]['name']}: {message}")
for w in report.get("warnings", []):
    st.warning(w)

# ------------------------------------------------------------------ A. overall score
st.markdown("## Overall score")
interp = scoring.get("interpretation", "Not available")
verdict_text = (report.get("summary") or {}).get("overall_verdict", {}).get("is_idea_clear")
card(
    f"<div class='report-score'>{score_ring(overall)}<div><h3>{esc(interp)}</h3>"
    f"<p>{esc(verdict_text or 'Overall verdict unavailable.')}</p></div></div>"
)
with st.container(key="review_disclosures_score"):
    with st.expander("**How We Calculate Your Score** · See what contributes to your total"):
        st.caption(
            "We combine the category scores using the weights below."
            if single_judge else "We average available judge scores in each category and combine them using the weights below."
        )
        st.caption("Each bar shows a category’s score out of 100. The points below it show what that category adds to your total.")
        inputs = score_rows(scoring.get("category_scores", {}), scoring.get("weights") or WEIGHTS)
        if overall is not None:
            st.html(f'<div class="review-score-total"><strong>Weighted total</strong><b>{overall:g} / 100</b></div>')
        with st.expander("View calculation notes"):
            if inputs:
                key, value, share = inputs[0]
                percent = f"{share * 100:.4f}".rstrip("0").rstrip(".")
                st.markdown(
                    f"**Worked example.** {LABELS[key]} scored **{value:g} / 100**. "
                    f"At a weight of **{percent}%**, "
                    f"it contributes **{value * share:.2f} points**."
                )
                st.markdown(
                    "**Rounding.** We add the weighted contributions before rounding the total to one decimal place. "
                    "The score ring shows the nearest whole point."
                )
            else:
                st.caption("No valid category scores were available to weight.")
            for note in scoring.get("notes", []):
                st.caption(note)
            st.markdown("**How to read the score**")
            lower = 0
            bands = []
            for upper, name in BANDS:
                interval = f"{lower}–100" if upper > 100 else f"{lower}–{upper - .1:g}"
                bands.append(f"<div><b>{interval}</b><span>{esc(name)}</span></div>")
                lower = upper
            st.html(f'<div class="review-score-bands">{"".join(bands)}</div>')
            if scoring.get("note"):
                st.caption(scoring["note"])

# ------------------------------------------------------------------ B. judge cards
st.markdown("## Your selected judge" if single_judge else "## The judges")
for key, meta in selected_judges.items():
    result = judges.get(key)
    if not result:
        card(f"<b>{esc(meta['name'])}</b><p>This judge did not complete.</p>")
        continue
    strengths = result["strengths"]
    weaknesses = sorted(result["weaknesses"], key=lambda item: -SEV_ORDER[item["severity"]])
    card(
        f"<div class='report-score'>{score_ring(result['overall_score'])}<div>"
        f"<h3 class='sr-judge-name'>{esc(meta['name'])}</h3><p>{esc(meta['personality'])}</p></div></div>"
    )
    works, needs = st.columns(2)
    with works:
        feedback_area("✓ What You Nailed", [first_sentence(strengths[0])] if strengths else ["No strengths listed."],
                      emphasis="review-strength")
    with needs:
        feedback_area("↗ What Needs Work", [first_sentence(weaknesses[0]["issue"])] if weaknesses else ["No issues flagged."],
                      emphasis="review-priority")
    with st.container(key=f"review_disclosures_judge_{key}"):
        with st.expander("**Full Judge Report** · Explore the judge’s complete feedback"):
            st.markdown("#### The verdict")
            st.markdown(esc(result["verdict"]))
            more_strengths = ([strengths[0]] if strengths and first_sentence(strengths[0]) != strengths[0] else []) + strengths[1:]
            if more_strengths:
                feedback_area("What works", more_strengths)
            if weaknesses:
                st.markdown("#### What holds it back")
                for item in weaknesses:
                    issue = item["issue"]
                    if item is weaknesses[0] and first_sentence(issue) == issue:
                        issue = item["evidence"]
                    else:
                        issue = f"{issue} · {item['evidence']}"
                    st.markdown(f"**Slide {item['slide_number']}** · {esc(issue)}")
            fixes = list(dict.fromkeys([*result["top_improvements"], *(item["suggestion"] for item in weaknesses)]))
            if fixes:
                feedback_area("What to fix first", fixes)
            if result.get("dropped_weaknesses"):
                st.caption(f"{result['dropped_weaknesses']} item(s) were hidden because they cited a slide that does not exist.")

# ------------------------------------------------------------------ D. AI review
st.markdown("## AI Review")
summary = report.get("summary")
if summary:
    st.markdown("### Overall verdict")
    v = summary["overall_verdict"]
    verdict_fields = (
        ("What the deck does well", "does_well"),
        ("Biggest weakness", "biggest_weakness"),
        ("Is the idea clear?", "is_idea_clear"),
        ("Most important next action", "next_action"),
    )
    verdict_blocks = "".join(
        f"<section><h3>{heading}</h3><p>{esc(v[field])}</p></section>"
        for heading, field in verdict_fields
    )
    st.markdown(f"<div class='sr-verdict'>{verdict_blocks}</div>", unsafe_allow_html=True)
else:
    st.info(
        "The AI summary is unavailable"
        + (f" ({report['summary_error']})" if report.get("summary_error") else "")
        + ". You can still use the available judge feedback."
    )

st.markdown("### Top 3 improvements")
if report["top_improvements"]:
    if not (summary or {}).get("top_improvements"):
        st.caption("These ideas come from the available judge feedback.")
    with st.container(key="report_priority_improvements"):
        for i, imp in enumerate(report["top_improvements"], 1):
            card(
                f"{pill(imp['severity'])}<b>{i}. Slide {imp['slide_number']}: {esc(imp['problem'])}</b><br>"
                f"<span class='sr-muted'><b>Why it matters:</b> {esc(imp['why_it_matters'])}</span><br>"
                f"<span class='sr-muted'><b>What to do:</b> {esc(imp['suggested_action'])}</span>"
            )
else:
    st.caption("No improvements were returned.")

# ------------------------------------------------------------------ E. slide fixer
render_slide_fixer(report)

# ------------------------------------------------------------------ F. slide-by-slide
st.markdown("## Slide-by-slide feedback")
with st.container(key="review_disclosures_slides"):
    high_count = sum(fb["severity"] == "high" for fb in report["slide_feedback"])
    if high_count:
        noun = "slide" if high_count == 1 else "slides"
        st.markdown(
            f"<div class='report-priority-count'><strong>Start here</strong>"
            f"<span>{high_count} high-priority {noun}</span></div>",
            unsafe_allow_html=True,
        )
    for fb in report["slide_feedback"]:
        number = fb["slide_number"]
        title = fb["slide_title"]
        title = re.sub(r"([\\`*_~\[\]<>])", r"\\\1", title) if title and title != "Untitled" else ""
        label = f"**Slide {number:02d}**" + (f" · **{title}**" if title else "")
        priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(fb["severity"])
        if fb["weaknesses"] and priority_color:
            priority = f"**{fb['severity'].title()} priority**"
            label += f" · :{priority_color}-background[{priority}]"
        with st.expander(label):
            if not fb["has_text"]:
                st.caption("No extractable text on this slide, so it could not be judged.")
            if fb["summary"]:
                st.markdown(esc(fb["summary"]))
            if fb["strengths"]:
                feedback_area("What’s working", fb["strengths"])
            if fb["weaknesses"]:
                st.markdown("#### What needs fixing")
                for issue in fb["weaknesses"]:
                    judge = JUDGES.get(issue.get("judge"), {}).get("name")
                    source = f" · {esc(judge)}" if judge and not single_judge else ""
                    st.markdown(
                        f"<div class='slide-feedback-issue'>"
                        f"{pill(issue['severity'])}<strong>{esc(issue['issue'])}</strong>{source}"
                        f"<p><b>Evidence</b> · {esc(issue['evidence'])}</p></div>",
                        unsafe_allow_html=True,
                    )
                feedback_area("How to improve", list(dict.fromkeys(issue["suggestion"] for issue in fb["weaknesses"])))
            elif fb["has_text"]:
                st.caption("No problems were flagged on this slide.")

# ------------------------------------------------------------------ G. judge questions
st.markdown("## Questions You Better Be Ready For")
for key, meta in selected_judges.items():
    r = judges.get(key)
    if not r:
        continue
    st.markdown(f"<h3>{esc(meta['name'])}</h3>", unsafe_allow_html=True)
    questions = []
    for q in r["judge_questions"]:
        prep = "".join(f"<li>{esc(p)}</li>" for p in q["preparation_points"])
        questions.append(
            f"<li class='sr-question'><strong>{esc(q['question'])}</strong>"
            f"<div class='sr-muted'>Why it matters: {esc(q['reason'])}</div>"
            f"<div>Prepare<ul>{prep}</ul></div></li>"
        )
    st.markdown(f"<ol>{''.join(questions)}</ol>", unsafe_allow_html=True)

st.divider()
if st.button("Roast another deck"):
    st.switch_page("pages/1_Upload.py")
