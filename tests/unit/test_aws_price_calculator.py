"""Unit tests for AWS Price Calculator."""

from unittest.mock import MagicMock, patch

import pytest

from aws_project_planning.core.pricing.calculator import AWSPriceCalculator, PricingResult, ResourceConfig


@pytest.fixture
def mock_pricing_client():
    """Create a mock AWS pricing client."""
    with patch("boto3.client") as mock_client:
        # Mock successful response
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
def price_calculator(mock_pricing_client):
    """Create an AWS Price Calculator instance with mocked client."""
    return AWSPriceCalculator(region="us-east-1")


def test_init_with_custom_region():
    """Test initializing calculator with custom region."""
    calculator = AWSPriceCalculator(region="us-west-2")
    assert calculator.default_region == "us-west-2"


def test_extract_price_success(price_calculator):
    """Test successful price extraction from API response."""
    price_list = [
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
    
    result = price_calculator._extract_price(price_list)
    assert result == 0.0416


def test_extract_price_empty_list(price_calculator):
    """Test price extraction with empty price list."""
    result = price_calculator._extract_price([])
    assert result is None


def test_extract_price_invalid_format(price_calculator):
    """Test price extraction with invalid response format."""
    price_list = [{"invalid": "format"}]
    result = price_calculator._extract_price(price_list)
    assert result is None


def test_get_ec2_price_success(price_calculator, mock_pricing_client):
    """Test successful EC2 price retrieval."""
    price = price_calculator._get_ec2_price("t3.medium", "us-east-1")
    assert price == 0.0416
    
    # Verify correct API call
    mock_pricing_client.return_value.get_products.assert_called_with(
        ServiceCode="AmazonEC2",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "t3.medium"},
            {"Type": "TERM_MATCH", "Field": "regionCode", "Value": "us-east-1"},
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ],
    )


def test_get_ec2_price_api_error(price_calculator):
    """Test EC2 price retrieval with API error."""
    with patch.object(price_calculator.pricing_client, "get_products", side_effect=Exception("API Error")):
        price = price_calculator._get_ec2_price("t3.medium", "us-east-1")
        
        # Should fall back to hardcoded price
        assert price == price_calculator.FALLBACK_PRICES["ec2"]["t3.medium"]


def test_get_ec2_price_no_results(price_calculator):
    """Test EC2 price retrieval with no results from API."""
    with patch.object(price_calculator.pricing_client, "get_products", return_value={"PriceList": []}):
        price = price_calculator._get_ec2_price("t3.medium", "us-east-1")
        
        # Should fall back to hardcoded price
        assert price == price_calculator.FALLBACK_PRICES["ec2"]["t3.medium"]


def test_get_ec2_price_unknown_instance(price_calculator):
    """Test EC2 price retrieval for unknown instance type."""
    price = price_calculator._get_ec2_price("unknown.instance", "us-east-1")
    
    # Should return a default price
    assert price == 0.05


def test_get_rds_price_success(price_calculator):
    """Test successful RDS price retrieval."""
    price = price_calculator._get_rds_price("db.t3.medium", "mysql", "us-east-1")
    assert price == 0.0416


def test_get_rds_storage_price(price_calculator):
    """Test RDS storage price retrieval."""
    price = price_calculator._get_rds_price("storage", "mysql", "us-east-1")
    
    # Should return hardcoded storage price
    assert price == price_calculator.FALLBACK_PRICES["rds"]["storage"]


def test_get_s3_price_success(price_calculator):
    """Test successful S3 price retrieval."""
    price = price_calculator._get_s3_price("Standard", "us-east-1")
    assert price == 0.0416


def test_get_s3_price_fallback(price_calculator):
    """Test S3 price fallback for unknown storage class."""
    with patch.object(price_calculator.pricing_client, "get_products", return_value={"PriceList": []}):
        price = price_calculator._get_s3_price("Unknown", "us-east-1")
        
        # Should return default Standard price
        assert price == price_calculator.FALLBACK_PRICES["s3"]["Standard"]


def test_calculate_resource_cost_ec2(price_calculator):
    """Test cost calculation for EC2 resource."""
    resource = ResourceConfig(
        service="ec2",
        resource_type="web_server",
        specs={"instance_type": "t3.medium"},
        region="us-east-1",
        quantity=2,
        usage_hours=730.0,
    )
    
    result = price_calculator.calculate_resource_cost(resource)
    
    assert isinstance(result, PricingResult)
    assert result.resource_type == "EC2 t3.medium"
    assert result.unit_price == 0.0416
    assert result.quantity == 2
    assert result.usage_hours == 730.0
    assert result.monthly_cost == 0.0416 * 2 * 730.0
    assert "instance_type" in result.details
    assert "hourly_rate" in result.details


def test_calculate_resource_cost_rds(price_calculator):
    """Test cost calculation for RDS resource."""
    resource = ResourceConfig(
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
    
    result = price_calculator.calculate_resource_cost(resource)
    
    assert isinstance(result, PricingResult)
    assert result.resource_type == "RDS db.t3.medium"
    assert "storage_cost" in result.details
    assert result.details["storage_gb"] == 100


def test_calculate_resource_cost_s3(price_calculator):
    """Test cost calculation for S3 resource."""
    resource = ResourceConfig(
        service="s3",
        resource_type="storage",
        specs={
            "storage_class": "Standard",
            "storage_gb": 500,
        },
        region="us-east-1",
    )
    
    result = price_calculator.calculate_resource_cost(resource)
    
    assert isinstance(result, PricingResult)
    assert result.resource_type == "S3 Standard"
    assert "storage_gb" in result.details
    assert result.details["storage_gb"] == 500


def test_calculate_resource_cost_unsupported_service(price_calculator):
    """Test cost calculation for unsupported service."""
    resource = ResourceConfig(
        service="unsupported",
        resource_type="test",
        specs={},
        region="us-east-1",
    )
    
    with pytest.raises(ValueError) as excinfo:
        price_calculator.calculate_resource_cost(resource)
    
    assert "Unsupported service: unsupported" in str(excinfo.value)


def test_calculate_total_cost(price_calculator):
    """Test total cost calculation for multiple resources."""
    resources = [
        ResourceConfig(
            service="ec2",
            resource_type="web_server",
            specs={"instance_type": "t3.medium"},
            region="us-east-1",
            quantity=2,
        ),
        ResourceConfig(
            service="s3",
            resource_type="storage",
            specs={
                "storage_class": "Standard",
                "storage_gb": 100,
            },
            region="us-east-1",
        ),
    ]
    
    result = price_calculator.calculate_total_cost(resources)
    
    assert "total_monthly_cost" in result
    assert "resources" in result
    assert len(result["resources"]) == 2
    
    # EC2 cost + S3 cost
    ec2_cost = 0.0416 * 2 * 730.0
    s3_cost = 0.0416 * 100  # Using mocked price
    assert result["total_monthly_cost"] == pytest.approx(ec2_cost + s3_cost) 