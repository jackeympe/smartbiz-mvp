# SmartBiz Fire — Cinematic Compliance MVP

This package is a deployable front-end prototype for the SmartBiz Fire AI Operating System.

## Included
- `index.html` — cinematic public website
- `inspection.html` — lead / inspection request capture
- `dashboard.html` — operations dashboard concept
- `styles.css` — responsive dark cinematic UI
- `app.js` — lightweight interactions
- `assets/smartbiz-fire-cinematic-hero.png` — generated hero visual

## Local preview
Run a simple static server from this directory:
`python3 -m http.server 8080`

Then open:
`http://localhost:8080`

## Production integration
The inspection form currently stores a demo lead in browser localStorage. Replace this with:
`POST /api/v1/leads`

Recommended production flow:
Website → API → PostgreSQL → Event/Outbox → Sales Agent → Discord → WhatsApp/Calendar → Compliance → Service → Documents → Renewal.

See `HERMES_SHIP_PROMPT.txt` for the build-and-deploy instruction.
