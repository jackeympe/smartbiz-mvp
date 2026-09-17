# SmartBiz MVP Deployment

## Local API

```bash
cd C:/Users/jacke/Downloads/smartbiz-mvp
uv venv
uv pip install -e .
PYTHONPATH='' .venv/Scripts/python.exe -m pytest tests/ -v
PYTHONPATH='' .venv/Scripts/python.exe -m uvicorn smartbiz.main:app --host 0.0.0.0 --port 8000
```

## Environment

Set these before deploying:

```bash
SMARTBIZ_ADMIN_TOKEN=your-admin-token
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email
SMTP_PASS=your-mail-password
SMARTBIZ_EMAIL_TO=your-recipient
PAYFAST_MERCHANT_ID=your-payfast-id
PAYFAST_MERCHANT_KEY=your-payfast-key
SMARBIZ_TECHNICIAN_TOKEN=your-tech-token
SMARBIZ_API_URL=https://your-api.example.com
```

Zoho credentials must be configured through the deployment secret manager once the Zoho integration is implemented. Do not commit them to source control.

## Cloudflare Pages

- Repo: connect GitHub repo `jackeympe/smartbiz-mvp`
- Project type: **Static assets**
- Root directory: `/`
- Build command: leave blank
- Build output directory: `website`
- Environment variables:
  - `SMARBIZ_API_URL` = `https://<your-api-domain>`
  - `SMARBIZ_ADMIN_TOKEN` = your admin token

## API hosting

Deploy `src/smartbiz/main.py` with `uvicorn smartbiz.main:app` to Render, Fly.io, Railway, or Azure Container Apps.

## Payments

- Use PayFast sandbox for testing
- Set `PAYFAST_MERCHANT_ID` and `PAYFAST_MERCHANT_KEY`
- Notify URL: `https://your-api.example.com/payfast/notify`
- Status update: `POST /bookings/{booking_id}/payfast-status`

## Technician QR flow

- QR endpoint: `GET /bookings/{booking_id}/qr`
- Technician complete: `POST /technician/complete/{booking_id}?token={token}`
- Mobile tech page: `website/technician.html`
- Technician PIN auth: `/api/v1/technicians`, `/api/v1/technicians/verify`

## Admin manual updates

- `PATCH /api/v1/bookings/{booking_id}` updates booking/payment evidence fields.
- Admin UI: **Admin Update** button in bookings table opens quick prompts for status and evidence notes.

## Zoho

Zoho is the designated accounting/business-operations replacement. The application should integrate with Zoho through a dedicated adapter rather than embedding provider-specific accounting logic throughout the core booking workflow.

## Readiness

- `/health` returns `{"status": "ok"}`
- `/api/v1/status` returns counts and readiness checks

## Monitoring

- Watch API logs for 4xx/5xx spikes
- Monitor booking completion and refund events
- Check PayFast IPN success/failure
