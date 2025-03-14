"""Unit tests for SOW service."""

import os
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from aws_project_planning.core.sow.service import SOWService


@pytest.fixture
def temp_template_dir(tmp_path):
    """Create a temporary template directory."""
    template_dir = tmp_path / "templates" / "sow"
    template_dir.mkdir(parents=True)
    return template_dir


@pytest.fixture
def sow_service(temp_template_dir):
    """Create a SOW service instance with temporary template directory."""
    return SOWService(str(temp_template_dir))


@pytest.fixture
def sample_sow_data():
    """Create sample SOW data."""
    return {
        "project_name": "Test Project",
        "client_name": "Test Client",
        "project_description": "This is a test project",
        "scope": [
            "Requirement gathering",
            "System design",
            "Implementation",
            "Testing",
        ],
        "deliverables": [
            "System documentation",
            "Source code",
            "Test reports",
        ],
        "timeline": [
            {"phase": "Planning", "duration": "2 weeks"},
            {"phase": "Development", "duration": "8 weeks"},
            {"phase": "Testing", "duration": "4 weeks"},
        ],
        "cost": {
            "total": 50000.0,
            "schedule": {
                "Initial Payment": 15000.0,
                "Milestone 1": 20000.0,
                "Final Payment": 15000.0,
            },
        },
        "assumptions": [
            "Client will provide timely feedback",
            "All required resources will be available",
        ],
    }


def test_list_templates(sow_service):
    """Test listing available templates."""
    templates = sow_service.list_templates()
    assert "standard" in templates


def test_get_template_info(sow_service):
    """Test getting template information."""
    info = sow_service.get_template_info("standard")
    assert info["name"] == "standard"
    assert "description" in info
    assert "sections" in info


def test_create_sow(sow_service, sample_sow_data, tmp_path):
    """Test creating a SOW document."""
    output_path = tmp_path / "test_sow.docx"
    
    result = sow_service.create_sow(
        template_name="standard",
        output_path=str(output_path),
        **sample_sow_data
    )
    
    assert os.path.exists(result)
    assert result == str(output_path)


def test_create_sow_invalid_template(sow_service, sample_sow_data, tmp_path):
    """Test creating a SOW with invalid template."""
    output_path = tmp_path / "test_sow.docx"
    
    with pytest.raises(ValueError) as exc_info:
        sow_service.create_sow(
            template_name="nonexistent",
            output_path=str(output_path),
            **sample_sow_data
        )
    
    assert "Template nonexistent not found" in str(exc_info.value)


def test_create_template(sow_service):
    """Test creating a new template."""
    template_config = {
        "name": "custom",
        "description": "Custom template for testing",
        "sections": [
            {
                "name": "overview",
                "title": "Overview",
                "required": True,
            }
        ],
    }
    
    sow_service.create_template("custom", template_config)
    templates = sow_service.list_templates()
    assert "custom" in templates
    
    info = sow_service.get_template_info("custom")
    assert info["name"] == "custom"
    assert info["description"] == "Custom template for testing" 