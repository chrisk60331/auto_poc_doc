"""Unit tests for CLI functionality."""

from click.testing import CliRunner

from aws_project_planning.cli.main import cli


def test_cli_version():
    """Test CLI version command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_sow_create():
    """Test SOW creation command."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["sow", "create", "--template", "standard", "--output", "test.docx"]
    )
    assert result.exit_code == 0
    assert "Creating SOW" in result.output


def test_diagram_create():
    """Test diagram creation command."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["diagram", "create", "--config", "test-config.yaml", "--output", "diagram.png"],
    )
    assert result.exit_code == 0
    assert "Creating diagram" in result.output


def test_pricing_estimate():
    """Test pricing estimate command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["pricing", "estimate", "--resources", "resources.yaml"])
    assert result.exit_code == 0
    assert "Calculating price estimate" in result.output 