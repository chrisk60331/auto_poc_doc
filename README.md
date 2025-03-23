# AWS Project Planning Tool

A comprehensive tool for creating Statement of Work (SOW), AWS Architecture Diagrams, and AWS Price Estimates.

## Features

- **Statement of Work Generation**: Create professional SOW documents from customizable templates
- **AWS Architecture Diagrams**: Generate clear and professional architecture diagrams
- **AWS Price Estimation**: Calculate cost estimates for AWS resources with two approaches:
  - Local calculation for quick estimates
  - Browser-based calculator for accurate, shareable AWS pricing
- **AI-Powered Configuration Generation**: Use Amazon Bedrock to generate AWS configurations from meeting notes or transcripts
- **End-to-End Workflow**: Go from meeting notes to complete deliverables in a single command
- Dual interface:
  - CLI using Click
  - REST API using FastAPI
- Comprehensive test coverage
- Modern dependency management with uv

## Project Structure

```
.
├── pyproject.toml           # Project configuration and dependencies
├── README.md                # This file
├── src/
│   ├── cli/                # Click-based CLI implementation
│   ├── api/                # FastAPI implementation
│   ├── core/               # Core business logic
│   │   ├── sow/           # SOW generation logic
│   │   ├── diagrams/      # AWS architecture diagram generation
│   │   └── pricing/       # AWS pricing calculation
│   └── utils/             # Shared utilities
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test fixtures
├── docs/                  # Documentation
└── examples/             # Example configurations and outputs
```

## Requirements

- Python 3.10+
- uv (for dependency management)
- AWS Account (for pricing calculations)
- Graphviz (for diagram generation)
- Chrome/Chromium (for browser-based pricing with pyppeteer)

## Installation

### Setting up with uv (Recommended)

```bash
# Install uv if not already installed
pip install uv

# Create and activate a new virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"
```

### Alternative Installation

```bash
# Install the package using uv
uv pip install aws-project-planning
```

or install from source:

```bash
git clone https://github.com/yourusername/aws-project-planning.git
cd aws-project-planning

# Create and activate a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install from source
uv pip install -e .
```

### Dependencies

To install Graphviz:
- macOS: `brew install graphviz`
- Ubuntu/Debian: `apt-get install graphviz`
- Windows: Download installer from the [Graphviz website](https://graphviz.org/download/)

## Usage

### Command-Line Interface

#### End-to-End Workflow

The most efficient way to use this tool is with the end-to-end workflow that generates all deliverables from meeting notes in a single command:

```bash
# Generate everything from meeting notes: SOW, diagram, and price estimate
aws-planner workflow end-to-end --notes meeting_notes.txt --output-dir my_project --sow-template standard

# Using the NMD Word template
aws-planner workflow end-to-end --notes meeting_notes.txt --output-dir my_project --sow-template NMD

# Additional options
aws-planner workflow end-to-end --notes meeting_notes.txt --output-dir my_project --sow-template standard --model anthropic.claude-v2 --region us-west-2 --no-save-configs
```

This will:
1. Generate all configurations (resources, diagram, SOW) using AI
2. Create the SOW document from the generated configuration
3. Create the architecture diagram from the generated configuration
4. Calculate AWS price estimates from the generated resources
5. Save all outputs to the specified directory

#### Generate Configurations from Meeting Notes

```bash
# Generate resources configuration
aws-planner generate resources --notes meeting_notes.txt --resources-output resources_config.yaml

# Generate diagram configuration
aws-planner generate diagram --notes meeting_notes.txt --diagram-output diagram_config.yaml

# Generate SOW configuration
aws-planner generate sow --notes meeting_notes.txt --sow-output sow_config.yaml

# Generate all configurations at once
aws-planner generate all --notes meeting_notes.txt --resources-output resources_config.yaml --diagram-output diagram_config.yaml --sow-output sow_config.yaml
```

#### Generate SOW Document

```bash
# Using standard Jinja2 template
aws-planner sow create --template standard --config sow_config.yaml --output my_sow.docx

# Using NMD Word template
aws-planner sow create --template NMD --config sow_config.yaml --output my_sow.docx
```

The SOW generator supports two types of templates:
- Jinja2 templates (e.g., `standard.j2`) - Text-based templates with placeholders
- Word document templates (e.g., `NMD.docx`) - Pre-formatted Word documents with placeholders

When using Word document templates:
- The generator automatically sets the prepared date to today's date
- The effective date is automatically set to two weeks from the prepared date
- Placeholders in the document are replaced with values from your configuration

To list available templates:
```bash
aws-planner sow list-templates
```

#### Generate AWS Architecture Diagram

```bash
# Create from diagram configuration
aws-planner diagram create --config diagram_config.yaml --output architecture.png

# Create from resources configuration (same as used for pricing)
aws-planner diagram from-resources --resources resources_config.yaml --output architecture.png
```

#### Generate AWS Price Estimate

The pricing module offers two methods for calculating AWS costs:

##### URL-Based Price Estimates

```bash
# Basic price estimate
aws-planner pricing estimate --resources resources_config.yaml --region us-east-1 --output estimate.txt

# Generate only the AWS Calculator URL
aws-planner pricing estimate --resources resources_config.yaml --url-only

# Generate price estimate with AWS Calculator URL
aws-planner pricing estimate --resources resources_config.yaml --include-url

# Generate just the AWS Calculator URL
aws-planner pricing calculator-url --resources resources_config.yaml
```

##### Browser-Based Price Estimates (New!)

For more accurate pricing directly from the AWS Calculator:

```bash
# Generate price estimate using headless browser automation
aws-planner pricing browser-estimate --resources resources_config.yaml --output-dir price_results

# Use a visible browser window for debugging
aws-planner pricing browser-estimate --resources resources_config.yaml --output-dir price_results --no-headless
```

The browser-based calculator:
- Uses pyppeteer to automate Chrome/Chromium
- Loads your resources into the official AWS Pricing Calculator
- Captures screenshots of the pricing page
- Extracts detailed pricing information
- Saves results and the calculator URL for sharing

This approach provides several benefits:
1. **Official AWS Pricing**: Uses the live AWS Calculator for up-to-date pricing
2. **Visual Verification**: Captures screenshots of the pricing estimate
3. **Accurate Breakdowns**: Gets detailed price data for each service
4. **Shareability**: Creates URLs that can be shared with clients or team members

### API Server

Start the API server:

```bash
uvicorn aws_project_planning.api.main:app --reload
```

Access the API documentation at http://localhost:8000/docs

The API provides endpoints for:
- Creating SOW documents
- Generating AWS architecture diagrams
- Calculating AWS price estimates
- Converting meeting notes to AWS configurations using AI

## Configuration Files

### Statement of Work Configuration

```yaml
project_name: "AWS Migration Project"
client_name: "Acme Corporation"
project_description: "Migration of on-premises infrastructure to AWS cloud platform."
scope:
  - "Assessment of current infrastructure"
  - "Design of target AWS architecture"
  - "Migration execution and testing"
deliverables:
  - "Architecture design document"
  - "Migration plan"
  - "Completed migration with test results"
timeline:
  - phase: "Assessment"
    duration: "2 weeks"
  - phase: "Design"
    duration: "3 weeks"
  - phase: "Migration"
    duration: "6 weeks"
cost:
  total: 75000
  schedule:
    "Phase 1 (Assessment)": 15000
    "Phase 2 (Design)": 25000
    "Phase 3 (Migration)": 35000
assumptions:
  - "Client will provide access to current infrastructure"
  - "Client will allocate resources for testing"
```

### Diagram Configuration

```yaml
name: "Three-Tier Web Application"
direction: "TB"  # Top to Bottom

clusters:
  - name: "Web Tier"
    nodes:
      - name: "web_server_1"
        service: "ec2"
      - name: "web_server_2"
        service: "ec2"
        
  - name: "App Tier"
    nodes:
      - name: "app_server_1"
        service: "ec2"
      - name: "app_server_2"
        service: "ec2"
        
  - name: "Database Tier"
    nodes:
      - name: "database"
        service: "rds"
      
connections:
  - from: "web_server_1"
    to: "app_server_1"
    label: "HTTP/S"
    
  - from: "web_server_2"
    to: "app_server_2"
    label: "HTTP/S"
    
  - from: "app_server_1"
    to: "database"
    label: "SQL"
    
  - from: "app_server_2"
    to: "database"
    label: "SQL"
```

### Resources Configuration

```yaml
resources:
  - service: ec2
    type: web_server
    specs:
      instance_type: t3.medium
    region: us-east-1
    quantity: 2
    usage_hours: 730  # 24/7 operation

  - service: ec2
    type: app_server
    specs:
      instance_type: t3.large
    region: us-east-1
    quantity: 2
    usage_hours: 730

  - service: rds
    type: database
    specs:
      instance_type: db.t3.large
      engine: mysql
      storage_gb: 100
    region: us-east-1
    quantity: 1
    usage_hours: 730

  - service: s3
    type: app_storage
    specs:
      storage_class: Standard
      storage_gb: 500
    region: us-east-1
```

## Development

```bash
# Setup development environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
```

## Demo Scripts

The repository includes demonstration scripts to help you get started:

```bash
# Test the browser-based pricing calculator
python demo_browser_calculator.py grid_visibility/configs/grid_visibility_resources.yaml

# Run with visible browser for debugging
python demo_browser_calculator.py grid_visibility/configs/grid_visibility_resources.yaml --no-headless
```

## AWS Bedrock Integration

This tool integrates with Amazon Bedrock to provide AI-powered generation of AWS configurations from natural language descriptions, meeting notes, or project transcripts. The LLM can:

1. Parse project requirements from unstructured text
2. Determine appropriate AWS services and instance types
3. Generate structured YAML configurations for resources, architecture diagrams, and SOW documents

To use the Bedrock integration:

1. Ensure your AWS credentials are configured with Bedrock access
2. Create a text file with project requirements or meeting notes
3. Use the `generate` commands to create configurations

The default model is `anthropic.claude-v2`, but you can specify other Bedrock models:

```bash
aws-planner generate resources --notes meeting_notes.txt --model amazon.titan-text-express-v1
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT

## Acknowledgments

- [Diagrams](https://diagrams.mingrammer.com/) for the architecture diagram generation
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework
- [Click](https://click.palletsprojects.com/) for the CLI framework
- [pyppeteer](https://github.com/pyppeteer/pyppeteer) for headless browser automation 