"""
Recipe compiler for converting ThinkForge recipes to executable workflow formats.

Supports compilation to:
- LangChain LCEL (LangChain Expression Language)
- LangGraph workflow definitions
- Langflow JSON format
- Generic workflow JSON
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from .models import Text2SQLCache, TemplateType

logger = logging.getLogger(__name__)


class WorkflowFormat(str, Enum):
    """Supported workflow export formats."""
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    LANGFLOW = "langflow"
    GENERIC = "generic"


@dataclass
class CompilationResult:
    """Result of recipe compilation process."""
    success: bool
    format: WorkflowFormat
    workflow_definition: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


@dataclass
class ToolReference:
    """Reference to a tool that can be executed."""
    tool_id: int
    tool_type: str
    configuration: Dict[str, Any]
    required_inputs: List[str]
    expected_outputs: List[str]


class RecipeCompiler:
    """Compiles ThinkForge recipes into executable workflow formats."""
    
    def __init__(self, tool_resolver=None):
        """
        Initialize the recipe compiler.
        
        Args:
            tool_resolver: Optional function to resolve tool IDs to tool definitions
        """
        self.tool_resolver = tool_resolver
        self.compilation_cache = {}
    
    def compile_recipe(
        self, 
        recipe: Text2SQLCache, 
        target_format: WorkflowFormat,
        parameters: Optional[Dict[str, Any]] = None
    ) -> CompilationResult:
        """
        Compile a ThinkForge recipe to the specified workflow format.
        
        Args:
            recipe: ThinkForge recipe cache entry
            target_format: Target workflow format
            parameters: Optional parameters for compilation
            
        Returns:
            CompilationResult with workflow definition and metadata
        """
        try:
            # Validate recipe is compilable
            validation_result = self._validate_recipe(recipe)
            if not validation_result[0]:
                return CompilationResult(
                    success=False,
                    format=target_format,
                    workflow_definition={},
                    metadata={},
                    errors=validation_result[1],
                    warnings=[]
                )
            
            # Parse recipe template
            recipe_data = self._parse_recipe_template(recipe)
            if not recipe_data:
                return CompilationResult(
                    success=False,
                    format=target_format,
                    workflow_definition={},
                    metadata={},
                    errors=["Failed to parse recipe template"],
                    warnings=[]
                )
            
            # Resolve tool dependencies
            tool_references = self._resolve_tool_dependencies(recipe_data)
            
            # Compile to target format
            if target_format == WorkflowFormat.LANGCHAIN:
                result = self._compile_to_langchain(recipe_data, tool_references, parameters)
            elif target_format == WorkflowFormat.LANGGRAPH:
                result = self._compile_to_langgraph(recipe_data, tool_references, parameters)
            elif target_format == WorkflowFormat.LANGFLOW:
                result = self._compile_to_langflow(recipe_data, tool_references, parameters)
            else:  # Generic
                result = self._compile_to_generic(recipe_data, tool_references, parameters)
            
            # Add metadata
            result.metadata.update({
                'source_recipe_id': recipe.id,
                'source_recipe_name': recipe.nl_query,
                'compilation_timestamp': self._get_timestamp(),
                'thinkforge_version': '1.0.0',
                'tool_count': len(tool_references),
                'step_count': len(recipe_data.get('steps', [])),
                'complexity_level': recipe.complexity_level,
                'estimated_execution_time': recipe.execution_time_estimate
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Recipe compilation failed: {e}", exc_info=True)
            return CompilationResult(
                success=False,
                format=target_format,
                workflow_definition={},
                metadata={},
                errors=[f"Compilation error: {str(e)}"],
                warnings=[]
            )
    
    def _validate_recipe(self, recipe: Text2SQLCache) -> Tuple[bool, List[str]]:
        """Validate that recipe can be compiled."""
        errors = []
        
        # Check recipe type
        if recipe.template_type not in [TemplateType.RECIPE, TemplateType.RECIPE_STEP]:
            errors.append(f"Invalid recipe type: {recipe.template_type}")
        
        # Check template is valid JSON
        try:
            json.loads(recipe.template)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON template: {e}")
        
        # Check required fields
        if not recipe.nl_query:
            errors.append("Recipe must have a natural language description")
        
        return len(errors) == 0, errors
    
    def _parse_recipe_template(self, recipe: Text2SQLCache) -> Optional[Dict[str, Any]]:
        """Parse the recipe template JSON."""
        try:
            return json.loads(recipe.template)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse recipe template: {e}")
            return None
    
    def _resolve_tool_dependencies(self, recipe_data: Dict[str, Any]) -> List[ToolReference]:
        """Resolve tool IDs to tool definitions."""
        tool_references = []
        
        # Extract tool IDs from recipe steps
        steps = recipe_data.get('steps', [])
        for step in steps:
            tool_id = step.get('tool_id')
            if tool_id:
                # Use tool resolver if available, otherwise create placeholder
                if self.tool_resolver:
                    tool_def = self.tool_resolver(tool_id)
                    if tool_def:
                        tool_ref = ToolReference(
                            tool_id=tool_id,
                            tool_type=tool_def.get('template_type', 'unknown'),
                            configuration=tool_def.get('execution_config', {}),
                            required_inputs=self._extract_required_inputs(tool_def),
                            expected_outputs=self._extract_expected_outputs(tool_def)
                        )
                        tool_references.append(tool_ref)
                else:
                    # Create placeholder tool reference
                    tool_ref = ToolReference(
                        tool_id=tool_id,
                        tool_type='placeholder',
                        configuration={},
                        required_inputs=[],
                        expected_outputs=[]
                    )
                    tool_references.append(tool_ref)
        
        return tool_references
    
    def _compile_to_langchain(
        self, 
        recipe_data: Dict[str, Any], 
        tool_references: List[ToolReference],
        parameters: Optional[Dict[str, Any]] = None
    ) -> CompilationResult:
        """Compile recipe to LangChain LCEL format."""
        workflow_definition = {
            "type": "langchain_workflow",
            "version": "1.0",
            "metadata": {
                "name": recipe_data.get('recipe_metadata', {}).get('name', 'Unnamed Recipe'),
                "description": recipe_data.get('recipe_metadata', {}).get('description', ''),
            },
            "chains": [],
            "connections": [],
            "error_handling": self._generate_langchain_error_handling(recipe_data),
        }
        
        # Convert steps to LangChain chains
        steps = recipe_data.get('steps', [])
        for i, step in enumerate(steps):
            chain_def = {
                "id": step.get('id', f"step_{i}"),
                "name": step.get('name', f"Step {i+1}"),
                "type": self._map_step_type_to_langchain(step.get('type', 'action')),
                "tool_reference": step.get('tool_id'),
                "parameters": step.get('parameters', {}),
                "retry_config": step.get('retry_config', {}),
                "depends_on": step.get('depends_on', [])
            }
            workflow_definition["chains"].append(chain_def)
        
        # Generate connections between chains
        workflow_definition["connections"] = self._generate_langchain_connections(steps)
        
        return CompilationResult(
            success=True,
            format=WorkflowFormat.LANGCHAIN,
            workflow_definition=workflow_definition,
            metadata={},
            errors=[],
            warnings=[]
        )
    
    def _compile_to_langgraph(
        self, 
        recipe_data: Dict[str, Any], 
        tool_references: List[ToolReference],
        parameters: Optional[Dict[str, Any]] = None
    ) -> CompilationResult:
        """Compile recipe to LangGraph format."""
        workflow_definition = {
            "type": "langgraph_workflow",
            "version": "1.0",
            "graph": {
                "nodes": [],
                "edges": [],
                "start_node": None,
                "end_nodes": []
            },
            "state_schema": self._generate_langgraph_state_schema(recipe_data),
            "checkpoints": recipe_data.get('execution_config', {}).get('enable_checkpoints', False)
        }
        
        # Convert steps to LangGraph nodes
        steps = recipe_data.get('steps', [])
        start_node = None
        
        for i, step in enumerate(steps):
            node_def = {
                "id": step.get('id', f"step_{i}"),
                "name": step.get('name', f"Step {i+1}"),
                "type": "function",
                "function_name": self._generate_langgraph_function_name(step),
                "parameters": step.get('parameters', {}),
                "conditional": step.get('type') == 'conditional',
                "parallel": step.get('type') == 'parallel'
            }
            workflow_definition["graph"]["nodes"].append(node_def)
            
            # Set start node
            if not step.get('depends_on') and not start_node:
                start_node = node_def["id"]
        
        workflow_definition["graph"]["start_node"] = start_node
        
        # Generate edges from dependencies
        workflow_definition["graph"]["edges"] = self._generate_langgraph_edges(steps)
        
        return CompilationResult(
            success=True,
            format=WorkflowFormat.LANGGRAPH,
            workflow_definition=workflow_definition,
            metadata={},
            errors=[],
            warnings=[]
        )
    
    def _compile_to_langflow(
        self, 
        recipe_data: Dict[str, Any], 
        tool_references: List[ToolReference],
        parameters: Optional[Dict[str, Any]] = None
    ) -> CompilationResult:
        """Compile recipe to Langflow JSON format."""
        workflow_definition = {
            "type": "langflow_workflow",
            "version": "1.0",
            "data": {
                "nodes": [],
                "edges": [],
                "viewport": {"x": 0, "y": 0, "zoom": 1}
            },
            "description": recipe_data.get('recipe_metadata', {}).get('description', ''),
            "name": recipe_data.get('recipe_metadata', {}).get('name', 'Untitled Flow')
        }
        
        # Convert steps to Langflow nodes
        steps = recipe_data.get('steps', [])
        y_position = 0
        
        for i, step in enumerate(steps):
            node_def = {
                "id": step.get('id', f"step_{i}"),
                "type": self._map_step_type_to_langflow(step.get('type', 'action')),
                "position": {"x": 100, "y": y_position},
                "data": {
                    "type": step.get('type', 'action'),
                    "node": {
                        "base_classes": ["CustomComponent"],
                        "display_name": step.get('name', f"Step {i+1}"),
                        "description": step.get('description', ''),
                        "template": self._generate_langflow_template(step, tool_references)
                    }
                },
                "selected": False,
                "positionAbsolute": {"x": 100, "y": y_position}
            }
            workflow_definition["data"]["nodes"].append(node_def)
            y_position += 150
        
        # Generate edges
        workflow_definition["data"]["edges"] = self._generate_langflow_edges(steps)
        
        return CompilationResult(
            success=True,
            format=WorkflowFormat.LANGFLOW,
            workflow_definition=workflow_definition,
            metadata={},
            errors=[],
            warnings=[]
        )
    
    def _compile_to_generic(
        self, 
        recipe_data: Dict[str, Any], 
        tool_references: List[ToolReference],
        parameters: Optional[Dict[str, Any]] = None
    ) -> CompilationResult:
        """Compile recipe to generic workflow format."""
        workflow_definition = {
            "type": "generic_workflow",
            "version": "1.0",
            "recipe": recipe_data,
            "tools": [asdict(tool_ref) for tool_ref in tool_references],
            "execution_plan": self._generate_execution_plan(recipe_data.get('steps', [])),
            "parameters": parameters or {}
        }
        
        return CompilationResult(
            success=True,
            format=WorkflowFormat.GENERIC,
            workflow_definition=workflow_definition,
            metadata={},
            errors=[],
            warnings=[]
        )
    
    # Helper methods for specific format mappings
    
    def _map_step_type_to_langchain(self, step_type: str) -> str:
        """Map ThinkForge step type to LangChain chain type."""
        mapping = {
            'action': 'sequence',
            'condition': 'conditional',
            'loop': 'map',
            'transform': 'lambda',
            'tool': 'tool',
            'parallel': 'parallel'
        }
        return mapping.get(step_type, 'sequence')
    
    def _map_step_type_to_langflow(self, step_type: str) -> str:
        """Map ThinkForge step type to Langflow node type."""
        mapping = {
            'action': 'CustomComponent',
            'condition': 'ConditionalRouter',
            'loop': 'ListLoop',
            'transform': 'PythonFunction',
            'tool': 'Tool',
            'parallel': 'Parallel'
        }
        return mapping.get(step_type, 'CustomComponent')
    
    def _generate_execution_plan(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate execution plan with dependencies resolved."""
        execution_plan = []
        
        # Build dependency graph
        dependency_graph = {}
        for step in steps:
            step_id = step.get('id', '')
            depends_on = step.get('depends_on', [])
            dependency_graph[step_id] = depends_on
        
        # Topological sort to determine execution order
        execution_order = self._topological_sort(dependency_graph)
        
        for step_id in execution_order:
            step = next((s for s in steps if s.get('id') == step_id), None)
            if step:
                execution_plan.append({
                    'step_id': step_id,
                    'step_name': step.get('name', ''),
                    'execution_order': len(execution_plan) + 1,
                    'can_parallelize': step.get('type') == 'parallel',
                    'dependencies_resolved': True
                })
        
        return execution_plan
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph."""
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(node):
            if node in temp_visited:
                return  # Cycle detected, skip
            if node in visited:
                return
            
            temp_visited.add(node)
            for dependency in graph.get(node, []):
                visit(dependency)
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in graph:
            if node not in visited:
                visit(node)
        
        return result
    
    def _extract_required_inputs(self, tool_def: Dict[str, Any]) -> List[str]:
        """Extract required inputs from tool definition."""
        # This would parse the tool's parameter schema
        return tool_def.get('required_inputs', [])
    
    def _extract_expected_outputs(self, tool_def: Dict[str, Any]) -> List[str]:
        """Extract expected outputs from tool definition."""
        # This would parse the tool's output schema
        return tool_def.get('expected_outputs', [])
    
    def _generate_langchain_error_handling(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LangChain error handling configuration."""
        execution_config = recipe_data.get('execution_config', {})
        return {
            'fail_fast': execution_config.get('fail_fast', True),
            'timeout_seconds': execution_config.get('timeout_seconds', 300),
            'retry_attempts': 3,
            'retry_delay': 1.0
        }
    
    def _generate_langchain_connections(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate connections between LangChain chains."""
        connections = []
        for step in steps:
            step_id = step.get('id', '')
            depends_on = step.get('depends_on', [])
            for dependency in depends_on:
                connections.append({
                    'from': dependency,
                    'to': step_id,
                    'type': 'sequential'
                })
        return connections
    
    def _generate_langgraph_state_schema(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LangGraph state schema."""
        return {
            'input_data': {'type': 'dict'},
            'current_step': {'type': 'string'},
            'step_results': {'type': 'dict'},
            'error_state': {'type': 'dict'},
            'metadata': {'type': 'dict'}
        }
    
    def _generate_langgraph_function_name(self, step: Dict[str, Any]) -> str:
        """Generate function name for LangGraph node."""
        step_id = step.get('id', 'unknown')
        step_type = step.get('type', 'action')
        return f"{step_type}_{step_id}".replace('-', '_').lower()
    
    def _generate_langgraph_edges(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate edges for LangGraph."""
        edges = []
        for step in steps:
            step_id = step.get('id', '')
            depends_on = step.get('depends_on', [])
            for dependency in depends_on:
                edges.append({
                    'source': dependency,
                    'target': step_id,
                    'condition': None  # Could add conditional logic here
                })
        return edges
    
    def _generate_langflow_template(self, step: Dict[str, Any], tool_references: List[ToolReference]) -> Dict[str, Any]:
        """Generate Langflow template for step."""
        return {
            'step_id': {'type': 'str', 'value': step.get('id', '')},
            'step_name': {'type': 'str', 'value': step.get('name', '')},
            'parameters': {'type': 'dict', 'value': step.get('parameters', {})},
            'tool_id': {'type': 'int', 'value': step.get('tool_id')}
        }
    
    def _generate_langflow_edges(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate edges for Langflow."""
        edges = []
        for step in steps:
            step_id = step.get('id', '')
            depends_on = step.get('depends_on', [])
            for dependency in depends_on:
                edges.append({
                    'id': f"{dependency}-{step_id}",
                    'source': dependency,
                    'target': step_id,
                    'sourceHandle': 'output',
                    'targetHandle': 'input',
                    'type': 'default'
                })
        return edges
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        from datetime import datetime
        return datetime.utcnow().isoformat()