"""Shared design system and presentation primitives for Slide Roast."""
from urllib.parse import quote

import streamlit as st

COLORS = {"text": "#24231F", "muted": "#625d58", "border": "#E8E4DD"}

ICON_PATHS = {
    "flame": '<path d="M12 22a7 7 0 0 0 7-7c0-3-2-5-4-7 0 3-2 4-2 4 0-4-2-7-4-9 0 4-4 7-4 12a7 7 0 0 0 7 7Z"/>',
    "cap": '<path d="m2 9 10-5 10 5-10 5-10-5Zm4 2v6c4 3 8 3 12 0v-6m4-2v7"/>',
    "chat": '<path d="M21 11a8 8 0 0 1-8 8H8l-5 3 1-6a8 8 0 0 1-1-5 8 8 0 0 1 8-8h2a8 8 0 0 1 8 8Z"/><path d="M8 11h8"/>',
    "upload": '<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
    "file": '<path d="M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10Zm0 0v7h7M8 14h8m-8 3h6"/>',
    "spark": '<path d="M12 2c0 6 4 10 10 10-6 0-10 4-10 10 0-6-4-10-10-10 6 0 10-4 10-10Z"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
}


def icon(name: str) -> str:
    return (
        '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">{ICON_PATHS[name]}</svg>'
    )


def score_markup(score: float) -> str:
    value = f"{score:.0f}"
    return (
        f'<div class="score-ring" role="img" aria-label="{value} out of 100" style="--score:{value}%">'
        f'<div><strong>{value}</strong><small>/ 100</small></div></div>'
    )


def inject_css() -> None:
    deck_icons = []
    for name in ("file", "flame", "cap", "chat"):
        svg = icon(name).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
        if name != "file":
            svg = svg.replace('stroke="currentColor"', 'stroke="#55515B"')
        deck_icons.append(f"--deck-{name}:url('data:image/svg+xml,{quote(svg, safe='')}')")
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=optional');
/* upload-icons */
:root {
  --cream:#FAF9F6; --white:#FFF; --ink:#24231F; --muted:#625D58; --border:#E8E4DD;
  --lilac:#B58ACB; --lilac-ink:#70418A; --lavender:#EAE0F2; --pink:#F6DAD8;
  --plum:#30213F; --plum-light:#483156; --violet-wash:#F5EEF9; --cream-shade:#F6EEE2;
  --green:#DDEBDD; --yellow:#F7EABB; --font:"Plus Jakarta Sans",system-ui,sans-serif;
  --shadow:0 18px 45px rgba(63,45,34,.075);
}
html {scroll-behavior:smooth}
.stApp {
  background:radial-gradient(ellipse at 92% 0%,#f1e7f6 0%,transparent 56%),
    radial-gradient(ellipse at 0% 28%,var(--cream-shade) 0%,transparent 44%),var(--cream);
  color:var(--ink)
}
.stApp :is(p,button,input,textarea,summary,a,li),.stApp :is(h1,h2,h3,h4) {font-family:var(--font)}
.stApp :is(h1,h2,h3,h4) {color:var(--ink);font-weight:800;letter-spacing:-.045em}
.stApp h1 {font-size:clamp(2.5rem,5.8vw,5.55rem);line-height:1.02}
.stApp h2 {font-size:clamp(1.85rem,4vw,3.4rem);line-height:1.12}
.stApp h3 {font-size:clamp(1.1rem,2vw,1.45rem);line-height:1.25}
.stApp p {line-height:1.65;color:var(--muted)}
#MainMenu,footer,[data-testid="stDecoration"],[data-testid="stHeader"],[data-testid="stSidebar"] {display:none}
[data-testid="stMainBlockContainer"] {max-width:1260px;padding:0 clamp(18px,4vw,54px) 44px}
[data-testid="stMain"] {scroll-behavior:smooth}
[data-testid="stElementContainer"]:has(.top-nav) {overflow:visible}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.top-nav) {
  position:sticky;top:0;z-index:100
}
.top-nav {position:relative;display:flex;align-items:center;justify-content:space-between;gap:18px;background:var(--cream);
  border-bottom:1px solid var(--border);min-height:78px;padding:10px 0}
.wordmark,.top-nav .wordmark {font-weight:800;font-size:1.45rem;letter-spacing:-.08em;color:var(--ink);text-decoration:none;white-space:nowrap}
.wordmark span {color:var(--lilac-ink)}
.desktop-links,.footer-links {display:flex;align-items:center;gap:clamp(12px,2.4vw,32px);flex-wrap:wrap}
.desktop-links a,.footer-links a,.mobile-menu a {font-size:.91rem;font-weight:700;color:var(--muted);text-decoration:none}
.desktop-links a:hover,.footer-links a:hover,.mobile-menu a:hover {color:var(--lilac-ink);text-decoration:underline}
.mobile-menu {display:none}
.cta-row {display:flex;gap:12px;flex-wrap:wrap}
.stApp a.cta {display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:10px 20px;
  border-radius:99px;border:1px solid var(--border);font-size:.9rem;font-weight:800;color:var(--ink);background:white;
  text-decoration:none;transition:transform .2s,background .2s}
.stApp a.cta.dark,[data-testid="stBaseButton-primary"]:not(:disabled) {background:var(--plum);border-color:var(--plum);color:white}
.stApp a.cta:hover {transform:translateY(-2px);background:var(--lavender)}
.stApp a.cta.dark:hover,[data-testid="stBaseButton-primary"]:hover:not(:disabled) {background:var(--plum-light);border-color:var(--plum-light);color:white}
.stApp :is(a,button,input,textarea,summary,[role="combobox"]):focus-visible {outline:2px solid var(--lilac-ink);outline-offset:3px}
.hero {display:grid;grid-template-columns:minmax(0,1.12fr) minmax(0,1fr);align-items:center;
  gap:clamp(24px,6vw,86px);padding:clamp(48px,8vw,108px) 0}
.hero h1 {max-width:10ch;margin:12px 0 16px}
.hero h1 em {font-style:normal;color:var(--lilac-ink);background:linear-gradient(transparent 79%,#e6cbed 79%)}
.hero .lead {max-width:34ch;font-size:1.12rem;margin:0 0 24px}
.badge,.stApp p.badge {display:inline-block;border-radius:99px;padding:6px 12px;background:var(--yellow);
  color:var(--ink);font-size:.78rem;font-weight:800;margin:0}
.panel,.sr-card {padding:clamp(20px,3vw,34px);border:1px solid var(--border);border-radius:28px;background:white;overflow-wrap:anywhere}
.sample {background:linear-gradient(145deg,var(--white) 45%,var(--violet-wash));box-shadow:var(--shadow)}
.sample-heading,.sample-score,.judge-card-top {display:flex;align-items:center;justify-content:space-between;gap:14px}
.sample-heading h2 {font-size:1.55rem;margin:0}
.eyebrow,.stApp p.eyebrow {font-size:.66rem;text-transform:uppercase;letter-spacing:.12em;font-weight:800;margin:0 0 4px}
.mini-icon {width:44px;height:44px;flex:none;display:inline-grid;place-items:center;background:white;border-radius:14px;color:var(--ink)}
.mini-icon svg,.mobile-menu svg {width:22px;height:22px}
.yellow {background:var(--yellow)}
.sample-score {justify-content:flex-start;background:var(--violet-wash);border:1px solid #e5d6ee;border-radius:20px;margin:18px 0;padding:16px}
.sample-score h3,.sample-score p {margin:0}
.sample-score p:not(.eyebrow) {font-size:.79rem}
.score-ring {width:112px;aspect-ratio:1;flex:none;border-radius:50%;display:grid;place-items:center;
  background:conic-gradient(var(--lilac) var(--score),var(--lavender) 0)}
.score-ring > div {width:84%;height:84%;display:grid;place-content:center;text-align:center;border-radius:50%;background:white}
.score-ring strong {font-size:1.95rem;line-height:1.1;font-weight:800;font-variant-numeric:tabular-nums}
.score-ring small {color:var(--muted)}
.sample-rows {display:grid;gap:12px}
.sample-row {display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:10px;font-size:.8rem}
.sample-row .mini-icon {width:36px;height:36px;background:var(--tint)}
.sample-row .mini-icon svg {width:18px;height:18px}
.sample-row progress {display:block;width:100%;margin-top:6px;height:7px;border:0;border-radius:99px;background:var(--cream);overflow:hidden}
.sample-row progress::-webkit-progress-bar {background:var(--cream)}
.sample-row progress::-webkit-progress-value {background:var(--tint)}
.sample-row progress::-moz-progress-bar {background:var(--tint)}
.stApp .sample-note {font-size:.74rem;margin:16px 0 0}
.investor {--tint:var(--pink)} .professor {--tint:var(--green)} .customer {--tint:var(--yellow)}
.panel.investor,.panel.professor,.judge-card,.sr-card.investor,.sr-card.professor,.sr-card.customer {background:var(--tint)}
.lavender {background:var(--lavender)}
.marketing-section {margin:clamp(56px,8vw,100px) 0}
.marketing-section > header,.center,.upload-heading,.final-cta {text-align:center}
.marketing-section > header {margin-bottom:28px}
.marketing-section > header p {margin-top:8px}
.three-grid,.two-grid {display:grid;gap:18px}
.three-grid {grid-template-columns:repeat(3,minmax(0,1fr))}
.two-grid {grid-template-columns:repeat(2,minmax(0,1fr))}
.judge-card {border-radius:28px;padding:clamp(18px,2.5vw,30px);display:flex;flex-direction:column;transition:transform .2s,box-shadow .2s}
.judge-card:hover {transform:translateY(-4px);box-shadow:var(--shadow)}
.judge-card-top {margin-bottom:12px;justify-content:space-between}
.judge-card .badge {background:#ffffffc7;padding:5px 9px;font-size:.68rem;text-align:center}
.quote {margin-top:auto;background:#ffffffa6;padding:14px;border-radius:16px}
.stApp blockquote {margin:8px 0;font-weight:650;font-size:1rem;color:var(--ink)}
.step > span {font-size:2.1rem;color:var(--lilac-ink);font-weight:800}
.center {margin-top:24px}
#home,#judges,#how-it-works,#sample-report,#upload,#privacy {scroll-margin-top:98px}
.final-cta {
  background:linear-gradient(125deg,var(--plum),var(--plum-light));border-radius:32px;
  padding:clamp(18px,4vw,46px);box-shadow:var(--shadow)
}
.stApp .final-cta h2 {color:var(--white)}
.stApp .final-cta p {color:#EEE2F3}
.stApp .final-cta a.cta.dark {background:#F3E0FC;border-color:#F3E0FC;color:var(--plum)}
.stApp .final-cta a.cta.dark:hover {background:var(--white);border-color:var(--white);color:var(--plum)}
.stApp .final-cta a.cta.dark:focus-visible {outline-color:var(--white)}
.st-key-upload_panel {--drop-height:286px;max-width:1150px;margin:0 auto;
  background:linear-gradient(135deg,var(--lavender),var(--violet-wash));border:1px solid #e1d2eb;
  border-radius:32px;padding:clamp(20px,4vw,48px)}
.st-key-upload_panel .upload-heading {margin-bottom:clamp(12px,2vw,24px)}
.st-key-upload_panel .upload-heading :is(h1,h2) {font-size:clamp(2rem,4.2vw,3rem);line-height:1.1;margin:0 0 10px}
.st-key-upload_panel .upload-heading p {font-size:1rem;margin:0}
.st-key-upload_panel [data-testid="stHorizontalBlock"] {gap:clamp(20px,3vw,36px)}
.st-key-upload_panel h3 {font-size:1.25rem;letter-spacing:-.035em}
.st-key-upload_panel [data-testid="stWidgetLabel"] p {font-size:.92rem;font-weight:700;color:var(--ink)}
.st-key-upload_panel :is([data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],
  [data-testid="stSelectbox"] [role="group"]) {
  background:var(--white);border:1px solid #cec0d7;border-radius:12px;min-height:48px;
}
.st-key-upload_panel :is([data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],
  [data-testid="stSelectbox"] [role="group"]):focus-within {border-color:var(--lilac-ink);box-shadow:0 0 0 2px #86549d37}
.st-key-upload_panel :is(input:not([type="radio"]),textarea) {font-size:1rem;color:var(--ink);background:transparent}
.st-key-upload_panel textarea {line-height:1.5}
.st-key-deck_dropzone {position:relative;min-width:0}
.st-key-deck_dropzone [data-testid="stFileUploaderDropzone"] {border:2px dashed var(--lilac);border-radius:24px;
  background:var(--white);transition:background .18s,border-color .18s}
.st-key-deck_dropzone [data-testid="stFileUploaderDropzone"]:is(:hover,:focus-within) {
  border-color:var(--lilac-ink);background:#fdfaff;
}
.st-key-deck_dropzone [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileUploaderDropzoneInstructions"]) {
  min-height:var(--drop-height);padding:0;
}
.st-key-deck_dropzone [data-testid="stFileUploaderDropzoneInstructions"] {visibility:hidden}
.st-key-deck_dropzone [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileUploaderDropzoneInstructions"])
  button[data-testid="stBaseButton-secondary"] {position:absolute;inset:0;width:100%;height:100%;opacity:0}
.st-key-deck_dropzone [data-testid="stElementContainer"]:has(.deck-drop-copy) {
  position:absolute;inset:0 0 auto;pointer-events:none;
}
.st-key-deck_dropzone:has([data-testid="stFileChips"]) .deck-drop-copy {display:none}
.deck-drop-copy {min-height:var(--drop-height);display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:5px;padding:14px;text-align:center;font-family:var(--font);color:var(--muted);font-size:.94rem}
.deck-drop-copy strong {font-size:1.16rem;color:var(--ink);font-weight:800}
.deck-drop-copy small {font-size:.79rem;line-height:1.4}
.deck-file-icon {display:block;width:54px;height:54px;margin-bottom:8px;border-radius:16px;
  background:var(--lavender) var(--deck-file) center / 28px no-repeat}
.deck-choose-pdf {background:var(--ink);color:white;border-radius:99px;padding:10px 17px;
  margin:6px 0 5px;font-weight:800;font-size:.87rem}
.st-key-deck_dropzone:has(button:focus-visible) .deck-choose-pdf {outline:2px solid var(--lilac-ink);outline-offset:3px}
.st-key-deck_dropzone [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChips"]) {
  border:1px solid #d5c7de;padding:14px;
}
.st-key-deck_dropzone [data-testid="stFileChip"] {min-width:0;background:#f5eff8;border-radius:12px}
.st-key-deck_dropzone button[aria-label="Add files"] {width:auto;min-height:44px;padding-inline:13px;gap:5px}
.st-key-deck_dropzone button[aria-label="Add files"]::after {content:"Replace PDF";font-size:.81rem;font-weight:700}
.final-cta {margin:clamp(48px,7vw,88px) 0}
.site-footer {border-top:1px solid var(--border);padding-top:28px;display:grid;grid-template-columns:1fr auto;align-items:start;gap:14px}
.site-footer .privacy-line {grid-column:1/-1;font-size:.85rem;margin:0}
.st-key-product_nav {padding:10px 0;border-bottom:1px solid var(--border);margin-bottom:22px}
.st-key-product_nav a,.st-key-footer_pages a {font-weight:750}
[data-testid="stFileUploaderDropzone"] {border:2px dashed #B58ACB;border-radius:20px;background:white;padding:clamp(16px,2.7vw,32px)}
[data-testid="stFileUploaderDropzone"]:focus-within {border-color:var(--lilac-ink)}
[data-testid="stExpander"] details {
  border:1px solid var(--border);background:white;border-radius:16px;
  /* Streamlit animates height in JS and leaves the element open until the animation finishes. */
  height:auto !important;overflow:visible !important;
}
[data-testid="stExpander"] details > [data-testid="stExpanderDetails"][inert] {display:none !important}
[data-testid="stExpander"] summary {
  background:#f3edf7;border-radius:15px;transition:background-color .18s ease;
}
[data-testid="stExpander"] details[open]:not(:has(> [data-testid="stExpanderDetails"][inert])) > summary {
  border-radius:15px 15px 0 0;
}
[data-testid="stExpander"] summary:focus-visible {outline-offset:-3px}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-secondary"] {min-height:44px;border-radius:99px;font-weight:800;padding-inline:18px}
.st-key-slide_rewrite_panel {background:white;border-color:var(--border);border-radius:22px}
.st-key-slide_rewrite_panel pre {white-space:pre-wrap;overflow-wrap:anywhere}
.st-key-slide_rewrite_panel :is(#slide-copy-text,#slide-download-text) {
  background:white;color:var(--ink);border:1px solid var(--border);border-radius:99px;
  min-height:44px;padding:8px 16px;margin:0 6px 6px 0;font-weight:700;cursor:pointer;
}
.st-key-slide_rewrite_panel :is(#slide-copy-text,#slide-download-text):hover {background:var(--lavender)}
.st-key-slide_visual_workspace [data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px}
.st-key-slide_visual_workspace [data-testid="stImage"] img {border:1px solid var(--border);border-radius:8px}
.st-key-studio_nav [class*="st-key-studio_thumb_card_"] {position:relative;gap:4px}
.st-key-studio_nav [class*="st-key-studio_thumb_card_"] [data-testid="stElementContainer"]:has([data-testid="stButton"]) {position:static}
.st-key-studio_nav [class*="st-key-studio_thumb_card_"] button {position:static;min-height:36px}
.st-key-studio_nav [class*="st-key-studio_thumb_card_"] button::before {content:"";position:absolute;inset:0;z-index:1}
.st-key-studio_nav [class*="st-key-studio_thumb_card_"]:has(button[kind="primary"]) img {border-color:var(--lilac-ink)}
.st-key-studio_nav [class*="st-key-studio_thumb_card_"] button[kind="primary"] {background:#f0e6f6;color:var(--ink);border-color:var(--lilac-ink)}
.sr-muted,.sr-label {color:var(--muted)}
.sr-pill {display:inline-block;padding:3px 9px;border-radius:99px;background:#efebe6;margin-right:8px;font-size:.75rem;font-weight:800}
.sr-sev-high {background:#FDE2E1;color:#8D2424}
.sr-sev-medium {background:#FEF2C6;color:#674900}
.sr-sev-low {background:#E1F3E7;color:#215B3B}
.sr-verdict {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.sr-verdict section,.sr-question {background:white;border:1px solid var(--border);padding:16px;border-radius:16px;margin-bottom:8px}
.sr-weakness {margin:12px 0}.sr-label {font-weight:800;margin-right:8px}.sr-judge-name {margin-top:0}
.report-score {display:flex;align-items:center;gap:clamp(16px,4vw,40px)}
.sr-card:has(.report-score) {background:linear-gradient(120deg,var(--white) 48%,var(--violet-wash))}
.report-score h3,.report-score p {margin:0}
.sr-card .score-ring {margin-bottom:12px}
.review-score-list {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:12px}
.review-score-row,.review-feedback {
  min-width:0;background:var(--white);border:1px solid var(--border);border-radius:16px;padding:14px 16px;
}
.review-score-row {transition:border-color .18s ease}
.review-score-row:hover {border-color:var(--lilac)}
.review-score-label {display:flex;justify-content:space-between;align-items:baseline;gap:6px 12px;flex-wrap:wrap;color:var(--ink)}
.review-score-label strong {font-size:1rem;font-weight:800}
.review-score-label span {font-weight:800;font-variant-numeric:tabular-nums}
.review-score-track {height:8px;margin:10px 0 8px;border-radius:99px;overflow:hidden;background:var(--lavender)}
.review-score-track > div {height:100%;border-radius:inherit;background:var(--lilac-ink)}
.review-score-row small {color:var(--muted);line-height:1.45}
.review-score-row small b {color:var(--lilac-ink)}
.review-score-total {display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;
  padding:12px 16px;background:var(--violet-wash);border:1px solid var(--border);border-radius:12px;color:var(--plum)}
.review-score-bands {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,145px),1fr));gap:8px}
.review-score-bands > div {display:grid;gap:4px;padding:9px 12px;border-radius:10px;background:var(--violet-wash);color:var(--muted)}
.review-score-bands b {color:var(--plum);font-variant-numeric:tabular-nums}
.review-feedback {border-inline-start:3px solid var(--lilac);overflow-wrap:anywhere}
.review-feedback.review-strength {border-inline-start-color:#719479}
.review-feedback.review-priority {border-inline-start-color:#9b82aa}
.review-feedback h3 {margin:0;font-size:1rem}
.review-feedback ul {margin:8px 0 0;padding-inline-start:21px}
.review-feedback li {line-height:1.55;margin:3px 0}
[class*="st-key-review_disclosures_"] [data-testid="stExpander"] summary {padding:12px 16px}
[class*="st-key-review_disclosures_"] [data-testid="stExpander"] summary > span:first-child {
  display:flex;width:100%;flex-direction:row-reverse;justify-content:space-between;gap:12px
}
[class*="st-key-review_disclosures_"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] {flex:1;min-width:0}
[class*="st-key-review_disclosures_"] [data-testid="stExpander"] summary:hover {background:var(--lavender)}
.st-key-review_disclosures_slides summary strong {font-weight:800}
.st-key-review_disclosures_slides [data-testid="stExpander"] h4 {
  color:var(--ink);font-size:1.04rem;font-weight:800;
}
.st-key-review_disclosures_slides .slide-feedback-issue {
  padding:12px 14px;border:1px solid var(--border);border-radius:12px;background:var(--white);
  color:var(--ink);overflow-wrap:anywhere;
}
.st-key-review_disclosures_slides .slide-feedback-issue p {margin:5px 0 0;color:var(--muted)}
.st-key-review_disclosures_slides .slide-feedback-issue p b {color:var(--ink);font-weight:800}
.st-key-review_disclosures_slides .review-feedback h3 {color:var(--ink);font-weight:800}
.st-key-report_priority_improvements,.st-key-review_disclosures_slides {
  --priority-high:#D65353;--priority-medium:#C39B26;--priority-low:#5B9D72;
}
:is(.st-key-report_priority_improvements,.st-key-review_disclosures_slides)
  :is(.sr-card,.slide-feedback-issue,details):has(.sr-sev-low) {
  --priority-line:var(--priority-low);--priority-wash:#F5FCF7;
}
:is(.st-key-report_priority_improvements,.st-key-review_disclosures_slides)
  :is(.sr-card,.slide-feedback-issue,details):has(.sr-sev-medium) {
  --priority-line:var(--priority-medium);--priority-wash:#FFFBEB;
}
:is(.st-key-report_priority_improvements,.st-key-review_disclosures_slides)
  :is(.sr-card,.slide-feedback-issue,details):has(.sr-sev-high) {
  --priority-line:var(--priority-high);--priority-wash:#FFF5F4;
}
.st-key-report_priority_improvements .sr-card:has(:is(.sr-sev-high,.sr-sev-medium,.sr-sev-low)),
.st-key-review_disclosures_slides details:has(:is(.sr-sev-high,.sr-sev-medium,.sr-sev-low)) > summary,
.st-key-review_disclosures_slides .slide-feedback-issue:has(:is(.sr-sev-high,.sr-sev-medium,.sr-sev-low)) {
  border-inline-start:3px solid var(--priority-line);
  background:var(--priority-wash);
}
.st-key-review_disclosures_slides .report-priority-count {
  display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;
  padding:10px 14px;border:1px solid var(--border);border-radius:12px;background:var(--white);color:#8D2424;
}
.st-key-review_disclosures_slides .report-priority-count strong {border-inline-start:3px solid var(--priority-high);padding-inline-start:8px}
.report-score .score-ring {margin-bottom:0}
.st-key-judge_personality [data-testid="stRadioGroup"] {--judge-selected:#A77CC4;display:grid;gap:9px}
.st-key-judge_personality [data-testid="stRadioGroup"] > div {--judge-icon:var(--deck-flame);
  position:relative;display:grid;grid-template-columns:36px minmax(0,1fr) 18px;column-gap:12px;row-gap:3px;
  min-width:0;min-height:68px;padding:12px 15px;background:#FFFFFF;border:1px solid #E5E1E8;
  border-radius:12px;cursor:pointer;transition:border-color .18s,box-shadow .18s;
}
.st-key-judge_personality [data-testid="stRadioGroup"] > div:nth-child(2) {--judge-icon:var(--deck-cap)}
.st-key-judge_personality [data-testid="stRadioGroup"] > div:nth-child(3) {--judge-icon:var(--deck-chat)}
.st-key-judge_personality [data-testid="stRadioGroup"] > div::before {
  content:"";grid-column:1;grid-row:1 / span 2;align-self:center;width:36px;height:36px;border-radius:9px;
  background:#F6F5F7 var(--judge-icon) center / 20px no-repeat;
}
.st-key-judge_personality [data-testid="stRadioGroup"] > div::after {
  content:"";grid-column:3;grid-row:1 / span 2;align-self:center;justify-self:end;width:18px;height:18px;
  display:grid;place-items:center;border:1px solid #A49CAA;background:#FFFFFF;border-radius:50%;pointer-events:none;
}
.st-key-judge_personality [data-testid="stRadioOption"] {grid-column:2;grid-row:1;align-self:end;position:static;
  display:block;margin:0;padding:0;min-width:0;color:#242424}
.st-key-judge_personality [data-testid="stRadioOption"]::after {position:absolute;inset:0;content:"";border-radius:inherit}
.st-key-judge_personality [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {display:none}
.st-key-judge_personality [data-testid="stRadioOption"] p {font-size:.9375rem;font-weight:600;line-height:1.3;margin:0;color:#242424}
.st-key-judge_personality [data-testid="stRadioCaption"] {grid-column:2;grid-row:2;align-self:start;margin:0;min-width:0}
.st-key-judge_personality [data-testid="stRadioCaption"] p {font-size:.8125rem;line-height:1.4;margin:0;color:#77717D}
.st-key-judge_personality [data-testid="stRadioGroup"] > div:hover {border-color:#C8B4D9}
.st-key-judge_personality [data-testid="stRadioGroup"] > div:has(input:checked) {
  border-color:var(--judge-selected);box-shadow:0 0 0 2px rgba(167,124,196,.10);
}
.st-key-judge_personality [data-testid="stRadioGroup"] > div:has(input:checked)::after {
  content:"✓";font:700 .75rem/1 var(--font);background:var(--judge-selected);color:white;border-color:var(--judge-selected);
}
.st-key-judge_personality [data-testid="stRadioGroup"] > div:has(input:focus-visible) {outline:2px solid var(--judge-selected);outline-offset:2px}
.st-key-deck_submit {width:min(100%,320px);margin:clamp(8px,2vw,16px) auto 0;text-align:center}
.stApp .st-key-deck_submit button {
  min-height:58px;transition:transform .18s;
}
.stApp .st-key-deck_submit button p {font-size:1.0625rem;font-weight:800;line-height:1.25}
.stApp .st-key-deck_submit button:not(:disabled) {background:var(--plum);border-color:var(--plum);color:#fff}
.stApp .st-key-deck_submit button:not(:disabled) p {color:#fff}
.stApp .st-key-deck_submit button:not(:disabled):is(:hover,:active,:focus) {
  background:var(--plum-light);border-color:var(--plum-light);
}
.st-key-deck_submit button:hover:not(:disabled) {transform:translateY(-2px)}
.st-key-deck_submit button:disabled {background:#ded3e4;color:#5d5262;border-color:#c4b6ce}
.stApp .st-key-deck_submit button:disabled p {color:#5d5262}
.st-key-deck_submit [data-testid="stCaptionContainer"] {text-align:center}

@keyframes reveal {from {opacity:0;transform:translateY(9px)} to {opacity:1;transform:translateY(0)}}
.hero-copy,.sample {animation:reveal .35s ease-out both}
.sample {animation-delay:.08s}
@media(max-width:1023px) {.hero {gap:26px}.judge-card-top {gap:7px;flex-wrap:wrap}}
@media(max-width:960px) {
  .st-key-slide_visual_workspace [data-testid="stHorizontalBlock"] {flex-direction:column}
  .st-key-slide_visual_workspace [data-testid="stColumn"] {width:100%;flex:1 1 auto}
}
@media(max-width:767px) {
  .desktop-links,.nav-cta {display:none!important}.mobile-menu {display:block}
  .mobile-menu summary {display:grid;place-items:center;list-style:none;min-width:44px;min-height:44px;cursor:pointer}
  .mobile-menu summary::-webkit-details-marker {display:none}
  .mobile-menu > div {position:absolute;top:100%;right:0;min-width:190px;display:grid;gap:12px;
    padding:16px;background:white;border:1px solid var(--border);border-radius:16px;box-shadow:var(--shadow)}
  .top-nav {min-height:65px}
  .hero,.three-grid,.two-grid,.sr-verdict,.site-footer {grid-template-columns:minmax(0,1fr)}
  .hero {padding:36px 0 18px}
  .hero h1 {max-width:13ch}
  .st-key-upload_panel [data-testid="stHorizontalBlock"],.st-key-slide_rewrite_panel [data-testid="stHorizontalBlock"] {flex-direction:column}
  .st-key-upload_panel [data-testid="stColumn"],.st-key-slide_rewrite_panel [data-testid="stColumn"] {width:100%;flex:1 1 auto}
  .st-key-upload_panel {--drop-height:252px;border-radius:24px}
  .st-key-deck_submit {width:100%}
}
@media(max-width:410px) {.cta-row a {flex:1 1 100%}.score-ring {width:88px}.score-ring strong {font-size:1.5rem}}
@media(prefers-reduced-motion:reduce) {*,*::before,*::after {scroll-behavior:auto!important;transition:none!important;animation:none!important}}
</style>
"""
    st.html(css.replace("/* upload-icons */", f".st-key-upload_panel{{{';'.join(deck_icons)}}}"))


def card(html: str, *, tone: str = "") -> None:
    variant = tone if tone in {"investor", "professor", "customer"} else ""
    st.markdown(f'<div class="sr-card {variant}">{html}</div>', unsafe_allow_html=True)
