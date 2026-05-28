from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)


def auth_headers():
    res = client.post(
        "/api/v1/auth/login",
        json={"username": settings.DEFAULT_ADMIN_USERNAME, "password": settings.DEFAULT_ADMIN_PASSWORD},
    )
    return {"Authorization": f"Bearer {res.json()['token']}"}


def test_policies_evaluate():
    headers = auth_headers()
    res = client.post("/api/v1/policies/evaluate?days=30", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "compliance_score" in data
    assert len(data["policies"]) >= 5


def test_alerts_flow(monkeypatch):
    monkeypatch.setattr(settings, "USE_DEMO_DATA", True)
    headers = auth_headers()
    client.get("/api/v1/billing/summary", headers=headers)
    rules = client.get("/api/v1/alerts/rules", headers=headers)
    assert rules.status_code == 200
    assert len(rules.json()) >= 1
    ev = client.post("/api/v1/alerts/evaluate", headers=headers)
    assert ev.status_code == 200
    events = client.get("/api/v1/alerts/events", headers=headers)
    assert events.status_code == 200


def test_gpu_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "USE_DEMO_DATA", True)
    headers = auth_headers()
    client.get("/api/v1/billing/summary", headers=headers)
    res = client.get("/api/v1/billing/gpu?days=30", headers=headers)
    assert res.status_code == 200
    assert "total_gpu_ai_cost" in res.json()


def test_remediation_dry_run(monkeypatch):
    monkeypatch.setattr(settings, "USE_DEMO_DATA", True)
    headers = auth_headers()
    client.get("/api/v1/billing/summary", headers=headers)
    recs = client.get("/api/v1/optimization/recommendations", headers=headers)
    assert recs.status_code == 200
    items = recs.json()
    if not items:
        return
    rec_id = items[0]["id"]
    dry = client.post(f"/api/v1/optimization/recommendations/{rec_id}/dry-run", headers=headers)
    assert dry.status_code == 200
    assert dry.json()["dry_run"] is True


def test_platform_features_flag():
    headers = auth_headers()
    res = client.get("/api/v1/platform/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["features"]["policies"] is True
