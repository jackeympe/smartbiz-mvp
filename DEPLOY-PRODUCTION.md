# SmartBiz Fire MVP — Production Deployment

## Architecture

- Frontend: Cloudflare Pages, static content from `website/`
- Backend: FastAPI container from `Dockerfile`
- Runtime database: persistent SQLite volume for the MVP
- Edge: Cloudflare DNS/HTTPS in front of the public site and API
- Orchestration: OpenClaw
- Engineering executor: Hermes
- Operations office: Discord

## Required production environment

Set these only in the backend secret store:

- `SMARTBIZ_ENV=production`
- `AUTH_SECRET`
- `SMARTBIZ_ADMIN_TOKEN`
- `SMARTBIZ_TECHNICIAN_TOKEN`
- `DEFAULT_ADMIN_EMAIL`
- `DEFAULT_ADMIN_PASSWORD`
- `DEFAULT_ADMIN_PHONE`
- `SMARTBIZ_ALLOWED_ORIGINS=https://smartbizfire.co.za,https://www.smartbizfire.co.za`
- SMTP credentials
- PayFast credentials
- Google Calendar credentials where enabled
- WhatsApp/Meta credentials only after verification

Never expose backend secrets to Cloudflare static frontend variables.

## Backend

Build:

```bash
docker build -t smartbiz-mvp .
```

Run with Compose:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8000/health
```

The Compose configuration stores `/app/data/smartbiz.sqlite` in the named `smartbiz_data` volume.

Back up that volume before upgrades or migrations.

## Frontend

Deploy only `website/` to Cloudflare Pages.

The browser must never receive:

- admin tokens
- authentication secrets
- OAuth refresh tokens
- SMTP passwords
- payment secrets

Configure the public API origin/route through Cloudflare or the static site's runtime configuration.

## Production acceptance

A launch is accepted only after all of these pass:

1. Homepage
2. Lead submission
3. Booking
4. Google Calendar synchronization
5. Admin login
6. Revenue Command Centre
7. Quote workflow
8. Job/inspection workflow
9. Certificate generation and public verification
10. Renewal workflow
11. Unauthorized access rejection
12. Health/automation verification

## Rollback

- Keep the previous container image/tag.
- Keep a database backup before deployment.
- If acceptance fails, restore the prior application image without replacing the SQLite volume.
- Never delete or overwrite production `smartbiz.sqlite` as part of application deployment.
