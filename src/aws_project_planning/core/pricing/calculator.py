"""AWS Price Calculator module."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import boto3


@dataclass
class ResourceConfig:
    """Configuration for an AWS resource."""

    service: str
    resource_type: str
    specs: Dict[str, Any]
    region: str
    quantity: int = 1
    usage_hours: float = 730.0  # Default to a month


@dataclass
class PricingResult:
    """Result of a pricing calculation."""

    resource_type: str
    unit_price: float
    quantity: int
    usage_hours: float
    monthly_cost: float
    details: Dict[str, Any]


class AWSPriceCalculator:
    """Calculator for AWS resource pricing."""

    # Fallback prices when API doesn't return results
    FALLBACK_PRICES = {
        "ec2": {
            "t3.nano": 0.0052,
            "t3.micro": 0.0104,
            "t3.small": 0.0208,
            "t3.medium": 0.0416,
            "t3.large": 0.0832,
            "t3.xlarge": 0.1664,
            "t3.2xlarge": 0.3328,
            "m5.large": 0.096,
            "m5.xlarge": 0.192,
            "m5.2xlarge": 0.384,
            "m5.4xlarge": 0.768,
        },
        "rds": {
            "db.t3.micro": 0.017,
            "db.t3.small": 0.034,
            "db.t3.medium": 0.068,
            "db.t3.large": 0.136,
            "db.t3.xlarge": 0.272,
            "db.t3.2xlarge": 0.544,
            "db.m5.large": 0.155,
            "db.m5.xlarge": 0.31,
            "db.m5.2xlarge": 0.62,
            "db.m5.4xlarge": 1.24,
            "storage": 0.115,  # Price per GB per month
        },
        "s3": {
            "Standard": 0.023,     # Per GB per month
            "Standard-IA": 0.0125, # Per GB per month
            "Glacier": 0.004,      # Per GB per month
        }
    }

    def __init__(self, region: str = "us-east-1"):
        """Initialize AWS Price Calculator."""
        self.pricing_client = boto3.client("pricing", region_name="us-east-1")
        self.default_region = region
        self.logger = logging.getLogger(__name__)

    def _extract_price(self, price_list: List[Dict]) -> Optional[float]:
        """Extract price from AWS pricing API response."""
        try:
            for item in price_list:
                # Parse the item as it comes as a string
                if isinstance(item, str):
                    item = json.loads(item)
                
                # Get the first OnDemand term
                terms = item.get("terms", {}).get("OnDemand", {})
                if not terms:
                    continue
                
                # Get the first price dimension
                for term_key in terms:
                    price_dimensions = terms[term_key].get("priceDimensions", {})
                    for dimension_key in price_dimensions:
                        price_per_unit = price_dimensions[dimension_key].get("pricePerUnit", {})
                        if "USD" in price_per_unit:
                            return float(price_per_unit["USD"])
            
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting price: {str(e)}")
            return None

    def _get_ec2_price(self, instance_type: str, region: str) -> float:
        """Get EC2 instance price."""
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                    {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                    {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                ],
            )

            price = self._extract_price(response["PriceList"])
            if price is not None:
                return price
            
            # Fallback to hardcoded prices
            self.logger.warning(f"No pricing found for EC2 {instance_type}, using fallback price")
            return self.FALLBACK_PRICES["ec2"].get(instance_type, 0.05)  # Default fallback of $0.05/hour

        except Exception as e:
            self.logger.warning(f"Error getting EC2 price: {str(e)}")
            return self.FALLBACK_PRICES["ec2"].get(instance_type, 0.05)  # Default fallback

    def _get_rds_price(self, instance_type: str, engine: str, region: str) -> float:
        """Get RDS instance price."""
        try:
            if instance_type == "storage":
                # For storage, return a per-GB price
                return self.FALLBACK_PRICES["rds"].get("storage", 0.115)
                
            response = self.pricing_client.get_products(
                ServiceCode="AmazonRDS",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                    {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": engine},
                ],
            )

            price = self._extract_price(response["PriceList"])
            if price is not None:
                return price
            
            # Fallback to hardcoded prices
            self.logger.warning(f"No pricing found for RDS {instance_type}, using fallback price")
            return self.FALLBACK_PRICES["rds"].get(instance_type, 0.1)  # Default fallback of $0.1/hour

        except Exception as e:
            self.logger.warning(f"Error getting RDS price: {str(e)}")
            return self.FALLBACK_PRICES["rds"].get(instance_type, 0.1)  # Default fallback

    def _get_s3_price(self, storage_class: str, region: str) -> float:
        """Get S3 storage price per GB."""
        try:
            response = self.pricing_client.get_products(
                ServiceCode="AmazonS3",
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "storageClass", "Value": storage_class},
                    {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                ],
            )

            price = self._extract_price(response["PriceList"])
            if price is not None:
                return price
            
            # Fallback to hardcoded prices
            self.logger.warning(f"No pricing found for S3 {storage_class}, using fallback price")
            return self.FALLBACK_PRICES["s3"].get(storage_class, 0.023)  # Default to Standard

        except Exception as e:
            self.logger.warning(f"Error getting S3 price: {str(e)}")
            return self.FALLBACK_PRICES["s3"].get(storage_class, 0.023)  # Default to Standard

    def calculate_resource_cost(self, resource: ResourceConfig) -> PricingResult:
        """Calculate cost for a single resource."""
        if resource.service == "ec2":
            unit_price = self._get_ec2_price(
                resource.specs["instance_type"], resource.region
            )
            monthly_cost = unit_price * resource.quantity * resource.usage_hours
            return PricingResult(
                resource_type=f"EC2 {resource.specs['instance_type']}",
                unit_price=unit_price,
                quantity=resource.quantity,
                usage_hours=resource.usage_hours,
                monthly_cost=monthly_cost,
                details={
                    "instance_type": resource.specs["instance_type"],
                    "region": resource.region,
                    "hourly_rate": unit_price,
                },
            )

        elif resource.service == "rds":
            unit_price = self._get_rds_price(
                resource.specs["instance_type"],
                resource.specs["engine"],
                resource.region,
            )
            monthly_cost = unit_price * resource.quantity * resource.usage_hours
            storage_gb = resource.specs.get("storage_gb", 0)
            storage_price = self._get_rds_price("storage", resource.specs["engine"], resource.region)
            storage_cost = storage_price * storage_gb
            total_cost = monthly_cost + storage_cost
            return PricingResult(
                resource_type=f"RDS {resource.specs['instance_type']}",
                unit_price=unit_price,
                quantity=resource.quantity,
                usage_hours=resource.usage_hours,
                monthly_cost=total_cost,
                details={
                    "instance_type": resource.specs["instance_type"],
                    "engine": resource.specs["engine"],
                    "storage_gb": storage_gb,
                    "region": resource.region,
                    "hourly_rate": unit_price,
                    "storage_price_per_gb": storage_price,
                    "storage_cost": storage_cost,
                },
            )

        elif resource.service == "s3":
            storage_class = resource.specs.get("storage_class", "Standard")
            unit_price = self._get_s3_price(storage_class, resource.region)
            storage_gb = resource.specs.get("storage_gb", 0)
            monthly_cost = unit_price * storage_gb
            return PricingResult(
                resource_type=f"S3 {storage_class}",
                unit_price=unit_price,
                quantity=1,
                usage_hours=730,
                monthly_cost=monthly_cost,
                details={
                    "storage_class": storage_class,
                    "storage_gb": storage_gb,
                    "region": resource.region,
                    "gb_month_rate": unit_price,
                },
            )

        elif resource.service == "sqs":
            # Fixed monthly cost for SQS
            monthly_cost = 0.40  # $0.40 per 1M requests
            return PricingResult(
                resource_type="SQS Standard Queue",
                unit_price=monthly_cost,
                quantity=1,
                usage_hours=730,
                monthly_cost=monthly_cost,
                details={
                    "region": resource.region,
                    "monthly_rate": monthly_cost,
                },
            )

        elif resource.service == "cloudwatch":
            # Basic CloudWatch monitoring cost
            monthly_cost = 0.30  # $0.30 per metric per month
            return PricingResult(
                resource_type="CloudWatch Monitoring",
                unit_price=monthly_cost,
                quantity=1,
                usage_hours=730,
                monthly_cost=monthly_cost,
                details={
                    "region": resource.region,
                    "monthly_rate": monthly_cost,
                },
            )

        elif resource.service == "waf":
            # WAF cost per month
            monthly_cost = 5.00  # $5 per Web ACL per month
            return PricingResult(
                resource_type="WAF",
                unit_price=monthly_cost,
                quantity=1,
                usage_hours=730,
                monthly_cost=monthly_cost,
                details={
                    "region": resource.region,
                    "monthly_rate": monthly_cost,
                },
            )

        else:
            raise ValueError(f"Unsupported service: {resource.service}")

    def calculate_total_cost(self, resources: List[ResourceConfig]) -> Dict[str, Any]:
        """Calculate total cost for all resources."""
        results = []
        total_cost = 0.0

        for resource in resources:
            result = self.calculate_resource_cost(resource)
            results.append(result)
            total_cost += result.monthly_cost

        return {
            "total_monthly_cost": total_cost,
            "resources": [
                {
                    "type": r.resource_type,
                    "monthly_cost": r.monthly_cost,
                    "details": r.details,
                }
                for r in results
            ],
        } 