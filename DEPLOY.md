# Deploy BoringStuff

Needs a host with a **persistent disk** (SQLite lives in `instance/`) and HTTPS.
Works on Railway, Render, Fly.io, or any VPS.

## Environment variables
| Name | Value |
|---|---|
| BORINGSTUFF_ENV | production |
| BORINGSTUFF_SECRET_KEY | `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| BORINGSTUFF_ALLOWED_HOSTS | boringstuff.com,www.boringstuff.com |
| BORINGSTUFF_PUBLIC_BASE_URL | https://boringstuff.com |
| BORINGSTUFF_TRUSTED_PROXIES | 1 |
| BORINGSTUFF_CONTACT_EMAIL | your real contact email (shown on /privacy and /terms) |
| GEMINI_API_KEY | a NEW key (rotate the one that was in the zip) |
| GEMINI_MODEL | a model name that exists in your Google AI Studio account |

## Start command
`pip install -r requirements.txt` then `waitress-serve --listen=0.0.0.0:$PORT wsgi:app` (also in `Procfile`).
Mount the persistent volume at `<app folder>/instance`.

## Health check
`GET /healthz` returns `{"status":"ok"}`. If your platform probes with its own hostname, add that hostname to BORINGSTUFF_ALLOWED_HOSTS or use a TCP check.

## After deploy: 10-minute smoke test
1. Open `/`, `/privacy`, `/terms`, `/robots.txt`, `/sitemap.xml`.
2. Try each of the 11 tools once on your phone and once on desktop.
3. Run one AI task (Gemini desk). Run "Rumus Excel" with a plain-language goal.
4. Save and reload a My Library item.
