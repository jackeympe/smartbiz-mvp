# SmartBiz Fire — Target Architecture (Phase 0)

**Version:** 2.0.0  
**Lead Architect:** Quin Suchi  
**Domain:** `smartbizfire.co.za`  

---

## 1. System Overview & Core Workflow

SmartBiz Fire is designed as an end-to-end digital operating system for South African fire protection and safety compliance operations. The architecture strictly models the real-world business lifecycle:

```text
LEAD (Web / WhatsApp / Referral)
  ↓
CUSTOMER & SITE REGISTRATION
  ↓
INSPECTION REQUEST (/book-inspection)
  ↓
CALENDAR SCHEDULING (Google / Outlook / Internal)
  ↓
TECHNICIAN ASSIGNMENT & DISPATCH
  ↓
MOBILE ON-SITE INSPECTION & EQUIPMENT QR SCAN
  ↓
CHECKLIST & EVIDENCE CAPTURE (Photos, Notes, Signatures)
  ↓
QUOTE GENERATION (/request-quote) & CUSTOMER APPROVAL
  ↓
JOB EXECUTION & QUALITY REVIEW
  ↓
DOCUMENT GENERATION (Inspection Report, Service Summary)
  ↓
CERTIFICATE ISSUANCE (COC with unique ID & verification link)
  ↓
INVOICING & PAYMENT (Zoho Books / PayFast)
  ↓
JOB COMPLETION & AUDIT EVENT LOGGING
  ↓
AUTOMATED RENEWAL REMINDER ENGINE (90 / 60 / 30 / 14 / 7 days)
  ↓
NEXT SERVICE SCHEDULING
```

---

## 2. Technology Stack

### Backend Architecture
- **Language & Runtime:** Python 3.11+ / FastAPI / Starlette / Uvicorn.
- **Data Validation & Schemas:** Pydantic v2.
- **Database Layer:** Normalized relational schema with dual-engine support: SQLite for local offline-first development, PostgreSQL for cloud production with SQL migrations.
- **PDF & Document Generation:** ReportLab 5.0+ producing branded A4 documents with QR verification stamps and digital signature placeholders.
- **Async & Background Scheduling:** Built-in lightweight scheduler / cron worker for renewal reminder processing and notification dispatch.

### Frontend Architecture
- **Public Website & Customer Portal:** Modern responsive HTML5/CSS3/JavaScript SPA/MPA hybrid with clean semantic styling, zero external bloat, and fast mobile rendering.
- **Design Tokens & Theme:**
  - Background: `#0b1220` (Dark navy / slate)
  - Cards: `#111c33`
  - Accents: `#f97316` (Fire safety orange), `#fb923c`
  - Success: `#22c55e` (Compliant green)
  - Error: `#ef4444` (Non-compliant / overdue red)
- **Technician Web App:** Mobile-first interface designed for low-bandwidth on-site use, featuring PIN authentication, one-tap QR scanner integration, step-by-step checklist execution, and customer signature canvas.

### Integrations & Adapters
- **WhatsApp Provider:** Pluggable `WhatsAppProvider` supporting Meta Cloud API / WhatsApp Business Platform, webhook verification, interactive message flows, and fallback notification dispatch.
- **Calendar Provider:** Pluggable `CalendarProvider` supporting Internal Calendar, Google Calendar API (OAuth2 / Service Account), and Microsoft Graph Outlook Calendar API with `Africa/Johannesburg` timezone synchronization.
- **Accounting & Payments:** Zoho Books API v3 (Contacts, Invoices, Customer Payments, Credit Notes) and PayFast sandbox / production payment gateway with IPN signature verification.
- **Email & Communications:** Multi-tier email provider with SMTP primary and AgentMail transactional fallback.

---

## 3. Database Schema (Normalized Entity-Relationship Model)

```text
┌──────────────┐       ┌────────────────┐       ┌─────────────┐
│    users     │◀─────▶│ customer_users │◀─────▶│  customers  │
└──────────────┘       └────────────────┘       └─────────────┘
       │                                               │
       ▼                                               ▼
┌──────────────┐                                ┌─────────────┐
│ technicians  │                                │    sites    │
└──────────────┘                                └─────────────┘
       │                                               │
       ▼                                               ▼
┌──────────────┐       ┌────────────────┐       ┌─────────────┐
│     jobs     │◀─────▶│  inspections   │◀─────▶│  equipment  │
└──────────────┘       └────────────────┘       └─────────────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐       ┌────────────────┐       ┌─────────────┐
│  job_events  │       │  certificates  │       │ serv_history│
└──────────────┘       └────────────────┘       └─────────────┘
       │                       │
       ▼                       ▼
┌──────────────┐       ┌────────────────┐
│    quotes    │       │ notifications  │
└──────────────┘       └────────────────┘
```

### Key Entities & Attributes

1. **`users`**: `id`, `email`, `password_hash`, `full_name`, `role` (`SUPER_ADMIN`, `ADMIN`, `MANAGER`, `TECHNICIAN`, `CUSTOMER`), `is_active`, `created_at`, `updated_at`.
2. **`customers`**: `id`, `company_name`, `account_number`, `contact_name`, `email`, `phone`, `whatsapp_number`, `billing_address`, `vat_number`, `created_at`, `updated_at`.
3. **`sites`**: `id`, `customer_id`, `site_name`, `address`, `suburb`, `city`, `province`, `postal_code`, `building_type`, `occupancy_type`, `contact_person`, `contact_phone`, `created_at`.
4. **`equipment`**: `id`, `qr_code` (e.g. `SB-FE-000184`), `site_id`, `serial_number`, `equipment_type` (`DCP_EXTINGUISHER`, `CO2_EXTINGUISHER`, `WATER_EXTINGUISHER`, `FOAM_EXTINGUISHER`, `WET_CHEMICAL`, `HOSE_REEL`, `HYDRANT`, `FIRE_BLANKET`, `FIRE_SIGN`, `FIRE_ALARM`, `SPRINKLER`, `OTHER`), `location_on_site`, `capacity`, `manufacturer`, `model_year`, `install_date`, `last_service_date`, `next_service_date`, `status` (`COMPLIANT`, `DUE`, `OVERDUE`, `FAILED`, `MISSING`), `notes`, `created_at`.
5. **`inspections`**: `id`, `site_id`, `technician_id`, `scheduled_date`, `status` (`REQUESTED`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `REVIEWED`), `overall_score`, `checklist_data` (JSON), `findings_summary`, `recommendations`, `signature_url`, `created_at`.
6. **`jobs`**: `id`, `job_number` (e.g. `JOB-2026-0052`), `customer_id`, `site_id`, `technician_id`, `job_type`, `scheduled_at`, `started_at`, `completed_at`, `status` (`NEW`, `SCHEDULED`, `ASSIGNED`, `EN_ROUTE`, `ARRIVED`, `IN_PROGRESS`, `AWAITING_REVIEW`, `COMPLETED`, `CANCELLED`), `priority`, `evidence_notes`, `evidence_photos` (JSON), `customer_signature`, `created_at`.
7. **`quotes`**: `id`, `quote_number` (e.g. `QT-2026-0041`), `customer_id`, `site_id`, `status` (`DRAFT`, `SENT`, `VIEWED`, `APPROVED`, `DECLINED`, `EXPIRED`), `subtotal_cents`, `vat_cents` (15%), `total_cents`, `line_items` (JSON), `valid_until`, `terms`, `created_at`.
8. **`certificates`**: `id`, `certificate_number` (e.g. `COC-2026-0891`), `customer_id`, `site_id`, `inspection_id`, `issue_date`, `expiry_date`, `scope_of_inspection`, `signatory_name`, `signatory_title`, `status` (`DRAFT`, `ISSUED`, `EXPIRED`, `REVOKED`), `pdf_url`, `created_at`.
9. **`leads`**: `id`, `first_name`, `last_name`, `email`, `phone`, `company`, `interest`, `status` (`NEW`, `CONTACTED`, `QUALIFIED`, `INSPECTION_REQUESTED`, `INSPECTION_BOOKED`, `QUOTE_SENT`, `APPROVED`, `LOST`, `CONVERTED`), `source`, `score`, `industry`, `location`, `message`, `created_at`, `updated_at`.
10. **`notifications`**: `id`, `recipient`, `channel` (`EMAIL`, `WHATSAPP`, `IN_APP`), `template_key`, `payload` (JSON), `status` (`QUEUED`, `SENT`, `DELIVERED`, `FAILED`), `scheduled_for`, `sent_at`, `created_at`.

---

## 4. API Architecture & Versioning

All business APIs reside under `/api/v1/*`. Legacy endpoints remain mapped for backward compatibility.

### Authentication & Core Endpoints
- `POST /api/v1/auth/login` — Login for Admin, Technician, Customer (JWT / session token).
- `POST /api/v1/auth/logout` — Invalidate session.
- `GET /api/v1/auth/me` — Current user context and role permissions.
- `GET /health` — Service health and subsystem statuses.

### CRM & Operations
- `/api/v1/leads` [GET, POST] — Lead management, filtering, and scoring.
- `/api/v1/customers` [GET, POST, GET/{id}, PATCH/{id}] — Customer account management.
- `/api/v1/sites` [GET, POST, GET/{id}, PATCH/{id}] — Site locations per customer.
- `/api/v1/equipment` [GET, POST, GET/{id}, PATCH/{id}] — Fire equipment register.
- `/api/v1/equipment/qr/{qr_code}` [GET] — Scan lookup for mobile technicians and public asset verification.
- `/api/v1/inspections` [GET, POST, GET/{id}, PATCH/{id}] — Inspection scheduling and checklist recording.
- `/api/v1/jobs` [GET, POST, GET/{id}, PATCH/{id}] — Job scheduling, dispatch, and completion.
- `/api/v1/quotes` [GET, POST, GET/{id}, PATCH/{id}, POST/{id}/approve] — Quote generator and customer approval flow.
- `/api/v1/certificates` [GET, POST, GET/{id}, GET/{id}/verify] — Certificate issuance and verification.

### Document & PDF Endpoints
- `GET /api/v1/documents/quotes/{quote_id}/pdf` — Branded quote PDF.
- `GET /api/v1/documents/inspections/{inspection_id}/pdf` — Comprehensive inspection report PDF.
- `GET /api/v1/documents/certificates/{certificate_id}/pdf` — Official Certificate of Compliance (COC) PDF.

### Integrations & Webhooks
- `POST /api/v1/webhooks/whatsapp` — Meta Cloud API webhook receiver.
- `POST /api/v1/webhooks/payfast` — PayFast Instant Payment Notification (IPN) receiver.
- Accounting webhooks are provider-specific and are exposed only through the provider-neutral accounting integration boundary.
- `GET /api/v1/calendar/events` [GET, POST] — Calendar sync provider endpoint.

---

## 5. Role-Based Access Control (RBAC) Matrix

| Feature / Resource | SUPER_ADMIN | ADMIN | MANAGER | TECHNICIAN | CUSTOMER |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Leads & Marketing** | Full | Full | Full | View Assigned | No |
| **Customer CRM** | Full | Full | Full | View Assigned | View Own |
| **Sites & Equipment** | Full | Full | Full | Update Status | View Own |
| **Inspections & Checklists** | Full | Full | Full | Complete Assigned | View Own |
| **Service Jobs** | Full | Full | Full | Complete Assigned | View Own |
| **Quotes & Invoices** | Full | Full | Full | No | View & Approve |
| **Certificates** | Full | Issue / Revoke | Issue | Draft Findings | View & Download |
| **System Settings & Users**| Full | Manage Users | View Only | No | No |

---

## 6. Security, South African Localization & Compliance

1. **South African Context:**
   - Currency: **South African Rand (ZAR)**, stored as integer cents to prevent floating point errors.
   - Timezone: `Africa/Johannesburg` (SAST, UTC+02:00) strictly enforced across all timestamps and calendar events.
   - VAT: 15% configurable standard rate.
   - Phone Numbers: Normalized to `+27` international format (e.g. `+27634965466` -> `+27677684582`).
2. **Data Protection & Privacy:**
   - Public QR equipment verification shows equipment status and validity without leaking customer names, financials, or internal technician notes.
   - Secrets are managed exclusively via environment variables; never committed to version control.
   - All input undergoes strict Pydantic validation; SQL queries use parameterized prepared statements.
