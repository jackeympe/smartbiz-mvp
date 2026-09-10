"""Fire Equipment Register & QR code management for SmartBiz Fire."""
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from smartbiz.db import get_connection, db_lock

EQUIPMENT_TYPES = [
    "DCP_EXTINGUISHER",
    "CO2_EXTINGUISHER",
    "WATER_EXTINGUISHER",
    "FOAM_EXTINGUISHER",
    "WET_CHEMICAL",
    "HOSE_REEL",
    "HYDRANT",
    "FIRE_BLANKET",
    "FIRE_SIGN",
    "FIRE_ALARM",
    "SPRINKLER",
    "OTHER",
]

EQUIPMENT_STATUSES = ["COMPLIANT", "DUE", "OVERDUE", "FAILED", "MISSING", "REMOVED", "REPLACED"]

def generate_qr_code_id() -> str:
    """Generates the next sequential QR identifier like SB-FE-000185."""
    with db_lock, get_connection() as con:
        row = con.execute("SELECT id FROM equipment ORDER BY id DESC LIMIT 1").fetchone()
        next_id = (row[0] + 1) if row else 1
        return f"SB-FE-{next_id:06d}"

def create_equipment(
    site_id: int,
    equipment_type: str,
    location_on_site: str,
    capacity: str = "4.5kg",
    serial_number: str = "",
    manufacturer: str = "SafePro",
    model_year: str = "2025",
    install_date: Optional[str] = None,
    last_service_date: Optional[str] = None,
    status: str = "COMPLIANT",
    notes: str = "",
    qr_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Registers a new equipment item with QR identifier."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    last_srv = last_service_date or now.strftime("%Y-%m-%d")
    next_srv = (now + timedelta(days=365)).strftime("%Y-%m-%d")
    inst_date = install_date or now.strftime("%Y-%m-%d")
    code = qr_code or generate_qr_code_id()

    with db_lock, get_connection() as con:
        cur = con.execute(
            """
            INSERT INTO equipment (
              qr_code, site_id, serial_number, equipment_type, location_on_site,
              capacity, manufacturer, model_year, install_date, last_service_date,
              next_service_date, status, technician_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code, site_id, serial_number, equipment_type, location_on_site,
                capacity, manufacturer, model_year, inst_date, last_srv,
                next_srv, status, notes, now_iso
            )
        )
        eq_id = cur.lastrowid
        con.commit()

        # Log initial service history
        con.execute(
            """
            INSERT INTO equipment_service_history (
              equipment_id, technician_id, service_date, service_type,
              findings, action_taken, parts_replaced, next_due_date, created_at
            ) VALUES (?, 0, ?, 'Commissioning / Initial Inspection', 'Passed inspection', 'Certified compliant', 'None', ?, ?)
            """,
            (eq_id, last_srv, next_srv, now_iso)
        )
        con.commit()

    return get_equipment_by_id(eq_id)

def get_equipment_by_id(eq_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves equipment by primary key."""
    with db_lock, get_connection() as con:
        row = con.execute(
            """
            SELECT e.*, s.site_name, s.address, s.customer_id, c.company_name as customer_name
            FROM equipment e
            LEFT JOIN sites s ON e.site_id = s.id
            LEFT JOIN customers c ON s.customer_id = c.id
            WHERE e.id = ?
            """,
            (eq_id,)
        ).fetchone()
        return dict(row) if row else None

def get_equipment_by_qr(qr_code: str) -> Optional[Dict[str, Any]]:
    """Retrieves public verification data for QR code scan without exposing sensitive customer info."""
    with db_lock, get_connection() as con:
        row = con.execute(
            """
            SELECT e.id, e.qr_code, e.equipment_type, e.capacity, e.location_on_site,
                   e.manufacturer, e.model_year, e.last_service_date, e.next_service_date,
                   e.status, s.site_name, s.city, s.province
            FROM equipment e
            LEFT JOIN sites s ON e.site_id = s.id
            WHERE e.qr_code = ?
            """,
            (qr_code,)
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        # Check if overdue
        if data.get("next_service_date"):
            try:
                due_date = datetime.strptime(data["next_service_date"], "%Y-%m-%d").date()
                if due_date < datetime.now(timezone.utc).date() and data["status"] == "COMPLIANT":
                    data["status"] = "OVERDUE"
            except Exception:
                pass
        return data

def list_equipment_for_site(site_id: int) -> List[Dict[str, Any]]:
    """Lists all equipment for a given site."""
    with db_lock, get_connection() as con:
        rows = con.execute(
            "SELECT * FROM equipment WHERE site_id = ? ORDER BY id ASC",
            (site_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def record_equipment_service(
    equipment_id: int,
    technician_id: int,
    service_type: str,
    findings: str,
    action_taken: str,
    status: str = "COMPLIANT",
    parts_replaced: str = "",
) -> Dict[str, Any]:
    """Records a service or inspection action on an equipment item."""
    now = datetime.now(timezone.utc)
    srv_date = now.strftime("%Y-%m-%d")
    next_due = (now + timedelta(days=365)).strftime("%Y-%m-%d")
    now_iso = now.isoformat()

    with db_lock, get_connection() as con:
        con.execute(
            """
            UPDATE equipment
            SET last_service_date = ?, next_service_date = ?, status = ?, technician_notes = ?
            WHERE id = ?
            """,
            (srv_date, next_due, status, f"{findings} - {action_taken}", equipment_id)
        )
        con.execute(
            """
            INSERT INTO equipment_service_history (
              equipment_id, technician_id, service_date, service_type,
              findings, action_taken, parts_replaced, next_due_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (equipment_id, technician_id, srv_date, service_type, findings, action_taken, parts_replaced, next_due, now_iso)
        )
        con.commit()

    return get_equipment_by_id(equipment_id)
