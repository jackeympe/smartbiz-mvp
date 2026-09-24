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
- `AGENTMAIL_INBOX_ID` = `compliance1660@agentmail.to`
- `AGENTMAIL_API_KEY` = your AgentMail API key
- `WHATSAPP_NUMBER` = `+27634965466`
- `SMARBIZ_API_URL` = your Render service URL after first deploy

## After deploy
- Set `SMARBIZ_API_URL` in Cloudflare Pages to the Render URL
- Test:
  ```
  curl https://<render-url>/api/v1/status
  curl -X POST https://<render-url>/api/v1/smtp-test -H 'x-smartbiz-token: dev' -H 'Content-Type: application/json' -d '{"to":"you@example.com"}'
  ```

## Accounting Integration

SmartBiz Fire uses Zoho as its accounting provider behind the provider-neutral accounting integration boundary.

Configure Zoho credentials through the deployment platform's secret manager. Do not commit OAuth client secrets, authorization codes, access tokens, or refresh tokens to the repository.

