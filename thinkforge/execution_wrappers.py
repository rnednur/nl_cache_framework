"""
Execution Wrappers for ThinkForge Workflow Framework

This module provides execution wrappers that bridge ThinkForge templates with actual execution 
systems like databases, APIs, and external tools. These wrappers handle the translation from
cached templates to executable operations with proper error handling and logging.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
import json
from datetime import datetime
import traceback

from .tool_invoker import ToolInvoker
from .entity_substitution import Text2SQLEntitySubstitution
from .models import TemplateType

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Standard result container for all execution operations."""
    
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        execution_time: Optional[float] = None,
        step_id: Optional[str] = None,
        template_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.execution_time = execution_time
        self.step_id = step_id
        self.template_type = template_type
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "step_id": self.step_id,
            "template_type": self.template_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class SQLExecutionWrapper:
    """
    Wrapper for SQL execution that integrates with nl2sql framework.
    
    This wrapper enhances SQL templates through ThinkForge's caching system
    and then executes them via the nl2sql framework's database connectivity.
    """
    
    def __init__(self, nl2sql_client=None, thinkforge_controller=None):
        """
        Initialize SQL execution wrapper.
        
        Args:
            nl2sql_client: Your nl2sql framework client with database connectivity
            thinkforge_controller: ThinkForge controller for cache operations
        """
        self.nl2sql_client = nl2sql_client
        self.controller = thinkforge_controller
        self.tool_invoker = None  # Will initialize when needed with proper session
        self.entity_substitution = Text2SQLEntitySubstitution()
        
    async def execute_sql_step(
        self, 
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute a SQL step with ThinkForge enhancement.
        
        Args:
            step_config: Step configuration containing template, cache_id, etc.
            entity_values: Dynamic values for entity substitution
            context: Additional execution context (previous step results, etc.)
            
        Returns:
            ExecutionResult with query results or error information
        """
        start_time = datetime.utcnow()
        step_id = step_config.get("id", "unknown")
        
        try:
            logger.info(f"Executing SQL step: {step_id}")
            
            # Get enhanced SQL from ThinkForge cache
            sql_template = await self._get_enhanced_sql(step_config, entity_values, context)
            
            if not sql_template:
                return ExecutionResult(
                    success=False,
                    error="Failed to generate SQL template",
                    step_id=step_id,
                    template_type="sql"
                )
            
            logger.info(f"Enhanced SQL template: {sql_template[:200]}...")
            
            # Execute via nl2sql framework
            if self.nl2sql_client:
                result = await self._execute_with_nl2sql(sql_template, step_config)
            else:
                # Fallback to direct execution via ToolInvoker
                result = await self._execute_with_tool_invoker(sql_template, step_config)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ExecutionResult(
                success=True,
                data=result,
                execution_time=execution_time,
                step_id=step_id,
                template_type="sql",
                metadata={
                    "sql_template": sql_template,
                    "enhanced_by_thinkforge": True
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"SQL execution failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            return ExecutionResult(
                success=False,
                error=error_msg,
                execution_time=execution_time,
                step_id=step_id,
                template_type="sql",
                metadata={"error_traceback": traceback.format_exc()}
            )
    
    async def _get_enhanced_sql(
        self, 
        step_config: Dict[str, Any], 
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Get enhanced SQL template from ThinkForge cache."""
        
        # Option 1: Direct cache lookup by ID
        cache_id = step_config.get("cache_id")
        if cache_id and self.controller:
            cache_entry = self.controller.get_query_by_id(cache_id)
            if cache_entry:
                template = cache_entry.get("template", "")
                
                # Apply entity substitution if needed
                if entity_values and cache_entry.get("is_template"):
                    entity_replacements = cache_entry.get("entity_replacements", {})
                    if entity_replacements:
                        substituted, _ = self.entity_substitution.extract_and_replace_entities(
                            nl_query="",
                            template=template,
                            entity_replacements=entity_replacements,
                            new_entity_values=entity_values,
                            template_type="sql"
                        )
                        return substituted
                
                return template
        
        # Option 2: Use raw template from step config
        template = step_config.get("template")
        if template:
            # Apply entity substitution if values provided
            if entity_values:
                try:
                    # Simple string replacement for direct templates
                    for key, value in entity_values.items():
                        template = template.replace(f"{{{key}}}", str(value))
                except Exception as e:
                    logger.warning(f"Entity substitution failed: {e}")
            
            return template
        
        # Option 3: Generate via tool invoker (if available)
        description = step_config.get("description", "")
        if description and self.tool_invoker:
            try:
                result = await self.tool_invoker.invoke_tool(
                    template_type="sql",
                    template=description,
                    entity_values=entity_values
                )
                if result and result.get("success"):
                    return result.get("output", "")
            except Exception as e:
                logger.warning(f"Tool invoker failed: {e}")
        
        return None
    
    async def _execute_with_nl2sql(self, sql_template: str, step_config: Dict[str, Any]) -> Any:
        """Execute SQL using the nl2sql framework client."""
        
        if not hasattr(self.nl2sql_client, 'execute'):
            raise ValueError("nl2sql_client does not have execute method")
        
        # Get database connection config from step if available
        execution_config = step_config.get("execution_config", {})
        database_config = execution_config.get("database", {})
        
        # Execute with nl2sql framework
        if asyncio.iscoroutinefunction(self.nl2sql_client.execute):
            result = await self.nl2sql_client.execute(
                sql=sql_template,
                database_config=database_config
            )
        else:
            result = self.nl2sql_client.execute(
                sql=sql_template,
                database_config=database_config
            )
        
        return result
    
    async def _execute_with_tool_invoker(self, sql_template: str, step_config: Dict[str, Any]) -> Any:
        """Fallback execution using ThinkForge's ToolInvoker."""
        
        if not self.tool_invoker:
            # Return the SQL template for external execution if no tool invoker
            return {"sql": sql_template, "execution_method": "external"}
        
        execution_config = step_config.get("execution_config", {})
        
        try:
            result = await self.tool_invoker.invoke_tool(
                template_type="sql",
                template=sql_template,
                execution_config=execution_config
            )
            
            if result and result.get("success"):
                return result.get("output")
            else:
                raise Exception(f"ToolInvoker execution failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Tool invoker execution failed: {e}")
            # Return the SQL template for external execution
            return {"sql": sql_template, "execution_method": "external", "error": str(e)}


class APIExecutionWrapper:
    """
    Wrapper for API execution that handles HTTP requests with proper authentication and headers.
    """
    
    def __init__(self, thinkforge_controller=None):
        """
        Initialize API execution wrapper.
        
        Args:
            thinkforge_controller: ThinkForge controller for cache operations
        """
        self.controller = thinkforge_controller
        self.tool_invoker = None  # Will initialize when needed with proper session
        self.entity_substitution = Text2SQLEntitySubstitution()
    
    async def execute_api_step(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute an API step with proper authentication and error handling.
        
        Args:
            step_config: Step configuration containing API template, URL, etc.
            entity_values: Dynamic values for entity substitution
            context: Additional execution context
            
        Returns:
            ExecutionResult with API response or error information
        """
        start_time = datetime.utcnow()
        step_id = step_config.get("id", "unknown")
        
        try:
            logger.info(f"Executing API step: {step_id}")
            
            # Get enhanced API configuration from ThinkForge
            api_config = await self._get_enhanced_api_config(step_config, entity_values, context)
            
            if not api_config:
                return ExecutionResult(
                    success=False,
                    error="Failed to generate API configuration",
                    step_id=step_id,
                    template_type="api"
                )
            
            # Execute API call via ToolInvoker (if available)
            if self.tool_invoker:
                result = await self.tool_invoker.invoke_tool(
                    template_type="api",
                    template=api_config.get("template", ""),
                    execution_config=api_config.get("execution_config", {})
                )
            else:
                # Return API config for external execution
                result = {"success": True, "output": api_config}
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            if result and result.get("success"):
                return ExecutionResult(
                    success=True,
                    data=result.get("output"),
                    execution_time=execution_time,
                    step_id=step_id,
                    template_type="api",
                    metadata={
                        "api_config": api_config,
                        "enhanced_by_thinkforge": True
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    error=result.get("error", "API execution failed"),
                    execution_time=execution_time,
                    step_id=step_id,
                    template_type="api"
                )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"API execution failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            return ExecutionResult(
                success=False,
                error=error_msg,
                execution_time=execution_time,
                step_id=step_id,
                template_type="api",
                metadata={"error_traceback": traceback.format_exc()}
            )
    
    async def _get_enhanced_api_config(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Get enhanced API configuration from ThinkForge cache."""
        
        # Get base configuration
        cache_id = step_config.get("cache_id")
        if cache_id and self.controller:
            cache_entry = self.controller.get_query_by_id(cache_id)
            if cache_entry:
                api_config = {
                    "template": cache_entry.get("template", ""),
                    "execution_config": cache_entry.get("execution_config", {})
                }
                
                # Apply entity substitution to URL and parameters
                if entity_values and cache_entry.get("is_template"):
                    entity_replacements = cache_entry.get("entity_replacements", {})
                    if entity_replacements:
                        substituted_template, _ = self.entity_substitution.extract_and_replace_entities(
                            nl_query="",
                            template=api_config["template"],
                            entity_replacements=entity_replacements,
                            new_entity_values=entity_values,
                            template_type="api"
                        )
                        api_config["template"] = substituted_template
                
                return api_config
        
        # Fallback to step config
        return {
            "template": step_config.get("template", ""),
            "execution_config": step_config.get("execution_config", {})
        }


class ToolExecutionWrapper:
    """
    Wrapper that routes tool execution to appropriate handlers based on template type.
    """
    
    def __init__(self, thinkforge_controller=None, nl2sql_client=None):
        """
        Initialize tool execution wrapper.
        
        Args:
            thinkforge_controller: ThinkForge controller for cache operations
            nl2sql_client: nl2sql framework client for SQL execution
        """
        self.controller = thinkforge_controller
        self.tool_invoker = None  # Will initialize when needed with proper session
        
        # Initialize specialized wrappers
        self.sql_wrapper = SQLExecutionWrapper(nl2sql_client, thinkforge_controller)
        self.api_wrapper = APIExecutionWrapper(thinkforge_controller)
    
    async def execute_tool_step(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Route tool execution based on template type.
        
        Args:
            step_config: Step configuration
            entity_values: Dynamic values for entity substitution
            context: Additional execution context
            
        Returns:
            ExecutionResult from appropriate wrapper
        """
        template_type = step_config.get("template_type", "").lower()
        step_id = step_config.get("id", "unknown")
        
        logger.info(f"Routing tool execution for step {step_id} (type: {template_type})")
        
        try:
            # Route to specialized wrappers
            if template_type == "sql":
                return await self.sql_wrapper.execute_sql_step(step_config, entity_values, context)
            
            elif template_type == "api":
                return await self.api_wrapper.execute_api_step(step_config, entity_values, context)
            
            elif template_type in ["function", "script", "mcp_tool", "agent", "url", "workflow"]:
                return await self._execute_generic_tool(step_config, entity_values, context)
            
            else:
                return ExecutionResult(
                    success=False,
                    error=f"Unsupported template type: {template_type}",
                    step_id=step_id,
                    template_type=template_type
                )
                
        except Exception as e:
            error_msg = f"Tool routing failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            return ExecutionResult(
                success=False,
                error=error_msg,
                step_id=step_id,
                template_type=template_type,
                metadata={"error_traceback": traceback.format_exc()}
            )
    
    async def _execute_generic_tool(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> ExecutionResult:
        """Execute generic tools via ToolInvoker."""
        
        start_time = datetime.utcnow()
        step_id = step_config.get("id", "unknown")
        template_type = step_config.get("template_type", "")
        
        try:
            # Get template from cache or config
            template = step_config.get("template", "")
            execution_config = step_config.get("execution_config", {})
            
            # Execute via ToolInvoker (if available)
            if self.tool_invoker:
                result = await self.tool_invoker.invoke_tool(
                    template_type=template_type,
                    template=template,
                    entity_values=entity_values,
                    execution_config=execution_config
                )
            else:
                # Return template for external execution
                result = {"success": True, "output": {"template": template, "execution_config": execution_config}}
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            if result and result.get("success"):
                return ExecutionResult(
                    success=True,
                    data=result.get("output"),
                    execution_time=execution_time,
                    step_id=step_id,
                    template_type=template_type
                )
            else:
                return ExecutionResult(
                    success=False,
                    error=result.get("error", "Tool execution failed"),
                    execution_time=execution_time,
                    step_id=step_id,
                    template_type=template_type
                )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = f"Generic tool execution failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            return ExecutionResult(
                success=False,
                error=error_msg,
                execution_time=execution_time,
                step_id=step_id,
                template_type=template_type,
                metadata={"error_traceback": traceback.format_exc()}
            )


class WorkflowExecutionWrapper:
    """
    Orchestrates multi-step workflow execution with proper dependency resolution and monitoring.
    """
    
    def __init__(self, thinkforge_controller=None, nl2sql_client=None):
        """
        Initialize workflow execution wrapper.
        
        Args:
            thinkforge_controller: ThinkForge controller for cache operations
            nl2sql_client: nl2sql framework client for SQL execution
        """
        self.controller = thinkforge_controller
        self.tool_wrapper = ToolExecutionWrapper(thinkforge_controller, nl2sql_client)
        
    async def execute_workflow(
        self,
        workflow_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow with dependency resolution and progress tracking.
        
        Args:
            workflow_config: Workflow configuration with steps and dependencies
            entity_values: Global entity values for substitution
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with workflow execution results
        """
        workflow_id = workflow_config.get("id", "unknown")
        steps = workflow_config.get("steps", [])
        
        logger.info(f"Executing workflow: {workflow_id} with {len(steps)} steps")
        
        # Initialize results tracking
        results = {
            "workflow_id": workflow_id,
            "status": "running",
            "steps": [],
            "step_results": {},
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "total_execution_time": None,
            "success": False
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Build dependency graph
            dependency_graph = self._build_dependency_graph(steps)
            execution_order = self._resolve_execution_order(dependency_graph)
            
            logger.info(f"Execution order: {execution_order}")
            
            # Execute steps in dependency order
            for i, step_id in enumerate(execution_order):
                step_config = next((s for s in steps if s.get("id") == step_id), None)
                if not step_config:
                    continue
                
                # Report progress
                if progress_callback:
                    progress_callback({
                        "step": i + 1,
                        "total": len(execution_order),
                        "current_step": step_id,
                        "status": "executing"
                    })
                
                # Build context from previous step results
                context = self._build_step_context(step_config, results["step_results"])
                
                # Execute step
                step_result = await self.tool_wrapper.execute_tool_step(
                    step_config=step_config,
                    entity_values=entity_values,
                    context=context
                )
                
                # Store results
                results["step_results"][step_id] = step_result.to_dict()
                results["steps"].append(step_result.to_dict())
                
                # Check for step failure
                if not step_result.success:
                    error_msg = f"Step {step_id} failed: {step_result.error}"
                    logger.error(error_msg)
                    
                    results["status"] = "failed"
                    results["error"] = error_msg
                    results["failed_step"] = step_id
                    break
            
            # Mark as successful if all steps completed
            if results["status"] == "running":
                results["status"] = "completed"
                results["success"] = True
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            results["status"] = "failed"
            results["error"] = error_msg
            results["error_traceback"] = traceback.format_exc()
        
        finally:
            # Finalize results
            end_time = datetime.utcnow()
            results["end_time"] = end_time.isoformat()
            results["total_execution_time"] = (end_time - start_time).total_seconds()
            
            # Final progress update
            if progress_callback:
                progress_callback({
                    "step": len(execution_order),
                    "total": len(execution_order),
                    "current_step": None,
                    "status": results["status"]
                })
        
        return results
    
    def _build_dependency_graph(self, steps: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build dependency graph from workflow steps."""
        graph = {}
        
        for step in steps:
            step_id = step.get("id")
            dependencies = step.get("dependencies", [])
            
            if step_id:
                graph[step_id] = dependencies
        
        return graph
    
    def _resolve_execution_order(self, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """Resolve execution order using topological sort."""
        from collections import deque, defaultdict
        
        # Calculate in-degrees
        in_degree = defaultdict(int)
        for node in dependency_graph:
            in_degree[node] = 0
        
        for node, deps in dependency_graph.items():
            for dep in deps:
                in_degree[node] += 1
        
        # Topological sort
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            # Update in-degrees
            for other_node, deps in dependency_graph.items():
                if node in deps:
                    in_degree[other_node] -= 1
                    if in_degree[other_node] == 0:
                        queue.append(other_node)
        
        return result
    
    def _build_step_context(
        self, 
        step_config: Dict[str, Any], 
        previous_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build execution context for a step from previous step results."""
        context = {
            "previous_results": previous_results,
            "step_outputs": {}
        }
        
        # Extract outputs from dependency steps
        dependencies = step_config.get("dependencies", [])
        for dep_id in dependencies:
            if dep_id in previous_results:
                dep_result = previous_results[dep_id]
                if dep_result.get("success"):
                    context["step_outputs"][dep_id] = dep_result.get("data")
        
        return context