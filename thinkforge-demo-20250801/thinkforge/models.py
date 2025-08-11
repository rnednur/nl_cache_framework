from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    Float,
    Boolean,
    DateTime,
    create_engine,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import numpy as np
import json
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)

# Get database schema from environment variable or use default
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")
logger.info(f"Using database schema: {DB_SCHEMA}")

# Use a generic Base, applications using the library will need to ensure
# this Base is part of their metadata if they use declarative models elsewhere.
# Alternatively, the application could provide its own Base.
Base = declarative_base()

# Define USE_PG_VECTOR at module level for import
try:
    from pgvector.sqlalchemy import Vector
    import os
    USE_PG_VECTOR = os.getenv('USE_PG_VECTOR', 'false').lower() == 'true'
except ImportError:
    USE_PG_VECTOR = False


class TemplateType(str, Enum):
    """Enumeration for the types of templates supported by the cache."""
    SQL = "sql"  # SQL query templates
    URL = "url"  # URL templates for API calls
    API = "api"  # API templates from Swagger/OpenAPI specs
    WORKFLOW = "workflow"
    """Workflow templates store a JSON structure defining a series of steps referencing other cache entries.
    Expected JSON format in the 'template' field:
    {
        'steps': [
            {'cache_id': int, 'type': 'sequential' or 'parallel', 'description': str},
            ...
        ]
    }
    These workflows can include Stagehand steps for browser-based automation, where each step may define specific browser actions or interactions."""
    GRAPHQL = "graphql"
    REGEX = "regex"
    SCRIPT = "script"
    """Script templates may include executable code in languages like Python or JavaScript.
    For visualization purposes, the template JSON may include 'visualization_type' and 'script' fields.
    Example JSON format in the 'template' field for visualization:
    {
        'code': str,
        'language': 'python' or 'javascript',
        'visualization_type': 'chart' or 'graph' or etc.,
        'script': str (optional executable script for rendering)
    }"""
    NOSQL = "nosql"
    CLI = "cli"
    PROMPT = "prompt"
    CONFIGURATION = "configuration"
    REASONING_STEPS = "reasoning_steps"
    """Reasoning steps templates capture step-by-step logical reasoning or problem-solving approaches.
    This can be used for documenting thought processes, mathematical proofs, or decision trees."""
    DSL = "dsl"
    """Domain Specific Language components for structured query building.
    DSL templates store individual query components that can be composed together.
    Expected JSON format in the 'template' field:
    {
        'component_type': 'TABLE' | 'COLUMN' | 'JOIN' | 'FILTER' | 'AGGREGATE' | 'GROUP_BY' | 'ORDER_BY' | 'LIMIT',
        'component_data': {
            // Component-specific data structure
            'table_name': str,          // For TABLE type
            'column_name': str,         // For COLUMN type  
            'join_condition': str,      // For JOIN type
            'filter_condition': str,    // For FILTER type
            'aggregate_function': str,  // For AGGREGATE type
            'group_columns': [str],     // For GROUP_BY type
            'order_columns': [str],     // For ORDER_BY type
            'limit_count': int          // For LIMIT type
        },
        'metadata': {
            'database_schema': str,
            'data_type': str,
            'nullable': bool,
            'description': str
        }
    }
    This enables compositional query building from reusable semantic components."""
    
    # Tool Hub specific template types
    MCP_TOOL = "mcp_tool"
    """Model Context Protocol (MCP) tools for extensible AI functionality.
    MCP tool templates define server connections and available tool specifications.
    Expected JSON format in the 'template' field:
    {
        'server_config': {
            'name': str,
            'command': str,
            'args': [str],
            'env': {str: str}
        },
        'tool_spec': {
            'name': str,
            'description': str,
            'input_schema': dict,
            'capabilities': [str]
        },
        'connection_params': {
            'timeout': int,
            'retry_count': int
        }
    }
    This enables integration with MCP-compatible tools and services."""
    
    AGENT = "agent"
    """AI Agent definitions for autonomous task execution.
    Agent templates define AI agents with specific capabilities and configurations.
    Expected JSON format in the 'template' field:
    {
        'agent_config': {
            'name': str,
            'description': str,
            'model': str,
            'temperature': float,
            'max_tokens': int
        },
        'capabilities': [str],
        'tools': [str],
        'system_prompt': str,
        'execution_params': {
            'max_iterations': int,
            'timeout': int,
            'memory_enabled': bool
        }
    }
    This enables creation and management of specialized AI agents."""
    
    FUNCTION = "function"
    """Reusable function definitions for various programming languages.
    Function templates store executable code with parameter definitions.
    Expected JSON format in the 'template' field:
    {
        'function_def': {
            'name': str,
            'description': str,
            'language': 'python' | 'javascript' | 'bash' | 'powershell',
            'code': str,
            'entry_point': str
        },
        'parameters': {
            'required': [str],
            'optional': [str],
            'schema': dict
        },
        'execution_config': {
            'timeout': int,
            'memory_limit': int,
            'allowed_imports': [str]
        }
    }
    This enables reusable function libraries with proper parameter validation."""
    
    # Recipe Hub specific template types
    RECIPE = "recipe"
    """Complete automation recipes defining multi-step workflows.
    Recipe templates orchestrate multiple tools and steps to achieve complex automation goals.
    Expected JSON format in the 'template' field:
    {
        'recipe_metadata': {
            'name': str,
            'description': str,
            'version': str,
            'author': str,
            'category': str
        },
        'steps': [
            {
                'id': str,
                'name': str,
                'type': 'tool' | 'recipe_step' | 'conditional' | 'parallel',
                'tool_id': int,  # Reference to tool cache entry
                'parameters': dict,
                'depends_on': [str],  # Step IDs this step depends on
                'retry_config': {
                    'max_attempts': int,
                    'delay_seconds': int
                }
            }
        ],
        'execution_config': {
            'timeout_seconds': int,
            'parallel_limit': int,
            'fail_fast': bool
        },
        'input_schema': dict,
        'output_schema': dict
    }
    This enables complete workflow automation with tool orchestration."""
    
    RECIPE_STEP = "recipe_step"
    """Individual recipe steps that can be composed into larger workflows.
    Recipe steps are reusable building blocks for common automation patterns.
    Expected JSON format in the 'template' field:
    {
        'step_metadata': {
            'name': str,
            'description': str,
            'category': str,
            'complexity_level': 'beginner' | 'intermediate' | 'advanced'
        },
        'step_definition': {
            'type': 'action' | 'condition' | 'loop' | 'transform',
            'implementation': dict,  # Step-specific implementation details
            'error_handling': {
                'on_error': 'fail' | 'continue' | 'retry',
                'fallback_action': dict
            }
        },
        'interface': {
            'inputs': dict,  # Input parameter schema
            'outputs': dict,  # Output parameter schema
            'side_effects': [str]  # Description of side effects
        }
    }
    This enables modular recipe composition from reusable steps."""
    
    RECIPE_TEMPLATE = "recipe_template"
    """Parameterized recipe templates for common automation patterns.
    Recipe templates provide configurable workflows that can be instantiated with specific parameters.
    Expected JSON format in the 'template' field:
    {
        'template_metadata': {
            'name': str,
            'description': str,
            'use_cases': [str],
            'industry_tags': [str]
        },
        'parameters': {
            'required': [str],
            'optional': [str],
            'parameter_schemas': {
                'param_name': {
                    'type': str,
                    'description': str,
                    'default': any,
                    'validation': dict
                }
            }
        },
        'recipe_blueprint': {
            'steps': [dict],  # Template steps with parameter placeholders
            'conditional_logic': dict,
            'error_scenarios': dict
        },
        'instantiation_examples': [
            {
                'name': str,
                'description': str,
                'parameter_values': dict
            }
        ]
    }
    This enables parameterized recipe creation for common automation patterns."""


class Status(str, Enum):
    """Enumeration for the status of cache entries."""
    PENDING = "pending"
    ACTIVE = "active"
    ARCHIVE = "archive"


class Text2SQLCache(Base):
    """Database model for storing cached Text-to-Template entries."""
    __tablename__ = "text2sql_cache"
    __table_args__ = {"schema": DB_SCHEMA}

    id: int = Column(Integer, primary_key=True, index=True)
    """Unique identifier for the cache entry."""

    nl_query: str = Column(String, index=True, nullable=False)
    """The original natural language query."""

    template: str = Column(Text, nullable=False)
    """The template (SQL, URL, API spec, etc.) corresponding to the NL query. For certain template types like 'workflow' or visualization-related types, this may contain JSON with additional metadata such as visualization_type and script."""

    template_type: str = Column(
        String, default=TemplateType.SQL, nullable=False, index=True
    )
    """Type of the template (sql, url, api, workflow). See TemplateType enum."""

    # Embedding storage using JSONB
    vector_embedding: Optional[list] = Column(JSONB)
    """JSONB list representation of the vector embedding for the nl_query."""
    
    # Conditional vector column for pg_vector extension if enabled
    if USE_PG_VECTOR:
        pg_vector: Optional[list] = Column(Vector(768))  # Adjust dimension based on your embedding model
        """Vector column for pg_vector extension when enabled."""

    # Template handling fields
    is_template: bool = Column(Boolean, default=False, nullable=False, index=True)
    """Flag indicating if this entry contains placeholders for entity substitution."""
    entity_replacements: Optional[Dict[str, Any]] = Column(JSON)
    """JSON blob describing placeholders and their types for substitution.
       Example: {'entity_key': {'placeholder': ':placeholder_name', 'type': 'string'}}."""

    # Metadata fields
    reasoning_trace: Optional[str] = Column(Text)
    """Optional text explaining how the template was derived from the NL query."""
    tags: Optional[Dict[str, List[str]]] = Column(JSON)
    """Optional name-value pairs for categorization or filtering. Keys are tag names, values are lists of strings."""
    catalog_type: Optional[str] = Column(String, index=True)
    """Optional catalog type for filtering cache entries."""
    catalog_subtype: Optional[str] = Column(String, index=True)
    """Optional catalog subtype for more specific filtering."""
    catalog_name: Optional[str] = Column(String, index=True)
    """Optional catalog name for precise filtering."""

    # Status field replacing is_valid and invalidation_reason
    status: str = Column(String, default=Status.ACTIVE, nullable=False, index=True)
    """Status of the cache entry (pending, active, archive). See Status enum."""

    # Tool-specific metadata fields
    tool_capabilities: Optional[List[str]] = Column(JSON)
    """JSON array of capabilities that the tool provides (e.g., ['image_processing', 'pdf_conversion'])."""
    
    tool_dependencies: Optional[Dict[str, Any]] = Column(JSON)
    """JSON object describing tool dependencies and requirements.
       Example: {'api_keys': ['OPENAI_API_KEY'], 'services': ['docker'], 'python_packages': ['requests']}."""
    
    execution_config: Optional[Dict[str, Any]] = Column(JSON)
    """JSON object for execution parameters and constraints.
       Example: {'timeout': 300, 'retry_count': 3, 'memory_limit': '1GB', 'concurrent_limit': 5}."""
    
    health_status: Optional[str] = Column(String, index=True)
    """Current health status of the tool ('healthy', 'degraded', 'unhealthy', 'unknown')."""
    
    last_tested: Optional[datetime.datetime] = Column(DateTime)
    """Timestamp of when the tool was last validated or tested."""

    # Recipe-specific metadata fields
    recipe_steps: Optional[List[Dict[str, Any]]] = Column(JSON)
    """JSON array of recipe steps with execution order, dependencies, and parameters.
       Example: [{'id': 'step1', 'tool_id': 123, 'parameters': {...}, 'depends_on': []}]."""
    
    required_tools: Optional[List[int]] = Column(JSON)
    """JSON array of tool cache entry IDs that this recipe depends on for execution."""
    
    execution_time_estimate: Optional[int] = Column(Integer)
    """Estimated execution time in seconds for the complete recipe."""
    
    complexity_level: Optional[str] = Column(String, index=True)
    """Recipe complexity level ('beginner', 'intermediate', 'advanced') for user guidance."""
    
    success_rate: Optional[float] = Column(Float)
    """Historical success rate percentage (0-100) based on execution history."""
    
    last_executed: Optional[datetime.datetime] = Column(DateTime)
    """Timestamp of when the recipe was last executed."""
    
    execution_count: Optional[int] = Column(Integer, default=0)
    """Total number of times this recipe has been executed."""

    # Timestamps
    created_at: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: datetime.datetime = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    # REINSTATE embedding property getter/setter for numpy conversion
    @property
    def embedding(self) -> Optional[np.ndarray]:
        """Return the vector embedding as a NumPy array."""
        if hasattr(self, 'pg_vector') and USE_PG_VECTOR and self.pg_vector is not None:
            try:
                return np.array(self.pg_vector, dtype=np.float32)
            except (TypeError, ValueError):
                logger.error(f"Could not convert pg_vector to numpy array for ID {self.id}", exc_info=True)
                return None
        elif self.vector_embedding:
            try:
                # Assuming it's stored as a list in JSONB
                return np.array(self.vector_embedding, dtype=np.float32)
            except (TypeError, ValueError):
                logger.error(f"Could not convert stored embedding to numpy array for ID {self.id}", exc_info=True)
                return None
        return None

    @embedding.setter
    def embedding(self, value: Optional[np.ndarray]):
        """Set the vector embedding from a NumPy array, storing as list or pg_vector."""
        if value is not None:
            try:
                if hasattr(self, 'pg_vector') and USE_PG_VECTOR:
                    self.pg_vector = value
                else:
                    self.vector_embedding = value.tolist()
            except AttributeError:
                logger.error(f"Failed to convert numpy array to list for storage for ID {self.id}", exc_info=True)
                self.vector_embedding = None
        else:
            if hasattr(self, 'pg_vector') and USE_PG_VECTOR:
                self.pg_vector = None
            self.vector_embedding = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the cache entry to a dictionary.
        """
        result = {
            "id": self.id,
            "nl_query": self.nl_query,
            "template": self.template,
            "template_type": self.template_type,
            "is_template": self.is_template,
            "entity_replacements": self.entity_replacements,
            "reasoning_trace": self.reasoning_trace,
            "tags": self.tags,
            "catalog_type": self.catalog_type,
            "catalog_subtype": self.catalog_subtype,
            "catalog_name": self.catalog_name,
            "status": self.status,
            # Tool-specific fields
            "tool_capabilities": self.tool_capabilities,
            "tool_dependencies": self.tool_dependencies,
            "execution_config": self.execution_config,
            "health_status": self.health_status,
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            # Recipe-specific fields
            "recipe_steps": self.recipe_steps,
            "required_tools": self.required_tools,
            "execution_time_estimate": self.execution_time_estimate,
            "complexity_level": self.complexity_level,
            "success_rate": self.success_rate,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "execution_count": self.execution_count,
            # Timestamps
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Ensure embedding is included, regardless of field name in database
            "embedding": self.vector_embedding if hasattr(self, 'vector_embedding') and not (hasattr(self, 'pg_vector') and USE_PG_VECTOR) else (self.pg_vector if hasattr(self, 'pg_vector') and USE_PG_VECTOR else None)
        }
        return result

    def __repr__(self):
        return f"<Text2SQLCache(id={self.id}, nl_query='{self.nl_query[:30]}...', template_type='{self.template_type}')>"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Text2SQLCache":
        """Create a model instance from a dictionary"""
        # Handle backward compatibility for sql_query field
        template = data.get("template")
        if template is None and "sql_query" in data:
            template = data.get("sql_query")
            logger.info("Used legacy 'sql_query' field instead of 'template'")

        # Handle backward compatibility for cache_type field
        is_template = data.get("is_template")
        if is_template is None and "cache_type" in data:
            is_template = str(data.get("cache_type")).lower() == "template"
            logger.info("Used legacy 'cache_type' field to determine 'is_template'")

        instance = cls(
            id=data.get("id"),
            is_template=bool(is_template) if is_template is not None else False,
            template_type=data.get("template_type", TemplateType.SQL),
            nl_query=data.get("nl_query"),
            template=template,
            entity_replacements=data.get("entity_replacements"),
            reasoning_trace=data.get("reasoning_trace"),
            tags=data.get("tags"),
            catalog_type=data.get("catalog_type"),
            catalog_subtype=data.get("catalog_subtype"),
            catalog_name=data.get("catalog_name"),
            status=data.get("status", Status.ACTIVE),
            # Tool-specific fields
            tool_capabilities=data.get("tool_capabilities"),
            tool_dependencies=data.get("tool_dependencies"),
            execution_config=data.get("execution_config"),
            health_status=data.get("health_status"),
            last_tested=data.get("last_tested"),
            # Recipe-specific fields
            recipe_steps=data.get("recipe_steps"),
            required_tools=data.get("required_tools"),
            execution_time_estimate=data.get("execution_time_estimate"),
            complexity_level=data.get("complexity_level"),
            success_rate=data.get("success_rate"),
            last_executed=data.get("last_executed"),
            execution_count=data.get("execution_count", 0),
        )

        # Handle embedding directly if provided (expecting list or ndarray)
        if "vector_embedding" in data and data["vector_embedding"] is not None:
            try:
                # We now store as list, so just assign if it's already a list
                if isinstance(data["vector_embedding"], list):
                    if USE_PG_VECTOR and hasattr(instance, 'pg_vector'):
                        instance.pg_vector = data["vector_embedding"]
                    else:
                        instance.vector_embedding = data["vector_embedding"]
                # If it's an ndarray, use the setter to convert to list
                elif isinstance(data["vector_embedding"], np.ndarray):
                    instance.embedding = data["vector_embedding"] # Use setter
                else:
                     logger.warning(f"Unexpected format for vector_embedding in from_dict: {type(data['vector_embedding'])}")
            except Exception as e:
                logger.error(f"Error processing vector_embedding in from_dict: {e}")
        return instance


# --- NEW Usage Log Model ---
class UsageLog(Base):
    """Database model for logging cache usage events."""
    __tablename__ = "usage_log"
    __table_args__ = {"schema": DB_SCHEMA}

    id: int = Column(Integer, primary_key=True)
    """Unique identifier for the log entry."""

    cache_entry_id: Optional[int] = Column(Integer, ForeignKey(f"{DB_SCHEMA}.text2sql_cache.id", ondelete="SET NULL"), nullable=True, index=True)
    """The ID of the cache entry that was used, if any."""

    timestamp: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    """Timestamp when the cache entry was used."""

    prompt: Optional[str] = Column(Text, nullable=True)
    """The natural language query or prompt from the request."""

    response: Optional[str] = Column(Text, nullable=True)
    """The response or template returned for the request."""

    success_status: Optional[bool] = Column(Boolean, nullable=True)
    """Flag indicating if the request was successfully processed."""

    similarity_score: Optional[float] = Column(Float, nullable=True)
    """Similarity score of the matched cache entry, if applicable."""

    error_message: Optional[str] = Column(Text, nullable=True)
    """Error message if the request processing failed."""

    catalog_type: Optional[str] = Column(String, nullable=True)
    """Catalog type associated with the request, if provided."""

    catalog_subtype: Optional[str] = Column(String, nullable=True)
    """Catalog subtype associated with the request, if provided."""

    catalog_name: Optional[str] = Column(String, nullable=True)
    """Catalog name associated with the request, if provided."""
    
    llm_used: Optional[bool] = Column(Boolean, default=False, nullable=True)
    """Flag indicating if LLM enhancement was used for this request."""

    considered_entries: Optional[list] = Column(JSON, nullable=True)
    """JSON array of cache entry IDs that were considered during processing."""

    is_confident: Optional[bool] = Column(Boolean, nullable=True)
    """Flag indicating the confidence level of the response, particularly for LLM-enhanced results."""

    # Optional: Define relationship for easier access from log to entry
    cache_entry = relationship("Text2SQLCache")

    def __repr__(self):
        return f"<UsageLog(id={self.id}, cache_entry_id={self.cache_entry_id}, timestamp='{self.timestamp}')>"

# --- End NEW Usage Log Model ---

# --- NEW Cache Audit Log Model ---
class CacheAuditLog(Base):
    """Database model for logging changes to cache entries."""
    __tablename__ = "cache_audit_log"
    __table_args__ = {"schema": DB_SCHEMA}

    id: int = Column(Integer, primary_key=True)
    """Unique identifier for the audit log entry."""

    cache_entry_id: int = Column(Integer, ForeignKey(f"{DB_SCHEMA}.text2sql_cache.id", ondelete="CASCADE"), nullable=False, index=True)
    """The ID of the cache entry that was modified."""

    changed_field: str = Column(String, nullable=False)
    """The field that was changed (e.g., 'status', 'template')."""

    old_value: Optional[str] = Column(Text, nullable=True)
    """The old value of the field before the change."""

    new_value: Optional[str] = Column(Text, nullable=True)
    """The new value of the field after the change."""

    change_reason: Optional[str] = Column(Text, nullable=True)
    """Optional reason or comment for the change."""

    changed_by: Optional[str] = Column(String, nullable=True)
    """Optional identifier of the user or system component that made the change."""

    timestamp: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    """Timestamp when the change occurred."""

    # Relationship for easier access from log to entry
    cache_entry = relationship("Text2SQLCache")

    def __repr__(self):
        return f"<CacheAuditLog(id={self.id}, cache_entry_id={self.cache_entry_id}, changed_field='{self.changed_field}', timestamp='{self.timestamp}')>"
# --- End NEW Cache Audit Log Model ---

# Helper function to create database engine (optional)
# def create_db_engine(db_url: str):
#     return create_engine(db_url)

# Helper function to create session (optional)
# def get_db_session(engine):
#     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     return SessionLocal()
