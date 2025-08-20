"""
Step Execution Templates for ThinkForge Framework

This module provides standardized execution templates for different step types,
wrapping them with proper API handlers, error handling, and monitoring.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import traceback

from .execution_wrappers import (
    SQLExecutionWrapper,
    APIExecutionWrapper, 
    ToolExecutionWrapper,
    ExecutionResult
)
from .execution_config import get_config_manager
from .models import TemplateType
from .llm_step_processor import LLMStepProcessor, LLMStepResult

logger = logging.getLogger(__name__)


class StepTemplate:
    """Base class for step execution templates."""
    
    def __init__(self, template_type: str):
        self.template_type = template_type
        self.config_manager = get_config_manager()
    
    async def execute(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> ExecutionResult:
        """Execute the step with proper error handling and monitoring."""
        
        step_id = step_config.get("id", "unknown")
        start_time = datetime.utcnow()
        
        try:
            # Report start
            if progress_callback:
                progress_callback({
                    "step_id": step_id,
                    "status": "starting",
                    "timestamp": start_time.isoformat()
                })
            
            # Merge execution configuration
            execution_config = self._merge_execution_config(step_config, context)
            
            # Execute the step
            result = await self._execute_impl(step_config, entity_values, context, execution_config)
            
            # Store result in DuckDB if context supports it and execution was successful
            if result.success and context and hasattr(context, 'store_step_output'):
                try:
                    execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    table_name = context.store_step_output(
                        step_id=step_id,
                        data=result.data,
                        template_type=self.template_type,
                        execution_time_ms=execution_time_ms,
                        metadata=result.metadata
                    )
                    
                    # Add table info to result metadata
                    result.metadata.update({
                        "duckdb_table": table_name,
                        "persisted": True
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to persist step output for {step_id}: {e}")
                    result.metadata.update({
                        "persistence_error": str(e),
                        "persisted": False
                    })
            
            # Report completion
            if progress_callback:
                progress_callback({
                    "step_id": step_id,
                    "status": "completed" if result.success else "failed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration": (datetime.utcnow() - start_time).total_seconds()
                })
            
            return result
            
        except Exception as e:
            error_msg = f"Step execution failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            if progress_callback:
                progress_callback({
                    "step_id": step_id,
                    "status": "error",
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return ExecutionResult(
                success=False,
                error=error_msg,
                step_id=step_id,
                template_type=self.template_type,
                metadata={"error_traceback": traceback.format_exc()}
            )
    
    def _merge_execution_config(
        self, 
        step_config: Dict[str, Any], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge execution configuration from various sources."""
        
        base_config = step_config.get("execution_config", {})
        workflow_id = context.get("workflow_id") if context else None
        step_id = step_config.get("id")
        
        return self.config_manager.merge_execution_config(
            base_config=base_config,
            template_type=self.template_type,
            workflow_id=workflow_id,
            step_id=step_id
        )
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Implementation-specific execution logic (to be overridden)."""
        raise NotImplementedError("Subclasses must implement _execute_impl")


class SQLStepTemplate(StepTemplate):
    """Execution template for SQL steps."""
    
    def __init__(self, nl2sql_client=None):
        super().__init__("sql")
        self.sql_wrapper = SQLExecutionWrapper(nl2sql_client)
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute SQL step with database connectivity."""
        
        # Update step config with merged execution config
        enhanced_step_config = step_config.copy()
        enhanced_step_config["execution_config"] = execution_config
        
        # Execute via SQL wrapper
        result = await self.sql_wrapper.execute_sql_step(
            enhanced_step_config, entity_values, context
        )
        
        # Add SQL-specific metadata
        if result.success and result.data:
            result.metadata.update({
                "row_count": len(result.data) if isinstance(result.data, list) else 1,
                "execution_method": "sql_wrapper"
            })
        
        return result


class APIStepTemplate(StepTemplate):
    """Execution template for API steps."""
    
    def __init__(self):
        super().__init__("api")
        self.api_wrapper = APIExecutionWrapper()
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute API step with HTTP client."""
        
        # Update step config with merged execution config
        enhanced_step_config = step_config.copy()
        enhanced_step_config["execution_config"] = execution_config
        
        # Execute via API wrapper
        result = await self.api_wrapper.execute_api_step(
            enhanced_step_config, entity_values, context
        )
        
        # Add API-specific metadata
        if result.success:
            result.metadata.update({
                "api_endpoint": execution_config.get("base_url", ""),
                "execution_method": "api_wrapper"
            })
        
        return result


class FunctionStepTemplate(StepTemplate):
    """Execution template for function/code steps."""
    
    def __init__(self):
        super().__init__("function")
        self.tool_wrapper = None  # Will initialize when needed
    
    def _get_tool_wrapper(self):
        """Get tool wrapper, creating if needed."""
        if self.tool_wrapper is None:
            self.tool_wrapper = ToolExecutionWrapper()
        return self.tool_wrapper
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute function step with code execution."""
        
        # Validate code safety (basic checks)
        template = step_config.get("template", "")
        if not self._is_safe_code(template):
            return ExecutionResult(
                success=False,
                error="Code contains potentially unsafe operations",
                step_id=step_config.get("id"),
                template_type=self.template_type
            )
        
        # Update step config with merged execution config
        enhanced_step_config = step_config.copy()
        enhanced_step_config["execution_config"] = execution_config
        
        # Execute via tool wrapper
        tool_wrapper = self._get_tool_wrapper()
        result = await tool_wrapper.execute_tool_step(
            enhanced_step_config, entity_values, context
        )
        
        # Add function-specific metadata
        if result.success:
            result.metadata.update({
                "code_length": len(template),
                "execution_method": "function_wrapper"
            })
        
        return result
    
    def _is_safe_code(self, code: str) -> bool:
        """Basic safety check for code execution."""
        dangerous_patterns = [
            "import os", "import subprocess", "import sys",
            "__import__", "eval(", "exec(", "open(",
            "file(", "input(", "raw_input("
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                logger.warning(f"Potentially unsafe code pattern detected: {pattern}")
                return False
        
        return True


class ScriptStepTemplate(StepTemplate):
    """Execution template for script steps."""
    
    def __init__(self):
        super().__init__("script")
        self.tool_wrapper = None  # Will initialize when needed
    
    def _get_tool_wrapper(self):
        """Get tool wrapper, creating if needed."""
        if self.tool_wrapper is None:
            self.tool_wrapper = ToolExecutionWrapper()
        return self.tool_wrapper
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute script step with shell/python execution."""
        
        # Update step config with merged execution config
        enhanced_step_config = step_config.copy()
        enhanced_step_config["execution_config"] = execution_config
        
        # Set resource limits for script execution
        tool_config = execution_config.get("tool", {})
        if "resource_limits" not in tool_config:
            tool_config["resource_limits"] = {
                "max_memory": "512MB",
                "max_cpu_time": 300,  # 5 minutes
                "max_output_size": "10MB"
            }
        
        # Execute via tool wrapper
        tool_wrapper = self._get_tool_wrapper()
        result = await tool_wrapper.execute_tool_step(
            enhanced_step_config, entity_values, context
        )
        
        # Add script-specific metadata
        if result.success:
            result.metadata.update({
                "script_type": self._detect_script_type(step_config.get("template", "")),
                "execution_method": "script_wrapper"
            })
        
        return result
    
    def _detect_script_type(self, script: str) -> str:
        """Detect the type of script based on content."""
        script_lower = script.lower().strip()
        
        if script_lower.startswith("#!/bin/bash") or script_lower.startswith("#!/bin/sh"):
            return "bash"
        elif script_lower.startswith("#!/usr/bin/env python") or "import " in script_lower:
            return "python"
        elif script_lower.startswith("#!/usr/bin/env node") or "require(" in script_lower:
            return "node"
        else:
            return "unknown"


class WorkflowStepTemplate(StepTemplate):
    """Execution template for nested workflow steps."""
    
    def __init__(self):
        super().__init__("workflow")
        from .execution_wrappers import WorkflowExecutionWrapper
        self.workflow_wrapper = WorkflowExecutionWrapper()
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute nested workflow step."""
        
        try:
            # Parse workflow template
            template = step_config.get("template", "")
            if isinstance(template, str):
                workflow_config = json.loads(template)
            else:
                workflow_config = template
            
            # Execute nested workflow
            workflow_result = await self.workflow_wrapper.execute_workflow(
                workflow_config=workflow_config,
                entity_values=entity_values
            )
            
            return ExecutionResult(
                success=workflow_result.get("success", False),
                data=workflow_result,
                step_id=step_config.get("id"),
                template_type=self.template_type,
                metadata={
                    "nested_workflow": True,
                    "step_count": len(workflow_result.get("steps", [])),
                    "execution_method": "workflow_wrapper"
                }
            )
            
        except json.JSONDecodeError as e:
            return ExecutionResult(
                success=False,
                error=f"Invalid workflow JSON: {str(e)}",
                step_id=step_config.get("id"),
                template_type=self.template_type
            )


class MCPToolStepTemplate(StepTemplate):
    """Execution template for MCP (Model Context Protocol) tool steps."""
    
    def __init__(self):
        super().__init__("mcp_tool")
        self.tool_wrapper = None  # Will initialize when needed
    
    def _get_tool_wrapper(self):
        """Get tool wrapper, creating if needed."""
        if self.tool_wrapper is None:
            self.tool_wrapper = ToolExecutionWrapper()
        return self.tool_wrapper
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute MCP tool step."""
        
        # Update step config with merged execution config
        enhanced_step_config = step_config.copy()
        enhanced_step_config["execution_config"] = execution_config
        
        # Validate MCP tool configuration
        if not self._validate_mcp_config(execution_config):
            return ExecutionResult(
                success=False,
                error="Invalid MCP tool configuration",
                step_id=step_config.get("id"),
                template_type=self.template_type
            )
        
        # Execute via tool wrapper
        tool_wrapper = self._get_tool_wrapper()
        result = await tool_wrapper.execute_tool_step(
            enhanced_step_config, entity_values, context
        )
        
        # Add MCP-specific metadata
        if result.success:
            result.metadata.update({
                "mcp_tool_name": execution_config.get("tool_name", "unknown"),
                "execution_method": "mcp_wrapper"
            })
        
        return result
    
    def _validate_mcp_config(self, config: Dict[str, Any]) -> bool:
        """Validate MCP tool configuration."""
        required_fields = ["tool_name", "mcp_server_url"]
        return all(field in config for field in required_fields)


class LLMStepTemplate(StepTemplate):
    """Execution template for LLM-powered steps."""
    
    def __init__(self, llm_service=None):
        super().__init__("llm_step")
        self.llm_processor = LLMStepProcessor(llm_service)
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute LLM step with AI processing."""
        
        try:
            # Extract LLM step template from step config
            llm_template = self._build_llm_template(step_config, execution_config)
            
            # Prepare input values (merge entity_values and context outputs)
            input_values = self._prepare_input_values(
                step_config, entity_values, context
            )
            
            # Execute the LLM step
            llm_result: LLMStepResult = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.llm_processor.execute_llm_step,
                llm_template,
                input_values
            )
            
            # Convert LLMStepResult to ExecutionResult
            return self._convert_llm_result(llm_result, step_config)
            
        except Exception as e:
            logger.error(f"LLM step execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                error=f"LLM step execution error: {str(e)}",
                step_id=step_config.get("id"),
                template_type=self.template_type,
                metadata={"error_type": "llm_execution_error"}
            )
    
    def _build_llm_template(
        self, 
        step_config: Dict[str, Any], 
        execution_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build LLM step template from step configuration."""
        
        # Get LLM config from step metadata or inputs
        metadata = step_config.get("metadata", {})
        llm_config = metadata.get("llmConfig", {})
        inputs = step_config.get("inputs", {})
        
        # Build step configuration
        step_template = {
            "step_config": {
                "prompt_template": inputs.get("prompt_template", llm_config.get("promptTemplate", "")),
                "input_parameters": inputs.get("input_parameters", llm_config.get("inputParameters", [])),
                "output_format": inputs.get("output_format", llm_config.get("outputFormat", "json")),
                "expected_output": inputs.get("expected_output", llm_config.get("expectedOutput", {})),
                "model": execution_config.get("model", inputs.get("model", llm_config.get("model", "google/gemini-pro"))),
                "temperature": execution_config.get("temperature", inputs.get("temperature", llm_config.get("temperature", 0.3))),
                "max_tokens": execution_config.get("max_tokens", inputs.get("max_tokens", llm_config.get("maxTokens", 500))),
                "system_prompt": inputs.get("system_prompt", llm_config.get("systemPrompt"))
            }
        }
        
        # Add validation rules if present
        validation_rules = inputs.get("validation_rules", llm_config.get("validationRules"))
        if validation_rules:
            step_template["validation_rules"] = validation_rules
        
        # Add examples if present
        examples = llm_config.get("examples", [])
        if examples:
            step_template["examples"] = examples
        
        return step_template
    
    def _prepare_input_values(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare input values for LLM step execution."""
        
        input_values = {}
        
        # Add entity values
        if entity_values:
            input_values.update(entity_values)
        
        # Add outputs from previous steps
        if context:
            step_outputs = context.get("step_outputs", {})
            input_values.update(step_outputs)
        
        # Handle step output references from inputs
        inputs = step_config.get("inputs", {})
        for key, value in inputs.items():
            if isinstance(value, dict) and value.get("type") == "placeholder":
                # This is a reference to another step's output
                source_step = value.get("source")
                output_key = value.get("key")
                
                if context and step_outputs and source_step in step_outputs:
                    step_result = step_outputs[source_step]
                    if isinstance(step_result, dict) and output_key in step_result:
                        input_values[key] = step_result[output_key]
                    elif output_key == f"{source_step}_result":
                        input_values[key] = step_result
                        
        return input_values
    
    def _convert_llm_result(
        self, 
        llm_result: LLMStepResult, 
        step_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Convert LLMStepResult to ExecutionResult."""
        
        metadata = {
            "llm_execution": True,
            "raw_response": llm_result.raw_response,
            "validation_passed": llm_result.validation_passed,
            "execution_method": "llm_processor"
        }
        
        # Add execution metadata if available
        if llm_result.execution_metadata:
            metadata.update(llm_result.execution_metadata)
        
        return ExecutionResult(
            success=llm_result.success,
            data=llm_result.output,
            error=llm_result.error_message,
            step_id=step_config.get("id"),
            template_type=self.template_type,
            metadata=metadata
        )


class DuckDBStepTemplate(StepTemplate):
    """Execution template for SQL data transformation steps using DuckDB."""
    
    def __init__(self):
        super().__init__("duckdb_sql")
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute SQL transformation step using DuckDB."""
        
        step_id = step_config.get("id", "unknown")
        
        try:
            # Get SQL query from step config
            sql_query = step_config.get("inputs", {}).get("query") or step_config.get("template", "")
            
            if not sql_query:
                return ExecutionResult(
                    success=False,
                    error="No SQL query provided",
                    step_id=step_id,
                    template_type=self.template_type
                )
            
            # Check if context supports SQL execution
            if not context or not hasattr(context, 'execute_sql'):
                return ExecutionResult(
                    success=False,
                    error="Context does not support SQL execution (DuckDB not available)",
                    step_id=step_id,
                    template_type=self.template_type
                )
            
            # Substitute entity values and variables in the query
            substituted_query = self._substitute_parameters(sql_query, entity_values, context)
            
            # Execute SQL query
            result_data = context.execute_sql(
                query=substituted_query,
                as_dataframe=True
            )
            
            # Convert DataFrame to dict for consistency
            if hasattr(result_data, 'to_dict'):
                result_dict = result_data.to_dict('records')
                row_count = len(result_data)
                column_count = len(result_data.columns)
            else:
                result_dict = result_data
                row_count = len(result_dict) if isinstance(result_dict, list) else 1
                column_count = len(result_dict[0].keys()) if result_dict and isinstance(result_dict, list) else 0
            
            return ExecutionResult(
                success=True,
                data=result_dict,
                step_id=step_id,
                template_type=self.template_type,
                metadata={
                    "sql_query": substituted_query,
                    "row_count": row_count,
                    "column_count": column_count,
                    "execution_method": "duckdb_sql"
                }
            )
            
        except Exception as e:
            logger.error(f"DuckDB SQL step execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                error=f"SQL execution error: {str(e)}",
                step_id=step_id,
                template_type=self.template_type,
                metadata={"sql_error": str(e)}
            )
    
    def _substitute_parameters(
        self,
        query: str,
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Substitute parameters in SQL query.
        
        Supports:
        - {variable_name} - from entity_values
        - {step_id.column} - from previous step outputs
        - {table:step_id} - reference to step's table name
        """
        substituted = query
        
        # Substitute entity values
        if entity_values:
            for key, value in entity_values.items():
                placeholder = f"{{{key}}}"
                if isinstance(value, str):
                    substituted = substituted.replace(placeholder, f"'{value}'")
                else:
                    substituted = substituted.replace(placeholder, str(value))
        
        # Substitute table references {table:step_id}
        if context and hasattr(context, 'get_available_tables'):
            import re
            table_refs = re.findall(r'\{table:(\w+)\}', substituted)
            
            for step_id in table_refs:
                # Find the most recent table for this step
                tables = context.get_available_tables()
                table_name = None
                
                for table_info in tables:
                    if table_info.step_id == step_id:
                        table_name = table_info.name
                        break
                
                if table_name:
                    substituted = substituted.replace(f"{{table:{step_id}}}", table_name)
                else:
                    logger.warning(f"No table found for step reference: {step_id}")
        
        # Substitute step output column references {step_id.column}
        if context and hasattr(context, 'get_step_output'):
            import re
            column_refs = re.findall(r'\{(\w+)\.(\w+)\}', substituted)
            
            for step_id, column in column_refs:
                try:
                    step_data = context.get_step_output(step_id, as_dict=True, limit=1)
                    if step_data and isinstance(step_data, list) and step_data:
                        value = step_data[0].get(column)
                        if value is not None:
                            if isinstance(value, str):
                                substituted = substituted.replace(f"{{{step_id}.{column}}}", f"'{value}'")
                            else:
                                substituted = substituted.replace(f"{{{step_id}.{column}}}", str(value))
                except Exception as e:
                    logger.warning(f"Failed to substitute {step_id}.{column}: {e}")
        
        return substituted


class StepTemplateFactory:
    """Factory for creating step execution templates."""
    
    _templates = {
        TemplateType.SQL: SQLStepTemplate,
        TemplateType.API: APIStepTemplate,
        TemplateType.FUNCTION: FunctionStepTemplate,
        TemplateType.SCRIPT: ScriptStepTemplate,
        TemplateType.WORKFLOW: WorkflowStepTemplate,
        TemplateType.MCP_TOOL: MCPToolStepTemplate,
        TemplateType.LLM_STEP: LLMStepTemplate,
        TemplateType.DUCKDB_SQL: DuckDBStepTemplate,
    }
    
    @classmethod
    def create_template(
        self,
        template_type: str,
        nl2sql_client=None,
        **kwargs
    ) -> StepTemplate:
        """
        Create a step template for the given type.
        
        Args:
            template_type: Type of template to create
            nl2sql_client: Optional nl2sql client for SQL templates
            **kwargs: Additional arguments for template initialization
            
        Returns:
            StepTemplate instance
        """
        template_type = template_type.lower()
        
        # Map string types to enum values
        type_mapping = {
            "sql": TemplateType.SQL,
            "api": TemplateType.API,
            "function": TemplateType.FUNCTION,
            "script": TemplateType.SCRIPT,
            "workflow": TemplateType.WORKFLOW,
            "mcp_tool": TemplateType.MCP_TOOL,
            "llm_step": TemplateType.LLM_STEP,
            "duckdb_sql": TemplateType.DUCKDB_SQL,
        }
        
        enum_type = type_mapping.get(template_type)
        if not enum_type:
            # Fallback to generic tool template
            return ToolStepTemplate(template_type, **kwargs)
        
        template_class = self._templates.get(enum_type)
        if not template_class:
            # Fallback to generic tool template
            return ToolStepTemplate(template_type, **kwargs)
        
        # Special handling for SQL templates
        if enum_type == TemplateType.SQL:
            return template_class(nl2sql_client)
        # Special handling for LLM templates
        elif enum_type == TemplateType.LLM_STEP:
            llm_service = kwargs.get('llm_service')
            return template_class(llm_service)
        else:
            return template_class(**kwargs)
    
    @classmethod
    def register_template(cls, template_type: str, template_class: type) -> None:
        """Register a custom step template."""
        cls._templates[template_type] = template_class


class ToolStepTemplate(StepTemplate):
    """Generic execution template for tool steps."""
    
    def __init__(self, template_type: str):
        super().__init__(template_type)
        self.tool_wrapper = None  # Will initialize when needed
    
    def _get_tool_wrapper(self):
        """Get tool wrapper, creating if needed."""
        if self.tool_wrapper is None:
            self.tool_wrapper = ToolExecutionWrapper()
        return self.tool_wrapper
    
    async def _execute_impl(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        execution_config: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute generic tool step."""
        
        # Update step config with merged execution config
        enhanced_step_config = step_config.copy()
        enhanced_step_config["execution_config"] = execution_config
        
        # Execute via tool wrapper
        tool_wrapper = self._get_tool_wrapper()
        result = await tool_wrapper.execute_tool_step(
            enhanced_step_config, entity_values, context
        )
        
        # Add generic tool metadata
        if result.success:
            result.metadata.update({
                "execution_method": "tool_wrapper",
                "tool_type": self.template_type
            })
        
        return result


class StepExecutor:
    """High-level step executor that uses templates."""
    
    def __init__(self, nl2sql_client=None):
        self.nl2sql_client = nl2sql_client
        self.template_cache = {}
    
    async def execute_step(
        self,
        step_config: Dict[str, Any],
        entity_values: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> ExecutionResult:
        """
        Execute a step using the appropriate template.
        
        Args:
            step_config: Step configuration
            entity_values: Entity values for substitution
            context: Execution context
            progress_callback: Optional progress callback
            
        Returns:
            ExecutionResult
        """
        template_type = step_config.get("template_type", "unknown")
        
        # Get or create template
        template = self._get_template(template_type)
        
        # Execute the step
        return await template.execute(
            step_config=step_config,
            entity_values=entity_values,
            context=context,
            progress_callback=progress_callback
        )
    
    def _get_template(self, template_type: str) -> StepTemplate:
        """Get or create a step template (with caching)."""
        if template_type not in self.template_cache:
            self.template_cache[template_type] = StepTemplateFactory.create_template(
                template_type=template_type,
                nl2sql_client=self.nl2sql_client
            )
        
        return self.template_cache[template_type]
    
    def clear_template_cache(self) -> None:
        """Clear the template cache."""
        self.template_cache.clear()


# Convenience functions for direct step execution
async def execute_sql_step(
    step_config: Dict[str, Any],
    entity_values: Optional[Dict[str, Any]] = None,
    nl2sql_client=None,
    progress_callback: Optional[Callable] = None
) -> ExecutionResult:
    """Execute a SQL step directly."""
    template = SQLStepTemplate(nl2sql_client)
    return await template.execute(step_config, entity_values, progress_callback=progress_callback)


async def execute_api_step(
    step_config: Dict[str, Any],
    entity_values: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None
) -> ExecutionResult:
    """Execute an API step directly."""
    template = APIStepTemplate()
    return await template.execute(step_config, entity_values, progress_callback=progress_callback)


async def execute_function_step(
    step_config: Dict[str, Any],
    entity_values: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None
) -> ExecutionResult:
    """Execute a function step directly."""
    template = FunctionStepTemplate()
    return await template.execute(step_config, entity_values, progress_callback=progress_callback)


async def execute_workflow_step(
    step_config: Dict[str, Any],
    entity_values: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None
) -> ExecutionResult:
    """Execute a workflow step directly."""
    template = WorkflowStepTemplate()
    return await template.execute(step_config, entity_values, progress_callback=progress_callback)


async def execute_llm_step(
    step_config: Dict[str, Any],
    entity_values: Optional[Dict[str, Any]] = None,
    llm_service=None,
    progress_callback: Optional[Callable] = None
) -> ExecutionResult:
    """Execute an LLM step directly."""
    template = LLMStepTemplate(llm_service)
    return await template.execute(step_config, entity_values, progress_callback=progress_callback)


async def execute_duckdb_sql_step(
    step_config: Dict[str, Any],
    entity_values: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None
) -> ExecutionResult:
    """Execute a DuckDB SQL step directly."""
    template = DuckDBStepTemplate()
    return await template.execute(step_config, entity_values, context, progress_callback)