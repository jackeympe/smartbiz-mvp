"""CRM service for managing Customers, Sites, Contacts, and Lead-to-Customer conversion."""
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from smartbiz.db import get_connection, db_lock

def generate_account_number() -> str:
    """Generates the next unique customer account number like SBF-2026-0104."""
    with db_lock, get_connection() as con:
        row = con.execute("SELECT id FROM customers ORDER BY id DESC LIMIT 1").fetchone()
        next_id = (row[0] + 1) if row else 1
        year = datetime.now(timezone.utc).year
        return f"SBF-{year}-{next_id:04d}"

def create_customer(
    company_name: str,
    contact_name: str,
    email: str,
    phone: str = "",
    whatsapp_number: str = "",
    billing_address: str = "",
    vat_number: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """Creates a new customer account."""
    now_iso = datetime.now(timezone.utc).isoformat()
    acc_num = generate_account_number()
    with db_lock, get_connection() as con:
        cur = con.execute(
            """
            INSERT INTO customers (
              company_name, account_number, contact_name, email, phone,
              whatsapp_number, billing_address, vat_number, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name, acc_num, contact_name, email, phone,
                whatsapp_number, billing_address, vat_number, notes, now_iso, now_iso
            )
        )
        cust_id = cur.lastrowid
        con.commit()
    return get_customer(cust_id)

def get_customer(customer_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves customer record with site counts and equipment summary."""
    with db_lock, get_connection() as con:
        row = con.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            return None
        cust = dict(row)
        sites = con.execute("SELECT * FROM sites WHERE customer_id = ?", (customer_id,)).fetchall()
        cust["sites"] = [dict(s) for s in sites]
        return cust

def list_customers(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Lists all customer records."""
    with db_lock, get_connection() as con:
        rows = con.execute(
            """
            SELECT c.*, count(s.id) as site_count
            FROM customers c
            LEFT JOIN sites s ON c.id = s.customer_id
            GROUP BY c.id
            ORDER BY c.id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]

def create_site(
    customer_id: int,
    site_name: str,
    address: str,
    suburb: str = "",
    city: str = "Johannesburg",
    province: str = "Gauteng",
    postal_code: str = "",
    building_type: str = "Commercial",
    occupancy_type: str = "Office",
    contact_person: str = "",
    contact_phone: str = "",
) -> Dict[str, Any]:
    """Creates a new site for a customer."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with db_lock, get_connection() as con:
        cur = con.execute(
            """
            INSERT INTO sites (
              customer_id, site_name, address, suburb, city, province,
              postal_code, building_type, occupancy_type, contact_person, contact_phone, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id, site_name, address, suburb, city, province,
                postal_code, building_type, occupancy_type, contact_person, contact_phone, now_iso
            )
        )
        site_id = cur.lastrowid
        con.commit()
    return get_site(site_id)

def get_site(site_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves site record."""
    with db_lock, get_connection() as con:
        row = con.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
        return dict(row) if row else None

def list_sites_for_customer(customer_id: int) -> List[Dict[str, Any]]:
    """Lists sites for a given customer."""
    with db_lock, get_connection() as con:
        rows = con.execute("SELECT * FROM sites WHERE customer_id = ? ORDER BY id ASC", (customer_id,)).fetchall()
        return [dict(r) for r in rows]

def ensure_customer_and_site_from_lead_or_booking(
    company_name: str,
    contact_name: str,
    email: str,
    phone: str,
    location_address: str,
    whatsapp_number: str = "",
) -> Tuple[int, int]:
    """Finds existing or creates new Customer and Site records."""
    comp = (company_name or f"{contact_name} Property").strip()
    addr = (location_address or "Johannesburg, South Africa").strip()

    with db_lock, get_connection() as con:
        # Check if customer exists with matching email or company name
        cust_row = con.execute(
            "SELECT id FROM customers WHERE email = ? OR company_name = ? LIMIT 1",
            (email, comp)
        ).fetchone()

        if cust_row:
            cust_id = cust_row[0]
        else:
            cust = create_customer(
                company_name=comp,
                contact_name=contact_name,
                email=email,
                phone=phone,
                whatsapp_number=whatsapp_number or phone,
            )
            cust_id = cust["id"]

        # Check if site exists
        site_row = con.execute(
            "SELECT id FROM sites WHERE customer_id = ? AND (address = ? OR site_name = ?) LIMIT 1",
            (cust_id, addr, f"{comp} Main Site")
        ).fetchone()

        if site_row:
            site_id = site_row[0]
        else:
            site = create_site(
                customer_id=cust_id,
                site_name=f"{comp} Main Site",
                address=addr,
                contact_person=contact_name,
                contact_phone=phone,
            )
            site_id = site["id"]

        return cust_id, site_id
