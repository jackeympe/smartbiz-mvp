"""Quotation management, calculation (15% South African VAT), and PDF generation for SmartBiz Fire."""
import io
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from smartbiz.db import get_connection, db_lock

VAT_RATE = 0.15  # 15% South African VAT

def generate_quote_number() -> str:
    """Generates sequential quote number like QT-2026-0042."""
    year = datetime.now(timezone.utc).year
    with db_lock, get_connection() as con:
        row = con.execute("SELECT id FROM quotes ORDER BY id DESC LIMIT 1").fetchone()
        next_id = (row[0] + 1) if row else 1
        return f"QT-{year}-{next_id:04d}"

def calculate_quote_totals(line_items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculates subtotal, VAT (15%), and total in integer cents."""
    subtotal_cents = 0
    for item in line_items:
        qty = int(item.get("quantity", 1))
        unit_price = int(item.get("unit_price_cents", 0))
        subtotal_cents += (qty * unit_price)
    vat_cents = int(round(subtotal_cents * VAT_RATE))
    total_cents = subtotal_cents + vat_cents
    return {
        "subtotal_cents": subtotal_cents,
        "vat_cents": vat_cents,
        "total_cents": total_cents,
    }

def create_quote(
    customer_id: int,
    site_id: int = 0,
    line_items: Optional[List[Dict[str, Any]]] = None,
    validity_days: int = 30,
    terms: str = "Payment terms: 30 days from invoice date. 15% South African VAT included.",
) -> Dict[str, Any]:
    """Creates a new quote record."""
    items = line_items or [
        {"description": "Annual Fire Safety Inspection & Certification", "quantity": 1, "unit_price_cents": 120000},
        {"description": "4.5kg DCP Fire Extinguisher Service & Pressure Test", "quantity": 4, "unit_price_cents": 18000},
        {"description": "9kg CO2 Fire Extinguisher Refill & Inspection", "quantity": 2, "unit_price_cents": 25000},
        {"description": "Fire Hose Reel Flow Test & Signage Check", "quantity": 2, "unit_price_cents": 15000},
    ]
    totals = calculate_quote_totals(items)
    now = datetime.now(timezone.utc)
    valid_until = (now + timedelta(days=validity_days)).strftime("%Y-%m-%d")
    quote_num = generate_quote_number()

    with db_lock, get_connection() as con:
        cur = con.execute(
            """
            INSERT INTO quotes (
              quote_number, customer_id, site_id, status, subtotal_cents,
              vat_cents, total_cents, line_items, valid_until, terms, created_at
            ) VALUES (?, ?, ?, 'DRAFT', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quote_num, customer_id, site_id, totals["subtotal_cents"],
                totals["vat_cents"], totals["total_cents"], json.dumps(items),
                valid_until, terms, now.isoformat()
            )
        )
        quote_id = cur.lastrowid
        con.commit()

    return get_quote(quote_id)

def get_quote(quote_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves quote record."""
    with db_lock, get_connection() as con:
        row = con.execute(
            """
            SELECT q.*, c.company_name, c.contact_name, c.email, c.phone, c.billing_address,
                   s.site_name, s.address as site_address
            FROM quotes q
            LEFT JOIN customers c ON q.customer_id = c.id
            LEFT JOIN sites s ON q.site_id = s.id
            WHERE q.id = ?
            """,
            (quote_id,)
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["line_items"] = json.loads(data["line_items"]) if data.get("line_items") else []
        return data

def approve_quote(quote_id: int, decision: str = "APPROVED", note: str = "") -> Dict[str, Any]:
    """Updates quote status to APPROVED or DECLINED."""
    with db_lock, get_connection() as con:
        con.execute(
            "UPDATE quotes SET status = ? WHERE id = ?",
            (decision, quote_id)
        )
        con.commit()
    return get_quote(quote_id)

def generate_quote_pdf(quote_id: int) -> bytes:
    """Generates a professional ReportLab PDF for a quotation."""
    quote = get_quote(quote_id)
    if not quote:
        raise ValueError(f"Quote {quote_id} not found")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Header
    story.append(Paragraph("<b>SMARTBIZ FIRE SAFETY (PTY) LTD</b>", styles["Heading1"]))
    story.append(Paragraph("Reg# 2025/515436/07 · SAQCC-Fire Reg. 22/064 · South Africa", styles["Normal"]))
    story.append(Paragraph("Email: compliance@smartbizfire.co.za · Phone: +27 11 000 0000", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Title & Metadata
    story.append(Paragraph(f"<b>OFFICIAL QUOTATION #{quote['quote_number']}</b>", styles["Heading2"]))
    story.append(Spacer(1, 8))

    meta_data = [
        ["Date Issued:", quote["created_at"][:10], "Valid Until:", quote["valid_until"]],
        ["Customer:", quote.get("company_name", "N/A"), "Contact:", quote.get("contact_name", "N/A")],
        ["Site Location:", quote.get("site_address", "Johannesburg CBD"), "Status:", quote["status"]],
    ]
    meta_table = Table(meta_data, colWidths=[100, 170, 90, 180])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#334155")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # Line items table
    table_data = [["Item Description", "Qty", "Unit Price (ZAR)", "Total (ZAR)"]]
    for item in quote.get("line_items", []):
        qty = int(item.get("quantity", 1))
        unit = int(item.get("unit_price_cents", 0)) / 100.0
        line_total = qty * unit
        table_data.append([item.get("description", "Service"), str(qty), f"R {unit:,.2f}", f"R {line_total:,.2f}"])

    subtotal = quote["subtotal_cents"] / 100.0
    vat = quote["vat_cents"] / 100.0
    total = quote["total_cents"] / 100.0

    table_data.append(["", "", "Subtotal:", f"R {subtotal:,.2f}"])
    table_data.append(["", "", "VAT (15%):", f"R {vat:,.2f}"])
    table_data.append(["", "", "<b>Total Due:</b>", f"<b>R {total:,.2f}</b>"])

    item_table = Table(table_data, colWidths=[280, 50, 110, 100])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-4), 0.5, colors.HexColor("#cbd5e1")),
        ('LINEABOVE', (2,-3), (-1,-1), 1, colors.HexColor("#0f172a")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 20))

    # Terms
    story.append(Paragraph("<b>Terms & Conditions:</b>", styles["Heading3"]))
    story.append(Paragraph(quote.get("terms", "All fire equipment servicing adheres to South African National Standards."), styles["Normal"]))
    story.append(Spacer(1, 20))

    # Signature Block
    sig_data = [
        ["Authorized by SmartBiz Fire:", "Customer Acceptance Signature:"],
        ["\n\n___________________________", "\n\n___________________________"],
        ["SmartBiz Fire Safety Officer", "Authorized Representative"],
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#475569")),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
