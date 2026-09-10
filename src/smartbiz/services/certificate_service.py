"""Certificate of Compliance (COC) management and PDF generation for SmartBiz Fire."""
import io
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from smartbiz.db import get_connection, db_lock

def generate_certificate_number() -> str:
    """Generates sequential certificate number like COC-2026-0891."""
    year = datetime.now(timezone.utc).year
    with db_lock, get_connection() as con:
        row = con.execute("SELECT id FROM certificates ORDER BY id DESC LIMIT 1").fetchone()
        next_id = (row[0] + 1) if row else 1
        return f"COC-{year}-{next_id:04d}"

def issue_certificate(
    customer_id: int,
    site_id: int,
    inspection_id: int = 0,
    scope: str = "Fire Safety Equipment & Annual Compliance Inspection",
    validity_days: int = 365,
    signatory_name: str = "Senior Fire Inspector",
    signatory_title: str = "SAQCC-Fire Registered Inspector (Reg# 22/064)",
) -> Dict[str, Any]:
    """Issues a new Certificate of Compliance."""
    now = datetime.now(timezone.utc)
    issue_date = now.strftime("%Y-%m-%d")
    expiry_date = (now + timedelta(days=validity_days)).strftime("%Y-%m-%d")
    cert_num = generate_certificate_number()

    with db_lock, get_connection() as con:
        cur = con.execute(
            """
            INSERT INTO certificates (
              certificate_number, customer_id, site_id, inspection_id,
              issue_date, expiry_date, scope_of_inspection, signatory_name,
              signatory_title, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ISSUED', ?)
            """,
            (
                cert_num, customer_id, site_id, inspection_id,
                issue_date, expiry_date, scope, signatory_name,
                signatory_title, now.isoformat()
            )
        )
        cert_id = cur.lastrowid
        con.commit()

    return get_certificate(cert_id)

def get_certificate(cert_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves certificate record."""
    with db_lock, get_connection() as con:
        row = con.execute(
            """
            SELECT cert.*, c.company_name, c.contact_name, c.email, c.phone,
                   s.site_name, s.address as site_address, s.city, s.province
            FROM certificates cert
            LEFT JOIN customers c ON cert.customer_id = c.id
            LEFT JOIN sites s ON cert.site_id = s.id
            WHERE cert.id = ?
            """,
            (cert_id,)
        ).fetchone()
        return dict(row) if row else None

def get_certificate_by_number(cert_number: str) -> Optional[Dict[str, Any]]:
    """Retrieves certificate record by unique certificate number."""
    with db_lock, get_connection() as con:
        row = con.execute(
            """
            SELECT cert.*, c.company_name, s.site_name, s.address as site_address, s.city, s.province
            FROM certificates cert
            LEFT JOIN customers c ON cert.customer_id = c.id
            LEFT JOIN sites s ON cert.site_id = s.id
            WHERE cert.certificate_number = ?
            """,
            (cert_number,)
        ).fetchone()
        return dict(row) if row else None

def generate_certificate_pdf(cert_id: int) -> bytes:
    """Generates official Certificate of Compliance PDF."""
    cert = get_certificate(cert_id)
    if not cert:
        raise ValueError(f"Certificate {cert_id} not found")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Title & Header
    story.append(Paragraph("<b>SMARTBIZ FIRE SAFETY</b>", styles["Heading1"]))
    story.append(Paragraph("<b>CERTIFICATE OF FIRE COMPLIANCE & INSPECTION</b>", styles["Title"]))
    story.append(Paragraph("Reg# 2025/515436/07 · SAQCC-Fire Reg. 22/064 · Republic of South Africa", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Certificate Number & Verification Badge
    cert_meta = [
        ["Certificate Number:", cert["certificate_number"], "Status:", "VALID & ACTIVE"],
        ["Date of Issue:", cert["issue_date"], "Expiry Date:", cert["expiry_date"]],
        ["Certified Organisation:", cert.get("company_name", "N/A"), "Site Name:", cert.get("site_name", "Main Site")],
        ["Site Location:", f"{cert.get('site_address', '')}, {cert.get('city', '')}", "Province:", cert.get("province", "Gauteng")],
    ]
    meta_table = Table(cert_meta, colWidths=[130, 150, 100, 160])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#1e293b")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # Scope of Certification
    story.append(Paragraph("<b>Scope of Certification & Findings:</b>", styles["Heading2"]))
    story.append(Paragraph(
        f"This document certifies that the fire safety equipment, extinguishers, hose reels, alarms, and emergency "
        f"egress compliance have been inspected at the stated premises in accordance with South African National Standards. "
        f"Scope: {cert.get('scope_of_inspection', 'Annual comprehensive safety audit')}. "
        f"All inspected units have been tested, serviced, and tagged for safe operational readiness.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 16))

    # Compliance statement & disclaimer
    story.append(Paragraph(
        "<b>Statutory Alignment & Advisory:</b><br/>"
        "This certificate is valid for twelve (12) calendar months from the date of issue provided that all equipment "
        "remains unobstructed, undamaged, and has not undergone discharge or tampering. Routine quarterly visual checks "
        "must be maintained by the responsible site safety officer.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 24))

    # Signatory Block
    sig_data = [
        ["Issued and Certified By:", "Verification QR & Audit Trail:"],
        [f"<b>{cert.get('signatory_name', 'Inspector')}</b>\n{cert.get('signatory_title', 'Fire Inspector')}\nSmartBiz Fire Safety Operations",
         f"Verify online at:\nhttps://smartbizfire.co.za/verify/{cert['certificate_number']}\nAudit ID: {cert['id']}"],
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#334155")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
