"""Product landing page with the live deck upload form."""
import streamlit as st

from utils.styles import icon, score_markup
from utils.upload_view import render_upload

LINKS = '<a href="#judges">Meet the Judges</a><a href="#how-it-works">How It Works</a><a href="#upload">Upload Deck</a>'
JUDGES = (
    ("investor", "flame", "The Skeptical Investor", "The money-minded one", 68,
     "Questions your business model, market size, competition, revenue strategy, and growth potential.",
     "Your market opportunity sounds exciting. Where is the evidence?"),
    ("professor", "cap", "The Bored Professor", "The detail detective", 75,
     "Checks your logic, clarity, technical depth, research, and whether your claims have evidence.",
     "Interesting claim. But you haven't proved it yet."),
    ("customer", "chat", "The Confused Customer", "The everyday human", 73,
     "Checks whether people understand the problem, your product, and why they should care.",
     "Wait... what exactly does your product do?"),
)

sample_rows = "".join(
    f'<div class="sample-row {key}"><span class="mini-icon">{icon(symbol)}</span>'
    f'<div><strong>{name}</strong><progress value="{score}" max="100" aria-label="{name} sample score"></progress></div>'
    f'<strong>{score}</strong></div>'
    for key, symbol, name, _, score, _, _ in JUDGES
)

# Keep the sticky navigation in its own Streamlit element so the hero can scroll.
st.html(f"""
<nav class="top-nav" id="landing-nav" aria-label="Main navigation">
  <a class="wordmark" href="#home">slide roast<span>.</span></a>
  <div class="desktop-links">{LINKS}</div>
  <a class="cta dark nav-cta" href="#upload">Get Roasted ↗</a>
  <details class="mobile-menu"><summary aria-label="Open navigation">{icon('menu')}</summary>
  <div>{LINKS}<a href="#upload">Get Roasted ↗</a></div></details>
</nav>
""" + """
<script>
{
    const nav = document.getElementById("landing-nav");
    nav.onclick = (event) => {
        const link = event.target.closest(".mobile-menu a");
        if (link) link.closest("details").open = false;
    };
}
</script>
""", unsafe_allow_javascript=True)

st.html(f"""
<section class="hero" id="home">
  <div class="hero-copy">
    <p class="badge">✦ Your brutally honest AI pitch panel</p>
    <h1>Your pitch deck needs a little <em>tough love.</em></h1>
    <p class="lead">Three AI judges. Three very different opinions. One pitch deck that's about to get a reality check.</p>
    <div class="cta-row"><a class="cta dark" href="#upload">Roast My Deck ↗</a>
    <a class="cta" href="#sample-report">See Sample Report</a></div>
  </div>
  <article class="sample panel" id="sample-report">
    <div class="sample-heading"><div><p class="eyebrow">Sample Roast Report</p><h2>Your pitch results</h2></div>
    <span class="mini-icon yellow">{icon('spark')}</span></div>
    <div class="sample-score">{score_markup(72)}
    <div><p class="eyebrow">Overall score</p><h3>Room to improve!</h3><p>A sample score to show how your report will look.</p></div></div>
    <div class="sample-rows">{sample_rows}</div>
    <p class="sample-note">Illustrative scores. Your report reflects the judge you choose.</p>
  </article>
</section>
""")

judge_cards = "".join(
    f'<article class="judge-card {key}"><div class="judge-card-top"><span class="mini-icon">{icon(symbol)}</span>'
    f'<span class="badge">{badge}</span></div><h3>{name}</h3><p>{description}</p>'
    f'<div class="quote"><p class="eyebrow">What they might say</p><blockquote>“{quote}”</blockquote></div></article>'
    for key, symbol, name, badge, _, description, quote in JUDGES
)

st.html(f"""
<section class="marketing-section" id="judges">
  <header><h2>Three judges. Three ways to get humbled.</h2>
  <p>Each judge looks at your deck from a completely different perspective.</p></header>
  <div class="three-grid">{judge_cards}</div>
  <p class="center"><a class="cta" href="#upload">Choose your judge ↗</a></p>
</section>
<section class="marketing-section" id="how-it-works">
  <header><h2>From upload to ouch.</h2><p>Getting honest feedback should be the easiest part of building your startup.</p></header>
  <div class="three-grid">
    <article class="panel step"><span>01</span><h3>Upload your deck</h3><p>Drop in your PDF pitch deck. No complicated setup.</p></article>
    <article class="panel step"><span>02</span><h3>Choose your judge</h3><p>Pick the personality you want to examine your pitch.</p></article>
    <article class="panel step"><span>03</span><h3>Get roasted</h3><p>Receive scores, honest feedback, and actionable fixes.</p></article>
  </div>
  <p class="center">Use the slide fixer to rewrite a weak slide before your next pitch.</p>
</section>
<section class="marketing-section">
  <header><h2>From weak pitch to stronger story.</h2><p>See how actionable feedback turns vague claims into clearer arguments.</p></header>
  <div class="two-grid">
    <article class="panel investor"><p class="eyebrow">Before the roast · Example</p><blockquote>“Our startup targets a massive market and will grow rapidly.”</blockquote><p>Vague market claim. No defined customer segment or evidence.</p></article>
    <article class="panel professor"><p class="eyebrow">After the fix · Example</p><blockquote>“We initially target [specific customer segment] experiencing [validated problem], with market size and demand to be supported by cited research.”</blockquote><p>The rewrite identifies what evidence you still need.</p></article>
  </div>
</section>
<section class="marketing-section">
  <header><h2>Why not just ask a chatbot?</h2><p>Slide Roast packages pitch-deck analysis into a focused, repeatable workflow.</p></header>
  <div class="two-grid">
    <article class="panel"><h3>General-purpose chatbot</h3><p>Flexible feedback when you supply the deck, evaluation criteria, and follow-up instructions.</p></article>
    <article class="panel lavender"><h3>Slide Roast</h3><p>Choose a judge, compare consistently weighted scores, find the slides that need attention, and rewrite a slide from the same report.</p></article>
  </div>
</section>
<div id="upload"></div>
""")

with st.container(key="upload_panel"):
    render_upload()

st.html("""
<section class="final-cta lavender">
  <h2>Ready to face the judges?</h2><p>Better to get roasted here than during your actual pitch.</p>
  <a class="cta dark" href="#upload">Roast My Deck ↗</a>
</section>
<div class="site-footer" id="privacy">
  <div><a class="wordmark" href="#home">slide roast<span>.</span></a><p>Better pitches start with better feedback.</p></div>
  <div class="footer-links"><a href="#home">Home</a><a href="#judges">Meet the Judges</a><a href="#how-it-works">How It Works</a>
  <a href="#upload">Upload Deck</a><a href="#privacy">Privacy</a></div>
  <p class="privacy-line">PDFs are processed in memory. Groq receives extracted text for review and for slide rewrites you request. Reports stay in the current session.</p>
  <p class="privacy-line">© 2026 Slide Roast.</p>
</div>
""")
with st.container(key="footer_pages", horizontal=True):
    st.page_link("pages/3_About.py", label="About")
    st.page_link("pages/2_Report_History.py", label="Report History")
