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


def test_forecast_endpoint():
    headers = auth_headers()
    res = client.get("/api/v1/billing/forecast?days=30", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "month_end_projection" in data
    assert "historical" in data


def test_budgets_list_and_create():
    headers = auth_headers()
    listed = client.get("/api/v1/billing/budgets", headers=headers)
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)
    assert len(listed.json()) >= 1

    created = client.post(
        "/api/v1/billing/budgets",
        headers=headers,
        json={"name": "Budget QA Test", "amount": 10000, "provider_filter": "AWS"},
    )
    assert created.status_code == 200
    assert created.json()["budget"]["name"] == "Budget QA Test"


def test_allocation_by_team():
    headers = auth_headers()
    res = client.get("/api/v1/billing/allocation?group_by=team&days=30", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["group_by"] == "team"
    assert "allocations" in data


def test_showback_summary():
    headers = auth_headers()
    res = client.get("/api/v1/billing/showback?days=30", headers=headers)
    assert res.status_code == 200
    assert "showback" in res.json()


def test_finops_analyze_with_data(monkeypatch):
    monkeypatch.setattr(settings, "USE_DEMO_DATA", True)
    headers = auth_headers()
    client.get("/api/v1/billing/summary", headers=headers)
    res = client.post("/api/v1/billing/finops/analyze", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "anomalies_detected" in body
