# AGENT_PERMISSION_MATRIX

**Project:** SmartBiz Fire MVP  
**Date:** 2026-09-20  
**Status:** DESIGN + AUDIT BASELINE; EFFECTIVE PERMISSIONS REQUIRE HOST VERIFICATION

## Authority hierarchy

```text
Human / Director
      ↓
Quin-Suchi
      ↓
Hermes
      ↓
Specialists
      ↓
Verifier
      ↓
Approval
      ↓
Execution
      ↓
Audit
```

## Permission matrix

| Role | Read CRM | Write CRM | Outreach | Pricing | Deploy | Approve | Verify | Secrets |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Director/Human | YES | YES | YES | YES | YES | YES | YES | Controlled |
| Quin-Suchi | YES | Controlled | Controlled | NO direct approval | NO direct deployment | Request/escalate | YES | NO raw secrets |
| Hermes | YES | Controlled | NO direct business outreach | NO | Controlled orchestration only | NO | Route | NO raw secrets |
| Sales | YES scoped | YES scoped | YES approved channels | NO | NO | NO | NO | No |
| Marketing | YES scoped | YES campaign data | YES approved campaigns | NO | NO | NO | NO | No |
| Engineering | YES technical | YES technical | NO | NO | Controlled | NO | Self-test only | Controlled |
| CRM | YES | YES CRM scope | NO unless assigned | NO | NO | NO | NO | No |
| Fire Operations | YES job scope | YES job scope | Controlled | NO | NO | NO | NO | No |
| Compliance | YES compliance scope | YES compliance scope | Controlled | NO | NO | NO | YES compliance | No |
| Quotations | YES opportunity scope | YES quote scope | Controlled | READ approved pricing | NO | NO | NO | No |
| Follow-up | YES assigned leads | YES activity scope | YES approved | NO | NO | NO | NO | No |
| Verifier | READ | NO | NO | READ | NO | NO | YES | NO |

## Critical controls

### Pricing

Specialist agents must not bypass:

```text
PRICING_PENDING_APPROVAL
```

The server must reject quote creation using unapproved pricing.

### Deployment

Engineering may prepare/test deployments, but production deployment must follow the project's approval policy.

### Verification

Verifier must have sufficient read access to independently inspect work but should not have write access to the artifacts it verifies.

### Secrets

Agents must not receive raw secrets unless strictly required by an approved tool boundary.

Secrets must never be placed in Discord messages or ordinary logs.

### Destructive operations

Database deletion, credential rotation, production changes, mass outreach, and other destructive/high-impact operations require explicit approval.

## Current evidence gap

The inventory confirms 16 agents and isolated workspaces/SQLite databases, but it does NOT yet establish the effective permission boundary for every agent.

Therefore:

```text
PERMISSION AUDIT = INCOMPLETE
```

## Required host audit

For every agent, capture:

```text
agent_id
agent_name
workspace
agentDir
Discord bindings
filesystem scope
database scope
available tools
MCP servers
secret references
deployment privileges
external API privileges
```

Do not expose secret values.

## Acceptance criterion

The permission model is operational only after the effective runtime permissions match the intended matrix and unauthorized actions have been tested and rejected.
