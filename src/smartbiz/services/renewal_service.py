"""Automated renewal reminder engine for equipment services and certificates."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from smartbiz.db import get_connection, db_lock

REMINDER_INTERVALS = [90, 60, 30, 14, 7, 0]  # Days before expiry

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
