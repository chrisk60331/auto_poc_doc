"""Command-line interface for AWS Project Planning Tool."""

import json
import os
from datetime import datetime
from pathlib import Path

import click
import yaml

from aws_project_planning import __version__
from aws_project_planning.core.bedrock.service import BedrockService
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


@cli.group()
def generate():
    """Generate configurations from project notes or transcripts using AI."""
    pass


@cli.group()
def workflow():
    """Run complete workflows from notes to deliverables."""
    pass


@workflow.command()
@click.option("--notes", type=click.Path(exists=True), required=True, help="File containing meeting notes or transcript")
@click.option("--output-dir", type=click.Path(), default="output", help="Directory for all output files")
@click.option("--sow-template", type=str, default="standard", help="SOW template to use")
@click.option("--model", type=str, default="anthropic.claude-v2", help="Bedrock model to use")
@click.option("--region", type=str, default="us-east-1", help="AWS region to use")
@click.option("--save-configs/--no-save-configs", default=True, help="Whether to save intermediate configuration files")
def end_to_end(notes: str, output_dir: str, sow_template: str, model: str, region: str, save_configs: bool):
    """Generate SOW, diagram, and price estimate from notes in one step.
    
    Takes meeting notes or transcript and generates all deliverables:
    1. Statement of Work document
    2. AWS Architecture diagram
    3. Price estimate report
    """
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Set paths for configs and outputs
        project_name = Path(notes).stem.replace("_", " ").title()
        path_prefix = f"{project_name.lower().replace(' ', '_')}"
        
        # Determine paths for configs and outputs
        configs_dir = os.path.join(output_dir, "configs")
        if save_configs:
            os.makedirs(configs_dir, exist_ok=True)
            resources_config_path = os.path.join(configs_dir, f"{path_prefix}_resources.yaml")
            diagram_config_path = os.path.join(configs_dir, f"{path_prefix}_diagram.yaml")
            sow_config_path = os.path.join(configs_dir, f"{path_prefix}_sow.yaml")
        else:
            resources_config_path = None
            diagram_config_path = None
            sow_config_path = None
        
        # Output paths for final artifacts
        sow_output_path = os.path.join(output_dir, f"{path_prefix}_sow.docx")
        diagram_output_path = os.path.join(output_dir, f"{path_prefix}_architecture.png")
        pricing_output_path = os.path.join(output_dir, f"{path_prefix}_pricing.txt")
        
        click.echo(f"\n🚀 Starting end-to-end workflow for: {project_name}")
        click.echo("───────────────────────────────────────────────────")
        
        # Initialize services
        bedrock_service = BedrockService(model_id=model)
        sow_service = SOWService()
        diagram_service = DiagramService(default_region=region)
        pricing_service = PricingService(default_region=region)
        
        # Read notes content
        with open(notes, "r") as f:
            notes_content = f.read()
        
        # Step 1: Generate all configurations
        click.echo("📝 Generating configurations from notes...")
        resources_config, diagram_config, sow_config = bedrock_service.generate_configs_from_file(
            file_path=notes,
            resources_output=resources_config_path,
            diagram_output=diagram_config_path,
            sow_output=sow_config_path
        )
        
        if save_configs:
            click.echo(f"  ✓ Resources config saved to: {resources_config_path}")
            click.echo(f"  ✓ Diagram config saved to: {diagram_config_path}")
            click.echo(f"  ✓ SOW config saved to: {sow_config_path}")
        
        # Step 2: Create SOW document
        click.echo("\n📄 Creating Statement of Work document...")
        try:
            # Create temporary file for config if not saving
            if not sow_config_path:
                temp_sow_config = os.path.join(output_dir, "temp_sow_config.yaml")
                with open(temp_sow_config, "w") as f:
                    yaml.dump(sow_config, f, default_flow_style=False)
                sow_config_path = temp_sow_config
            
            # Create SOW document
            sow_path = sow_service.create_sow(
                template_name=sow_template,
                output_path=sow_output_path,
                **sow_config
            )
            click.echo(f"  ✓ SOW document created: {sow_path}")
            
            # Clean up temporary file if created
            if not save_configs and os.path.exists(temp_sow_config):
                os.remove(temp_sow_config)
                
        except Exception as e:
            click.echo(f"  ✗ Error creating SOW document: {str(e)}", err=True)
        
        # Step 3: Create architecture diagram
        click.echo("\n🏗️ Creating AWS architecture diagram...")
        try:
            # Create temporary file for config if not saving
            if not diagram_config_path:
                temp_diagram_config = os.path.join(output_dir, "temp_diagram_config.yaml")
                with open(temp_diagram_config, "w") as f:
                    yaml.dump(diagram_config, f, default_flow_style=False)
                diagram_config_path = temp_diagram_config
            
            # Create diagram
            diagram_path = diagram_service.create_diagram(
                config=diagram_config_path,
                output_path=diagram_output_path
            )
            click.echo(f"  ✓ Architecture diagram created: {diagram_path}")
            
            # Clean up temporary file if created
            if not save_configs and os.path.exists(temp_diagram_config):
                os.remove(temp_diagram_config)
                
        except Exception as e:
            click.echo(f"  ✗ Error creating architecture diagram: {str(e)}", err=True)
        
        # Step 4: Calculate prices
        click.echo("\n💰 Calculating AWS price estimate...")
        try:
            # Create temporary file for config if not saving
            if not resources_config_path:
                temp_resources_config = os.path.join(output_dir, "temp_resources_config.yaml")
                with open(temp_resources_config, "w") as f:
                    yaml.dump(resources_config, f, default_flow_style=False)
                resources_config_path = temp_resources_config
            
            # Calculate prices
            costs = pricing_service.estimate_from_config(resources_config_path)
            
            # Format and save report
            report = pricing_service.format_cost_report(costs)
            with open(pricing_output_path, "w") as f:
                f.write(report)
            
            click.echo(f"  ✓ Price estimate generated: {pricing_output_path}")
            click.echo(f"\n  Total monthly cost: ${costs['total_monthly_cost']:,.2f}")
            
            # Clean up temporary file if created
            if not save_configs and os.path.exists(temp_resources_config):
                os.remove(temp_resources_config)
                
        except Exception as e:
            click.echo(f"  ✗ Error calculating price estimate: {str(e)}", err=True)
        
        # Output summary
        click.echo("\n✅ Workflow complete! Generated outputs:")
        click.echo("───────────────────────────────────────────────────")
        click.echo(f"  📄 SOW Document:          {sow_output_path}")
        click.echo(f"  🏗️ Architecture Diagram:   {diagram_output_path}")
        click.echo(f"  💰 Price Estimate:        {pricing_output_path}")
        
        if save_configs:
            click.echo("\n  Configuration files:")
            click.echo(f"  📝 Resources Config:      {resources_config_path}")
            click.echo(f"  📝 Diagram Config:        {diagram_config_path}")
            click.echo(f"  📝 SOW Config:            {sow_config_path}")
            
    except Exception as e:
        click.echo(f"Error in end-to-end workflow: {str(e)}", err=True)
        raise click.Abort()


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


@generate.command()
@click.option("--notes", type=click.Path(exists=True), required=True, help="File containing meeting notes or transcript")
@click.option("--resources-output", type=click.Path(), help="Output file for resources configuration")
@click.option("--model", type=str, default="anthropic.claude-v2", help="Bedrock model to use")
def resources(notes: str, resources_output: str, model: str):
    """Generate AWS resources configuration from notes/transcript using AI."""
    try:
        click.echo("Generating AWS resources configuration from notes...")
        
        # Initialize Bedrock service
        service = BedrockService(model_id=model)
        
        # Generate resources configuration
        resources_config = service.generate_resources_config(
            text=open(notes, "r").read(),
            output_path=resources_output
        )
        
        # Output result
        if resources_output:
            click.echo(f"Resources configuration saved to: {resources_output}")
        else:
            # If no output file specified, print to console
            click.echo("\nGenerated resources configuration:")
            click.echo("-----------------------------------")
            click.echo(yaml.dump(resources_config, default_flow_style=False))
            
    except Exception as e:
        click.echo(f"Error generating resources configuration: {str(e)}", err=True)
        raise click.Abort()


@generate.command()
@click.option("--notes", type=click.Path(exists=True), required=True, help="File containing meeting notes or transcript")
@click.option("--diagram-output", type=click.Path(), help="Output file for diagram configuration")
@click.option("--model", type=str, default="anthropic.claude-v2", help="Bedrock model to use")
def diagram(notes: str, diagram_output: str, model: str):
    """Generate AWS architecture diagram configuration from notes/transcript using AI."""
    try:
        click.echo("Generating AWS architecture diagram configuration from notes...")
        
        # Initialize Bedrock service
        service = BedrockService(model_id=model)
        
        # Generate diagram configuration
        diagram_config = service.generate_diagram_config(
            text=open(notes, "r").read(),
            output_path=diagram_output
        )
        
        # Output result
        if diagram_output:
            click.echo(f"Diagram configuration saved to: {diagram_output}")
        else:
            # If no output file specified, print to console
            click.echo("\nGenerated diagram configuration:")
            click.echo("---------------------------------")
            click.echo(yaml.dump(diagram_config, default_flow_style=False))
            
    except Exception as e:
        click.echo(f"Error generating diagram configuration: {str(e)}", err=True)
        raise click.Abort()


@generate.command()
@click.option("--notes", type=click.Path(exists=True), required=True, help="File containing meeting notes or transcript")
@click.option("--sow-output", type=click.Path(), help="Output file for SOW configuration")
@click.option("--model", type=str, default="anthropic.claude-v2", help="Bedrock model to use")
def sow(notes: str, sow_output: str, model: str):
    """Generate Statement of Work configuration from notes/transcript using AI."""
    try:
        click.echo("Generating Statement of Work configuration from notes...")
        
        # Initialize Bedrock service
        service = BedrockService(model_id=model)
        
        # Generate SOW configuration
        sow_config = service.generate_sow_config(
            text=open(notes, "r").read(),
            output_path=sow_output
        )
        
        # Output result
        if sow_output:
            click.echo(f"SOW configuration saved to: {sow_output}")
        else:
            # If no output file specified, print to console
            click.echo("\nGenerated SOW configuration:")
            click.echo("----------------------------")
            click.echo(yaml.dump(sow_config, default_flow_style=False))
            
    except Exception as e:
        click.echo(f"Error generating SOW configuration: {str(e)}", err=True)
        raise click.Abort()


@generate.command()
@click.option("--notes", type=click.Path(exists=True), required=True, help="File containing meeting notes or transcript")
@click.option("--resources-output", type=click.Path(), help="Output file for resources configuration")
@click.option("--diagram-output", type=click.Path(), help="Output file for diagram configuration")
@click.option("--sow-output", type=click.Path(), help="Output file for SOW configuration")
@click.option("--model", type=str, default="anthropic.claude-v2", help="Bedrock model to use")
def all(notes: str, resources_output: str, diagram_output: str, sow_output: str, model: str):
    """Generate all configurations from notes/transcript using AI."""
    try:
        click.echo("Generating AWS configurations from notes...")
        
        # Initialize Bedrock service
        service = BedrockService(model_id=model)
        
        # Generate configurations
        resources_config, diagram_config, sow_config = service.generate_configs_from_file(
            file_path=notes,
            resources_output=resources_output,
            diagram_output=diagram_output,
            sow_output=sow_output
        )
        
        # Output result
        if resources_output:
            click.echo(f"Resources configuration saved to: {resources_output}")
        if diagram_output:
            click.echo(f"Diagram configuration saved to: {diagram_output}")
        if sow_output:
            click.echo(f"SOW configuration saved to: {sow_output}")
            
        if not resources_output and not diagram_output and not sow_output:
            # If no output files specified, print to console
            click.echo("\nGenerated resources configuration:")
            click.echo("-----------------------------------")
            click.echo(yaml.dump(resources_config, default_flow_style=False))
            
            click.echo("\nGenerated diagram configuration:")
            click.echo("---------------------------------")
            click.echo(yaml.dump(diagram_config, default_flow_style=False))
            
            if sow_config:
                click.echo("\nGenerated SOW configuration:")
                click.echo("----------------------------")
                click.echo(yaml.dump(sow_config, default_flow_style=False))
            
    except Exception as e:
        click.echo(f"Error generating configurations: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli() 