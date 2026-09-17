# SmartBiz Production Deploy Checklist

## Environment variables
- `SMARTBIZ_ADMIN_TOKEN`
- `SMARBIZ_TECHNICIAN_TOKEN`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMARTBIZ_EMAIL_TO`
- `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE`, `PAYFAST_URL`
- `SMARBIZ_API_URL`
- `SMARBIZ_SITE_URL`
- Zoho credentials: configure only in the deployment secret manager after the Zoho integration is implemented.

## API host
- Recommended: Render, Fly.io, Railway, Azure Container Apps
- Expose port 8000
- Set workers/instances to at least 1

## Database
- SQLite file `smartbiz.sqlite` is created automatically on first run
- For production, back up the SQLite file regularly
- For scaling, plan migration to PostgreSQL/RDS

## Security
- Use strong admin and technician tokens
- Enable HTTPS on the API host
- Restrict Cloudflare Pages `SMARBIZ_API_URL` to HTTPS
- Store all third-party credentials only in the deployment secret manager

## Cloudflare Pages
- Project type: Static assets
- Environment variables:
  - `SMARBIZ_API_URL` = `https://your-api.example.com`
  - `SMARTBIZ_ADMIN_TOKEN` = your chosen admin token

## PayFast
- Set PayFast notify URL to `https://your-api.example.com/payfast/notify`
- Enable IPN/notify in PayFast merchant settings
- Verify merchant key and passphrase

## Zoho
- Zoho is the accounting/business-operations replacement for the cancelled Xero integration.
- Implement Zoho through a dedicated integration module with credentials supplied through the deployment secret manager.
- Do not store Zoho secrets in source control or `.env.example`.

## Verification
- `/health` returns `{"status": "ok"}`
- `/api/v1/status` returns counts

## Monitoring
- Watch API logs for 4xx/5xx spikes
- Monitor booking completion and refund events
- Check PayFast IPN success/failure
