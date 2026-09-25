"""Automated renewal reminder engine for equipment services and certificates."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from smartbiz.db import get_connection, db_lock

REMINDER_INTERVALS = [90, 60, 30, 14, 7, 0]  # Days before expiry

RENEWAL_STAGES = (
    "EXPIRED",
    "URGENT",
    "RENEWAL_DUE",
    "RENEWAL_WINDOW",
    "UPCOMING",
)


def _renewal_stage(days_until_expiry: int) -> str:
    """Classify certificate renewal urgency."""
    if days_until_expiry <= 0:
        return "EXPIRED"
    if days_until_expiry <= 30:
        return "URGENT"
    if days_until_expiry <= 60:
        return "RENEWAL_DUE"
    if days_until_expiry <= 90:
        return "RENEWAL_WINDOW"
    return "UPCOMING"


def get_certificate_renewal_status(certificate_id: int):
    """Return operational renewal intelligence for one certificate."""

    with db_lock, get_connection() as con:
        row = con.execute(
            """
            SELECT
                cert.id AS certificate_id,
                cert.certificate_number,
                cert.expiry_date,
                cert.issue_date,
                cert.status,
                cert.customer_id,
                cert.site_id,
                c.company_name,
                c.contact_name,
                c.email,
                c.phone,
                s.site_name,
                s.address AS site_address,
                s.city,
                s.province
            FROM certificates cert
            LEFT JOIN customers c
                ON c.id = cert.customer_id
            LEFT JOIN sites s
                ON s.id = cert.site_id
            WHERE cert.id = ?
            """,
            (certificate_id,),
        ).fetchone()

    if not row:
        return None

    data = dict(row)

    expiry_value = data.get("expiry_date")

    try:
        expiry = datetime.strptime(
            expiry_value,
            "%Y-%m-%d"
        ).date()
    except (TypeError, ValueError):
        raise ValueError(
            f"Certificate {certificate_id} has invalid expiry_date"
        )

    today = datetime.now(timezone.utc).date()
    days_until_expiry = (expiry - today).days
    stage = _renewal_stage(days_until_expiry)

    actions = {
        "UPCOMING":
            "Monitor certificate and prepare renewal outreach.",
        "RENEWAL_WINDOW":
            "Contact customer and schedule renewal inspection.",
        "RENEWAL_DUE":
            "Renewal is due; contact customer and schedule inspection.",
        "URGENT":
            "Urgent renewal action required; schedule inspection immediately.",
        "EXPIRED":
            "Certificate has expired; arrange a new compliance inspection.",
    }

    data.update({
        "days_until_expiry": days_until_expiry,
        "renewal_stage": stage,
        "recommended_action": actions[stage],
    })

    return data


def list_due_certificate_renewals():
    """Return issued certificates ordered by renewal urgency."""

    with db_lock, get_connection() as con:
        rows = con.execute(
            """
            SELECT cert.id AS certificate_id
            FROM certificates cert
            WHERE cert.expiry_date != ''
              AND cert.status = 'ISSUED'
            ORDER BY cert.expiry_date ASC, cert.id ASC
            """
        ).fetchall()

    results = []

    for row in rows:
        item = get_certificate_renewal_status(
            int(row["certificate_id"])
        )

        if item:
            results.append(item)

    stage_rank = {
        "EXPIRED": 0,
        "URGENT": 1,
        "RENEWAL_DUE": 2,
        "RENEWAL_WINDOW": 3,
        "UPCOMING": 4,
    }

    results.sort(
        key=lambda item: (
            stage_rank.get(item["renewal_stage"], 99),
            item["days_until_expiry"],
            item["certificate_id"],
        )
    )

    return results


def scan_and_generate_renewal_reminders() -> Dict[str, Any]:
    """Scans all equipment and certificates for upcoming due/expiration dates and queues notifications."""
    now_date = datetime.now(timezone.utc).date()
    now_iso = datetime.now(timezone.utc).isoformat()
    queued_count = 0
    equipment_checked = 0
    certificates_checked = 0

    with db_lock, get_connection() as con:
        # 1. Scan Equipment next_service_date
        eq_rows = con.execute(
            """
            SELECT e.id, e.qr_code, e.equipment_type, e.location_on_site, e.next_service_date,
                   s.site_name, c.company_name, c.email, c.phone, c.whatsapp_number
            FROM equipment e
            JOIN sites s ON e.site_id = s.id
            JOIN customers c ON s.customer_id = c.id
            WHERE e.next_service_date != ''
            """
        ).fetchall()

        for row in eq_rows:
            equipment_checked += 1
            eq = dict(row)
            try:
                due_date = datetime.strptime(eq["next_service_date"], "%Y-%m-%d").date()
                days_until = (due_date - now_date).days

                for interval in REMINDER_INTERVALS:
                    if days_until == interval or (interval == 0 and days_until < 0):
                        template_key = "renewal_reminder_equipment" if days_until >= 0 else "equipment_overdue"
                        recipient = eq.get("email") or eq.get("phone") or "client"

                        # Deduplication check: have we queued a notification for this eq and interval today?
                        existing = con.execute(
                            """
                            SELECT id FROM notifications
                            WHERE recipient = ? AND template_key = ? AND scheduled_for = ?
                            """,
                            (recipient, f"{template_key}_{eq['id']}_{interval}", str(now_date))
                        ).fetchone()

                        if not existing:
                            payload = json.dumps({
                                "equipment_id": eq["id"],
                                "qr_code": eq["qr_code"],
                                "equipment_type": eq["equipment_type"],
                                "days_until_due": days_until,
                                "due_date": eq["next_service_date"],
                                "company_name": eq["company_name"],
                                "site_name": eq["site_name"],
                            })
                            con.execute(
                                """
                                INSERT INTO notifications (
                                  recipient, channel, template_key, payload, status, scheduled_for, created_at
                                ) VALUES (?, 'EMAIL', ?, ?, 'QUEUED', ?, ?)
                                """,
                                (recipient, f"{template_key}_{eq['id']}_{interval}", payload, str(now_date), now_iso)
                            )
                            queued_count += 1
            except Exception:
                continue

        # 2. Scan Certificates expiry_date
        cert_rows = con.execute(
            """
            SELECT cert.id, cert.certificate_number, cert.expiry_date,
                   s.site_name, c.company_name, c.email, c.phone
            FROM certificates cert
            JOIN sites s ON cert.site_id = s.id
            JOIN customers c ON cert.customer_id = c.id
            WHERE cert.expiry_date != '' AND cert.status = 'ISSUED'
            """
        ).fetchall()

        for row in cert_rows:
            certificates_checked += 1
            cert = dict(row)
            try:
                exp_date = datetime.strptime(cert["expiry_date"], "%Y-%m-%d").date()
                days_until = (exp_date - now_date).days

                for interval in REMINDER_INTERVALS:
                    if days_until == interval or (interval == 0 and days_until < 0):
                        template_key = "renewal_reminder_certificate" if days_until >= 0 else "certificate_expired"
                        recipient = cert.get("email") or cert.get("phone") or "client"

                        existing = con.execute(
                            """
                            SELECT id FROM notifications
                            WHERE recipient = ? AND template_key = ? AND scheduled_for = ?
                            """,
                            (recipient, f"{template_key}_{cert['id']}_{interval}", str(now_date))
                        ).fetchone()

                        if not existing:
                            payload = json.dumps({
                                "certificate_id": cert["id"],
                                "certificate_number": cert["certificate_number"],
                                "days_until_expiry": days_until,
                                "expiry_date": cert["expiry_date"],
                                "company_name": cert["company_name"],
                                "site_name": cert["site_name"],
                            })
                            con.execute(
                                """
                                INSERT INTO notifications (
                                  recipient, channel, template_key, payload, status, scheduled_for, created_at
                                ) VALUES (?, 'EMAIL', ?, ?, 'QUEUED', ?, ?)
                                """,
                                (recipient, f"{template_key}_{cert['id']}_{interval}", payload, str(now_date), now_iso)
                            )
                            queued_count += 1
            except Exception:
                continue

        con.commit()

    return {
        "ok": True,
        "scanned_equipment": equipment_checked,
        "scanned_certificates": certificates_checked,
        "new_reminders_queued": queued_count,
        "timestamp": now_iso,
    }
