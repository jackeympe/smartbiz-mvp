"""Inspection checklist engine, scoring, and comprehensive report PDF generator for SmartBiz Fire."""
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from smartbiz.db import get_connection, db_lock

DEFAULT_INSPECTION_CHECKLIST = [
    {"id": "chk_ext_access", "item": "Fire extinguishers unobstructed and clearly mounted with signage", "category": "Extinguishers", "status": "PASS", "severity": "HIGH"},
    {"id": "chk_ext_pressure", "item": "Pressure gauges in green operating zone & tamper seals intact", "category": "Extinguishers", "status": "PASS", "severity": "HIGH"},
    {"id": "chk_ext_date", "item": "Service tags up to date with valid annual inspection stamp", "category": "Extinguishers", "status": "PASS", "severity": "MEDIUM"},
    {"id": "chk_hose_reel", "item": "Hose reels accessible, nozzle undamaged, pressure tested", "category": "Hose Reels", "status": "PASS", "severity": "HIGH"},
    {"id": "chk_hydrant", "item": "Fire hydrants clear of debris and booster connections operable", "category": "Hydrants", "status": "PASS", "severity": "CRITICAL"},
    {"id": "chk_alarm_panel", "item": "Fire alarm control panel showing normal (no faults or troubles)", "category": "Alarms", "status": "PASS", "severity": "CRITICAL"},
    {"id": "chk_emergency_exits", "item": "Emergency exit doors unlocked, unobstructed, illuminated", "category": "Egress", "status": "PASS", "severity": "CRITICAL"},
    {"id": "chk_signage", "item": "Photoluminescent statutory fire and escape route signage in place", "category": "Signage", "status": "PASS", "severity": "MEDIUM"},
    {"id": "chk_flammable_storage", "item": "Flammable liquids and combustible items stored in rated areas", "category": "Storage", "status": "PASS", "severity": "HIGH"},
    {"id": "chk_evac_plan", "item": "Evacuation floor plans displayed and emergency contact numbers listed", "category": "Management", "status": "PASS", "severity": "MEDIUM"},
]

def create_inspection(
    site_id: int,
    technician_id: int = 0,
    scheduled_date: Optional[str] = None,
    checklist_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Schedules a new on-site inspection."""
    now = datetime.now(timezone.utc)
    sched = scheduled_date or now.strftime("%Y-%m-%d")
    items = checklist_data or DEFAULT_INSPECTION_CHECKLIST

    with db_lock, get_connection() as con:
        cur = con.execute(
            """
            INSERT INTO inspections (
              site_id, technician_id, scheduled_date, status, checklist_data, created_at
            ) VALUES (?, ?, ?, 'SCHEDULED', ?, ?)
            """,
            (site_id, technician_id, sched, json.dumps(items), now.isoformat())
        )
        insp_id = cur.lastrowid
        con.commit()

    return get_inspection(insp_id)

def get_inspection(inspection_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves inspection record."""
    with db_lock, get_connection() as con:
        row = con.execute(
            """
            SELECT i.*, s.site_name, s.address as site_address, s.city, s.province,
                   c.id as customer_id, c.company_name, c.contact_name, c.email, c.phone,
                   t.name as technician_name
            FROM inspections i
            LEFT JOIN sites s ON i.site_id = s.id
            LEFT JOIN customers c ON s.customer_id = c.id
            LEFT JOIN technicians t ON i.technician_id = t.id
            WHERE i.id = ?
            """,
            (inspection_id,)
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["checklist_data"] = json.loads(data["checklist_data"]) if data.get("checklist_data") else []
        return data

def complete_inspection(
    inspection_id: int,
    checklist_results: List[Dict[str, Any]],
    findings_summary: str = "All equipment inspected and operational.",
    recommendations: str = "Maintain quarterly visual checks.",
    signature_url: str = "",
) -> Dict[str, Any]:
    """Records the completed checklist and computes compliance score."""
    total_items = len(checklist_results)
    passed_items = sum(1 for item in checklist_results if item.get("status", "").upper() == "PASS")
    score = int(round((passed_items / total_items) * 100)) if total_items > 0 else 100
    now_iso = datetime.now(timezone.utc).isoformat()

    with db_lock, get_connection() as con:
        con.execute(
            """
            UPDATE inspections
            SET status = 'COMPLETED', overall_score = ?, checklist_data = ?,
                findings_summary = ?, recommendations = ?, signature_url = ?, completed_at = ?
            WHERE id = ?
            """,
            (
                score, json.dumps(checklist_results), findings_summary,
                recommendations, signature_url, now_iso, inspection_id
            )
        )
        con.commit()

    return get_inspection(inspection_id)

def generate_inspection_report_pdf(inspection_id: int) -> bytes:
    """Generates comprehensive inspection report PDF."""
    insp = get_inspection(inspection_id)
    if not insp:
        raise ValueError(f"Inspection {inspection_id} not found")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>SMARTBIZ FIRE SAFETY</b>", styles["Heading1"]))
    story.append(Paragraph("<b>COMPREHENSIVE ON-SITE FIRE INSPECTION REPORT</b>", styles["Heading2"]))
    story.append(Paragraph(f"Inspection #{insp['id']} · Date: {insp['scheduled_date']} · Status: {insp['status']}", styles["Normal"]))
    story.append(Spacer(1, 14))

    meta = [
        ["Customer:", insp.get("company_name", "N/A"), "Site:", insp.get("site_name", "N/A")],
        ["Address:", f"{insp.get('site_address', '')}, {insp.get('city', '')}", "Technician:", insp.get("technician_name", "Assigned Lead")],
        ["Overall Score:", f"{insp.get('overall_score', 100)}% Compliance", "Inspection Status:", insp["status"]],
    ]
    t_meta = Table(meta, colWidths=[100, 170, 90, 180])
    t_meta.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Checklist Findings & Compliance Matrix:</b>", styles["Heading3"]))
    chk_rows = [["Item", "Category", "Severity", "Result"]]
    for item in insp.get("checklist_data", []):
        chk_rows.append([
            item.get("item", ""),
            item.get("category", "General"),
            item.get("severity", "MEDIUM"),
            item.get("status", "PASS")
        ])
    t_chk = Table(chk_rows, colWidths=[260, 100, 90, 90])
    t_chk.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_chk)
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Summary & Corrective Recommendations:</b>", styles["Heading3"]))
    story.append(Paragraph(insp.get("findings_summary", "Site in satisfactory operational condition."), styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Recommended Action:</b> {insp.get('recommendations', 'Continue regular maintenance schedule.')}", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()
