"""
Generic wrapper service client for tool resolution and execution.
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urljoin
import structlog

from .tool_resolver import ToolResolver, Tool, ToolSearchResult

logger = structlog.get_logger()

class WrapperServiceError(Exception):
    """Exception raised when wrapper service communication fails."""
    pass

class WrapperClient(ToolResolver):
    """Generic HTTP client for wrapper services."""
    
    def __init__(self, 
                 service_url: str,
                 timeout: float = 30.0,
                 max_retries: int = 3,
                 auth_token: Optional[str] = None):
        """
        Initialize wrapper client.
        
        Args:
            service_url: Base URL of the wrapper service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            auth_token: Optional authentication token
        """
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.auth_token = auth_token
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Setup headers
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'notebook-sandbox/1.0.0'
        }
        
        if auth_token:
            self.headers['Authorization'] = f'Bearer {auth_token}'
        
        logger.info("WrapperClient initialized", 
                   service_url=self.service_url,
                   timeout=timeout)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _request(self, 
                      method: str, 
                      endpoint: str, 
                      data: Optional[Dict[str, Any]] = None,
                      params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make HTTP request to wrapper service.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data
            
        Raises:
            WrapperServiceError: If request fails
        """
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self.headers
            )
        
        url = urljoin(self.service_url, endpoint)
        
        for attempt in range(self.max_retries + 1):
            try:
                async with self.session.request(
                    method, 
                    url, 
                    json=data, 
                    params=params
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return result
                    elif response.status == 404:
                        raise WrapperServiceError(f"Endpoint not found: {endpoint}")
                    elif response.status >= 500:
                        # Server error - retry
                        if attempt < self.max_retries:
                            wait_time = 2 ** attempt
                            logger.warning("Server error, retrying",
                                         status=response.status,
                                         attempt=attempt,
                                         wait_time=wait_time)
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            raise WrapperServiceError(f"Server error: {response.status} - {error_text}")
                    else:
                        error_text = await response.text()
                        raise WrapperServiceError(f"Request failed: {response.status} - {error_text}")
            
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning("Network error, retrying",
                                 error=str(e),
                                 attempt=attempt,
                                 wait_time=wait_time)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise WrapperServiceError(f"Network error: {str(e)}")
        
        raise WrapperServiceError("Max retries exceeded")
    
    async def resolve_tools(self, 
                           step_description: str,
                           tool_type: Optional[str] = None,
                           limit: int = 10,
                           threshold: float = 0.5) -> ToolSearchResult:
        """
        Resolve tools via wrapper service.
        
        Args:
            step_description: Natural language description
            tool_type: Optional tool type filter
            limit: Maximum number of results
            threshold: Minimum confidence threshold
            
        Returns:
            ToolSearchResult with matching tools
        """
        import time
        start_time = time.time()
        
        try:
            request_data = {
                "query": step_description,
                "limit": limit,
                "threshold": threshold
            }
            
            if tool_type:
                request_data["tool_type"] = tool_type
            
            response = await self._request("POST", "/tools/resolve", data=request_data)
            
            # Parse tools from response
            tools = []
            for tool_data in response.get("tools", []):
                tool = Tool(
                    id=tool_data["id"],
                    name=tool_data["name"],
                    description=tool_data["description"],
                    tool_type=tool_data["tool_type"],
                    input_schema=tool_data.get("input_schema"),
                    output_schema=tool_data.get("output_schema"),
                    execution_config=tool_data.get("execution_config"),
                    tags=tool_data.get("tags", []),
                    category=tool_data.get("category"),
                    confidence_score=tool_data.get("confidence_score", 0.0)
                )
                tools.append(tool)
            
            search_time = time.time() - start_time
            
            logger.info("Tool resolution completed via wrapper service",
                       query=step_description,
                       found_tools=len(tools),
                       search_time=search_time)
            
            return ToolSearchResult(
                query=step_description,
                tools=tools,
                total_count=response.get("total_count", len(tools)),
                search_time=search_time,
                metadata=response.get("metadata", {})
            )
        
        except Exception as e:
            logger.error("Tool resolution failed",
                        query=step_description,
                        error=str(e))
            raise WrapperServiceError(f"Tool resolution failed: {str(e)}")
    
    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get specific tool by ID.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Tool if found, None otherwise
        """
        try:
            response = await self._request("GET", f"/tools/{tool_id}")
            
            tool_data = response.get("tool")
            if not tool_data:
                return None
            
            return Tool(
                id=tool_data["id"],
                name=tool_data["name"],
                description=tool_data["description"],
                tool_type=tool_data["tool_type"],
                input_schema=tool_data.get("input_schema"),
                output_schema=tool_data.get("output_schema"),
                execution_config=tool_data.get("execution_config"),
                tags=tool_data.get("tags", []),
                category=tool_data.get("category"),
                confidence_score=tool_data.get("confidence_score", 0.0)
            )
        
        except WrapperServiceError as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def list_tools(self, 
                        tool_type: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: int = 100) -> List[Tool]:
        """
        List available tools.
        
        Args:
            tool_type: Optional tool type filter
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of tools
        """
        try:
            params = {"limit": limit}
            if tool_type:
                params["tool_type"] = tool_type
            if category:
                params["category"] = category
            
            response = await self._request("GET", "/tools", params=params)
            
            tools = []
            for tool_data in response.get("tools", []):
                tool = Tool(
                    id=tool_data["id"],
                    name=tool_data["name"],
                    description=tool_data["description"],
                    tool_type=tool_data["tool_type"],
                    input_schema=tool_data.get("input_schema"),
                    output_schema=tool_data.get("output_schema"),
                    execution_config=tool_data.get("execution_config"),
                    tags=tool_data.get("tags", []),
                    category=tool_data.get("category"),
                    confidence_score=tool_data.get("confidence_score", 0.0)
                )
                tools.append(tool)
            
            logger.info("Tools listed via wrapper service",
                       count=len(tools),
                       tool_type=tool_type,
                       category=category)
            
            return tools
        
        except Exception as e:
            logger.error("Tool listing failed", error=str(e))
            raise WrapperServiceError(f"Tool listing failed: {str(e)}")
    
    async def execute_tool(self, 
                          tool_id: str, 
                          inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool via wrapper service.
        
        Args:
            tool_id: Tool identifier
            inputs: Tool input parameters
            
        Returns:
            Execution result
        """
        try:
            request_data = {
                "tool_id": tool_id,
                "inputs": inputs
            }
            
            response = await self._request("POST", "/tools/execute", data=request_data)
            
            logger.info("Tool executed via wrapper service",
                       tool_id=tool_id,
                       success=response.get("success", False))
            
            return response
        
        except Exception as e:
            logger.error("Tool execution failed",
                        tool_id=tool_id,
                        error=str(e))
            raise WrapperServiceError(f"Tool execution failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check wrapper service health.
        
        Returns:
            Health status
        """
        try:
            response = await self._request("GET", "/health")
            return {
                "status": "healthy",
                "resolver_type": "wrapper_client",
                "service_url": self.service_url,
                "service_status": response
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "resolver_type": "wrapper_client", 
                "service_url": self.service_url,
                "error": str(e)
            }