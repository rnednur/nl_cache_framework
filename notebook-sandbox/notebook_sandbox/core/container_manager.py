"""
Docker container management for notebook sandbox.
"""

import asyncio
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()

class ContainerError(Exception):
    """Exception raised for container management errors."""
    pass

class ContainerManager:
    """Manages Docker containers for notebook execution."""
    
    def __init__(self, 
                 compose_file_path: Optional[Path] = None,
                 project_name: str = "notebook-sandbox"):
        """
        Initialize container manager.
        
        Args:
            compose_file_path: Path to docker-compose file
            project_name: Docker Compose project name
        """
        self.compose_file_path = compose_file_path or self._find_compose_file()
        self.project_name = project_name
        
        logger.info("ContainerManager initialized",
                   compose_file=str(self.compose_file_path),
                   project_name=project_name)
    
    def _find_compose_file(self) -> Path:
        """Find docker-compose file."""
        # Look in common locations
        current_dir = Path(__file__).parent
        
        search_paths = [
            current_dir.parent / "docker" / "docker-compose.yml",
            current_dir.parent / "docker-compose.yml",
            current_dir.parent.parent / "docker" / "notebook-sandbox" / "docker-compose.sandbox.yml",
            Path.cwd() / "docker-compose.yml"
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        # Default fallback
        return current_dir.parent / "docker" / "docker-compose.yml"
    
    async def start_container(self, 
                            service_name: str = "notebook-sandbox",
                            timeout: int = 120) -> bool:
        """
        Start the sandbox container.
        
        Args:
            service_name: Docker Compose service name
            timeout: Startup timeout in seconds
            
        Returns:
            True if started successfully
        """
        try:
            cmd = [
                "docker", "compose",
                "-f", str(self.compose_file_path),
                "-p", self.project_name,
                "up", "-d", service_name
            ]
            
            logger.info("Starting container", 
                       service=service_name,
                       command=" ".join(cmd))
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            if process.returncode == 0:
                logger.info("Container started successfully", service=service_name)
                
                # Wait for container to be healthy
                await self._wait_for_health(service_name)
                return True
            else:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error("Container start failed",
                           service=service_name,
                           return_code=process.returncode,
                           error=error_msg)
                return False
        
        except asyncio.TimeoutError:
            logger.error("Container start timeout", 
                        service=service_name,
                        timeout=timeout)
            return False
        except Exception as e:
            logger.error("Container start exception",
                        service=service_name,
                        error=str(e))
            return False
    
    async def stop_container(self, 
                           service_name: str = "notebook-sandbox",
                           timeout: int = 60) -> bool:
        """
        Stop the sandbox container.
        
        Args:
            service_name: Docker Compose service name
            timeout: Stop timeout in seconds
            
        Returns:
            True if stopped successfully
        """
        try:
            cmd = [
                "docker", "compose",
                "-f", str(self.compose_file_path),
                "-p", self.project_name,
                "down", service_name
            ]
            
            logger.info("Stopping container",
                       service=service_name,
                       command=" ".join(cmd))
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            if process.returncode == 0:
                logger.info("Container stopped successfully", service=service_name)
                return True
            else:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error("Container stop failed",
                           service=service_name,
                           return_code=process.returncode,
                           error=error_msg)
                return False
        
        except asyncio.TimeoutError:
            logger.error("Container stop timeout",
                        service=service_name,
                        timeout=timeout)
            return False
        except Exception as e:
            logger.error("Container stop exception",
                        service=service_name,
                        error=str(e))
            return False
    
    async def restart_container(self, 
                              service_name: str = "notebook-sandbox",
                              timeout: int = 120) -> bool:
        """
        Restart the sandbox container.
        
        Args:
            service_name: Docker Compose service name
            timeout: Restart timeout in seconds
            
        Returns:
            True if restarted successfully
        """
        logger.info("Restarting container", service=service_name)
        
        # Stop first
        stop_success = await self.stop_container(service_name, timeout // 2)
        if not stop_success:
            logger.warning("Container stop failed during restart")
        
        # Start again
        return await self.start_container(service_name, timeout // 2)
    
    async def get_container_status(self, 
                                 service_name: str = "notebook-sandbox") -> Dict[str, Any]:
        """
        Get container status information.
        
        Args:
            service_name: Docker Compose service name
            
        Returns:
            Status information dictionary
        """
        try:
            # Get service status
            cmd = [
                "docker", "compose",
                "-f", str(self.compose_file_path),
                "-p", self.project_name,
                "ps", "--format", "json", service_name
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and stdout:
                try:
                    # Parse JSON output
                    containers = json.loads(stdout.decode('utf-8'))
                    if containers:
                        container = containers[0] if isinstance(containers, list) else containers
                        
                        return {
                            "status": container.get("State", "unknown"),
                            "health": container.get("Health", "unknown"),
                            "name": container.get("Name", service_name),
                            "ports": container.get("Ports", ""),
                            "image": container.get("Image", ""),
                            "created": container.get("CreatedAt", ""),
                            "running": container.get("State", "").lower() == "running"
                        }
                except json.JSONDecodeError:
                    pass
            
            # Fallback: container not found or not running
            return {
                "status": "not_found",
                "health": "unknown",
                "name": service_name,
                "running": False
            }
        
        except Exception as e:
            logger.error("Failed to get container status",
                        service=service_name,
                        error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "running": False
            }
    
    async def _wait_for_health(self, 
                             service_name: str = "notebook-sandbox",
                             max_wait: int = 60,
                             check_interval: float = 2.0):
        """
        Wait for container to become healthy.
        
        Args:
            service_name: Docker Compose service name
            max_wait: Maximum wait time in seconds
            check_interval: Time between health checks
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                logger.warning("Container health check timeout",
                             service=service_name,
                             elapsed=elapsed)
                break
            
            status = await self.get_container_status(service_name)
            
            if status.get("running"):
                health = status.get("health", "").lower()
                if health in ["healthy", "unknown"]:  # unknown means no health check defined
                    logger.info("Container is healthy", service=service_name)
                    return
                elif health == "unhealthy":
                    logger.warning("Container is unhealthy", service=service_name)
                    break
            
            await asyncio.sleep(check_interval)
    
    async def get_container_logs(self, 
                               service_name: str = "notebook-sandbox",
                               tail: int = 100) -> str:
        """
        Get container logs.
        
        Args:
            service_name: Docker Compose service name
            tail: Number of recent log lines to retrieve
            
        Returns:
            Log content as string
        """
        try:
            cmd = [
                "docker", "compose",
                "-f", str(self.compose_file_path),
                "-p", self.project_name,
                "logs", "--tail", str(tail), service_name
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode('utf-8')
            else:
                error_msg = stderr.decode('utf-8') if stderr else "Failed to get logs"
                logger.error("Failed to get container logs",
                           service=service_name,
                           error=error_msg)
                return f"Error getting logs: {error_msg}"
        
        except Exception as e:
            logger.error("Exception getting container logs",
                        service=service_name,
                        error=str(e))
            return f"Exception getting logs: {str(e)}"
    
    async def exec_command(self, 
                         command: List[str],
                         service_name: str = "notebook-sandbox",
                         timeout: int = 30) -> Dict[str, Any]:
        """
        Execute command in container.
        
        Args:
            command: Command to execute
            service_name: Docker Compose service name
            timeout: Command timeout in seconds
            
        Returns:
            Execution result with stdout, stderr, return code
        """
        try:
            cmd = [
                "docker", "compose",
                "-f", str(self.compose_file_path),
                "-p", self.project_name,
                "exec", "-T", service_name
            ] + command
            
            logger.info("Executing command in container",
                       service=service_name,
                       command=" ".join(command))
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8')
            }
        
        except asyncio.TimeoutError:
            logger.error("Command execution timeout",
                        service=service_name,
                        command=" ".join(command))
            return {
                "success": False,
                "error": "Command timeout",
                "timeout": timeout
            }
        except Exception as e:
            logger.error("Command execution failed",
                        service=service_name,
                        command=" ".join(command),
                        error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check container manager health.
        
        Returns:
            Health status information
        """
        try:
            # Check if Docker is available
            process = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode != 0:
                return {
                    "status": "unhealthy",
                    "error": "Docker not available"
                }
            
            # Check compose file existence
            if not self.compose_file_path.exists():
                return {
                    "status": "unhealthy",
                    "error": f"Compose file not found: {self.compose_file_path}"
                }
            
            # Check container status
            container_status = await self.get_container_status()
            
            return {
                "status": "healthy",
                "docker_available": True,
                "compose_file": str(self.compose_file_path),
                "container_status": container_status
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }