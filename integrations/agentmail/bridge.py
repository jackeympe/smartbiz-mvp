#!/usr/bin/env python3

import json
import os
import subprocess
import time
from pathlib import Path

import requests


# ============================================================
# SMARTBIZ FIRE AGENTMAIL -> OPENCLAW -> DISCORD BRIDGE
# ============================================================

BASE_DIR = Path("/home/jacke/.openclaw/workspace/projects/smartbiz-mvp")

# Explicit absolute path. Do NOT rely on systemd/NVM PATH discovery.
OPENCLAW_BIN = "/home/jacke/.nvm/versions/node/v24.21.0/bin/openclaw"

# AgentMail
INBOX = os.environ["AGENTMAIL_INBOX"]
KEY = os.environ["AGENTMAIL_API_KEY"]

# Discord
CHANNEL = os.environ["OPENCLAW_DISCORD_CHANNEL"]

# AgentMail API
API_BASE = "https://api.agentmail.to/v0"

# Persistent bridge state
STATE_FILE = BASE_DIR / "integrations" / "agentmail" / "state.json"

POLL_SECONDS = 30


# ============================================================
# STATE
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return {
            "initialized": False,
            "seen": []
        }

    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "initialized": False,
            "seen": []
        }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = STATE_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    temp_file.replace(STATE_FILE)


# ============================================================
# AGENTMAIL
# ============================================================

def get_messages():
    url = f"{API_BASE}/inboxes/{INBOX}/messages"

    headers = {
        "Authorization": f"Bearer {KEY}",
        "Accept": "application/json",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("messages", [])


# ============================================================
# OPENCLAW / DISCORD
# ============================================================

def send_to_discord(message):

    sender = message.get("from", "Unknown")
    subject = message.get("subject", "(no subject)")
    preview = message.get("preview", "")

    text = (
        "📧 **SMARTBIZ FIRE EMAIL**\n\n"
        f"**From:** {sender}\n"
        f"**Subject:** {subject}\n\n"
        f"{preview}"
    )

    command = [
        OPENCLAW_BIN,
        "message",
        "send",
        "--channel",
        "discord",
        "--target",
        CHANNEL,
        "--message",
        text,
    ]

    print(
        "Sending email notification to Discord...",
        flush=True,
    )

    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout.strip(), flush=True)

    if result.stderr:
        print(result.stderr.strip(), flush=True)


# ============================================================
# STARTUP VALIDATION
# ============================================================

def validate_environment():

    if not os.path.isfile(OPENCLAW_BIN):
        raise RuntimeError(
            f"OpenClaw executable not found: {OPENCLAW_BIN}"
        )

    if not os.access(OPENCLAW_BIN, os.X_OK):
        raise RuntimeError(
            f"OpenClaw executable is not executable: {OPENCLAW_BIN}"
        )

    print(
        f"OpenClaw: {OPENCLAW_BIN}",
        flush=True,
    )

    print(
        f"AgentMail inbox: {INBOX}",
        flush=True,
    )

    print(
        f"Discord channel: {CHANNEL}",
        flush=True,
    )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    validate_environment()

    state = load_state()

    messages = get_messages()

    # First startup:
    # Mark all existing messages as seen so old email
    # does not flood Discord.
    if not state["initialized"]:

        state["seen"] = [
            message.get("message_id")
            for message in messages
            if message.get("message_id")
        ]

        state["initialized"] = True

        save_state(state)

        print(
            f"Bridge initialized. Existing messages marked as seen: "
            f"{len(state['seen'])}",
            flush=True,
        )

    else:

        print(
            f"Bridge resumed. Previously seen messages: "
            f"{len(state['seen'])}",
            flush=True,
        )

    print(
        "Waiting for NEW email...",
        flush=True,
    )

    while True:

        try:

            messages = get_messages()

            seen = set(state.get("seen", []))

            for message in reversed(messages):

                message_id = message.get("message_id")

                if not message_id:
                    continue

                if message_id in seen:
                    continue

                print(
                    f"New email detected: "
                    f"{message.get('subject', '(no subject)')}",
                    flush=True,
                )

                send_to_discord(message)

                seen.add(message_id)

                state["seen"] = list(seen)

                save_state(state)

                print(
                    "Email forwarded successfully.",
                    flush=True,
                )

        except Exception as exc:

            print(
                f"Bridge error: {exc}",
                flush=True,
            )

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()


# ============================================================
# OPENCLAW
# ============================================================

OPENCLAW_BIN = os.getenv("OPENCLAW_BIN", "openclaw")

if not os.path.isfile(OPENCLAW_BIN):
    resolved = shutil.which(OPENCLAW_BIN)
    if resolved:
        OPENCLAW_BIN = resolved
    else:
        raise RuntimeError(f"OpenClaw binary not found: {OPENCLAW_BIN}")


# ============================================================
# AGENTMAIL
# ============================================================

API = "https://api.agentmail.to/v0"

INBOX = os.environ["AGENTMAIL_INBOX"]
KEY = os.environ["AGENTMAIL_API_KEY"]

headers = {
    "Authorization": f"Bearer {KEY}"
}


# ============================================================
# DISCORD ROUTING
# ============================================================

DEFAULT_CHANNEL = os.environ["OPENCLAW_DISCORD_CHANNEL"]

CHANNELS = {
    "control": os.getenv(
        "OPENCLAW_DISCORD_FIRE_CONTROL",
        DEFAULT_CHANNEL,
    ),
    "compliance": os.getenv(
        "OPENCLAW_DISCORD_FIRE_COMPLIANCE",
    ),
    "tenders": os.getenv(
        "OPENCLAW_DISCORD_FIRE_TENDERS",
    ),
    "finance": os.getenv(
        "OPENCLAW_DISCORD_FIRE_FINANCE",
    ),
    "marketing": os.getenv(
        "OPENCLAW_DISCORD_FIRE_MARKETING",
    ),
    "approvals": os.getenv(
        "OPENCLAW_DISCORD_FIRE_APPROVALS",
    ),
    "system": os.getenv(
        "OPENCLAW_DISCORD_FIRE_SYSTEM",
    ),
    "security": os.getenv(
        "OPENCLAW_DISCORD_FIRE_SECURITY",
    ),
}


# ============================================================
# ROUTING PATTERNS
# ============================================================

SECURITY_PATTERNS = [
    "otp",
    "one-time password",
    "one time password",
    "verification code",
    "verify your email",
    "verify your email address",
    "verify email",
    "password reset",
    "reset your password",
    "sign in",
    "signin",
    "login",
    "authentication",
    "security alert",
    "security code",
    "two-factor",
    "two factor",
    "2fa",
]

TENDER_PATTERNS = [
    "tender",
    "rfq",
    "rfi",
    "rfp",
    "request for quotation",
    "request for proposal",
    "quotation request",
    "bid invitation",
    "bid request",
    "procurement",
    "expression of interest",
    "eoi",
]

COMPLIANCE_PATTERNS = [
    "certificate of compliance",
    "compliance",
    "fire inspection",
    "inspection",
    "fire extinguisher",
    "fire extinguishers",
    "hose reel",
    "hose reels",
    "hydrant",
    "hydrants",
    "sprinkler",
    "fire safety",
    "safety inspection",
    "coc",
]

FINANCE_PATTERNS = [
    "invoice",
    "statement",
    "payment",
    "payment received",
    "payment reminder",
    "overdue",
    "receipt",
    "remittance",
    "purchase order",
    "purchase order number",
    "po number",
    "accounts payable",
    "accounts receivable",
]

MARKETING_PATTERNS = [
    "newsletter",
    "unsubscribe",
    "marketing",
    "campaign",
    "promotion",
    "promotional",
    "special offer",
]

APPROVAL_PATTERNS = [
    "approval required",
    "approve",
    "approval",
    "authorization required",
    "authorisation required",
    "authorise",
    "authorize",
    "sign off",
    "sign-off",
]

SYSTEM_PATTERNS = [
    "delivery failure",
    "delivery status notification",
    "undelivered mail",
    "mail delivery subsystem",
    "mailer-daemon",
    "mail delivery failed",
    "returned to sender",
    "bounce",
    "cloudflare",
    "email routing",
]


# ============================================================
# STATE / QUARANTINE
# ============================================================

STATE_FILE = Path("integrations/agentmail/.state.json")
QUARANTINE_FILE = Path(
    "integrations/agentmail/.quarantine.jsonl"
)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            print(
                "WARNING: state file could not be read; "
                "starting with empty state.",
                flush=True,
            )

    return {
        "initialized": False,
        "seen": [],
        "routes": {},
    }


def save_state(state):
    temp_file = STATE_FILE.with_suffix(".tmp")

    temp_file.write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
        )
    )

    temp_file.replace(STATE_FILE)


def quarantine(message, reason):
    QUARANTINE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    record = {
        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        ),
        "reason": reason,
        "message_id": message.get("message_id"),
        "from": message.get("from"),
        "subject": message.get("subject"),
    }

    with QUARANTINE_FILE.open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )


# ============================================================
# AGENTMAIL
# ============================================================

def get_messages():
    response = requests.get(
        f"{API}/inboxes/{INBOX}/messages",
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    return response.json().get(
        "messages",
        [],
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_message(message):
    subject = str(
        message.get("subject", "")
    )

    preview = str(
        message.get("preview", "")
    )

    sender = str(
        message.get("from", "")
    )

    searchable = (
        f"{subject}\n"
        f"{preview}\n"
        f"{sender}"
    ).lower()

    # SECURITY MUST HAVE HIGHEST PRIORITY.
    if any(
        pattern in searchable
        for pattern in SECURITY_PATTERNS
    ):
        return "security"

    if any(
        pattern in searchable
        for pattern in TENDER_PATTERNS
    ):
        return "tenders"

    if any(
        pattern in searchable
        for pattern in COMPLIANCE_PATTERNS
    ):
        return "compliance"

    if any(
        pattern in searchable
        for pattern in FINANCE_PATTERNS
    ):
        return "finance"

    if any(
        pattern in searchable
        for pattern in MARKETING_PATTERNS
    ):
        return "marketing"

    if any(
        pattern in searchable
        for pattern in APPROVAL_PATTERNS
    ):
        return "approvals"

    if any(
        pattern in searchable
        for pattern in SYSTEM_PATTERNS
    ):
        return "system"

    return "control"


# ============================================================
# DISCORD
# ============================================================

def send_to_discord(message, route):
    channel = CHANNELS.get(route)

    sender = message.get(
        "from",
        "Unknown",
    )

    subject = message.get(
        "subject",
        "(no subject)",
    )

    preview = message.get(
        "preview",
        "",
    )

    message_id = message.get(
        "message_id",
        "unknown",
    )

    # --------------------------------------------------------
    # SECURITY ROUTE
    #
    # Never expose security/OTP content in normal operations.
    # If no dedicated security channel exists, quarantine it.
    # --------------------------------------------------------

    if route == "security":
        if not channel:
            quarantine(
                message,
                "security message; "
                "no security Discord channel configured",
            )

            print(
                f"QUARANTINED SECURITY MESSAGE: "
                f"{subject}",
                flush=True,
            )

            return "quarantined"

        text = (
            "🔐 **SMARTBIZ FIRE SECURITY ALERT**\n\n"
            f"**From:** {sender}\n"
            f"**Subject:** {subject}\n"
            f"**Message ID:** {message_id}\n\n"
            "Security-related email detected. "
            "Sensitive message content has been withheld."
        )

    else:
        # If a specialized channel isn't configured yet,
        # temporarily route to fire-control.
        if not channel:
            channel = CHANNELS["control"]
            route_label = (
                f"{route} → control (fallback)"
            )
        else:
            route_label = route

        text = (
            "📧 **SMARTBIZ FIRE EMAIL**\n\n"
            f"**Route:** `{route_label}`\n"
            f"**From:** {sender}\n"
            f"**Subject:** {subject}\n"
            f"**Message ID:** {message_id}\n\n"
            f"{preview}"
        )

    subprocess.run(
        [
            OPENCLAW_BIN,
            "message",
            "send",
            "--channel",
            "discord",
            "--target",
            channel,
            "--message",
            text,
        ],
        check=True,
    )

    return channel


# ============================================================
# STARTUP
# ============================================================

state = load_state()

messages = get_messages()


# First run:
# preserve existing behavior and do not dump historical email.
if not state["initialized"]:

    state["seen"] = [
        m.get("message_id")
        for m in messages
        if m.get("message_id")
    ]

    state["initialized"] = True

    save_state(state)

    print(
        "Bridge initialized. "
        f"Existing messages marked as seen: "
        f"{len(state['seen'])}",
        flush=True,
    )

    print(
        "Waiting for NEW email...",
        flush=True,
    )

else:

    print(
        "AgentMail bridge started.",
        flush=True,
    )

    print(
        f"Inbox: {INBOX}",
        flush=True,
    )

    print(
        f"Default Discord: {DEFAULT_CHANNEL}",
        flush=True,
    )


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:

        messages = get_messages()

        for message in reversed(messages):

            message_id = message.get(
                "message_id"
            )

            if (
                not message_id
                or message_id in state["seen"]
            ):
                continue

            route = classify_message(
                message
            )

            print(
                f"Classified: "
                f"{message.get('subject', '(no subject)')} "
                f"→ {route}",
                flush=True,
            )

            destination = send_to_discord(
                message,
                route,
            )

            state["routes"][message_id] = {
                "route": route,
                "destination": destination,
            }

            state["seen"].append(
                message_id
            )

            # Keep state bounded.
            state["seen"] = state["seen"][-1000:]

            if len(state["routes"]) > 1000:
                state["routes"] = dict(
                    list(
                        state["routes"].items()
                    )[-1000:]
                )

            save_state(state)

            print(
                f"Forwarded: "
                f"{message.get('subject', '(no subject)')} "
                f"→ {route}",
                flush=True,
            )

        time.sleep(30)

    except Exception as e:

        print(
            f"Bridge error: {e}",
            flush=True,
        )

        time.sleep(30)
