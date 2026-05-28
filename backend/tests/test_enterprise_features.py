from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def auth_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "finops2026"},
    )
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_platform_enterprise_flags():
    headers = auth_headers()
    res = client.get("/api/v1/platform/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "oidc_enabled" in data
    assert "github_automation" in data
    assert "sync_scheduler" in data


def test_rag_reindex():
    headers = auth_headers()
    res = client.post("/api/v1/copilot/rag/reindex", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_github_automation_not_configured():
    headers = auth_headers()
    res = client.get("/api/v1/automation/github/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["configured"] is False


def test_schedules_list():
    headers = auth_headers()
    res = client.get("/api/v1/schedules", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
