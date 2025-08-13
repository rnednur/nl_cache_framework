"""
Notebook generator system with plugin architecture.
"""

from .base_generator import BaseNotebookGenerator
from .python_generator import PythonNotebookGenerator
from .cell_templates import CellTemplate, CellTemplateLibrary

__all__ = [
    "BaseNotebookGenerator",
    "PythonNotebookGenerator", 
    "CellTemplate",
    "CellTemplateLibrary",
]