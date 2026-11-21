# Slide Roast — Project Checklist

## Completed
- [x] Phase 1: structure, requirements, .env.example, .gitignore, dark theme, landing page
- [x] Phase 2: pdf_service (size/page limits, corrupt, password, empty, scanned), validators, upload page, sample decks
- [x] Phase 3: 3 judge prompts, Pydantic schemas, groq_service (retries, JSON validation, friendly errors), summary step, report_service pipeline, Start Roasting wired
- [x] Phase 4: scoring_service (backend weighted formula), Roast Report dashboard (score ring, judge cards, Plotly charts, verdict, top 3, slide-by-slide, judge questions)
- [x] Choose one judge on upload, with a separate AI review and an on-demand slide text fixer
- [x] Automated tests with mocked Groq, so no key or quota needed

## Pending
- [ ] Phase 5: database_service (SQLite), report history page, comparison_service
- [ ] Phase 6: About/business-model page, README, demo path, final real end-to-end test
- [ ] Optional: visual (image) analysis of slides. NOT implemented; the UI says "unavailable".

## NOT yet verified (needs a real API key)
- Run `python test_groq_raw.py` for a live synthetic Groq request.
- Run `python -m tests.live_check` to send the bundled sample deck's extracted text to Groq.
- The model is configured in `services/groq_service.py`. If Groq reports that the configured Llama model is retired, the service switches to the replacement model.

## Known limitations
- Judging uses extracted TEXT only (no layout/visual analysis).
- Report lives in st.session_state until Phase 5 adds SQLite, so refreshing the browser loses it.

## Required environment variables
- `GROQ_API_KEY` (required, read from `.env` or Streamlit Secrets)

## Module contracts
| Module | Input | Output |
|---|---|---|
| pdf_service.extract_slides | PDF bytes | {ok, error, page_count, slides[], pages_without_text[], warnings[]} |
| groq_service.run_judge | judge key, project info, slides | validated judge dict (or GroqError) |
| groq_service.generate_summary | slides + judge results | {overall_verdict, top_improvements[3], slides[]} |
| scoring_service.calculate | {judge_key: judge dict} | {overall_score, category_scores, interpretation, method, notes} |
| report_service.run_analysis | project info + extraction | ONE report dict (JSON-friendly; Phase 5 saves it) |
