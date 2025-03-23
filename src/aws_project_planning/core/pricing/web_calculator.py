"""AWS Web Calculator service for generating shareable price estimates."""

import base64
import json
import urllib.parse
from typing import Any, Dict, List, Optional, Union

from . import calculator
from .calculator import ResourceConfig


class AWSWebCalculator:
    """
    Service for generating AWS Price Calculator URLs.
    
    This service creates shareable links to the AWS Pricing Calculator
    (https://calculator.aws/) based on resource specifications.
    """
    
    # Base URL for the AWS Calculator
    CALCULATOR_BASE_URL = "https://calculator.aws/#/estimate"
    
    # Map our service names to AWS Calculator service codes
    SERVICE_CODE_MAP = {
        "ec2": "AmazonEC2",
        "rds": "AmazonRDS", 
        "s3": "AmazonS3",
    }
    
    # Map EC2 instance types to the corresponding calculator values
    EC2_TYPE_MAP = {
        # General Purpose
        "t3.nano": {"family": "t3", "type": "t3.nano"},
        "t3.micro": {"family": "t3", "type": "t3.micro"},
        "t3.small": {"family": "t3", "type": "t3.small"},
        "t3.medium": {"family": "t3", "type": "t3.medium"},
        "t3.large": {"family": "t3", "type": "t3.large"},
        "t3.xlarge": {"family": "t3", "type": "t3.xlarge"},
        "t3.2xlarge": {"family": "t3", "type": "t3.2xlarge"},
        
        "m5.large": {"family": "m5", "type": "m5.large"},
        "m5.xlarge": {"family": "m5", "type": "m5.xlarge"},
        "m5.2xlarge": {"family": "m5", "type": "m5.2xlarge"},
        "m5.4xlarge": {"family": "m5", "type": "m5.4xlarge"},
        
        # Compute Optimized
        "c5.large": {"family": "c5", "type": "c5.large"},
        "c5.xlarge": {"family": "c5", "type": "c5.xlarge"},
        "c5.2xlarge": {"family": "c5", "type": "c5.2xlarge"},
        
        # Memory Optimized
        "r5.large": {"family": "r5", "type": "r5.large"},
        "r5.xlarge": {"family": "r5", "type": "r5.xlarge"},
        "r5.2xlarge": {"family": "r5", "type": "r5.2xlarge"},
    }
    
    # Map RDS instance types to the corresponding calculator values
    RDS_TYPE_MAP = {
        "db.t3.micro": {"family": "db.t3", "type": "db.t3.micro"},
        "db.t3.small": {"family": "db.t3", "type": "db.t3.small"},
        "db.t3.medium": {"family": "db.t3", "type": "db.t3.medium"},
        "db.t3.large": {"family": "db.t3", "type": "db.t3.large"},
        "db.t3.xlarge": {"family": "db.t3", "type": "db.t3.xlarge"},
        "db.t3.2xlarge": {"family": "db.t3", "type": "db.t3.2xlarge"},
        
        "db.m5.large": {"family": "db.m5", "type": "db.m5.large"},
        "db.m5.xlarge": {"family": "db.m5", "type": "db.m5.xlarge"},
        "db.m5.2xlarge": {"family": "db.m5", "type": "db.m5.2xlarge"},
    }
    
    # Map RDS engines to calculator values
    RDS_ENGINE_MAP = {
        "mysql": "MySQL",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mariadb": "MariaDB",
        "oracle": "Oracle",
        "sqlserver": "SQL Server",
    }
    
    # Map S3 storage classes to calculator values
    S3_STORAGE_CLASS_MAP = {
        "Standard": "General Purpose",
        "standard": "General Purpose",
        "StandardIA": "Infrequent Access",
        "standard-ia": "Infrequent Access",
        "OneZoneIA": "One Zone-IA",
        "onezone-ia": "One Zone-IA", 
        "Glacier": "Glacier Flexible Retrieval",
        "glacier": "Glacier Flexible Retrieval",
        "DeepArchive": "Glacier Deep Archive",
        "deep-archive": "Glacier Deep Archive",
        "Intelligent-Tiering": "Intelligent-Tiering",
        "intelligent-tiering": "Intelligent-Tiering",
    }
    
    def __init__(self):
        """Initialize AWS Web Calculator service."""
        pass
    
    def _convert_ec2_to_calculator_format(self, resource: ResourceConfig) -> Dict[str, Any]:
        """Convert EC2 resource to AWS Calculator format."""
        instance_type = resource.specs.get("instance_type", "t3.medium")
        instance_info = self.EC2_TYPE_MAP.get(instance_type, {"family": "t3", "type": "t3.medium"})
        
        return {
            "service": "AmazonEC2",
            "name": f"{resource.resource_type} ({instance_type})",
            "description": f"{resource.resource_type} - {resource.quantity} x {instance_type}",
            "tags": resource.resource_type,
            "quantity": resource.quantity,
            "costComponents": [
                {
                    "name": "EC2 Instance",
                    "unit": "hours",
                    "hourlyQuantity": 1,
                    "monthlyQuantity": resource.usage_hours,
                    "price": 0,  # AWS Calculator will calculate this
                    "service": "AmazonEC2",
                    "family": instance_info["family"],
                    "instanceType": instance_info["type"],
                    "region": resource.region,
                    "operatingSystem": "Linux",
                    "type": "EC2",
                }
            ]
        }
    
    def _convert_rds_to_calculator_format(self, resource: ResourceConfig) -> Dict[str, Any]:
        """Convert RDS resource to AWS Calculator format."""
        instance_type = resource.specs.get("instance_type", "db.t3.medium")
        instance_info = self.RDS_TYPE_MAP.get(instance_type, {"family": "db.t3", "type": "db.t3.medium"})
        
        engine = resource.specs.get("engine", "mysql")
        engine_name = self.RDS_ENGINE_MAP.get(engine.lower(), "MySQL")
        
        storage_gb = resource.specs.get("storage_gb", 100)
        
        return {
            "service": "AmazonRDS",
            "name": f"{resource.resource_type} ({instance_type} - {engine_name})",
            "description": f"{resource.resource_type} - {resource.quantity} x {instance_type} {engine_name} DB with {storage_gb}GB storage",
            "tags": resource.resource_type,
            "quantity": resource.quantity,
            "costComponents": [
                {
                    "name": "Database Instance",
                    "unit": "hours",
                    "hourlyQuantity": 1,
                    "monthlyQuantity": resource.usage_hours,
                    "price": 0,  # AWS Calculator will calculate this
                    "service": "AmazonRDS",
                    "family": instance_info["family"],
                    "instanceType": instance_info["type"],
                    "databaseEngine": engine_name,
                    "deploymentOption": "Single-AZ",
                    "region": resource.region,
                    "type": "RDS",
                },
                {
                    "name": "Storage",
                    "unit": "GB",
                    "hourlyQuantity": None,
                    "monthlyQuantity": storage_gb,
                    "price": 0,  # AWS Calculator will calculate this
                    "service": "AmazonRDS",
                    "storageType": "General Purpose",
                    "region": resource.region,
                    "type": "RDS-Storage"
                }
            ]
        }
    
    def _convert_s3_to_calculator_format(self, resource: ResourceConfig) -> Dict[str, Any]:
        """Convert S3 resource to AWS Calculator format."""
        storage_class = resource.specs.get("storage_class", "Standard")
        aws_storage_class = self.S3_STORAGE_CLASS_MAP.get(storage_class, "General Purpose")
        
        storage_gb = resource.specs.get("storage_gb", 100)
        
        return {
            "service": "AmazonS3",
            "name": f"{resource.resource_type} ({storage_class})",
            "description": f"{resource.resource_type} - {storage_gb}GB {storage_class} storage",
            "tags": resource.resource_type,
            "costComponents": [
                {
                    "name": "Storage",
                    "unit": "GB",
                    "hourlyQuantity": None,
                    "monthlyQuantity": storage_gb,
                    "price": 0,  # AWS Calculator will calculate this
                    "service": "AmazonS3",
                    "storageClass": aws_storage_class,
                    "region": resource.region,
                    "type": "S3-Storage"
                }
            ]
        }
    
    def _encode_calculator_data(self, calculator_data: Dict[str, Any]) -> str:
        """Encode calculator data for use in URL."""
        # Convert the data to a JSON string
        json_data = json.dumps(calculator_data)
        
        # Encode as base64
        base64_data = base64.b64encode(json_data.encode()).decode()
        
        # URL encode
        url_encoded_data = urllib.parse.quote(base64_data)
        
        return url_encoded_data
    
    def convert_resource_to_calculator_format(self, resource: ResourceConfig) -> Optional[Dict[str, Any]]:
        """Convert a resource to AWS Calculator format."""
        if resource.service == "ec2":
            return self._convert_ec2_to_calculator_format(resource)
        elif resource.service == "rds":
            return self._convert_rds_to_calculator_format(resource)
        elif resource.service == "s3":
            return self._convert_s3_to_calculator_format(resource)
        else:
            return None
    
    def convert_resources_to_calculator_format(self, resources: List[ResourceConfig]) -> Dict[str, Any]:
        """Convert resources to AWS Calculator format."""
        calculator_resources = []
        
        for resource in resources:
            calculator_resource = self.convert_resource_to_calculator_format(resource)
            if calculator_resource:
                calculator_resources.append(calculator_resource)
        
        calculator_data = {
            "estimate": {
                "resources": calculator_resources,
                "totalCost": 0,  # AWS Calculator will calculate this
                "currency": "USD",
                "timeframe": "monthly"
            }
        }
        
        return calculator_data
    
    def generate_calculator_url(self, resources: List[ResourceConfig]) -> str:
        """Generate AWS Calculator URL for the given resources."""
        calculator_data = self.convert_resources_to_calculator_format(resources)
        encoded_data = self._encode_calculator_data(calculator_data)
        
        # Construct the shareable URL
        url = f"{self.CALCULATOR_BASE_URL}?data={encoded_data}"
        
        return url 