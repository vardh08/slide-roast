"""Upload a PDF and choose the judge that will review it."""
import streamlit as st

from prompts.judges import JUDGES
from services.groq_service import GroqError
from services.pdf_service import extract_slides
from services.report_service import run_analysis
from utils.helpers import AUDIENCES, MAX_FILE_MB, MAX_PAGES, get_api_key
from utils.validators import validate_file_basics, validate_project_inputs

JUDGE_DESCRIPTIONS = {
    "investor": "Challenges your market, business model, and revenue potential.",
    "professor": "Examines your logic, research, structure, and evidence.",
    "customer": "Questions whether your idea is clear, useful, and understandable.",
}


def render_upload(*, standalone: bool = False) -> None:
    heading = "h1" if standalone else "h2"
    st.html(f"""
    <header class="upload-heading">
        <{heading}>Let's see what you've got.</{heading}>
        <p>Upload your pitch deck, choose your judge, and get feedback that actually helps.</p>
    </header>
    """)

    if not get_api_key():
        st.warning(
            "No Groq API key found. You can upload and preview extraction, but AI judging needs a key. "
            "Set `GROQ_API_KEY` in your `.env` file or Streamlit Secrets."
        )

    left, right = st.columns([0.9, 1.1], gap="medium")

    # ---------- Left: upload ----------
    with left:
        st.subheader("PDF upload", anchor=False)
        with st.container(key="deck_dropzone"):
            uploaded = st.file_uploader(
                f"Choose a PDF, up to {MAX_FILE_MB} MB and {MAX_PAGES} pages",
                type=["pdf"],
                key=f"uploader_{st.session_state.get('uploader_key', 0)}",
                label_visibility="collapsed",
            )
            if uploaded is None:
                st.html(f"""
                <div class="deck-drop-copy" aria-hidden="true">
                    <span class="deck-file-icon"></span>
                    <strong>Drop your PDF here</strong>
                    <span>or click to browse your files</span>
                    <span class="deck-choose-pdf">Choose PDF</span>
                    <small>PDF only · Max {MAX_FILE_MB} MB · Max {MAX_PAGES} pages</small>
                </div>
                """)
        st.caption("Your PDF is processed in memory. Extracted slide text is available during this session.")

        file_errors, extraction = [], None
        if uploaded is not None:
            pdf_bytes = uploaded.getvalue()
            file_errors = validate_file_basics(uploaded.name, len(pdf_bytes))
            if not file_errors:
                with st.spinner("Reading your slides…"):
                    extraction = extract_slides(pdf_bytes)  # cheap, so we just re-run it
                if not extraction["ok"]:
                    file_errors = [extraction["error"]]
            for err in file_errors:
                st.error(err)
            if extraction and extraction["ok"]:
                st.success(f"PDF is valid · {extraction['page_count']} slide(s) read.")
                for w in extraction["warnings"]:
                    st.warning(w)

    # ---------- Right: project info ----------
    with right:
        st.subheader("Tell us about your pitch", anchor=False)
        project_name = st.text_input("Project name *", max_chars=100, placeholder="e.g. Campus Barter")
        description = st.text_area(
            "Project description (optional)", max_chars=1500, height=120,
            placeholder="Briefly describe your idea and anything the slides might not explain.",
        )
        audience = st.selectbox("Target audience *", AUDIENCES)

        st.subheader("Choose your judge", anchor=False)
        judge_key = st.radio(
            "Who do you want reviewing your pitch?",
            options=list(JUDGES),
            index=None,
            format_func=lambda key: JUDGES[key]["name"],
            captions=[JUDGE_DESCRIPTIONS[key] for key in JUDGES],
            key="judge_personality",
            width="stretch",
        )

    valid_upload = extraction is not None and extraction["ok"]
    problems = validate_project_inputs(project_name, audience, description)
    requirements = []
    if not valid_upload:
        requirements.append("Upload a valid PDF.")
    requirements.extend(problems)
    if judge_key is None:
        requirements.append("Choose a judge.")
    with st.container(key="deck_submit"):
        start = st.button("Roast My Deck ↗", type="primary", disabled=bool(requirements), width="stretch")
        if requirements:
            st.caption(" ".join(requirements))

    if start and judge_key is not None and uploaded is not None and extraction is not None:
        if problems:
            for p in problems:
                st.error(p)
        else:
            try:
                with st.status("Roasting your deck…", expanded=True) as status:
                    st.write("PDF checked. Slide text extracted.")
                    report = run_analysis(
                        project_name.strip(),
                        description.strip(),
                        audience,
                        uploaded.name,
                        extraction,
                        progress=lambda msg: st.write(msg.removeprefix("✅ ").removeprefix("⚠️ ")),
                        judge_key=judge_key,
                    )
                    if report["status"] == "failed":
                        status.update(label="The selected judge could not finish", state="error")
                    else:
                        status.update(label="Review complete", state="complete")
            except GroqError as exc:
                st.error(exc.user_message)
                report = None

            if report and report["status"] == "failed":
                for key, message in report["judge_errors"].items():
                    st.error(f"{JUDGES[key]['name']}: {message}")
            elif report:
                st.session_state["report"] = report
                st.session_state.setdefault("report_history", []).append(report)
                st.switch_page("pages/4_Roast_Report.py")

    # ---------- Extraction preview ----------
    if extraction and extraction["ok"]:
        st.markdown("### Extracted slide text")
        for s in extraction["slides"]:
            label = f"Slide {s['slide_number']}" + ("" if s["has_text"] else "  no extractable text")
            with st.expander(label):
                st.text(s["text"] or "(nothing extracted)")
