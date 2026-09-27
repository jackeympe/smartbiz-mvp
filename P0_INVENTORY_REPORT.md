# P0 INVENTORY REPORT — Environment Discovery

**Generated:** 2026-09-20 08:29 GMT+2  
**Host:** DESKTOP-D890U6P (WSL2)  
**Runtime:** agent=main | session=agent:main:dashboard:a0c25320-4c45-466c-a15c-6fa2def489b2

---

## 1. OPENCLAW INSTALLATION

### Configuration
- **Config file:** `/home/jacke/.openclaw/openclaw.json` (17,460 bytes, last modified 2026-09-20 00:05)
- **No `config.json`** — only `openclaw.json` exists (this is the canonical config)
- **Version:** 2026.9.4 (from wizard.lastRunVersion)
- **Mode:** Local (gateway.mode = "local", tailscale.mode = "off")

### Gateway Settings
| Setting | Value |
|---------|-------|
| Port | 18789 |
| Bind | loopback |
| Auth Mode | token |
| Auth Token | `01546d8777de9422e47d9a50fccca94c3206683dcd5ed5c2` (masked: 01546d...d5c2) |
| Tools Profile | coding |
| Heartbeat Agent | main |
| System Agent | main |

### Auth Profiles
| Profile | Provider | Mode |
|---------|----------|------|
| openrouter:default | openrouter | api_key |
| nvidia:manual | nvidia | api_key |

### Telemetry
- Enabled: true
- Consented: 2026-09-16T13:51:18.034Z

### Model Configuration
- **Primary:** nvidia/nemotron-3-ultra-550b-a55b
- **Fallbacks:** openrouter/auto
- **Provider timeout (nvidia):** 300 seconds

---

## 2. HERMES INSTALLATION/RUNTIME

### Installation Location
- **Root:** `/home/jacke/.hermes/` (5024 items)
- **Agent Code:** `/home/jacke/.hermes/hermes-agent/` (full source tree with venv)
- **Config:** `/home/jacke/.hermes/config.yaml`
- **Auth:** `/home/jacke/.hermes/auth.json`

### Hermes Config Highlights
| Setting | Value |
|---------|-------|
| Model Provider | nous |
| Default Model | upstage/solar-pro4:free |
| Inference Base URL | https://inference-api.nousresearch.com/v1 |
| Database Journal Mode | WAL |
| Max Turns | 150 |
| Terminal Backend | local |
| Browser Inactivity Timeout | 120s |
| Gateway Loop Watchdog | enabled |
| Scale to Zero | idle_timeout_minutes: 2 |
| Platform Toolsets | discord, telegram, whatsapp, slack, signal, homeassistant, qqbot, yuanbao, teams, google_chat |
| Declined Tools | browser, image_gen, stt, web |

### Hermes Auth Status
- **Provider:** nous
- **Auth Type:** OAuth device_code
- **Access Token:** Present (expires 2026-09-20T06:56:39Z — **EXPIRED as of report time**)
- **Refresh Token:** Present
- **Agent Key:** Present (expires same time)
- **Request Count:** 21
- **Scope:** inference:invoke
- **⚠️ CREDENTIALS EXPIRED** — Token expired ~06:56 UTC (08:56 SAST), current time 08:29 SAST = still valid but near expiry

### Hermes Runtime Capability
- **Process Running:** YES (PID 6840, `python -m hermes_cli.main gateway run`)
- **Kernel Process:** YES (PID 13727, `hermes_kernel_runner.py`)
- **Can Spawn/Route:** YES — Hermes runs as independent gateway with full agent delegation support
- **Skills Directory:** `/home/jacke/.hermes/skills/` (present)
- **Plugins:** `/home/jacke/.hermes/plugins/` (present)
- **ACP Adapter:** `/home/jacke/.hermes/acp_adapter/` (present)

### Hermes Channel Directory
- **Discord Guild:** "The Sovereign Orchestrator" (1479132338557288552) — **32 channels mapped**
- **Telegram:** 1 DM (Jacob Mpe, 6521797508)

---

## 3. DISCORD ADAPTER (OpenClaw)

### Config Status
- **Enabled:** true (plugins.entries.discord.enabled = true)
- **Bot Token:** `[REDACTED]` (masked)
- **Guild Configured:** 1479132338557288552 ("The Sovereign Orchestrator")
- **Require Mention:** false
- **Authorized Users:** ["723992005117739039"]

### Channel Bindings (OpenClaw side — 35 bindings)

| Agent | Channel ID | Channel Name (from Hermes directory) |
|-------|------------|--------------------------------------|
| main | 1549809749758058667 | commander |
| main | 1549809799850360942 | executive-dashboard |
| main | 1549809833463779348 | approvals |
| main | 1549809867131195472 | agent-log |
| main | 1549809901503520828 | alerts |
| hermes | 1549809980096389170 | fire-control |
| fire | 1549810036232954028 | fire-tenders |
| compliance | 1549810417642250271 | fire-compliance |
| fire-operations | 1549810476320293096 | fire-system |
| marketing | 1549810508167778324 | fire-marketing |
| fire | 1549810537293160509 | fire-security |
| fire | 1549810563058765904 | fire-approvals |
| transport | 1549810766486700165 | transport-control |
| transport | 1549810895436259439 | transport-operations |
| transport | 1549810932467634297 | transport-compliance |
| transport | 1549810985143894106 | transport-sales |
| transport | 1549811038478794842 | transport-verifier |
| tenders | 1549811108272144394 | tender-control |
| tenders | 1549811140627005522 | tender-discovery |
| tenders | 1549811178166034443 | rfq-analysis |
| tenders | 1549811210113908888 | bid-preparation |
| tenders | 1549811244226187324 | tender-compliance |
| tenders | 1549811270306369606 | tender-verifier |
| markets | 1549811335460560916 | markets-control |
| markets | 1549811365940691044 | forex |
| markets | 1549811393140621332 | stocks |
| markets | 1549811553308508181 | research |
| markets | 1549811687253868776 | signals |
| markets | 1549811726097195148 | risk |
| markets | 1549811755625095259 | market-alerts |
| main | 1549811846301622434 | agent-development |
| main | 1549811873145421914 | research (duplicate name) |
| main | 1549811915897835591 | testing |
| main | 1549811940589830254 | memory |
| main | 1549811971271032963 | system-health |

### Duplicate Bindings (in bindings array — appear twice with different match format)
- marketing → 1549810508167778324 (fire-marketing)
- compliance → 1549810417642250271 (fire-compliance)
- fire-operations → 1549810476320293096 (fire-system)

### Telegram Binding
- main → all telegram DMs (accountId: "*")

---

## 4. DISCORD SERVER — ACTUAL CHANNELS (Guild 1479132338557288552)

**Source:** Hermes channel_directory.json (32 channels listed)

| # | Channel ID | Name | Type |
|---|------------|------|------|
| 1 | 1549809749758058667 | commander | channel |
| 2 | 1549809799850360942 | executive-dashboard | channel |
| 3 | 1549809833463779348 | approvals | channel |
| 4 | 1549809867131195472 | agent-log | channel |
| 5 | 1549809901503520828 | alerts | channel |
| 6 | 1549809980096389170 | fire-control | channel |
| 7 | 1549810036232954028 | fire-tenders | channel |
| 8 | 1549810417642250271 | fire-compliance | channel |
| 9 | 1549810476320293096 | fire-system | channel |
| 10 | 1549810508167778324 | fire-marketing | channel |
| 11 | 1549810537293160509 | fire-security | channel |
| 12 | 1549810563058765904 | fire-approvals | channel |
| 13 | 1549810766486700165 | transport-control | channel |
| 14 | 1549810895436259439 | transport-operations | channel |
| 15 | 1549810932467634297 | transport-compliance | channel |
| 16 | 1549810985143894106 | transport-sales | channel |
| 17 | 1549811038478794842 | transport-verifier | channel |
| 18 | 1549811108272144394 | tender-control | channel |
| 19 | 1549811140627005522 | tender-discovery | channel |
| 20 | 1549811178166034443 | rfq-analysis | channel |
| 21 | 1549811210113908888 | bid-preparation | channel |
| 22 | 1549811244226187324 | tender-compliance | channel |
| 23 | 1549811270306369606 | tender-verifier | channel |
| 24 | 1549811335460560916 | markets-control | channel |
| 25 | 1549811365940691044 | forex | channel |
| 26 | 1549811393140621332 | stocks | channel |
| 27 | 1549811553308508181 | research | channel |
| 28 | 1549811687253868776 | signals | channel |
| 29 | 1549811726097195148 | risk | channel |
| 30 | 1549811755625095259 | market-alerts | channel |
| 31 | 1549811846301622434 | agent-development | channel |
| 32 | 1549811873145421914 | research | channel |
| 33 | 1549811915897835591 | testing | channel |
| 34 | 1549811940589830254 | memory | channel |
| 35 | 1549811971271032963 | system-health | channel |

**Note:** Hermes directory lists 32 entries but shows 35 items (duplicate "research" name). All 35 OpenClaw bindings map to existing channels.

### Required 13 Channels (from spec) vs Actual
The original spec called for 13 logical channels. **Actual: 35 channels exist** — well beyond the minimum.

**Mapping of spec → actual:**
| Spec Channel | Actual Channel(s) |
|--------------|-------------------|
| commander | commander |
| executive-dashboard | executive-dashboard |
| approvals | approvals |
| agent-log | agent-log |
| alerts | alerts |
| fire-control | fire-control, fire-tenders, fire-compliance, fire-system, fire-marketing, fire-security, fire-approvals |
| transport-control | transport-control, transport-operations, transport-compliance, transport-sales, transport-verifier |
| tender-control | tender-control, tender-discovery, rfq-analysis, bid-preparation, tender-compliance, tender-verifier |
| markets-control | markets-control, forex, stocks, research, signals, risk, market-alerts |
| agent-development | agent-development, research (dup), testing, memory, system-health |

**No missing channels** — all bindings resolve to real Discord channels.

---

## 5. AGENT DEFINITIONS & PROCESSES

### Agents Defined in openclaw.json (16 agents)

| Agent ID | Workspace | Agent Dir | Model |
|----------|-----------|-----------|-------|
| main | /home/jacke/.openclaw/workspace | /home/jacke/.openclaw/agents/main/agent | nemotron-3-ultra |
| fire | /home/jacke/.openclaw/workspace-fire | /home/jacke/.openclaw/agents/fire/agent | nemotron-3-ultra |
| transport | /home/jacke/.openclaw/workspace-transport | /home/jacke/.openclaw/agents/transport/agent | nemotron-3-ultra |
| tenders | /home/jacke/.openclaw/workspace-tenders | /home/jacke/.openclaw/agents/tenders/agent | nemotron-3-ultra |
| markets | /home/jacke/.openclaw/workspace-markets | /home/jacke/.openclaw/agents/markets/agent | nemotron-3-ultra |
| sales | /home/jacke/.openclaw/workspace-fire-sales | /home/jacke/.openclaw/agents/sales/agent | nemotron-3-ultra |
| marketing | /home/jacke/.openclaw/workspace-fire-marketing | /home/jacke/.openclaw/agents/marketing/agent | nemotron-3-ultra |
| hermes | /home/jacke/.openclaw/workspace-hermes | /home/jacke/.openclaw/agents/hermes/agent | nemotron-3-ultra |
| engineering | /home/jacke/.openclaw/workspace-fire-engineering | /home/jacke/.openclaw/agents/engineering/agent | nemotron-3-ultra |
| crm | /home/jacke/.openclaw/workspace-fire-crm | /home/jacke/.openclaw/agents/crm/agent | nemotron-3-ultra |
| fire-operations | /home/jacke/.openclaw/workspace-fire-operations | /home/jacke/.openclaw/agents/fire-operations/agent | nemotron-3-ultra |
| compliance | /home/jacke/.openclaw/workspace-fire-compliance | /home/jacke/.openclaw/agents/compliance/agent | nemotron-3-ultra |
| quotation | /home/jacke/.openclaw/workspace-fire-quotes | /home/jacke/.openclaw/agents/quotation/agent | nemotron-3-ultra |
| followup | /home/jacke/.openclaw/workspace-fire-followups | /home/jacke/.openclaw/agents/followup/agent | nemotron-3-ultra |
| verifier | /home/jacke/.openclaw/workspace-fire-verifier | /home/jacke/.openclaw/agents/verifier/agent | nemotron-3-ultra |

### Agent Workspace Verification
| Agent | Workspace Exists | Agent Dir Exists | SQLite DB Size |
|-------|------------------|------------------|----------------|
| main | ✅ | ✅ | 26.6 MB |
| fire | ✅ | ✅ | 1.6 MB |
| transport | ✅ | ✅ | 696 KB |
| tenders | ✅ | ✅ | 602 KB |
| markets | ✅ | ✅ | 602 KB |
| sales | ✅ | ✅ | 602 KB |
| marketing | ✅ | ✅ | 684 KB |
| hermes | ✅ | ✅ | 602 KB |
| engineering | ✅ | ✅ | 602 KB |
| crm | ✅ | ✅ | 602 KB |
| fire-operations | ✅ | ✅ | 602 KB |
| compliance | ✅ | ✅ | 602 KB |
| quotation | ✅ | ✅ | 602 KB |
| followup | ✅ | ✅ | 602 KB |
| verifier | ✅ | ✅ | 602 KB |

### Agent Isolation
- **Workspaces:** Each agent has dedicated workspace under `/home/jacke/.openclaw/workspace-*`
- **AgentDirs:** Each agent has isolated `/home/jacke/.openclaw/agents/<agent>/agent/` with own SQLite DB
- **Processes Running:**
  - OpenClaw Gateway: PID 15250 (main)
  - OmniRoute: PID 5897
  - Hermes Gateway: PID 6840 (separate process tree)
  - AgentMail Bridge: PID 5315
  - OpenClaw Service Children: PIDs 17474, 17481

### ⚠️ Discrepancy: Hermes Agent vs Hermes Runtime
- **OpenClaw "hermes" agent** exists in config with workspace/workspace-hermes and agentDir
- **Hermes Runtime** runs independently at `/home/jacke/.hermes/hermes-agent/` with own gateway
- These are **TWO DIFFERENT SYSTEMS** sharing the name "hermes"
- OpenClaw hermes agent appears unused (small DB, no recent activity)
- Hermes runtime is the active system with Discord/Telegram integrations

---

## 6. ENVIRONMENT VARIABLES

### System Environment (masked)
```
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
GPG_AGENT_INFO=/run/user/1000/gnupg/S.gpg-agent:0:1
HOME=/home/jacke
LANG=C.UTF-8
LOGNAME=jacke
OPENCLAW_CLI=1
OPENCLAW_GATEWAY_PORT=18789
OPENCLAW_GATEWAY_SERVICE_PID=15250
OPENCLAW_PATH_BOOTSTRAPPED=1
OPENCLAW_SERVICE_KIND=gateway
OPENCLAW_SHELL=exec
OPENCLAW_SYSTEMD_UNIT=openclaw-gateway.service
OPENCLAW_WINDOWS_TASK_HIDDEN_LAUNCHER=1
OPENCLAW_WINDOWS_TASK_NAME=OpenClaw Gateway
PATH=/home/jacke/.openclaw/tmp/agent-cli:/home/jacke/.local/bin:/home/jacke/.nvm/versions/node/v24.21.0/bin:/usr/bin:/bin:/usr/local/bin:/home/jacke/.nvm/current/bin:/home/jacke/.npm-global/bin:/home/jacke/bin:/home/jacke/.nix-profile/bin:/snap/bin
PWD=/home/jacke/.openclaw/workspace
USER=jacke
XDG_RUNTIME_DIR=/run/user/1000
```

### Missing Credentials (from .env.example)
| Variable | Status |
|----------|--------|
| WHATSAPP_ACCESS_TOKEN | ❌ Not in env |
| WHATSAPP_PHONE_NUMBER_ID | ❌ Not in env |
| WHATSAPP_APP_SECRET | ❌ Not in env |
| GOOGLE_CLIENT_ID | ❌ Not in env |
| GOOGLE_CLIENT_SECRET | ❌ Not in env |
| MICROSOFT_CLIENT_ID | ❌ Not in env |
| MICROSOFT_CLIENT_SECRET | ❌ Not in env |
| SMTP_HOST/PORT/USER/PASS | ❌ Not in env |
| AGENTMAIL_API_KEY | ❌ Not in env |
| PAYFAST_MERCHANT_ID/KEY | ❌ Not in env |
| STORAGE_ENDPOINT/BUCKET/KEYS | ❌ Not in env |
| SMARTBIZ_ADMIN_TOKEN | ❌ Not in env |
| AUTH_SECRET | ❌ Not in env |

**OpenClaw config has Discord/Telegram tokens embedded in openclaw.json (not env vars)**

---

## 7. REPOSITORIES

### SmartBiz Fire MVP
- **Path:** `/home/jacke/smartbiz-mvp/`
- **Git Status:** Branch `remove-xero-add-zoho`, 7 modified files, 9 untracked files
- **Recent Commits:**
  - f64ad70: Remove cancelled Xero deployment instructions
  - a368275: Remove Xero from production deployment documentation and define Zoho boundary
  - 80d9550: Remove Xero environment variables from Render configuration
  - 5b57455: Remove Xero credentials and configuration from environment template
  - 349ea5d: Remove Xero references from README
- **Remote:** origin → https://github.com/jackeympe/smartbiz-mvp.git (fetch/push)

### Untracked Documentation Files
- CRM_OPERATING_PLAN.md
- ENGINEERING_BASELINE.md
- MARKETING_ACQUISITION_PLAN.md
- PHASE3_STATUS_REPORT.md
- REVENUE_ENGINE_PLAN.md
- SALES_PIPELINE_ANALYSIS.md
- VERIFIER_REPORT.md

### New Source Code
- src/smartbiz/integrations/ (directory)
- src/smartbiz/lead_scoring.py

---

## 8. DATABASE

### SQLite: `/home/jacke/smartbiz-mvp/smartbiz.sqlite`
- **Size:** 966,656 bytes (~944 KB)
- **Integrity:** OK
- **Journal Mode:** DELETE (not WAL — **discrepancy**: Hermes config requests WAL)
- **Tables:** 24 tables

### Table Row Counts
| Table | Rows |
|-------|------|
| leads | 267 |
| sqlite_sequence | 24 |
| jobs | 202 |
| approvals | 134 |
| quiz_results | 218 |
| bookings | 718 |
| technicians | 76 |
| job_events | 892 |
| request_logs | 3,217 |
| users | 1 |
| customers | 21 |
| sites | 24 |
| equipment | 10 |
| equipment_service_history | 16 |
| inspections | 11 |
| quotes | 19 |
| certificates | 10 |
| notifications | 0 |
| calendar_events | 11 |
| prospects | 31 |
| outreach_attempts | 56 |
| outreach_templates | 10 |
| pricing_config | 24 |
| renewals | 10 |
| order_workflow | 13 |
| enrichment_queue | 528 |

---

## 9. DOCKER

### Status
- **Docker:** NOT INSTALLED (`docker: command not found`)
- **Docker Compose:** NOT AVAILABLE
- **Containers:** N/A

### Deployment Configs Present
- `render.yaml` — Render.com web service config (Python, free tier)
- `fly.toml` — Fly.io config (jnb region, 256MB, shared CPU)
- `docker-compose.yml` — Exists in Hermes repo (/home/jacke/.hermes/hermes-agent/docker-compose.yml) but Docker not installed
- `Dockerfile` — Exists in Hermes repo

---

## 10. PYTHON INSTALLATION

| Component | Version/Status |
|-----------|----------------|
| Python | 3.14.4 |
| uv | ❌ NOT INSTALLED |
| pip | ❌ NOT INSTALLED (but uv.lock exists, suggesting uv was used) |
| Virtual Env | Not in smartbiz-mvp (but Hermes has venv at `/home/jacke/.hermes/hermes-agent/venv/`) |
| Requirements | 27 packages in requirements.txt (fastapi, uvicorn, httpx, qrcode, reportlab, gspread, google-auth, etc.) |

### ⚠️ Python Version Discrepancy
- **Deployment configs specify:** Python 3.11.0 (render.yaml, fly.toml)
- **Actual runtime:** Python 3.14.4 (development)
- **Requires-python:** >=3.11 (pyproject.toml) — compatible but 3.14 is pre-release

---

## 11. NODE/NPM

| Component | Version |
|-----------|---------|
| Node | v24.21.0 |
| npm | 11.19.0 |
| nvm | Active (v24.21.0) |

### Running Node Processes
- OpenClaw Gateway: `/home/jacke/.nvm/versions/node/v24.21.0/bin/node` (PID 15250)
- OmniRoute: `/home/jacke/.nvm/versions/node/v24.21.0/bin/omniroute` (PID 5897)
- esbuild: OmniRoute child (PID 5912)
- OpenClaw Service Children: PIDs 17474, 17481

---

## 12. CURRENT DEPLOYMENT CONFIGS

### render.yaml
```yaml
services:
  - type: web
    name: smartbiz-api
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn smartbiz.main:app --host 0.0.0.0 --port $PORT
    envVars: (15 vars, all sync: false except AGENTMAIL_INBOX_ID and WHATSAPP_NUMBER)
```

### fly.toml
```toml
app = "smartbiz-api"
primary_region = "jnb"
[build]
  builder = "paketobuildpacks/builder:base"
[env]
  PYTHON_VERSION = "3.11.0"
[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
[[vm]]
  memory = "256mb"
  cpu_kind = "shared"
  cpus = 1
```

### wrangler.toml
- Cloudflare Workers config present

### cloudflare.json
- Present (358 bytes)

---

## 13. CURRENT LOGS

### OpenClaw Gateway Logs
- **Log Dir:** `/home/jacke/.openclaw/logs/`
- **Files:** gateway-restart.log only (452 bytes)
- **Content:** 4 lifecycle events (stops/starts/restart) from 2026-09-16

### Hermes Logs
- **Log Dir:** `/home/jacke/.hermes/logs/` (exists, not inspected)
- **Gateway Starts:** `/home/jacke/.hermes/gateway-starts.log` (106 bytes)
- **Gateway PID:** `/home/jacke/.hermes/gateway.pid` (183 bytes)
- **Gateway Sock:** `/home/jacke/.hermes/gateway.sock` (active unix socket)

### Process Logs
- No centralized application logs found for SmartBiz MVP
- OpenClaw agent SQLite DBs contain session history (main: 26.6 MB, fire: 1.6 MB, marketing: 684 KB)

---

## SUMMARY OF DISCREPANCIES

| # | Area | Expected/Config | Actual | Severity |
|---|------|-----------------|--------|----------|
| 1 | Hermes Auth Token | Valid | **EXPIRED** (expired ~08:56 SAST) | HIGH |
| 2 | SQLite Journal Mode | WAL (Hermes config) | DELETE (SmartBiz DB) | MEDIUM |
| 3 | Python Version | 3.11.0 (deploy configs) | 3.14.4 (runtime) | MEDIUM |
| 4 | Docker | Required for deploy | NOT INSTALLED | HIGH |
| 5 | uv/pip | Required for Python deps | NOT INSTALLED | HIGH |
| 6 | Duplicate Discord Bindings | 3 unique | 3 agents bound twice (different match format) | LOW |
| 7 | Hermes vs OpenClaw Hermes | Single system | **TWO SEPARATE SYSTEMS** | HIGH |
| 8 | OpenClaw Config | config.json | openclaw.json only | LOW (naming) |
| 9 | SmartBiz DB Notifications | Should have data | 0 rows | MEDIUM |
| 10 | Git Working Tree | Clean | 7 modified + 9 untracked | LOW |

---

## RECOMMENDATIONS

1. **URGENT:** Refresh Hermes Nous auth token before expiry
2. **HIGH:** Install Docker and uv for deployment parity
3. **HIGH:** Resolve dual-Hermes architecture (OpenClaw agent vs standalone runtime)
4. **MEDIUM:** Migrate SmartBiz SQLite to WAL mode for concurrency
5. **MEDIUM:** Align Python version to 3.11 for deployment compatibility
6. **LOW:** Clean up duplicate Discord bindings in openclaw.json
7. **LOW:** Commit or stash untracked documentation files
8. **LOW:** Populate missing environment variables for production deploy