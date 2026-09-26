import os
import tempfile
from pathlib import Path

# Deterministic test authentication.
# Never inherit production/admin credentials into pytest.
os.environ["SMARTBIZ_ADMIN_TOKEN"] = "dev"
os.environ["SMARBIZ_TECHNICIAN_TOKEN"] = "test-tech-token"

# Isolated SQLite database for the entire test session.
_fd, _db_path = tempfile.mkstemp(prefix="smartbiz-pytest-", suffix=".sqlite")
os.close(_fd)
Path(_db_path).unlink(missing_ok=True)

os.environ["DB_PATH"] = _db_path

from smartbiz.db import init_all_tables, get_connection
from smartbiz.auth import seed_default_admin

init_all_tables()
seed_default_admin()

# Deterministic Customer -> Site -> Technician test data.
with get_connection() as con:
    con.execute(
        """
        INSERT INTO customers (
            id, company_name, account_number, contact_name,
            email, phone, whatsapp_number, billing_address,
            vat_number, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "SmartBiz Pytest Customer",
            "TEST-0001",
            "Test Contact",
            "pytest-customer@smartbizfire.co.za",
            "0100000000",
            "0100000000",
            "1 Test Street, Johannesburg",
            "",
            "Automated test fixture",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )

    con.execute(
        """
        INSERT INTO sites (
            id, customer_id, site_name, address, suburb,
            city, province, postal_code, building_type,
            occupancy_type, contact_person, contact_phone,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1,
            "SmartBiz Pytest Site",
            "1 Test Street",
            "Test Suburb",
            "Johannesburg",
            "Gauteng",
            "2000",
            "Commercial",
            "Office",
            "Test Contact",
            "0100000000",
            "2026-01-01T00:00:00+00:00",
        ),
    )

    con.execute(
        """
        INSERT INTO technicians
            (name, email, pin, active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (
            "Test Technician",
            "pytest-technician@smartbizfire.co.za",
            "2468",
            "2026-01-01T00:00:00+00:00",
        ),
    )

    con.commit()


def pytest_sessionfinish(session, exitstatus):
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(_db_path + suffix).unlink()
        except FileNotFoundError:
            pass
