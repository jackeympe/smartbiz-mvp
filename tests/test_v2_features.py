import os
"""Comprehensive test suite for SmartBiz Fire V2 Platform features:
Auth, Customers, Sites, Equipment Register, QR verification, Inspections, Quotes (15% VAT), Certificates, Calendar, WhatsApp, and Renewal Reminders.
"""
import base64
import json
import os
import pytest
from starlette.testclient import TestClient
from smartbiz.main import app
from smartbiz.db import init_all_tables
from smartbiz.auth import hash_password, seed_default_admin

@pytest.fixture(autouse=True)
def setup_db():
    init_all_tables()
    seed_default_admin()

def test_v2_auth_login_and_me():
    client = TestClient(app)
    admin_headers = {"x-smartbiz-token": os.environ.get("SMARTBIZ_ADMIN_TOKEN", "dev")}
    # 1. Login with default seeded admin
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@smartbizfire.co.za",
        "password": "SmartBizFire2026!"
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert "token" in data
    assert data["user"]["email"] == "admin@smartbizfire.co.za"
    assert data["user"]["role"] == "SUPER_ADMIN"

    # 2. Check /auth/me with Bearer token
    token = data["token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user"]["email"] == "admin@smartbizfire.co.za"

def test_v2_customer_and_site_lifecycle():
    client = TestClient(app)
    # 1. Create customer
    cust_resp = client.post("/api/v1/customers", json={
        "company_name": "Sandton Towers Properties",
        "contact_name": "Lindiwe Ndlovu",
        "email": "lindiwe@sandtontowers.co.za",
        "phone": "+27118880000",
        "whatsapp_number": "+27677684582",
        "billing_address": "83 Rivonia Rd, Sandton, 2196",
        "vat_number": "4980234567"
    })
    assert cust_resp.status_code == 200
    cust = cust_resp.json()["customer"]
    cust_id = cust["id"]
    assert cust["account_number"].startswith("SBF-")
    assert cust["company_name"] == "Sandton Towers Properties"

    # 2. Create site under customer
    site_resp = client.post("/api/v1/sites", json={
        "customer_id": cust_id,
        "site_name": "Tower A - Corporate Office",
        "address": "83 Rivonia Rd",
        "suburb": "Sandton",
        "city": "Johannesburg",
        "province": "Gauteng",
        "building_type": "High-Rise Commercial",
        "occupancy_type": "Office"
    })
    assert site_resp.status_code == 200
    site = site_resp.json()["site"]
    site_id = site["id"]
    assert site["customer_id"] == cust_id

    # 3. Retrieve customer with nested sites
    detail_resp = client.get(f"/api/v1/customers/{cust_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["customer"]
    assert len(detail["sites"]) >= 1

def test_v2_equipment_register_and_qr_verification():
    client = TestClient(app)
    # 1. Create equipment on site
    eq_resp = client.post("/api/v1/equipment", json={
        "site_id": 1,
        "equipment_type": "DCP_EXTINGUISHER",
        "location_on_site": "Level 4 - Server Room",
        "capacity": "9kg",
        "serial_number": "SN-2026-9912",
        "status": "COMPLIANT"
    })
    assert eq_resp.status_code == 200
    eq = eq_resp.json()["equipment"]
    eq_id = eq["id"]
    qr_code = eq["qr_code"]
    assert qr_code.startswith("SB-FE-")

    # 2. Public / Mobile QR scan lookup
    scan_resp = client.get(f"/api/v1/equipment/qr/{qr_code}")
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()["equipment"]
    assert scan_data["qr_code"] == qr_code
    assert scan_data["equipment_type"] == "DCP_EXTINGUISHER"
    assert scan_data["status"] == "COMPLIANT"

    # 3. Record service action
    srv_resp = client.patch(f"/api/v1/equipment/{eq_id}", json={
        "status": "COMPLIANT",
        "findings": "Pressure gauge verified in green",
        "action_taken": "Safety seal renewed & weight verified",
        "technician_id": 1
    })
    assert srv_resp.status_code == 200
    updated_eq = srv_resp.json()["equipment"]
    assert "Safety seal renewed" in updated_eq["technician_notes"]

def test_v2_quote_lifecycle_vat_calculation_and_pdf():
    client = TestClient(app)
    # 1. Create Quote with line items
    items = [
        {"description": "Annual Extinguisher Inspection", "quantity": 10, "unit_price_cents": 15000}, # R 1,500.00
        {"description": "Fire Hose Reel Hydrostatic Test", "quantity": 2, "unit_price_cents": 25000},  # R   500.00
    ] # Subtotal: R 2,000.00 (200,000 cents) -> VAT 15%: R 300.00 (30,000 cents) -> Total: R 2,300.00 (230,000 cents)

    quote_resp = client.post("/api/v1/quotes", json={
        "customer_id": 1,
        "site_id": 1,
        "line_items": items,
        "validity_days": 30
    })
    assert quote_resp.status_code == 200
    quote = quote_resp.json()["quote"]
    quote_id = quote["id"]
    assert quote["subtotal_cents"] == 200000
    assert quote["vat_cents"] == 30000
    assert quote["total_cents"] == 230000
    assert quote["status"] == "DRAFT"

    # 2. Customer approves quote
    appr_resp = client.post(f"/api/v1/quotes/{quote_id}/approve", json={"decision": "APPROVED"})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["quote"]["status"] == "APPROVED"

    # 3. Generate Quote PDF
    pdf_resp = client.get(f"/api/v1/quotes/{quote_id}/pdf")
    assert pdf_resp.status_code == 200
    pdf_data = pdf_resp.json()
    assert "pdf_base64" in pdf_data
    assert len(base64.b64decode(pdf_data["pdf_base64"])) > 1000

def test_v2_inspection_and_certificate_of_compliance():
    client = TestClient(app)
    admin_headers = {"x-smartbiz-token": os.environ.get("SMARTBIZ_ADMIN_TOKEN", "dev")}
    # 1. Create Inspection
    insp_resp = client.post("/api/v1/inspections", json={
        "site_id": 1,
        "technician_id": 1,
        "scheduled_date": "2026-09-12"
    }, headers=admin_headers)
    assert insp_resp.status_code == 200
    insp_id = insp_resp.json()["inspection"]["id"]

    # 2. Complete checklist
    results = [
        {"id": "chk_ext_access", "item": "Extinguishers accessible", "status": "PASS"},
        {"id": "chk_hose_reel", "item": "Hose reels tested", "status": "PASS"},
        {"id": "chk_alarm", "item": "Alarm sounder test", "status": "PASS"},
    ]
    comp_resp = client.post(f"/api/v1/inspections/{insp_id}/complete", json={
        "checklist_results": results,
        "findings_summary": "100% compliant during annual audit",
        "recommendations": "Keep exits clear at all times"
    }, headers=admin_headers)
    assert comp_resp.status_code == 200
    completed_insp = comp_resp.json()["inspection"]
    assert completed_insp["status"] == "COMPLETED"
    assert completed_insp["overall_score"] == 100

    # 3. Generate Inspection Report PDF
    insp_pdf_resp = client.get(
        f"/api/v1/inspections/{insp_id}/pdf",
        headers=admin_headers
    )
    assert insp_pdf_resp.status_code == 200

    # 4. Issue Certificate of Compliance (COC)
    cert_resp = client.post("/api/v1/certificates", json={
        "customer_id": 1,
        "site_id": 1,
        "inspection_id": insp_id,
        "scope": "Comprehensive Annual Fire Safety Certification",
        "validity_days": 365
    })
    assert cert_resp.status_code == 200
    cert = cert_resp.json()["certificate"]
    cert_id = cert["id"]
    cert_num = cert["certificate_number"]
    assert cert_num.startswith("COC-")
    assert cert["status"] == "ISSUED"

    # 5. Public verification of COC
    ver_resp = client.get(f"/api/v1/certificates/verify/{cert_num}")
    assert ver_resp.status_code == 200
    assert ver_resp.json()["verified"] is True

    # 6. Generate Certificate PDF
    cert_pdf_resp = client.get(f"/api/v1/certificates/{cert_id}/pdf")
    assert cert_pdf_resp.status_code == 200

def test_v2_calendar_and_renewal_engine():
    client = TestClient(app)
    # 1. Calendar event creation
    cal_resp = client.post("/api/v1/calendar/events", json={
        "title": "On-Site Extinguisher Inspection",
        "start_time": "2026-09-15T09:00:00",
        "end_time": "2026-09-15T11:00:00",
        "customer_id": 1,
        "site_id": 1
    })
    assert cal_resp.status_code == 200
    assert cal_resp.json()["ok"] is True

    # 2. List calendar events
    list_resp = client.get("/api/v1/calendar/events")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["events"]) >= 1

    # 3. Trigger Renewal Engine scan
    renewal_resp = client.post("/api/v1/renewal/scan")
    assert renewal_resp.status_code == 200
    data = renewal_resp.json()
    assert data["ok"] is True
    assert "scanned_equipment" in data
    assert "scanned_certificates" in data

def test_v2_whatsapp_webhook_and_menu_flow():
    client = TestClient(app)
    # 1. Webhook verification GET
    verify_resp = client.get("/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=smartbiz_fire_verify_2026&hub.challenge=CHALLENGE_ACCEPTED")
    assert verify_resp.status_code == 200
    assert verify_resp.text == "CHALLENGE_ACCEPTED"

    # 2. Simulate incoming 'Hi' message
    msg_resp = client.post("/api/v1/webhooks/whatsapp", json={
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "27677684582",
                        "text": {"body": "Hi"}
                    }]
                }
            }]
        }]
    })
    assert msg_resp.status_code == 200
    res_data = msg_resp.json()
    assert res_data["ok"] is True
    assert len(res_data["responses"]) == 1
    assert "SmartBiz Fire Safety" in res_data["responses"][0]["message"]
