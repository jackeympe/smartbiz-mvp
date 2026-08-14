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
