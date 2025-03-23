"""Unit tests for AWS Web Calculator."""

import base64
import json
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

from aws_project_planning.core.pricing.calculator import ResourceConfig
from aws_project_planning.core.pricing.web_calculator import AWSWebCalculator


@pytest.fixture
def web_calculator():
    """Create an AWS Web Calculator instance."""
    return AWSWebCalculator()


@pytest.fixture
def sample_ec2_resource():
    """Create a sample EC2 resource configuration."""
    return ResourceConfig(
        service="ec2",
        resource_type="web_server",
        specs={"instance_type": "t3.medium"},
        region="us-east-1",
        quantity=2,
        usage_hours=730.0,
    )


@pytest.fixture
def sample_rds_resource():
    """Create a sample RDS resource configuration."""
    return ResourceConfig(
        service="rds",
        resource_type="database",
        specs={
            "instance_type": "db.t3.medium",
            "engine": "mysql",
            "storage_gb": 100,
        },
        region="us-east-1",
        quantity=1,
        usage_hours=730.0,
    )


@pytest.fixture
def sample_s3_resource():
    """Create a sample S3 resource configuration."""
    return ResourceConfig(
        service="s3",
        resource_type="data_storage",
        specs={
            "storage_class": "Standard",
            "storage_gb": 500,
        },
        region="us-east-1",
    )


def test_init(web_calculator):
    """Test initializing the calculator."""
    assert web_calculator is not None


def test_ec2_conversion(web_calculator, sample_ec2_resource):
    """Test converting EC2 resource to AWS Calculator format."""
    result = web_calculator._convert_ec2_to_calculator_format(sample_ec2_resource)
    
    assert result["service"] == "AmazonEC2"
    assert "web_server" in result["name"]
    assert result["quantity"] == 2
    
    # Check cost components
    components = result["costComponents"]
    assert len(components) == 1
    assert components[0]["name"] == "EC2 Instance"
    assert components[0]["monthlyQuantity"] == 730.0
    assert components[0]["family"] == "t3"
    assert components[0]["type"] == "t3.medium"
    assert components[0]["region"] == "us-east-1"


def test_rds_conversion(web_calculator, sample_rds_resource):
    """Test converting RDS resource to AWS Calculator format."""
    result = web_calculator._convert_rds_to_calculator_format(sample_rds_resource)
    
    assert result["service"] == "AmazonRDS"
    assert "database" in result["name"]
    assert "mysql" in result["name"].lower() or "MySQL" in result["name"]
    assert result["quantity"] == 1
    
    # Check cost components
    components = result["costComponents"]
    assert len(components) == 2  # Instance and storage
    
    # Instance component
    instance_component = [c for c in components if c["name"] == "Database Instance"][0]
    assert instance_component["family"] == "db.t3"
    assert instance_component["type"] == "db.t3.medium"
    assert instance_component["databaseEngine"] == "MySQL"
    
    # Storage component
    storage_component = [c for c in components if c["name"] == "Storage"][0]
    assert storage_component["monthlyQuantity"] == 100
    assert "General Purpose" in storage_component["volumeType"]


def test_s3_conversion(web_calculator, sample_s3_resource):
    """Test converting S3 resource to AWS Calculator format."""
    result = web_calculator._convert_s3_to_calculator_format(sample_s3_resource)
    
    assert result["service"] == "AmazonS3"
    assert "data_storage" in result["name"]
    assert "Standard" in result["name"]
    
    # Check cost components
    components = result["costComponents"]
    assert len(components) == 1
    assert components[0]["name"] == "Storage"
    assert components[0]["monthlyQuantity"] == 500
    assert components[0]["region"] == "us-east-1"
    assert "General Purpose" in components[0]["storageClass"]


def test_encode_calculator_data(web_calculator):
    """Test encoding calculator data for URL."""
    test_data = {"test": "value"}
    encoded = web_calculator._encode_calculator_data(test_data)
    
    # Decode and verify
    decoded_json = json.loads(base64.b64decode(urllib.parse.unquote(encoded)).decode())
    assert decoded_json == test_data


def test_convert_resource_to_calculator_format(web_calculator, sample_ec2_resource, sample_rds_resource, sample_s3_resource):
    """Test converting various resources to calculator format."""
    # EC2
    ec2_result = web_calculator.convert_resource_to_calculator_format(sample_ec2_resource)
    assert ec2_result["service"] == "AmazonEC2"
    
    # RDS
    rds_result = web_calculator.convert_resource_to_calculator_format(sample_rds_resource)
    assert rds_result["service"] == "AmazonRDS"
    
    # S3
    s3_result = web_calculator.convert_resource_to_calculator_format(sample_s3_resource)
    assert s3_result["service"] == "AmazonS3"
    
    # Unsupported service
    unsupported = ResourceConfig(
        service="unsupported",
        resource_type="test",
        specs={},
        region="us-east-1",
    )
    result = web_calculator.convert_resource_to_calculator_format(unsupported)
    assert result is None


def test_convert_resources_to_calculator_format(web_calculator, sample_ec2_resource, sample_s3_resource):
    """Test converting a list of resources to calculator format."""
    resources = [sample_ec2_resource, sample_s3_resource]
    
    result = web_calculator.convert_resources_to_calculator_format(resources)
    
    assert "estimate" in result
    assert "resources" in result["estimate"]
    assert len(result["estimate"]["resources"]) == 2
    assert result["estimate"]["currency"] == "USD"
    assert result["estimate"]["timeframe"] == "MONTHLY"


def test_generate_calculator_url(web_calculator, sample_ec2_resource, sample_rds_resource):
    """Test generating a calculator URL."""
    resources = [sample_ec2_resource, sample_rds_resource]
    
    url = web_calculator.generate_calculator_url(resources)
    
    # Check URL format
    assert url.startswith("https://calculator.aws/#/estimate?data=")
    
    # Decode the URL data and verify basic structure
    encoded_data = url.split("?data=")[1]
    decoded_json = json.loads(base64.b64decode(urllib.parse.unquote(encoded_data)).decode())
    
    assert "estimate" in decoded_json
    assert "resources" in decoded_json["estimate"]
    assert len(decoded_json["estimate"]["resources"]) == 2 