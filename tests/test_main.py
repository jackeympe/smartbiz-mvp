from fastapi.testclient import TestClient
from smartbiz.main import app, DB_PATH
import threading
from datetime import datetime, timezone, timedelta
import sqlite3
import json
import os

client = TestClient(app)
lock = threading.Lock()

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample_data.json")
with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
    FIXTURES = json.load(f)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_jobs_create_and_list():
    r = client.post("/jobs", json={"client": "Jack", "site": "Site A"}, headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "job_id" in body

    r2 = client.get("/jobs", headers={"x-smartbiz-token": "dev"})
    assert r2.status_code == 200
    data = r2.json()["jobs"]
    assert any(item["client"] == "Jack" and item["site"] == "Site A" for item in data)

def test_job_requires_fields():
    r = client.post("/jobs", json={}, headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 400

def test_approve_reject_job():
    r = client.post("/jobs", json={"client": "Test", "site": "Site"}, headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    approve = client.post(f"/jobs/{job_id}/approve", json={"note": "looks good"}, headers={"x-smartbiz-token": "dev"})
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    reject = client.post(f"/jobs/{job_id}/reject", json={"note": "redo"}, headers={"x-smartbiz-token": "dev"})
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

def test_document_stub():
    r = client.post("/jobs", json={"client": "Doc", "site": "Site"}, headers={"x-smartbiz-token": "dev"})
    job_id = r.json()["job_id"]
    doc = client.get(f"/api/v1/documents/{job_id}", headers={"x-smartbiz-token": "dev"})
    assert doc.status_code == 200
    body = doc.json()
    assert body["type"] == "job_summary"
    assert "disclaimer" in body

def test_app_status():
    r = client.get("/api/v1/status", headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "counts" in body
    assert "checks" in body
    assert "db" in body["checks"]
    assert "xero" in body["checks"]
    assert "smtp" in body["checks"]

def test_create_lead_persists_and_lists():
    payload = FIXTURES["lead"]
    r = client.post("/api/v1/leads", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "lead_id" in body

    r2 = client.get("/leads", headers={"x-smartbiz-token": "dev"})
    assert r2.status_code == 200
    data = r2.json()["leads"]
    assert any(item["email"] == payload["email"] for item in data)

def test_create_lead_requires_fields():
    r = client.post("/api/v1/leads", json={"email": "x@y.com"})
    assert r.status_code == 400

def test_token_gate():
    r = client.get("/jobs")
    assert r.status_code == 401

def test_quiz_questions_count():
    r = client.get("/api/v1/quiz/questions")
    assert r.status_code == 200
    body = r.json()
    assert "questions" in body
    assert len(body["questions"]) == 10

def test_quiz_submit_requires_contact():
    r = client.post("/api/v1/quiz/submit", json={"answers": FIXTURES["quiz_answers"]})
    assert r.status_code == 400

def test_quiz_submit_returns_score():
    payload = {
        "first_name": "Quiz",
        "last_name": "User",
        "email": "quiz@example.com",
        "answers": FIXTURES["quiz_answers"],
    }
    r = client.post("/api/v1/quiz/submit", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "score" in body
    assert "label" in body

def test_export_leads_json():
    client.post("/api/v1/leads", json=FIXTURES["lead"])
    r = client.get("/leads/export", headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    data = r.json()
    assert "leads" in data
    assert any(item["email"] == FIXTURES["lead"]["email"] for item in data["leads"])

def test_export_quiz_csv():
    client.post("/api/v1/quiz/submit", json={"first_name":"Q","last_name":"T","email":"q@t.com","answers": FIXTURES["quiz_answers"]})
    r = client.get("/quiz/export?format=csv", headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    data = r.json()
    assert "csv" in data
    assert "first_name,last_name,email" in data["csv"]

def test_create_booking():
    payload = FIXTURES["booking"]
    r = client.post("/api/v1/bookings", json=payload, headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "booking_id" in body
    assert isinstance(body["payfast_url"], str)

def test_booking_list_and_analytics():
    r = client.get("/api/v1/bookings", headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    assert "bookings" in r.json()

    r2 = client.get("/api/v1/analytics/summary", headers={"x-smartbiz-token": "dev"})
    assert r2.status_code == 200
    body = r2.json()
    assert "bookings" in body
    assert "refunds" in body

def test_technician_qr_and_complete_with_evidence():
    payload = {
        "first_name": "Tech",
        "last_name": "Client",
        "email": "tech@example.com",
        "service": "site-inspection",
        "amount_cents": 1000,
    }
    r = client.post("/api/v1/bookings", json=payload, headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]

    qr = client.get(f"/bookings/{booking_id}/qr", headers={"x-smartbiz-token": "dev"})
    assert qr.status_code == 200
    body = qr.json()
    assert body["booking_id"] == booking_id
    assert body["qr_png_base64"]

    complete = client.post(f"/technician/complete/{booking_id}?token=tech-complete-1234", json={"visited": True, "completed": True, "evidence_notes": "extinguishers ok", "evidence_photo_url": "https://example.com/photo.jpg"}, headers={"x-smartbiz-token": "dev"})
    assert complete.status_code == 200
    assert complete.json()["status"] == "technician_completed"

    booking = client.get(f"/api/v1/bookings/{booking_id}/public").json()
    assert booking["evidence_notes"] == "extinguishers ok"
    assert booking["evidence_photo_url"] == "https://example.com/photo.jpg"

def test_refund_window_enforced():
    payload = {
        "first_name": "Refund",
        "last_name": "Client",
        "email": "refund@example.com",
        "service": "site-inspection",
        "amount_cents": 2000,
    }
    r = client.post("/api/v1/bookings", json=payload, headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]

    refund = client.post(f"/bookings/{booking_id}/refund", json={"reason": "no-show"}, headers={"x-smartbiz-token": "dev"})
    assert refund.status_code == 403
    assert "refund window" in refund.json()["detail"]

    with lock, sqlite3.connect(DB_PATH) as con:
        con.execute("UPDATE bookings SET created_at=? WHERE id=?", ((datetime.now(timezone.utc) - timedelta(days=6)).isoformat(), booking_id))
        con.commit()
    refund2 = client.post(f"/bookings/{booking_id}/refund", json={"reason": "no-show"}, headers={"x-smartbiz-token": "dev"})
    assert refund2.status_code == 200
    assert refund2.json()["status"] == "refunded"
    booking = client.get(f"/api/v1/bookings/{booking_id}/public").json()
    assert booking["status"] == "refunded"
    assert booking["payfast_status"] == "refunded"

def test_xero_not_configured():
    r = client.post("/api/v1/bookings", json=FIXTURES["booking"], headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]

    for path in [
        f"/xero/bookings/{booking_id}/contact",
        f"/xero/bookings/{booking_id}/invoice",
        f"/xero/bookings/{booking_id}/creditnote",
    ]:
        resp = client.post(path, headers={"x-smartbiz-token": "dev"})
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"]

def test_xero_health_reports_config():
    r = client.get("/xero/health", headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    body = r.json()
    assert "ok" in body
    assert isinstance(body["ok"], bool)

def test_booking_pdf_document():
    r = client.post("/api/v1/bookings", json=FIXTURES["booking"], headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]
    pdf = client.get(f"/bookings/{booking_id}/pdf", headers={"x-smartbiz-token": "dev"})
    assert pdf.status_code == 200
    body = pdf.json()
    assert body["booking_id"] == booking_id
    assert "pdf_base64" in body
    assert "booking-" in body["filename"]

def test_booking_coc_pdf_document():
    r = client.post("/api/v1/bookings", json=FIXTURES["booking"], headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]
    client.post(f"/technician/complete/{booking_id}?token=tech-complete-1234", json={"visited": True, "completed": True}, headers={"x-smartbiz-token": "dev"})
    client.post("/api/v1/quiz/submit", json={"first_name":"COC","last_name":"Doc","email":"coc@example.com","answers": FIXTURES["quiz_answers"]})
    pdf = client.get(f"/bookings/{booking_id}/coc-pdf", headers={"x-smartbiz-token": "dev"})
    assert pdf.status_code == 200
    body = pdf.json()
    assert body["booking_id"] == booking_id
    assert "pdf_base64" in body
    assert "coc-booking-" in body["filename"]

def test_technician_pin_flow():
    payload = FIXTURES["technician"]
    created = client.post("/api/v1/technicians", json=payload, headers={"x-smartbiz-token": "dev"})
    assert created.status_code == 200
    technician_id = created.json()["technician_id"]

    verified = client.post("/api/v1/technicians/verify", json={"pin": payload["pin"]}, headers={"x-smartbiz-token": "dev"})
    assert verified.status_code == 200
    assert verified.json()["technician"]["name"] == payload["name"]

    profile = client.get(f"/api/v1/technicians/{technician_id}", headers={"x-smartbiz-token": "dev"})
    assert profile.status_code == 200
    assert profile.json()["name"] == payload["name"]

    listing = client.get("/api/v1/technicians", headers={"x-smartbiz-token": "dev"})
    assert listing.status_code == 200
    assert any(item["email"] == payload["email"] for item in listing.json()["technicians"])

def test_technician_pin_rejects_invalid():
    r = client.post("/api/v1/technicians/verify", json={"pin": "0000"}, headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 403

def test_payfast_status_update():
    r = client.post("/api/v1/bookings", json=FIXTURES["booking"], headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]
    update = client.post(f"/bookings/{booking_id}/payfast-status", json={"status": "paid", "pf_payment_id": "pf-1", "payment_id": "pay-1"}, headers={"x-smartbiz-token": "dev"})
    assert update.status_code == 200
    assert update.json()["payfast_status"] == "paid"

    booking = client.get(f"/api/v1/bookings/{booking_id}/public").json()
    assert booking["payfast_status"] == "paid"

def test_xero_webhook_updates_booking_status():
    r = client.post("/api/v1/bookings", json=FIXTURES["booking"], headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]
    paid = client.post("/xero/webhook", json={"event_type": "INVOICE.PAID", "resource": {"booking_id": str(booking_id)}})
    assert paid.status_code == 200
    assert paid.json()["event"] == "invoice.paid"
    assert client.get(f"/api/v1/bookings/{booking_id}/public").json()["status"] == "paid"

    refunded = client.post("/xero/webhook", json={"event_type": "CREDITNOTE.CREATED", "resource": {"booking_id": str(booking_id)}})
    assert refunded.status_code == 200
    assert client.get(f"/api/v1/bookings/{booking_id}/public").json()["status"] == "refunded"

def test_end_to_end_quiz_booking_completion_pdf():
    answers = FIXTURES["quiz_answers"]
    quiz = client.post("/api/v1/quiz/submit", json={"first_name":"E2E","last_name":"Flow","email":"e2e@example.com","answers":answers})
    assert quiz.status_code == 200

    booking = client.post("/api/v1/bookings", json={"first_name":"E2E","last_name":"Flow","email":"e2e@example.com","service":"site-inspection","amount_cents":5000}, headers={"x-smartbiz-token": "dev"})
    assert booking.status_code == 200
    booking_id = booking.json()["booking_id"]

    qr = client.get(f"/bookings/{booking_id}/qr", headers={"x-smartbiz-token": "dev"})
    assert qr.status_code == 200

    complete = client.post(f"/technician/complete/{booking_id}?token=tech-complete-1234", json={"visited": True, "completed": True, "evidence_notes": "ok", "evidence_photo_url": "https://example.com/photo.jpg"}, headers={"x-smartbiz-token": "dev"})
    assert complete.status_code == 200
    assert complete.json()["status"] == "technician_completed"

    pdf = client.get(f"/bookings/{booking_id}/pdf", headers={"x-smartbiz-token": "dev"})
    assert pdf.status_code == 200
    body = pdf.json()
    assert body["booking_id"] == booking_id
    assert "pdf_base64" in body

    coc = client.get(f"/bookings/{booking_id}/coc-pdf", headers={"x-smartbiz-token": "dev"})
    assert coc.status_code == 200
    body = coc.json()
    assert body["booking_id"] == booking_id
    assert "pdf_base64" in body

    refund = client.post(f"/bookings/{booking_id}/refund", json={"reason": "no-show"}, headers={"x-smartbiz-token": "dev"})
    assert refund.status_code == 403

def test_technician_page_allows_evidence_input():
    with open("website/technician.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert "evidence_notes" in html
    assert "evidence_photo_url" in html
