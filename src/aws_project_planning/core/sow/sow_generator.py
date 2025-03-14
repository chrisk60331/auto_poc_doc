"""Statement of Work (SOW) generator module."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.shared import Inches, Pt
from jinja2 import Environment, FileSystemLoader


@dataclass
class SOWSection:
    """Represents a section in the Statement of Work."""

    title: str
    content: str
    subsections: Optional[List["SOWSection"]] = None


@dataclass
class SOWData:
    """Data structure for SOW content."""

    project_name: str
    client_name: str
    start_date: datetime
    end_date: datetime
    project_description: str
    scope: List[str]
    deliverables: List[str]
    assumptions: List[str]
    timeline: List[Dict[str, Any]]
    cost: Dict[str, Any]


class SOWGenerator:
    """Generates Statement of Work documents."""

    def __init__(self, template_dir: str = "templates/sow"):
        """Initialize SOW generator with template directory."""
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _create_document(self) -> Document:
        """Create a new Word document with basic styling."""
        doc = Document()
        
        # Set up default styles
        style = doc.styles["Normal"]
        style.font.name = "Arial"
        style.font.size = Pt(11)
        
        # Set up margins
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
        
        return doc

    def _add_header(self, doc: Document, data: SOWData) -> None:
        """Add header section to the document."""
        doc.add_heading("Statement of Work", 0)
        doc.add_paragraph(f"Project: {data.project_name}")
        doc.add_paragraph(f"Client: {data.client_name}")
        doc.add_paragraph(f"Date: {data.start_date.strftime('%B %d, %Y')}")

    def _add_section(self, doc: Document, section: SOWSection, level: int = 1) -> None:
        """Add a section to the document."""
        doc.add_heading(section.title, level)
        doc.add_paragraph(section.content)
        
        if section.subsections:
            for subsection in section.subsections:
                self._add_section(doc, subsection, level + 1)

    def generate(self, data: SOWData, template_name: str, output_path: str) -> None:
        """Generate SOW document using provided data and template."""
        # Load template
        template = self.env.get_template(f"{template_name}.j2")
        
        # Create document
        doc = self._create_document()
        
        # Add header
        self._add_header(doc, data)
        
        # Add project overview
        overview = SOWSection(
            title="Project Overview",
            content=data.project_description
        )
        self._add_section(doc, overview)
        
        # Add scope
        scope_content = "\n".join([f"- {item}" for item in data.scope])
        scope = SOWSection(
            title="Scope of Work",
            content=scope_content
        )
        self._add_section(doc, scope)
        
        # Add deliverables
        deliverables_content = "\n".join([f"- {item}" for item in data.deliverables])
        deliverables = SOWSection(
            title="Deliverables",
            content=deliverables_content
        )
        self._add_section(doc, deliverables)
        
        # Add timeline
        timeline_content = "\n".join(
            [f"- {item['phase']}: {item['duration']}" for item in data.timeline]
        )
        timeline = SOWSection(
            title="Project Timeline",
            content=timeline_content
        )
        self._add_section(doc, timeline)
        
        # Add cost
        cost_content = (
            f"Total Project Cost: ${data.cost['total']:,.2f}\n"
            f"Payment Schedule:\n"
            + "\n".join([f"- {k}: ${v:,.2f}" for k, v in data.cost['schedule'].items()])
        )
        cost = SOWSection(
            title="Cost and Payment Schedule",
            content=cost_content
        )
        self._add_section(doc, cost)
        
        # Add assumptions
        assumptions_content = "\n".join([f"- {item}" for item in data.assumptions])
        assumptions = SOWSection(
            title="Assumptions and Constraints",
            content=assumptions_content
        )
        self._add_section(doc, assumptions)
        
        # Save document
        doc.save(output_path) 