"""
Natural Language to SQL/Template Caching Framework.

This package provides a framework for caching natural language to SQL/template translations,
with tools for similarity search, entity substitution, and various template types.
"""

import logging
from logging import NullHandler

from .controller import Text2SQLController
from .models import TemplateType, Text2SQLCache, Base
from .entity_substitution import Text2SQLEntitySubstitution
from .similarity import Text2SQLSimilarity

# Configure basic logging for the library
# Applications using the library should configure their own handlers
logging.getLogger(__name__).addHandler(NullHandler())

__version__ = "0.1.0"

__all__ = [
    "Text2SQLController",
    "TemplateType",
    "Text2SQLCache",
    "Text2SQLEntitySubstitution",
    "Text2SQLSimilarity",
    "Base",
    "__version__",
]
