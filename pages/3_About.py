"""About the evaluation workflow and its limits."""
import streamlit as st

st.title("About Slide Roast")
st.write("Slide Roast helps founders, students, and hackathon teams prepare for the questions their pitch deck will face.")
st.html("""
<div class="two-grid">
<article class="panel lavender"><h3>One deck, three perspectives</h3><p>Pick an investor, professor, or customer. The selected judge evaluates your deck, and Slide Roast calculates your overall score from the weighted category scores.</p></article>
<article class="panel"><h3>Feedback you can use</h3><p>Read prioritized improvements, see the evidence behind each finding, and draft replacement text for an individual slide.</p></article>
</div>
""")
st.subheader("Privacy and scope")
st.write("PDFs are processed in memory. Google’s Groq API receives extracted text for review and for rewrites you request. Reports and edits stay in the current Streamlit session.")
if st.button("Upload a deck", type="primary"):
    st.switch_page("pages/1_Upload.py")
