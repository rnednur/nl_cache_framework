"""
Tool Invocation System for ThinkForge

This module provides direct tool execution capabilities for workflow steps,
supporting various tool types including API calls, SQL queries, scripts,
MCP tools, and more.
"""

import asyncio
import aiohttp
import logging
import json
import subprocess
import tempfile
import os
import sqlite3
import psycopg2
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from sqlalchemy import text

from .models import Text2SQLCache, TemplateType
from .entity_substitution import Text2SQLEntitySubstitution

logger = logging.getLogger(__name__)


class ToolInvokerError(Exception):
    """Base exception for tool invocation errors"""
    pass


class ToolInvoker:
    """
    Tool invocation system for executing workflow steps.
    
    Supports direct execution of various tool types including:
    - API calls (REST, GraphQL)
    - SQL queries (PostgreSQL, SQLite)
    - Script execution (Python, Shell)
    - MCP tools
    - Agent invocations
    """

    def __init__(self, db_session: Session):
        """
        Initialize the tool invoker.

        Args:
            db_session: Database session for tool data access
        """
        self.db_session = db_session
        self.entity_substitution = Text2SQLEntitySubstitution()
        self.http_session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_session:
            await self.http_session.close()

    async def invoke_tool(
        self,
        template_type: str,
        template: str,
        inputs: Dict[str, Any],
        context_variables: Optional[Dict[str, Any]] = None,
        tool_id: Optional[int] = None
    ) -> Any:
        """
        Invoke a tool with the given parameters.

        Args:
            template_type: Type of tool/template (api, sql, script, etc.)
            template: Template content to execute
            inputs: Input parameters for the tool
            context_variables: Additional context variables
            tool_id: Optional tool ID to load from cache

        Returns:
            Tool execution result

        Raises:
            ToolInvokerError: If tool execution fails
        """
        logger.info(f"Invoking tool: type={template_type}, tool_id={tool_id}")

        try:
            # Load tool from cache if tool_id provided
            if tool_id:
                tool_entry = await self._load_tool(tool_id)
                if tool_entry:
                    template = tool_entry.template
                    template_type = tool_entry.template_type

            # Ensure HTTP session is available
            if not self.http_session:
                self.http_session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                )

            # Apply entity substitution to template
            processed_template = await self._apply_entity_substitution(
                template, template_type, inputs, context_variables
            )

            # Route to appropriate invoker based on template type
            template_type_lower = template_type.lower()

            if template_type_lower in ['api', 'rest']:
                return await self._invoke_api_tool(processed_template, inputs)
            elif template_type_lower == 'sql':
                return await self._invoke_sql_tool(processed_template, inputs)
            elif template_type_lower == 'graphql':
                return await self._invoke_graphql_tool(processed_template, inputs)
            elif template_type_lower in ['script', 'python']:
                return await self._invoke_script_tool(processed_template, inputs, 'python')
            elif template_type_lower == 'cli':
                return await self._invoke_cli_tool(processed_template, inputs)
            elif template_type_lower == 'url':
                return await self._invoke_url_tool(processed_template, inputs)
            elif template_type_lower == 'mcp_tool':
                return await self._invoke_mcp_tool(processed_template, inputs)
            elif template_type_lower == 'agent':
                return await self._invoke_agent_tool(processed_template, inputs)
            elif template_type_lower == 'function':
                return await self._invoke_function_tool(processed_template, inputs)
            elif template_type_lower == 'workflow':
                return await self._invoke_workflow_tool(processed_template, inputs)
            elif template_type_lower == 'prompt':
                return await self._invoke_prompt_tool(processed_template, inputs)
            else:
                # Generic template processing
                return await self._invoke_generic_tool(processed_template, inputs)

        except Exception as e:
            logger.error(f"Tool invocation failed: {e}")
            raise ToolInvokerError(f"Tool execution failed: {str(e)}")

    async def _load_tool(self, tool_id: int) -> Optional[Text2SQLCache]:
        """Load tool from cache"""
        try:
            return self.db_session.query(Text2SQLCache).filter_by(id=tool_id).first()
        except Exception as e:
            logger.error(f"Failed to load tool {tool_id}: {e}")
            return None

    async def _apply_entity_substitution(
        self,
        template: str,
        template_type: str,
        inputs: Dict[str, Any],
        context_variables: Optional[Dict[str, Any]]
    ) -> str:
        """Apply entity substitution to template"""
        try:
            # Combine inputs and context variables
            all_variables = {**(context_variables or {}), **inputs}
            
            # Apply entity substitution
            result = self.entity_substitution.substitute_entities(
                template=template,
                template_type=template_type,
                entity_values=all_variables
            )
            
            return result.get('substituted_template', template)
        except Exception as e:
            logger.warning(f"Entity substitution failed: {e}")
            return template

    async def _invoke_api_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke REST API tool"""
        try:
            # Parse API configuration from template
            if template.startswith('{'):
                # JSON configuration
                config = json.loads(template)
            else:
                # Simple URL
                config = {"url": template, "method": "GET"}

            url = config.get("url")
            method = config.get("method", "GET").upper()
            headers = config.get("headers", {})
            params = config.get("params", {})
            data = config.get("data")
            timeout = config.get("timeout", 30)

            # Add input parameters
            if inputs.get("headers"):
                headers.update(inputs["headers"])
            if inputs.get("params"):
                params.update(inputs["params"])
            if inputs.get("data"):
                data = inputs["data"]

            # Ensure required headers
            if not headers.get("Content-Type") and data:
                headers["Content-Type"] = "application/json"

            logger.info(f"Making API call: {method} {url}")

            async with self.http_session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data if isinstance(data, (dict, list)) else None,
                data=data if isinstance(data, (str, bytes)) else None,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                result = {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }

                # Try to parse JSON response
                try:
                    result["data"] = await response.json()
                except:
                    result["data"] = await response.text()

                response.raise_for_status()
                return result

        except Exception as e:
            raise ToolInvokerError(f"API call failed: {str(e)}")

    async def _invoke_sql_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke SQL tool"""
        try:
            # Extract database connection info from inputs or environment
            db_url = inputs.get("database_url") or os.getenv("DATABASE_URL")
            
            if not db_url:
                raise ToolInvokerError("No database connection URL provided")

            # Parse database URL
            parsed = urlparse(db_url)
            
            if parsed.scheme.startswith('postgresql'):
                return await self._execute_postgresql_query(template, db_url, inputs)
            elif parsed.scheme == 'sqlite':
                return await self._execute_sqlite_query(template, db_url, inputs)
            else:
                raise ToolInvokerError(f"Unsupported database type: {parsed.scheme}")

        except Exception as e:
            raise ToolInvokerError(f"SQL execution failed: {str(e)}")

    async def _execute_postgresql_query(
        self, 
        query: str, 
        db_url: str, 
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute PostgreSQL query"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def run_query():
            with psycopg2.connect(db_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    
                    if cursor.description:
                        # SELECT query
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        return {
                            "columns": columns,
                            "rows": [dict(zip(columns, row)) for row in rows],
                            "row_count": len(rows)
                        }
                    else:
                        # INSERT/UPDATE/DELETE query
                        conn.commit()
                        return {
                            "rows_affected": cursor.rowcount,
                            "message": "Query executed successfully"
                        }

        # Run in thread pool to avoid blocking
        with ThreadPoolExecutor() as executor:
            return await asyncio.get_event_loop().run_in_executor(executor, run_query)

    async def _execute_sqlite_query(
        self, 
        query: str, 
        db_url: str, 
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute SQLite query"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def run_query():
            # Extract path from sqlite URL
            db_path = db_url.replace('sqlite:///', '').replace('sqlite://', '')
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(query)
                
                if cursor.description:
                    # SELECT query
                    rows = cursor.fetchall()
                    return {
                        "columns": list(rows[0].keys()) if rows else [],
                        "rows": [dict(row) for row in rows],
                        "row_count": len(rows)
                    }
                else:
                    # INSERT/UPDATE/DELETE query
                    conn.commit()
                    return {
                        "rows_affected": cursor.rowcount,
                        "message": "Query executed successfully"
                    }

        # Run in thread pool to avoid blocking
        with ThreadPoolExecutor() as executor:
            return await asyncio.get_event_loop().run_in_executor(executor, run_query)

    async def _invoke_graphql_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke GraphQL tool"""
        try:
            # Parse GraphQL configuration
            config = json.loads(template) if template.startswith('{') else {"query": template}
            
            url = config.get("url") or inputs.get("url")
            query = config.get("query", template)
            variables = config.get("variables", {})
            headers = config.get("headers", {"Content-Type": "application/json"})

            # Add input variables
            if inputs.get("variables"):
                variables.update(inputs["variables"])

            payload = {
                "query": query,
                "variables": variables
            }

            async with self.http_session.post(
                url=url,
                json=payload,
                headers=headers
            ) as response:
                response.raise_for_status()
                return await response.json()

        except Exception as e:
            raise ToolInvokerError(f"GraphQL execution failed: {str(e)}")

    async def _invoke_script_tool(
        self, 
        template: str, 
        inputs: Dict[str, Any], 
        language: str = 'python'
    ) -> Dict[str, Any]:
        """Invoke script tool"""
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            def run_script():
                # Create temporary script file
                if language == 'python':
                    suffix = '.py'
                    command = ['python']
                else:
                    suffix = '.sh'
                    command = ['bash']

                with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
                    f.write(template)
                    script_path = f.name

                try:
                    # Prepare environment with input variables
                    env = os.environ.copy()
                    for key, value in inputs.items():
                        env[f"INPUT_{key.upper()}"] = str(value)

                    # Execute script
                    result = subprocess.run(
                        command + [script_path],
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=60
                    )

                    return {
                        "exit_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "success": result.returncode == 0
                    }

                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(script_path)
                    except:
                        pass

            # Run in thread pool to avoid blocking
            with ThreadPoolExecutor() as executor:
                return await asyncio.get_event_loop().run_in_executor(executor, run_script)

        except Exception as e:
            raise ToolInvokerError(f"Script execution failed: {str(e)}")

    async def _invoke_cli_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke CLI tool"""
        try:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            import shlex

            def run_command():
                # Parse command with arguments
                if isinstance(template, str):
                    # Simple command string
                    command = shlex.split(template)
                else:
                    # Command configuration
                    config = json.loads(template) if isinstance(template, str) else template
                    command = config.get("command", [])
                    if isinstance(command, str):
                        command = shlex.split(command)

                # Prepare environment
                env = os.environ.copy()
                for key, value in inputs.items():
                    env[f"INPUT_{key.upper()}"] = str(value)

                # Execute command
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=60
                )

                return {
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0,
                    "command": " ".join(command)
                }

            # Run in thread pool to avoid blocking
            with ThreadPoolExecutor() as executor:
                return await asyncio.get_event_loop().run_in_executor(executor, run_command)

        except Exception as e:
            raise ToolInvokerError(f"CLI execution failed: {str(e)}")

    async def _invoke_url_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke URL tool (simple GET request)"""
        try:
            async with self.http_session.get(template) as response:
                result = {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }

                try:
                    result["data"] = await response.json()
                except:
                    result["data"] = await response.text()

                response.raise_for_status()
                return result

        except Exception as e:
            raise ToolInvokerError(f"URL fetch failed: {str(e)}")

    async def _invoke_mcp_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke MCP (Model Context Protocol) tool"""
        # Placeholder for MCP tool integration
        # This would integrate with MCP servers and tools
        logger.warning("MCP tool invocation not yet implemented")
        return {
            "message": "MCP tool invocation not yet implemented",
            "template": template,
            "inputs": inputs
        }

    async def _invoke_agent_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke AI agent tool"""
        try:
            # Parse agent configuration
            config = json.loads(template) if template.startswith('{') else {"prompt": template}
            
            prompt = config.get("prompt", template)
            system_prompt = config.get("system_prompt", "")
            model = config.get("model", "gpt-3.5-turbo")

            # Add input context to prompt
            if inputs:
                prompt += f"\n\nContext: {json.dumps(inputs, indent=2)}"

            # This would integrate with LLM service
            # For now, return a placeholder response
            return {
                "response": "Agent response placeholder",
                "model": model,
                "prompt": prompt,
                "message": "Agent tool execution - placeholder implementation"
            }

        except Exception as e:
            raise ToolInvokerError(f"Agent execution failed: {str(e)}")

    async def _invoke_function_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke function tool"""
        try:
            # Parse function configuration
            config = json.loads(template) if template.startswith('{') else {"code": template}
            
            function_code = config.get("code", template)
            function_name = config.get("name", "execute")

            # Create a safe execution environment
            namespace = {
                "inputs": inputs,
                "json": json,
                "datetime": datetime,
                "__builtins__": {
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "round": round,
                }
            }

            # Execute function
            exec(function_code, namespace)
            
            if function_name in namespace:
                result = namespace[function_name](inputs)
            else:
                result = namespace.get("result", "Function executed")

            return {
                "result": result,
                "function_name": function_name,
                "success": True
            }

        except Exception as e:
            raise ToolInvokerError(f"Function execution failed: {str(e)}")

    async def _invoke_workflow_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke sub-workflow tool"""
        # This would recursively execute another workflow
        logger.warning("Workflow tool invocation not yet implemented")
        return {
            "message": "Sub-workflow execution not yet implemented",
            "template": template,
            "inputs": inputs
        }

    async def _invoke_prompt_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke prompt tool (LLM interaction)"""
        try:
            # This would integrate with LLM service
            # For now, return the processed prompt
            return {
                "prompt": template,
                "inputs": inputs,
                "response": "LLM response placeholder",
                "message": "Prompt tool execution - placeholder implementation"
            }

        except Exception as e:
            raise ToolInvokerError(f"Prompt execution failed: {str(e)}")

    async def _invoke_generic_tool(self, template: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke generic tool (return processed template)"""
        return {
            "processed_template": template,
            "inputs": inputs,
            "message": "Generic tool execution - template processed"
        }

    async def close(self):
        """Close HTTP session and cleanup resources"""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None