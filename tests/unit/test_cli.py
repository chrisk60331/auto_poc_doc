"""Unit tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aws_project_planning.cli.main import sow, diagram, pricing, generate, workflow


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()


def test_sow_create_command_success(cli_runner):
    """Test successful execution of SOW create command."""
    with patch("aws_project_planning.cli.main.SOWService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.create_sow.return_value = "test_output.docx"
        
        result = cli_runner.invoke(
            sow,
            ["create", "--template", "standard", "--config", "test_config.yaml", "--output", "test_output.docx"],
        )
        
        assert result.exit_code == 0
        assert "Successfully created SOW" in result.output
        mock_instance.create_sow.assert_called_once()


def test_sow_create_command_error(cli_runner):
    """Test error handling in SOW create command."""
    with patch("aws_project_planning.cli.main.SOWService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.create_sow.side_effect = ValueError("Test error")
        
        result = cli_runner.invoke(
            sow,
            ["create", "--template", "standard", "--config", "test_config.yaml", "--output", "test_output.docx"],
        )
        
        assert result.exit_code != 0
        assert "Error creating SOW" in result.output


def test_sow_list_templates_command(cli_runner):
    """Test the SOW list-templates command."""
    with patch("aws_project_planning.cli.main.SOWService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.list_templates.return_value = ["standard", "custom"]
        
        result = cli_runner.invoke(sow, ["list-templates"])
        
        assert result.exit_code == 0
        assert "Available templates" in result.output
        assert "standard" in result.output
        assert "custom" in result.output


def test_diagram_create_command_success(cli_runner):
    """Test successful execution of diagram create command."""
    with patch("aws_project_planning.cli.main.DiagramService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.create_diagram.return_value = "test_output.png"
        
        result = cli_runner.invoke(
            diagram,
            ["create", "--config", "test_config.yaml", "--output", "test_output.png"],
        )
        
        assert result.exit_code == 0
        assert "Successfully created diagram" in result.output
        mock_instance.create_diagram.assert_called_once()


def test_diagram_create_command_error(cli_runner):
    """Test error handling in diagram create command."""
    with patch("aws_project_planning.cli.main.DiagramService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.create_diagram.side_effect = ValueError("Test error")
        
        result = cli_runner.invoke(
            diagram,
            ["create", "--config", "test_config.yaml", "--output", "test_output.png"],
        )
        
        assert result.exit_code != 0
        assert "Error creating diagram" in result.output


def test_diagram_from_resources_command(cli_runner):
    """Test diagram from-resources command."""
    with patch("aws_project_planning.cli.main.DiagramService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_from_resources.return_value = "test_output.png"
        
        result = cli_runner.invoke(
            diagram,
            ["from-resources", "--resources", "test_resources.yaml", "--output", "test_output.png"],
        )
        
        assert result.exit_code == 0
        assert "Successfully created diagram" in result.output
        mock_instance.generate_from_resources.assert_called_once()


def test_pricing_estimate_command_success(cli_runner):
    """Test successful execution of pricing estimate command."""
    with patch("aws_project_planning.cli.main.PricingService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.estimate_from_config.return_value = {"total_monthly_cost": 100.0}
        mock_instance.format_cost_report.return_value = "Test cost report"
        
        result = cli_runner.invoke(
            pricing,
            ["estimate", "--resources", "test_resources.yaml", "--region", "us-east-1", "--output", "test_output.txt"],
        )
        
        assert result.exit_code == 0
        assert "Successfully created cost estimate" in result.output
        mock_instance.estimate_from_config.assert_called_once()
        mock_instance.format_cost_report.assert_called_once()


def test_pricing_estimate_command_error(cli_runner):
    """Test error handling in pricing estimate command."""
    with patch("aws_project_planning.cli.main.PricingService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.estimate_from_config.side_effect = ValueError("Test error")
        
        result = cli_runner.invoke(
            pricing,
            ["estimate", "--resources", "test_resources.yaml", "--region", "us-east-1", "--output", "test_output.txt"],
        )
        
        assert result.exit_code != 0
        assert "Error calculating prices" in result.output


def test_generate_resources_command(cli_runner):
    """Test generate resources command."""
    with patch("aws_project_planning.cli.main.BedrockService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_resources_config.return_value = {"resources": []}
        
        # Mock file reading
        with patch("builtins.open", MagicMock()):
            with patch("aws_project_planning.cli.main.yaml.dump") as mock_yaml_dump:
                result = cli_runner.invoke(
                    generate,
                    ["resources", "--notes", "test_notes.txt", "--resources-output", "resources_config.yaml", "--model", "test-model"],
                )
                
                assert result.exit_code == 0
                assert "Successfully generated resources configuration" in result.output
                mock_instance.generate_resources_config.assert_called_once()
                mock_yaml_dump.assert_called_once()


def test_generate_diagram_command(cli_runner):
    """Test generate diagram command."""
    with patch("aws_project_planning.cli.main.BedrockService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_diagram_config.return_value = {"clusters": []}
        
        # Mock file reading
        with patch("builtins.open", MagicMock()):
            with patch("aws_project_planning.cli.main.yaml.dump") as mock_yaml_dump:
                result = cli_runner.invoke(
                    generate,
                    ["diagram", "--notes", "test_notes.txt", "--diagram-output", "diagram_config.yaml"],
                )
                
                assert result.exit_code == 0
                assert "Successfully generated diagram configuration" in result.output
                mock_instance.generate_diagram_config.assert_called_once()
                mock_yaml_dump.assert_called_once()


def test_generate_sow_command(cli_runner):
    """Test generate sow command."""
    with patch("aws_project_planning.cli.main.BedrockService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_sow_config.return_value = {"project_name": "Test"}
        
        # Mock file reading
        with patch("builtins.open", MagicMock()):
            with patch("aws_project_planning.cli.main.yaml.dump") as mock_yaml_dump:
                result = cli_runner.invoke(
                    generate,
                    ["sow", "--notes", "test_notes.txt", "--sow-output", "sow_config.yaml"],
                )
                
                assert result.exit_code == 0
                assert "Successfully generated SOW configuration" in result.output
                mock_instance.generate_sow_config.assert_called_once()
                mock_yaml_dump.assert_called_once()


def test_generate_all_command(cli_runner):
    """Test generate all command."""
    with patch("aws_project_planning.cli.main.BedrockService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.generate_resources_config.return_value = {"resources": []}
        mock_instance.generate_diagram_config.return_value = {"clusters": []}
        mock_instance.generate_sow_config.return_value = {"project_name": "Test"}
        
        # Mock file reading
        with patch("builtins.open", MagicMock()):
            with patch("aws_project_planning.cli.main.yaml.dump") as mock_yaml_dump:
                result = cli_runner.invoke(
                    generate,
                    [
                        "all",
                        "--notes", "test_notes.txt",
                        "--resources-output", "resources_config.yaml",
                        "--diagram-output", "diagram_config.yaml",
                        "--sow-output", "sow_config.yaml",
                    ],
                )
                
                assert result.exit_code == 0
                assert "Successfully generated all configurations" in result.output
                assert mock_instance.generate_resources_config.called
                assert mock_instance.generate_diagram_config.called
                assert mock_instance.generate_sow_config.called
                assert mock_yaml_dump.call_count >= 3


def test_workflow_end_to_end_command(cli_runner):
    """Test workflow end-to-end command."""
    # Mock all service classes
    with patch("aws_project_planning.cli.main.BedrockService") as mock_bedrock, \
         patch("aws_project_planning.cli.main.DiagramService") as mock_diagram, \
         patch("aws_project_planning.cli.main.PricingService") as mock_pricing, \
         patch("aws_project_planning.cli.main.SOWService") as mock_sow:
        
        # Configure mock return values
        mock_bedrock_instance = mock_bedrock.return_value
        mock_bedrock_instance.generate_resources_config.return_value = {"resources": []}
        mock_bedrock_instance.generate_diagram_config.return_value = {"clusters": []}
        mock_bedrock_instance.generate_sow_config.return_value = {"project_name": "Test"}
        
        mock_diagram_instance = mock_diagram.return_value
        mock_diagram_instance.create_diagram.return_value = "test_diagram.png"
        
        mock_pricing_instance = mock_pricing.return_value
        mock_pricing_instance.estimate_from_config.return_value = {"total_monthly_cost": 100.0}
        mock_pricing_instance.format_cost_report.return_value = "Test cost report"
        
        mock_sow_instance = mock_sow.return_value
        mock_sow_instance.create_sow.return_value = "test_sow.docx"
        
        # Mock file operations
        with patch("builtins.open", MagicMock()), \
             patch("aws_project_planning.cli.main.yaml.dump"), \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"):
            
            result = cli_runner.invoke(
                workflow,
                [
                    "end-to-end",
                    "--notes", "test_notes.txt",
                    "--output-dir", "test_output",
                    "--sow-template", "standard",
                ],
            )
            
            assert result.exit_code == 0
            assert "Successfully completed end-to-end workflow" in result.output
            assert mock_bedrock_instance.generate_resources_config.called
            assert mock_bedrock_instance.generate_diagram_config.called
            assert mock_bedrock_instance.generate_sow_config.called
            assert mock_diagram_instance.create_diagram.called
            assert mock_pricing_instance.estimate_from_config.called
            assert mock_sow_instance.create_sow.called


def test_workflow_error_handling(cli_runner):
    """Test error handling in workflow command."""
    with patch("aws_project_planning.cli.main.BedrockService") as mock_bedrock:
        mock_instance = mock_bedrock.return_value
        mock_instance.generate_resources_config.side_effect = ValueError("Test error")
        
        # Mock file operations
        with patch("builtins.open", MagicMock()):
            result = cli_runner.invoke(
                workflow,
                [
                    "end-to-end",
                    "--notes", "test_notes.txt",
                    "--output-dir", "test_output",
                    "--sow-template", "standard",
                ],
            )
            
            assert result.exit_code != 0
            assert "Error in workflow" in result.output 