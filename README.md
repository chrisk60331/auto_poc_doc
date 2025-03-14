# AWS Project Planning Tool

A comprehensive tool for creating Statement of Work (SOW), AWS Architecture Diagrams, and AWS Price Estimates.

## Features

- **Statement of Work Generation**: Create professional SOW documents from customizable templates
- **AWS Architecture Diagrams**: Generate clear and professional architecture diagrams
- **AWS Price Estimation**: Calculate cost estimates for AWS resources
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

#### Generate SOW Document

```bash
aws-planner sow create --template standard --config sow_config.yaml --output my_sow.docx
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