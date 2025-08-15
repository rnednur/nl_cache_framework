"""
Workflow Compiler Module for converting ReactFlow nodes/edges to executable workflow templates.

This module implements the Python equivalent of the TypeScript functions in frontend/components/ui/WorkflowTypes.ts.
"""

from enum import Enum
from typing import Dict, List, Any, Union, Optional

# Execution mode for steps
class ExecutionMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"

# Workflow template structures
class StepOutputRef:
    """Reference to output from a previous step"""
    def __init__(self, source: str, key: str):
        self.source = source  # ID of the source step
        self.key = key        # Output key from the source step
        self.type = "placeholder"  # Marker to indicate this is a placeholder

    def to_dict(self):
        return {
            "source": self.source,
            "key": self.key,
            "type": self.type
        }

class WorkflowStep:
    """A single step in the workflow"""
    def __init__(
        self,
        id: str,
        template_type: str,
        inputs: Dict[str, Any],
        dependencies: List[str],
        output_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.template_type = template_type
        self.inputs = inputs
        self.dependencies = dependencies
        self.output_key = output_key
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "id": self.id,
            "templateType": self.template_type,
            "inputs": {k: v.to_dict() if isinstance(v, StepOutputRef) else v for k, v in self.inputs.items()},
            "dependencies": self.dependencies,
            "outputKey": self.output_key,
            "metadata": self.metadata
        }

class ExecutionGroup:
    """A group of steps to be executed together"""
    def __init__(self, mode: ExecutionMode, steps: List[str]):
        self.mode = mode
        self.steps = steps

    def to_dict(self):
        return {
            "mode": self.mode,
            "steps": self.steps
        }

class WorkflowTemplate:
    """Complete workflow template"""
    def __init__(self, name: str, steps: Dict[str, WorkflowStep], execution_plan: List[ExecutionGroup]):
        self.name = name
        self.steps = steps
        self.execution_plan = execution_plan

    def to_dict(self):
        return {
            "name": self.name,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "executionPlan": [group.to_dict() for group in self.execution_plan]
        }

def compile_workflow_template(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert ReactFlow nodes/edges to a structured workflow template.
    This is the Python equivalent of buildWorkflowFromReactFlow in WorkflowTypes.ts.
    
    Args:
        nodes: List of ReactFlow nodes
        edges: List of ReactFlow edges
        
    Returns:
        Dictionary representation of the workflow template
    """
    # Initialize the workflow template
    template = {
        "name": "workflow_template",
        "steps": {},
        "executionPlan": []
    }
    
    # Map nodes to steps (excluding the start node)
    steps = {}
    for node in nodes:
        if node.get("id") == "start":
            continue
        
        data = node.get("data", {})
        template_type = data.get("originalStepType", "unknown")
        
        # Special handling for LLM steps
        inputs = {"template": data.get("template")}
        if template_type == "llm_step":
            # For LLM steps, add specific inputs for parameters
            llm_config = data.get("llmConfig", {})
            inputs.update({
                "prompt_template": llm_config.get("promptTemplate", ""),
                "input_parameters": llm_config.get("inputParameters", []),
                "output_format": llm_config.get("outputFormat", "json"),
                "expected_output": llm_config.get("expectedOutput", {}),
                "model": llm_config.get("model", "google/gemini-pro"),
                "temperature": llm_config.get("temperature", 0.3),
                "max_tokens": llm_config.get("maxTokens", 500),
                "system_prompt": llm_config.get("systemPrompt"),
                "validation_rules": llm_config.get("validationRules")
            })
        
        step = WorkflowStep(
            id=node.get("id"),
            template_type=template_type,
            inputs=inputs,
            dependencies=[],
            output_key=f"{node.get('id')}_result",
            metadata={
                "label": data.get("label"),
                "originalStepId": data.get("originalStepId"),
                "catalogType": data.get("catalogType"),
                "catalogSubtype": data.get("catalogSubtype"),
                "catalogName": data.get("catalogName"),
                "inputModifications": data.get("inputModifications", ""),
                "llmConfig": data.get("llmConfig", {}) if template_type == "llm_step" else None
            }
        )
        steps[node.get("id")] = step
    
    # Add dependencies from edges
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source == "start" or target not in steps:
            continue
        
        steps[target].dependencies.append(source)
    
    # Build execution plan
    def build_execution_plan() -> List[ExecutionGroup]:
        execution_groups = []
        processed = set()
        remaining = set(steps.keys())
        
        # Helper for creating execution groups
        def create_groups() -> bool:
            parallel_group = []
            sequential_group = []
            
            for step_id in list(remaining):
                step = steps[step_id]
                
                # Check if all dependencies are processed
                all_dependencies_processed = all(dep in processed for dep in step.dependencies)
                
                if all_dependencies_processed:
                    # Check if step can run in parallel with others in the group
                    can_run_parallel = True
                    for other_id in remaining:
                        if other_id != step_id:
                            other = steps[other_id]
                            # Check for direct dependency between steps
                            has_dependency = step_id in other.dependencies or other_id in step.dependencies
                            # Check for shared dependency that could cause conflicts
                            has_shared_dependency = any(dep in other.dependencies for dep in step.dependencies)
                            
                            if has_dependency or has_shared_dependency:
                                can_run_parallel = False
                                break
                    
                    if can_run_parallel and parallel_group:
                        parallel_group.append(step_id)
                    else:
                        sequential_group.append(step_id)
            
            # Add parallel group if it exists and has more than one step
            if len(parallel_group) > 1:
                execution_groups.append(ExecutionGroup(ExecutionMode.PARALLEL, parallel_group))
                for step_id in parallel_group:
                    processed.add(step_id)
                    remaining.remove(step_id)
            
            # Add sequential groups
            for step_id in sequential_group:
                execution_groups.append(ExecutionGroup(ExecutionMode.SEQUENTIAL, [step_id]))
                processed.add(step_id)
                remaining.remove(step_id)
            
            return len(remaining) > 0
        
        # Process nodes with no dependencies first
        no_dep_steps = [step_id for step_id, step in steps.items() if not step.dependencies]
        
        if no_dep_steps:
            # If multiple no-dependency steps, they can run in parallel
            if len(no_dep_steps) > 1:
                execution_groups.append(ExecutionGroup(ExecutionMode.PARALLEL, no_dep_steps))
            else:
                execution_groups.append(ExecutionGroup(ExecutionMode.SEQUENTIAL, no_dep_steps))
            
            for step_id in no_dep_steps:
                processed.add(step_id)
                remaining.remove(step_id)
        
        # Process remaining steps until all are processed
        while remaining:
            has_remaining = create_groups()
            if not has_remaining:
                break
        
        return execution_groups
    
    # Set the execution plan
    execution_plan = build_execution_plan()
    
    # Augment inputs with placeholders for dependencies
    for step_id, step in steps.items():
        for dep_id in step.dependencies:
            dep_step = steps[dep_id]
            placeholder_key = f"{dep_id}_output"
            
            step.inputs[placeholder_key] = StepOutputRef(
                source=dep_id,
                key=dep_step.output_key
            )
    
    # Create the final template
    workflow_template = WorkflowTemplate(
        name="workflow_template",
        steps=steps,
        execution_plan=execution_plan
    )
    
    # Return the dictionary representation
    return workflow_template.to_dict()

def serialize_workflow(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    """
    Serialize a ReactFlow graph to a workflow template JSON string.
    
    Args:
        nodes: List of ReactFlow nodes
        edges: List of ReactFlow edges
        
    Returns:
        JSON string representation of the workflow template
    """
    import json
    template = compile_workflow_template(nodes, edges)
    return json.dumps(template, indent=2)


def compile_llm_step_to_langchain(step: WorkflowStep) -> Dict[str, Any]:
    """
    Convert an LLM step to LangChain LCEL format.
    
    Args:
        step: WorkflowStep representing an LLM step
        
    Returns:
        LangChain compatible step configuration
    """
    if step.template_type != "llm_step":
        raise ValueError(f"Step {step.id} is not an LLM step")
    
    inputs = step.inputs
    metadata = step.metadata.get("llmConfig", {})
    
    # Build the LangChain prompt template
    prompt_template = inputs.get("prompt_template", "")
    input_params = inputs.get("input_parameters", [])
    
    # Create LangChain-style configuration
    langchain_step = {
        "id": step.id,
        "type": "llm_chain",
        "config": {
            "llm": {
                "model": inputs.get("model", "google/gemini-pro"),
                "temperature": inputs.get("temperature", 0.3),
                "max_tokens": inputs.get("max_tokens", 500)
            },
            "prompt": {
                "template": prompt_template,
                "input_variables": input_params
            },
            "output_parser": {
                "type": inputs.get("output_format", "json"),
                "schema": inputs.get("expected_output", {})
            }
        },
        "inputs": {param: f"{{{{ {param} }}}}" for param in input_params},
        "outputs": [step.output_key],
        "metadata": {
            "label": metadata.get("label", step.id),
            "description": f"LLM processing step: {step.id}"
        }
    }
    
    # Add system prompt if provided
    system_prompt = inputs.get("system_prompt")
    if system_prompt:
        langchain_step["config"]["system_prompt"] = system_prompt
    
    # Add validation rules if provided
    validation_rules = inputs.get("validation_rules")
    if validation_rules:
        langchain_step["config"]["validation"] = validation_rules
    
    return langchain_step


def compile_llm_step_to_langflow(step: WorkflowStep) -> Dict[str, Any]:
    """
    Convert an LLM step to Langflow node format.
    
    Args:
        step: WorkflowStep representing an LLM step
        
    Returns:
        Langflow compatible node configuration
    """
    if step.template_type != "llm_step":
        raise ValueError(f"Step {step.id} is not an LLM step")
    
    inputs = step.inputs
    metadata = step.metadata.get("llmConfig", {})
    
    # Build Langflow node
    langflow_node = {
        "id": step.id,
        "type": "LLMChain",
        "position": {"x": 100, "y": 100},  # Default position
        "data": {
            "node": {
                "template": {
                    "llm": {
                        "type": "ChatOpenAI",
                        "model": inputs.get("model", "google/gemini-pro"),
                        "temperature": inputs.get("temperature", 0.3),
                        "max_tokens": inputs.get("max_tokens", 500)
                    },
                    "prompt": {
                        "type": "PromptTemplate",
                        "template": inputs.get("prompt_template", ""),
                        "input_variables": inputs.get("input_parameters", [])
                    },
                    "output_parser": {
                        "type": inputs.get("output_format", "json").upper() + "OutputParser"
                    }
                },
                "base_classes": ["LLMChain", "Chain"],
                "name": step.id,
                "display_name": metadata.get("label", step.id),
                "description": f"LLM processing step: {step.id}"
            }
        }
    }
    
    # Add system message if provided
    system_prompt = inputs.get("system_prompt")
    if system_prompt:
        langflow_node["data"]["node"]["template"]["system_message"] = {
            "type": "SystemMessagePromptTemplate",
            "content": system_prompt
        }
    
    return langflow_node


def compile_llm_step_to_langgraph(step: WorkflowStep) -> Dict[str, Any]:
    """
    Convert an LLM step to LangGraph node format.
    
    Args:
        step: WorkflowStep representing an LLM step
        
    Returns:
        LangGraph compatible node configuration
    """
    if step.template_type != "llm_step":
        raise ValueError(f"Step {step.id} is not an LLM step")
    
    inputs = step.inputs
    metadata = step.metadata.get("llmConfig", {})
    
    # Build LangGraph node
    langgraph_node = {
        "id": step.id,
        "type": "llm_node",
        "config": {
            "llm": {
                "provider": "openai",  # Or detect from model string
                "model": inputs.get("model", "google/gemini-pro"),
                "temperature": inputs.get("temperature", 0.3),
                "max_tokens": inputs.get("max_tokens", 500)
            },
            "prompt_template": inputs.get("prompt_template", ""),
            "input_schema": {
                "type": "object",
                "properties": {
                    param: {"type": "string"} for param in inputs.get("input_parameters", [])
                },
                "required": inputs.get("input_parameters", [])
            },
            "output_schema": inputs.get("expected_output", {}),
            "output_format": inputs.get("output_format", "json")
        },
        "state": {
            "input_keys": inputs.get("input_parameters", []),
            "output_keys": [step.output_key]
        },
        "metadata": {
            "name": metadata.get("label", step.id),
            "description": f"LLM processing step: {step.id}"
        }
    }
    
    # Add system prompt if provided
    system_prompt = inputs.get("system_prompt")
    if system_prompt:
        langgraph_node["config"]["system_prompt"] = system_prompt
    
    # Add validation if provided
    validation_rules = inputs.get("validation_rules")
    if validation_rules:
        langgraph_node["config"]["validation"] = validation_rules
    
    return langgraph_node


def compile_workflow_with_llm_steps(
    nodes: List[Dict[str, Any]], 
    edges: List[Dict[str, Any]], 
    target_format: str = "generic"
) -> Dict[str, Any]:
    """
    Compile a workflow that may contain LLM steps to a specific format.
    
    Args:
        nodes: List of ReactFlow nodes
        edges: List of ReactFlow edges  
        target_format: Target format ("langchain", "langflow", "langgraph", "generic")
        
    Returns:
        Compiled workflow in the specified format
    """
    # First compile to generic format
    generic_workflow = compile_workflow_template(nodes, edges)
    
    if target_format == "generic":
        return generic_workflow
    
    # Convert LLM steps to target format
    converted_steps = {}
    for step_id, step_data in generic_workflow["steps"].items():
        # Reconstruct WorkflowStep object
        step = WorkflowStep(
            id=step_data["id"],
            template_type=step_data["templateType"],
            inputs=step_data["inputs"],
            dependencies=step_data["dependencies"],
            output_key=step_data["outputKey"],
            metadata=step_data["metadata"]
        )
        
        if step.template_type == "llm_step":
            if target_format == "langchain":
                converted_steps[step_id] = compile_llm_step_to_langchain(step)
            elif target_format == "langflow":
                converted_steps[step_id] = compile_llm_step_to_langflow(step)
            elif target_format == "langgraph":
                converted_steps[step_id] = compile_llm_step_to_langgraph(step)
            else:
                # Keep generic format for unknown targets
                converted_steps[step_id] = step_data
        else:
            # Keep non-LLM steps as-is
            converted_steps[step_id] = step_data
    
    # Update the workflow with converted steps
    result = generic_workflow.copy()
    result["steps"] = converted_steps
    result["format"] = target_format
    result["metadata"] = {
        "compiled_at": "now",  # Would use datetime in real implementation
        "target_format": target_format,
        "contains_llm_steps": any(
            step.get("templateType") == "llm_step" or step.get("type") in ["llm_node", "LLMChain"]
            for step in converted_steps.values()
        )
    }
    
    return result 