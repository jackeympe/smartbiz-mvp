from typing import Any
from uvicorn import run
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = "smartbiz.sqlite"
lock = threading.Lock()
ADMIN_TOKEN = "dev"

QUIZ_QUESTIONS = [
  {"id": "q1", "text": "Do you have a current fire risk assessment on file?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q2", "text": "Are your fire extinguishers serviced annually?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q3", "text": "Do you have a clear evacuation plan and signage?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q4", "text": "Has your team done fire warden training this year?", "options": ["Yes", "No", "Not sure"]},
  {"id": "q5", "text": "Are smoke/heat detectors tested quarterly?", "options": ["Yes", "No", "Not sure"]},
]

class SimpleTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Any, call_next: Any) -> JSONResponse:
        if request.url.path.startswith(("/jobs", "/api/v1/documents", "/api/v1/status", "/leads")):
            if request.headers.get("x-smartbiz-token") != ADMIN_TOKEN:
                return JSONResponse({"detail": "missing or invalid token"}, status_code=401)
        return await call_next(request)

def init_db() -> None:
    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT NOT NULL DEFAULT '',
              company TEXT NOT NULL DEFAULT '',
              interest TEXT NOT NULL DEFAULT 'demo',
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
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
        con.commit()

init_db()

def homepage(request: Any) -> JSONResponse:
    return JSONResponse({"service": "SmartBiz MVP"})

def health(request: Any) -> JSONResponse:
    return JSONResponse({"status": "ok"})

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
            return JSONResponse({"detail": "job not found"}, status_code=404)
        job = dict(row)
    return JSONResponse(job)

async def create_job(request: Any) -> JSONResponse:
    body = await request.json()
    client = (body.get("client") or "").strip()
    site = (body.get("site") or "").strip()
    if not client or not site:
        return JSONResponse({"detail": "client and site are required"}, status_code=400)
    created_at = datetime.now(timezone.utc).isoformat()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO jobs (client, site, status, created_at) VALUES (?, ?, 'draft', ?)",
            (client, site, created_at),
        )
        job_id = cur.lastrowid
        con.commit()
    return JSONResponse({"ok": True, "job_id": job_id})

async def approve_job(request: Request) -> JSONResponse:
    job_id = int(request.path_params["job_id"])
    body = await request.json()
    note = (body.get("note") or "").strip()
    decided_at = datetime.now(timezone.utc).isoformat()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
        if cur.fetchone() is None:
            return JSONResponse({"detail": "job not found"}, status_code=404)
        con.execute("UPDATE jobs SET status = 'approved' WHERE id = ?", (job_id,))
        con.execute(
            "INSERT INTO approvals (job_id, decision, note, decided_at) VALUES (?, 'approved', ?, ?)",
            (job_id, note, decided_at),
        )
        con.commit()
    return JSONResponse({"ok": True, "status": "approved"})

async def reject_job(request: Request) -> JSONResponse:
    job_id = int(request.path_params["job_id"])
    body = await request.json()
    note = (body.get("note") or "").strip()
    decided_at = datetime.now(timezone.utc).isoformat()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
        if cur.fetchone() is None:
            return JSONResponse({"detail": "job not found"}, status_code=404)
        con.execute("UPDATE jobs SET status = 'rejected' WHERE id = ?", (job_id,))
        con.execute(
            "INSERT INTO approvals (job_id, decision, note, decided_at) VALUES (?, 'rejected', ?, ?)",
            (job_id, note, decided_at),
        )
        con.commit()
    return JSONResponse({"ok": True, "status": "rejected"})

async def list_leads(request: Any) -> JSONResponse:
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id, first_name, last_name, email, phone, company, interest, created_at FROM leads ORDER BY id DESC").fetchall()
        data = [dict(r) for r in rows]
    return JSONResponse({"leads": data})

async def create_lead(request: Any) -> JSONResponse:
    body = await request.json()
    first = (body.get("first_name") or "").strip()
    last = (body.get("last_name") or "").strip()
    email = (body.get("email") or "").strip()
    phone = (body.get("phone") or "").strip()
    company = (body.get("company") or "").strip()
    interest = (body.get("interest") or "demo").strip()
    if not first or not last or not email:
        return JSONResponse({"detail": "first_name, last_name and email are required"}, status_code=400)
    created_at = datetime.now(timezone.utc).isoformat()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO leads (first_name, last_name, email, phone, company, interest, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (first, last, email, phone, company, interest, created_at),
        )
        lead_id = cur.lastrowid
        con.commit()
    return JSONResponse({"ok": True, "lead_id": lead_id})

async def generate_document(request: Request) -> JSONResponse:
    job_id = int(request.path_params["job_id"])
    with lock, sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT id, client, site, status, created_at FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return JSONResponse({"detail": "job not found"}, status_code=404)
        job = dict(row)
    doc = {
        "type": "job_summary",
        "job": job,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "This is a stub document generated from SmartBiz MVP.",
    }
    return JSONResponse(doc)

async def app_status(request: Request) -> JSONResponse:
    with lock, sqlite3.connect(DB_PATH) as con:
        jobs = con.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()[0]
        leads = con.execute("SELECT COUNT(*) AS count FROM leads").fetchone()[0]
        approvals = con.execute("SELECT COUNT(*) AS count FROM approvals").fetchone()[0]
        quiz = con.execute("SELECT COUNT(*) AS count FROM quiz_results").fetchone()[0]
    return JSONResponse({
        "service": "SmartBiz MVP",
        "status": "ok",
        "counts": {"jobs": jobs, "leads": leads, "approvals": approvals, "quiz_results": quiz},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })

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
        return JSONResponse({"detail": "first_name, last_name and email are required"}, status_code=400)
    submitted_at = datetime.now(timezone.utc).isoformat()
    with lock, sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO quiz_results (first_name, last_name, email, phone, company, score, answers, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (first, last, email, phone, company, score, str(answers), submitted_at),
        )
        quiz_id = cur.lastrowid
        con.commit()
    label = "Needs review"
    if score >= 4:
        label = "Mostly compliant"
    elif score == 3:
        label = "Partially compliant"
    return JSONResponse({"ok": True, "quiz_id": quiz_id, "score": score, "label": label})

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
    ],
    middleware=[Middleware(SimpleTokenMiddleware)],
)

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
