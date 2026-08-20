from typing import Any
from uvicorn import run
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.background import BackgroundTask
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
import hmac
import hashlib
import os
import smtplib
from email.mime.text import MIMEText
import json
import base64
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
import subprocess

DB_PATH = "smartbiz.sqlite"
lock = threading.Lock()
ADMIN_TOKEN = os.environ.get("SMARTBIZ_ADMIN_TOKEN", "dev")
AGENTMAIL_INBOX_ID = os.environ.get("AGENTMAIL_INBOX_ID", "compliance1660@agentmail.to")
AGENTMAIL_API_KEY = os.environ.get("AGENTMAIL_API_KEY", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")

QUIZ_QUESTIONS = [
  {"id": "q1", "text": "Do you have a current fire risk assessment on file?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q2", "text": "Are your fire extinguishers serviced annually?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q3", "text": "Do you have a clear evacuation plan and signage?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q4", "text": "Has your team done fire warden training this year?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q5", "text": "Are smoke/heat detectors tested quarterly?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q6", "text": "Are emergency exits kept clear and unlocked during business hours?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q7", "text": "Do you keep a log of fire safety checks and incidents?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q8", "text": "Is your fire alarm system tested weekly?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q9", "text": "Do you have appropriate fire insurance coverage?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q10", "text": "Are flammable materials stored safely?", "options": ["Yes", "No", "Not sure"]},
]

class SimpleTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Any, call_next: Any) -> JSONResponse:
        # Allow CORS preflight
        if request.method == "OPTIONS":
            return JSONResponse({}, status_code=204, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, x-smartbiz-token",
                "Access-Control-Max-Age": "86400",
            })
        path = request.url.path
        # Admin-only paths
        if path.startswith(("/jobs", "/api/v1/documents", "/api/v1/status", "/leads", "/api/v1/export")):
            if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
                return JSONResponse({"detail": "missing or invalid admin token"}, status_code=401)
        # Technician-only paths
        if path.startswith(("/technician/complete", "/bookings/")) and request.method in ("POST", "PATCH"):
            tech_token = request.headers.get("x-smartbiz-token") or request.query_params.get("token")
            if tech_token not in [ADMIN_TOKEN, os.environ.get("SMARBIZ_TECHNICIAN_TOKEN", "tech-complete-1234")]:
                return JSONResponse({"detail": "missing or invalid technician token"}, status_code=401)
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Any, call_next: Any) -> JSONResponse:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization, x-smartbiz-token")
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, max_requests: int = 600, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}

    async def dispatch(self, request: Any, call_next: Any) -> JSONResponse:
        ip = request.client.host if request.client else "unknown"
        key = ip + "|" + request.url.path
        now = datetime.now(timezone.utc).timestamp()
        hits = self._hits.get(key, [])
        hits = [t for t in hits if now - t <= self.window_seconds]
        if len(hits) >= self.max_requests:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        hits.append(now)
        self._hits[key] = hits
        return await call_next(request)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Any, call_next: Any) -> JSONResponse:
        start = datetime.now(timezone.utc)
        response = await call_next(request)
        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        try:
            with lock, sqlite3.connect(DB_PATH) as con:
                con.execute(
                    "INSERT INTO request_logs (method, path, status_code, duration_ms, created_at) VALUES (?, ?, ?, ?, ?)",
                    (request.method, request.url.path, response.status_code, duration_ms, _now_iso()),
                )
                con.commit()
        except Exception:
            pass
        return response

def init_db() -> None:
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT,
              company TEXT,
              interest TEXT,
              status TEXT NOT NULL DEFAULT 'new',
              source TEXT DEFAULT 'organic',
              score INTEGER NOT NULL DEFAULT 0,
              industry TEXT NOT NULL DEFAULT 'general',
              location TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        try:
            con.execute("ALTER TABLE leads ADD COLUMN industry TEXT NOT NULL DEFAULT 'general'")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE leads ADD COLUMN location TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              client TEXT NOT NULL,
              site TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'draft',
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id INTEGER NOT NULL,
              decision TEXT NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              decided_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_results (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT NOT NULL DEFAULT '',
              company TEXT NOT NULL DEFAULT '',
              score INTEGER NOT NULL DEFAULT 0,
              answers TEXT NOT NULL DEFAULT '{}',
              submitted_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT NOT NULL DEFAULT '',
              company TEXT NOT NULL DEFAULT '',
              service TEXT NOT NULL DEFAULT 'site-inspection',
              status TEXT NOT NULL DEFAULT 'pending',
              amount_cents INTEGER NOT NULL DEFAULT 0,
              currency TEXT NOT NULL DEFAULT 'ZAR',
              payfast_payment_id TEXT NOT NULL DEFAULT '',
              payfast_pf_payment_id TEXT NOT NULL DEFAULT '',
              payfast_status TEXT NOT NULL DEFAULT 'pending',
              payfast_updated_at TEXT NOT NULL DEFAULT '',
              evidence_notes TEXT NOT NULL DEFAULT '',
              evidence_photo_url TEXT NOT NULL DEFAULT '',
              assigned_technician_id INTEGER NOT NULL DEFAULT 0,
              location TEXT NOT NULL DEFAULT '',
              whatsapp_number TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        try:
            con.execute("ALTER TABLE bookings ADD COLUMN location TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE bookings ADD COLUMN whatsapp_number TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        con.execute("PRAGMA user_version = 4")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS technicians (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT NOT NULL,
              pin TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS request_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              method TEXT NOT NULL,
              path TEXT NOT NULL,
              status_code INTEGER NOT NULL,
              duration_ms INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS job_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              detail TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.commit()
        # migrate bookings columns if missing
        try:
            con.execute("ALTER TABLE bookings ADD COLUMN payfast_status TEXT NOT NULL DEFAULT 'pending'")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE bookings ADD COLUMN payfast_updated_at TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE bookings ADD COLUMN evidence_notes TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE leads ADD COLUMN status TEXT NOT NULL DEFAULT 'new'")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE leads ADD COLUMN source TEXT DEFAULT 'organic'")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE leads ADD COLUMN score INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE leads ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            con.execute("UPDATE leads SET updated_at = created_at WHERE updated_at = ''")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE bookings ADD COLUMN assigned_technician_id INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        con.commit()

init_db()

def homepage(request: Any) -> JSONResponse:
    return JSONResponse({"service": "SmartBiz MVP"})

def health(request: Any) -> JSONResponse:
    return JSONResponse({"status": "ok"})

def _json_error(detail: str, status_code: int = 400):
    return JSONResponse({"detail": detail}, status_code=status_code)

def _payfast_hmac_valid(data: dict, signature: str, key: str) -> bool:
    if not signature or not key:
        return False
    payload = "".join(f"{k}={urllib.parse.quote(str(v), safe='')}&" for k, v in sorted(data.items())).rstrip("&")
    expected = hmac.new(key.encode(), payload.encode(), hashlib.md5).hexdigest()
    return hmac.compare_digest(expected, signature.strip())

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _send_email(subject: str, body: str, to_addr: str | None = None) -> None:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "0") or "0")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = to_addr or os.environ.get("SMARTBIZ_EMAIL_TO") or user
    if all([host, port, user, password, to_addr]):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr
        try:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls()
                s.login(user, password)
                s.send_message(msg)
                return
        except Exception:
            pass
    if AGENTMAIL_API_KEY and AGENTMAIL_INBOX_ID and to_addr:
        try:
            _send_email_via_agentmail(subject, body, to_addr)
        except Exception:
            pass


def _send_email_via_agentmail(subject: str, body: str, to_addr: str) -> None:
    payload = json.dumps({
        "inbox_id": AGENTMAIL_INBOX_ID,
        "to": to_addr,
        "subject": subject,
        "text": body,
    }).encode()
    req = urllib.request.Request(
        "https://api.agentmail.to/v0/inboxes/messages/send",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AGENTMAIL_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()

def _send_whatsapp_confirmation(booking: dict) -> None:
    if not WHATSAPP_NUMBER:
        return
    number = (booking.get("whatsapp_number") or "").strip()
    if not number:
        return
    text = (
        f"Hi {booking.get('first_name', '')}, your SmartBiz fire compliance booking #{booking['id']} is confirmed."
        f"\nService: {booking.get('service', '')}"
        f"\nLocation: {booking.get('location', '') or 'TBD'}"
        "\nWe will send timing and technician details here."
    )
    payload = json.dumps({
        "to": number,
        "text": text,
    }).encode()
    req = urllib.request.Request(
        "https://api.agentmail.to/v0/inboxes/messages/send",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AGENTMAIL_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()


def _booking_email_subject(event: str, booking_id: int) -> str:
    return f"SmartBiz booking #{booking_id}: {event}"

def _booking_confirmed_email(booking_id: int, booking: dict) -> str:
    return f"""Hi {booking.get('first_name', '')},

Your fire compliance booking #{booking_id} is confirmed.
Service: {booking.get('service', '')}
Amount: {booking.get('amount_cents', 0) / 100} {booking.get('currency', 'ZAR')}

Next: complete payment via PayFast.
"""

def _technician_completed_email(booking_id: int, booking: dict) -> str:
    return f"""Hi {booking.get('first_name', '')},

Booking #{booking_id} has been marked complete by our technician.
Service: {booking.get('service', '')}
Status: technician completed

You will receive your compliance documents shortly.
"""

def _refund_confirmed_email(booking_id: int, booking: dict, refund_cents: int) -> str:
    return f"""Hi {booking.get('first_name', '')},

Your refund for booking #{booking_id} has been processed.
Refund amount: {refund_cents / 100} {booking.get('currency', 'ZAR')}
Refund reason: no-show/failed job after 5 days

If you have questions, reply to this email.
"""

def _record_job_event(job_id: int, event_type: str, detail: str = "") -> None:
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, ?, ?, ?)",
            (job_id, event_type, detail, _now_iso()),
        )
        con.commit()

async def list_jobs(request: Any) -> JSONResponse:
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, client, site, status, created_at FROM jobs ORDER BY id DESC").fetchall()
        data = [dict(r) for r in rows]
    return JSONResponse({"jobs": data})

async def get_job(request: Request) -> JSONResponse:
    job_id = int(request.path_params["job_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, client, site, status, created_at FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return _json_error("job not found", 404)
        job = dict(row)
    return JSONResponse(job)

async def create_job(request: Any) -> JSONResponse:
    body = await request.json()
    client = (body.get("client") or "").strip()
    site = (body.get("site") or "").strip()
    if not client or not site:
        return _json_error("client and site are required")
    created_at = _now_iso()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO jobs (client, site, status, created_at) VALUES (?, ?, 'draft', ?)",
            (client, site, created_at),
        )
        job_id = cur.lastrowid
        con.commit()
    _record_job_event(job_id, "created", "Job created by API")
    return JSONResponse({"ok": True, "job_id": job_id})

async def approve_job(request: Request) -> JSONResponse:
    job_id = int(request.path_params["job_id"])
    body = await request.json()
    note = (body.get("note") or "").strip()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
        if cur.fetchone() is None:
            return _json_error("job not found", 404)
        con.execute("UPDATE jobs SET status = 'approved' WHERE id = ?", (job_id,))
        con.execute(
            "INSERT INTO approvals (job_id, decision, note, decided_at) VALUES (?, 'approved', ?, ?)",
            (job_id, note, _now_iso()),
        )
        con.commit()
    _record_job_event(job_id, "approved", note or "Job approved")
    return JSONResponse({"ok": True, "status": "approved"})

async def reject_job(request: Request) -> JSONResponse:
    job_id = int(request.path_params["job_id"])
    body = await request.json()
    note = (body.get("note") or "").strip()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
        if cur.fetchone() is None:
            return _json_error("job not found", 404)
        con.execute("UPDATE jobs SET status = 'rejected' WHERE id = ?", (job_id,))
        con.execute(
            "INSERT INTO approvals (job_id, decision, note, decided_at) VALUES (?, 'rejected', ?, ?)",
            (job_id, note, _now_iso()),
        )
        con.commit()
    _record_job_event(job_id, "rejected", note or "Job rejected")
    return JSONResponse({"ok": True, "status": "rejected"})

async def list_leads(request: Request) -> JSONResponse:
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, first_name, last_name, email, phone, company, interest, status, source, score, industry, location, created_at FROM leads ORDER BY id DESC").fetchall()
        data = [dict(r) for r in rows]
    return JSONResponse({"leads": data})

async def export_leads_google_sheets(request: Request) -> JSONResponse:
    spreadsheet_id = (request.query_params.get("spreadsheet_id") or "").strip()
    worksheet_title = (request.query_params.get("worksheet") or "Leads").strip()
    if not spreadsheet_id:
        return _json_error("spreadsheet_id is required")
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not credentials_path or not os.path.exists(credentials_path):
        return _json_error("GOOGLE_APPLICATION_CREDENTIALS is not configured or file missing", 500)
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        import gspread
    except Exception as e:
        return _json_error("google export dependency missing: " + str(e), 500)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
    authed = AuthorizedSession(credentials)
    client = gspread.Client(auth=credentials, session=authed)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, first_name, last_name, email, phone, company, interest, status, source, score, industry, location, created_at FROM leads ORDER BY id DESC").fetchall()
        data = [dict(r) for r in rows]
    sheet = client.open_by_key(spreadsheet_id)
    try:
        worksheet = sheet.worksheet(worksheet_title)
        worksheet.clear()
    except Exception:
        worksheet = sheet.add_worksheet(title=worksheet_title, rows=max(len(data)+1, 2), cols=13)
    headers = ["id", "first_name", "last_name", "email", "phone", "company", "interest", "status", "source", "score", "industry", "location", "created_at"]
    values = [headers]
    for row in data:
        values.append([row.get(h, "") for h in headers])
    worksheet.update(values)
    return JSONResponse({"ok": True, "spreadsheet_id": spreadsheet_id, "worksheet": worksheet_title, "exported": len(data)})

async def update_lead(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid admin token"}, status_code=401)
    lead_id = int(request.path_params["lead_id"])
    body = await request.json() or {}
    allowed = {"status", "source", "score", "interest", "phone", "company"}
    updates = {k: body[k] for k in body if k in allowed}
    if not updates:
        return _json_error("no valid update fields")
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [_now_iso(), lead_id]
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE leads SET {set_clause}, updated_at=? WHERE id=?", values)
        con.commit()
    return JSONResponse({"ok": True, "updated": list(updates.keys())})


async def lead_outreach(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid admin token"}, status_code=401)
    lead_id = int(request.path_params["lead_id"])
    body = await request.json() or {}
    template = (body.get("template") or "cold_intro").strip()
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, first_name, last_name, email, phone, company, interest, status FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            return _json_error("lead not found", 404)
        lead = dict(row)
    try:
        from smartbiz.leads import outreach_email
        content = outreach_email(lead, template=template)
        _send_email(f"SmartBiz outreach: {template}", content, lead["email"])
        with lock, sqlite3.connect(DB_PATH) as con:
            con.execute("UPDATE leads SET status=?, updated_at=? WHERE id=?", ("contacted", _now_iso(), lead_id))
            con.execute("INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'outreach', ?, ?)", (lead_id, f"template={template}", _now_iso()))
            con.commit()
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)
    return JSONResponse({"ok": True, "template": template, "to": lead["email"]})


async def import_leads_json_endpoint(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid admin token"}, status_code=401)
    body = await request.json() or {}
    raw = body.get("leads") or body.get("content") or ""
    if isinstance(raw, list):
        content = json.dumps(raw)
    else:
        content = str(raw)
    default_source = (body.get("source") or "import").strip()
    try:
        from smartbiz.leads import import_leads_json, save_leads
        leads = import_leads_json(content, default_source=default_source)
        count = save_leads(leads, DB_PATH)
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=400)
    return JSONResponse({"ok": True, "imported": count})

async def lead_to_appointment(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid admin token"}, status_code=401)
    lead_id = int(request.path_params["lead_id"])
    try:
        body = await request.json() or {}
    except Exception:
        body = {}
    location = (body.get("location") or "").strip()
    whatsapp_number = (body.get("whatsapp_number") or "").strip()
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, first_name, last_name, email, phone, company, interest, status FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            return _json_error("lead not found", 404)
        lead = dict(row)
        cur = con.execute(
            "INSERT INTO bookings (first_name, last_name, email, phone, company, service, status, amount_cents, currency, location, whatsapp_number, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)",
            (lead["first_name"], lead["last_name"], lead["email"], lead["phone"], lead["company"], lead["interest"] or "site-inspection", 0, "ZAR", location, whatsapp_number, _now_iso()),
        )
        booking_id = cur.lastrowid
        con.execute("UPDATE leads SET status='appointment', updated_at=? WHERE id=?", (_now_iso(), lead_id))
        con.execute("INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'appointment', ?, ?)", (booking_id, f"lead_id={lead_id}", _now_iso()))
        con.commit()
    try:
        from smartbiz.leads import outreach_email
        content = outreach_email(lead, template="appointment_confirm")
        _send_email("Appointment booked", content, lead["email"])
    except Exception:
        pass
    return JSONResponse({"ok": True, "booking_id": booking_id, "lead_id": lead_id})

async def confirm_booking(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, first_name, last_name, email, phone, company, service, status, location, whatsapp_number FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if not row:
            return _json_error("booking not found", 404)
        booking = dict(row)
        if booking["status"] == "confirmed":
            return JSONResponse({"ok": True, "booking_id": booking_id, "status": "confirmed"})
        if booking["status"] != "pending":
            return _json_error(f"booking cannot be confirmed from status '{booking['status']}'", 400)
        con.execute("UPDATE bookings SET status='confirmed' WHERE id=?", (booking_id,))
        con.execute("INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'confirmed', ?, ?)", (booking_id, "Client confirmed appointment", _now_iso()))
        con.commit()
    try:
        _send_email(
            _booking_email_subject("confirmed", booking_id),
            f"Hi {booking.get('first_name', '')},\n\nYour fire compliance booking #{booking_id} is confirmed.\nService: {booking.get('service', '')}\nLocation: {booking.get('location', '')}\n\nWe'll be in touch with timing and technician details shortly.\n\nBest,\nSmartBiz",
            booking.get("email"),
        )
    except Exception:
        pass
    try:
        _send_whatsapp_confirmation(booking)
    except Exception:
        pass
    return JSONResponse({"ok": True, "booking_id": booking_id, "status": "confirmed"})

async def create_lead(request: Any) -> JSONResponse:
    body = await request.json()
    first = (body.get("first_name") or "").strip()
    last = (body.get("last_name") or "").strip()
    email = (body.get("email") or "").strip()
    phone = (body.get("phone") or "").strip()
    company = (body.get("company") or "").strip()
    interest = (body.get("interest") or "demo").strip()
    source = (body.get("source") or "organic").strip()
    score = int(body.get("score") or 0)
    industry = (body.get("industry") or "general").strip()
    location = (body.get("location") or "").strip()
    if not first or not last or not email:
        return _json_error("first_name, last_name and email are required")
    created_at = _now_iso()
    updated_at = created_at
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO leads (first_name, last_name, email, phone, company, interest, status, source, score, industry, location, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?)",
            (first, last, email, phone, company, interest, source, score, industry, location, created_at, updated_at),
        )
        lead_id = cur.lastrowid
        con.commit()
    try:
        _send_email("New lead: " + first + " " + last, "New lead\nName: " + first + " " + last + "\nEmail: " + email + "\nPhone: " + phone + "\nCompany: " + company + "\nInterest: " + interest + "\nSource: " + source + "\nScore: " + str(score) + "\nIndustry: " + industry + "\nLocation: " + location)
    except Exception:
        pass
    return JSONResponse({"ok": True, "lead_id": lead_id, "status": "new", "source": source, "score": score})

async def generate_document(request: Request) -> JSONResponse:
    job_id = int(request.path_params["job_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, client, site, status, created_at FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return _json_error("job not found", 404)
        job = dict(row)
    doc = {
        "type": "job_summary",
        "job": job,
        "generated_at": _now_iso(),
        "disclaimer": "This is a stub document generated from SmartBiz MVP.",
    }
    return JSONResponse(doc)

async def app_status(request: Request) -> JSONResponse:
    checks = {}
    try:
        with lock, sqlite3.connect(DB_PATH) as con:
            checks["db"] = con.execute("SELECT 1").fetchone()[0] == 1
    except Exception:
        checks["db"] = False
    checks["xero"] = _xero_configured()
    checks["smtp"] = all([os.environ.get("SMTP_HOST"), os.environ.get("SMTP_PORT"), os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS")])
    with lock, sqlite3.connect(DB_PATH) as con:
        jobs = con.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()[0]
        leads = con.execute("SELECT COUNT(*) AS count FROM leads").fetchone()[0]
        approvals = con.execute("SELECT COUNT(*) AS count FROM approvals").fetchone()[0]
        quiz = con.execute("SELECT COUNT(*) AS count FROM quiz_results").fetchone()[0]
        bookings = con.execute("SELECT COUNT(*) AS count FROM bookings").fetchone()[0]
        technicians = con.execute("SELECT COUNT(*) AS count FROM technicians").fetchone()[0]
    return JSONResponse({
        "service": "SmartBiz MVP",
        "status": "ok",
        "checks": checks,
        "counts": {"jobs": jobs, "leads": leads, "approvals": approvals, "quiz_results": quiz, "bookings": bookings, "technicians": technicians},
        "generated_at": _now_iso(),
    })

async def export_leads(request: Request) -> JSONResponse:
    fmt = (request.query_params.get("format") or "json").lower()
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, first_name, last_name, email, phone, company, interest, status, source, score, created_at FROM leads ORDER BY id DESC").fetchall()
        data = [dict(r) for r in rows]
    if fmt == "csv":
        import csv, io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "first_name", "last_name", "email", "phone", "company", "interest", "status", "source", "score", "created_at"])
        writer.writeheader()
        writer.writerows(data)
        return JSONResponse({"csv": buf.getvalue()})
    return JSONResponse({"leads": data})

async def export_quiz(request: Request) -> JSONResponse:
    fmt = (request.query_params.get("format") or "json").lower()
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, first_name, last_name, email, phone, company, score, answers, submitted_at FROM quiz_results ORDER BY id DESC").fetchall()
        data = [dict(r) for r in rows]
    if fmt == "csv":
        import csv, io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "first_name", "last_name", "email", "phone", "company", "score", "answers", "submitted_at"])
        writer.writeheader()
        writer.writerows(data)
        return JSONResponse({"csv": buf.getvalue()})
    return JSONResponse({"quiz_results": data})

async def quiz_questions(request: Request) -> JSONResponse:
    return JSONResponse({"questions": QUIZ_QUESTIONS})

async def quiz_submit(request: Request) -> JSONResponse:
    body = await request.json()
    first = (body.get("first_name") or "").strip()
    last = (body.get("last_name") or "").strip()
    email = (body.get("email") or "").strip()
    phone = (body.get("phone") or "").strip()
    company = (body.get("company") or "").strip()
    answers = body.get("answers") or {}
    score = 0
    for q in QUIZ_QUESTIONS:
        ans = answers.get(q["id"])
        if ans == "Yes":
            score += 1
    if not first or not last or not email:
        return _json_error("first_name, last_name and email are required")
    submitted_at = _now_iso()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO quiz_results (first_name, last_name, email, phone, company, score, answers, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (first, last, email, phone, company, score, str(answers), submitted_at),
        )
        quiz_id = cur.lastrowid
        con.commit()
    label = "Needs review"
    if score >= 8:
        label = "Mostly compliant"
    elif score >= 5:
        label = "Partially compliant"
    try:
        _send_email("New quiz result: " + first + " " + last, "Quiz result\nName: " + first + " " + last + "\nEmail: " + email + "\nScore: " + str(score) + "/" + str(len(QUIZ_QUESTIONS)) + "\nLabel: " + label)
    except Exception:
        pass
    return JSONResponse({"ok": True, "quiz_id": quiz_id, "score": score, "label": label})

def _build_payfast_url(first: str, last: str, email: str, amount_cents: int, item_name: str, booking_id: int) -> str:
    base = "https://sandbox.payfast.co.za/eng/process"
    merchant_id = os.environ.get("PAYFAST_MERCHANT_ID")
    merchant_key = os.environ.get("PAYFAST_MERCHANT_KEY")
    if not merchant_id or not merchant_key:
        raise RuntimeError("PayFast is not configured")
    params = {
        "merchant_id": merchant_id,
        "merchant_key": merchant_key,
        "return_url": "https://smartbiz-safety.pages.dev/booking-success.html",
        "cancel_url": "https://smartbiz-safety.pages.dev/booking-cancel.html",
        "notify_url": os.environ.get("SMARBIZ_API_URL", "http://localhost:8000") + "/payfast/notify",
        "m_payment_id": str(booking_id),
        "amount": f"{amount_cents/100:.2f}",
        "item_name": item_name,
        "email_address": email,
        "name_first": first,
        "name_last": last,
    }
    import urllib.parse
    return base + "?" + "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in params.items())

async def create_booking(request: Request) -> JSONResponse:
    body = await request.json()
    first = (body.get("first_name") or "").strip()
    last = (body.get("last_name") or "").strip()
    email = (body.get("email") or "").strip()
    phone = (body.get("phone") or "").strip()
    company = (body.get("company") or "").strip()
    service = (body.get("service") or "site-inspection").strip()
    amount_cents = int(body.get("amount_cents") or 0)
    currency = (body.get("currency") or "ZAR").strip()
    assigned_technician_id = int(body.get("assigned_technician_id") or 0)
    location = (body.get("location") or "").strip()
    whatsapp_number = (body.get("whatsapp_number") or "").strip()
    if not first or not last or not email:
        return _json_error("first_name, last_name and email are required")
    created_at = _now_iso()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO bookings (first_name, last_name, email, phone, company, service, status, amount_cents, currency, assigned_technician_id, location, whatsapp_number, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)",
            (first, last, email, phone, company, service, amount_cents, currency, assigned_technician_id, location, whatsapp_number, created_at),
        )
        booking_id = cur.lastrowid
        con.commit()
    payfast_url = ""
    try:
        payfast_url = _build_payfast_url(first, last, email, amount_cents, service, booking_id)
    except Exception:
        pass
    try:
        _send_email(
            _booking_email_subject("confirmed", booking_id),
            _booking_confirmed_email(booking_id, {"first_name": first, "service": service, "amount_cents": amount_cents, "currency": currency}),
            email,
        )
    except Exception:
        pass
    return JSONResponse({"ok": True, "booking_id": booking_id, "payfast_url": payfast_url, "assigned_technician_id": assigned_technician_id})

async def payfast_notify(request: Request) -> JSONResponse:
    body = await request.body()
    data = dict(await request.form())
    payment_id = data.get("m_payment_id") or data.get("custom_str1") or ""
    pf_payment_id = data.get("pf_payment_id") or ""
    amount_gross = data.get("amount_gross") or "0"
    signature = data.get("signature") or ""
    key = os.environ.get("PAYFAST_MERCHANT_KEY", "")
    if not _payfast_hmac_valid(data, signature, key):
        return JSONResponse({"detail": "invalid signature"}, status_code=400)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE bookings SET payfast_payment_id=?, payfast_pf_payment_id=? WHERE id=?",
            (str(payment_id), str(pf_payment_id), str(payment_id)),
        )
        con.execute(
            "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'payment_confirmed', ?, ?)",
            (int(payment_id), "PayFast payment confirmed: " + str(amount_gross), _now_iso()),
        )
        con.commit()
    try:
        await _xero_create_invoice_for_booking(int(payment_id))
    except Exception:
        pass
    return JSONResponse({"ok": True})

async def list_bookings(request: Any) -> JSONResponse:
    query = request.query_params.get("q") or ""
    status = (request.query_params.get("status") or "").strip()
    service = (request.query_params.get("service") or "").strip()
    try:
        page = max(1, int(request.query_params.get("page") or "1"))
    except Exception:
        page = 1
    try:
        limit = max(1, min(100, int(request.query_params.get("limit") or "20")))
    except Exception:
        limit = 20
    offset = (page - 1) * limit
    where = ["1=1"]
    params = []
    if status:
        where.append("status = ?")
        params.append(status)
    if service:
        where.append("service = ?")
        params.append(service)
    if query:
        like = f"%{query}%"
        where.append("(first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR service LIKE ?)")
        params.extend([like, like, like, like])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            f"SELECT id, first_name, last_name, email, phone, company, service, status, amount_cents, currency, payfast_status, evidence_notes, evidence_photo_url, created_at FROM bookings WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        total = con.execute(
            f"SELECT COUNT(*) AS count FROM bookings WHERE {' AND '.join(where)}",
            params,
        ).fetchone()[0]
        data = [dict(r) for r in rows]
    return JSONResponse({"bookings": data, "total": total, "page": page, "limit": limit})

async def get_public_booking(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, first_name, last_name, email, phone, company, service, status, amount_cents, currency, payfast_status, evidence_notes, evidence_photo_url, created_at FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            return _json_error("booking not found", 404)
        booking = dict(row)
    return JSONResponse(booking)

async def get_technician_qr(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    complete_token = os.environ.get("SMARBIZ_TECHNICIAN_TOKEN", "tech-complete-1234")
    qr_url = (os.environ.get("SMARBIZ_API_URL", "http://localhost:8000") + f"/technician/complete/{booking_id}?token={complete_token}").replace(" ", "")
    try:
        import qrcode, io, base64
        img = qrcode.make(qr_url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as e:
        return _json_error("qr generation failed: " + str(e), 500)
    return JSONResponse({"booking_id": booking_id, "qr_png_base64": encoded, "complete_url": qr_url})

async def create_technician(request: Request) -> JSONResponse:
    body = await request.json()
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    pin = (body.get("pin") or "").strip()
    if not name or not email or not pin:
        return _json_error("name, email, and pin are required")
    created_at = _now_iso()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO technicians (name, email, pin, active, created_at) VALUES (?, ?, ?, 1, ?)",
            (name, email, pin, created_at),
        )
        technician_id = cur.lastrowid
        con.commit()
    return JSONResponse({"ok": True, "technician_id": technician_id})

async def verify_technician_pin(request: Request) -> JSONResponse:
    body = await request.json()
    pin = (body.get("pin") or "").strip()
    if not pin:
        return _json_error("pin is required", 400)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, name, email, active FROM technicians WHERE pin = ? AND active = 1", (pin,)).fetchone()
        if not row:
            return _json_error("invalid or inactive pin", 403)
        technician = dict(row)
    return JSONResponse({"ok": True, "technician": technician})

async def get_technician_profile(request: Request) -> JSONResponse:
    technician_id = int(request.path_params["technician_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, name, email, active, created_at FROM technicians WHERE id = ?", (technician_id,)).fetchone()
        if not row:
            return _json_error("technician not found", 404)
        technician = dict(row)
    return JSONResponse(technician)

async def list_technicians(request: Request) -> JSONResponse:
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, name, email, active, created_at FROM technicians ORDER BY id DESC").fetchall()
        data = [dict(r) for r in rows]
    return JSONResponse({"technicians": data})

async def assign_technician(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid admin token"}, status_code=401)
    booking_id = int(request.path_params["booking_id"])
    body = await request.json() or {}
    technician_id = int(body.get("technician_id") or 0)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE bookings SET assigned_technician_id=? WHERE id=?", (technician_id, booking_id))
        con.execute(
            "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'assigned', ?, ?)",
            (booking_id, f"assigned_technician_id={technician_id}", _now_iso()),
        )
        con.commit()
    return JSONResponse({"ok": True, "booking_id": booking_id, "assigned_technician_id": technician_id})

async def booking_history(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, status, assigned_technician_id, created_at FROM bookings WHERE id=?", (booking_id,)).fetchone()
        events = con.execute("SELECT event_type, detail, created_at FROM job_events WHERE job_id=? ORDER BY id DESC", (booking_id,)).fetchall()
    if not row:
        return _json_error("booking not found", 404)
    booking = dict(row)
    return JSONResponse({
        "booking_id": booking_id,
        "status": booking["status"],
        "assigned_technician_id": booking["assigned_technician_id"],
        "created_at": booking["created_at"],
        "events": [dict(e) for e in events],
    })

async def technician_complete(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    token = (request.query_params.get("token") or "").strip()
    header_token = (request.headers.get("x-smartbiz-token") or "").strip()
    tech_token = os.environ.get("SMARBIZ_TECHNICIAN_TOKEN", "tech-complete-1234")
    if header_token == ADMIN_TOKEN:
        pass
    elif token == tech_token or header_token == tech_token:
        pass
    else:
        return _json_error("invalid technician token or missing admin token", 401)
    body = await request.json() or {}
    visited = bool(body.get("visited"))
    completed = bool(body.get("completed"))
    evidence_notes = (body.get("evidence_notes") or "").strip()
    evidence_photo_url = (body.get("evidence_photo_url") or "").strip()
    detail = ("visited" if visited else "") + (", completed" if completed else "")
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "UPDATE bookings SET status='technician_completed', evidence_notes=?, evidence_photo_url=? WHERE id=?",
            (evidence_notes, evidence_photo_url, booking_id),
        )
        if cur.rowcount == 0:
            return _json_error("booking not found", 404)
        con.execute(
            "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'technician_complete', ?, ?)",
            (booking_id, detail or "complete", _now_iso()),
        )
        con.commit()
    try:
        row = con.execute("SELECT first_name, email, service, amount_cents, currency FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if row:
            booking = dict(zip(["first_name", "email", "service", "amount_cents", "currency"], row))
            _send_email(
                _booking_email_subject("technician completed", booking_id),
                _technician_completed_email(booking_id, booking),
                booking.get("email"),
            )
    except Exception:
        pass
    return JSONResponse({"ok": True, "status": "technician_completed"})

async def refund_booking(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    body = await request.json() or {}
    reason = (body.get("reason") or "").strip()
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, status, amount_cents, created_at, payfast_status FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            return _json_error("booking not found", 404)
        created_at = datetime.fromisoformat(row["created_at"])
        if datetime.now(timezone.utc) - created_at < timedelta(days=5):
            return _json_error("refund window is 5 days after payment", 403)
        refund_amount = int((row["amount_cents"] * 0.9) // 1)
        con.execute("UPDATE bookings SET status='refunded', payfast_status='refunded' WHERE id=?", (booking_id,))
        con.execute(
            "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'refund', ?, ?)",
            (booking_id, f"90% refund after technician no-show/failed job; refund_amount_cents={refund_amount}", _now_iso()),
        )
        con.commit()
    try:
        row = con.execute("SELECT first_name, email, service, amount_cents, currency FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if row:
            booking = dict(zip(["first_name", "email", "service", "amount_cents", "currency"], row))
            _send_email(
                _booking_email_subject("refund processed", booking_id),
                _refund_confirmed_email(booking_id, booking, refund_amount),
                booking.get("email"),
            )
    except Exception:
        pass
    return JSONResponse({"ok": True, "status": "refunded"})

async def payfast_status_update(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    body = await request.json() or {}
    status = (body.get("status") or "").strip()
    pf_payment_id = (body.get("pf_payment_id") or "").strip()
    payment_id = (body.get("payment_id") or "").strip()
    if not status:
        return _json_error("status is required", 400)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE bookings SET payfast_status=?, payfast_pf_payment_id=?, payfast_payment_id=?, payfast_updated_at=? WHERE id=?",
            (status, pf_payment_id, payment_id, _now_iso(), booking_id),
        )
        con.execute(
            "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'payfast_update', ?, ?)",
            (booking_id, f"payfast_status={status}", _now_iso()),
        )
        con.commit()
    return JSONResponse({"ok": True, "booking_id": booking_id, "status": status})

async def update_booking(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid token"}, status_code=401)
    booking_id = int(request.path_params["booking_id"])
    body = await request.json() or {}
    allowed = ["status", "payfast_status", "evidence_notes", "evidence_photo_url", "payfast_payment_id", "payfast_pf_payment_id"]
    updates = {k: body[k] for k in allowed if k in body}
    if not updates:
        return _json_error("no valid fields to update")
    columns = ", ".join([f"{k}=?" for k in updates])
    values = list(updates.values()) + [_now_iso(), booking_id]
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE bookings SET {columns}, payfast_updated_at=? WHERE id=?", values)
        con.execute(
            "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'admin_update', ?, ?)",
            (booking_id, f"updated fields: {', '.join(updates.keys())}", _now_iso()),
        )
        con.commit()
    return JSONResponse({"ok": True, "updated": list(updates.keys())})

async def export_all(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid token"}, status_code=401)
    fmt = (request.query_params.get("format") or "json").strip().lower()
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        leads = [dict(r) for r in con.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()]
        jobs = [dict(r) for r in con.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()]
        bookings = [dict(r) for r in con.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()]
        technicians = [dict(r) for r in con.execute("SELECT * FROM technicians ORDER BY id DESC").fetchall()]
    if fmt == "csv":
        lines = ["leads: id,first_name,last_name,email,phone,company,interest,created_at"]
        for row in leads:
            lines.append(",".join(str(row.get(k, "")) for k in ["id", "first_name", "last_name", "email", "phone", "company", "interest", "created_at"]))
        lines.append("")
        lines.append("bookings: id,first_name,last_name,email,service,status,amount_cents,currency,payfast_status,created_at")
        for row in bookings:
            lines.append(",".join(str(row.get(k, "")) for k in ["id", "first_name", "last_name", "email", "service", "status", "amount_cents", "currency", "payfast_status", "created_at"]))
        return JSONResponse({"csv": "\n".join(lines)})
    return JSONResponse({"leads": leads, "jobs": jobs, "bookings": bookings, "technicians": technicians})

async def xero_webhook_receiver(request: Request) -> JSONResponse:
    body = await request.json() or {}
    event = (body.get("event_type") or "").strip().lower()
    resource = body.get("resource") or {}
    booking_id_raw = (resource.get("booking_id") or resource.get("reference") or "").strip()
    if not event or not booking_id_raw:
        return _json_error("missing event_type or booking_id/reference", 400)
    try:
        booking_id = int(booking_id_raw)
    except Exception:
        return _json_error("invalid booking_id", 400)
    with lock, sqlite3.connect(DB_PATH) as con:
        if "invoice" in event and "paid" in event:
            con.execute("UPDATE bookings SET status='paid', payfast_status='paid' WHERE id=?", (booking_id,))
            con.execute(
                "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'xero_paid', ?, ?)",
                (booking_id, "Xero invoice paid", _now_iso()),
            )
        elif "creditnote" in event:
            con.execute("UPDATE bookings SET status='refunded', payfast_status='refunded' WHERE id=?", (booking_id,))
            con.execute(
                "INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'xero_refunded', ?, ?)",
                (booking_id, "Xero credit note processed", _now_iso()),
            )
        con.commit()
    return JSONResponse({"ok": True, "event": event, "booking_id": booking_id})

async def analytics_summary(request: Request) -> JSONResponse:
    with lock, sqlite3.connect(DB_PATH) as con:
        leads = con.execute("SELECT COUNT(*) AS count FROM leads").fetchone()[0]
        bookings = con.execute("SELECT COUNT(*) AS count FROM bookings").fetchone()[0]
        payments_confirmed = con.execute("SELECT COUNT(*) AS count FROM bookings WHERE status != 'pending'").fetchone()[0]
        technician_completed = con.execute("SELECT COUNT(*) AS count FROM bookings WHERE status='technician_completed'").fetchone()[0]
        refunds = con.execute("SELECT COUNT(*) AS count FROM bookings WHERE status='refunded'").fetchone()[0]
        request_count = con.execute("SELECT COUNT(*) AS count FROM request_logs").fetchone()[0]
        avg_duration = con.execute("SELECT AVG(duration_ms) FROM request_logs").fetchone()[0]
    return JSONResponse({
        "leads": leads,
        "bookings": bookings,
        "payments_confirmed": payments_confirmed,
        "technician_completed": technician_completed,
        "refunds": refunds,
        "request_count": request_count or 0,
        "avg_duration_ms": int(avg_duration or 0),
        "generated_at": _now_iso(),
    })

def _xero_configured() -> bool:
    return all([
        os.environ.get("XERO_CLIENT_ID"),
        os.environ.get("XERO_CLIENT_SECRET"),
        os.environ.get("XERO_TENANT_ID"),
    ])

def _xero_token() -> str | None:
    if not _xero_configured():
        return None
    token_url = "https://identity.xero.com/connect/token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "accounting.transactions offline_access",
    }).encode()
    req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    basic = base64.b64encode((os.environ["XERO_CLIENT_ID"] + ":" + os.environ["XERO_CLIENT_SECRET"]).encode()).decode()
    req.add_header("Authorization", "Basic " + basic)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            payload = json.loads(r.read().decode())
            return payload.get("access_token")
    except Exception as e:
        raise RuntimeError("xero token failed: " + str(e))

import base64
import urllib.parse

async def xero_sync_contact(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    if not _xero_configured():
        return _json_error("Xero is not configured", 400)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, first_name, last_name, email, phone, company, service, amount_cents, currency, created_at FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            return _json_error("booking not found", 404)
        booking = dict(row)
    token = _xero_token()
    contact = {
        "Name": (booking.get("first_name") or "") + " " + (booking.get("last_name") or ""),
        "EmailAddress": booking.get("email") or "",
        "Phones": [{"PhoneType": "DEFAULT", "PhoneNumber": booking.get("phone") or ""}],
        "ContactStatus": "ACTIVE",
    }
    url = "https://api.xero.com/api.xro/2.0/Contacts"
    payload = json.dumps({"Contacts": [contact]}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "Xero-tenant-id": os.environ["XERO_TENANT_ID"],
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return _json_error("xero contact failed: " + str(e.read().decode()), e.code)
    except Exception as e:
        return _json_error("xero contact failed: " + str(e), 500)
    return JSONResponse({"ok": True, "contact": body.get("Contacts", [None])[0]})

async def xero_create_invoice(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    return await _xero_create_invoice_for_booking(booking_id)

async def smtp_test_endpoint(request: Request) -> JSONResponse:
    if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
        return JSONResponse({"detail": "missing or invalid admin token"}, status_code=401)
    host = os.environ.get("SMTP_HOST")
    port = os.environ.get("SMTP_PORT")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("SMARBIZ_EMAIL_TO") or user
    if not all([host, port, user, password, to_addr]):
        return JSONResponse({"ok": False, "detail": "SMTP is not configured"}, status_code=400)
    try:
        _send_email("SmartBiz SMTP test", "This is a test message from SmartBiz.", to_addr)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)

async def _xero_create_invoice_for_booking(booking_id: int) -> JSONResponse:
    if not _xero_configured():
        return _json_error("Xero is not configured", 400)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, first_name, last_name, email, amount_cents, currency FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            return _json_error("booking not found", 404)
        booking = dict(row)
    token = _xero_token()
    contact_name = (booking.get("first_name") or "") + " " + (booking.get("last_name") or "")
    amount = (booking.get("amount_cents") or 0) / 100.0
    invoice = {
        "Type": "ACCREC",
        "Contact": {"Name": contact_name},
        "LineItems": [
            {
                "Description": "SmartBiz booking/service",
                "Quantity": 1.0,
                "UnitAmount": amount,
                "AccountCode": "200",
            }
        ],
        "Status": "AUTHORISED",
    }
    url = "https://api.xero.com/api.xro/2.0/Invoices"
    payload = json.dumps({"Invoices": [invoice]}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "Xero-tenant-id": os.environ["XERO_TENANT_ID"],
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return _json_error("xero invoice failed: " + str(e.read().decode()), e.code)
    except Exception as e:
        return _json_error("xero invoice failed: " + str(e), 500)
    return JSONResponse({"ok": True, "invoice": body.get("Invoices", [None])[0]})

async def xero_refund_credit_note(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    if not _xero_configured():
        return _json_error("Xero is not configured", 400)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, first_name, last_name, email, amount_cents, currency, created_at FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            return _json_error("booking not found", 404)
        created_at = datetime.fromisoformat(row["created_at"])
        if datetime.now(timezone.utc) - created_at < timedelta(days=5):
            return _json_error("refund window is 5 days after payment", 403)
        booking = dict(row)
    token = _xero_token()
    contact_name = (booking.get("first_name") or "") + " " + (booking.get("last_name") or "")
    amount = (booking.get("amount_cents") or 0) / 100.0
    credit_note = {
        "Type": "CREDITNOTE",
        "Contact": {"Name": contact_name},
        "LineItems": [
            {
                "Description": "Refund after technician no-show/failed job",
                "Quantity": 1.0,
                "UnitAmount": amount,
                "AccountCode": "200",
            }
        ],
    }
    url = "https://api.xero.com/api.xro/2.0/CreditNotes"
    payload = json.dumps({"CreditNotes": [credit_note]}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
        "Xero-tenant-id": os.environ["XERO_TENANT_ID"],
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return _json_error("xero credit note failed: " + str(e.read().decode()), e.code)
    except Exception as e:
        return _json_error("xero credit note failed: " + str(e), 500)
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE bookings SET status='refunded' WHERE id=?", (booking_id,))
        con.execute("INSERT INTO job_events (job_id, event_type, detail, created_at) VALUES (?, 'refund', ?, ?)", (booking_id, "90% refund after technician no-show/failed job", _now_iso()))
        con.commit()
    return JSONResponse({"ok": True, "credit_note": body.get("CreditNotes", [None])[0]})

async def pdf_booking_document(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        booking = con.execute("SELECT id, first_name, last_name, email, phone, company, service, status, amount_cents, currency, created_at FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not booking:
            return _json_error("booking not found", 404)
        booking = dict(booking)
        events = con.execute("SELECT event_type, detail, created_at FROM job_events WHERE job_id = ? ORDER BY id ASC", (booking_id,)).fetchall()
        events = [dict(e) for e in events]
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm
    except Exception as e:
        return _json_error("pdf generation unavailable: " + str(e), 500)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("SmartBiz Fire Safety — Booking Document", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Booking #: {booking['id']}", styles["Normal"]))
    story.append(Paragraph(f"Client: {booking['first_name']} {booking['last_name']}", styles["Normal"]))
    story.append(Paragraph(f"Email: {booking['email']}", styles["Normal"]))
    story.append(Paragraph(f"Phone: {booking['phone']}", styles["Normal"]))
    story.append(Paragraph(f"Company: {booking['company']}", styles["Normal"]))
    story.append(Paragraph(f"Service: {booking['service']}", styles["Normal"]))
    story.append(Paragraph(f"Amount: {booking['currency']} {booking['amount_cents']/100:.2f}", styles["Normal"]))
    story.append(Paragraph(f"Status: {booking['status']}", styles["Normal"]))
    story.append(Paragraph(f"Created: {booking['created_at']}", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Events", styles["Heading2"]))
    data = [["Time", "Event", "Detail"]] + [[e["created_at"], e["event_type"], e["detail"]] for e in events]
    table = Table(data, colWidths=[90*mm, 50*mm, 60*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f97316")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#fff7ed")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,1), (-1,-1), 9),
    ]))
    story.append(table)
    doc.build(story)
    pdf = buf.getvalue()
    return JSONResponse({"booking_id": booking_id, "pdf_base64": base64.b64encode(pdf).decode("ascii"), "filename": f"booking-{booking_id}.pdf"})


def _build_coc_pdf(booking_id: int, booking: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    issue_date = datetime.now(timezone.utc)
    expiry_date = issue_date + timedelta(days=365)

    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        events = con.execute(
            "SELECT event_type, detail, created_at FROM job_events WHERE job_id = ? ORDER BY id ASC",
            (booking_id,),
        ).fetchall()
        events = [dict(e) for e in events]
        quiz_score_row = con.execute(
            "SELECT score FROM quiz_results WHERE email = ? ORDER BY id DESC LIMIT 1",
            (booking.get("email", ""),),
        ).fetchone()
        compliance_score = quiz_score_row["score"] if quiz_score_row else None

    tech_status = booking.get("status", "pending")
    tech_completed = tech_status == "technician_completed"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Certificate of Compliance", styles["Title"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Booking Reference: {booking['id']}", styles["Normal"]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("Client Information", styles["Heading2"]))
    data = [
        ["Name", f"{booking['first_name']} {booking['last_name']}"],
        ["Email", booking["email"]],
        ["Phone", booking["phone"]],
        ["Company", booking["company"]],
        ["Service", booking["service"]],
    ]
    table = Table(data, colWidths=[40*mm, 120*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#f9fafb")),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Compliance Details", styles["Heading2"]))
    data = [
        ["Issue Date", issue_date.strftime("%Y-%m-%d")],
        ["Expiry Date", expiry_date.strftime("%Y-%m-%d")],
        ["Technician Status", "Completed" if tech_completed else tech_status],
    ]
    if compliance_score is not None:
        data.append(["Compliance Score", f"{compliance_score}/10"])
    table = Table(data, colWidths=[50*mm, 110*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#f9fafb")),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Declaration", styles["Heading2"]))
    story.append(Paragraph(
        "This certificate confirms that the fire safety inspection and associated compliance "
        "checks have been recorded for the client and site details listed above. "
        "The technician has marked this booking as completed.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 24))

    story.append(Paragraph("Authorised Signature", styles["Heading2"]))
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 40, styles["Normal"]))
    story.append(Paragraph("SmartBiz Fire Safety — Authorised Signatory", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Date: {issue_date.strftime('%Y-%m-%d')}", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()


async def coc_booking_document(request: Request) -> JSONResponse:
    booking_id = int(request.path_params["booking_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        booking = con.execute("SELECT id, first_name, last_name, email, phone, company, service, status, amount_cents, currency, created_at FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not booking:
            return _json_error("booking not found", 404)
        booking = dict(booking)
    try:
        pdf = _build_coc_pdf(booking_id, booking)
    except Exception as e:
        return _json_error("coc pdf generation failed: " + str(e), 500)
    return JSONResponse({
        "booking_id": booking_id,
        "pdf_base64": base64.b64encode(pdf).decode("ascii"),
        "filename": f"coc-booking-{booking_id}.pdf",
    })


app = Starlette(
    routes=[
        Route("/", homepage),
        Route("/health", health, methods=["GET"]),
        Route("/jobs", list_jobs, methods=["GET"]),
        Route("/jobs", create_job, methods=["POST"]),
        Route("/jobs/{job_id}", get_job, methods=["GET"]),
        Route("/jobs/{job_id}/approve", approve_job, methods=["POST"]),
        Route("/jobs/{job_id}/reject", reject_job, methods=["POST"]),
        Route("/leads", list_leads, methods=["GET"]),
        Route("/api/v1/leads", create_lead, methods=["POST"]),
        Route("/api/v1/documents/{job_id}", generate_document, methods=["GET"]),
        Route("/api/v1/status", app_status, methods=["GET"]),
        Route("/api/v1/quiz/questions", quiz_questions, methods=["GET"]),
        Route("/api/v1/quiz/submit", quiz_submit, methods=["POST"]),
        Route("/leads/export", export_leads, methods=["GET"]),
        Route("/quiz/export", export_quiz, methods=["GET"]),
        Route("/api/v1/bookings", create_booking, methods=["POST"]),
        Route("/api/v1/bookings", list_bookings, methods=["GET"]),
        Route("/api/v1/bookings/{booking_id}/public", get_public_booking, methods=["GET"]),
        Route("/api/v1/bookings/{booking_id}/confirm", confirm_booking, methods=["POST"]),
        Route("/bookings/{booking_id}/qr", get_technician_qr, methods=["GET"]),
        Route("/technician/complete/{booking_id}", technician_complete, methods=["POST"]),
        Route("/api/v1/technicians", create_technician, methods=["POST"]),
        Route("/api/v1/technicians/verify", verify_technician_pin, methods=["POST"]),
        Route("/api/v1/leads", list_leads, methods=["GET"]),
        Route("/api/v1/leads/import", import_leads_json_endpoint, methods=["POST"]),
        Route("/api/v1/leads/{lead_id}", update_lead, methods=["PATCH"]),
        Route("/api/v1/leads/{lead_id}/appointment", lead_to_appointment, methods=["POST"]),
        Route("/api/v1/leads/{lead_id}/outreach", lead_outreach, methods=["POST"]),
        Route("/api/v1/technicians", list_technicians, methods=["GET"]),
        Route("/api/v1/technicians/{technician_id}", get_technician_profile, methods=["GET"]),
        Route("/api/v1/leads/export/google-sheets", export_leads_google_sheets, methods=["GET"]),
        Route("/bookings/{booking_id}/refund", refund_booking, methods=["POST"]),
        Route("/bookings/{booking_id}/payfast-status", payfast_status_update, methods=["POST"]),
        Route("/api/v1/bookings/{booking_id}", update_booking, methods=["PATCH"]),
        Route("/api/v1/bookings/{booking_id}/assign", assign_technician, methods=["POST"]),
        Route("/api/v1/bookings/{booking_id}/history", booking_history, methods=["GET"]),
        Route("/api/v1/export/all", export_all, methods=["GET"]),
        Route("/payfast/notify", payfast_notify, methods=["POST"]),
        Route("/xero/webhook", xero_webhook_receiver, methods=["POST"]),
        Route("/api/v1/analytics/summary", analytics_summary, methods=["GET"]),
        Route("/xero/bookings/{booking_id}/contact", xero_sync_contact, methods=["POST"]),
        Route("/xero/bookings/{booking_id}/invoice", xero_create_invoice, methods=["POST"]),
        Route("/xero/bookings/{booking_id}/creditnote", xero_refund_credit_note, methods=["POST"]),
        Route("/bookings/{booking_id}/pdf", pdf_booking_document, methods=["GET"]),
        Route("/bookings/{booking_id}/coc-pdf", coc_booking_document, methods=["GET"]),
        Route("/xero/health", lambda request: JSONResponse({"ok": _xero_configured()}), methods=["GET"]),
        Route("/api/v1/smtp-test", smtp_test_endpoint, methods=["POST"]),
    ],
    middleware=[
        Middleware(SecurityHeadersMiddleware),
        Middleware(RateLimitMiddleware, max_requests=120, window_seconds=60),
        Middleware(RequestLoggingMiddleware),
        Middleware(SimpleTokenMiddleware),
    ],
)

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
