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
        step = WorkflowStep(
            id=node.get("id"),
            template_type=data.get("originalStepType", "unknown"),
            inputs={"template": data.get("template")},
            dependencies=[],
            output_key=f"{node.get('id')}_result",
            metadata={
                "label": data.get("label"),
                "originalStepId": data.get("originalStepId"),
                "catalogType": data.get("catalogType"),
                "catalogSubtype": data.get("catalogSubtype"),
                "catalogName": data.get("catalogName"),
                "inputModifications": data.get("inputModifications", "")
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