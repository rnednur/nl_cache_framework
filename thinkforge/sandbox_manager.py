"""
Sandbox Manager for secure notebook execution.
Manages Docker containers and provides interface for notebook execution.
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import structlog

logger = structlog.get_logger()

class SandboxManager:
    """Manages notebook sandbox containers and execution."""
    
    def __init__(self, 
                 sandbox_api_url: str = "http://localhost:8888",
                 docker_compose_path: str = None):
        """Initialize sandbox manager."""
        self.sandbox_api_url = sandbox_api_url.rstrip('/')
        self.docker_compose_path = docker_compose_path or self._find_compose_file()
        self.session = None
        
        logger.info("SandboxManager initialized", 
                   api_url=self.sandbox_api_url,
                   compose_path=self.docker_compose_path)
    
    def _find_compose_file(self) -> str:
        """Find the docker-compose file for sandbox."""
        current_dir = Path(__file__).parent
        
        # Look for compose file in docker directory
        compose_paths = [
            current_dir.parent / "docker" / "notebook-sandbox" / "docker-compose.sandbox.yml",
            current_dir.parent / "docker-compose.sandbox.yml",
            current_dir / "docker-compose.sandbox.yml"
        ]
        
        for path in compose_paths:
            if path.exists():
                return str(path)
        
        logger.warning("Docker compose file not found, using default path")
        return str(current_dir.parent / "docker" / "notebook-sandbox" / "docker-compose.sandbox.yml")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def start_sandbox(self) -> bool:
        """Start the sandbox container."""
        try:
            import subprocess
            
            # Check if docker-compose is available
            compose_cmd = ["docker", "compose", "-f", self.docker_compose_path, "up", "-d"]
            
            logger.info("Starting sandbox container", command=" ".join(compose_cmd))
            
            result = subprocess.run(
                compose_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info("Sandbox container started successfully")
                
                # Wait for API to be available
                await self._wait_for_api()
                return True
            else:
                logger.error("Failed to start sandbox container", 
                           stderr=result.stderr,
                           stdout=result.stdout)
                return False
        
        except Exception as e:
            logger.error("Exception starting sandbox", error=str(e))
            return False
    
    async def stop_sandbox(self) -> bool:
        """Stop the sandbox container."""
        try:
            import subprocess
            
            compose_cmd = ["docker", "compose", "-f", self.docker_compose_path, "down"]
            
            logger.info("Stopping sandbox container", command=" ".join(compose_cmd))
            
            result = subprocess.run(
                compose_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("Sandbox container stopped successfully")
                return True
            else:
                logger.error("Failed to stop sandbox container", 
                           stderr=result.stderr)
                return False
        
        except Exception as e:
            logger.error("Exception stopping sandbox", error=str(e))
            return False
    
    async def _wait_for_api(self, max_retries: int = 30, delay: float = 2.0):
        """Wait for sandbox API to become available."""
        for attempt in range(max_retries):
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()
                
                async with self.session.get(f"{self.sandbox_api_url}/health") as response:
                    if response.status == 200:
                        logger.info("Sandbox API is available")
                        return
            
            except Exception:
                pass
            
            logger.debug("Waiting for sandbox API", 
                        attempt=attempt + 1,
                        max_retries=max_retries)
            await asyncio.sleep(delay)
        
        raise Exception(f"Sandbox API not available after {max_retries} attempts")
    
    async def upload_notebook(self, notebook_content: str, filename: str) -> Dict[str, Any]:
        """Upload a notebook to the sandbox."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Create form data
            data = aiohttp.FormData()
            data.add_field('file',
                          notebook_content,
                          filename=filename,
                          content_type='application/x-ipynb+json')
            
            async with self.session.post(
                f"{self.sandbox_api_url}/notebooks/upload",
                data=data
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info("Notebook uploaded successfully", 
                              filename=filename,
                              size=len(notebook_content))
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Upload failed: {error_text}")
        
        except Exception as e:
            logger.error("Failed to upload notebook", 
                        filename=filename,
                        error=str(e))
            raise
    
    async def validate_notebook(self, notebook_path: str) -> Dict[str, Any]:
        """Validate a notebook in the sandbox."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = {"notebook_path": notebook_path}
            
            async with self.session.post(
                f"{self.sandbox_api_url}/notebooks/validate",
                json=payload
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info("Notebook validation completed", 
                              notebook_path=notebook_path,
                              valid=result.get("valid", False))
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Validation failed: {error_text}")
        
        except Exception as e:
            logger.error("Failed to validate notebook", 
                        notebook_path=notebook_path,
                        error=str(e))
            raise
    
    async def execute_notebook(self, 
                             notebook_path: str,
                             memory_limit_mb: int = 512,
                             cpu_time_limit: int = 300,
                             wall_time_limit: int = 600) -> str:
        """Start notebook execution and return execution ID."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = {
                "notebook_path": notebook_path,
                "memory_limit_mb": memory_limit_mb,
                "cpu_time_limit": cpu_time_limit,
                "wall_time_limit": wall_time_limit
            }
            
            async with self.session.post(
                f"{self.sandbox_api_url}/notebooks/execute",
                json=payload
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    execution_id = result["execution_id"]
                    logger.info("Notebook execution started", 
                              notebook_path=notebook_path,
                              execution_id=execution_id)
                    return execution_id
                else:
                    error_text = await response.text()
                    raise Exception(f"Execution start failed: {error_text}")
        
        except Exception as e:
            logger.error("Failed to start notebook execution", 
                        notebook_path=notebook_path,
                        error=str(e))
            raise
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get the status of a notebook execution."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.sandbox_api_url}/notebooks/execution/{execution_id}"
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result
                elif response.status == 404:
                    raise Exception(f"Execution not found: {execution_id}")
                else:
                    error_text = await response.text()
                    raise Exception(f"Status check failed: {error_text}")
        
        except Exception as e:
            logger.error("Failed to get execution status", 
                        execution_id=execution_id,
                        error=str(e))
            raise
    
    async def wait_for_execution(self, 
                                execution_id: str, 
                                timeout: int = 600,
                                poll_interval: float = 5.0) -> Dict[str, Any]:
        """Wait for notebook execution to complete."""
        start_time = datetime.utcnow()
        
        while True:
            try:
                status = await self.get_execution_status(execution_id)
                
                if status["status"] in ["completed", "failed"]:
                    logger.info("Notebook execution finished", 
                              execution_id=execution_id,
                              status=status["status"])
                    return status
                
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout:
                    raise Exception(f"Execution timeout after {timeout} seconds")
                
                await asyncio.sleep(poll_interval)
            
            except Exception as e:
                logger.error("Error waiting for execution", 
                           execution_id=execution_id,
                           error=str(e))
                raise
    
    async def list_notebooks(self) -> Dict[str, Any]:
        """List all notebooks in the sandbox."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(
                f"{self.sandbox_api_url}/notebooks"
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"List notebooks failed: {error_text}")
        
        except Exception as e:
            logger.error("Failed to list notebooks", error=str(e))
            raise
    
    async def delete_notebook(self, notebook_path: str) -> bool:
        """Delete a notebook from the sandbox."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.delete(
                f"{self.sandbox_api_url}/notebooks/{notebook_path}"
            ) as response:
                
                if response.status == 200:
                    logger.info("Notebook deleted successfully", 
                              notebook_path=notebook_path)
                    return True
                else:
                    error_text = await response.text()
                    raise Exception(f"Delete failed: {error_text}")
        
        except Exception as e:
            logger.error("Failed to delete notebook", 
                        notebook_path=notebook_path,
                        error=str(e))
            raise
    
    async def execute_dsl_workflow(self, 
                                 dsl_content: Dict[str, Any],
                                 workflow_name: str = "generated_workflow") -> Dict[str, Any]:
        """Execute a DSL workflow by converting to notebook and running in sandbox."""
        try:
            # Import notebook generator
            from .notebook_generator import PythonNotebookGenerator
            
            # Generate notebook from DSL
            generator = PythonNotebookGenerator()
            notebook_content = generator.generate_from_dsl(dsl_content)
            
            # Create filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{workflow_name}_{timestamp}.ipynb"
            
            # Upload notebook
            upload_result = await self.upload_notebook(notebook_content, filename)
            notebook_path = upload_result["path"]
            
            # Validate notebook
            validation_result = await self.validate_notebook(notebook_path)
            if not validation_result["valid"]:
                raise Exception(f"Notebook validation failed: {validation_result['issues']}")
            
            # Execute notebook
            execution_id = await self.execute_notebook(notebook_path)
            
            # Wait for completion
            execution_result = await self.wait_for_execution(execution_id)
            
            logger.info("DSL workflow execution completed", 
                       workflow_name=workflow_name,
                       execution_id=execution_id,
                       success=execution_result.get("result", {}).get("success", False))
            
            return {
                "workflow_name": workflow_name,
                "notebook_path": notebook_path,
                "execution_id": execution_id,
                "validation_result": validation_result,
                "execution_result": execution_result
            }
        
        except Exception as e:
            logger.error("Failed to execute DSL workflow", 
                        workflow_name=workflow_name,
                        error=str(e))
            raise