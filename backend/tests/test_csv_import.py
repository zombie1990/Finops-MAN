from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def auth_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "finops2026"},
    )
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_csv_preview_and_import():
    headers = auth_headers()
    csv_content = (
        "date,provider,service,cost,account_id\n"
        "2026-05-01,AWS,Amazon EC2,120.5,aws-test\n"
        "2026-05-02,Azure,Virtual Machines,80.0,azure-test\n"
    ).encode("utf-8")

    preview = client.post(
        "/api/v1/data/import/preview",
        headers=headers,
        files={"file": ("costs.csv", csv_content, "text/csv")},
    )
    assert preview.status_code == 200
    assert preview.json()["validation_ok"] is True

    imported = client.post(
        "/api/v1/data/import",
        headers=headers,
        files={"file": ("costs.csv", csv_content, "text/csv")},
    )
    assert imported.status_code == 200
    assert imported.json()["items_imported"] == 2


def test_platform_status_production_mode():
    headers = auth_headers()
    status = client.get("/api/v1/platform/status", headers=headers)
    assert status.status_code == 200
    payload = status.json()
    assert payload["demo_mode"] is False
    assert payload["data_mode"] == "production"
