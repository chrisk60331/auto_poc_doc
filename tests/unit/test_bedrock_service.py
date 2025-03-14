"""Unit tests for Bedrock service."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from aws_project_planning.core.bedrock.service import BedrockService


@pytest.fixture
def mock_bedrock_client():
    """Mock the Bedrock client."""
    with patch("boto3.client") as mock_client:
        # Mock the response for Claude model
        mock_response = MagicMock()
        mock_response_body = MagicMock()
        mock_response_body.read.return_value = json.dumps({
            "completion": """```yaml
resources:
  - service: ec2
    type: web_server
    specs:
      instance_type: t3.xlarge
    region: us-east-1
    quantity: 4
    usage_hours: 730
  - service: elb
    type: load_balancer
    specs: {}
    region: us-east-1
    quantity: 1
    usage_hours: 730
```"""
        })
        mock_response.__getitem__.return_value = mock_response_body
        mock_client.return_value.invoke_model.return_value = mock_response
        yield mock_client


@pytest.fixture
def bedrock_service(mock_bedrock_client):
    """Create a Bedrock service instance with mocked client."""
    return BedrockService(model_id="anthropic.claude-v2")


@pytest.fixture
def sample_notes():
    """Sample project notes for testing."""
    return """
Meeting Notes: E-Commerce Platform Migration to AWS
Date: 2023-10-15

Project Requirements:
1. Migrate e-commerce platform to AWS
2. Need to handle 10,000 concurrent users
3. Database has 500GB of data
4. High availability required
5. Need disaster recovery

Proposed Architecture:
- ELB for load balancing
- 4 EC2 instances (t3.xlarge)
- RDS for database
- S3 for static assets
"""


def test_invoke_bedrock(bedrock_service, mock_bedrock_client):
    """Test invoking the Bedrock model."""
    response = bedrock_service._invoke_bedrock("Test prompt")
    
    # Check that boto3 client was called with correct parameters
    mock_bedrock_client.assert_called_once_with("bedrock-runtime", region_name="us-east-1")
    mock_bedrock_client.return_value.invoke_model.assert_called_once()
    
    # Validate the prompt format for Claude
    call_args = mock_bedrock_client.return_value.invoke_model.call_args[1]
    request_body = json.loads(call_args["body"])
    assert "prompt" in request_body
    assert request_body["prompt"].startswith("\n\nHuman:")
    assert request_body["prompt"].endswith("\n\nAssistant:")
    
    # Check that we got the mocked response
    assert "```yaml" in response


def test_generate_resources_config(bedrock_service, sample_notes):
    """Test generating resources configuration from notes."""
    result = bedrock_service.generate_resources_config(sample_notes)
    
    # Check the generated configuration
    assert "resources" in result
    assert isinstance(result["resources"], list)
    assert len(result["resources"]) >= 1
    
    # Check that the first resource has the expected fields
    first_resource = result["resources"][0]
    assert "service" in first_resource
    assert "type" in first_resource
    assert "specs" in first_resource
    assert "region" in first_resource
    assert "quantity" in first_resource
    assert "usage_hours" in first_resource


def test_generate_diagram_config(bedrock_service, sample_notes, mock_bedrock_client):
    """Test generating diagram configuration from notes."""
    # Mock a different response for diagram config
    mock_response_body = MagicMock()
    mock_response_body.read.return_value = json.dumps({
        "completion": """```yaml
name: "E-Commerce Architecture"
direction: "TB"
clusters:
  - name: "Web Tier"
    nodes:
      - name: "web_server_1"
        service: "ec2"
      - name: "web_server_2"
        service: "ec2"
connections:
  - from: "web_server_1"
    to: "database"
    label: "SQL"
```"""
    })
    mock_response = MagicMock()
    mock_response.__getitem__.return_value = mock_response_body
    mock_bedrock_client.return_value.invoke_model.return_value = mock_response
    
    result = bedrock_service.generate_diagram_config(sample_notes)
    
    # Check the generated configuration
    assert "name" in result
    assert result["name"] == "E-Commerce Architecture"
    assert "direction" in result
    assert "clusters" in result
    assert isinstance(result["clusters"], list)
    assert len(result["clusters"]) >= 1
    
    # Check that the clusters have expected structure
    first_cluster = result["clusters"][0]
    assert "name" in first_cluster
    assert "nodes" in first_cluster
    assert isinstance(first_cluster["nodes"], list)
    
    # Check connections
    assert "connections" in result
    assert isinstance(result["connections"], list)
    assert len(result["connections"]) >= 1


def test_generate_configs_from_file(bedrock_service, tmp_path, mock_bedrock_client):
    """Test generating both configs from a file."""
    # Create a temporary notes file
    notes_file = tmp_path / "test_notes.txt"
    notes_file.write_text("Test project notes about AWS architecture")
    
    # Mock different responses for each call
    def mock_invoke_side_effect(*args, **kwargs):
        prompt = json.loads(kwargs["body"])["prompt"]
        mock_response = MagicMock()
        mock_response_body = MagicMock()
        
        if "resources configuration" in prompt:
            mock_response_body.read.return_value = json.dumps({
                "completion": """```yaml
resources:
  - service: ec2
    type: web_server
    specs:
      instance_type: t3.large
    region: us-east-1
    quantity: 2
    usage_hours: 730
```"""
            })
        else:  # diagram config
            mock_response_body.read.return_value = json.dumps({
                "completion": """```yaml
name: "Test Architecture"
direction: "TB"
clusters:
  - name: "Web Tier"
    nodes:
      - name: "web_1"
        service: "ec2"
```"""
            })
            
        mock_response.__getitem__.return_value = mock_response_body
        return mock_response
    
    mock_bedrock_client.return_value.invoke_model.side_effect = mock_invoke_side_effect
    
    # Set up output paths
    resources_output = tmp_path / "resources.yaml"
    diagram_output = tmp_path / "diagram.yaml"
    
    # Generate configs
    resources_config, diagram_config = bedrock_service.generate_configs_from_file(
        file_path=str(notes_file),
        resources_output=str(resources_output),
        diagram_output=str(diagram_output)
    )
    
    # Check that both configs were generated
    assert "resources" in resources_config
    assert "name" in diagram_config
    
    # Check that files were created
    assert resources_output.exists()
    assert diagram_output.exists()
    
    # Verify file contents
    with open(resources_output, "r") as f:
        saved_resources = yaml.safe_load(f)
        assert saved_resources == resources_config
        
    with open(diagram_output, "r") as f:
        saved_diagram = yaml.safe_load(f)
        assert saved_diagram == diagram_config 