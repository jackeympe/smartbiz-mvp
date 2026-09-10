# SmartBiz Fire — Current State Audit (Phase 0)

**Date:** 2026-09-10  
**Lead Architect:** Quin Suchi  
**System:** SmartBiz Fire Platform (Target: `https://smartbizfire.co.za`)  
**Repo:** `jackeympe/smartbiz-mvp` (local: `C:\Users\jacke\Downloads\smartbiz-mvp`)  

---

## 1. Executive Audit Summary

The current codebase is a monolithic Python/Starlette application backed by SQLite (`smartbiz.sqlite`) with static HTML/JS frontend pages (`website/index.html`, `website/admin.html`, `website/technician.html`). It has 46 passing automated tests (`tests/test_main.py`), PayFast checkout/IPN stubs, ReportLab PDF generation (Inspection and Certificate of Compliance COC), Xero integration stubs, AgentMail/SMTP email dispatch, QR code generation, technician PIN verification, and lead import/outreach automation.

While the existing MVP provides basic booking, inspection completion, and PDF generation, it does not yet have a multi-site CRM, full equipment register (QR-tagged asset tracking), multi-page customer/public site, comprehensive inspection checklist engine, or full customer portal.

---

## 2. What Exists

### Backend Components (`src/smartbiz/main.py`, `src/smartbiz/leads.py`)
- **API Framework:** Starlette/FastAPI running via Uvicorn on port 8000.
- **Database:** SQLite (`smartbiz.sqlite`) with tables:
  - `leads` (189 rows)
  - `jobs` (178 rows)
  - `approvals` (118 rows)
  - `quiz_results` (186 rows)
  - `bookings` (569 rows)
  - `technicians` (60 rows)
  - `job_events` (682 rows)
  - `request_logs` (2,213 rows)
- **Middleware:** Security headers, rate limiting (120 req/60s), request logging, simple token authentication (`x-smartbiz-token` with role-based segregation for admin vs technician).
- **PDF Engine:** ReportLab-based inspection report and Certificate of Compliance (COC) generation with authorized signatory block.
- **Lead Pipeline:** Lead creation, scoring, JSON/CSV export, outreach templating (`cold_intro`, `follow_up_1`, `appointment_confirm`, `missed_booking`), and Google Sheets export endpoint.
- **Booking & Service:** Booking creation, confirmation, technician assignment, technician mobile completion with evidence notes and photo URL, refund window enforcement, and PayFast status tracking.
- **Accounting & Integrations:** Xero OAuth / contact sync / invoice generation / credit note stubs, AgentMail / SMTP email integration, WhatsApp notification dispatch hook (`WHATSAPP_NUMBER=0677684582`).

### Frontend Components (`website/`)
- `index.html`: Responsive single-page marketing site with hero, CTA buttons, trust stats, module overview, value propositions, testimonials, pricing, 48hr case study, compliance quiz, lead booking form, and live API health pill.
- `admin.html`: Operations dashboard with tabs for overview metrics, leads pipeline, bookings management, technician assignment, quiz submissions, and manual actions.
- `technician.html`: Mobile-first technician interface with PIN verification, booking details, evidence notes, photo URL capture, and completion trigger.

### Deployment & CI Configuration
- Cloudflare Pages setup (`website/` directory, `cloudflare.json`, deployed to `https://e130f59f.smartbiz-mvp.pages.dev`).
- Render configuration (`render.yaml`, `requirements.txt`, `RENDER-SETUP.md`).
- Fly.io configuration (`fly.toml`).
- Batch launcher (`run-api.bat`).

---

## 3. What Works (Verified)

1. **Test Suite:** 46/46 unit and integration tests passing (`pytest tests/ -v`).
2. **Lead & Quiz Funnel:**
   - 10-question compliance quiz (`/api/v1/quiz/questions` and `/api/v1/quiz/submit`) calculates score and labels.
   - Lead submission persists to SQLite with scoring and auto-notification trigger.
3. **Booking & Appointment Engine:**
   - Booking creation and idempotent transition to `confirmed` (`/api/v1/bookings/{id}/confirm`).
   - 5 recent verified appointments (#551-#555) tested and stored.
4. **Technician Workflow:**
   - QR code generation (`/bookings/{id}/qr`) and PIN verification (`/api/v1/technicians/verify`).
   - Job completion with evidence notes and photo URL updates job state and records `job_events`.
5. **Document Generation:**
   - PDF Service Summary document generation (`/bookings/{id}/pdf`).
   - Certificate of Compliance (COC) PDF generation (`/bookings/{id}/coc-pdf`).
6. **Exports:**
   - JSON/CSV export for leads, quiz results, and full database dump (`/api/v1/export/all`).
   - Google Sheets sync endpoint (`/api/v1/leads/export/google-sheets`).

---

## 4. What Is Broken or Fragile

1. **Database Concurrency & Migrations:**
   - Raw SQLite in-process connection with manual `lock = threading.Lock()` can lock during high-concurrency background jobs or external HTTP calls.
   - Migrations are handled via ad-hoc `ALTER TABLE` try-except statements in `init_db()` rather than versioned schema migration files.
2. **Hardcoded Token Auth:**
   - Authentication relies on static header tokens (`x-smartbiz-token: dev`, `technician-pin`) rather than JWT/session-based RBAC with salted password hashing and role hierarchies.
3. **Monolithic Backend File:**
   - `src/smartbiz/main.py` is 1,607 lines containing models, routing, business logic, PDF generation, third-party API clients, and HTML rendering in a single file.
4. **Static Frontend Pages:**
   - The frontend is composed of individual HTML files with inline vanilla JS and hardcoded API base logic rather than a unified multi-page structure with shared component layouts, client-side routing, and type safety.

---

## 5. What Is Missing (Against Master Specification)

1. **Comprehensive Public Website Multi-page Routes:**
   - Missing dedicated pages: `/services/*` (fire extinguishers, equipment, inspections, compliance, safety files), `/industries/*` (schools, restaurants, offices, retail, warehouses, factories), `/about`, `/contact`, `/book-inspection`, `/request-quote`, `/resources`, `/privacy`, `/terms`.
2. **Customer CRM & Multi-Site Hierarchy:**
   - `Customer -> Contacts -> Sites -> Equipment -> Inspections -> Jobs -> Quotes -> Invoices -> Documents -> Certificates`.
   - Current DB only has flat `bookings` and `leads` with no relational customer/site structure.
3. **Fire Equipment Register & QR Tagging:**
   - Dedicated `equipment` table with serial numbers, equipment types (DCP, CO2, Foam, Hose Reel, Hydrant, etc.), capacity, location, installation date, last service, next service, status (`COMPLIANT`, `DUE`, `OVERDUE`, `FAILED`, `MISSING`), and QR code scan lookup (`/equipment/{qr_id}`).
4. **Comprehensive Quote Engine:**
   - `/request-quote` multi-step flow and quote lifecycle (`DRAFT`, `SENT`, `VIEWED`, `APPROVED`, `DECLINED`), quote line items, VAT (15% ZAR configurable), and PDF quote generation.
5. **Configurable Inspection Checklist Engine:**
   - Configurable checklist items, severity grading, pass/fail status, corrective actions, and multi-photo evidence capture.
6. **Customer Portal (`/portal`):**
   - Customer view of sites, equipment status, active jobs, quote approvals, document and certificate downloads.
7. **Calendar Integration Abstraction:**
   - `CalendarProvider` supporting Internal Calendar, Google Calendar, and Outlook with `Africa/Johannesburg` timezone handling.
8. **WhatsApp Integration Abstraction:**
   - `WhatsAppProvider` supporting Meta Cloud API / WhatsApp Business webhook handling, 2-way menu navigation, and template triggers.
9. **Automated Renewal & Maintenance Engine:**
   - Scheduled background reminders at 90, 60, 30, 14, 7 days before service/inspection/certificate expiry with deduplication and notification logging.

---

## 6. What Should Be Reused

1. **Core Domain Rules & Lifecycle Logic:**
   - Booking state transitions (`pending` -> `confirmed` -> `completed`).
   - Technician PIN verification and completion evidence capture.
   - Lead scoring algorithms from `src/smartbiz/leads.py`.
   - Quiz questions and scoring thresholds (10 questions, >=8 mostly compliant, >=5 partially compliant).
   - ReportLab PDF generation logic and formatting styles for Service Reports and COCs.
   - AgentMail / SMTP fallback communication patterns.
   - Existing 46 unit/integration test specifications and contracts.

---

## 7. What Should Be Refactored

1. **Backend Architecture:**
   - Modularize `src/smartbiz/main.py` into clean modules: `core/`, `models/`, `routers/`, `services/` (equipment, inspections, quotes, certificates, pdf, calendar, whatsapp, renewal), `database/`.
   - Support both SQLite (local development) and PostgreSQL (production) seamlessly.
2. **Authentication & RBAC:**
   - Introduce secure token/session authentication with password hashing and role enforcement (`SUPER_ADMIN`, `ADMIN`, `MANAGER`, `TECHNICIAN`, `CUSTOMER`).
3. **API Endpoints:**
   - Standardize all endpoints under `/api/v1/*` with consistent response envelopes and Pydantic validation schemas.
4. **Frontend Architecture:**
   - Provide a complete multi-page public website, customer portal, admin suite, and mobile technician web app with modern, responsive, accessible UI components.

---

## 8. What Should NOT Be Touched / Broken

1. Existing legacy endpoints (`/health`, `/api/v1/status`, `/api/v1/bookings`, `/api/v1/leads`, `/api/v1/quiz/*`, `/technician/complete/*`, `/bookings/{id}/pdf`, `/bookings/{id}/coc-pdf`) must remain backwards compatible so existing clients, scripts, and tests continue passing without regression.
2. Existing 46 automated tests in `tests/test_main.py` must remain 100% green at all times.
