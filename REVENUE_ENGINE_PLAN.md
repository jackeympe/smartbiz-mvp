# SmartBiz Fire Revenue Engine - Implementation Plan

**Created:** 2026-09-18
**Status:** IN PROGRESS

---

## PHASE 1: FOUNDATION (Day 1-2)

### 1.1 Extend Leads Schema
Add missing directive fields to `leads` table:
- `job_title` TEXT
- `whatsapp` TEXT
- `website` TEXT
- `business_type` TEXT
- `estimated_size` TEXT
- `fire_safety_relevance` TEXT
- `existing_supplier` TEXT
- `lead_source` TEXT (distinct from existing `source`)
- `lead_status` TEXT DEFAULT 'NEW' (per directive statuses)
- `last_contact` TEXT
- `next_action` TEXT
- `notes` TEXT
- `opportunity_value_cents` INTEGER DEFAULT 0
- `probability_pct` INTEGER DEFAULT 0
- `assigned_agent` TEXT

### 1.2 Create Lead Scoring Function
Implement directive scoring algorithm:
- +20 identifiable commercial premises
- +20 clear fire-equipment requirement
- +15 multiple extinguishers/equipment likely required
- +15 recurring servicing potential
- +10 decision-maker identified
- +10 phone/WhatsApp available
- +10 email available
- Max 100
- Classification: 80-100 HIGH, 60-79 MEDIUM, 40-59 LOW, <40 NURTURE

### 1.3 Create Prospects Table (Separate from Leads)
For raw prospect data before qualification:
- Company research fields
- Industry categorization
- Contact discovery tracking
- Source attribution

### 1.4 Extend Quotes with Pipeline Fields
Add: `follow_up_date`, `customer_response`, `won_lost_reason`, `quote_stage`

---

## PHASE 2: PROSPECTING ENGINE (Day 2-3)

### 2.1 Prospect Generation Agent
- Industry targeting per ICP (restaurants, retail, warehouses, etc.)
- Gauteng geographic focus
- Company identification via public sources
- Contact discovery

### 2.2 Qualification Workflow
- Research → Score → Qualify → Assign
- Automated scoring on prospect creation
- Status transitions: NEW → RESEARCHED → QUALIFIED

---

## PHASE 3: OUTREACH ENGINE (Day 3-4)

### 3.1 Communication Templates
- WhatsApp templates (short, CTA-focused)
- Email templates
- Call scripts

### 3.2 Outreach Scheduler
- Cadence automation (Day 0, 1, 3, 7, 14)
- Opt-out handling
- Channel selection

### 3.3 Outreach Tracking
- Log every attempt in `job_events` or new `outreach_attempts` table
- Response recording
- Status updates

---

## PHASE 4: SALES PIPELINE (Day 4-5)

### 4.1 Pipeline Stages
NEW → QUALIFIED → CONTACTED → CONVERSATION → ASSESSMENT → QUOTE → FOLLOW_UP → WON/LOST

### 4.2 Quote Follow-up Automation
- Automated follow-up scheduling
- Reminder generation
- Stage progression tracking

---

## PHASE 5: REVENUE DASHBOARD (Day 5-6)

### 5.1 Daily Metrics
- New leads, qualified, outreach, responses, appointments, quotes, sales, revenue, outstanding, follow-ups due

### 5.2 Weekly/Monthly Aggregates
- Pipeline value, won revenue, avg deal value, conversion rates
- Revenue by service, industry, channel

### 5.3 Commander Report Format
Per directive specification

---

## PHASE 6: AGENT ORCHESTRATION (Day 6-7)

### 6.1 Specialized OpenClaw Agents
- PROSPECTOR, QUALIFIER, OUTREACH, APPOINTMENT, QUOTER, FOLLOWUP, CRM, COMPLIANCE, ANALYST, VERIFIER

### 6.2 Approval Gates
- Human approval for contracts, certifications, pricing outside rules, payments

---

## IMMEDIATE NEXT ACTIONS (Next 2 Hours)

1. [ ] Extend leads table schema (migration)
2. [ ] Create lead scoring module
3. [ ] Build prospect generation workflow
4. [ ] Create first 100-prospect acquisition plan
5. [ ] Set up revenue dashboard API endpoints
6. [ ] Report blockers requiring human intervention

---

## BLOCKERS REQUIRING HUMAN INTERVENTION

1. **Prospect data source** - Need approved data sources for Gauteng business directories
2. **Communication channels** - WhatsApp Business API / AgentMail credentials needed
3. **Pricing rules** - Approved pricing matrix for standard services
4. **Compliance sign-off** - Authorized signatory for certificates
5. **Payment processing** - PayFast production credentials

---

## KPI TARGETS (First 30 Days)

- 100 qualified prospects in database
- 50 outreach attempts
- 10 conversations
- 5 appointments
- 3 quotes sent
- 1 won deal
- Revenue dashboard operational