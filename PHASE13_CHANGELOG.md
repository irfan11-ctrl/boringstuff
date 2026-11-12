# BoringStuff Phase 13 — Everyday Tools Rebuild

## Product direction
BoringStuff is now a compact collection of simple tools for small, repetitive tasks. It is not positioned as a career platform, document generator, or social media suite.

## Visible tools
### Gemini-powered writing tools
- Text Rewriter
- Email Reply
- Text Summarizer
- Grammar Fixer
- Translator

### Browser-local utilities
- Word Counter
- Case Converter
- Duplicate Line Remover
- Text Cleaner
- Bullet Formatter

## Engineering changes
- Replaced the old career/document/social/PDF interface with one responsive tools workspace.
- Rebuilt the Flask backend around only the new AI endpoint, session-based My Library, AI status, and basic site metadata routes.
- Removed legacy document generation, social caption generation, resume/interview workflows, PDF compression, and their heavy Python dependencies.
- Kept the existing SQLite `library_items` and `ai_usage` tables compatible so the user's existing `instance/boringstuff.sqlite3` file can be retained. The old library item kinds remain accepted for backward compatibility.
- AI tools require Gemini. No local template fallback is returned if the API key is missing or Gemini fails.
- Local utilities run entirely in the browser and do not upload input text.
- Added validation, a 20-request-per-browser-session rolling hourly limit, explicit AI errors, privacy notice, and focused tests.

## Verification
- Python syntax compilation: passed.
- Frontend structural tests: 8/8 passed.
- Inline JavaScript syntax check with Node: passed.
- Full Flask backend tests could not run in this build container because Flask is not installed and package installation is unavailable. Run `python -m unittest discover -v` locally after installing the reduced requirements.
