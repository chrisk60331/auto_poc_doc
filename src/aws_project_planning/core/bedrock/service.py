"""Service for generating AWS configurations from text using Bedrock LLM."""

import json
import os
from typing import Dict, List, Optional, Tuple, Union

import boto3
import yaml


class BedrockService:
    """Service for generating AWS configurations using Amazon Bedrock."""

    def __init__(self, model_id: str = "anthropic.claude-v2"):
        """Initialize Bedrock service with specified model.
        
        Args:
            model_id: The Bedrock model ID to use (default: Claude v2)
        """
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")
        self.model_id = model_id

    def _invoke_bedrock(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Invoke the Bedrock LLM with the given prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens in the response
            temperature: Temperature for response generation (higher = more creative)
            
        Returns:
            The LLM response text
        """
        # Different request formats based on model provider
        if self.model_id.startswith("anthropic."):
            # Claude models
            request_body = {
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": max_tokens,
                "temperature": temperature,
            }
        elif self.model_id.startswith("amazon."):
            # Amazon Titan models
            request_body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                }
            }
        else:
            raise ValueError(f"Unsupported model ID format: {self.model_id}")

        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get("body").read())
        
        # Extract text based on model provider
        if self.model_id.startswith("anthropic."):
            return response_body.get("completion", "")
        elif self.model_id.startswith("amazon."):
            return response_body.get("results")[0].get("outputText", "")
        
        raise ValueError(f"Unsupported model response format: {self.model_id}")

    def generate_sow_config(self, text: str, output_path: Optional[str] = None) -> Dict:
        """Generate Statement of Work configuration from text.
        
        Args:
            text: The meeting notes, transcript, or description text
            output_path: Optional path to save the YAML file
            
        Returns:
            Dictionary containing the generated SOW configuration
        """
        prompt = f"""
You are an AWS Solutions Architect and Project Manager. Based on the following project notes/transcript, create a YAML configuration file 
for a Statement of Work (SOW). The configuration should follow this format:

```yaml
project_name: "AWS Migration Project"
client_name: "Acme Corporation"  # Extract or infer client name from notes
project_description: "Migration of on-premises infrastructure to AWS cloud platform."  # Detailed description based on notes
scope:
  - "Assessment of current infrastructure"
  - "Design of target AWS architecture"
  - "Migration execution and testing"
  # Add more scope items as needed
deliverables:
  - "Architecture design document"
  - "Migration plan"
  - "Completed migration with test results"
  # Add more deliverables as needed
timeline:
  - phase: "Assessment"
    duration: "2 weeks"
  - phase: "Design"
    duration: "3 weeks"
  - phase: "Migration"
    duration: "6 weeks"
  # Add more phases as needed
cost:
  total: 75000  # Estimate total cost in USD
  schedule:
    "Phase 1 (Assessment)": 15000
    "Phase 2 (Design)": 25000
    "Phase 3 (Migration)": 35000
    # Distribute costs across phases
assumptions:
  - "Client will provide access to current infrastructure"
  - "Client will allocate resources for testing"
  # Add more assumptions as needed
```

Be realistic and practical in your recommendations, focusing on common AWS project patterns.
Extract any specific project details, requirements, timelines, and client information from the notes.
Make reasonable assumptions where details are not explicitly stated, but keep them realistic.
Ensure the timeline and costs are appropriate for the scope of work described.
Only return the YAML file and nothing else.

Here are the project notes/transcript:

{text}
"""
        
        # Call the Bedrock LLM
        response = self._invoke_bedrock(prompt, max_tokens=4000, temperature=0.2)
        
        # Extract YAML content from the response
        yaml_content = ""
        if "```yaml" in response:
            yaml_content = response.split("```yaml")[1].split("```")[0].strip()
        elif "```" in response:
            yaml_content = response.split("```")[1].split("```")[0].strip()
        else:
            yaml_content = response.strip()
        
        # Parse the YAML content
        try:
            config = yaml.safe_load(yaml_content)
            
            # Save to file if output path is provided
            if output_path:
                with open(output_path, "w") as f:
                    yaml.dump(config, f, default_flow_style=False)
                    
            return config
        except Exception as e:
            raise ValueError(f"Failed to parse generated YAML: {str(e)}\nGenerated content: {yaml_content}")

    def generate_resources_config(self, text: str, output_path: Optional[str] = None) -> Dict:
        """Generate AWS resources configuration from text.
        
        Args:
            text: The meeting notes, transcript, or description text
            output_path: Optional path to save the YAML file
            
        Returns:
            Dictionary containing the generated resources configuration
        """
        prompt = f"""
You are an AWS Cloud Architect. Based on the following project notes/transcript, create a YAML configuration file 
for AWS resources that would be needed. The configuration should follow this format:

```yaml
resources:
  - service: ec2  # service type (ec2, rds, s3, etc.)
    type: web_server  # purpose of the resource
    specs:
      instance_type: t3.medium  # appropriate EC2 instance type
    region: us-east-1  # appropriate AWS region
    quantity: 2  # number of instances needed
    usage_hours: 730  # monthly usage hours

  - service: rds  # another resource example
    type: database
    specs:
      instance_type: db.t3.large
      engine: mysql
      storage_gb: 100
    region: us-east-1
    quantity: 1
    usage_hours: 730
```

Choose appropriate services, instance types, quantities, and other parameters based on the requirements.
Include only supported AWS services: ec2, rds, s3, elb, ecs, cloudwatch. 
Be realistic and practical in your recommendations, focusing on common AWS architecture patterns.
Only return the YAML file and nothing else.

Here are the project notes/transcript:

{text}
"""
        
        # Call the Bedrock LLM
        response = self._invoke_bedrock(prompt, max_tokens=4000, temperature=0.2)
        
        # Extract YAML content from the response
        # The LLM might include explanation text or markdown formatting
        yaml_content = ""
        if "```yaml" in response:
            yaml_content = response.split("```yaml")[1].split("```")[0].strip()
        elif "```" in response:
            yaml_content = response.split("```")[1].split("```")[0].strip()
        else:
            yaml_content = response.strip()
        
        # Parse the YAML content
        try:
            config = yaml.safe_load(yaml_content)
            
            # Save to file if output path is provided
            if output_path:
                with open(output_path, "w") as f:
                    yaml.dump(config, f, default_flow_style=False)
                    
            return config
        except Exception as e:
            raise ValueError(f"Failed to parse generated YAML: {str(e)}\nGenerated content: {yaml_content}")

    def generate_diagram_config(self, text: str, output_path: Optional[str] = None) -> Dict:
        """Generate AWS architecture diagram configuration from text.
        
        Args:
            text: The meeting notes, transcript, or description text
            output_path: Optional path to save the YAML file
            
        Returns:
            Dictionary containing the generated diagram configuration
        """
        prompt = f"""
You are an AWS Cloud Architect. Based on the following project notes/transcript, create a YAML configuration file 
for an AWS architecture diagram. The configuration should follow this format:

```yaml
name: "Three-Tier Web Application"  # Name of the architecture
direction: "TB"  # Top to Bottom direction (TB, LR, RL, BT)

clusters:
  - name: "Web Tier"  # Logical grouping of resources
    nodes:
      - name: "web_server_1"  # Unique node identifier
        service: "ec2"  # AWS service (ec2, rds, s3, elb, etc.)
      - name: "web_server_2"
        service: "ec2"
        
  - name: "App Tier"  # Another cluster
    nodes:
      - name: "app_server_1"
        service: "ec2"
      - name: "app_server_2"
        service: "ec2"
        
connections:  # How components connect
  - from: "web_server_1"  # Source node name
    to: "app_server_1"  # Destination node name
    label: "HTTP/S"  # Optional connection label
```

Design an appropriate architecture that reflects the requirements in the notes. 
Include only supported AWS services: ec2, rds, s3, elb, vpc, ecs, waf, sqs, cloudwatch.
Create logical groupings (clusters) and show appropriate connections between components.
Only return the YAML file and nothing else.

Here are the project notes/transcript:

{text}
"""
        
        # Call the Bedrock LLM
        response = self._invoke_bedrock(prompt, max_tokens=4000, temperature=0.2)
        
        # Extract YAML content from the response
        yaml_content = ""
        if "```yaml" in response:
            yaml_content = response.split("```yaml")[1].split("```")[0].strip()
        elif "```" in response:
            yaml_content = response.split("```")[1].split("```")[0].strip()
        else:
            yaml_content = response.strip()
        
        # Parse the YAML content
        try:
            config = yaml.safe_load(yaml_content)
            
            # Save to file if output path is provided
            if output_path:
                with open(output_path, "w") as f:
                    yaml.dump(config, f, default_flow_style=False)
                    
            return config
        except Exception as e:
            raise ValueError(f"Failed to parse generated YAML: {str(e)}\nGenerated content: {yaml_content}")

    def generate_configs_from_file(self, file_path: str, 
                                   resources_output: Optional[str] = None,
                                   diagram_output: Optional[str] = None,
                                   sow_output: Optional[str] = None) -> Tuple[Dict, Dict, Optional[Dict]]:
        """Generate configs from a file.
        
        Args:
            file_path: Path to the text file containing notes/transcript
            resources_output: Optional path to save resources configuration
            diagram_output: Optional path to save diagram configuration
            sow_output: Optional path to save SOW configuration
            
        Returns:
            Tuple of (resources_config, diagram_config, sow_config) dictionaries
        """
        # Read the input file
        with open(file_path, "r") as f:
            text = f.read()
            
        # Generate configurations
        resources_config = self.generate_resources_config(text, resources_output)
        diagram_config = self.generate_diagram_config(text, diagram_output)
        
        # Generate SOW configuration if output path is provided
        sow_config = None
        if sow_output:
            sow_config = self.generate_sow_config(text, sow_output)
        
        return resources_config, diagram_config, sow_config 