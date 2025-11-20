"""
Tests for health endpoints
"""

import pytest
from fastapi.testclient import TestClient

from src.core.server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_endpoint(client):
    """Test basic health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_detailed_health_endpoint(client):
    """Test detailed health check endpoint"""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "system" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "name" in data


def test_readiness_endpoint(client):
    """Test readiness probe"""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


def test_liveness_endpoint(client):
    """Test liveness probe"""
    response = client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True
