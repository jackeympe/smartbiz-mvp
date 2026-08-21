# Render deploy checklist for SmartBiz API

## One-time setup
1. Go to https://dashboard.render.com
2. Sign up / log in with GitHub
3. Click **New +** → **Web Service**
4. Connect repo: `jackeympe/smartbiz-mvp`
5. Branch: `main`
6. Runtime: `Python 3.11`
7. Build command:
   ```
   pip install -r requirements.txt
   ```
8. Start command:
   ```
   uvicorn smartbiz.main:app --host 0.0.0.0 --port $PORT
   ```
9. Plan: `Free`

## Required env vars
- `SMARTBIZ_ADMIN_TOKEN` = `dev`
- `SMTP_HOST` = your SMTP host or leave blank to use AgentMail fallback
- `SMTP_PORT` = `587` or blank
- `SMTP_USER` = your SMTP user or blank
- `SMTP_PASS` = your SMTP pass or blank
- `SMARTBIZ_EMAIL_TO` = recipient for notifications
- `PAYFAST_MERCHANT_ID` = PayFast merchant id
- `PAYFAST_MERCHANT_KEY` = PayFast merchant key
- `XERO_CLIENT_ID` = `EE092CA6A9EF41ABB38629D754A9526F`
- `XERO_CLIENT_SECRET` = your Xero client secret
- `XERO_TENANT_ID` = `78C3A293-8B24-441A-893E-812B3E8CBE0A`
- `AGENTMAIL_INBOX_ID` = `compliance1660@agentmail.to`
- `AGENTMAIL_API_KEY` = your AgentMail API key
- `WHATSAPP_NUMBER` = `0677684582`
- `SMARBIZ_API_URL` = your Render service URL after first deploy

## After deploy
- Set `SMARBIZ_API_URL` in Cloudflare Pages to the Render URL
- Test:
  ```
  curl https://<render-url>/api/v1/status
  curl -X POST https://<render-url>/api/v1/smtp-test -H 'x-smartbiz-token: dev' -H 'Content-Type: application/json' -d '{"to":"you@example.com"}'
  ```
