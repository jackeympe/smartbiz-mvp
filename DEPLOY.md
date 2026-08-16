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
- Project type: **Static assets**
- Environment variables:
  - `SMARBIZ_API_URL` = `https://<your-api-domain>`
  - `SMARBIZ_ADMIN_TOKEN` = your admin token

After deploy, verify:
- Open Pages site
- Open browser console: should show API status in prod mode
- Admin login should load data from API

## API hosting

Deploy `src/smartbiz/main.py` with `uvicorn smartbiz.main:app` to:
- Render, Fly.io, Railway, or Azure Container Apps

## Payments

- Use PayFast sandbox for testing
- Set `PAYFAST_MERCHANT_ID` and `PAYFAST_MERCHANT_KEY`
- Notify URL: `https://your-api.example.com/payfast/notify`
- Status update: `POST /bookings/{booking_id}/payfast-status`

## Technician QR flow

- QR endpoint: `GET /bookings/{booking_id}/qr`
- Technician complete: `POST /technician/complete/{booking_id}?token={token}`
- If technician no-shows/fails, refund after 5 days via `POST /bookings/{booking_id}/refund`
- Mobile tech page: `website/technician.html`
- Technician PIN auth: `/api/v1/technicians`, `/api/v1/technicians/verify`

## Admin manual updates

- `PATCH /api/v1/bookings/{booking_id}` updates `status`, `payfast_status`, `evidence_notes`, `evidence_photo_url`, `payfast_payment_id`, `payfast_pf_payment_id`
- Admin UI: **Admin Update** button in bookings table opens quick prompts for status and evidence notes

## Xero hold/release

- Endpoints: `/xero/bookings/{booking_id}/contact`, `/xero/bookings/{booking_id}/invoice`, `/xero/bookings/{booking_id}/creditnote`
- Webhook: `POST /xero/webhook`
- Health: `GET /xero/health`
- Refund logic: after 5 days from `created_at`, admin can trigger `POST /bookings/{booking_id}/refund`
- Refund amount: **90%** of booking amount

## Readiness

- `/health` returns `{"status": "ok"}`
- `/api/v1/status` returns counts and readiness checks
- `/xero/health` returns `{"ok": true/false}`

## Monitoring

- Watch API logs for 4xx/5xx spikes
- Monitor booking completion and refund events
- Check PayFast IPN success/failure

## Render

Use `render.yaml` in this repo. Set these env vars in Render dashboard:
- `SMARTBIZ_ADMIN_TOKEN`
- `SMARBIZ_TECHNICIAN_TOKEN`
- `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMARTBIZ_EMAIL_TO`
- `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_TENANT_ID`
- `SMARBIZ_API_URL` = `https://<your-render-service>.onrender.com`

## Fly.io

```bash
fly launch
fly secrets set SMARTBIZ_ADMIN_TOKEN=... SMARBIZ_TECHNICIAN_TOKEN=...
fly deploy
```

## Railway

Push to GitHub and connect repo in Railway. Set env vars in Railway dashboard.
