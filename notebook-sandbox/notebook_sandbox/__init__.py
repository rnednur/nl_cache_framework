"""
Notebook Sandbox - Secure notebook execution environment

A reusable package for secure execution of Jupyter notebooks with 
wrapper service integration for tool resolution and execution.
"""

__version__ = "1.0.0"
__author__ = "ThinkForge Team"
__email__ = "team@thinkforge.dev"

# Core components
from .core.executor import NotebookExecutor
from .core.container_manager import ContainerManager
from .core.validator import NotebookValidator

# Generator system
from .generators.base_generator import BaseNotebookGenerator
from .generators.python_generator import PythonNotebookGenerator

# Integration clients
from .integrations.wrapper_client import WrapperClient
from .integrations.tool_resolver import ToolResolver

# Configuration
from .config.security import SecurityConfig
from .config.resources import ResourceConfig

__all__ = [
    # Core
    "NotebookExecutor",
    "ContainerManager", 
    "NotebookValidator",
    
    # Generators
    "BaseNotebookGenerator",
    "PythonNotebookGenerator",
    
    # Integrations
    "WrapperClient",
    "ToolResolver",
    
    # Configuration
    "SecurityConfig",
    "ResourceConfig",
    
    # Metadata
    "__version__",
    "__author__",
    "__email__",
]