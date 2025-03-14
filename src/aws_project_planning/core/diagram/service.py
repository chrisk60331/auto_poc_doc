"""Service layer for AWS architecture diagrams."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2, ECS
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB, VPC
from diagrams.aws.storage import S3
from diagrams.aws.security import WAF
from diagrams.aws.integration import SQS
from diagrams.aws.management import Cloudwatch


class DiagramService:
    """Service for creating AWS architecture diagrams."""

    def __init__(self, default_region: str = "us-east-1"):
        """Initialize diagram service."""
        self.default_region = default_region
        self._resource_icons = {
            "ec2": EC2,
            "rds": RDS,
            "s3": S3,
            "elb": ELB,
            "vpc": VPC,
            "ecs": ECS,
            "waf": WAF,
            "sqs": SQS,
            "cloudwatch": Cloudwatch,
        }

    def load_config(self, config_path: str) -> Dict:
        """Load diagram configuration from a YAML file."""
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _create_node(self, diagram_context, node_config: Dict) -> object:
        """Create a diagram node based on configuration."""
        service = node_config.get("service", "").lower()
        name = node_config.get("name", service.upper())
        
        if service not in self._resource_icons:
            raise ValueError(f"Unsupported AWS service: {service}")
        
        return self._resource_icons[service](name)

    def _create_cluster(self, diagram_context, cluster_config: Dict) -> Tuple[Cluster, Dict[str, object]]:
        """Create a diagram cluster with nodes."""
        cluster_name = cluster_config.get("name", "Cluster")
        
        with Cluster(cluster_name):
            nodes = {}
            # Create nodes within the cluster
            for node_config in cluster_config.get("nodes", []):
                node_name = node_config.get("name")
                node = self._create_node(diagram_context, node_config)
                if node_name:
                    nodes[node_name] = node
                    
            return nodes

    def _create_connections(self, nodes: Dict[str, object], connections: List[Dict]) -> None:
        """Create connections between nodes."""
        for connection in connections:
            from_node = connection.get("from")
            to_node = connection.get("to")
            label = connection.get("label", "")
            
            if from_node in nodes and to_node in nodes:
                if label:
                    nodes[from_node] >> Edge(label=label) >> nodes[to_node]
                else:
                    nodes[from_node] >> nodes[to_node]

    def create_diagram(self, config: Union[str, Dict], output_path: str) -> str:
        """Create an AWS architecture diagram from configuration."""
        # Load configuration if a file path is provided
        if isinstance(config, str):
            config = self.load_config(config)
            
        # Extract diagram properties
        diagram_name = config.get("name", "AWS Architecture Diagram")
        diagram_direction = config.get("direction", "LR")  # LR = Left to Right
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # Create the diagram
        with Diagram(
            name=diagram_name,
            filename=Path(output_path).stem,
            outformat="png",
            direction=diagram_direction,
            show=False,
        ) as diagram:
            nodes = {}
            
            # Create standalone nodes
            for node_config in config.get("nodes", []):
                node_name = node_config.get("name")
                node = self._create_node(diagram, node_config)
                if node_name:
                    nodes[node_name] = node
            
            # Create clusters
            for cluster_config in config.get("clusters", []):
                cluster_nodes = self._create_cluster(diagram, cluster_config)
                nodes.update(cluster_nodes)
                
            # Create connections
            self._create_connections(nodes, config.get("connections", []))
            
        # Return the full path to the generated diagram
        return f"{output_path}.png"

    def generate_from_resources(self, resources_config: Union[str, Dict], output_path: str) -> str:
        """Generate a diagram from a resources configuration file."""
        # Load resources configuration if a file path is provided
        if isinstance(resources_config, str):
            with open(resources_config, "r") as f:
                resources_config = yaml.safe_load(f)
                
        # Extract resources
        resources = resources_config.get("resources", [])
        
        # Create a diagram configuration
        diagram_config = {
            "name": "AWS Architecture Diagram",
            "direction": "TB",  # Top to Bottom
            "nodes": [],
            "clusters": [],
            "connections": [],
        }
        
        # Create clusters based on resource types
        clusters = {}
        for resource in resources:
            service = resource.get("service")
            resource_type = resource.get("type")
            
            # Determine which cluster this resource belongs to
            cluster_name = resource_type.split("_")[0] if "_" in resource_type else service
            
            # Create cluster if it doesn't exist
            if cluster_name not in clusters:
                clusters[cluster_name] = {
                    "name": f"{cluster_name.capitalize()} Tier",
                    "nodes": [],
                }
                diagram_config["clusters"].append(clusters[cluster_name])
                
            # Add node to the cluster
            node_name = f"{resource_type}_{len(clusters[cluster_name]['nodes']) + 1}"
            clusters[cluster_name]["nodes"].append({
                "name": node_name,
                "service": service,
                "label": f"{resource_type} ({service})",
            })
            
            # Add connections based on likely architecture patterns
            if service == "ec2" and "web" in resource_type:
                # Connect web servers to app servers if they exist
                for app_node in clusters.get("app", {}).get("nodes", []):
                    diagram_config["connections"].append({
                        "from": node_name,
                        "to": app_node["name"],
                        "label": "HTTP/S",
                    })
                    
            if service == "ec2" and "app" in resource_type:
                # Connect app servers to databases if they exist
                for db_node in clusters.get("database", {}).get("nodes", []):
                    diagram_config["connections"].append({
                        "from": node_name,
                        "to": db_node["name"],
                        "label": "DB Connection",
                    })
                
        # Create the diagram
        return self.create_diagram(diagram_config, output_path) 