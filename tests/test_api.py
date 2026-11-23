import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_analyze_missing_dependency_auto_pr(client):
    r = client.post("/analyze", json={"run_id": "run-missing-dep"})
    body = r.json()
    assert r.status_code == 200
    assert body["diagnosis"]["category"] == "missing_dependency"
    assert body["status"] == "resolved_auto"


def test_rollback_requires_then_gets_approval(client):
    inc = client.post("/analyze", json={"run_id": "run-deploy-crash", "environment": "production"}).json()
    assert inc["status"] == "awaiting_approval"
    done = client.post(f"/incidents/{inc['id']}/approve").json()
    assert done["status"] == "executed" and done["action_result"]["simulated"] is True
    assert client.post(f"/incidents/{inc['id']}/approve").status_code == 409


def test_reject(client):
    inc = client.post("/analyze", json={"run_id": "run-deploy-crash"}).json()
    assert client.post(f"/incidents/{inc['id']}/reject").json()["status"] == "rejected"


def test_validation_errors_have_stable_format(client):
    for payload in ({}, {"log_text": "   "}):
        r = client.post("/analyze", json=payload)
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_unknown_run_is_404(client):
    r = client.post("/analyze", json={"run_id": "nope"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "run_not_found"


def test_path_traversal_blocked(client):
    assert client.post("/analyze", json={"run_id": "../../.env"}).status_code == 404


def test_unknown_incident(client):
    assert client.get("/incidents/zzz").json()["error"]["code"] == "incident_not_found"


def test_audit_trail_is_written(client):
    client.post("/analyze", json={"run_id": "run-deploy-crash"})
    events = [e["event"] for e in client.get("/audit").json()]
    assert "diagnosed" in events and "approval_requested" in events


def test_secret_never_returned_in_evidence(client):
    body = client.post("/analyze", json={"run_id": "run-expired-token"}).json()
    assert "abcdefghijklmnopqrstuvwxyz123456" not in str(body)
