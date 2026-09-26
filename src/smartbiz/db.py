"""Database connection, schema definitions, and migration management for SmartBiz Fire."""
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

DB_PATH = os.environ.get("DB_PATH", "smartbiz.sqlite")
db_lock = threading.Lock()

def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_all_tables() -> None:
    """Initializes all database tables required for the SmartBiz Fire platform."""
    with db_lock, sqlite3.connect(DB_PATH) as con:
        # 1. Legacy tables preservation
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT DEFAULT '',
              company TEXT DEFAULT '',
              interest TEXT DEFAULT 'demo',
              status TEXT NOT NULL DEFAULT 'new',
              source TEXT DEFAULT 'organic',
              score INTEGER NOT NULL DEFAULT 0,
              industry TEXT NOT NULL DEFAULT 'general',
              location TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL DEFAULT ''
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
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id INTEGER NOT NULL,
              decision TEXT NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              decided_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_results (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT NOT NULL DEFAULT '',
              company TEXT NOT NULL DEFAULT '',
              score INTEGER NOT NULL DEFAULT 0,
              answers TEXT NOT NULL DEFAULT '{}',
              submitted_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT NOT NULL DEFAULT '',
              company TEXT NOT NULL DEFAULT '',
              service TEXT NOT NULL DEFAULT 'site-inspection',
              status TEXT NOT NULL DEFAULT 'pending',
              amount_cents INTEGER NOT NULL DEFAULT 0,
              currency TEXT NOT NULL DEFAULT 'ZAR',
              payfast_payment_id TEXT NOT NULL DEFAULT '',
              payfast_pf_payment_id TEXT NOT NULL DEFAULT '',
              payfast_status TEXT NOT NULL DEFAULT 'pending',
              payfast_updated_at TEXT NOT NULL DEFAULT '',
              evidence_notes TEXT NOT NULL DEFAULT '',
              evidence_photo_url TEXT NOT NULL DEFAULT '',
              assigned_technician_id INTEGER NOT NULL DEFAULT 0,
              location TEXT NOT NULL DEFAULT '',
              whatsapp_number TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        # Appointment booking lifecycle fields (idempotent migration).
        for statement in (
            "ALTER TABLE bookings ADD COLUMN scheduled_start TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE bookings ADD COLUMN scheduled_end TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE bookings ADD COLUMN booking_reference TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE bookings ADD COLUMN calendar_event_id INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE bookings ADD COLUMN whatsapp_status TEXT NOT NULL DEFAULT 'PENDING'",
        ):
            try:
                con.execute(statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_reference "
            "ON bookings(booking_reference) WHERE booking_reference != ''"
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS technicians (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT NOT NULL,
              pin TEXT NOT NULL DEFAULT '0000',
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS job_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              detail TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS request_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              method TEXT NOT NULL,
              path TEXT NOT NULL,
              status_code INTEGER NOT NULL,
              duration_ms INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )

        # 2. Advanced CRM & Platform Entities
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              full_name TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'CUSTOMER',
              phone TEXT NOT NULL DEFAULT '',
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              company_name TEXT NOT NULL,
              account_number TEXT UNIQUE NOT NULL,
              contact_name TEXT NOT NULL,
              email TEXT NOT NULL,
              phone TEXT NOT NULL DEFAULT '',
              whatsapp_number TEXT NOT NULL DEFAULT '',
              billing_address TEXT NOT NULL DEFAULT '',
              vat_number TEXT NOT NULL DEFAULT '',
              notes TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sites (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              customer_id INTEGER NOT NULL,
              site_name TEXT NOT NULL,
              address TEXT NOT NULL,
              suburb TEXT NOT NULL DEFAULT '',
              city TEXT NOT NULL DEFAULT 'Johannesburg',
              province TEXT NOT NULL DEFAULT 'Gauteng',
              postal_code TEXT NOT NULL DEFAULT '',
              building_type TEXT NOT NULL DEFAULT 'Commercial',
              occupancy_type TEXT NOT NULL DEFAULT 'Office',
              contact_person TEXT NOT NULL DEFAULT '',
              contact_phone TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              qr_code TEXT UNIQUE NOT NULL,
              site_id INTEGER NOT NULL,
              serial_number TEXT NOT NULL DEFAULT '',
              equipment_type TEXT NOT NULL,
              location_on_site TEXT NOT NULL DEFAULT '',
              capacity TEXT NOT NULL DEFAULT '4.5kg',
              manufacturer TEXT NOT NULL DEFAULT 'SmartBiz',
              model_year TEXT NOT NULL DEFAULT '2025',
              install_date TEXT NOT NULL DEFAULT '',
              last_service_date TEXT NOT NULL DEFAULT '',
              next_service_date TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'COMPLIANT',
              technician_notes TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(site_id) REFERENCES sites(id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_service_history (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              equipment_id INTEGER NOT NULL,
              technician_id INTEGER NOT NULL DEFAULT 0,
              service_date TEXT NOT NULL,
              service_type TEXT NOT NULL DEFAULT 'Annual Inspection',
              findings TEXT NOT NULL DEFAULT '',
              action_taken TEXT NOT NULL DEFAULT '',
              parts_replaced TEXT NOT NULL DEFAULT '',
              next_due_date TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(equipment_id) REFERENCES equipment(id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS inspections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              site_id INTEGER NOT NULL,
              technician_id INTEGER NOT NULL DEFAULT 0,
              scheduled_date TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'REQUESTED',
              overall_score INTEGER NOT NULL DEFAULT 100,
              checklist_data TEXT NOT NULL DEFAULT '[]',
              findings_summary TEXT NOT NULL DEFAULT '',
              recommendations TEXT NOT NULL DEFAULT '',
              signature_url TEXT NOT NULL DEFAULT '',
              completed_at TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(site_id) REFERENCES sites(id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              quote_number TEXT UNIQUE NOT NULL,
              customer_id INTEGER NOT NULL,
              site_id INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'DRAFT',
              subtotal_cents INTEGER NOT NULL DEFAULT 0,
              vat_cents INTEGER NOT NULL DEFAULT 0,
              total_cents INTEGER NOT NULL DEFAULT 0,
              line_items TEXT NOT NULL DEFAULT '[]',
              valid_until TEXT NOT NULL DEFAULT '',
              terms TEXT NOT NULL DEFAULT 'Payment due within 30 days. Standard South African VAT applies.',
              created_at TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS certificates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              certificate_number TEXT UNIQUE NOT NULL,
              customer_id INTEGER NOT NULL,
              site_id INTEGER NOT NULL,
              inspection_id INTEGER NOT NULL DEFAULT 0,
              issue_date TEXT NOT NULL,
              expiry_date TEXT NOT NULL,
              scope_of_inspection TEXT NOT NULL DEFAULT 'Fire Equipment & Extinguishers Inspection and Compliance',
              signatory_name TEXT NOT NULL DEFAULT 'Authorized Inspector',
              signatory_title TEXT NOT NULL DEFAULT 'Senior Fire Compliance Inspector',
              status TEXT NOT NULL DEFAULT 'ISSUED',
              pdf_url TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(customer_id) REFERENCES customers(id),
              FOREIGN KEY(site_id) REFERENCES sites(id)
            )
            """
        )
        # External calendar mirror fields.
        for statement in (
            "ALTER TABLE calendar_events ADD COLUMN external_event_id TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE calendar_events ADD COLUMN external_event_url TEXT NOT NULL DEFAULT ''",
        ):
            try:
                con.execute(statement)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              recipient TEXT NOT NULL,
              channel TEXT NOT NULL DEFAULT 'EMAIL',
              template_key TEXT NOT NULL,
              payload TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'QUEUED',
              scheduled_for TEXT NOT NULL DEFAULT '',
              sent_at TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              start_time TEXT NOT NULL,
              end_time TEXT NOT NULL,
              timezone TEXT NOT NULL DEFAULT 'Africa/Johannesburg',
              provider TEXT NOT NULL DEFAULT 'INTERNAL',
              external_event_id TEXT NOT NULL DEFAULT '',
              customer_id INTEGER NOT NULL DEFAULT 0,
              site_id INTEGER NOT NULL DEFAULT 0,
              technician_id INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        con.commit()
