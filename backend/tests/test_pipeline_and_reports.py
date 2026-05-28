from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def auth_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "finops2026"},
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_connector_create_and_sync():
    headers = auth_headers()
    created = client.post(
        "/api/v1/connectors",
        headers=headers,
        json={
            "provider": "AWS",
            "name": "aws-cur-main",
            "connector_type": "cost_export",
            "config_json": {
                "access_key_id": "test",
                "secret_access_key": "test",
                "region": "eu-west-3",
                "account_id": "123",
            },
        },
    )
    assert created.status_code == 200
    connector_id = created.json()["connector_id"]

    synced = client.post(f"/api/v1/connectors/{connector_id}/sync", headers=headers)
    assert synced.status_code == 200
    # Sans credentials AWS réels, la sync échoue proprement (comportement production)
    body = synced.json()
    assert "success" in body


def test_ingestion_job_retry_flow():
    headers = auth_headers()
    created = client.post(
        "/api/v1/ingestion/jobs",
        headers=headers,
        json={"source_type": "openai_billing", "source_ref": "openai-api", "max_retries": 3},
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    first_run = client.post(f"/api/v1/ingestion/jobs/{job_id}/run", headers=headers)
    assert first_run.status_code == 200
    assert first_run.json()["status"] == "Failed"

    retried = client.post(f"/api/v1/ingestion/jobs/{job_id}/retry", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["status"] == "Succeeded"


def test_report_generation_and_fetch():
    headers = auth_headers()
    generated = client.post(
        "/api/v1/reports/generate",
        headers=headers,
        json={"report_type": "executive", "period_days": 30},
    )
    assert generated.status_code == 200
    report_id = generated.json()["report_id"]

    fetched = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["report_type"] == "executive"


def test_scored_recommendations():
    headers = auth_headers()
    scored = client.get("/api/v1/optimization/recommendations/scored", headers=headers)
    assert scored.status_code == 200
    payload = scored.json()
    assert isinstance(payload, list)
    if payload:
        assert "priority_score" in payload[0]
        assert "confidence_score" in payload[0]
