"""FastAPI application for AWS Project Planning Tool."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from aws_project_planning import __version__
from aws_project_planning.core.bedrock.service import BedrockService
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
    """Response model for pricing estimates."""
    
    status: str = "success"
    message: str = "AWS price estimate"
    total_cost: float
    resources: List[Dict[str, Any]]
    report: str
    calculator_url: Optional[str] = None


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


class GenerateRequest(BaseModel):
    """Request model for generating configurations from notes."""
    
    notes: str = Field(..., description="Project notes or meeting transcript")
    model_id: str = Field(default="anthropic.claude-v2", description="Bedrock model ID to use")


class GenerateResourcesResponse(BaseModel):
    """Response model for generated resources configuration."""
    
    status: str
    message: str
    resources_config: Dict


class GenerateDiagramResponse(BaseModel):
    """Response model for generated diagram configuration."""
    
    status: str
    message: str
    diagram_config: Dict


class GenerateSOWResponse(BaseModel):
    """Response model for generated SOW configuration."""
    
    status: str
    message: str
    sow_config: Dict


class GenerateAllResponse(BaseModel):
    """Response model for generated configurations."""
    
    status: str
    message: str
    resources_config: Dict
    diagram_config: Dict
    sow_config: Optional[Dict] = None


class TemplateInfo(BaseModel):
    """Response model for template information."""

    name: str
    description: str
    sections: List[Dict]


class WorkflowRequest(BaseModel):
    """Request model for end-to-end workflow."""
    
    notes: str = Field(..., description="Project notes or meeting transcript")
    project_name: Optional[str] = Field(None, description="Project name (defaults to generated from notes)")
    sow_template: str = Field(default="standard", description="SOW template to use")
    model_id: str = Field(default="anthropic.claude-v2", description="Bedrock model ID to use")
    region: str = Field(default="us-east-1", description="AWS region to use")


class WorkflowResponse(BaseModel):
    """Response model for end-to-end workflow."""
    
    status: str
    message: str
    sow_path: str
    diagram_path: str
    pricing_path: str
    resources_config: Dict
    diagram_config: Dict
    sow_config: Dict
    pricing_summary: Dict


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "AWS Project Planning Tool",
        "version": __version__,
        "description": "API for creating SOW, AWS Architecture Diagrams, and Price Estimates",
        "endpoints": [
            "/sow/templates",
            "/sow/create",
            "/pricing/estimate",
            "/diagram/create", 
            "/diagram/from-resources",
            "/generate/resources",
            "/generate/diagram",
            "/generate/sow",
            "/generate/all",
            "/generate/from-file",
            "/workflow/end-to-end"
        ]
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
async def estimate_pricing(
    resources: List[ResourceConfig],
    region: str = "us-east-1",
    include_calculator_url: bool = True,
) -> PricingResponse:
    """Calculate AWS pricing estimate for resources."""
    try:
        # Initialize service
        service = PricingService(default_region=region)
        
        # Generate cost report with calculator URL if requested
        result = service.generate_cost_report(resources, include_url=include_calculator_url)
        
        # Prepare response
        response = PricingResponse(
            status="success",
            message="AWS pricing estimate generated successfully",
            total_cost=result["costs"]["total_monthly_cost"],
            resources=result["costs"]["resources"],
            report=result["report"],
        )
        
        # Add calculator URL if it was included in the result
        if "calculator_url" in result:
            response.calculator_url = result["calculator_url"]
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pricing/calculator-url")
async def get_calculator_url(
    resources: List[ResourceConfig],
    region: str = "us-east-1",
) -> Dict[str, str]:
    """Generate AWS Calculator URL for resources."""
    try:
        # Initialize service
        service = PricingService(default_region=region)
        
        # Generate calculator URL
        calculator_url = service.generate_calculator_url(resources)
        
        return {
            "status": "success",
            "message": "AWS Calculator URL generated successfully",
            "calculator_url": calculator_url,
        }
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


@app.post("/generate/resources", response_model=GenerateResourcesResponse)
async def generate_resources(request: GenerateRequest) -> GenerateResourcesResponse:
    """Generate AWS resources configuration from notes/transcript using AI."""
    try:
        # Initialize Bedrock service
        service = BedrockService(model_id=request.model_id)
        
        # Generate resources configuration
        resources_config = service.generate_resources_config(text=request.notes)
        
        return GenerateResourcesResponse(
            status="success",
            message="Resources configuration generated successfully",
            resources_config=resources_config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/diagram", response_model=GenerateDiagramResponse)
async def generate_diagram(request: GenerateRequest) -> GenerateDiagramResponse:
    """Generate AWS architecture diagram configuration from notes/transcript using AI."""
    try:
        # Initialize Bedrock service
        service = BedrockService(model_id=request.model_id)
        
        # Generate diagram configuration
        diagram_config = service.generate_diagram_config(text=request.notes)
        
        return GenerateDiagramResponse(
            status="success",
            message="Diagram configuration generated successfully",
            diagram_config=diagram_config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/sow", response_model=GenerateSOWResponse)
async def generate_sow(request: GenerateRequest) -> GenerateSOWResponse:
    """Generate Statement of Work configuration from notes/transcript using AI."""
    try:
        # Initialize Bedrock service
        service = BedrockService(model_id=request.model_id)
        
        # Generate SOW configuration
        sow_config = service.generate_sow_config(text=request.notes)
        
        return GenerateSOWResponse(
            status="success",
            message="SOW configuration generated successfully",
            sow_config=sow_config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/all", response_model=GenerateAllResponse)
async def generate_all(request: GenerateRequest) -> GenerateAllResponse:
    """Generate all configurations from notes/transcript using AI."""
    try:
        # Initialize Bedrock service
        service = BedrockService(model_id=request.model_id)
        
        # Generate resources configuration
        resources_config = service.generate_resources_config(text=request.notes)
        
        # Generate diagram configuration
        diagram_config = service.generate_diagram_config(text=request.notes)
        
        # Generate SOW configuration
        sow_config = service.generate_sow_config(text=request.notes)
        
        return GenerateAllResponse(
            status="success",
            message="Configurations generated successfully",
            resources_config=resources_config,
            diagram_config=diagram_config,
            sow_config=sow_config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/from-file")
async def generate_from_file(
    file: UploadFile = File(...),
    model_id: str = Form("anthropic.claude-v2"),
    output_type: str = Form("all"),  # 'all', 'resources', 'diagram', or 'sow'
) -> Union[GenerateAllResponse, GenerateResourcesResponse, GenerateDiagramResponse, GenerateSOWResponse]:
    """Generate configurations from an uploaded file containing notes/transcript."""
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save uploaded file
        temp_file_path = f"temp/{file.filename}"
        with open(temp_file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Initialize Bedrock service
        service = BedrockService(model_id=model_id)
        
        # Read the file content
        with open(temp_file_path, "r") as f:
            text = f.read()
        
        # Generate configurations based on output_type
        if output_type == "resources":
            resources_config = service.generate_resources_config(text=text)
            return GenerateResourcesResponse(
                status="success",
                message="Resources configuration generated successfully",
                resources_config=resources_config,
            )
        elif output_type == "diagram":
            diagram_config = service.generate_diagram_config(text=text)
            return GenerateDiagramResponse(
                status="success",
                message="Diagram configuration generated successfully",
                diagram_config=diagram_config,
            )
        elif output_type == "sow":
            sow_config = service.generate_sow_config(text=text)
            return GenerateSOWResponse(
                status="success",
                message="SOW configuration generated successfully",
                sow_config=sow_config,
            )
        else:  # 'all' is the default
            resources_config = service.generate_resources_config(text=text)
            diagram_config = service.generate_diagram_config(text=text)
            sow_config = service.generate_sow_config(text=text)
            return GenerateAllResponse(
                status="success",
                message="Configurations generated successfully",
                resources_config=resources_config,
                diagram_config=diagram_config,
                sow_config=sow_config,
            )
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/workflow/end-to-end", response_model=WorkflowResponse)
async def end_to_end_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """Execute end-to-end workflow to create all deliverables from notes."""
    try:
        # Create output directory structure
        output_dir = "output/workflows"
        configs_dir = f"{output_dir}/configs"
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(configs_dir, exist_ok=True)
        
        # Generate project name and prefix for filenames
        project_name = request.project_name or f"Project-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        safe_name = project_name.lower().replace(" ", "_")
        
        # Set paths for configs and outputs
        resources_config_path = f"{configs_dir}/{safe_name}_resources.yaml"
        diagram_config_path = f"{configs_dir}/{safe_name}_diagram.yaml"
        sow_config_path = f"{configs_dir}/{safe_name}_sow.yaml"
        
        # Set paths for final artifacts
        sow_output_path = f"{output_dir}/{safe_name}_sow.docx"
        diagram_output_path = f"{output_dir}/{safe_name}_architecture.png"
        pricing_output_path = f"{output_dir}/{safe_name}_pricing.txt"
        
        # Initialize services
        bedrock_service = BedrockService(model_id=request.model_id)
        sow_service = SOWService()
        diagram_service = DiagramService(default_region=request.region)
        pricing_service = PricingService(default_region=request.region)
        
        # Step 1: Generate all configurations
        resources_config, diagram_config, sow_config = None, None, None
        
        # Create temp file for notes
        notes_path = f"{configs_dir}/{safe_name}_notes.txt"
        with open(notes_path, "w") as f:
            f.write(request.notes)
        
        # Generate configurations
        resources_config, diagram_config, sow_config = bedrock_service.generate_configs_from_file(
            file_path=notes_path,
            resources_output=resources_config_path,
            diagram_output=diagram_config_path,
            sow_output=sow_config_path
        )
        
        # Step 2: Create SOW document
        sow_path = sow_service.create_sow(
            template_name=request.sow_template,
            output_path=sow_output_path,
            **sow_config
        )
        
        # Step 3: Create architecture diagram
        diagram_path = diagram_service.create_diagram(
            config=diagram_config_path,
            output_path=diagram_output_path
        )
        
        # Step 4: Calculate prices
        costs = pricing_service.estimate_from_config(resources_config_path)
        
        # Format and save pricing report
        report = pricing_service.format_cost_report(costs)
        with open(pricing_output_path, "w") as f:
            f.write(report)
        
        # Create pricing summary for response
        pricing_summary = {
            "total_monthly_cost": costs["total_monthly_cost"],
            "resource_count": len(costs["resources"]),
            "formatted_report_path": pricing_output_path
        }
        
        # Clean up notes file
        if os.path.exists(notes_path):
            os.remove(notes_path)
            
        return WorkflowResponse(
            status="success",
            message="End-to-end workflow completed successfully",
            sow_path=sow_path,
            diagram_path=diagram_path,
            pricing_path=pricing_output_path,
            resources_config=resources_config,
            diagram_config=diagram_config,
            sow_config=sow_config,
            pricing_summary=pricing_summary
        )
        
    except Exception as e:
        # Clean up any temp files
        raise HTTPException(status_code=500, detail=f"Error in workflow execution: {str(e)}")


@app.post("/workflow/end-to-end/file", response_model=WorkflowResponse)
async def end_to_end_workflow_from_file(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    sow_template: str = Form("standard"),
    model_id: str = Form("anthropic.claude-v2"),
    region: str = Form("us-east-1")
) -> WorkflowResponse:
    """Execute end-to-end workflow from an uploaded file containing notes."""
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save uploaded file
        temp_file_path = f"temp/{file.filename}"
        with open(temp_file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Read the file content
        with open(temp_file_path, "r") as f:
            notes = f.read()
        
        # Create workflow request
        request = WorkflowRequest(
            notes=notes,
            project_name=project_name or Path(file.filename).stem.replace("_", " ").title(),
            sow_template=sow_template,
            model_id=model_id,
            region=region
        )
        
        # Process the request using the main endpoint
        response = await end_to_end_workflow(request)
        
        return response
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Error in workflow execution: {str(e)}")
    finally:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path) 