"""Unit tests for diagram service."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from aws_project_planning.core.diagram.service import DiagramService


@pytest.fixture
def diagram_service():
    """Create a diagram service instance."""
    with patch("diagrams.Diagram") as mock_diagram:
        # Mock the diagram context manager
        mock_diagram.return_value.__enter__.return_value = MagicMock()
        yield DiagramService()


@pytest.fixture
def sample_config(tmp_path):
    """Create a sample diagram configuration file."""
    config = {
        "name": "Test Diagram",
        "direction": "TB",
        "clusters": [
            {
                "name": "Web Tier",
                "nodes": [
                    {"name": "web_server_1", "service": "ec2"},
                    {"name": "web_server_2", "service": "ec2"},
                ],
            },
            {
                "name": "Database Tier",
                "nodes": [
                    {"name": "database", "service": "rds"},
                ],
            },
        ],
        "connections": [
            {"from": "web_server_1", "to": "database", "label": "SQL"},
            {"from": "web_server_2", "to": "database", "label": "SQL"},
        ],
    }
    
    config_path = tmp_path / "test_diagram.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    
    return str(config_path)


@pytest.fixture
def sample_resources_config(tmp_path):
    """Create a sample resources configuration file."""
    config = {
        "resources": [
            {
                "service": "ec2",
                "type": "web_server",
                "specs": {"instance_type": "t3.medium"},
                "region": "us-east-1",
                "quantity": 2,
            },
            {
                "service": "rds",
                "type": "database",
                "specs": {
                    "instance_type": "db.t3.medium",
                    "engine": "mysql",
                    "storage_gb": 100,
                },
                "region": "us-east-1",
            },
        ]
    }
    
    config_path = tmp_path / "test_resources.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    
    return str(config_path)


def test_load_config(diagram_service, sample_config):
    """Test loading configuration from file."""
    config = diagram_service.load_config(sample_config)
    
    assert config["name"] == "Test Diagram"
    assert config["direction"] == "TB"
    assert len(config["clusters"]) == 2
    assert len(config["connections"]) == 2


@patch("diagrams.Cluster")
@patch("diagrams.aws.compute.EC2")
@patch("diagrams.aws.database.RDS")
def test_create_diagram(mock_rds, mock_ec2, mock_cluster, diagram_service, sample_config, tmp_path):
    """Test creating a diagram from configuration."""
    output_path = str(tmp_path / "test_output")
    
    # Setup mocks
    mock_ec2.return_value = MagicMock()
    mock_rds.return_value = MagicMock()
    mock_cluster.return_value.__enter__.return_value = MagicMock()
    
    result = diagram_service.create_diagram(sample_config, output_path)
    
    assert result == f"{output_path}.png"
    

@patch("diagrams.Cluster")
@patch("diagrams.aws.compute.EC2")
@patch("diagrams.aws.database.RDS")
def test_generate_from_resources(mock_rds, mock_ec2, mock_cluster, diagram_service, sample_resources_config, tmp_path):
    """Test generating a diagram from resources configuration."""
    output_path = str(tmp_path / "test_output")
    
    # Setup mocks
    mock_ec2.return_value = MagicMock()
    mock_rds.return_value = MagicMock()
    mock_cluster.return_value.__enter__.return_value = MagicMock()
    
    result = diagram_service.generate_from_resources(sample_resources_config, output_path)
    
    assert result == f"{output_path}.png"


def test_create_node_unsupported_service(diagram_service):
    """Test creating a node with an unsupported service."""
    with pytest.raises(ValueError, match="Unsupported AWS service"):
        diagram_service._create_node(None, {"service": "unsupported_service"}) 