"""
MCP (Model Context Protocol) client for tool resolution.
Integrates with MCP servers for tool discovery and execution.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Union
import structlog

from .tool_resolver import ToolResolver, Tool, ToolSearchResult
from .wrapper_client import WrapperClient, WrapperServiceError

logger = structlog.get_logger()

class MCPError(Exception):
    """Exception raised for MCP protocol errors."""
    pass

class MCPClient(ToolResolver):
    """MCP client for JSON-RPC communication with MCP servers."""
    
    def __init__(self, 
                 mcp_server_url: str,
                 protocol_version: str = "2024-11-05",
                 timeout: float = 30.0):
        """
        Initialize MCP client.
        
        Args:
            mcp_server_url: URL of the MCP server
            protocol_version: MCP protocol version
            timeout: Request timeout
        """
        self.mcp_server_url = mcp_server_url
        self.protocol_version = protocol_version
        self.timeout = timeout
        
        # Use wrapper client for HTTP communication
        self.wrapper_client = WrapperClient(
            service_url=mcp_server_url,
            timeout=timeout
        )
        
        logger.info("MCPClient initialized",
                   server_url=mcp_server_url,
                   protocol_version=protocol_version)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.wrapper_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.wrapper_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _send_mcp_request(self, 
                              method: str, 
                              params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send MCP JSON-RPC request.
        
        Args:
            method: MCP method name
            params: Method parameters
            
        Returns:
            Response data
            
        Raises:
            MCPError: If request fails
        """
        request_id = str(uuid.uuid4())
        
        request_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        
        if params:
            request_data["params"] = params
        
        try:
            # Send via wrapper client
            response = await self.wrapper_client._request(
                "POST", 
                "/mcp/rpc",  # Assume MCP endpoint
                data=request_data
            )
            
            # Validate MCP response
            if "error" in response:
                error = response["error"]
                raise MCPError(f"MCP error {error.get('code', 'unknown')}: {error.get('message', 'Unknown error')}")
            
            return response.get("result", {})
        
        except WrapperServiceError as e:
            raise MCPError(f"MCP communication failed: {str(e)}")
    
    async def _initialize_session(self) -> Dict[str, Any]:
        """Initialize MCP session with server."""
        try:
            result = await self._send_mcp_request("initialize", {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": False},
                    "prompts": {"listChanged": False}
                },
                "clientInfo": {
                    "name": "notebook-sandbox",
                    "version": "1.0.0"
                }
            })
            
            logger.info("MCP session initialized", 
                       server_capabilities=result.get("capabilities", {}))
            
            return result
        
        except Exception as e:
            logger.error("MCP session initialization failed", error=str(e))
            raise MCPError(f"Session initialization failed: {str(e)}")
    
    async def resolve_tools(self, 
                           step_description: str,
                           tool_type: Optional[str] = None,
                           limit: int = 10,
                           threshold: float = 0.5) -> ToolSearchResult:
        """
        Resolve tools using MCP server.
        
        Args:
            step_description: Natural language description
            tool_type: Optional tool type filter
            limit: Maximum results
            threshold: Minimum confidence
            
        Returns:
            ToolSearchResult with matching tools
        """
        import time
        start_time = time.time()
        
        try:
            # First, list available tools
            tools_result = await self._send_mcp_request("tools/list")
            available_tools = tools_result.get("tools", [])
            
            # Convert MCP tools to our Tool format
            converted_tools = []
            for mcp_tool in available_tools:
                tool = self._convert_mcp_tool(mcp_tool)
                if tool:
                    # Calculate relevance score
                    score = self._calculate_relevance_score(
                        step_description, 
                        tool, 
                        tool_type
                    )
                    
                    if score >= threshold:
                        tool.confidence_score = score
                        converted_tools.append(tool)
            
            # Sort by confidence and apply limit
            converted_tools.sort(key=lambda t: t.confidence_score, reverse=True)
            converted_tools = converted_tools[:limit]
            
            search_time = time.time() - start_time
            
            logger.info("MCP tool resolution completed",
                       query=step_description,
                       found_tools=len(converted_tools),
                       search_time=search_time)
            
            return ToolSearchResult(
                query=step_description,
                tools=converted_tools,
                total_count=len(converted_tools),
                search_time=search_time,
                metadata={"resolver": "mcp", "mcp_server": self.mcp_server_url}
            )
        
        except Exception as e:
            logger.error("MCP tool resolution failed",
                        query=step_description,
                        error=str(e))
            raise MCPError(f"Tool resolution failed: {str(e)}")
    
    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get specific tool by ID via MCP.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Tool if found
        """
        try:
            # List all tools and find the one with matching ID
            tools_result = await self._send_mcp_request("tools/list")
            available_tools = tools_result.get("tools", [])
            
            for mcp_tool in available_tools:
                if mcp_tool.get("name") == tool_id:
                    return self._convert_mcp_tool(mcp_tool)
            
            return None
        
        except Exception as e:
            logger.error("MCP tool retrieval failed",
                        tool_id=tool_id,
                        error=str(e))
            return None
    
    async def list_tools(self, 
                        tool_type: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: int = 100) -> List[Tool]:
        """
        List tools via MCP server.
        
        Args:
            tool_type: Optional type filter
            category: Optional category filter
            limit: Maximum results
            
        Returns:
            List of available tools
        """
        try:
            tools_result = await self._send_mcp_request("tools/list")
            available_tools = tools_result.get("tools", [])
            
            converted_tools = []
            for mcp_tool in available_tools:
                tool = self._convert_mcp_tool(mcp_tool)
                if tool:
                    # Apply filters
                    if tool_type and tool.tool_type != tool_type:
                        continue
                    if category and tool.category != category:
                        continue
                    
                    converted_tools.append(tool)
            
            # Apply limit
            converted_tools = converted_tools[:limit]
            
            logger.info("MCP tools listed",
                       count=len(converted_tools),
                       total_available=len(available_tools))
            
            return converted_tools
        
        except Exception as e:
            logger.error("MCP tool listing failed", error=str(e))
            raise MCPError(f"Tool listing failed: {str(e)}")
    
    async def execute_tool(self, 
                          tool_id: str, 
                          arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool via MCP server.
        
        Args:
            tool_id: Tool identifier
            arguments: Tool arguments
            
        Returns:
            Execution result
        """
        try:
            result = await self._send_mcp_request("tools/call", {
                "name": tool_id,
                "arguments": arguments
            })
            
            logger.info("MCP tool executed",
                       tool_id=tool_id,
                       success=True)
            
            return {
                "success": True,
                "result": result,
                "tool_id": tool_id
            }
        
        except Exception as e:
            logger.error("MCP tool execution failed",
                        tool_id=tool_id,
                        error=str(e))
            return {
                "success": False,
                "error": str(e),
                "tool_id": tool_id
            }
    
    def _convert_mcp_tool(self, mcp_tool: Dict[str, Any]) -> Optional[Tool]:
        """
        Convert MCP tool definition to our Tool format.
        
        Args:
            mcp_tool: MCP tool definition
            
        Returns:
            Converted Tool or None
        """
        try:
            # Extract basic info
            name = mcp_tool.get("name", "")
            if not name:
                return None
            
            description = mcp_tool.get("description", "")
            input_schema = mcp_tool.get("inputSchema", {})
            
            # Determine tool type from schema or description
            tool_type = self._infer_tool_type(mcp_tool)
            
            # Extract tags from description or schema
            tags = self._extract_tags(mcp_tool)
            
            return Tool(
                id=name,
                name=name,
                description=description,
                tool_type=tool_type,
                input_schema=input_schema,
                output_schema=None,  # MCP doesn't specify output schemas
                execution_config={"mcp_server": self.mcp_server_url},
                tags=tags,
                category=self._infer_category(tool_type),
                confidence_score=0.0
            )
        
        except Exception as e:
            logger.warning("Failed to convert MCP tool",
                          tool_name=mcp_tool.get("name", "unknown"),
                          error=str(e))
            return None
    
    def _infer_tool_type(self, mcp_tool: Dict[str, Any]) -> str:
        """Infer tool type from MCP tool definition."""
        name = mcp_tool.get("name", "").lower()
        description = mcp_tool.get("description", "").lower()
        
        # SQL-related keywords
        if any(keyword in name or keyword in description 
               for keyword in ["sql", "query", "database", "db"]):
            return "sql"
        
        # API-related keywords
        if any(keyword in name or keyword in description 
               for keyword in ["api", "http", "rest", "request", "fetch"]):
            return "api"
        
        # File/filesystem keywords
        if any(keyword in name or keyword in description 
               for keyword in ["file", "read", "write", "filesystem"]):
            return "file"
        
        # Script/code keywords
        if any(keyword in name or keyword in description 
               for keyword in ["script", "execute", "run", "code"]):
            return "script"
        
        # Default
        return "mcp"
    
    def _extract_tags(self, mcp_tool: Dict[str, Any]) -> List[str]:
        """Extract tags from MCP tool definition."""
        tags = ["mcp"]
        
        name = mcp_tool.get("name", "").lower()
        description = mcp_tool.get("description", "").lower()
        
        # Add common tags based on keywords
        keyword_tags = {
            "database": ["database", "data"],
            "sql": ["sql", "query"],
            "api": ["api", "http"],
            "file": ["file", "io"],
            "script": ["script", "code"],
            "python": ["python", "script"],
            "shell": ["shell", "command"],
            "git": ["git", "version-control"],
            "docker": ["docker", "container"]
        }
        
        for keyword, tag_list in keyword_tags.items():
            if keyword in name or keyword in description:
                tags.extend(tag_list)
        
        return list(set(tags))  # Remove duplicates
    
    def _infer_category(self, tool_type: str) -> str:
        """Infer category from tool type."""
        category_mapping = {
            "sql": "data_access",
            "api": "integration", 
            "file": "file_system",
            "script": "computation",
            "mcp": "general"
        }
        return category_mapping.get(tool_type, "general")
    
    def _calculate_relevance_score(self, 
                                 query: str, 
                                 tool: Tool, 
                                 tool_type_filter: Optional[str]) -> float:
        """Calculate relevance score for a tool given a query."""
        score = 0.0
        query_lower = query.lower()
        
        # Tool type match bonus
        if tool_type_filter and tool.tool_type == tool_type_filter:
            score += 0.3
        
        # Name matching
        if any(word in tool.name.lower() for word in query_lower.split()):
            score += 0.4
        
        # Description matching
        description_words = tool.description.lower().split()
        query_words = query_lower.split()
        
        matching_words = sum(1 for word in query_words if word in description_words)
        if query_words:
            score += (matching_words / len(query_words)) * 0.3
        
        # Tag matching
        if tool.tags:
            tag_matches = sum(1 for tag in tool.tags if tag in query_lower)
            score += tag_matches * 0.1
        
        return min(score, 1.0)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MCP server health."""
        try:
            # Try to initialize session
            await self._initialize_session()
            
            return {
                "status": "healthy",
                "resolver_type": "mcp_client",
                "mcp_server": self.mcp_server_url,
                "protocol_version": self.protocol_version
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "resolver_type": "mcp_client",
                "mcp_server": self.mcp_server_url,
                "error": str(e)
            }