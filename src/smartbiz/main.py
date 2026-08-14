from typing import Any
from uvicorn import run
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
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

app = Starlette(routes=[
    Route("/", homepage),
    Route("/health", health, methods=["GET"]),
    Route("/jobs", list_jobs, methods=["GET"]),
    Route("/jobs", create_job, methods=["POST"]),
    Route("/leads", list_leads, methods=["GET"]),
    Route("/api/v1/leads", create_lead, methods=["POST"]),
])

if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
