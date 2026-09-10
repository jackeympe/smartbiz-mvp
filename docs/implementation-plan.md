# SmartBiz Fire — Master Implementation Plan (Phase 0)

**Lead Architect:** Quin Suchi  
**Project:** SmartBiz Fire Compliance & Service Management Platform  
**Target Production Domain:** `https://smartbizfire.co.za`  

---

## Phased Implementation Roadmap

### Phase 0: System Audit & Planning (COMPLETED)
- [x] Inspect existing repository, SQLite database, Starlette backend, and frontend pages.
- [x] Verify existing 46/46 unit and integration test suite.
- [x] Generate `docs/current-state.md`, `docs/architecture.md`, `docs/implementation-plan.md`, and `docs/progress.md`.

---

### Phase 1: Foundation & Modular Backend Architecture
- [ ] Implement database models & migration scripts supporting normalized entities: `users`, `customers`, `sites`, `equipment`, `inspections`, `jobs`, `quotes`, `certificates`, `notifications`.
- [ ] Implement secure authentication & RBAC engine (`SUPER_ADMIN`, `ADMIN`, `MANAGER`, `TECHNICIAN`, `CUSTOMER`) with password hashing and session tokens.
- [ ] Create standardized error handlers, security headers, rate limiting, and request logging.
- [ ] Ensure backward compatibility for all existing test suites.

---

### Phase 2: Comprehensive Public Multi-Page Website
- [ ] Build responsive South African fire-safety website with navigation and SEO:
  - Homepage (`/`) with Hero, Trust badges, Services grid, Industries, Equipment, Pricing, Testimonials, FAQ, and CTAs.
  - Dedicated service pages: `/services/fire-extinguishers`, `/services/fire-equipment`, `/services/fire-inspections`, `/services/fire-compliance`, `/services/safety-files`.
  - Industry vertical pages: `/industries/schools`, `/industries/restaurants`, `/industries/offices`, `/industries/retail`, `/industries/warehouses`, `/industries/factories`.
  - Company & legal pages: `/about`, `/contact`, `/resources`, `/privacy`, `/terms`.
  - Conversion flows: `/book-inspection`, `/request-quote`, interactive Compliance Quiz.
- [ ] Integrate WhatsApp direct messaging and South African localized CTAs (`Africa/Johannesburg` timezone, ZAR currency).

---

### Phase 3: Customer CRM & Multi-Site Hierarchy
- [ ] Build customer management APIs (`/api/v1/customers`, `/api/v1/sites`, `/api/v1/contacts`).
- [ ] Implement lead ingestion, automatic conversion to customer & site records upon booking.
- [ ] Add CRM activity timeline tracking customer interactions, site visits, and job history.

---

### Phase 4: Fire Operations, Equipment Register & QR System
- [ ] Build Equipment Register API (`/api/v1/equipment`) supporting DCP, CO2, Foam, Hose Reels, Hydrants, Blankets, Alarms.
- [ ] Implement unique QR code generation (e.g. `SB-FE-000184`) and public verification endpoint (`/equipment/{qr_code}`).
- [ ] Build mobile-first Technician Interface (`/technician`):
  - Daily assigned jobs list with priority and location.
  - Equipment scanning and on-site checklist execution.
  - Evidence notes, photo upload hooks, and customer signature capture.

---

### Phase 5: Document & PDF Generation Engine
- [ ] Build professional ReportLab PDF generators:
  - Quotation PDF (`/api/v1/documents/quotes/{id}/pdf`).
  - Inspection / Service Report PDF (`/api/v1/documents/inspections/{id}/pdf`).
  - Official Certificate of Compliance (COC) PDF with QR verification stamp (`/api/v1/documents/certificates/{id}/pdf`).
- [ ] Implement certificate lifecycle (`DRAFT` -> `REVIEW` -> `ISSUED` -> `EXPIRED`) with audit trail.

---

### Phase 6: Customer Portal (`/portal`)
- [ ] Build Customer Portal dashboard:
  - Overall compliance status badge.
  - Multi-site overview and equipment list.
  - Active jobs and service history.
  - Quote review and one-click customer approval / decline.
  - Instant PDF report and certificate downloads.

---

### Phase 7: WhatsApp Integration Engine
- [ ] Build `WhatsAppProvider` abstraction supporting Meta Cloud API / WhatsApp Business Platform.
- [ ] Implement webhook receiver with signature validation and 2-way menu navigation.
- [ ] Implement automated transactional notifications (lead received, booking confirmation, technician dispatch, report ready, renewal reminder).

---

### Phase 8: Calendar Integration Engine
- [ ] Build `CalendarProvider` abstraction supporting Internal Calendar, Google Calendar, and Microsoft Outlook.
- [ ] Implement automated calendar event creation upon inspection booking and technician scheduling in `Africa/Johannesburg` timezone.

---

### Phase 9: Automated Renewal & Notification Scheduler
- [ ] Implement automated background renewal engine calculating upcoming equipment and certificate expirations.
- [ ] Schedule multi-tier reminder notifications (90, 60, 30, 14, 7 days before due date).
- [ ] Implement deduplication and notification delivery logging.

---

### Phase 10: Production Hardening, Acceptance Testing & Deployment
- [ ] Run full test suite (Unit, Integration, End-to-End Acceptance test journey from Lead -> Inspection -> Quote -> Job -> COC -> Renewal).
- [ ] Verify security, environment configurations (`.env.example`), and production build.
- [ ] Prepare deployment scripts for Cloudflare Pages (frontend) and Render/Fly (API).
- [ ] Produce Final Master Build Report.
