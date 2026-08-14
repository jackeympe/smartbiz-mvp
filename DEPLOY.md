# SmartBiz MVP Deployment

## Local API

```bash
cd C:/Users/jacke/Downloads/smartbiz-mvp
uv venv
uv pip install -e .
PYTHONPATH='' .venv/Scripts/python.exe -m uvicorn smartbiz.main:app --host 0.0.0.0 --port 8000
```

## Environment

Set these before deploying:

```bash
SMARTBIZ_ADMIN_TOKEN=your-admin-token
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMARBIZ_EMAIL_TO=dimakatso@smartbiz.local
PAYFAST_MERCHANT_ID=your-payfast-id
PAYFAST_MERCHANT_KEY=your-payfast-key
SMARBIZ_TECHNICIAN_TOKEN=your-tech-token
SMARBIZ_API_URL=https://your-api.example.com
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_TENANT_ID=your-xero-tenant-id
```

## Cloudflare Pages

- Root `/`
- Publish dir `website`
- Environment variables: `SMARBIZ_API_URL`, `SMARBIZ_ADMIN_TOKEN`

## API hosting

Deploy `src/smartbiz/main.py` with `uvicorn smartbiz.main:app` to:
- Render, Fly.io, Railway, or Azure Container Apps

## Payments

- Use PayFast sandbox for testing
- Set `PAYFAST_MERCHANT_ID` and `PAYFAST_MERCHANT_KEY`
- Notify URL: `https://your-api.example.com/payfast/notify`

## Technician QR flow

- QR endpoint: `GET /bookings/{booking_id}/qr`
- Technician complete: `POST /technician/complete/{booking_id}?token={token}`
- If technician no-shows/fails, refund after 5 days via `POST /bookings/{booking_id}/refund`

## Xero hold/release

- This MVP tracks payments in SQLite.
- For real Xero hold/release, integrate the Xero API to create bills/credits.
- Recommended: webhook from PayFast notify -> Xero contact/credit-note creation.
- Refund logic: after 5 days from `created_at`, admin can trigger `POST /bookings/{booking_id}/refund`.
