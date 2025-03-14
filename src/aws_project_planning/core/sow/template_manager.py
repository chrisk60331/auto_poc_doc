"""Template manager for SOW documents."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class TemplateManager:
    """Manages SOW templates and their configurations."""

    def __init__(self, template_dir: str = "templates/sow"):
        """Initialize template manager with template directory."""
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, Dict] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all available templates from the template directory."""
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True)
            self._create_default_template()

        for config_file in self.template_dir.glob("*.yaml"):
            template_name = config_file.stem
            with open(config_file, "r") as f:
                self.templates[template_name] = yaml.safe_load(f)

    def _create_default_template(self) -> None:
        """Create a default template if none exists."""
        default_template = {
            "name": "standard",
            "description": "Standard SOW template",
            "sections": [
                {
                    "name": "project_overview",
                    "title": "Project Overview",
                    "required": True,
                },
                {
                    "name": "scope",
                    "title": "Scope of Work",
                    "required": True,
                },
                {
                    "name": "deliverables",
                    "title": "Deliverables",
                    "required": True,
                },
                {
                    "name": "timeline",
                    "title": "Project Timeline",
                    "required": True,
                },
                {
                    "name": "cost",
                    "title": "Cost and Payment Schedule",
                    "required": True,
                },
                {
                    "name": "assumptions",
                    "title": "Assumptions and Constraints",
                    "required": False,
                },
            ],
        }

        # Save default template configuration
        config_path = self.template_dir / "standard.yaml"
        with open(config_path, "w") as f:
            yaml.dump(default_template, f)

        # Create default template file
        template_path = self.template_dir / "standard.j2"
        template_content = """# {{ project_name }}

## Project Overview
{{ project_description }}

## Scope of Work
{% for item in scope %}
- {{ item }}
{% endfor %}

## Deliverables
{% for item in deliverables %}
- {{ item }}
{% endfor %}

## Project Timeline
{% for phase in timeline %}
- {{ phase.name }}: {{ phase.duration }}
{% endfor %}

## Cost and Payment Schedule
Total Cost: ${{ cost.total }}

Payment Schedule:
{% for milestone, amount in cost.schedule.items() %}
- {{ milestone }}: ${{ amount }}
{% endfor %}

{% if assumptions %}
## Assumptions and Constraints
{% for item in assumptions %}
- {{ item }}
{% endfor %}
{% endif %}
"""
        with open(template_path, "w") as f:
            f.write(template_content)

    def get_template(self, template_name: str) -> Optional[Dict]:
        """Get template configuration by name."""
        return self.templates.get(template_name)

    def list_templates(self) -> List[str]:
        """List all available templates."""
        return list(self.templates.keys())

    def validate_template(self, template_name: str) -> bool:
        """Validate if a template exists and has required files."""
        if template_name not in self.templates:
            return False

        template_file = self.template_dir / f"{template_name}.j2"
        return template_file.exists()

    def create_template(self, name: str, config: Dict) -> None:
        """Create a new template with the given configuration."""
        config_path = self.template_dir / f"{name}.yaml"
        if config_path.exists():
            raise ValueError(f"Template {name} already exists")

        with open(config_path, "w") as f:
            yaml.dump(config, f)

        self.templates[name] = config 