# Slide Roast — Project Checklist

## Completed
- [x] Phase 1: structure, requirements, .env.example, .gitignore, dark theme, landing page
- [x] Phase 2: pdf_service (size/page limits, corrupt, password, empty, scanned), validators, upload page, sample decks
- [x] Phase 3: 3 judge prompts, Pydantic schemas, gemini_service (retries, JSON validation, friendly errors), summary step, report_service pipeline, Start Roasting wired
- [x] Phase 4: scoring_service (backend weighted formula), Roast Report dashboard (score ring, judge cards, Plotly charts, verdict, top 3, slide-by-slide, judge questions)
- [x] Choose one judge on upload, with a separate AI review and an on-demand slide text fixer
- [x] Automated tests with mocked Gemini, so no key or quota needed

## Pending
- [ ] Phase 5: database_service (SQLite), report history page, comparison_service
- [ ] Phase 6: About/business-model page, README, demo path, final real end-to-end test
- [ ] Optional: visual (image) analysis of slides. NOT implemented; the UI says "unavailable".

## NOT yet verified (needs a real API key)
- Live Gemini calls. Run `python -m tests.live_check` once your key is in .env.
- Gemini accepting our JSON schema (`response_json_schema` built from Pydantic). If it rejects it, the error shows as a
  "bad_request" message; the fix would be in services/gemini_service.py `_call_model`.
- Model name `gemini-3.8-flash` (from the docs on 2026-11-18). If you get "model not found", change GEMINI_MODEL in .env.

## Known limitations
- Judging uses extracted TEXT only (no layout/visual analysis).
- Report lives in st.session_state until Phase 5 adds SQLite, so refreshing the browser loses it.

## Required environment variables
- GEMINI_API_KEY (required) · GEMINI_MODEL (optional)

## Module contracts
| Module | Input | Output |
|---|---|---|
| pdf_service.extract_slides | PDF bytes | {ok, error, page_count, slides[], pages_without_text[], warnings[]} |
| gemini_service.run_judge | judge key, project info, slides | validated judge dict (or GeminiError) |
| gemini_service.generate_summary | slides + judge results | {overall_verdict, top_improvements[3], slides[]} |
| scoring_service.calculate | {judge_key: judge dict} | {overall_score, category_scores, interpretation, method, notes} |
| report_service.run_analysis | project info + extraction | ONE report dict (JSON-friendly; Phase 5 saves it) |
