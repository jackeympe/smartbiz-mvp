from typing import Any
from uvicorn import run
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = "smartbiz.sqlite"
lock = threading.Lock()

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

app = Starlette(routes=[
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
])

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
