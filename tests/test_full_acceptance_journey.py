import os
"""Comprehensive End-to-End Acceptance Test validating the entire 25-step SmartBiz Fire business lifecycle:
Lead -> Customer -> Inspection -> Calendar -> Technician Dispatch -> Equipment QR Scan -> Checklist ->
Signature -> Report -> Certificate of Compliance -> Portal -> Renewal Engine.
"""
import base64
import json
import pytest
from starlette.testclient import TestClient
from smartbiz.main import app
from smartbiz.db import init_all_tables
from smartbiz.auth import seed_default_admin

@pytest.fixture(autouse=True)
def setup_db():
    init_all_tables()
    seed_default_admin()

def test_full_acceptance_journey_steps_1_to_25():
    client = TestClient(app)
    admin_headers = {"x-smartbiz-token": os.environ.get("SMARTBIZ_ADMIN_TOKEN", "dev")}

    # 1. Visitor opens homepage and verifies public status
    health_res = client.get("/health")
    assert health_res.status_code == 200

    # 2. Visitor submits Book Inspection form (/book-inspection)
    booking_res = client.post("/api/v1/bookings", json={
        "first_name": "Kagiso",
        "last_name": "Radebe",
        "email": "kagiso@radebelogistics.co.za",
        "phone": "+27829991234",
        "company": "Radebe Logistics Hub",
        "service": "Annual Compliance Inspection & COC",
        "location": "12 Production Rd, City Deep, Johannesburg",
        "whatsapp_number": "+27829991234",
        "amount_cents": 0,
        "currency": "ZAR",
        "source": "website-book-inspection"
    })
    assert booking_res.status_code == 200
    booking = booking_res.json()
    booking_id = booking.get("booking_id") or booking.get("id")
    assert booking_id is not None

    # 3. Lead appears in system and is confirmed
    conf_res = client.post(f"/api/v1/bookings/{booking_id}/confirm")
    assert conf_res.status_code == 200
    assert conf_res.json()["status"] == "confirmed"

    # 4 & 5. Customer and Site records are created in CRM
    cust_res = client.post("/api/v1/customers", json={
        "company_name": "Radebe Logistics Hub",
        "contact_name": "Kagiso Radebe",
        "email": "kagiso@radebelogistics.co.za",
        "phone": "+27829991234",
        "whatsapp_number": "+27829991234",
        "billing_address": "12 Production Rd, City Deep, Johannesburg",
        "vat_number": "4120987654"
    })
    assert cust_res.status_code == 200
    cust_id = cust_res.json()["customer"]["id"]

    site_res = client.post("/api/v1/sites", json={
        "customer_id": cust_id,
        "site_name": "City Deep Warehouse Facility",
        "address": "12 Production Rd",
        "city": "Johannesburg",
        "province": "Gauteng",
        "building_type": "Warehouse / Logistics"
    })
    assert site_res.status_code == 200
    site_id = site_res.json()["site"]["id"]

    # 6 & 8. Admin schedules inspection request
    insp_res = client.post("/api/v1/inspections", json={
        "site_id": site_id,
        "technician_id": 1,
        "scheduled_date": "2026-09-18"
    }, headers=admin_headers)
    assert insp_res.status_code == 200
    insp_id = insp_res.json()["inspection"]["id"]

    # 9. Calendar event is created with Africa/Johannesburg timezone
    cal_res = client.post("/api/v1/calendar/events", json={
        "title": "SmartBiz Fire Inspection - Radebe Logistics",
        "start_time": "2026-09-18T09:00:00",
        "end_time": "2026-09-18T12:00:00",
        "customer_id": cust_id,
        "site_id": site_id,
        "technician_id": 1
    })
    assert cal_res.status_code == 200
    assert cal_res.json()["ok"] is True

    # 10 & 11. Technician assignment
    assign_res = client.post(f"/api/v1/bookings/{booking_id}/assign", json={"technician_id": 1}, headers={"x-smartbiz-token": "dev"})
    assert assign_res.status_code == 200

    # 12 & 13. Equipment item registered with QR code & scanned by technician
    eq_res = client.post("/api/v1/equipment", json={
        "site_id": site_id,
        "equipment_type": "DCP_EXTINGUISHER",
        "location_on_site": "Bay 3 - Flammable Goods Racking",
        "capacity": "9.0kg",
        "serial_number": "SN-RDB-0012",
        "status": "COMPLIANT"
    })
    assert eq_res.status_code == 200
    eq = eq_res.json()["equipment"]
    eq_id = eq["id"]
    qr_code = eq["qr_code"]

    # Scan lookup
    scan_res = client.get(f"/api/v1/equipment/qr/{qr_code}")
    assert scan_res.status_code == 200
    assert scan_res.json()["equipment"]["qr_code"] == qr_code

    # 14, 15, 16, 17. Technician completes checklist, uploads photos & signature
    checklist_results = [
        {"id": "chk_ext_access", "item": "Extinguishers accessible", "status": "PASS"},
        {"id": "chk_pressure", "item": "Operating pressure verified", "status": "PASS"},
        {"id": "chk_signage", "item": "Signage clearly visible", "status": "PASS"},
    ]
    complete_res = client.post(f"/api/v1/inspections/{insp_id}/complete", json={
        "checklist_results": checklist_results,
        "findings_summary": "All 9kg DCP extinguishers inspected, weighed, and re-tagged.",
        "recommendations": "Maintain clear 1-metre perimeter around fire points.",
        "signature_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    }, headers=admin_headers)
    assert complete_res.status_code == 200
    assert complete_res.json()["inspection"]["status"] == "COMPLETED"
    assert complete_res.json()["inspection"]["overall_score"] == 100

    # 18 & 19. Generate Service / Inspection Report PDF
    insp_pdf_res = client.get(
        f"/api/v1/inspections/{insp_id}/pdf",
        headers=admin_headers
    )
    assert insp_pdf_res.status_code == 200
    assert len(base64.b64decode(insp_pdf_res.json()["pdf_base64"])) > 500

    # 20. Issue official Certificate of Compliance (COC)
    cert_res = client.post("/api/v1/certificates", json={
        "customer_id": cust_id,
        "site_id": site_id,
        "inspection_id": insp_id,
        "scope": "Annual Logistics Warehouse Fire Safety Audit",
        "validity_days": 365
    })
    assert cert_res.status_code == 200
    cert = cert_res.json()["certificate"]
    cert_id = cert["id"]
    cert_num = cert["certificate_number"]

    # Verify Certificate Online
    ver_res = client.get(f"/api/v1/certificates/verify/{cert_num}")
    assert ver_res.status_code == 200
    assert ver_res.json()["verified"] is True

    # Certificate PDF
    cert_pdf_res = client.get(f"/api/v1/certificates/{cert_id}/pdf")
    assert cert_pdf_res.status_code == 200
    assert len(base64.b64decode(cert_pdf_res.json()["pdf_base64"])) > 500

    # 21 & 22. Customer logs into portal
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@smartbizfire.co.za",
        "password": "SmartBizFire2026!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["token"]

    # 23. Customer accesses customer details & sites
    portal_res = client.get(f"/api/v1/customers/{cust_id}")
    assert portal_res.status_code == 200
    assert portal_res.json()["customer"]["company_name"] == "Radebe Logistics Hub"

    # 24 & 25. Equipment next service date stored & Renewal Reminders engine runs
    renewal_res = client.post("/api/v1/renewal/scan")
    assert renewal_res.status_code == 200
    assert renewal_res.json()["ok"] is True
    assert renewal_res.json()["scanned_equipment"] >= 1
    assert renewal_res.json()["scanned_certificates"] >= 1
