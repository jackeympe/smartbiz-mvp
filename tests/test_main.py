from fastapi.testclient import TestClient
from smartbiz.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_job():
    r = client.post("/jobs", json={"id": 1, "title": "Service A"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["job"] == {"id": 1, "title": "Service A"}

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

    r2 = client.get("/leads")
    assert r2.status_code == 200
    data = r2.json()["leads"]
    assert any(item["email"] == payload["email"] for item in data)

def test_create_lead_requires_fields():
    r = client.post("/api/v1/leads", json={"email": "x@y.com"})
    assert r.status_code == 400
