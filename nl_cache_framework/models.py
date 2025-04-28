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

# Setup logger
logger = logging.getLogger(__name__)

# Use a generic Base, applications using the library will need to ensure
# this Base is part of their metadata if they use declarative models elsewhere.
# Alternatively, the application could provide its own Base.
Base = declarative_base()


class TemplateType(str, Enum):
    """Enumeration for the types of templates supported by the cache."""
    SQL = "sql"
    URL = "url"
    API = "api"
    WORKFLOW = "workflow"


class Text2SQLCache(Base):
    """Database model for storing cached Text-to-Template entries."""
    __tablename__ = "text2sql_cache"

    id: int = Column(Integer, primary_key=True, index=True)
    """Unique identifier for the cache entry."""

    nl_query: str = Column(String, index=True, nullable=False)
    """The original natural language query."""

    template: str = Column(Text, nullable=False)
    """The template (SQL, URL, API spec, etc.) corresponding to the NL query."""

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
    suggested_visualization: Optional[str] = Column(String)
    """Optional hint for how the result of the template might be visualized."""
    database_name: Optional[str] = Column(String, index=True)
    """Optional identifier for the target database, if applicable."""
    schema_name: Optional[str] = Column(String, index=True)
    """Optional identifier for the target schema, if applicable."""
    catalog_id: Optional[int] = Column(Integer, index=True)
    """Optional identifier linking to an external data catalog."""

    # Tracking and validity
    is_valid: bool = Column(Boolean, default=True, nullable=False, index=True)
    """Flag indicating if the cache entry is currently considered valid."""
    invalidation_reason: Optional[str] = Column(String)
    """Optional reason why the entry was marked as invalid."""

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
        """Convert the SQLAlchemy model instance to a dictionary.

        Excludes the vector_embedding by default.
        Includes common fields.
        """
        d = {}
        for col in self.__table__.columns:
            # Exclude vector embedding by default from general dict representation
            if col.name == "vector_embedding":
                continue
            val = getattr(self, col.name)
            # Convert datetime objects to ISO format string
            if isinstance(val, datetime.datetime):
                 d[col.name] = val.isoformat()
            else:
                 d[col.name] = val
        return d

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
            suggested_visualization=data.get("suggested_visualization"),
            database_name=data.get("database_name"),
            schema_name=data.get("schema_name"),
            catalog_id=data.get("catalog_id"),
            is_valid=data.get("is_valid", True),
            invalidation_reason=data.get("invalidation_reason"),
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

    id: int = Column(Integer, primary_key=True)
    """Unique identifier for the log entry."""

    cache_entry_id: int = Column(Integer, ForeignKey("text2sql_cache.id"), nullable=False, index=True)
    """The ID of the cache entry that was used."""

    timestamp: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    """Timestamp when the cache entry was used."""

    # Optional: Define relationship for easier access from log to entry
    cache_entry = relationship("Text2SQLCache")

    def __repr__(self):
        return f"<UsageLog(id={self.id}, cache_entry_id={self.cache_entry_id}, timestamp='{self.timestamp}')>"

# --- End NEW Usage Log Model ---

# Helper function to create database engine (optional)
# def create_db_engine(db_url: str):
#     return create_engine(db_url)

# Helper function to create session (optional)
# def get_db_session(engine):
#     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     return SessionLocal()
