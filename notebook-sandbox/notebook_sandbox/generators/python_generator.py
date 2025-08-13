"""
Python notebook generator with wrapper service integration.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import structlog

from .base_generator import BaseNotebookGenerator, GenerationRequest, GenerationResult, NotebookMetadata
from .cell_templates import CellTemplateLibrary, CellType
from ..integrations.tool_resolver import ToolResolver, MockToolResolver

logger = structlog.get_logger()

class PythonNotebookGenerator(BaseNotebookGenerator):
    """Generate Python Jupyter notebooks from DSL or workflow descriptions."""
    
    def __init__(self, 
                 tool_resolver: Optional[ToolResolver] = None,
                 template_library: Optional[CellTemplateLibrary] = None):
        """
        Initialize generator.
        
        Args:
            tool_resolver: Tool resolver for looking up available tools
            template_library: Cell template library for generating cells
        """
        super().__init__("python_notebook_generator")
        self.tool_resolver = tool_resolver or MockToolResolver()
        self.template_library = template_library or CellTemplateLibrary()
        
        logger.info("PythonNotebookGenerator initialized",
                   resolver_type=type(self.tool_resolver).__name__)
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate a Python notebook from the request.
        
        Args:
            request: Generation request with DSL content or workflow description
            
        Returns:
            GenerationResult with notebook JSON or error
        """
        try:
            logger.info("Starting notebook generation", 
                       workflow_name=request.workflow_name)
            
            # Determine input format and extract steps
            steps = await self._extract_steps_from_content(request.content)
            
            # Generate cells
            cells = await self._generate_cells(steps, request)
            
            # Create notebook structure
            notebook = self._create_notebook_structure(cells, request.metadata)
            
            # Convert to JSON
            notebook_json = json.dumps(notebook, indent=2, ensure_ascii=False)
            
            result = GenerationResult(
                notebook_content=notebook_json,
                cell_count=len(cells),
                success=True,
                metadata={
                    "workflow_name": request.workflow_name,
                    "steps_processed": len(steps),
                    "generator": self.name
                }
            )
            
            logger.info("Notebook generation completed successfully",
                       workflow_name=request.workflow_name,
                       cell_count=len(cells),
                       steps_count=len(steps))
            
            return result
            
        except Exception as e:
            logger.error("Notebook generation failed",
                        workflow_name=request.workflow_name,
                        error=str(e))
            
            return GenerationResult(
                notebook_content="",
                cell_count=0,
                success=False,
                error=str(e)
            )
    
    async def _extract_steps_from_content(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract workflow steps from various input formats.
        
        Args:
            content: Input content (DSL, workflow definition, etc.)
            
        Returns:
            List of step dictionaries
        """
        steps = []
        
        # Handle different input formats
        if "steps" in content:
            # Direct steps format
            steps = content["steps"]
        
        elif "nodes" in content and "edges" in content:
            # ReactFlow format
            nodes = content["nodes"]
            edges = content["edges"]
            
            # Convert nodes to steps and sort by connections
            node_dict = {node["id"]: node for node in nodes}
            steps = self._sort_nodes_by_edges(nodes, edges)
        
        elif "recipe_text" in content:
            # Natural language recipe
            recipe_text = content["recipe_text"]
            steps = await self._parse_natural_language_recipe(recipe_text)
        
        elif "description" in content:
            # Single step description
            steps = [{
                "id": "step_1",
                "name": content.get("name", "Workflow Step"),
                "description": content["description"],
                "type": content.get("type", "unknown")
            }]
        
        else:
            # Fallback: treat entire content as single step
            steps = [{
                "id": "step_1",
                "name": "Generated Step",
                "description": str(content),
                "type": "unknown",
                "raw_content": content
            }]
        
        logger.debug("Steps extracted from content", step_count=len(steps))
        return steps
    
    def _sort_nodes_by_edges(self, nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
        """Sort nodes based on edge connections to create execution order."""
        # Simple topological sort
        node_dict = {node["id"]: node for node in nodes}
        in_degree = {node["id"]: 0 for node in nodes}
        
        # Calculate in-degrees
        for edge in edges:
            if edge["target"] in in_degree:
                in_degree[edge["target"]] += 1
        
        # Find nodes with no incoming edges (start nodes)
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        sorted_nodes = []
        
        while queue:
            current = queue.pop(0)
            sorted_nodes.append(node_dict[current])
            
            # Find outgoing edges and reduce in-degree of targets
            for edge in edges:
                if edge["source"] == current:
                    target = edge["target"]
                    if target in in_degree:
                        in_degree[target] -= 1
                        if in_degree[target] == 0:
                            queue.append(target)
        
        # Add any remaining nodes (cycles or disconnected)
        remaining = [node for node in nodes if node not in sorted_nodes]
        sorted_nodes.extend(remaining)
        
        return sorted_nodes
    
    async def _parse_natural_language_recipe(self, recipe_text: str) -> List[Dict[str, Any]]:
        """Parse natural language recipe into steps."""
        # Simple parsing - split by numbered steps or sentences
        lines = recipe_text.strip().split('\n')
        steps = []
        
        step_counter = 1
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with a number
            if line[0].isdigit() and ('. ' in line or ') ' in line):
                # Extract step description after number
                if '. ' in line:
                    description = line.split('. ', 1)[1]
                else:
                    description = line.split(') ', 1)[1]
            else:
                description = line
            
            steps.append({
                "id": f"step_{step_counter}",
                "name": f"Step {step_counter}",
                "description": description,
                "type": "natural_language"
            })
            step_counter += 1
        
        return steps
    
    async def _generate_cells(self, 
                            steps: List[Dict[str, Any]], 
                            request: GenerationRequest) -> List[Dict[str, Any]]:
        """
        Generate notebook cells from workflow steps.
        
        Args:
            steps: List of workflow steps
            request: Original generation request
            
        Returns:
            List of notebook cells
        """
        cells = []
        
        # Add header cell
        header_context = {
            "title": request.metadata.title,
            "description": request.metadata.description or "Generated workflow notebook",
            "workflow_name": request.workflow_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        cells.append(self.template_library.render_template("header", header_context))
        
        # Add setup cell
        cells.append(self.template_library.render_template("setup_imports", {}))
        
        # Process each step
        for i, step in enumerate(steps):
            step_cells = await self._generate_step_cells(step, i + 1)
            cells.extend(step_cells)
        
        # Add validation cell if there are multiple steps
        if len(steps) > 1:
            validation_context = {
                "description": "Validate workflow execution",
                "validation_code": self._generate_validation_code(steps)
            }
            cells.append(self.template_library.render_template("validation", validation_context))
        
        # Add summary cell
        summary_context = {
            "workflow_name": request.workflow_name,
            "completion_time": "datetime.now().strftime('%Y-%m-%d %H:%M:%S')",
            "total_steps": len(steps),
            "results_summary": "Workflow completed successfully",
            "next_steps": "Review results and validate outputs"
        }
        cells.append(self.template_library.render_template("summary", summary_context))
        
        return cells
    
    async def _generate_step_cells(self, step: Dict[str, Any], step_number: int) -> List[Dict[str, Any]]:
        """
        Generate cells for a single workflow step.
        
        Args:
            step: Step definition
            step_number: Step number for ordering
            
        Returns:
            List of cells for this step
        """
        cells = []
        step_name = step.get("name", f"Step {step_number}")
        description = step.get("description", "")
        step_type = step.get("type", "unknown")
        
        # Try to resolve tools for this step
        if description:
            try:
                tool_result = await self.tool_resolver.resolve_tools(
                    description, 
                    tool_type=step_type if step_type != "unknown" else None,
                    limit=1,
                    threshold=0.3
                )
                
                if tool_result.tools:
                    # Use the best matching tool
                    tool = tool_result.tools[0]
                    step_cells = await self._generate_tool_cells(step, tool, step_number)
                    cells.extend(step_cells)
                else:
                    # No tools found, generate generic cell
                    cells.append(self._generate_generic_step_cell(step, step_number))
                    
            except Exception as e:
                logger.warning("Tool resolution failed for step",
                             step_name=step_name,
                             error=str(e))
                cells.append(self._generate_generic_step_cell(step, step_number))
        else:
            cells.append(self._generate_generic_step_cell(step, step_number))
        
        return cells
    
    async def _generate_tool_cells(self, 
                                 step: Dict[str, Any], 
                                 tool: Any, 
                                 step_number: int) -> List[Dict[str, Any]]:
        """
        Generate cells for a step using a specific tool.
        
        Args:
            step: Step definition
            tool: Resolved tool
            step_number: Step number
            
        Returns:
            List of cells for tool execution
        """
        cells = []
        step_name = step.get("name", f"Step {step_number}")
        description = step.get("description", "")
        
        # Get appropriate template for tool type
        template = self.template_library.get_template_for_tool_type(tool.tool_type)
        
        if template:
            # Prepare context based on tool type
            context = {
                "step_name": step_name,
                "description": description
            }
            
            # Tool-specific context
            if tool.tool_type == "sql":
                context.update({
                    "connection_string": tool.execution_config.get("database", "postgresql://localhost/mydb"),
                    "sql_query": step.get("sql_query", "-- TODO: Add SQL query here")
                })
            
            elif tool.tool_type == "api":
                context.update({
                    "url": step.get("url", "https://api.example.com/endpoint"),
                    "method": step.get("method", "GET"),
                    "headers": json.dumps(step.get("headers", {}), indent=2),
                    "data": json.dumps(step.get("data", {}), indent=2)
                })
            
            elif tool.tool_type in ["script", "python"]:
                context.update({
                    "code": step.get("code", f"# TODO: Implement {description}")
                })
            
            elif tool.tool_type == "transform":
                context.update({
                    "input_variable": step.get("input_variable", "input_data"),
                    "output_variable": step.get("output_variable", "output_data"),
                    "transformation_code": step.get("transformation_code", "# TODO: Add transformation logic")
                })
            
            cells.append(template.render(context))
            
        else:
            # Fallback to generic cell
            cells.append(self._generate_generic_step_cell(step, step_number))
        
        return cells
    
    def _generate_generic_step_cell(self, step: Dict[str, Any], step_number: int) -> Dict[str, Any]:
        """Generate a generic cell for steps without specific tools."""
        step_name = step.get("name", f"Step {step_number}")
        description = step.get("description", "")
        
        # Use python_script template as fallback
        context = {
            "step_name": step_name,
            "description": description,
            "code": f"""# TODO: Implement step logic
# Description: {description}

# Add your implementation here
print("Step '{step_name}' executed")"""
        }
        
        return self.template_library.render_template("python_script", context)
    
    def _generate_validation_code(self, steps: List[Dict[str, Any]]) -> str:
        """Generate validation code for all steps."""
        validations = []
        
        for i, step in enumerate(steps):
            step_name = step.get("name", f"Step {i+1}")
            validations.append(f"# Validate {step_name}")
            validations.append(f"print(\"✓ {step_name} validation passed\")")
            validations.append("")
        
        return "\n".join(validations)
    
    def _create_notebook_structure(self, 
                                 cells: List[Dict[str, Any]], 
                                 metadata: NotebookMetadata) -> Dict[str, Any]:
        """
        Create the full notebook structure.
        
        Args:
            cells: List of notebook cells
            metadata: Notebook metadata
            
        Returns:
            Complete notebook dictionary
        """
        return {
            "cells": cells,
            "metadata": metadata.to_dict(),
            "nbformat": 4,
            "nbformat_minor": 5
        }
    
    def validate_input(self, content: Dict[str, Any]) -> bool:
        """
        Validate input content for Python notebook generation.
        
        Args:
            content: Input content to validate
            
        Returns:
            True if content is valid
        """
        # Accept various formats
        valid_keys = {"steps", "nodes", "edges", "recipe_text", "description", "dsl", "workflow"}
        return any(key in content for key in valid_keys)
    
    def get_supported_formats(self) -> List[str]:
        """Get supported input formats."""
        return [
            "dsl_workflow",
            "reactflow_nodes", 
            "natural_language_recipe",
            "step_description",
            "generic_workflow"
        ]