"""
Abstract tool resolution interface and implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()

@dataclass
class Tool:
    """Represents a tool that can be invoked from a notebook."""
    
    id: str
    name: str
    description: str
    tool_type: str  # 'api', 'sql', 'script', 'mcp', etc.
    
    # Tool specification
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    
    # Execution details
    execution_config: Optional[Dict[str, Any]] = None
    
    # Metadata
    tags: List[str] = None
    category: Optional[str] = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "execution_config": self.execution_config,
            "tags": self.tags,
            "category": self.category,
            "confidence_score": self.confidence_score
        }

@dataclass 
class ToolSearchResult:
    """Result of a tool search operation."""
    
    query: str
    tools: List[Tool]
    total_count: int
    search_time: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "tools": [tool.to_dict() for tool in self.tools],
            "total_count": self.total_count,
            "search_time": self.search_time,
            "metadata": self.metadata or {}
        }

class ToolResolver(ABC):
    """Abstract base class for tool resolution."""
    
    @abstractmethod
    async def resolve_tools(self, 
                           step_description: str,
                           tool_type: Optional[str] = None,
                           limit: int = 10,
                           threshold: float = 0.5) -> ToolSearchResult:
        """
        Resolve tools for a given step description.
        
        Args:
            step_description: Natural language description of the step
            tool_type: Optional filter by tool type
            limit: Maximum number of tools to return
            threshold: Minimum confidence threshold
            
        Returns:
            ToolSearchResult with matching tools
        """
        pass
    
    @abstractmethod
    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """
        Get a specific tool by ID.
        
        Args:
            tool_id: Unique tool identifier
            
        Returns:
            Tool if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list_tools(self, 
                        tool_type: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: int = 100) -> List[Tool]:
        """
        List available tools with optional filtering.
        
        Args:
            tool_type: Optional filter by tool type
            category: Optional filter by category
            limit: Maximum number of tools to return
            
        Returns:
            List of available tools
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the tool resolver.
        
        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "resolver_type": self.__class__.__name__
        }

class MockToolResolver(ToolResolver):
    """Mock tool resolver for testing and development."""
    
    def __init__(self):
        """Initialize with some mock tools."""
        self.tools = [
            Tool(
                id="sql_query_1",
                name="Database Query Tool",
                description="Execute SQL queries against PostgreSQL database",
                tool_type="sql",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                execution_config={"database": "postgresql://localhost/mydb"},
                tags=["database", "sql", "query"],
                category="data_access"
            ),
            Tool(
                id="api_call_1", 
                name="REST API Client",
                description="Make HTTP requests to REST APIs",
                tool_type="api",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                        "headers": {"type": "object"},
                        "data": {"type": "object"}
                    }
                },
                output_schema={"type": "object", "properties": {"response": {"type": "object"}}},
                tags=["api", "http", "rest"],
                category="integration"
            ),
            Tool(
                id="python_script_1",
                name="Python Script Executor", 
                description="Execute Python code snippets",
                tool_type="script",
                input_schema={"type": "object", "properties": {"code": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"output": {"type": "string"}}},
                tags=["python", "script", "code"],
                category="computation"
            )
        ]
    
    async def resolve_tools(self, 
                           step_description: str,
                           tool_type: Optional[str] = None,
                           limit: int = 10,
                           threshold: float = 0.5) -> ToolSearchResult:
        """Mock tool resolution based on simple keyword matching."""
        import time
        start_time = time.time()
        
        # Simple keyword matching
        step_lower = step_description.lower()
        matching_tools = []
        
        for tool in self.tools:
            if tool_type and tool.tool_type != tool_type:
                continue
            
            # Calculate simple confidence based on keyword matches
            confidence = 0.0
            description_lower = tool.description.lower()
            name_lower = tool.name.lower()
            
            # Check for keyword matches
            keywords = step_lower.split()
            for keyword in keywords:
                if keyword in description_lower:
                    confidence += 0.3
                if keyword in name_lower:
                    confidence += 0.5
                if keyword in tool.tags:
                    confidence += 0.2
            
            # Normalize confidence
            confidence = min(confidence, 1.0)
            
            if confidence >= threshold:
                tool.confidence_score = confidence
                matching_tools.append(tool)
        
        # Sort by confidence
        matching_tools.sort(key=lambda t: t.confidence_score, reverse=True)
        
        # Apply limit
        matching_tools = matching_tools[:limit]
        
        search_time = time.time() - start_time
        
        logger.info("Tool resolution completed",
                   query=step_description,
                   found_tools=len(matching_tools),
                   search_time=search_time)
        
        return ToolSearchResult(
            query=step_description,
            tools=matching_tools,
            total_count=len(matching_tools),
            search_time=search_time,
            metadata={"resolver": "mock"}
        )
    
    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get tool by ID."""
        for tool in self.tools:
            if tool.id == tool_id:
                return tool
        return None
    
    async def list_tools(self, 
                        tool_type: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: int = 100) -> List[Tool]:
        """List tools with filtering."""
        filtered_tools = []
        
        for tool in self.tools:
            if tool_type and tool.tool_type != tool_type:
                continue
            if category and tool.category != category:
                continue
            filtered_tools.append(tool)
        
        return filtered_tools[:limit]