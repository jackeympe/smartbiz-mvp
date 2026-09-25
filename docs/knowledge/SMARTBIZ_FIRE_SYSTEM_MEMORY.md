# SMARTBIZ FIRE — SYSTEM MEMORY

## 1. COMPANY

Company:
SmartBiz Fire (Pty) Ltd

Registration:
2025/515436/07

Business:
Fire protection, fire safety equipment servicing, inspections, compliance documentation, Certificates of Compliance, maintenance and recurring fire-safety services.

Primary operating principle:

Revenue → Customers → Operations → Systems → Automation → Scale → Profitability.

---

## 2. SMARTBIZ FIRE MVP

Repository:
smartbiz-mvp

Workspace:
~/.openclaw/workspace/projects/smartbiz-mvp

Primary source:
src/smartbiz/

Database:
SQLite currently used by the MVP.

API:
FastAPI / Starlette application running through Uvicorn.

Containerisation:
Docker Compose.

Services:
- api
- postgres

Important:
The current certificate implementation and database currently operate against SQLite despite PostgreSQL also existing in Docker.

---

## 3. AI ARCHITECTURE

OpenClaw:
Authoritative orchestration layer.

Responsibilities:
- routing
- approvals
- Discord
- authoritative operational memory
- agent coordination

Hermes:
Reasoning and execution layer.

Responsibilities:
- coding
- testing
- implementation
- technical execution
- specialist task execution

Do NOT run Hermes as a second independent Discord commander.

---

## 4. SMARTBIZ FIRE OPERATIONAL AGENTS

Commander
Sales
Compliance
Tender
Marketing
Approval
Security
System

Agents should operate from the shared SmartBiz Fire knowledge base.

---

## 5. CURRENT MVP CAPABILITIES

Customer management.

Site management.

Inspection scheduling.

Inspection completion.

Checklist results.

Certificate issuance.

Certificate lookup.

Certificate verification.

Certificate PDF generation.

Renewal scanning/reminder infrastructure.

Equipment QR lookup.

SMTP integration.

Booking workflow.

PayFast-related infrastructure.

---

## 6. CERTIFICATE WORKFLOW

Inspection:

POST /api/v1/inspections

Inspection completion:

POST /api/v1/inspections/{inspection_id}/complete

Certificate creation:

POST /api/v1/certificates

Certificate lookup:

GET /api/v1/certificates/{certificate_id}

Certificate PDF:

GET /api/v1/certificates/{certificate_id}/pdf

Public certificate verification:

GET /api/v1/certificates/verify/{certificate_number}

Renewal scan:

POST /api/v1/renewal/scan

Do not invent endpoint paths. Inspect routes_v2.py before adding or changing an endpoint.

---

## 7. VERIFIED TEST RECORD

Verified certificate:

COC-2026-0044

Certificate ID:
44

Inspection:
46

Customer:
MVP Test Customer

Site:
MVP Test Site

Issue:
2026-09-25

Expiry:
2027-09-25

Status:
ISSUED

Public verification smoke test:
PASS

Certificate verification returned:
verified=true

---

## 8. CURRENT TESTING STATE

Pytest is installed in the project's .venv.

Run:

python -m pytest -q

Previous result:

50 passed
3 failed

Known failures were related to:
1. admin authentication headers in inspection tests
2. SMTP test endpoint expected response
3. missing admin_headers variable in test_v2_features.py

Do not claim the regression suite is fully passing until pytest reports zero failures.

---

## 9. GIT

Current local branch:
remove-xero-add-zoho

GitHub repository:
jackeympe/smartbiz-mvp

GitHub CLI authentication:
configured as jackeympe

Use:

gh auth status

gh auth setup-git

Never use GitHub account passwords for git push.

Never commit:
- SQLite runtime database changes
- __pycache__
- *.pyc
- backup files
- secrets
- .env files

---

## 10. DEVELOPMENT RULES

Build production systems, not demonstrations.

Before modifying code:

1. inspect existing implementation
2. identify route/service/database dependencies
3. make the smallest safe change
4. run tests
5. run API smoke tests
6. inspect logs
7. verify database state
8. commit only verified source changes

Never claim a feature works without verification.

Never create a command that requires the user to paste broken fragments across multiple shell prompts.

Prefer complete one-line commands or complete shell blocks.

---

## 11. CERTIFICATE SAFETY

Certificate generation must use actual customer/site/inspection data.

Do not fabricate:
- inspectors
- registrations
- compliance findings
- signatures
- certificates
- regulatory claims

Signatory details must come from configured authorised data.

Verification must resolve against the database.

---

## 12. CURRENT ENGINEERING LESSONS

Common shell failure:
Commands split across lines caused fragments such as:

-H: command not found

Avoid this.

Use:

TOKEN="..."

followed by a complete command on one line, or use a complete heredoc/script.

Do not tell the operator to execute JSON as shell commands.

Do not tell the operator to execute output objects directly in Bash.

---

## 13. DATABASE LESSONS

SQLite is configured with:

journal_mode = WAL
busy_timeout = 5000

Certificate IDs observed:
42, 43, 44

Avoid ambiguous SQL columns such as:

SELECT id

when joining tables containing multiple id columns.

Use:

certificates.id AS certificate_id

---

## 14. OPERATING METHOD

OBSERVE
→ ORIENT
→ DECIDE
→ ACT
→ MEASURE
→ IMPROVE

Priority order:

1. Revenue
2. Customer acquisition
3. Sales conversations
4. Quotes
5. Fire-service operations
6. Compliance
7. Recurring revenue
8. Automation
9. Data
10. Scalable technology

---

## 15. SECURITY

Never expose:
- SMARTBIZ_ADMIN_TOKEN
- GitHub tokens
- API keys
- SMTP passwords
- PayFast credentials
- database credentials
- private customer information

Secrets belong in environment configuration, not source code or memory files.

---

## 16. NEXT ENGINEERING OBJECTIVE

Stabilise the renewal workflow.

Then achieve:

python -m pytest -q

with:

0 failed

After that:
- regression smoke test
- certificate PDF test
- certificate verification test
- renewal scan test
- Git commit
- GitHub push
- deployment verification

Only then move to the next product capability.
