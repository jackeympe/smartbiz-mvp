# DUAL_HERMES_COMPARISON

**Project:** SmartBiz Fire MVP  
**Date:** 2026-09-20  
**Status:** INVESTIGATION REQUIRED — DO NOT RETIRE EITHER RUNTIME

## Purpose

Determine the ownership and responsibilities of the two Hermes implementations currently reported in the SmartBiz Fire environment:

1. OpenClaw's `hermes` agent.
2. Standalone Hermes runtime at `~/.hermes/hermes-agent/`.

## Verified inventory baseline

| Item | Finding | Status |
|---|---|---|
| OpenClaw | v2026.9.4, local mode, port 18789, token auth | VERIFIED |
| Standalone Hermes | Running, PID 6840, standalone venv | VERIFIED |
| Hermes Nous authentication | Token reported expired | BLOCKED |
| Discord | Enabled; 35 bindings resolve to real channels | VERIFIED |
| Agents | 16 agents defined; isolated workspaces/agentDirs and SQLite DBs | VERIFIED |
| SmartBiz DB | 944 KB, 24 tables, integrity OK, DELETE journal mode | VERIFIED |
| Docker | Not installed | VERIFIED |
| uv/pip | Not installed | VERIFIED |
| Python | 3.14.4 | VERIFIED |
| Deployment configs | Render/Fly/Cloudflare configs target Python 3.11 | VERIFIED |

## Comparison matrix

| Dimension | OpenClaw `hermes` agent | Standalone Hermes | Evidence required |
|---|---|---|---|
| Process/PID | Not yet established | PID 6840 reported | `ps`, service status |
| Version | Not yet established | Not yet independently captured | runtime version |
| Config | Not yet inspected | `~/.hermes/hermes-agent/` exists | config inspection |
| Workspace | Existing OpenClaw agent workspace | Standalone Hermes workspace | filesystem/process inspection |
| Discord access | Must be tested | Must be tested | live E2E test |
| Agent registry | 16-agent OpenClaw environment | Not established | runtime inspection |
| Tool/MCP access | Not established | Not established | permission/tool inspection |
| Authentication | OpenClaw token auth reported | Nous token reported expired | live auth test |
| Delegation | Not proven | Not proven | E2E trace |
| Logging | Not established | Not established | log inspection |
| Startup mechanism | Not established | Not established | systemd/process inspection |
| Ownership of orchestration | UNRESOLVED | UNRESOLVED | architecture decision |

## Required investigation

Run on the SmartBiz host:

```bash
ps aux | grep -Ei '[h]ermes|[o]penclaw'
ss -ltnp | grep 18789 || true
systemctl --user list-units --type=service --no-pager | grep -Ei 'hermes|openclaw' || true
```

Then inspect the effective configuration for each runtime without exposing secrets.

## Architectural rule

There must be exactly one orchestration authority.

Target control plane:

```text
Human
  ↓
Quin-Suchi
  ↓
Hermes
  ↓
Specialist agents
  ↓
Verifier
  ↓
Hermes
  ↓
Quin-Suchi
```

The second Hermes implementation must be classified as:

- subordinate,
- compatibility layer,
- unused,
- or safely retired.

Do not delete or disable it until dependency analysis proves that it is safe.

## Acceptance criterion

This document is not complete until both runtimes have been compared from actual host evidence and one orchestration owner has been selected.
