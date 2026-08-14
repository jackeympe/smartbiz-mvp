from fastapi.testclient import TestClient
from smartbiz.main import app

client = TestClient(app)

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

def test_create_lead_persists_and_lists():
    payload = {
        "first_name": "Jack",
        "last_name": "Mpe",
        "email": "jack@example.com",
        "phone": "0720000000",
        "company": "SmartBiz",
        "interest": "demo",
    }
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
    r = client.post("/api/v1/quiz/submit", json={"answers": {"q1": "Yes"}})
    assert r.status_code == 400

def test_quiz_submit_returns_score():
    answers = {f"q{i}": "Yes" if i % 2 == 1 else "No" for i in range(1, 11)}
    payload = {
        "first_name": "Quiz",
        "last_name": "User",
        "email": "quiz@example.com",
        "answers": answers,
    }
    r = client.post("/api/v1/quiz/submit", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "score" in body
    assert "label" in body
    assert body["score"] == 5

def test_export_leads_json():
    client.post("/api/v1/leads", json={"first_name":"E","last_name":"L","email":"e@l.com"})
    r = client.get("/leads/export", headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    data = r.json()
    assert "leads" in data
    assert any(item["email"] == "e@l.com" for item in data["leads"])

def test_export_quiz_csv():
    client.post("/api/v1/quiz/submit", json={"first_name":"Q","last_name":"T","email":"q@t.com","answers":{"q1":"Yes"}})
    r = client.get("/quiz/export?format=csv", headers={"x-smartbiz-token": "dev"})
    assert r.status_code == 200
    data = r.json()
    assert "csv" in data
    assert "first_name,last_name,email" in data["csv"]

def test_create_booking():
    payload = {
        "first_name": "Client",
        "last_name": "One",
        "email": "client@example.com",
        "phone": "0710000000",
        "company": "Acme",
        "service": "site-inspection",
        "amount_cents": 5000,
        "currency": "ZAR",
    }
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

def test_technician_qr_and_complete():
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

    complete = client.post(f"/technician/complete/{booking_id}?token=tech-complete-1234", json={"visited": True, "completed": True}, headers={"x-smartbiz-token": "dev"})
    assert complete.status_code == 200
    assert complete.json()["status"] == "technician_completed"

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

def test_xero_not_configured():
    r = client.post("/api/v1/bookings", json={"first_name":"X","last_name":"R","email":"x@r.com","amount_cents":1000}, headers={"x-smartbiz-token": "dev"})
    booking_id = r.json()["booking_id"]

    for path in [
        f"/xero/bookings/{booking_id}/contact",
        f"/xero/bookings/{booking_id}/invoice",
        f"/xero/bookings/{booking_id}/creditnote",
    ]:
        resp = client.post(path, headers={"x-smartbiz-token": "dev"})
        assert resp.status_code == 400
        assert "not configured" in resp.json()["detail"]
