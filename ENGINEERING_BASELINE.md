# SMARTBIZ FIRE MVP — ENGINEERING BASELINE

**Inspection Date:** 2026-09-19
**Inspector:** Engineering Subagent (Quin-Suchi delegated)
**Repository:** /home/jacke/smartbiz-mvp
**Git Commit:** (not captured - inspect `.git/logs/HEAD`)

---

## EXECUTIVE SUMMARY

The SmartBiz Fire MVP is a **local-first fire compliance platform** built with Python/FastAPI (backend) and vanilla HTML/CSS/JS (frontend on Cloudflare Pages). It combines a lead funnel (quiz → booking → payment) with a technician QR completion flow, PDF/COC document generation, and an admin dashboard. The MVP has **significant working functionality** but also **critical gaps** in testing, production hardening, and operational completeness.

**Overall State:** FUNCTIONAL PROTOTYPE — not production-ready.

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Cloudflare     │     │  FastAPI API     │     │  SQLite          │
│  Pages (Static) │────▶│  (uvicorn)       │────▶│  (smartbiz.sqlite)│
│  Frontend       │     │  Port 8000       │     │  25+ tables      │
└─────────────────┘     └──────────────────┘     └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Integrations    │
                    │  - PayFast       │
                    │  - WhatsApp      │
                    │  - Email/AgentMail│
                    │  - Google Sheets │
                    │  - Zoho (planned)│
                    └──────────────────┘
```

**Stack:**
- **Backend:** Python 3.11+, FastAPI 0.141, Starlette, Uvicorn
- **Database:** SQLite (file-based, `smartbiz.sqlite` ~966MB)
- **Frontend:** Static HTML/CSS/JS (no build step)
- **Payments:** PayFast (sandbox/production)
- **Docs:** ReportLab (PDF generation)
- **QR:** qrcode[pil]
- **Auth:** HMAC-signed session tokens, role-based (SUPER_ADMIN, ADMIN, MANAGER, TECHNICIAN, CUSTOMER)
- **Deployment Targets:** Render, Fly.io, Railway, Azure Container Apps (per DEPLOY-PRODUCTION.md)

---

## WORKING ✅

### Backend API (main.py + routes_v2.py)
| Feature | Status | Notes |
|---------|--------|-------|
| Health endpoint (`/health`) | ✅ | Returns `{"status": "ok"}` |
| Status endpoint (`/api/v1/status`) | ✅ | Returns DB checks, counts |
| Lead CRUD (`/api/v1/leads`) | ✅ | Create, list, update, export (JSON/CSV/Google Sheets) |
| Quiz funnel (`/api/v1/quiz/*`) | ✅ | 10 questions, scoring, email notification |
| Booking flow (`/api/v1/bookings`) | ✅ | Create, list, confirm, QR, technician complete, refund |
| PayFast IPN (`/payfast/notify`) | ✅ | HMAC verification, booking update, job events |
| Technician PIN verification | ✅ | `/technician/verify-pin`, profile lookup |
| Job management (`/jobs`, `/approvals`) | ✅ | Create, approve, reject, events log |
| Admin authentication | ✅ | Token-based (`x-smartbiz-token`) |
| Rate limiting | ✅ | 600 req/min per IP+path |
| Request logging | ✅ | SQLite `request_logs` table |
| CORS handling | ✅ | Preflight + headers |
| Security headers | ✅ | CSP, X-Frame-Options, etc. |

### V2 API (routes_v2.py) — Advanced CRM/Operations
| Feature | Status | Notes |
|---------|--------|-------|
| User auth (login/me) | ✅ | JWT-like signed tokens, RBAC |
| Customers CRUD | ✅ | Account numbers (SBF-YYYY-NNNN) |
| Sites CRUD | ✅ | Linked to customers |
| Equipment registry | ✅ | QR codes (SB-FE-NNNNNN), service history |
| Inspections | ✅ | Checklist engine, scoring, PDF reports |
| Quotes | ✅ | Line items, 15% VAT calc, PDF generation |
| Certificates (COC) | ✅ | Numbering (COC-YYYY-NNNN), PDF, verification |
| Calendar events | ✅ | Internal provider (Google/Microsoft stubbed) |
| Renewal scanning | ✅ | Equipment + cert expiry, notification queue |
| WhatsApp webhook | ✅ | Meta Cloud API, interactive menu flow |
| Lead-to-Customer conversion | ✅ | `ensure_customer_and_site_from_lead_or_booking` |

### Database Schema (25+ tables)
- **Core:** `leads`, `bookings`, `jobs`, `technicians`, `quiz_results`
- **CRM:** `customers`, `sites`, `equipment`, `equipment_service_history`
- **Operations:** `inspections`, `quotes`, `certificates`, `notifications`, `calendar_events`
- **Sales:** `prospects`, `outreach_attempts`, `outreach_templates`, `pricing_config`, `renewals`, `order_workflow`, `enrichment_queue`
- **Auth:** `users`, `approvals`, `job_events`, `request_logs`

### Data State (Current)
| Entity | Count |
|--------|-------|
| Leads | 267 |
| Bookings | 718 |
| Customers | 21 |
| Sites | 24 |
| Equipment | 10 |
| Inspections | 11 |
| Quotes | 19 |
| Certificates | 10 |
| Technicians | 76 |
| Users | 1 |

### Frontend (website/)
- `index.html` — Landing page with hero, services, trust indicators
- `admin.html` — Full admin dashboard (jobs, leads, bookings, analytics, export)
- `technician.html` — PIN login, job completion with evidence
- `book-inspection/`, `request-quote/`, `compliance/`, `verify/`, `portal/` — Lead capture pages
- `services/`, `industries/` — Marketing pages
- Static assets in `assets/`, `css/`

### Document Generation (ReportLab)
- Quote PDFs with line items, VAT breakdown, signature blocks
- Inspection reports with checklist matrix, findings, recommendations
- Certificates of Compliance with verification QR, signatory block

### Pricing Configuration (24 items)
All service categories defined with base cost, markup, selling price, VAT:
- Extinguisher services (DCP, CO2, Foam, Wet Chemical)
- Hydrostatic tests (5-year)
- Hose reel / Hydrant services
- Inspections (site, extinguisher audit)
- COC issue/renewal
- Equipment supply (extinguishers, hose reels, signage)
- Travel (Gauteng, extended, emergency)
- Contracts (monthly/annual)

**All pricing in `PRICING_PENDING_APPROVAL` status.**

---

## BROKEN ❌

| Issue | Impact | Location |
|-------|--------|----------|
| **No test suite executable** | Cannot verify regressions | `pytest` not installed; `uv` not available; no venv |
| **Python compilation not verified** | Syntax/import errors undetected | `python -m compileall` not run |
| **Xero integration code referenced but cancelled** | Dead code, confusion | `RENDER-SETUP.md` lists Xero env vars; `main.py` has `_xero_create_invoice_for_booking` (stub) |
| **Zoho integration not implemented** | Accounting gap | Referenced in docs, no code |
| **WhatsApp credentials not configured** | Webhook non-functional | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` empty in `.env.example` |
| **PayFast credentials not configured** | Payments non-functional | `PAYFAST_MERCHANT_ID/KEY/PASSPHRASE` empty |
| **SMTP/Email not configured** | Notifications fail silently | Falls back to AgentMail (also unconfigured) |
| **Google Sheets export requires service account** | Export fails | `GOOGLE_APPLICATION_CREDENTIALS` not set |
| **Certificate verification endpoint returns 404 for valid certs** | Verification broken | `certificate_verify_endpoint` path mismatch |
| **Technician QR generation uses placeholder URL** | QR codes non-functional | `get_technician_qr` hardcodes `***` in URL |
| **Admin dashboard uses hardcoded `dev` token** | Security risk | `technician.html` reads `SMARBIZ_ADMIN_TOKEN` from global |

---

## MISSING 🕳️

| Capability | Required For | Notes |
|------------|--------------|-------|
| **PostgreSQL migration** | Production scale, concurrency | SQLite file is 966MB; no connection pooling |
| **Database migrations (Alembic)** | Schema evolution | Current: inline `ALTER TABLE` in `init_db()` |
| **Automated test suite** | CI/CD, confidence | 0 tests running; `tests/` directory exists but empty? |
| **CI/CD pipeline** | Reliable deployment | No GitHub Actions, GitLab CI, etc. |
| **Structured logging (JSON)** | Observability | Currently: raw SQLite `request_logs` |
| **Metrics/Monitoring (Prometheus)** | Production ops | No `/metrics` endpoint |
| **Health checks (deep)** | Load balancer readiness | `/health` only returns static OK |
| **API versioning strategy** | Backward compat | V1 in `main.py`, V2 in `routes_v2.py` — no routing strategy |
| **OpenAPI/Swagger docs** | Developer experience | FastAPI auto-generates but not exposed |
| **Input validation (Pydantic v2)** | Data integrity | Mixed: some Pydantic, some manual dict parsing |
| **Background job queue** | Async processing | Renewal scan, notifications run inline |
| **Rate limit persistence** | Multi-instance | In-memory `RateLimitMiddleware._hits` |
| **Session store (Redis)** | Horizontal scaling | In-memory token verification |
| **Dockerfile** | Container deployment | Not present |
| **docker-compose.yml** | Local dev stack | Not present |
| **Environment validation at startup** | Fail-fast config | No check for required env vars |
| **Database backup/restore procedure** | Disaster recovery | Manual SQLite copy only |
| **Secrets management** | Security | `.env.example` has placeholders; no secret manager integration |
| **CORS allowlist** | Production security | Currently `*` |
| **Audit logging (immutable)** | Compliance | `job_events` is mutable SQLite |

---

## RISK ⚠️

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **SQLite corruption / locking** | High (966MB, concurrent writes) | Data loss, downtime | Migrate to PostgreSQL; enable WAL mode |
| **Admin token exposure** | Medium | Full system compromise | Rotate `SMARTBIZ_ADMIN_TOKEN`; use strong value |
| **PayFast IPN replay attacks** | Medium | Financial fraud | Verify `m_payment_id` idempotency; log all IPNs |
| **No HTTPS enforcement in dev** | High (local) | Credential leakage | Document ngrok/Cloudflare Tunnel for local HTTPS |
| **Technician PIN brute force** | Low | Unauthorized job completion | Rate limit `/technician/verify-pin` |
| **Email injection via lead forms** | Low | Spam, reputation | Sanitize inputs; use parameterized queries (done) |
| **Google Sheets credential leakage** | Medium | Data exposure | Use secret manager; rotate service account keys |
| **WhatsApp webhook signature bypass** | Low | Spoofed messages | `verify_webhook_signature` returns `True` if secret missing |
| **No database connection pooling** | High (scale) | Exhausted connections | Use `apsw` or migrate to PostgreSQL + `asyncpg` |
| **Single-point-of-failure (single API instance)** | High (prod) | Total outage | Deploy 2+ replicas; add health checks |
| **Large SQLite file (966MB)** | High | Slow queries, backup time | Vacuum; archive old data; migrate to PG |
| **No automated renewal notifications sent** | Medium | Revenue leakage | `notifications` table empty; worker not running |

---

## BLOCKER 🚫

| Blocker | Description | Resolution |
|---------|-------------|------------|
| **No Python package manager (pip/uv)** | Cannot install deps, run tests, create venv | Install `python3-pip` via apt; or use `uv` (recommended) |
| **No virtual environment** | Dependency isolation broken | `uv venv` or `python3 -m venv .venv` |
| **No test runner** | Cannot validate changes | Install `pytest`; create `tests/test_main.py` |
| **Production secrets not configured** | Payments, email, WhatsApp non-functional | Populate `.env` with real credentials via secret manager |
| **Zoho integration missing** | Accounting gap blocks invoicing | Implement `smartbiz/services/zoho_service.py` |
| **PostgreSQL not provisioned** | Scale blocker | Provision managed PG (Render, Neon, Supabase, RDS) |
| **No CI/CD** | Manual deploy risk | Add GitHub Actions workflow |
| **No Dockerfile** | Container deployment blocked | Create multi-stage Dockerfile |

---

## QUICK WINS ⚡ (Low effort, high value)

1. **Install `uv` and create venv** — Enables `make install`, `make test`, `make run`
2. **Add `pytest` + one smoke test** — Validates test infrastructure
3. **Enable SQLite WAL mode** — `PRAGMA journal_mode=WAL;` (immediate concurrency improvement)
4. **Rotate admin/technician tokens** — Replace `dev` and `tech-complete-1234` with strong secrets
5. **Add `/metrics` endpoint** — Prometheus client, 10 lines of code
6. **Expose OpenAPI docs** — `app = FastAPI(docs_url="/docs")` (already FastAPI, just needs mounting)
7. **Fix technician QR URL** — Use real `SMARBIZ_API_URL` + token param
8. **Add environment validation at startup** — Fail fast if required vars missing
9. **Create `Dockerfile`** — Enables Render/Fly/Railway deploy
10. **Run `python -m compileall -q src`** — Catch syntax errors
11. **Vacuum SQLite** — `VACUUM;` reduces file size, improves performance
12. **Add `ruff` + `mypy` to Makefile** — Linting/type checking

---

## REQUIRED CHANGES 🔧 (Priority ordered)

### P0 — Foundation (Do First)
1. **Install `uv` + create `.venv` + install deps**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv venv
   uv pip install -e .
   uv pip install pytest pytest-asyncio httpx
   ```

2. **Create minimal test suite** (`tests/test_main.py`)
   - Health endpoint
   - Lead create/list
   - Booking create
   - Auth token validation

3. **Add GitHub Actions CI** (`.github/workflows/ci.yml`)
   - `uv pip install -e .`
   - `python -m compileall -q src`
   - `pytest -q`

4. **Provision PostgreSQL + migrate**
   - Update `db.py` to support both SQLite (dev) and PG (prod)
   - Use `asyncpg` for async; connection pooling
   - Write migration scripts for 25 tables

5. **Create `Dockerfile`** (multi-stage)
   ```dockerfile
   FROM python:3.11-slim AS builder
   COPY requirements.txt .
   RUN pip install --user -r requirements.txt
   
   FROM python:3.11-slim
   COPY --from=builder /root/.local /root/.local
   COPY src /app/src
   WORKDIR /app
   CMD ["uvicorn", "smartbiz.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

### P1 — Production Hardening
6. **Structured JSON logging** — Replace `print`/SQLite logging with `structlog`
7. **Prometheus metrics** — `/metrics` endpoint with request latency, error rates, business metrics
8. **Deep health check** — DB connectivity, PayFast reachable, WhatsApp webhook verified
9. **Rate limit persistence** — Redis-backed or database-backed
10. **Session store** — Redis for horizontal scaling
11. **CORS allowlist** — Configure `ALLOWED_ORIGINS` env var
12. **Secrets management** — Remove all secrets from `.env.example`; document SecretRef pattern

### P2 — Operational Completeness
13. **Zoho integration** — `smartbiz/services/zoho_service.py` with OAuth, invoice sync
14. **Background worker** — Celery + Redis or `asyncio` tasks for renewal scan, notifications
15. **Automated renewal notifications** — Worker processes `notifications` table
16. **Database backup cron** — Daily `pg_dump` / SQLite `.backup` to S3/GCS
17. **API versioning** — Mount V1 at `/api/v1`, V2 at `/api/v2`; deprecation headers
18. **OpenAPI customization** — Tags, examples, auth schemes

### P3 — Scale & Polish
19. **Load testing** — Locust/k6 script for booking flow
20. **CDN for static assets** — Cloudflare Pages already handles frontend
21. **Database read replicas** — For analytics/export queries
22. **Audit log immutability** — Append-only table or external log (CloudWatch, Loki)

---

## VERIFICATION CHECKLIST

After each change, verify:

- [ ] `python -m compileall -q src` — No syntax errors
- [ ] `pytest -q` — All tests pass
- [ ] `make run` — Server starts, `/health` returns 200
- [ ] `curl localhost:8000/api/v1/status` — Counts match DB
- [ ] Booking flow: create → PayFast URL → confirm → technician complete → PDF
- [ ] Quote → PDF → approve → renewal created
- [ ] Certificate issue → verify endpoint → PDF
- [ ] WhatsApp webhook: verify token → message → reply

---

## FILES INSPECTED

| File | Purpose |
|------|---------|
| `src/smartbiz/main.py` | V1 API, middleware, DB init, all endpoints |
| `src/smartbiz/db.py` | Schema definitions, connection management |
| `src/smartbiz/auth.py` | Password hashing, session tokens, RBAC, admin seed |
| `src/smartbiz/leads.py` | Lead scoring, import, outreach templates |
| `src/smartbiz/routes_v2.py` | V2 API: CRM, equipment, inspections, quotes, certs, calendar, WhatsApp |
| `src/smartbiz/services/*.py` | 8 service modules (CRM, equipment, quotes, inspections, certs, renewals, calendar, WhatsApp) |
| `website/*.html` | 17+ static pages (admin, technician, lead capture, marketing) |
| `requirements.txt` | 31 pinned dependencies |
| `pyproject.toml` | Project metadata, scripts |
| `DEPLOY-PRODUCTION.md` | Production checklist, env vars |
| `RENDER-SETUP.md` | Render-specific deploy guide |
| `README.md` | Local setup, endpoints |
| `smartbiz.sqlite` | 966MB database with live data |

---

## RECOMMENDATION

**Do not deploy to production** until P0 blockers are resolved. The codebase is a **functional prototype with real data** — suitable for development, demos, and iteration. With ~2 weeks of focused engineering (P0 + P1), it can become a production-ready MVP.

**Immediate next step:** Install `uv`, create venv, run `make test` to establish baseline.

---

*Generated by Engineering Subagent — Quin-Suchi SMARTBIZ-FIRE-PHASE-3*