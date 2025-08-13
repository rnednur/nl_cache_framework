"""
Workflow Execution Engine for ThinkForge

This module provides native workflow execution capabilities, allowing workflows
defined in the cache to be executed step-by-step with proper dependency resolution,
error handling, and progress tracking.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from .models import Text2SQLCache, Status, TemplateType
from .tool_invoker import ToolInvoker

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Individual step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a single step execution"""
    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }


@dataclass
class ExecutionContext:
    """Context for workflow execution"""
    workflow_id: int
    run_id: str
    status: ExecutionStatus
    current_step: Optional[str] = None
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    step_outputs: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
            "variables": self.variables,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "progress": self.calculate_progress()
        }

    def calculate_progress(self) -> Dict[str, Any]:
        """Calculate execution progress"""
        total_steps = len(self.step_results)
        if total_steps == 0:
            return {"completed": 0, "total": 0, "percentage": 0}

        completed_steps = sum(1 for result in self.step_results.values() 
                            if result.status == StepStatus.COMPLETED)
        failed_steps = sum(1 for result in self.step_results.values() 
                         if result.status == StepStatus.FAILED)

        return {
            "completed": completed_steps,
            "failed": failed_steps,
            "total": total_steps,
            "percentage": (completed_steps / total_steps) * 100 if total_steps > 0 else 0
        }


class WorkflowExecutor:
    """
    Native workflow execution engine for ThinkForge.
    
    Executes workflows step-by-step with proper dependency resolution,
    parallel execution support, and comprehensive error handling.
    """

    def __init__(self, db_session: Session, tool_invoker: Optional[ToolInvoker] = None):
        """
        Initialize the workflow executor.

        Args:
            db_session: Database session for workflow and tool data
            tool_invoker: Tool invoker for step execution (created if None)
        """
        self.db_session = db_session
        self.tool_invoker = tool_invoker or ToolInvoker(db_session)
        self.active_executions: Dict[str, ExecutionContext] = {}
        self._shutdown_requested = False

    async def execute_workflow(
        self,
        workflow_id: int,
        input_variables: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> ExecutionContext:
        """
        Execute a workflow from the cache.

        Args:
            workflow_id: ID of the workflow cache entry
            input_variables: Input variables for the workflow
            progress_callback: Optional callback for execution progress

        Returns:
            ExecutionContext with results

        Raises:
            ValueError: If workflow not found or invalid
            RuntimeError: If execution fails
        """
        # Load workflow from cache
        workflow = self.db_session.query(Text2SQLCache).filter_by(id=workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow with ID {workflow_id} not found")

        # Parse workflow template
        try:
            workflow_template = json.loads(workflow.template)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid workflow template JSON: {e}")

        # Create execution context
        run_id = str(uuid.uuid4())
        context = ExecutionContext(
            workflow_id=workflow_id,
            run_id=run_id,
            status=ExecutionStatus.RUNNING,
            variables=input_variables or {},
            started_at=datetime.now(),
            progress_callback=progress_callback
        )

        # Register active execution
        self.active_executions[run_id] = context

        try:
            logger.info(f"Starting workflow execution: {workflow_id}, run: {run_id}")

            # Execute the workflow
            await self._execute_workflow_steps(workflow_template, context)

            # Mark as completed
            context.status = ExecutionStatus.COMPLETED
            context.completed_at = datetime.now()

            logger.info(f"Workflow execution completed: {workflow_id}, run: {run_id}")

        except Exception as e:
            logger.error(f"Workflow execution failed: {workflow_id}, run: {run_id}, error: {e}")
            context.status = ExecutionStatus.FAILED
            context.error_message = str(e)
            context.completed_at = datetime.now()

        finally:
            # Send final progress update
            if context.progress_callback:
                try:
                    await context.progress_callback(context.to_dict())
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

            # Clean up active execution
            self.active_executions.pop(run_id, None)

        return context

    async def _execute_workflow_steps(
        self,
        workflow_template: Dict[str, Any],
        context: ExecutionContext
    ) -> None:
        """
        Execute workflow steps with dependency resolution.

        Args:
            workflow_template: Parsed workflow template
            context: Execution context
        """
        # Extract steps and execution plan
        steps = workflow_template.get("steps", {})
        execution_plan = workflow_template.get("executionPlan", [])

        # Initialize step results
        for step_id in steps.keys():
            context.step_results[step_id] = StepResult(
                step_id=step_id,
                status=StepStatus.PENDING
            )

        # Execute according to execution plan
        if execution_plan:
            await self._execute_planned_steps(steps, execution_plan, context)
        else:
            # Fallback to dependency-based execution
            await self._execute_dependency_based_steps(steps, context)

    async def _execute_planned_steps(
        self,
        steps: Dict[str, Any],
        execution_plan: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> None:
        """
        Execute steps according to the execution plan.

        Args:
            steps: Step definitions
            execution_plan: Execution plan with groups
            context: Execution context
        """
        for group in execution_plan:
            if self._shutdown_requested or context.status == ExecutionStatus.CANCELLED:
                break

            mode = group.get("mode", "sequential")
            group_steps = group.get("steps", [])

            logger.info(f"Executing group with {len(group_steps)} steps in {mode} mode")

            if mode == "parallel":
                # Execute steps in parallel
                tasks = []
                for step_id in group_steps:
                    if step_id in steps:
                        task = self._execute_single_step(step_id, steps[step_id], context)
                        tasks.append(task)

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Execute steps sequentially
                for step_id in group_steps:
                    if step_id in steps:
                        await self._execute_single_step(step_id, steps[step_id], context)

                        # Check if execution should continue
                        if context.step_results[step_id].status == StepStatus.FAILED:
                            # Handle error based on workflow configuration
                            error_handling = steps[step_id].get("metadata", {}).get("errorHandling", "fail_fast")
                            if error_handling == "fail_fast":
                                raise RuntimeError(f"Step {step_id} failed: {context.step_results[step_id].error}")

    async def _execute_dependency_based_steps(
        self,
        steps: Dict[str, Any],
        context: ExecutionContext
    ) -> None:
        """
        Execute steps based on dependencies (topological sort).

        Args:
            steps: Step definitions
            context: Execution context
        """
        # Build dependency graph
        dependencies = {}
        for step_id, step_def in steps.items():
            dependencies[step_id] = step_def.get("dependencies", [])

        # Topological sort
        execution_order = self._topological_sort(dependencies)

        # Execute in dependency order
        for step_id in execution_order:
            if self._shutdown_requested or context.status == ExecutionStatus.CANCELLED:
                break

            if step_id in steps:
                await self._execute_single_step(step_id, steps[step_id], context)

                # Check for failure
                if context.step_results[step_id].status == StepStatus.FAILED:
                    error_handling = steps[step_id].get("metadata", {}).get("errorHandling", "fail_fast")
                    if error_handling == "fail_fast":
                        raise RuntimeError(f"Step {step_id} failed: {context.step_results[step_id].error}")

    async def _execute_single_step(
        self,
        step_id: str,
        step_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> None:
        """
        Execute a single workflow step.

        Args:
            step_id: Step identifier
            step_definition: Step definition
            context: Execution context
        """
        step_result = context.step_results[step_id]
        step_result.status = StepStatus.RUNNING
        step_result.started_at = datetime.now()
        context.current_step = step_id

        # Send progress update
        if context.progress_callback:
            try:
                await context.progress_callback(context.to_dict())
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

        try:
            logger.info(f"Executing step: {step_id}")

            # Resolve step inputs with variable substitution
            resolved_inputs = await self._resolve_step_inputs(
                step_definition.get("inputs", {}),
                context
            )

            # Execute the step using tool invoker
            template_type = step_definition.get("templateType", "api")
            template = resolved_inputs.get("template", "")

            # Execute based on template type
            output = await self.tool_invoker.invoke_tool(
                template_type=template_type,
                template=template,
                inputs=resolved_inputs,
                context_variables=context.variables
            )

            # Store step output
            output_key = step_definition.get("outputKey", f"{step_id}_result")
            context.step_outputs[output_key] = output
            context.step_outputs[step_id] = output  # Also store by step ID

            # Mark step as completed
            step_result.status = StepStatus.COMPLETED
            step_result.output = output
            step_result.completed_at = datetime.now()

            logger.info(f"Step completed successfully: {step_id}")

        except Exception as e:
            logger.error(f"Step execution failed: {step_id}, error: {e}")
            step_result.status = StepStatus.FAILED
            step_result.error = str(e)
            step_result.completed_at = datetime.now()

        # Calculate duration
        if step_result.started_at and step_result.completed_at:
            duration = step_result.completed_at - step_result.started_at
            step_result.duration_ms = int(duration.total_seconds() * 1000)

        context.current_step = None

    async def _resolve_step_inputs(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Resolve step inputs by substituting variables and step outputs.

        Args:
            inputs: Raw input definitions
            context: Execution context

        Returns:
            Resolved inputs with substitutions applied
        """
        resolved = {}

        for key, value in inputs.items():
            if isinstance(value, dict) and value.get("type") == "placeholder":
                # This is a step output reference
                source = value.get("source")
                output_key = value.get("key")

                if source in context.step_outputs:
                    resolved[key] = context.step_outputs[source]
                elif output_key in context.step_outputs:
                    resolved[key] = context.step_outputs[output_key]
                else:
                    logger.warning(f"Step output not found: {source} or {output_key}")
                    resolved[key] = None
            elif isinstance(value, str):
                # Perform variable substitution
                resolved[key] = self._substitute_variables(value, context)
            else:
                resolved[key] = value

        return resolved

    def _substitute_variables(self, template: str, context: ExecutionContext) -> str:
        """
        Substitute variables in a template string.

        Args:
            template: Template string with {variable} placeholders
            context: Execution context with variables

        Returns:
            String with variables substituted
        """
        try:
            # Simple variable substitution
            import re
            
            def replace_variable(match):
                var_name = match.group(1)
                if var_name in context.variables:
                    return str(context.variables[var_name])
                elif var_name in context.step_outputs:
                    return str(context.step_outputs[var_name])
                else:
                    logger.warning(f"Variable not found: {var_name}")
                    return match.group(0)  # Return original if not found

            return re.sub(r'\{([^}]+)\}', replace_variable, template)
        except Exception as e:
            logger.error(f"Variable substitution failed: {e}")
            return template

    def _topological_sort(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """
        Perform topological sort on dependencies.

        Args:
            dependencies: Dictionary mapping step_id to list of dependency step_ids

        Returns:
            List of step IDs in execution order

        Raises:
            ValueError: If circular dependencies detected
        """
        # Kahn's algorithm for topological sorting
        in_degree = {}
        graph = {}

        # Initialize
        for node in dependencies:
            in_degree[node] = 0
            graph[node] = []

        # Build graph and calculate in-degrees
        for node, deps in dependencies.items():
            for dep in deps:
                if dep in graph:
                    graph[dep].append(node)
                    in_degree[node] += 1

        # Find nodes with no incoming edges
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # Remove edges from this node
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for circular dependencies
        if len(result) != len(dependencies):
            raise ValueError("Circular dependencies detected in workflow")

        return result

    async def pause_execution(self, run_id: str) -> bool:
        """
        Pause a running workflow execution.

        Args:
            run_id: Execution run ID

        Returns:
            True if successfully paused, False if not found or not running
        """
        if run_id in self.active_executions:
            context = self.active_executions[run_id]
            if context.status == ExecutionStatus.RUNNING:
                context.status = ExecutionStatus.PAUSED
                logger.info(f"Workflow execution paused: {run_id}")
                return True
        return False

    async def resume_execution(self, run_id: str) -> bool:
        """
        Resume a paused workflow execution.

        Args:
            run_id: Execution run ID

        Returns:
            True if successfully resumed, False if not found or not paused
        """
        if run_id in self.active_executions:
            context = self.active_executions[run_id]
            if context.status == ExecutionStatus.PAUSED:
                context.status = ExecutionStatus.RUNNING
                logger.info(f"Workflow execution resumed: {run_id}")
                return True
        return False

    async def cancel_execution(self, run_id: str) -> bool:
        """
        Cancel a workflow execution.

        Args:
            run_id: Execution run ID

        Returns:
            True if successfully cancelled, False if not found
        """
        if run_id in self.active_executions:
            context = self.active_executions[run_id]
            context.status = ExecutionStatus.CANCELLED
            context.completed_at = datetime.now()
            logger.info(f"Workflow execution cancelled: {run_id}")
            return True
        return False

    def get_execution_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a workflow execution.

        Args:
            run_id: Execution run ID

        Returns:
            Execution status dictionary or None if not found
        """
        if run_id in self.active_executions:
            return self.active_executions[run_id].to_dict()
        return None

    def list_active_executions(self) -> List[Dict[str, Any]]:
        """
        List all active workflow executions.

        Returns:
            List of execution status dictionaries
        """
        return [context.to_dict() for context in self.active_executions.values()]

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the workflow executor.
        """
        self._shutdown_requested = True
        logger.info("Workflow executor shutdown requested")

        # Cancel all active executions
        for run_id in list(self.active_executions.keys()):
            await self.cancel_execution(run_id)

        logger.info("Workflow executor shutdown completed")