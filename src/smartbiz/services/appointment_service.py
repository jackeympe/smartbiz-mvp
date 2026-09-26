"""Public appointment booking orchestration for SmartBiz Fire.

A booking is only CONFIRMED when the calendar reservation exists and the
WhatsApp confirmation is accepted by the configured provider. Otherwise the
calendar reservation is retained as PENDING_CONFIRMATION for operational
follow-up.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from smartbiz.db import db_lock, get_connection
from smartbiz.services.whatsapp_service import send_whatsapp_message

TIMEZONE_SA = "Africa/Johannesburg"


def _parse_local(value: str) -> datetime:
    value = (value or "").strip()
    if not value:
        raise ValueError("start_time is required")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("start_time must be ISO-8601, for example 2026-10-05T09:00:00") from exc
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def _booking_ref(booking_id: int) -> str:
    return f"SB-APT-{booking_id:06d}"


def check_availability(start_time: str, duration_minutes: int = 90) -> Dict[str, Any]:
    start = _parse_local(start_time)
    if duration_minutes < 30 or duration_minutes > 480:
        raise ValueError("duration_minutes must be between 30 and 480")
    end = start + timedelta(minutes=duration_minutes)
    start_iso = start.isoformat(timespec="seconds")
    end_iso = end.isoformat(timespec="seconds")

    with db_lock, get_connection() as con:
        conflict = con.execute(
            """
            SELECT id, title, start_time, end_time
            FROM calendar_events
            WHERE start_time < ? AND end_time > ?
            ORDER BY start_time
            LIMIT 1
            """,
            (end_iso, start_iso),
        ).fetchone()

    return {
        "available": conflict is None,
        "start_time": start_iso,
        "end_time": end_iso,
        "timezone": TIMEZONE_SA,
        "conflict": dict(conflict) if conflict else None,
    }


def create_confirmed_appointment(payload: Dict[str, Any]) -> Dict[str, Any]:
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    phone = (payload.get("phone") or "").strip()
    whatsapp = (payload.get("whatsapp_number") or phone).strip()
    company = (payload.get("company") or "").strip()
    service = (payload.get("service") or "Fire Safety Inspection").strip()
    location = (payload.get("location") or "").strip()
    notes = (payload.get("notes") or "").strip()
    duration = int(payload.get("duration_minutes") or 90)

    if not first_name or not last_name or not email or not whatsapp or not company or not location:
        raise ValueError("first_name, last_name, email, whatsapp_number, company and location are required")

    availability = check_availability(payload.get("start_time") or "", duration)
    if not availability["available"]:
        return {"ok": False, "status": "UNAVAILABLE", **availability}

    start_iso = availability["start_time"]
    end_iso = availability["end_time"]
    now_iso = datetime.now(timezone.utc).isoformat()

    with db_lock, get_connection() as con:
        con.execute("BEGIN IMMEDIATE")

        # Re-check inside the write transaction to prevent double booking.
        conflict = con.execute(
            "SELECT id FROM calendar_events WHERE start_time < ? AND end_time > ? LIMIT 1",
            (end_iso, start_iso),
        ).fetchone()
        if conflict:
            con.rollback()
            return {"ok": False, "status": "UNAVAILABLE", **availability}

        customer = con.execute(
            "SELECT id FROM customers WHERE email = ? OR company_name = ? ORDER BY id LIMIT 1",
            (email, company),
        ).fetchone()
        if customer:
            customer_id = int(customer["id"])
        else:
            last_customer = con.execute("SELECT id FROM customers ORDER BY id DESC LIMIT 1").fetchone()
            next_id = (int(last_customer["id"]) + 1) if last_customer else 1
            account_number = f"SBF-{datetime.now().year}-{next_id:04d}"
            cur = con.execute(
                """
                INSERT INTO customers (
                  company_name, account_number, contact_name, email, phone,
                  whatsapp_number, billing_address, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company, account_number, f"{first_name} {last_name}", email, phone,
                    whatsapp, location, notes, now_iso, now_iso,
                ),
            )
            customer_id = int(cur.lastrowid)

        site = con.execute(
            "SELECT id FROM sites WHERE customer_id = ? AND address = ? ORDER BY id LIMIT 1",
            (customer_id, location),
        ).fetchone()
        if site:
            site_id = int(site["id"])
        else:
            cur = con.execute(
                """
                INSERT INTO sites (
                  customer_id, site_name, address, contact_person, contact_phone, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (customer_id, f"{company} Main Site", location, f"{first_name} {last_name}", phone, now_iso),
            )
            site_id = int(cur.lastrowid)

        cur = con.execute(
            """
            INSERT INTO bookings (
              first_name, last_name, email, phone, company, service, status,
              amount_cents, currency, location, whatsapp_number, created_at,
              scheduled_start, scheduled_end, booking_reference, calendar_event_id,
              whatsapp_status
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending_confirmation', 0, 'ZAR', ?, ?, ?, ?, ?, '', 0, 'PENDING')
            """,
            (
                first_name, last_name, email, phone, company, service,
                location, whatsapp, now_iso, start_iso, end_iso,
            ),
        )
        booking_id = int(cur.lastrowid)
        booking_reference = _booking_ref(booking_id)

        title = f"{service} — {company}"
        description = f"Booking {booking_reference}. Contact: {first_name} {last_name}. WhatsApp: {whatsapp}. {notes}".strip()
        cur = con.execute(
            """
            INSERT INTO calendar_events (
              title, description, start_time, end_time, timezone, provider,
              customer_id, site_id, technician_id, created_at
            ) VALUES (?, ?, ?, ?, ?, 'INTERNAL', ?, ?, 0, ?)
            """,
            (title, description, start_iso, end_iso, TIMEZONE_SA, customer_id, site_id, now_iso),
        )
        calendar_event_id = int(cur.lastrowid)

        con.execute(
            """
            UPDATE bookings
            SET booking_reference = ?, calendar_event_id = ?
            WHERE id = ?
            """,
            (booking_reference, calendar_event_id, booking_id),
        )
        con.execute(
            """
            INSERT INTO job_events (job_id, event_type, detail, created_at)
            VALUES (?, 'calendar_reserved', ?, ?)
            """,
            (booking_id, f"{start_iso} to {end_iso}; event_id={calendar_event_id}", now_iso),
        )

        # Operational reminders are queued now; a dispatcher can deliver them later.
        start_dt = datetime.fromisoformat(start_iso)
        for hours_before, template_key in ((24, "APPOINTMENT_REMINDER_24H"), (2, "APPOINTMENT_REMINDER_2H")):
            scheduled = start_dt - timedelta(hours=hours_before)
            con.execute(
                """
                INSERT INTO notifications (
                  recipient, channel, template_key, payload, status, scheduled_for, created_at
                ) VALUES (?, 'WHATSAPP', ?, ?, 'QUEUED', ?, ?)
                """,
                (
                    whatsapp,
                    template_key,
                    json.dumps({"booking_id": booking_id, "booking_reference": booking_reference}),
                    scheduled.isoformat(timespec="seconds"),
                    now_iso,
                ),
            )
        con.commit()

    message = (
        f"SmartBiz Fire appointment {booking_reference}\n"
        f"Status: Calendar reserved\n"
        f"Service: {service}\n"
        f"Business: {company}\n"
        f"Site: {location}\n"
        f"Date/time: {start_iso.replace('T', ' ')} ({TIMEZONE_SA})\n"
        "Reply CONFIRM to acknowledge, RESCHEDULE to change the appointment, or CANCEL to cancel."
    )
    whatsapp_result = send_whatsapp_message(whatsapp, message)
    live_sent = bool(whatsapp_result.get("ok")) and whatsapp_result.get("mode") == "meta_cloud"

    final_status = "confirmed" if live_sent else "pending_confirmation"
    wa_status = "SENT" if live_sent else ("MOCK" if whatsapp_result.get("mode") == "mock" else "FAILED")
    with db_lock, get_connection() as con:
        con.execute(
            "UPDATE bookings SET status = ?, whatsapp_status = ? WHERE id = ?",
            (final_status, wa_status, booking_id),
        )
        con.execute(
            """
            INSERT INTO job_events (job_id, event_type, detail, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                booking_id,
                "whatsapp_confirmation_sent" if live_sent else "whatsapp_confirmation_pending",
                json.dumps(whatsapp_result, default=str),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        con.commit()

    return {
        "ok": True,
        "booking_id": booking_id,
        "booking_reference": booking_reference,
        "status": final_status.upper(),
        "calendar_reserved": True,
        "calendar_event_id": calendar_event_id,
        "whatsapp_sent": live_sent,
        "whatsapp_status": wa_status,
        "start_time": start_iso,
        "end_time": end_iso,
        "timezone": TIMEZONE_SA,
    }
