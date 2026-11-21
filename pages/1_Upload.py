"""Direct link to the deck upload form."""
import streamlit as st

from utils.styles import inject_css
from utils.upload_view import render_upload

st.set_page_config(page_title="Upload Deck · Slide Roast", layout="wide")
inject_css()
with st.container(key="upload_panel"):
    render_upload(standalone=True)
