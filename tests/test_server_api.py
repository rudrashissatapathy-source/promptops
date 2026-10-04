"""Comprehensive tests for FastAPI server and API endpoints."""

import pytest
from starlette.testclient import TestClient

from promptops.server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """Verify system health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "promptops"


def test_list_models(client):
    """Verify model catalog retrieval."""
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "mock-fast" in data["models"]
    assert "mock-heavy" in data["models"]


def test_list_prompts(client):
    """Verify prompt registry list endpoint."""
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    assert len(data["prompts"]) >= 2


def test_prompt_diff(client):
    """Verify prompt version diff endpoint."""
    response = client.get("/api/prompts/diff?prompt_id=event_brief_synthesizer&v1=v1.0.0&v2=v2.0.0")
    assert response.status_code == 200
    data = response.json()
    assert "system_prompt_diff" in data
    assert data["v1"] == "v1.0.0"
    assert data["v2"] == "v2.0.0"


def test_generate_and_cache(client):
    """Verify synchronous generation and exact-match cache hit on second run."""
    payload = {
        "event_brief": "Organize a full-day developer summit for 300 backend engineers.",
        "prompt_id": "event_brief_synthesizer",
        "prompt_version": "v2.0.0",
        "model_name": "mock-fast",
        "routing_policy": "speed_first",
        "use_cache": True,
    }

    # First call: cache miss
    res1 = client.post("/api/generate", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["is_valid"] is True
    assert data1["cache_hit"] is False
    assert "validated_artifact" in data1

    # Second call: cache hit
    res2 = client.post("/api/generate", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_valid"] is True
    assert data2["cache_hit"] is True


def test_telemetry_endpoints(client):
    """Verify telemetry runs and summary endpoints."""
    # Ensure at least one run is logged
    client.post("/api/generate", json={
        "event_brief": "Quick test brief for telemetry.",
        "prompt_version": "v2.0.0",
        "model_name": "mock-fast",
    })

    runs_res = client.get("/api/telemetry/runs?limit=10")
    assert runs_res.status_code == 200
    assert len(runs_res.json()["runs"]) >= 1

    summary_res = client.get("/api/telemetry/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_runs"] >= 1
    assert "schema_validity_percent" in summary


def test_benchmark_results_endpoint(client):
    """Verify benchmark matrix results retrieval."""
    res = client.get("/api/benchmark/results")
    assert res.status_code == 200
    data = res.json()
    assert "matrix_summary" in data
