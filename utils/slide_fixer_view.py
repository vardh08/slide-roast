"""Text-only slide improvement UI."""
import streamlit as st

from prompts.judges import JUDGES
from services.gemini_service import GeminiError, REWRITE_STYLES, generate_slide_fix


def _remember_edit(entry: dict, key: str) -> None:
    entry["edited"] = st.session_state[key]


def render_slide_fixer(report: dict) -> None:
    st.markdown("## AI Slide Fixer")
    st.badge("AI-powered text improvement", color="violet")
    st.subheader("Make every word of your pitch count.")
    st.caption("Select a slide, choose how you want to improve it, and let AI turn weak writing into clearer, stronger presentation content.")

    slides = {slide["slide_number"]: slide for slide in report.get("slides", [])}
    if not slides:
        st.info("No presentation uploaded yet. Upload a pitch deck to start improving your slides.")
        return
    titles = {item["slide_number"]: item["slide_title"] for item in report.get("slide_feedback", [])}
    st.markdown("### Choose a slide to improve")
    number = st.selectbox(
        "Slide to fix", list(slides), index=None,
        format_func=lambda n: f"Slide {n} · {titles.get(n) or slides[n]['text'].splitlines()[0][:85] if slides[n]['text'].strip() else 'No readable text'}",
        key="fixer_slide_number",
    )
    if number is None or number not in slides:
        st.info("Select a slide to begin.")
        return
    slide = slides[number]
    if not slide["has_text"] or not slide["text"].strip():
        st.info("No readable text found on this slide. It may be scanned or image-based.")
        return

    controls, perspective = st.columns(2)
    with controls:
        style = st.radio("How should we improve this slide?", list(REWRITE_STYLES), horizontal=True, key="rewrite_style")
        st.caption(REWRITE_STYLES[style])
    with perspective:
        default_judge = next((key for key, review in report.get("judges", {}).items() if review and key in JUDGES), None)
        choices = [default_judge, *(key for key in JUDGES if key != default_judge)]
        judge = st.selectbox("Judge perspective", choices,
                             format_func=lambda key: JUDGES[key]["name"] if key else "General audience",
                             key=f"rewrite_judge_{id(report)}")

    fixes = report.setdefault("slide_fixes", {})
    entry = fixes.get(str(number))
    if entry and "generated" not in entry:
        entry["generated"] = entry["edited"] = f"{entry['title']}\n\n{entry['body']}"
    editor_key = f"slide_edit_{id(report)}_{number}"
    manually_edited = bool(entry and entry.get("edited", entry["generated"]) != entry["generated"])
    confirmed = not manually_edited
    if manually_edited:
        st.warning("Regenerating replaces your edited text after a successful rewrite.")
        confirmed = st.checkbox("Replace my edits when regenerating", key=f"rewrite_confirm_{editor_key}")
    if st.button("Regenerate Rewrite" if entry else "Rewrite This Slide", key="generate_slide_fix",
                 type="secondary" if entry else "primary", disabled=not confirmed):
        try:
            with st.spinner("Improving your slide…"):
                fix = generate_slide_fix(report, number, style=style, judge_key=judge)
            generated = f"{fix['title']}\n\n{fix['body']}"
            entry = {**fix, "generated": generated, "edited": generated}
            fixes[str(number)] = entry
            st.session_state[editor_key] = generated
        except GeminiError as exc:
            st.error(exc.user_message)

    with st.container(key="slide_rewrite_panel"):
        before, after = st.columns(2)
        with before, st.container(border=True):
            st.markdown("### Original Text")
            st.caption("Your slide before improvement")
            st.code(slide["text"], language=None, wrap_lines=True)
        with after, st.container(border=True):
            st.markdown("### Improved Text")
            st.caption("Your slide after AI refinement")
            if entry:
                if editor_key not in st.session_state:
                    st.session_state[editor_key] = entry["edited"]
                st.text_area("Edit the improved text", key=editor_key, height=240,
                             on_change=_remember_edit, args=(entry, editor_key))
                # Both actions read the editor directly, including a change that is still focused.
                st.html("""
                <button type="button" id="slide-copy-text">Copy Text</button>
                <button type="button" id="slide-download-text" data-slide="SLIDE_NUMBER">Download Text</button>
                <span id="slide-copy-result" role="status"></span>
                <script>{
                    const button = document.getElementById("slide-copy-text");
                    button.onclick = async () => {
                        const status = document.getElementById("slide-copy-result");
                        const editor = button.closest(".st-key-slide_rewrite_panel").querySelector("textarea");
                        try {
                            await navigator.clipboard.writeText(editor.value);
                            status.textContent = " Copied";
                        } catch {
                            editor.focus();
                            editor.select();
                            status.textContent = " Text selected. Press Ctrl+C or Command+C.";
                        }
                    };
                    const download = document.getElementById("slide-download-text");
                    download.onclick = () => {
                        const editor = download.closest(".st-key-slide_rewrite_panel").querySelector("textarea");
                        const url = URL.createObjectURL(new Blob([editor.value], {type: "text/plain;charset=utf-8"}));
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = "slide-" + download.dataset.slide + "-improved.txt";
                        link.click();
                        setTimeout(() => URL.revokeObjectURL(url), 1000);
                    };
                }</script>
                """.replace("SLIDE_NUMBER", str(number)), unsafe_allow_javascript=True)
            else:
                st.info("Rewrite this slide to start editing.")
    if entry:
        with st.container(border=True):
            st.markdown("### What Changed?")
            for change in entry["changes"]:
                st.text(f"• {change}")
            st.markdown("### Suggestions to Make This Slide Stronger")
            if entry["evidence_to_add"]:
                for suggestion in entry["evidence_to_add"]:
                    st.text(f"• {suggestion}")
            else:
                st.caption("No additional evidence was suggested.")
