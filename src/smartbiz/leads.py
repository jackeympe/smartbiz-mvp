"""Lead sourcing helpers: import CSV/JSON leads, score rules, and outreach templates."""

import csv
import io
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

LEAD_SOURCES = ["website", "referral", "cold", "walkin", "call", "social", "repeat"]

LEAD_STATUSES = ["new", "contacted", "qualified", "appointment", "closed", "lost"]

INTEREST_KEYWORDS = {
    "site-inspection": ["inspection", "inspect", "site", "compliance"],
    "equipment-supply": ["extinguisher", "hose", "detector", "equipment", "supply"],
    "emergency-support": ["emergency", "urgent", "breakdown"],
    "training": ["training", "warden", "sans", "course"],
}


def score_lead(lead: dict[str, Any]) -> int:
    """Simple rule-based lead score from available fields."""
    score = 0
    interest = (lead.get("interest") or "").lower()
    company = (lead.get("company") or "").lower()
    phone = (lead.get("phone") or "").strip()
    email = (lead.get("email") or "").strip()
    source = (lead.get("source") or "organic").lower()
    if interest and any(k in interest for k in ["inspection", "equipment", "training"]):
        score += 2
    if company:
        score += 1
    if phone and re.fullmatch(r"(\+?\d[\d\s\-().]{7,})", phone):
        score += 1
    if email and "@" in email:
        score += 1
    if source == "referral":
        score += 2
    if source == "call":
        score += 1
    return min(score, 10)


def normalize_interest(text: str) -> str:
    text = (text or "").lower()
    for interest, keywords in INTEREST_KEYWORDS.items():
        if any(k in text for k in keywords):
            return interest
    return "site-inspection"


def outreach_email(lead: dict[str, Any], template: str = "cold_intro") -> str:
    first = (lead.get("first_name") or "").strip() or "there"
    company = (lead.get("company") or "").strip() or "your team"
    interest = (lead.get("interest") or "site-inspection").strip()
    templates = {
        "cold_intro": f"Hi {first},\n\nWe help {company} keep fire compliance up to date with inspections, equipment, and certificates of compliance.\n\nAre you open to a short chat about {interest}?\n\nBest,\nSmartBiz",
        "follow_up_1": f"Hi {first},\n\nQuick follow-up on fire compliance for {company}. We can schedule inspections, issue COCs, and track renewals for you.\n\nWant me to send a booking link?\n\nBest,\nSmartBiz",
        "appointment_confirm": f"Hi {first},\n\nYour compliance check is booked. We’ll confirm the time, technician, and prep steps shortly.\n\nBest,\nSmartBiz",
        "missed_booking": f"Hi {first},\n\nWe missed you for the scheduled compliance activity. Reply to reschedule or call us for next available slots.\n\nBest,\nSmartBiz",
    }
    return templates.get(template, templates["cold_intro"])


def import_leads_csv(content: str, default_source: str = "import") -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content))
    leads: list[dict[str, Any]] = []
    for row in reader:
        interest = normalize_interest(row.get("interest") or row.get("Interest") or "")
        lead = {
            "first_name": (row.get("first_name") or row.get("First name") or "").strip(),
            "last_name": (row.get("last_name") or row.get("Last name") or "").strip(),
            "email": (row.get("email") or row.get("Email") or "").strip(),
            "phone": (row.get("phone") or row.get("Phone") or "").strip(),
            "company": (row.get("company") or row.get("Company") or "").strip(),
            "interest": interest,
            "source": (row.get("source") or row.get("Source") or default_source).strip(),
            "score": score_lead({
                "first_name": (row.get("first_name") or row.get("First name") or ""),
                "last_name": (row.get("last_name") or row.get("Last name") or ""),
                "email": (row.get("email") or row.get("Email") or ""),
                "phone": (row.get("phone") or row.get("Phone") or ""),
                "company": (row.get("company") or row.get("Company") or ""),
                "interest": interest,
                "source": (row.get("source") or row.get("Source") or default_source),
            }),
        }
        if lead["first_name"] and lead["email"]:
            leads.append(lead)
    return leads


def import_leads_json(content: str, default_source: str = "import") -> list[dict[str, Any]]:
    data = json.loads(content)
    items = data if isinstance(data, list) else data.get("leads", [])
    leads: list[dict[str, Any]] = []
    for item in items:
        interest = normalize_interest(item.get("interest") or "")
        lead = {
            "first_name": (item.get("first_name") or "").strip(),
            "last_name": (item.get("last_name") or "").strip(),
            "email": (item.get("email") or "").strip(),
            "phone": (item.get("phone") or "").strip(),
            "company": (item.get("company") or "").strip(),
            "interest": interest,
            "source": (item.get("source") or default_source).strip(),
            "score": score_lead({
                "first_name": item.get("first_name"),
                "last_name": item.get("last_name"),
                "email": item.get("email"),
                "phone": item.get("phone"),
                "company": item.get("company"),
                "interest": interest,
                "source": item.get("source") or default_source,
            }),
        }
        if lead["first_name"] and lead["email"]:
            leads.append(lead)
    return leads


def save_leads(leads: list[dict[str, Any]], db_path: str) -> int:
    """Persist scored leads to SQLite."""
    import sqlite3
    from smartbiz.main import _now_iso, lock
    count = 0
    with lock, sqlite3.connect(db_path) as con:
        for lead in leads:
            try:
                con.execute(
                    "INSERT INTO leads (first_name, last_name, email, phone, company, interest, status, source, score, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?)",
                    (
                        lead["first_name"],
                        lead["last_name"],
                        lead["email"],
                        lead["phone"],
                        lead["company"],
                        lead["interest"],
                        lead["source"],
                        lead["score"],
                        _now_iso(),
                        _now_iso(),
                    ),
                )
                count += 1
            except Exception:
                continue
        con.commit()
    return count
