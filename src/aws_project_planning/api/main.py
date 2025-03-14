"""FastAPI application for AWS Project Planning Tool."""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from aws_project_planning import __version__
from aws_project_planning.core.diagram.service import DiagramService
from aws_project_planning.core.pricing.service import PricingService
from aws_project_planning.core.sow.service import SOWService

app = FastAPI(
    title="AWS Project Planning Tool",
    description="API for creating SOW, AWS Architecture Diagrams, and Price Estimates",
    version=__version__,
)


class TimelineItem(BaseModel):
    """Timeline item in the SOW."""

    phase: str
    duration: str


class CostSchedule(BaseModel):
    """Cost schedule in the SOW."""

    total: float
    schedule: Dict[str, float]


class SOWRequest(BaseModel):
    """Request model for SOW creation."""

    template_name: str = Field(..., description="Name of the template to use")
    project_name: str = Field(..., description="Name of the project")
    client_name: str = Field(..., description="Name of the client")
    project_description: str = Field(..., description="Detailed project description")
    scope: List[str] = Field(..., description="List of scope items")
    deliverables: List[str] = Field(..., description="List of deliverables")
    timeline: List[TimelineItem] = Field(..., description="Project timeline")
    cost: CostSchedule = Field(..., description="Project cost and payment schedule")
    assumptions: Optional[List[str]] = Field(default=None, description="List of assumptions")
    start_date: Optional[datetime] = Field(default=None, description="Project start date")
    end_date: Optional[datetime] = Field(default=None, description="Project end date")


class ResourceSpecs(BaseModel):
    """Specifications for an AWS resource."""

    instance_type: Optional[str] = None
    engine: Optional[str] = None
    storage_gb: Optional[int] = None
    storage_class: Optional[str] = None


class ResourceConfig(BaseModel):
    """Configuration for an AWS resource."""

    service: str = Field(..., description="AWS service (e.g., ec2, rds, s3)")
    type: str = Field(..., description="Resource type or purpose")
    specs: ResourceSpecs = Field(..., description="Resource specifications")
    region: str = Field(default="us-east-1", description="AWS region")
    quantity: int = Field(default=1, description="Number of resources")
    usage_hours: float = Field(default=730.0, description="Monthly usage hours")


class PricingRequest(BaseModel):
    """Request model for pricing estimation."""

    resources: List[ResourceConfig] = Field(..., description="List of AWS resources")
    default_region: str = Field(default="us-east-1", description="Default AWS region")


class ResourceCostDetails(BaseModel):
    """Cost details for a single resource."""

    type: str
    monthly_cost: float
    details: Dict[str, Any]


class PricingResponse(BaseModel):
    """Response model for pricing estimation."""

    total_monthly_cost: float
    resources: List[ResourceCostDetails]
    formatted_report: str


class NodeConfig(BaseModel):
    """Configuration for a diagram node."""
    
    name: str
    service: str
    label: Optional[str] = None


class ClusterConfig(BaseModel):
    """Configuration for a diagram cluster."""
    
    name: str
    nodes: List[NodeConfig]


class ConnectionConfig(BaseModel):
    """Configuration for a connection between nodes."""
    
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    label: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class DiagramRequest(BaseModel):
    """Request model for diagram creation."""

    name: str = Field(..., description="Name of the diagram")
    direction: str = Field(default="TB", description="Direction of the diagram (TB, LR, RL, BT)")
    nodes: Optional[List[NodeConfig]] = Field(default=[], description="List of standalone nodes")
    clusters: Optional[List[ClusterConfig]] = Field(default=[], description="List of node clusters")
    connections: Optional[List[ConnectionConfig]] = Field(default=[], description="List of connections between nodes")


class DiagramResponse(BaseModel):
    """Response model for diagram creation."""

    status: str
    message: str
    file_path: str


class TemplateInfo(BaseModel):
    """Response model for template information."""

    name: str
    description: str
    sections: List[Dict]


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "AWS Project Planning Tool",
        "version": __version__,
        "description": "API for creating SOW, AWS Architecture Diagrams, and Price Estimates",
    }


@app.get("/sow/templates")
async def list_templates() -> List[TemplateInfo]:
    """List available SOW templates."""
    service = SOWService()
    templates = []
    for template_name in service.list_templates():
        template_info = service.get_template_info(template_name)
        templates.append(TemplateInfo(**template_info))
    return templates


@app.post("/sow/create")
async def create_sow(request: SOWRequest):
    """Create a new Statement of Work document."""
    try:
        service = SOWService()
        output_path = service.create_sow(
            template_name=request.template_name,
            output_path=f"output/sow/{request.project_name.lower().replace(' ', '_')}.docx",
            project_name=request.project_name,
            client_name=request.client_name,
            project_description=request.project_description,
            scope=request.scope,
            deliverables=request.deliverables,
            timeline=[item.dict() for item in request.timeline],
            cost=request.cost.dict(),
            assumptions=request.assumptions,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        return {
            "status": "success",
            "message": f"SOW created successfully",
            "file_path": output_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pricing/estimate")
async def estimate_pricing(request: PricingRequest) -> PricingResponse:
    """Generate AWS price estimate."""
    try:
        service = PricingService(default_region=request.default_region)
        
        # Convert Pydantic models to ResourceConfig objects
        resources = [
            ResourceConfig(
                service=r.service,
                resource_type=r.type,
                specs=r.specs.dict(exclude_none=True),
                region=r.region,
                quantity=r.quantity,
                usage_hours=r.usage_hours,
            )
            for r in request.resources
        ]
        
        # Calculate costs
        costs = service.calculate_costs(resources)
        
        # Generate formatted report
        formatted_report = service.format_cost_report(costs)
        
        return PricingResponse(
            total_monthly_cost=costs["total_monthly_cost"],
            resources=[ResourceCostDetails(**r) for r in costs["resources"]],
            formatted_report=formatted_report,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/diagram/create")
async def create_diagram(request: DiagramRequest) -> DiagramResponse:
    """Create a new AWS architecture diagram."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs("output/diagrams", exist_ok=True)
        
        # Initialize service
        service = DiagramService()
        
        # Convert Pydantic model to dictionary for the service
        diagram_config = {
            "name": request.name,
            "direction": request.direction,
            "nodes": [node.dict(exclude_none=True) for node in request.nodes],
            "clusters": [cluster.dict(exclude_none=True) for cluster in request.clusters],
            "connections": [conn.dict(by_alias=True, exclude_none=True) for conn in request.connections],
        }
        
        # Generate unique filename based on diagram name
        filename = f"output/diagrams/{request.name.lower().replace(' ', '_')}"
        
        # Create diagram
        diagram_path = service.create_diagram(diagram_config, filename)
        
        return DiagramResponse(
            status="success",
            message="AWS architecture diagram created successfully",
            file_path=diagram_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/diagram/from-resources")
async def create_diagram_from_resources(
    resources: List[ResourceConfig],
    name: str = "AWS Architecture",
    region: str = "us-east-1",
) -> DiagramResponse:
    """Generate AWS architecture diagram from resources configuration."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs("output/diagrams", exist_ok=True)
        
        # Initialize service
        service = DiagramService(default_region=region)
        
        # Prepare resources configuration
        resources_config = {
            "resources": [
                {
                    "service": r.service,
                    "type": r.type,
                    "specs": r.specs.dict(exclude_none=True),
                    "region": r.region,
                    "quantity": r.quantity,
                }
                for r in resources
            ]
        }
        
        # Generate unique filename based on diagram name
        filename = f"output/diagrams/{name.lower().replace(' ', '_')}"
        
        # Create diagram from resources
        diagram_path = service.generate_from_resources(resources_config, filename)
        
        return DiagramResponse(
            status="success",
            message="AWS architecture diagram created successfully from resources",
            file_path=diagram_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 