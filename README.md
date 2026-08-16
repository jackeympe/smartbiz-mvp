# SmartBiz Fire Safety MVP

Local-first fire compliance platform: quiz lead funnel, bookings, PayFast payments, technician QR completion, PDF/COC docs, Xero sync, and admin dashboard.

## Stack
- Python + FastAPI + SQLite
- Cloudflare Pages static site
- PayFast for payments
- Xero for invoicing/credit notes

## Local setup
```bash
cd C:/Users/jacke/Downloads/smartbiz-mvp
uv venv
uv pip install -e .
PYTHONPATH='' .venv/Scripts/python.exe -m pytest tests/ -v
PYTHONPATH='' .venv/Scripts/python.exe -m uvicorn smartbiz.main:app --host 0.0.0.0 --port 8000
```

## Tests
```bash
PYTHONPATH='' .venv/Scripts/python.exe -m pytest tests/ -v
```

## Env vars
- `SMARTBIZ_ADMIN_TOKEN`
- `SMARBIZ_TECHNICIAN_TOKEN`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMARBIZ_EMAIL_TO`
- `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE`, `PAYFAST_URL`
- `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_TENANT_ID`
- `SMARBIZ_API_URL`

## Key endpoints
- `GET /health`
- `GET /api/v1/status`
- `POST /api/v1/leads`
- `GET /api/v1/quiz/questions`
- `POST /api/v1/quiz/submit`
- `POST /api/v1/bookings`
- `GET /api/v1/bookings`
- `GET /bookings/{id}/qr`
- `POST /technician/complete/{id}`
- `POST /bookings/{id}/refund`
- `POST /payfast/notify`
- `POST /xero/webhook`
- `GET /xero/health`
- `GET /bookings/{id}/pdf`
- `GET /bookings/{id}/coc-pdf`
- `POST /api/v1/smtp-test`

## Deploy
See `DEPLOY.md` and `DEPLOY-PRODUCTION.md`.

## Release notes: 1.2.3
- Refined Cloudflare Pages static deploy config
- Added GitHub Actions workflow for tests + Pages deployment
- Improved admin dashboard prod-mode handling with status pill
- Hardened API docs and endpoint coverage
