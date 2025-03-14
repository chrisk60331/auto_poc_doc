"""Service layer for SOW generation."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .sow_generator import SOWData, SOWGenerator
from .template_manager import TemplateManager


class SOWService:
    """Service for managing SOW generation."""

    def __init__(self, template_dir: str = "templates/sow"):
        """Initialize SOW service."""
        self.template_manager = TemplateManager(template_dir)
        self.generator = SOWGenerator(template_dir)

    def create_sow(
        self,
        template_name: str,
        output_path: str,
        project_name: str,
        client_name: str,
        project_description: str,
        scope: List[str],
        deliverables: List[str],
        timeline: List[Dict[str, Any]],
        cost: Dict[str, Any],
        assumptions: List[str] = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> str:
        """Create a new SOW document."""
        # Validate template
        if not self.template_manager.validate_template(template_name):
            raise ValueError(f"Template {template_name} not found or invalid")

        # Set default dates if not provided
        start_date = start_date or datetime.now()
        end_date = end_date or datetime.now()
        assumptions = assumptions or []

        # Create SOW data
        sow_data = SOWData(
            project_name=project_name,
            client_name=client_name,
            start_date=start_date,
            end_date=end_date,
            project_description=project_description,
            scope=scope,
            deliverables=deliverables,
            assumptions=assumptions,
            timeline=timeline,
            cost=cost,
        )

        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate SOW
        self.generator.generate(sow_data, template_name, str(output_path))
        return str(output_path)

    def list_templates(self) -> List[str]:
        """List available templates."""
        return self.template_manager.list_templates()

    def get_template_info(self, template_name: str) -> Dict:
        """Get template information."""
        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"Template {template_name} not found")
        return template

    def create_template(self, name: str, config: Dict) -> None:
        """Create a new template."""
        self.template_manager.create_template(name, config) 