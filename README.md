# SmartBiz Fire Safety MVP

Local-first fire compliance platform: quiz lead funnel, bookings, PayFast payments, technician QR completion, PDF/COC docs, and admin dashboard.

## Stack
- Python + FastAPI + SQLite
- Cloudflare Pages static site
- PayFast for payments
- Zoho for accounting/business operations (integration to be implemented)

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
- `SMARBIZ_API_URL`
- Zoho credentials should be configured only through the deployment secret manager when the Zoho integration is implemented.

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
- `GET /bookings/{id}/pdf`
- `GET /bookings/{id}/coc-pdf`
- `POST /api/v1/smtp-test`

## Deploy
See `DEPLOY.md` and `DEPLOY-PRODUCTION.md`.
