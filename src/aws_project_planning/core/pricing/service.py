"""Service layer for AWS pricing calculations."""

from typing import Any, Dict, List, Optional

import yaml

from .calculator import AWSPriceCalculator, ResourceConfig
from .web_calculator import AWSWebCalculator
from .browser_calculator import get_price_estimate, save_price_estimate


class PricingService:
    """Service for managing AWS pricing calculations."""

    def __init__(self, default_region: str = "us-east-1"):
        """Initialize pricing service."""
        self.calculator = AWSPriceCalculator(default_region)
        self.web_calculator = AWSWebCalculator()
        self.default_region = default_region

    def load_resources_from_config(self, config_path: str) -> List[ResourceConfig]:
        """Load resource configurations from a YAML file."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        resources = []
        for resource in config.get("resources", []):
            resources.append(
                ResourceConfig(
                    service=resource["service"],
                    resource_type=resource["type"],
                    specs=resource["specs"],
                    region=resource.get("region", self.default_region),
                    quantity=resource.get("quantity", 1),
                    usage_hours=resource.get("usage_hours", 730.0),
                )
            )
        return resources

    def calculate_costs(self, resources: List[ResourceConfig]) -> Dict[str, Any]:
        """Calculate costs for all resources."""
        return self.calculator.calculate_total_cost(resources)

    def estimate_from_config(self, config_path: str) -> Dict[str, Any]:
        """Calculate costs from a configuration file."""
        resources = self.load_resources_from_config(config_path)
        return self.calculate_costs(resources)

    def format_cost_report(self, costs: Dict[str, Any]) -> str:
        """Format cost information into a readable report."""
        report = [
            "AWS Cost Estimate",
            "=================",
            f"Total Monthly Cost: ${costs['total_monthly_cost']:,.2f}",
            "",
            "Resource Breakdown:",
            "-------------------",
        ]
        
        for resource in costs["resources"]:
            report.append(f"{resource['type']}: ${resource['monthly_cost']:,.2f}")
            
            # Add details if available
            details = resource.get("details", {})
            if details:
                for key, value in details.items():
                    if key in ["instance_type", "engine", "storage_gb", "region", "hourly_rate", "storage_class"]:
                        if isinstance(value, float):
                            report.append(f"  - {key}: ${value:,.4f}")
                        else:
                            report.append(f"  - {key}: {value}")
            
            report.append("")
        
        return "\n".join(report)
    
    def generate_calculator_url(self, resources: List[ResourceConfig]) -> str:
        """Generate AWS Calculator URL for the given resources."""
        return self.web_calculator.generate_calculator_url(resources)
    
    def generate_calculator_url_from_config(self, config_path: str) -> str:
        """Generate AWS Calculator URL from a configuration file."""
        resources = self.load_resources_from_config(config_path)
        return self.generate_calculator_url(resources)
    
    def generate_cost_report(self, resources: List[ResourceConfig], include_url: bool = True) -> Dict[str, Any]:
        """
        Generate a comprehensive cost report with both calculated costs and a share URL.
        
        Args:
            resources: List of resource configurations
            include_url: Whether to include a URL to the AWS Calculator (default: True)
            
        Returns:
            Dict containing costs, formatted report, and optionally a share URL
        """
        # Calculate costs using our local calculator
        costs = self.calculate_costs(resources)
        
        # Format a readable report
        report = self.format_cost_report(costs)
        
        result = {
            "costs": costs,
            "report": report,
        }
        
        # Add share URL if requested
        if include_url:
            calculator_url = self.generate_calculator_url(resources)
            result["calculator_url"] = calculator_url
            
        return result
    
    def generate_cost_report_from_config(self, config_path: str, include_url: bool = True) -> Dict[str, Any]:
        """Generate a comprehensive cost report from a configuration file."""
        resources = self.load_resources_from_config(config_path)
        return self.generate_cost_report(resources, include_url)
    
    def get_browser_price_estimate(self, resources: List[ResourceConfig], 
                                screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed price estimate using browser automation.
        
        This provides more accurate pricing by actually loading the AWS Calculator
        in a headless browser and extracting the computed values.
        
        Args:
            resources: List of resource configurations
            screenshot_path: Optional path to save screenshot of the estimate
                
        Returns:
            Dict containing detailed pricing information
        """
        return get_price_estimate(resources, screenshot_path)

    def get_browser_price_estimate_from_config(self, config_path: str, 
                                            screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """Get browser-based price estimate from a configuration file."""
        resources = self.load_resources_from_config(config_path)
        return self.get_browser_price_estimate(resources, screenshot_path)

    def save_browser_price_estimate(self, resources: List[ResourceConfig], 
                                output_dir: str) -> Dict[str, Any]:
        """
        Save complete price estimate with screenshot to the specified directory.
        
        Args:
            resources: List of resource configurations
            output_dir: Directory to save outputs
                
        Returns:
            Dict containing result details including file paths
        """
        return save_price_estimate(resources, output_dir)

    def save_browser_price_estimate_from_config(self, config_path: str, 
                                            output_dir: str) -> Dict[str, Any]:
        """Save browser-based price estimate from a configuration file."""
        resources = self.load_resources_from_config(config_path)
        return self.save_browser_price_estimate(resources, output_dir) 