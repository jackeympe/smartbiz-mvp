# SmartBiz MVP — Cloudflare Pages Deployment

## Deploy `website/` to Cloudflare Pages

### 1. Push to GitHub

```bash
git push origin main
```

### 2. Create Pages project

1. Go to https://dash.cloudflare.com/pages
2. **Create a project** → **Connect to Git**
3. Select **jackeympe/smartbiz-mvp**
4. Set:
   - Branch: `main`
   - Root directory: `/`
   - Build command: leave blank
   - Publish directory: `website`
5. Deploy

## Environment variables

Add in Cloudflare Pages **Settings → Environment variables**:

- `SMARBIZ_API_URL` = your hosted API URL

If you deploy the API separately, set it to that public URL. For local testing, you can leave it unset and the site will fall back to `http://localhost:8000`.

## Troubleshooting

- If deploy fails with a `wrangler` Worker error, ensure the Pages project type is **Static assets** / **Static site**, not Worker.
- If you see `403 Forbidden`, retry the deployment from the Pages dashboard.
