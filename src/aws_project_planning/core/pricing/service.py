"""Service layer for AWS pricing calculations."""

from typing import Any, Dict, List

import yaml

from .calculator import AWSPriceCalculator, ResourceConfig


class PricingService:
    """Service for managing AWS pricing calculations."""

    def __init__(self, default_region: str = "us-east-1"):
        """Initialize pricing service."""
        self.calculator = AWSPriceCalculator(default_region)

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
                    region=resource.get("region", self.calculator.default_region),
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
        """Format cost calculation results as a readable report."""
        report = []
        report.append("AWS Cost Estimate")
        report.append("=" * 50)
        report.append("")

        # Add resource details
        report.append("Resource Details:")
        report.append("-" * 20)
        for resource in costs["resources"]:
            report.append(f"\n{resource['type']}:")
            report.append(f"  Monthly Cost: ${resource['monthly_cost']:,.2f}")
            for key, value in resource["details"].items():
                if isinstance(value, float):
                    report.append(f"  {key}: ${value:,.4f}")
                else:
                    report.append(f"  {key}: {value}")

        # Add total
        report.append("\n" + "=" * 50)
        report.append(f"Total Monthly Cost: ${costs['total_monthly_cost']:,.2f}")
        report.append("=" * 50)

        return "\n".join(report) 