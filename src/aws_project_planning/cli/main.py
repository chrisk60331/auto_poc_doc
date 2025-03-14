"""Command-line interface for AWS Project Planning Tool."""

import json
from datetime import datetime
from pathlib import Path

import click
import yaml

from aws_project_planning import __version__
from aws_project_planning.core.diagram.service import DiagramService
from aws_project_planning.core.pricing.service import PricingService
from aws_project_planning.core.sow.service import SOWService


@click.group()
@click.version_option(version=__version__)
def cli():
    """AWS Project Planning Tool - Create SOW, Diagrams, and Price Estimates."""
    pass


@cli.group()
def sow():
    """Manage Statement of Work documents."""
    pass


@cli.group()
def diagram():
    """Create and manage AWS architecture diagrams."""
    pass


@cli.group()
def pricing():
    """Calculate AWS price estimates."""
    pass


@sow.command()
@click.option("--template", type=str, required=True, help="Template name to use")
@click.option("--output", type=click.Path(), required=True, help="Output file path")
@click.option("--config", type=click.Path(exists=True), required=True, help="SOW configuration file")
def create(template: str, output: str, config: str):
    """Create a new Statement of Work document."""
    try:
        # Load configuration
        with open(config, "r") as f:
            sow_config = yaml.safe_load(f)

        # Initialize service
        service = SOWService()

        # Create SOW
        output_path = service.create_sow(
            template_name=template,
            output_path=output,
            **sow_config
        )
        click.echo(f"Successfully created SOW at: {output_path}")

    except Exception as e:
        click.echo(f"Error creating SOW: {str(e)}", err=True)
        raise click.Abort()


@sow.command()
def list_templates():
    """List available SOW templates."""
    service = SOWService()
    templates = service.list_templates()
    click.echo("\nAvailable templates:")
    for template in templates:
        info = service.get_template_info(template)
        click.echo(f"- {template}: {info['description']}")


@diagram.command()
@click.option("--config", type=click.Path(exists=True), required=True, help="Diagram configuration file")
@click.option("--output", type=click.Path(), required=True, help="Output diagram path")
@click.option("--region", type=str, default="us-east-1", help="AWS region for the diagram")
def create(config: str, output: str, region: str):
    """Create a new AWS architecture diagram."""
    try:
        # Initialize service
        service = DiagramService(default_region=region)
        
        # Create diagram
        diagram_path = service.create_diagram(config, output)
        
        click.echo(f"Successfully created diagram at: {diagram_path}")
    except Exception as e:
        click.echo(f"Error creating diagram: {str(e)}", err=True)
        raise click.Abort()


@diagram.command()
@click.option("--resources", type=click.Path(exists=True), required=True, help="Resources configuration file")
@click.option("--output", type=click.Path(), required=True, help="Output diagram path")
@click.option("--region", type=str, default="us-east-1", help="AWS region for the diagram")
def from_resources(resources: str, output: str, region: str):
    """Generate AWS architecture diagram from resources configuration."""
    try:
        # Initialize service
        service = DiagramService(default_region=region)
        
        # Create diagram from resources
        diagram_path = service.generate_from_resources(resources, output)
        
        click.echo(f"Successfully created diagram at: {diagram_path}")
    except Exception as e:
        click.echo(f"Error creating diagram: {str(e)}", err=True)
        raise click.Abort()


@pricing.command()
@click.option("--resources", type=click.Path(exists=True), required=True, help="Resources configuration file")
@click.option("--region", type=str, default="us-east-1", help="Default AWS region")
@click.option("--output", type=click.Path(), help="Output file for the cost report")
def estimate(resources: str, region: str, output: str):
    """Generate AWS price estimate."""
    try:
        # Initialize service
        service = PricingService(default_region=region)

        # Calculate costs
        costs = service.estimate_from_config(resources)

        # Format report
        report = service.format_cost_report(costs)

        # Output results
        click.echo("\n" + report)

        # Save to file if specified
        if output:
            with open(output, "w") as f:
                if output.endswith(".json"):
                    json.dump(costs, f, indent=2)
                else:
                    f.write(report)
            click.echo(f"\nReport saved to: {output}")

    except Exception as e:
        click.echo(f"Error calculating prices: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli() 