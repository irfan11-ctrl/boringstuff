# BoringStuff Phase 12 — AI Product Upgrade

## What changed

- Gemini REST integration on the Flask backend for cover letters, resignation letters, and social captions.
- Local template fallback for document and caption generation when no key is configured or Gemini is temporarily unavailable / rate-limited.
- New AI Career Studio with resume-to-job-description review and interview preparation.
- Structured JSON validation for AI career tools and output-length checks for generated letters/captions.
- Per-browser-session limit of 20 AI requests per rolling hour, stored in SQLite.
- API key loaded from `.env`; never exposed to frontend JavaScript or API status responses.
- Visible privacy notices and AI-mode status indicators.
- Added backend test cases for AI routing, fallback, status, resume review, and interview prep.
- Added Windows setup instructions in `GEMINI_SETUP.md`.

## Important limits

- AI features require the user to configure their own Gemini API key in `.env`.
- Resume match score is heuristic guidance, not an ATS result or hiring prediction.
- Gemini free-tier quotas and model availability are controlled by Google and can change.
- Google states that free-tier content may be used to improve its products. Do not submit sensitive or confidential data.
- PDF compression and My Library remain local; no AI is used for PDF compression.

## Verification in this build environment

- Python compilation: passed.
- Frontend structural tests: 8/8 passed.
- Inline JavaScript syntax (`node --check`): passed.
- Full backend unit tests could not be executed in this build environment because Flask is not installed here and package installation is unavailable. Run the full suite locally after installing `requirements.txt`.

## Phase 12.1 — Test environment isolation

- Fixed test configuration so a developer's local `.env` Gemini key is not inherited by tests unless a test explicitly supplies `GEMINI_API_KEY`.
- This prevents real Gemini calls from changing deterministic local-fallback tests and fixes the four reported failures caused by running the suite in a folder containing a configured Gemini key.


## Additive Everyday Tools upgrade
- Added five browser-only text utilities: word/character counter, case converter, duplicate-line remover, text cleaner, and bullet formatter.
- Added five Gemini-required writing tools: text rewriter, email reply writer, text summarizer, grammar fixer, and translator.
- Added explicit AI status, output-language and tone controls, copy/download actions, request validation, and privacy messaging.
- Preserved the existing document generator, social copywriter, AI Career Studio, PDF compressor, My Library, donation links, navigation, security headers, SEO metadata, and deployment files.


## AI integrity correction
- AI-generated document and caption endpoints now require Gemini and return an explicit error when Gemini is not configured or unavailable.
- Removed silent template fallback from the generation flow; local deterministic helpers remain available for validation and internal reference only.
- Caption generation now validates all three AI-generated variants and all three AI-generated CTA suggestions before returning success.
