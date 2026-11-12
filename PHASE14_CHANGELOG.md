# Phase 14: Local Tools Rebuild

- Removed Social Captions and PDF Compressor from the tool tabs.
- Added 5 browser-only tools (no API, no upload): Split Bill, List Diff, Margin Calculator, Text to Table (CSV), Photo to PDF.
- Logic lives in `static/local-tools.js`; panels and cards are in `index.html`.
- Marketplace fee rates are user-entered on purpose (no hardcoded Shopee/Tokopedia rates).
- Old social/PDF panels stay hidden in the DOM and their backend routes remain, so existing JS/tests do not break. Remove them in a cleanup pass.
- Page language set to `id`, SEO metadata rewritten for the new direction.
- Frontend tests updated (8 tabs, 10 panels, 3 scripts): 11/11 pass.

## Second pass
- Added Excel Cleaner (phone/name/date normalisation, dedupe, .xlsx/.csv out), QR Code (link/WhatsApp/WiFi, PNG/SVG), Image Resizer/WebP (bulk, ZIP), .xlsx export for Text to Table.
- Everyday Text Tools: sanitize PDF/web copy, extract emails, extract Indonesian phone numbers.
- Gemini desk: polite message rewriter and Excel/Sheets formula generator.
- Backend: /privacy, /terms, /healthz, HTML 404, CSP + HSTS + Permissions-Policy, per-IP AI limit (hashed), optional ProxyFix, retired caption/PDF endpoints off by default (BORINGSTUFF_LEGACY_TOOLS=1 re-enables).
- Fixed misleading My Library text (items are stored server-side per session, not only in the browser).
- New: DEPLOY.md, Procfile, test_phase14.py.
