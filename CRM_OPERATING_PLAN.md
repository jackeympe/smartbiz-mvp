# SMARTBIZ FIRE — CRM OPERATING PLAN

**Created:** 2026-09-20
**Owner:** CRM Specialist (Quin-Suchi delegated)
**Status:** ACTIVE — Phase 3 Execution
**Source of Truth:** `/home/jacke/smartbiz-mvp/smartbiz.sqlite` — All leads, customers, sites, equipment, inspections, quotes, certificates, bookings, jobs, technicians, users, notifications, calendar_events, prospects, outreach_attempts, outreach_templates, pricing_config, renewals, order_workflow, enrichment_queue

---

## 1. CRM MISSION

**Become the single source of truth for:**
- Leads (prospects → qualified → opportunities)
- Companies (customers, prospects, partners)
- Contacts (decision-makers, influencers, technicians)
- Sites (physical locations with fire equipment)
- Equipment (extinguishers, hose reels, hydrants, sprinklers, signage, alarms)
- Equipment Service History (every service, inspection, repair)
- Inspections (scheduled, completed, findings, reports)
- Jobs (field work orders, technician assignment, completion)
- Quotes (generated, sent, followed up, won/lost)
- Certificates (COC issued, verified, renewed)
- Conversations (WhatsApp, email, call logs, notes)
- Activities (every touchpoint, task, follow-up)
- Customers (active, recurring, churned)
- Follow-ups (scheduled, due, overdue, completed)
- Renewals (equipment services, certificate expiries)

**Every active lead must have a next action.**
**Every opportunity must have a status.**
**Every customer interaction must be traceable.**

---

## 2. CURRENT STATE ASSESSMENT

### 2.1 Database Tables (25+ tables, 2,000+ records)

| Table | Records | Purpose | Status |
|-------|---------|---------|--------|
| `leads` | 267 | Raw lead capture | ⚠️ Missing qualification fields |
| `prospects` | 31 | Pre-qualification research | ⚠️ Only CONVERTED/NEW |
| `customers` | 21 | Active customers | ✅ Good |
| `sites` | 24 | Customer locations | ✅ Good |
| `equipment` | 10 | Fire equipment register | ⚠️ Low count |
| `equipment_service_history` | 0 | Service records | ❌ Empty |
| `inspections` | 11 | Site inspections | ✅ Working |
| `quotes` | 19 | Quotations | ⚠️ All PRICING_PENDING_APPROVAL |
| `certificates` | 10 | COCs issued | ✅ Working |
| `bookings` | 718 | Appointments | ✅ High volume |
| `technicians` | 76 | Field staff | ✅ High count |
| `jobs` | 202 | Work orders | ✅ Working |
| `order_workflow` | ? | Order processing | ⚠️ No status column |
| `renewals` | 10 | Renewal tracking | ✅ Auto-created |
| `notifications` | 0 | Notification queue | ❌ Empty (worker not running) |
| `outreach_attempts` | 56 | Outreach log | ⚠️ Not linked to leads |
| `outreach_templates` | 10 | Message templates | ✅ Defined |
| `pricing_config` | 24 | Service pricing | ⚠️ All PENDING_APPROVAL |
| `enrichment_queue` | ? | Data enrichment | ⚠️ Unknown status |
| `calendar_events` | 11 | Scheduling | ✅ Working |
| `users` | 1 | System users | ⚠️ Only 1 admin |

### 2.2 Critical Gaps

| Gap | Impact | Fix |
|-----|--------|-----|
| No `opportunities` table | No deal pipeline tracking | Create table |
| No `next_action` on leads | Sales doesn't know what to do | Add columns |
| No `assigned_agent` on leads | No ownership | Add column |
| No `lead_status` pipeline stages | Can't track funnel | Add column + values |
| `outreach_attempts` not linked to `leads` | Can't measure outreach effectiveness | Add `lead_id` FK |
| `notifications` table empty | No automated reminders | Start worker |
| `pricing_config` all pending | Can't send real quotes | Approve pricing |
| No `activities` table | No unified interaction log | Create table |
| No `conversations` table | WhatsApp/email/call logs scattered | Create table |

---

## 3. SCHEMA MIGRATIONS REQUIRED

### 3.1 Leads Table Extensions (Priority 1)
```sql
-- Lead pipeline & ownership
ALTER TABLE leads ADD COLUMN lead_status TEXT DEFAULT 'NEW';  -- NEW, ENRICHED, QUALIFIED, CONTACTED, APPOINTMENT, QUOTE, WON, LOST, NURTURE
ALTER TABLE leads ADD COLUMN assigned_agent TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN next_action TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN next_action_date TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN last_contact TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN qualification_notes TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN opportunity_value_cents INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN probability_pct INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN job_title TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN whatsapp TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN website TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN business_type TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN estimated_size TEXT DEFAULT '';  -- '1-10','11-50','51-200','201-500','500+'
ALTER TABLE leads ADD COLUMN fire_safety_relevance TEXT DEFAULT '';  -- 'high','medium','low'
ALTER TABLE leads ADD COLUMN existing_supplier TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN lead_source TEXT DEFAULT '';  -- granular campaign source
ALTER TABLE leads ADD COLUMN utm_params TEXT DEFAULT '{}';  -- JSON
ALTER TABLE leads ADD COLUMN enrichment_data TEXT DEFAULT '{}';  -- JSON

-- Indexes
CREATE INDEX idx_leads_status ON leads(lead_status);
CREATE INDEX idx_leads_assigned ON leads(assigned_agent);
CREATE INDEX idx_leads_next_action ON leads(next_action_date);
CREATE INDEX idx_leads_score ON leads(score DESC);
```

### 3.2 Opportunities Table (Priority 1)
```sql
CREATE TABLE opportunities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id INTEGER NOT NULL,
  customer_id INTEGER DEFAULT 0,
  site_id INTEGER DEFAULT 0,
  name TEXT NOT NULL,
  stage TEXT NOT NULL DEFAULT 'QUALIFIED',  -- QUALIFIED, APPOINTMENT, QUOTE, NEGOTIATION, WON, LOST
  value_cents INTEGER NOT NULL DEFAULT 0,
  probability_pct INTEGER NOT NULL DEFAULT 0,
  expected_close_date TEXT DEFAULT '',
  assigned_agent TEXT DEFAULT '',
  next_action TEXT DEFAULT '',
  next_action_date TEXT DEFAULT '',
  lost_reason TEXT DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(lead_id) REFERENCES leads(id)
);
CREATE INDEX idx_opp_stage ON opportunities(stage);
CREATE INDEX idx_opp_assigned ON opportunities(assigned_agent);
CREATE INDEX idx_opp_close ON opportunities(expected_close_date);
```

### 3.3 Activities Table (Priority 2) — Unified Interaction Log
```sql
CREATE TABLE activities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,  -- 'lead', 'customer', 'opportunity', 'quote', 'job', 'inspection'
  entity_id INTEGER NOT NULL,
  activity_type TEXT NOT NULL,  -- 'call', 'email', 'whatsapp', 'meeting', 'site_visit', 'note', 'task', 'system'
  direction TEXT NOT NULL DEFAULT 'outbound',  -- 'inbound', 'outbound', 'internal'
  subject TEXT DEFAULT '',
  body TEXT DEFAULT '',
  outcome TEXT DEFAULT '',  -- 'connected', 'voicemail', 'no_answer', 'replied', 'booked', 'declined'
  duration_seconds INTEGER DEFAULT 0,
  performed_by TEXT DEFAULT '',  -- agent name or 'system'
  scheduled_at TEXT DEFAULT '',
  completed_at TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  metadata TEXT DEFAULT '{}'  -- JSON for flexible data
);
CREATE INDEX idx_act_entity ON activities(entity_type, entity_id);
CREATE INDEX idx_act_date ON activities(completed_at);
CREATE INDEX idx_act_type ON activities(activity_type);
```

### 3.4 Conversations Table (Priority 2) — WhatsApp/Email Threads
```sql
CREATE TABLE conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel TEXT NOT NULL,  -- 'whatsapp', 'email', 'phone', 'in_person'
  external_thread_id TEXT DEFAULT '',  -- WhatsApp message ID, email thread ID
  customer_id INTEGER DEFAULT 0,
  lead_id INTEGER DEFAULT 0,
  subject TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open',  -- 'open', 'closed', 'archived'
  last_message_at TEXT DEFAULT '',
  last_message_preview TEXT DEFAULT '',
  unread_count INTEGER DEFAULT 0,
  assigned_agent TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_conv_customer ON conversations(customer_id);
CREATE INDEX idx_conv_lead ON conversations(lead_id);
CREATE INDEX idx_conv_status ON conversations(status);
```

### 3.5 Outreach Attempts Link (Priority 1)
```sql
ALTER TABLE outreach_attempts ADD COLUMN lead_id INTEGER DEFAULT 0;
ALTER TABLE outreach_attempts ADD COLUMN opportunity_id INTEGER DEFAULT 0;
CREATE INDEX idx_outreach_lead ON outreach_attempts(lead_id);
```

### 3.6 Notifications Worker (Priority 1)
```sql
-- Ensure notifications table has proper indexes
CREATE INDEX IF NOT EXISTS idx_notif_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notif_scheduled ON notifications(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_notif_recipient ON notifications(recipient);
```

---

## 4. CRM WORKFLOWS

### 4.1 Lead Lifecycle (Automated + Manual)

```
NEW (form submit/import)
  → Auto: Score, Enrich, Assign → ENRICHED
  → Sales: Qualify (BANT) → QUALIFIED
  → Sales: Book appointment → APPOINTMENT
  → Ops: Assessment → QUOTE
  → Sales: Send quote → QUOTE
  → Sales: Follow up → NEGOTIATION
  → Customer: Accept → WON (create opportunity, job, customer)
  → Customer: Decline → LOST (record reason)
  → If no action 90 days → NURTURE
```

### 4.2 Lead Status Transitions (Enforced by CRM)

| From | To | Trigger | Who | Required Fields |
|------|-----|---------|-----|-----------------|
| NEW | ENRICHED | Auto-enrichment complete | System | `enrichment_data`, `score` |
| ENRICHED | QUALIFIED | BANT confirmed | Sales | `qualification_notes`, `opportunity_value_cents`, `probability_pct` |
| ENRICHED | NURTURE | Score <40, no trigger | System | — |
| QUALIFIED | APPOINTMENT | Booking created | Sales | `next_action='assessment'`, `booking_id` |
| QUALIFIED | LOST | Disqualified | Sales | `lost_reason` |
| APPOINTMENT | QUOTE | Assessment done | Ops | `inspection_id`, `quote_id` |
| APPOINTMENT | LOST | No-show / cancelled | Sales | `lost_reason` |
| QUOTE | NEGOTIATION | Quote sent | Sales | `quote_id`, `next_action='follow_up'` |
| QUOTE | LOST | Declined / expired | Sales | `lost_reason` |
| NEGOTIATION | WON | Quote accepted | Sales | `opportunity_id`, `customer_id`, `job_id` |
| NEGOTIATION | LOST | Final decline | Sales | `lost_reason` |
| WON | — | — | — | Create `customer`, `site`, `job`, `opportunity` |
| NURTURE | QUALIFIED | Re-scored >60 or trigger | Marketing | — |
| NURTURE | LOST | Explicit opt-out | Sales | `lost_reason='opt_out'` |

### 4.3 Mandatory Next Action Rule
**Every lead with `lead_status` IN ('NEW','ENRICHED','QUALIFIED','APPOINTMENT','QUOTE','NEGOTIATION') MUST have:**
- `next_action` (specific, actionable: "Call Facilities Manager re: COC expiry")
- `next_action_date` (ISO date, within 7 days)
- `assigned_agent` (sales rep name)

**Validation:** Daily cron checks for violations → Alert sales lead.

---

## 5. CUSTOMER 360 VIEW (Per Customer Record)

When viewing a customer, show:
1. **Header:** Company, Account #, Status (Active/At Risk/Churned), Primary Contact, ARR
2. **Sites:** List with equipment count, last inspection, next COC expiry
3. **Equipment:** All equipment across sites, compliance status, next service dates
4. **Inspections:** History with scores, findings, certificates
5. **Quotes:** All quotes (won/lost/pending), pipeline value
6. **Jobs:** Completed, scheduled, overdue
7. **Certificates:** All COCs, expiry dates, renewal status
8. **Renewals:** Upcoming equipment services, certificate renewals
9. **Activities:** Complete interaction timeline (calls, emails, WhatsApp, visits)
10. **Conversations:** Open threads, unread messages
11. **Invoices/Payments:** (Future: Zoho integration)
12. **Health Score:** Composite (compliance % + renewal rate + NPS + ARR trend)

---

## 6. DAILY CRM OPERATIONS

### 6.1 Morning Standup (Sales Team, 08:30)
| Item | Source | Action |
|------|--------|--------|
| Leads with `next_action_date` = today | `leads` | Execute or reschedule |
| Overdue activities | `activities` | Complete or reassign |
| Expired quotes (`valid_until` < today) | `quotes` | Close or extend |
| Certificate expiries (7 days) | `certificates` | Trigger renewal campaign |
| Equipment services due (7 days) | `equipment` | Create jobs |
| New leads unassigned | `leads` | Assign to rep |

### 6.2 End-of-Day Logging (Mandatory)
Every interaction → `activities` table:
- Call: duration, outcome, notes, next action
- Email/WhatsApp: auto-log via webhook + manual outcome
- Meeting: attendees, decisions, next steps
- Site visit: photos, findings, equipment updates

### 6.3 Weekly Pipeline Review (Friday)
| Metric | Target | Source |
|--------|--------|--------|
| NEW → ENRICHED conversion | 100% | `leads` |
| ENRICHED → QUALIFIED rate | >30% | `leads` |
| QUALIFIED → APPOINTMENT rate | >60% | `leads` + `bookings` |
| APPOINTMENT → QUOTE rate | >80% | `bookings` + `quotes` |
| QUOTE → WON rate | >40% | `quotes` + `opportunities` |
| Average sales cycle | <21 days | `opportunities` |
| Pipeline coverage (3x quota) | >3.0 | `opportunities` |

---

## 7. AUTOMATION RULES (CRM-Level)

| Rule | Trigger | Action |
|------|---------|--------|
| **Auto-enrich** | Lead created | Clearbit/Companies House → `enrichment_data` |
| **Auto-score** | Lead created/enriched | `score_lead_v2()` → `score`, `classification` |
| **Auto-assign** | Lead qualified | Round-robin by industry → `assigned_agent` |
| **COC expiry sequence** | `certificates.expiry_date` in 90/60/30/14/7 days | Create `notifications` + `activities` |
| **Equipment service due** | `equipment.next_service_date` in 30/14/7 days | Create `notifications` + `job` (draft) |
| **Quote follow-up** | Quote sent, no response 2/5/7/14/30 days | Create `activities` + `outreach_attempts` |
| **Stale lead alert** | Lead no `next_action` >7 days | Alert `assigned_agent` + sales lead |
| **No-show follow-up** | `booking.status` = 'confirmed', past `created_at` + 2hrs | Create `activities` (missed) → reschedule |
| **Renewal opportunity** | `renewals.renewal_date` = today | Create `opportunity` (recurring) |
| **Birthday/anniversary** | Customer anniversary | Create `activity` (personal touch) |

---

## 8. DATA QUALITY STANDARDS

| Field | Standard | Validation |
|-------|----------|------------|
| Email | Valid format, deliverable | Regex + bounce tracking |
| Phone (SA) | +27 XX XXX XXXX or 0XX XXX XXXX | Regex + WhatsApp check |
| Company | Official CIPC name preferred | CIPC lookup on enrich |
| Site Address | Full physical address | Google Places autocomplete |
| Equipment QR | SB-FE-NNNNNN format | Unique, sequential |
| Certificate # | COC-YYYY-NNNN format | Unique, sequential |
| Quote # | QT-YYYY-NNNN format | Unique, sequential |
| Job # | JOB-YYYY-NNNN format | Unique, sequential |

**Deduplication:** Daily job on `email` + `company` + `phone` fuzzy match.

---

## 9. REPORTING & DASHBOARDS

### 9.1 Commander Dashboard (Daily)
- Total pipeline value by stage
- Leads by status, source, industry, assigned
- Activities completed today
- Overdue next actions
- Revenue: MTD, QTD, YTD vs target

### 9.2 Sales Rep Dashboard (Personal)
- My leads by status
- My overdue next actions
- My quotes pending follow-up
- My appointments this week
- My conversion rates

### 9.3 Marketing Dashboard
- Leads by source/campaign (UTM)
- MQL → SQL conversion by channel
- Content asset performance
- CAC by channel

### 9.4 Operations Dashboard
- Jobs scheduled this week
- Technician utilization
- Equipment compliance %
- Certificate expiry pipeline
- SLA adherence (response time, completion time)

---

## 10. INTEGRATION POINTS

| System | Sync Direction | Frequency | Data |
|--------|----------------|-----------|------|
| **WhatsApp Business API** | Bidirectional | Real-time | Conversations, leads, bookings |
| **Email (SMTP/AgentMail)** | Outbound + Inbound parse | Real-time | Outreach, notifications, quotes |
| **PayFast** | Inbound (IPN) | Real-time | Payment confirmation → booking/job |
| **Google Sheets** | Outbound (export) | On-demand | Lead lists, pipeline reports |
| **Zoho (Future)** | Bidirectional | Real-time | Customers, invoices, payments, quotes |
| **Calendar (Google/Outlook)** | Bidirectional | Real-time | Appointments, technician schedules |
| **Website Forms** | Inbound | Real-time | Leads, bookings, quote requests |

---

## 11. IMMEDIATE ACTION PLAN (Week 1)

| Day | Action | Owner | Deliverable |
|-----|--------|-------|-------------|
| **Mon** | Run schema migrations (3.1, 3.2, 3.5) | Engineering | Updated `smartbiz.sqlite` |
| **Mon** | Deploy `lead_scoring_v2.py` + auto-enrich | Engineering | Scoring on create |
| **Tue** | Build admin CRM views (Lead Kanban, Customer 360) | Engineering | `/admin/crm` pages |
| **Tue** | Link `outreach_attempts` to `leads` | Engineering | FK + migration |
| **Wed** | Start `notifications` worker (cron) | Engineering | Renewal/equipment alerts firing |
| **Wed** | Approve `pricing_config` (all 24 items) | Human + Sales | Quotes sendable |
| **Thu** | Segment 237 'general' leads by industry | Sales + Marketing | `leads.industry` updated |
| **Thu** | Assign top 50 leads (score ≥80) to reps | Sales Lead | `assigned_agent` populated |
| **Thu** | Define `next_action` for all 44 APPOINTMENT leads | Sales | `next_action`, `next_action_date` |
| **Fri** | Qualify 29 CONTACTED leads (BANT calls) | Sales | `lead_status` → QUALIFIED/LOST |
| **Fri** | Weekly pipeline review | All | Dashboard + actions |

---

## 12. PERMISSION MODEL (Least Privilege)

| Role | Leads | Customers | Opportunities | Quotes | Jobs | Equipment | Certificates | Admin |
|------|-------|-----------|---------------|--------|------|-----------|--------------|-------|
| **Super Admin** | CRUD | CRUD | CRUD | CRUD | CRUD | CRUD | CRUD | Full |
| **Sales Lead** | CRUD | Read | CRUD | CRUD | Read | Read | Read | Team mgmt |
| **Sales Rep** | CRUD (own) | Read (own) | CRUD (own) | CRUD (own) | Read (own) | Read | Read | — |
| **Marketing** | Create, Read | Read | Read | Read | — | — | — | Campaigns |
| **Operations** | Read | CRUD | Read | Read | CRUD | CRUD | CRUD | Scheduling |
| **Technician** | — | Read (assigned) | — | — | Update (assigned) | Update (assigned) | — | — |
| **Verifier** | Read | Read | Read | Read | Read | Read | Read | Audit |

---

## 13. VERIFICATION CHECKLIST (Per Verifier Requirement)

- [ ] Every lead has `lead_status` ∈ valid enum
- [ ] Every active lead has `next_action` + `next_action_date` + `assigned_agent`
- [ ] Every `outreach_attempts` row links to `lead_id`
- [ ] Every `booking` has `lead_id` (or creates lead)
- [ ] Every `quote` has `opportunity_id` (or creates one on won)
- [ ] Every `job` has `customer_id` + `site_id` + `technician_id`
- [ ] Every `certificate` has `customer_id` + `site_id` + `inspection_id`
- [ ] Every `equipment` has `site_id` + `customer_id` (via site)
- [ ] `notifications` worker running (check `sent_at` populated)
- [ ] No orphan records (FK integrity)
- [ ] Audit trail: `activities` covers all interactions
- [ ] `job_events` immutable (append-only)
- [ ] PII access logged (who viewed what, when)

---

## 14. BLOCKERS

| Blocker | Required From | Resolution |
|---------|---------------|------------|
| Schema migrations need deployment | Engineering | Deploy to `smartbiz-mvp` |
| Pricing approval (24 items) | Human (Director) | Sign off `pricing_config` |
| WhatsApp Business API verified | Human (Meta) | Enable outbound templates |
| Zoho credentials | Human (Zoho admin) | Configure in secret manager |
| SMTP/AgentMail credentials | Human | Configure email channel |

---

*This plan makes the SmartBiz Fire CRM the authoritative operational backbone. All specialist agents (Sales, Marketing, Engineering, Operations, Compliance, Verifier) read/write through this schema.*

**Next:** Engineering deploys migrations; Sales begins qualification; Marketing launches campaigns with UTM tracking; Verifier tests data integrity.

---

*Generated by CRM Specialist — SMARTBIZ-FIRE-PHASE-3*