"""Integration tests for API endpoints using the test client."""

import pytest


def test_health_endpoint_ok(test_client):
    resp = test_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "database_connected" in data


def test_root_endpoint(test_client):
    resp = test_client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "docs" in data


def test_docs_available(test_client):
    resp = test_client.get("/api/docs")
    assert resp.status_code == 200


def test_openapi_schema_available(test_client):
    resp = test_client.get("/api/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    assert "info" in schema
