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


class TemplateType(str, Enum):
    """Enumeration for the types of templates supported by the cache."""
    SQL = "sql"
    URL = "url"
    API = "api"
    sql = "sql"
    WORKFLOW = "workflow"
    """Workflow templates store a JSON structure defining a series of steps referencing other cache entries.
    Expected JSON format in the 'template' field:
    {
        'steps': [
            {'cache_id': int, 'type': 'sequential' or 'parallel', 'description': str},
            ...
        ]
    }"""
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

    # Template handling fields
    is_template: bool = Column(Boolean, default=False, nullable=False, index=True)
    """Flag indicating if this entry contains placeholders for entity substitution."""
    entity_replacements: Optional[Dict[str, Any]] = Column(JSON)
    """JSON blob describing placeholders and their types for substitution.
       Example: {'entity_key': {'placeholder': ':placeholder_name', 'type': 'string'}}."""

    # Metadata fields
    reasoning_trace: Optional[str] = Column(Text)
    """Optional text explaining how the template was derived from the NL query."""
    tags: Optional[List[str]] = Column(JSON)
    """Optional list of strings for categorization or filtering."""
    catalog_type: Optional[str] = Column(String, index=True)
    """Optional catalog type for filtering cache entries."""
    catalog_subtype: Optional[str] = Column(String, index=True)
    """Optional catalog subtype for more specific filtering."""
    catalog_name: Optional[str] = Column(String, index=True)
    """Optional catalog name for precise filtering."""

    # Status field replacing is_valid and invalidation_reason
    status: str = Column(String, default=Status.ACTIVE, nullable=False, index=True)
    """Status of the cache entry (pending, active, archive). See Status enum."""

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
        if self.vector_embedding:
            try:
                # Assuming it's stored as a list in JSONB
                return np.array(self.vector_embedding, dtype=np.float32)
            except (TypeError, ValueError):
                logger.error(f"Could not convert stored embedding to numpy array for ID {self.id}", exc_info=True)
                return None
        return None

    @embedding.setter
    def embedding(self, value: Optional[np.ndarray]):
        """Set the vector embedding from a NumPy array, storing as list."""
        if value is not None:
            try:
                self.vector_embedding = value.tolist()
            except AttributeError:
                logger.error(f"Failed to convert numpy array to list for storage for ID {self.id}", exc_info=True)
                self.vector_embedding = None
        else:
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Ensure embedding is included, regardless of field name in database
            "embedding": self.vector_embedding if hasattr(self, 'vector_embedding') else (self.embedding if hasattr(self, 'embedding') else None)
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
        )

        # Handle embedding directly if provided (expecting list or ndarray)
        if "vector_embedding" in data and data["vector_embedding"] is not None:
            try:
                # We now store as list, so just assign if it's already a list
                if isinstance(data["vector_embedding"], list):
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
