"""
Base notebook generator interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()

@dataclass
class NotebookMetadata:
    """Metadata for generated notebooks."""
    
    title: str
    description: Optional[str] = None
    tags: List[str] = None
    author: Optional[str] = None
    created_by: str = "notebook-sandbox"
    kernel_name: str = "python3"
    language: str = "python"
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to notebook metadata format."""
        return {
            "kernelspec": {
                "display_name": f"Python 3 ({self.kernel_name})",
                "language": self.language,
                "name": self.kernel_name
            },
            "language_info": {
                "name": self.language,
                "version": "3.11.0"
            },
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "author": self.author,
            "created_by": self.created_by
        }

@dataclass
class GenerationRequest:
    """Request for notebook generation."""
    
    content: Dict[str, Any]  # DSL content or other input
    workflow_name: str
    metadata: Optional[NotebookMetadata] = None
    options: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = NotebookMetadata(
                title=self.workflow_name,
                description=f"Generated notebook for workflow: {self.workflow_name}"
            )
        if self.options is None:
            self.options = {}

@dataclass
class GenerationResult:
    """Result of notebook generation."""
    
    notebook_content: str  # JSON string of notebook
    cell_count: int
    success: bool = True
    error: Optional[str] = None
    warnings: List[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}

class BaseNotebookGenerator(ABC):
    """Abstract base class for notebook generators."""
    
    def __init__(self, name: str):
        """Initialize generator with a name."""
        self.name = name
        self.logger = structlog.get_logger().bind(generator=name)
    
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate a notebook from the given request.
        
        Args:
            request: Generation request with content and metadata
            
        Returns:
            GenerationResult with notebook content or error
        """
        pass
    
    @abstractmethod
    def validate_input(self, content: Dict[str, Any]) -> bool:
        """
        Validate that the input content is supported by this generator.
        
        Args:
            content: Input content to validate
            
        Returns:
            True if content is valid for this generator
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported input formats.
        
        Returns:
            List of format names this generator supports
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get generator information.
        
        Returns:
            Dictionary with generator metadata
        """
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "supported_formats": self.get_supported_formats()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check generator health.
        
        Returns:
            Health status information
        """
        return {
            "generator": self.name,
            "status": "healthy",
            "class": self.__class__.__name__
        }