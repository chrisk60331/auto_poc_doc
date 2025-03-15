# AWS Project Planning Tool

A comprehensive tool for creating Statement of Work (SOW), AWS Architecture Diagrams, and AWS Price Estimates.

## Features

- **Statement of Work Generation**: Create professional SOW documents from customizable templates
- **AWS Architecture Diagrams**: Generate clear and professional architecture diagrams
- **AWS Price Estimation**: Calculate cost estimates for AWS resources
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
├── README.md               # This file
├── src/
│   ├── cli/               # Click-based CLI implementation
│   ├── api/               # FastAPI implementation
│   ├── core/              # Core business logic
│   │   ├── sow/          # SOW generation logic
│   │   ├── diagrams/     # AWS architecture diagram generation
│   │   └── pricing/      # AWS pricing calculation
│   └── utils/            # Shared utilities
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Test fixtures
├── docs/                 # Documentation
└── examples/            # Example configurations and outputs
```

## Requirements

- Python 3.10+
- uv (for dependency management)
- AWS Account (for pricing calculations)

## Installation

```bash
pip install aws-project-planning
```

or install from source:

```bash
git clone https://github.com/yourusername/aws-project-planning.git
cd aws-project-planning
pip install -e .
```

## Dependencies

- Python 3.8+
- Graphviz (required for diagram generation)

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

# Generate both configurations at once
aws-planner generate all --notes meeting_notes.txt --resources-output resources_config.yaml --diagram-output diagram_config.yaml
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

Available templates:
- `standard` - Basic text-based template
- `NMD` - Formatted Word document template with professional layout

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

```bash
aws-planner pricing estimate --resources resources_config.yaml --region us-east-1 --output estimate.txt
```

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

1. Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Run linting:
```bash
ruff check .
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

## AWS Bedrock Integration

This tool integrates with Amazon Bedrock to provide AI-powered generation of AWS configurations from natural language descriptions, meeting notes, or project transcripts. The LLM can:

1. Parse project requirements from unstructured text
2. Determine appropriate AWS services and instance types
3. Generate structured YAML configurations for both resources and architecture diagrams

To use the Bedrock integration:

1. Ensure your AWS credentials are configured with Bedrock access
2. Create a text file with project requirements or meeting notes
3. Use the `generate` commands to create configurations

Example usage:

```bash
# Generate both resources and diagram configs
aws-planner generate all --notes examples/meeting_notes.txt --resources-output generated_resources.yaml --diagram-output generated_diagram.yaml

# Generate SOW configuration and document
aws-planner generate sow --notes examples/meeting_notes.txt --sow-output generated_sow.yaml
aws-planner sow create --config generated_sow.yaml --output project_sow.docx --template NMD

# Create diagram from the generated config
aws-planner diagram create --config generated_diagram.yaml --output architecture.png

# Calculate cost estimate from the generated resources
aws-planner pricing estimate --resources generated_resources.yaml --output estimate.txt
```

### Supported Bedrock Models

The default model is `anthropic.claude-v2`, but you can specify other Bedrock models:

```bash
aws-planner generate resources --notes meeting_notes.txt --model amazon.titan-text-express-v1
```

The API endpoints also accept a `model_id` parameter for specifying the Bedrock model to use. 