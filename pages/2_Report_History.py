"""Reports generated in this Streamlit session."""
import streamlit as st

from prompts.judges import JUDGES
from utils.helpers import esc
from utils.styles import card

st.title("Your Past Roasts")
st.write("Because great pitches aren't built in one try.")
st.caption("Reports are available for the current session.")

history = st.session_state.get("report_history", [])
if not history:
    st.info("No roasts yet. Your first pitch deck is waiting.")
    if st.button("Roast Your First Deck", type="primary"):
        st.switch_page("pages/1_Upload.py")

for index in reversed(range(len(history))):
    report = history[index]
    judges = ", ".join(JUDGES[key]["name"] for key in report["judges"])
    score = (report.get("scoring") or {}).get("overall_score")
    score_label = f"{score:g} / 100" if score is not None else "Score unavailable"
    card(
        f"<h3>{esc(report['project_name'])}</h3>"
        f"<p>{esc(report['filename'])} · {esc(report['created_at'][:10])} · {esc(judges)}</p>"
        f"<strong>{score_label}</strong>"
    )
    if st.button("View Report", key=f"view_past_roast_{index}"):
        st.session_state["report"] = report
        st.switch_page("pages/4_Roast_Report.py")
