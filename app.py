"""Slide Roast public routes."""
import streamlit as st

from utils.styles import inject_css

st.set_page_config(page_title="Slide Roast", layout="wide")
page = st.navigation(
    [
        st.Page("pages/home.py", title="Home", default=True),
        st.Page("pages/1_Upload.py", title="Upload Deck", url_path="Upload"),
        st.Page("pages/2_Report_History.py", title="Report History", url_path="Report_History"),
        st.Page("pages/3_About.py", title="About", url_path="About"),
        st.Page("pages/4_Roast_Report.py", title="Roast Report", url_path="Roast_Report"),
        st.Page("pages/5_AI_Slide_Fixer.py", title="AI Slide Fixer", url_path="Slide_Fixer"),
    ],
    position="hidden",
)
if page.url_path != "Upload":
    inject_css()
if page.url_path:
    with st.container(key="product_nav", horizontal=True):
        st.page_link("pages/home.py", label="slide roast.")
        st.page_link("pages/1_Upload.py", label="Upload Deck")
        st.page_link("pages/2_Report_History.py", label="Report History")
        st.page_link("pages/3_About.py", label="About")
        if st.session_state.get("report"):
            st.page_link("pages/5_AI_Slide_Fixer.py", label="AI Slide Fixer")
page.run()
