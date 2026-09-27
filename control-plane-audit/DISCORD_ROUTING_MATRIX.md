# DISCORD_ROUTING_MATRIX

**Project:** SmartBiz Fire MVP  
**Date:** 2026-09-20  
**Status:** CHANNEL CONFIGURATION VERIFIED; END-TO-END ROUTING NOT YET PROVEN

## Verified baseline

- Discord integration is enabled.
- 35 channels are mapped.
- All 35 bindings reportedly resolve to real Discord channels.
- The existence of valid bindings is NOT proof that runtime delegation works.

## Routing architecture

```text
Discord
  ↓
Quin-Suchi
  ↓
Hermes
  ↓
Specialist
  ↓
Verifier
  ↓
Hermes
  ↓
Quin-Suchi
  ↓
Discord
```

## Routing matrix

| Logical role | Discord channel | Channel ID | Binding | Agent | Permission | Runtime proof |
|---|---|---|---|---|---|---|
| Fire Control | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Quin-Suchi | Command/observe | NOT PROVEN |
| Orchestration | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Hermes | Delegate/route | NOT PROVEN |
| Sales | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Sales | CRM/sales scope | NOT PROVEN |
| Marketing | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Marketing | Campaign/content scope | NOT PROVEN |
| Engineering | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Engineering | Code/test scope | NOT PROVEN |
| CRM | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | CRM | CRM scope | NOT PROVEN |
| Fire Operations | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Fire Operations | Operations scope | NOT PROVEN |
| Compliance | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Compliance | Compliance scope | NOT PROVEN |
| Quotations | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Quotes | Quote scope + pricing gate | NOT PROVEN |
| Follow-up | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Follow-up | Outreach scope | NOT PROVEN |
| Verifier | INVENTORY REQUIRED | INVENTORY REQUIRED | Existing | Verifier | Read-only verification | NOT PROVEN |

## Important constraint

Do NOT create additional Discord channels simply to satisfy the architecture.

The current environment already contains 35 bindings. First inventory and map all 35.

## Required host evidence

Produce the complete 35-channel mapping from the actual OpenClaw configuration/runtime:

```text
channel name
channel ID
binding
agent
workspace
permissions
last observed activity
```

Secrets and bot tokens must never appear in the matrix.

## E2E acceptance test

A route is PASS only when a real message completes:

```text
Discord
→ Quin-Suchi
→ Hermes
→ specialist
→ Verifier
→ Hermes
→ Quin-Suchi
→ Discord
```

with the same `trace_id` preserved throughout.
