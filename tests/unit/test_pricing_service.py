"""Unit tests for pricing service."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from aws_project_planning.core.pricing.calculator import ResourceConfig
from aws_project_planning.core.pricing.service import PricingService
from aws_project_planning.core.pricing.web_calculator import AWSWebCalculator


@pytest.fixture
def mock_pricing_client():
    """Create a mock AWS pricing client."""
    with patch("boto3.client") as mock_client:
        # Mock EC2 pricing
        mock_client.return_value.get_products.return_value = {
            "PriceList": [
                {
                    "terms": {
                        "OnDemand": {
                            "test": {
                                "priceDimensions": {
                                    "test": {"pricePerUnit": {"USD": "0.0416"}}
                                }
                            }
                        }
                    }
                }
            ]
        }
        yield mock_client


@pytest.fixture
def mock_web_calculator():
    """Create a mock AWS Web Calculator."""
    with patch("aws_project_planning.core.pricing.web_calculator.AWSWebCalculator") as mock:
        mock_instance = mock.return_value
        mock_instance.generate_calculator_url.return_value = "https://calculator.aws/#/estimate?data=mock-data"
        yield mock_instance


@pytest.fixture
def pricing_service(mock_pricing_client, mock_web_calculator):
    """Create a pricing service instance with mocked components."""
    with patch("aws_project_planning.core.pricing.service.AWSWebCalculator", return_value=mock_web_calculator):
        service = PricingService()
        service.web_calculator = mock_web_calculator
        return service


@pytest.fixture
def sample_config(tmp_path):
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


def test_load_resources_from_config(pricing_service, sample_config):
    """Test loading resources from configuration file."""
    resources = pricing_service.load_resources_from_config(sample_config)
    
    assert len(resources) == 2
    assert isinstance(resources[0], ResourceConfig)
    assert resources[0].service == "ec2"
    assert resources[0].quantity == 2
    assert resources[1].service == "rds"
    assert resources[1].specs["storage_gb"] == 100


def test_calculate_costs(pricing_service):
    """Test cost calculation for resources."""
    resources = [
        ResourceConfig(
            service="ec2",
            resource_type="web_server",
            specs={"instance_type": "t3.medium"},
            region="us-east-1",
            quantity=2,
        )
    ]
    
    result = pricing_service.calculate_costs(resources)
    
    assert "total_monthly_cost" in result
    assert "resources" in result
    assert len(result["resources"]) == 1
    assert result["resources"][0]["type"] == "EC2 t3.medium"


def test_estimate_from_config(pricing_service, sample_config):
    """Test cost estimation from configuration file."""
    result = pricing_service.estimate_from_config(sample_config)
    
    assert "total_monthly_cost" in result
    assert "resources" in result
    assert len(result["resources"]) == 2


def test_format_cost_report(pricing_service):
    """Test cost report formatting."""
    costs = {
        "total_monthly_cost": 1000.50,
        "resources": [
            {
                "type": "EC2 t3.medium",
                "monthly_cost": 500.25,
                "details": {
                    "instance_type": "t3.medium",
                    "region": "us-east-1",
                    "hourly_rate": 0.0416,
                },
            }
        ],
    }
    
    report = pricing_service.format_cost_report(costs)
    
    assert isinstance(report, str)
    assert "AWS Cost Estimate" in report
    assert "Total Monthly Cost: $1,000.50" in report
    assert "EC2 t3.medium" in report


def test_generate_calculator_url(pricing_service, mock_web_calculator):
    """Test generating AWS Calculator URL."""
    resources = [
        ResourceConfig(
            service="ec2",
            resource_type="web_server",
            specs={"instance_type": "t3.medium"},
            region="us-east-1",
            quantity=2,
        )
    ]
    
    url = pricing_service.generate_calculator_url(resources)
    
    assert url == "https://calculator.aws/#/estimate?data=mock-data"
    mock_web_calculator.generate_calculator_url.assert_called_once_with(resources)


def test_generate_calculator_url_from_config(pricing_service, sample_config, mock_web_calculator):
    """Test generating AWS Calculator URL from configuration file."""
    url = pricing_service.generate_calculator_url_from_config(sample_config)
    
    assert url == "https://calculator.aws/#/estimate?data=mock-data"
    mock_web_calculator.generate_calculator_url.assert_called_once()


def test_generate_cost_report_with_url(pricing_service, mock_web_calculator):
    """Test generating cost report with URL."""
    resources = [
        ResourceConfig(
            service="ec2",
            resource_type="web_server",
            specs={"instance_type": "t3.medium"},
            region="us-east-1",
            quantity=2,
        )
    ]
    
    result = pricing_service.generate_cost_report(resources, include_url=True)
    
    assert "costs" in result
    assert "report" in result
    assert "calculator_url" in result
    assert result["calculator_url"] == "https://calculator.aws/#/estimate?data=mock-data"
    mock_web_calculator.generate_calculator_url.assert_called_once_with(resources)


def test_generate_cost_report_without_url(pricing_service, mock_web_calculator):
    """Test generating cost report without URL."""
    resources = [
        ResourceConfig(
            service="ec2",
            resource_type="web_server",
            specs={"instance_type": "t3.medium"},
            region="us-east-1",
            quantity=2,
        )
    ]
    
    result = pricing_service.generate_cost_report(resources, include_url=False)
    
    assert "costs" in result
    assert "report" in result
    assert "calculator_url" not in result
    mock_web_calculator.generate_calculator_url.assert_not_called()


def test_generate_cost_report_from_config(pricing_service, sample_config, mock_web_calculator):
    """Test generating cost report from configuration file."""
    result = pricing_service.generate_cost_report_from_config(sample_config, include_url=True)
    
    assert "costs" in result
    assert "report" in result
    assert "calculator_url" in result
    assert result["calculator_url"] == "https://calculator.aws/#/estimate?data=mock-data"
    mock_web_calculator.generate_calculator_url.assert_called_once() 