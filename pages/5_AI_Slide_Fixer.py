"""Dedicated studio for the active deck."""
import streamlit as st

from utils.slide_fixer_view import render_slide_fixer

report = st.session_state.get("report")
if report:
    render_slide_fixer(report)
else:
    st.title("AI Slide Fixer")
    st.info("No presentation uploaded yet. Upload a pitch deck to start improving your slides.")
    st.page_link("pages/1_Upload.py", label="Upload a deck")
