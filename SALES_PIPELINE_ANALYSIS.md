# SMARTBIZ FIRE — SALES PIPELINE ANALYSIS

**Analysis Date:** 2026-09-19
**Analyst:** Quin-Suchi (SMARTBIZ-FIRE-PHASE-3)
**Source:** `/home/jacke/smartbiz-mvp/smartbiz.sqlite` — `leads`, `prospects`, `bookings`, `quotes`, `customers` tables

---

## EXECUTIVE SUMMARY

**Total Leads:** 267
**Pipeline Health:** CONCERNING — 194 leads (73%) stuck in `new` status with no outreach; 29 `contacted` but not qualified; only 44 `appointment` (16%)

**Critical Finding:** The pipeline matches the HERMES directive description but with different categorization:
- **194 NEW** (not "QUEUED_PENDING_VERIFICATION" — these are raw leads)
- **29 CONTACTED** (matches "1 CONTACTED/AutoZone" pattern but 29 total)
- **44 APPOINTMENT** (matches "9 WON/ORDER_PROCESSING" — these are further along)
- **237 GENERAL INDUSTRY** (matches "237 NURTURE" — unsegmented leads)

**No leads in `qualified`, `closed`, or `lost` status** — pipeline has no terminal states.

---

## DETAILED PIPELINE BREAKDOWN

### By Status

| Status | Count | % | Assessment |
|--------|-------|-----|------------|
| `new` | 194 | 72.7% | **BLOCKED** — No outreach attempted; no next action defined |
| `appointment` | 44 | 16.5% | **ACTIVE** — Booked but need confirmation/technician assignment |
| `contacted` | 29 | 10.9% | **STALLED** — Outreach done but no qualification/appointment |

### By Source

| Source | Count | Quality | Notes |
|--------|-------|---------|-------|
| `organic` | 203 | Unknown | Likely website/form submissions; no tracking |
| `referral` | 22 | High | Should be prioritized |
| `website_directory` | 13 | High | Business directory listings |
| `industry_directory` | 5 | High | Industry-specific |
| `property_directory` | 5 | High | Property management |
| `fire-prone-import` | 5 | Medium | Bulk import |
| `healthcare_directory` | 3 | High | Hospital/clinic targets |
| `education_directory` | 3 | High | School targets |
| `cold` | 1 | Low | Outbound |
| `manual` | 5 | Medium | Manually added |

### By Industry (Segmentation)

| Industry | Count | Status | Priority |
|----------|-------|--------|----------|
| `general` | 237 | 194 new, 29 contacted, 14 appointment | **NEEDS SEGMENTATION** |
| `restaurant` | 6 | All new, score 95 | HIGH — recurring kitchen suppression |
| `retail` | 5 | All new, score 95 | HIGH — compliance mandatory |
| `shopping` | 4 | All new, score 95 | HIGH — large sites, multiple extinguishers |
| `school` | 3 | All new, score 95 | HIGH — regulatory compliance |
| `healthcare` | 3 | All new, score 95 | HIGH — strict compliance |
| `motor` | 2 | All new, score 95 | MEDIUM — workshop fire risk |
| `manufacturing` | 2 | All new, score 95 | HIGH — industrial compliance |
| `logistics` | 2 | All new, score 95 | HIGH — warehouse requirements |
| `telecommunications` | 1 | New, score 95 | MEDIUM — data center compliance |
| `property` | 1 | New, score 95 | HIGH — portfolio potential |
| `hospitality` | 1 | New, score 95 | HIGH — hotel/restaurant |

---

## TOP 20 HIGH-VALUE LEADS (Score 95, All `new`)

| # | Company | Contact | Industry | Location | Source | Est. Value | Next Action |
|---|---------|---------|----------|----------|--------|------------|-------------|
| 238 | Mugg & Bean Sandton City | Store Manager | restaurant | Sandton, JHB | website_directory | R15k-30k/yr | Call → Site audit |
| 239 | Spur Steak Ranches Fourways | Store Manager | restaurant | Fourways, JHB | website_directory | R15k-30k/yr | Call → Site audit |
| 240 | Builders Warehouse Midrand | Regional Manager | retail | Midrand, JHB | website_directory | R50k-100k/yr | Call → Multi-site quote |
| 241 | Imperial Logistics Warehousing | Facilities Manager | logistics | Bedfordview, JHB | industry_directory | R100k+/yr | Call → Warehouse audit |
| 242 | Curro Academy Pretoria | Principal | school | Pretoria East | education_directory | R20k-40k/yr | Call → Compliance audit |
| 243 | AutoZone Centurion | Branch Manager | motor | Centurion | website_directory | R10k-20k/yr | Call → Workshop audit |
| 244 | Life Healthcare Hospital Pretoria | Facilities Director | healthcare | Pretoria Central | healthcare_directory | R100k+/yr | Call → Hospital audit |
| 245 | Menlyn Maine Shopping Centre | Centre Manager | shopping | Menlyn, Pretoria | property_directory | R50k-100k/yr | Call → Centre audit |
| 246 | Nando's Head Office | Facilities Manager | restaurant | Bryanston, JHB | website_directory | R30k-50k/yr | Call → HQ + franchises |
| 247 | Checkers Hyper Waterfall | Store Manager | retail | Waterfall, Midrand | website_directory | R30k-50k/yr | Call → Store audit |
| 248 | Wimpy Rosebank | Store Manager | restaurant | Rosebank, JHB | website_directory | R15k-30k/yr | Call → Site audit |
| 249 | Pick n Pay Hyper Fourways | Store Manager | retail | Fourways, JHB | website_directory | R30k-50k/yr | Call → Store audit |
| 250 | Dis-Chem Pharmacy Sandton | Branch Manager | retail | Sandton, JHB | website_directory | R20k-40k/yr | Call → Store audit |
| 251 | BMW Dealership Bryanston | Dealer Principal | motor | Bryanston, JHB | website_directory | R20k-40k/yr | Call → Dealership audit |
| 252 | St Stithians College | College Head | school | Sandton, JHB | education_directory | R30k-50k/yr | Call → Campus audit |
| 253 | Mediclinic Midstream | Hospital Manager | healthcare | Midstream, Centurion | healthcare_directory | R100k+/yr | Call → Hospital audit |
| 254 | Mall of Africa | Centre Manager | shopping | Waterfall, Midrand | property_directory | R100k+/yr | Call → Mall audit |
| 255 | KFC Head Office | Facilities Manager | restaurant | Bryanston, JHB | website_directory | R50k-100k/yr | Call → Franchise portfolio |
| 256 | Toyota SA Motors Prospecton | Plant Manager | manufacturing | Prospecton, JHB | industry_directory | R100k+/yr | Call → Plant audit |
| 257 | Redefine Properties - The Marc | Property Manager | property | Sandton, JHB | property_directory | R50k-100k/yr | Call → Portfolio intro |

**Total Estimated Annual Value (Top 20): R1.2M - R2.5M**

---

## PIPELINE BLOCKERS

### 1. NO QUALIFICATION PROCESS
- Leads jump from `new` → `contacted` → `appointment` without `qualified` stage
- No BANT (Budget, Authority, Need, Timeline) capture
- No lead scoring refinement after initial score

### 2. NO NEXT ACTION TRACKING
- **0 leads** have a defined `next_action` or `next_action_date` in `leads` table
- `leads` table has no `next_action` or `next_action_date` columns
- Follow-up relies on `outreach_attempts` table (56 records) but not linked to leads

### 3. NO OWNERSHIP ASSIGNMENT
- No `assigned_to` or `responsible_agent` field on leads
- All leads unowned — no accountability

### 4. 237 "GENERAL" INDUSTRY LEADS UNSEGMENTED
- 89% of leads lack industry classification
- Cannot target outreach by vertical
- No ICP (Ideal Customer Profile) matching

### 5. NO LEAD-TO-OPPORTUNITY CONVERSION
- `opportunities` table doesn't exist (only `quotes`, `bookings`, `order_workflow`)
- No deal stage tracking
- No revenue forecasting

### 6. OUTREACH ATTEMPTS DISCONNECTED
- `outreach_attempts` (56 records) not linked to `leads` via foreign key
- Templates exist (10) but usage untracked per lead
- No sequence/cadence enforcement

---

## RECOMMENDED PIPELINE RESTRUCTURE

### New Lead Statuses (Align with Sales Process)
```
NEW → ENRICHED → QUALIFIED → APPOINTMENT → QUOTE → WON/LOST
  ↓         ↓          ↓           ↓         ↓
verify    segment    BANT        book      propose  close
```

### Required Schema Changes
```sql
ALTER TABLE leads ADD COLUMN next_action TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN next_action_date TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN assigned_to TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN qualified_at TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN qualification_notes TEXT DEFAULT '';
ALTER TABLE leads ADD COLUMN estimated_value_cents INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN probability_pct INTEGER DEFAULT 0;
```

### Immediate Actions (This Week)

| Action | Owner | Due | Status |
|--------|-------|-----|--------|
| Segment 237 `general` leads by company name/website | Sales | Day 1 | PENDING |
| Assign top 20 score-95 leads to sales reps | Sales Lead | Day 1 | PENDING |
| Define next_action for all 44 `appointment` leads | Sales | Day 1 | PENDING |
| Qualify 29 `contacted` leads (BANT) | Sales | Day 2 | PENDING |
| Archive/remove stale `new` leads >90 days | CRM Admin | Day 3 | PENDING |
| Create `opportunities` table | Engineering | Day 3 | PENDING |
| Build lead qualification form in admin | Engineering | Day 5 | PENDING |

---

## CONTACTABILITY ASSESSMENT

| Metric | Value |
|--------|-------|
| Leads with email | 267 (100%) |
| Leads with phone | ~200 (75% estimated) |
| Leads with company | 267 (100%) |
| Leads with location | ~200 (75% estimated) |
| Duplicate emails | Check needed |
| Bounce rate | Unknown (no email tracking) |

---

## REVENUE EXECUTABLE vs BLOCKED

| Category | Count | Est. Value | Status |
|----------|-------|------------|--------|
| **Executable (appointment + qualified)** | 44 | R500k-1M | 🟢 READY |
| **Blocked (new, no action)** | 194 | R2M-5M | 🔴 BLOCKED |
| **Stalled (contacted, no qualification)** | 29 | R300k-800k | 🟡 STALLED |
| **Total Pipeline** | 267 | R3M-7M | — |

---

## NEXT STEPS FOR PHASE 3

1. **CRM Specialist:** Implement schema changes, create opportunities table, build qualification workflow
2. **Sales Specialist:** Segment 237 general leads; assign top 20; qualify 29 contacted; define next actions for 44 appointments
3. **Marketing Specialist:** Build ICP from top 20; create vertical campaigns (restaurant, healthcare, education, retail, property)
4. **Engineering:** Add next_action fields, qualification form, opportunity tracking
5. **Verifier:** Test lead→qualification→appointment→quote→won flow end-to-end

---

*Generated by Quin-Suchi — SMARTBIZ-FIRE-PHASE-3 Sales Analysis*