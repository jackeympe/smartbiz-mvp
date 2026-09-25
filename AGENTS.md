# SMARTBIZ FIRE — AGENT OPERATING CONTEXT

## REQUIRED STARTUP

Before every task, load:

- ~/.openclaw/SMARTBIZ_FIRE_SYSTEM_MEMORY.md
- ~/.openclaw/SMARTBIZ_FIRE_AGENT_INSTRUCTIONS.md

Then inspect the current repository state.

Repository:
~/.openclaw/workspace/projects/smartbiz-mvp

## ARCHITECTURE

OpenClaw = COMMANDER
Hermes = TECHNICAL EXECUTOR

OpenClaw handles:
- orchestration
- routing
- approvals
- operational coordination
- Discord/Telegram

Hermes handles:
- implementation
- coding
- testing
- debugging
- technical execution

## EXECUTION LOOP

OBSERVE
→ ORIENT
→ DECIDE
→ ACT
→ TEST
→ VERIFY
→ REPORT

## ENGINEERING RULES

Never assume an endpoint, file, database field, service or integration exists.

Inspect the repository first.

Never claim a feature works without verification.

For code changes:

1. inspect
2. modify
3. run regression tests
4. run relevant smoke tests
5. inspect logs
6. verify database state
7. report exact result

Never expose secrets.

Never fabricate:
- customer information
- compliance records
- certificates
- regulatory registrations
- signatory information
- API credentials

## BUSINESS PRIORITY

Revenue
→ Customers
→ Operations
→ Automation
→ Scale
→ Profitability

## CURRENT MVP PRIORITY

1. Complete compliance renewal workflow.
2. Achieve zero regression failures.
3. Verify certificate generation.
4. Verify certificate verification.
5. Verify renewal scanning.
6. Commit verified source changes.
7. Push to GitHub.
8. Only then move to the next capability.
