"""Unit tests for diagram service."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from diagrams import Cluster, Diagram, Edge, Node

from aws_project_planning.core.diagram.service import DiagramService


@pytest.fixture
def mock_diagram():
    """Mock Diagram class."""
    with patch("aws_project_planning.core.diagram.service.Diagram") as mock:
        # Configure the mock to return a MagicMock when instantiated
        mock_instance = MagicMock()
        mock.return_value.__enter__.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_cluster():
    """Mock Cluster class."""
    with patch("aws_project_planning.core.diagram.service.Cluster") as mock:
        # Configure the mock to return a MagicMock when instantiated
        mock_instance = MagicMock()
        mock.return_value.__enter__.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_node_classes():
    """Mock all AWS resource node classes."""
    with patch("aws_project_planning.core.diagram.service.EC2") as mock_ec2, \
         patch("aws_project_planning.core.diagram.service.RDS") as mock_rds, \
         patch("aws_project_planning.core.diagram.service.S3") as mock_s3, \
         patch("aws_project_planning.core.diagram.service.ELB") as mock_elb, \
         patch("aws_project_planning.core.diagram.service.VPC") as mock_vpc, \
         patch("aws_project_planning.core.diagram.service.ECS") as mock_ecs, \
         patch("aws_project_planning.core.diagram.service.WAF") as mock_waf, \
         patch("aws_project_planning.core.diagram.service.SQS") as mock_sqs, \
         patch("aws_project_planning.core.diagram.service.Cloudwatch") as mock_cloudwatch:
        # Set up return values for node classes
        mock_ec2.return_value = MagicMock(spec=Node)
        mock_rds.return_value = MagicMock(spec=Node)
        mock_s3.return_value = MagicMock(spec=Node)
        mock_elb.return_value = MagicMock(spec=Node)
        mock_vpc.return_value = MagicMock(spec=Node)
        mock_ecs.return_value = MagicMock(spec=Node)
        mock_waf.return_value = MagicMock(spec=Node)
        mock_sqs.return_value = MagicMock(spec=Node)
        mock_cloudwatch.return_value = MagicMock(spec=Node)
        
        yield {
            "ec2": mock_ec2,
            "rds": mock_rds,
            "s3": mock_s3,
            "elb": mock_elb,
            "vpc": mock_vpc,
            "ecs": mock_ecs,
            "waf": mock_waf,
            "sqs": mock_sqs,
            "cloudwatch": mock_cloudwatch,
        }


@pytest.fixture
def diagram_service():
    """Create a diagram service instance."""
    return DiagramService(default_region="us-east-1")


@pytest.fixture
def sample_config():
    """Create a sample diagram configuration."""
    return {
        "name": "Test Diagram",
        "direction": "LR",
        "nodes": [
            {
                "name": "standalone_node",
                "service": "ec2",
            }
        ],
        "clusters": [
            {
                "name": "Test Cluster",
                "nodes": [
                    {
                        "name": "cluster_node_1",
                        "service": "ec2",
                    },
                    {
                        "name": "cluster_node_2",
                        "service": "rds",
                    }
                ]
            }
        ],
        "connections": [
            {
                "from": "standalone_node",
                "to": "cluster_node_1",
                "label": "Test Connection",
            }
        ]
    }


@pytest.fixture
def sample_config_file(tmp_path, sample_config):
    """Create a sample diagram configuration file."""
    config_path = tmp_path / "test_diagram.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config, f)
    return str(config_path)


def test_init_default_region():
    """Test initializing with default region."""
    service = DiagramService()
    assert service.default_region == "us-east-1"


def test_init_custom_region():
    """Test initializing with custom region."""
    service = DiagramService(default_region="us-west-2")
    assert service.default_region == "us-west-2"


def test_load_config(diagram_service, sample_config_file, sample_config):
    """Test loading configuration from file."""
    config = diagram_service.load_config(sample_config_file)
    assert config == sample_config


def test_create_node_success(diagram_service, mock_node_classes):
    """Test creating a diagram node successfully."""
    for service_name in diagram_service._resource_icons.keys():
        node_config = {"service": service_name, "name": f"test_{service_name}"}
        node = diagram_service._create_node(None, node_config)
        assert node is not None
        assert mock_node_classes[service_name].called


def test_create_node_unknown_service(diagram_service):
    """Test creating a node with unknown service."""
    node_config = {"service": "unknown_service", "name": "test_node"}
    
    with pytest.raises(ValueError) as excinfo:
        diagram_service._create_node(None, node_config)
    
    assert "Unsupported AWS service: unknown_service" in str(excinfo.value)


def test_create_node_with_default_name(diagram_service, mock_node_classes):
    """Test creating a node without specifying a name."""
    node_config = {"service": "ec2"}
    node = diagram_service._create_node(None, node_config)
    
    assert node is not None
    mock_node_classes["ec2"].assert_called_with("EC2")


def test_create_cluster(diagram_service, mock_cluster, mock_node_classes):
    """Test creating a cluster with nodes."""
    cluster_config = {
        "name": "Test Cluster",
        "nodes": [
            {
                "name": "node1",
                "service": "ec2",
            },
            {
                "name": "node2",
                "service": "rds",
            }
        ]
    }
    
    nodes = diagram_service._create_cluster(None, cluster_config)
    
    # Verify cluster was created
    mock_cluster.assert_called_with("Test Cluster")
    
    # Verify nodes were created and returned
    assert "node1" in nodes
    assert "node2" in nodes
    assert mock_node_classes["ec2"].called
    assert mock_node_classes["rds"].called


def test_create_empty_cluster(diagram_service, mock_cluster):
    """Test creating a cluster with no nodes."""
    cluster_config = {
        "name": "Empty Cluster",
        "nodes": []
    }
    
    nodes = diagram_service._create_cluster(None, cluster_config)
    
    # Verify cluster was created
    mock_cluster.assert_called_with("Empty Cluster")
    
    # Verify empty dict returned
    assert nodes == {}


def test_create_connections(diagram_service):
    """Test creating connections between nodes."""
    node1 = MagicMock()
    node2 = MagicMock()
    nodes = {
        "node1": node1,
        "node2": node2,
    }
    
    connections = [
        {
            "from": "node1",
            "to": "node2",
            "label": "Test Connection",
        }
    ]
    
    diagram_service._create_connections(nodes, connections)
    
    # Verify that the edge was created
    assert node1.__gt__.called
    node1.__gt__.assert_called_with(node2)


def test_create_connections_with_missing_node(diagram_service):
    """Test creating connections with missing node."""
    node1 = MagicMock()
    nodes = {
        "node1": node1,
    }
    
    connections = [
        {
            "from": "node1",
            "to": "nonexistent_node",
            "label": "Test Connection",
        }
    ]
    
    # Should not raise exception, but log a warning
    diagram_service._create_connections(nodes, connections)
    
    # Verify no edge was created
    assert not node1.__gt__.called


def test_create_diagram_from_dict(diagram_service, mock_diagram, mock_cluster, mock_node_classes, sample_config, tmp_path):
    """Test creating a diagram from a configuration dictionary."""
    output_path = str(tmp_path / "test_output")
    
    # Create the diagram
    result = diagram_service.create_diagram(sample_config, output_path)
    
    # Verify diagram was created with correct parameters
    mock_diagram.assert_called_with(
        name="Test Diagram",
        filename=Path(output_path).stem,
        outformat="png",
        direction="LR",
        show=False,
    )
    
    # Verify result path
    assert result == f"{output_path}.png"


def test_create_diagram_from_file(diagram_service, mock_diagram, sample_config_file, tmp_path):
    """Test creating a diagram from a configuration file."""
    output_path = str(tmp_path / "test_output")
    
    # Create the diagram
    with patch.object(diagram_service, "load_config", return_value={
        "name": "Test Diagram",
        "direction": "LR",
        "nodes": [],
        "clusters": [],
        "connections": [],
    }) as mock_load:
        result = diagram_service.create_diagram(sample_config_file, output_path)
        
        # Verify config was loaded
        mock_load.assert_called_with(sample_config_file)
    
    # Verify diagram was created
    mock_diagram.assert_called()
    
    # Verify result path
    assert result == f"{output_path}.png"


def test_create_diagram_creates_output_dir(diagram_service, mock_diagram, sample_config, tmp_path):
    """Test that output directory is created if it doesn't exist."""
    output_dir = tmp_path / "nonexistent" / "directory"
    output_path = str(output_dir / "test_output")
    
    with patch("os.makedirs") as mock_makedirs:
        diagram_service.create_diagram(sample_config, output_path)
        
        # Verify directory was created
        mock_makedirs.assert_called_with(str(output_dir), exist_ok=True)


def test_generate_from_resources(diagram_service, tmp_path):
    """Test generating a diagram from resources configuration."""
    resources_config = {
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
    
    output_path = str(tmp_path / "test_from_resources")
    
    # Mock the create_diagram method to avoid creating an actual diagram
    with patch.object(diagram_service, "create_diagram", return_value=f"{output_path}.png") as mock_create:
        result = diagram_service.generate_from_resources(resources_config, output_path)
        
        # Verify create_diagram was called with the correct parameters
        mock_create.assert_called_once()
        config = mock_create.call_args[0][0]
        
        # Verify the generated configuration structure
        assert config["name"] == "AWS Architecture Diagram"
        assert config["direction"] == "TB"
        assert "clusters" in config
        assert len(config["clusters"]) == 2  # web and database tiers
        assert "connections" in config
        
        # Verify result path
        assert result == f"{output_path}.png"


def test_generate_from_resources_file(diagram_service, tmp_path):
    """Test generating a diagram from resources configuration file."""
    resources_config = {
        "resources": [
            {
                "service": "ec2",
                "type": "web_server",
                "specs": {"instance_type": "t3.medium"},
                "region": "us-east-1",
                "quantity": 2,
            }
        ]
    }
    
    # Create resources config file
    resources_path = tmp_path / "resources.yaml"
    with open(resources_path, "w") as f:
        yaml.dump(resources_config, f)
    
    output_path = str(tmp_path / "test_from_resources_file")
    
    # Mock the create_diagram method to avoid creating an actual diagram
    with patch.object(diagram_service, "create_diagram", return_value=f"{output_path}.png") as mock_create:
        result = diagram_service.generate_from_resources(str(resources_path), output_path)
        
        # Verify create_diagram was called
        mock_create.assert_called_once()
        
        # Verify result path
        assert result == f"{output_path}.png" 