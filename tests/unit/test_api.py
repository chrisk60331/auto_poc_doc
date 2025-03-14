"""Unit tests for API functionality."""

from fastapi.testclient import TestClient

from aws_project_planning.api.main import app

client = TestClient(app)


def test_read_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()


def test_create_sow():
    """Test SOW creation endpoint."""
    response = client.post(
        "/sow/create",
        json={
            "template_name": "standard",
            "project_name": "Test Project",
            "description": "Test Description",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Creating SOW" in response.json()["message"]


def test_create_diagram():
    """Test diagram creation endpoint."""
    response = client.post(
        "/diagram/create",
        json={
            "config": {
                "type": "web",
                "components": ["vpc", "ec2", "rds"],
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Creating AWS architecture diagram" in response.json()["message"]


def test_estimate_pricing():
    """Test pricing estimate endpoint."""
    response = client.post(
        "/pricing/estimate",
        json={
            "resources": {
                "ec2": {"type": "t3.micro", "count": 2},
                "rds": {"type": "db.t3.micro", "storage": 20},
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Calculating AWS price estimate" in response.json()["message"] 