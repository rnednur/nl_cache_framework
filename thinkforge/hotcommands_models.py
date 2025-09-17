"""
Hot Commands models for ThinkForge Framework Integration
Extends ThinkForge with slash command and spaces functionality
"""

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
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import datetime
import os

# Import base from main models
from .models import Base, DB_SCHEMA

class CommandStatus(str, Enum):
    """Status enumeration for hot commands."""
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    PRIVATE = "private"

class CommandQueryType(str, Enum):
    """Query type enumeration for hot commands."""
    NL2SQL = "nl2sql"
    DIRECT_SQL = "direct_sql"
    TOOL_CALL = "tool_call"
    WORKFLOW = "workflow"

class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PENDING = "pending"

class SpaceType(str, Enum):
    """Space type enumeration."""
    PERSONAL = "personal"
    TEAM = "team"
    PUBLIC = "public"
    TEMPORARY = "temporary"

class ContentType(str, Enum):
    """Content type enumeration for spaces."""
    QUERY_RESULT = "query_result"
    TEMPLATE = "template"
    VISUALIZATION = "visualization"
    REPORT = "report"
    DASHBOARD = "dashboard"
    DATASET = "dataset"
    WEBPAGE = "webpage"

class FeedbackType(str, Enum):
    """Feedback type enumeration."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    COMMENT = "comment"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"

class Priority(str, Enum):
    """Priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class StorageBackend(str, Enum):
    """Storage backend enumeration for external storage."""
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"

class ScheduleType(str, Enum):
    """Schedule type enumeration for space automation."""
    NONE = "none"
    INTERVAL = "interval"
    CRON = "cron"
    WEBHOOK = "webhook"

class AccessLevel(str, Enum):
    """Access level enumeration for space permissions."""
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"
    ADMIN = "admin"

# Set table args based on schema configuration
table_args = {"schema": DB_SCHEMA} if DB_SCHEMA != "public" else {}

class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"
    __table_args__ = table_args

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # User preferences and metadata
    domains = Column(ARRAY(String), nullable=True)
    permissions = Column(ARRAY(String), nullable=True) 
    roles = Column(ARRAY(String), nullable=True)
    preferences = Column(JSONB, nullable=True)
    command_count = Column(Integer, default=0)
    favorite_commands = Column(ARRAY(String), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    hot_commands = relationship("HotCommand", back_populates="user", cascade="all, delete-orphan")
    command_executions = relationship("CommandExecution", back_populates="user", cascade="all, delete-orphan")
    spaces = relationship("Space", back_populates="owner", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

class HotCommand(Base):
    """Hot command model for storing user-created command shortcuts."""
    __tablename__ = "hot_commands"
    __table_args__ = table_args

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA != "public" else "users.id"), nullable=False, index=True)
    
    # Command identification
    command_name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Query definition
    query_text = Column(Text, nullable=False)
    query_type = Column(String(20), nullable=False, default=CommandQueryType.NL2SQL)
    original_command = Column(Text, nullable=True)
    
    # Connection to ThinkForge cache entry (no foreign key constraint for now)
    cache_entry_id = Column(Integer, nullable=True, index=True)
    
    # Inherited metadata from cache entry (cached for performance)
    source_template_type = Column(String(50), nullable=True, index=True)  # From cache entry template_type
    source_reasoning = Column(Text, nullable=True)  # From cache entry reasoning_trace
    source_tags = Column(JSONB, nullable=True)  # From cache entry tags
    source_execution_stats = Column(JSONB, nullable=True)  # Cached stats: success_rate, execution_count, etc.
    
    # Categorization
    domain = Column(String(50), nullable=True, index=True)
    category = Column(String(50), nullable=True, index=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # Parameters and configuration
    parameters = Column(JSONB, nullable=True)
    parameter_schema = Column(JSONB, nullable=True)
    default_values = Column(JSONB, nullable=True)
    
    # Status and permissions
    status = Column(String(20), nullable=False, default=CommandStatus.ACTIVE, index=True)
    is_public = Column(Boolean, default=False, nullable=False, index=True)
    is_template = Column(Boolean, default=False, nullable=False)
    shared_with = Column(ARRAY(Integer), nullable=True)
    team_id = Column(String(50), nullable=True)
    permissions = Column(JSONB, nullable=True)
    
    # Usage statistics
    usage_count = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)
    avg_execution_time = Column(Float, nullable=True)  # in milliseconds
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # User feedback
    rating = Column(Float, default=0.0, nullable=False)
    rating_count = Column(Integer, default=0, nullable=False)
    
    # Output configuration
    output_format = Column(String(20), default="table", nullable=False)
    visualization_config = Column(JSONB, nullable=True)
    export_settings = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="hot_commands")
    executions = relationship("CommandExecution", back_populates="hot_command", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="hot_command", cascade="all, delete-orphan")
    # Note: cache_entry relationship handled manually due to potential import issues
    
    # Indexes
    __table_args__ = (
        Index('ix_hot_commands_user_command', 'user_id', 'command_name'),
        Index('ix_hot_commands_domain_category', 'domain', 'category'),
        Index('ix_hot_commands_status_public', 'status', 'is_public'),
        Index('ix_hot_commands_cache_entry', 'cache_entry_id'),
        Index('ix_hot_commands_source_type', 'source_template_type'),
        table_args
    )

class CommandExecution(Base):
    """Command execution log for tracking usage and performance."""
    __tablename__ = "command_executions"
    __table_args__ = table_args

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA != "public" else "users.id"), nullable=False, index=True)
    hot_command_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.hot_commands.id" if DB_SCHEMA != "public" else "hot_commands.id"), nullable=True, index=True)
    
    # Execution context
    session_id = Column(String(255), nullable=True, index=True)
    command_name = Column(String(100), nullable=False, index=True)
    parameters = Column(JSONB, nullable=True)
    raw_input = Column(Text, nullable=True)
    
    # Categorization
    domain = Column(String(50), nullable=True, index=True)
    category = Column(String(50), nullable=True, index=True)
    
    # Execution results
    status = Column(String(20), nullable=False, default=ExecutionStatus.PENDING, index=True)
    execution_time_ms = Column(Integer, nullable=True)
    result_size_bytes = Column(Integer, nullable=True)
    result_rows = Column(Integer, nullable=True)
    result_data = Column(JSONB, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Output configuration
    output_format = Column(String(20), nullable=True)
    visualization_type = Column(String(50), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="command_executions")
    hot_command = relationship("HotCommand", back_populates="executions")
    spaces = relationship("Space", back_populates="source_execution", cascade="all, delete-orphan")

class Space(Base):
    """Spaces model for sharing and storing query results."""
    __tablename__ = "spaces"
    __table_args__ = table_args

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA != "public" else "users.id"), nullable=False, index=True)
    
    # Space identification
    name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Space type and content
    space_type = Column(String(20), nullable=False, default=SpaceType.PERSONAL, index=True)
    content_type = Column(String(20), nullable=False, default=ContentType.QUERY_RESULT, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Content storage
    content_data = Column(JSONB, nullable=True)
    content_metadata = Column(JSONB, nullable=True)
    
    # Source tracking
    source_command_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.hot_commands.id" if DB_SCHEMA != "public" else "hot_commands.id"), nullable=True, index=True)
    source_execution_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.command_executions.id" if DB_SCHEMA != "public" else "command_executions.id"), nullable=True, index=True)
    
    # Categorization
    domain = Column(String(50), nullable=True, index=True)
    category = Column(String(50), nullable=True, index=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # Sharing and permissions
    is_public = Column(Boolean, default=False, nullable=False, index=True)
    shared_with = Column(ARRAY(Integer), nullable=True)
    permissions = Column(JSONB, nullable=True)
    
    # Template functionality
    is_template = Column(Boolean, default=False, nullable=False, index=True)
    template_parameters = Column(JSONB, nullable=True)
    template_schema = Column(JSONB, nullable=True)
    base_query = Column(Text, nullable=True)
    source_query = Column(Text, nullable=True)
    
    # External storage
    storage_path = Column(String(500), nullable=True)
    storage_backend = Column(String(20), default=StorageBackend.LOCAL, nullable=False)
    storage_size_bytes = Column(Integer, default=0, nullable=False)
    external_url = Column(String(1000), nullable=True)
    
    # Scheduling and automation
    schedule_type = Column(String(20), default=ScheduleType.NONE, nullable=False)
    schedule_config = Column(JSONB, nullable=True)
    next_execution = Column(DateTime(timezone=True), nullable=True, index=True)
    last_execution = Column(DateTime(timezone=True), nullable=True, index=True)
    execution_count = Column(Integer, default=0, nullable=False)
    is_scheduled_active = Column(Boolean, default=False, nullable=False, index=True)
    
    # Enhanced sharing and permissions
    access_permissions = Column(JSONB, nullable=True)
    team_id = Column(String(100), nullable=True, index=True)
    
    # Expiration and cleanup
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    auto_cleanup = Column(Boolean, default=False, nullable=False)
    retention_days = Column(Integer, nullable=True)
    
    # Usage statistics
    view_count = Column(Integer, default=0, nullable=False)
    share_count = Column(Integer, default=0, nullable=False)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="spaces")
    source_command = relationship("HotCommand", backref="result_spaces")
    source_execution = relationship("CommandExecution", back_populates="spaces")
    feedback = relationship("Feedback", back_populates="space", cascade="all, delete-orphan")
    
    # Business logic methods
    def is_template_space(self) -> bool:
        """Check if this space is a template."""
        return self.is_template and self.content_type == ContentType.TEMPLATE
    
    def get_template_parameters(self) -> List[Dict[str, Any]]:
        """Get template parameters with their definitions."""
        if not self.is_template_space():
            return []
        return self.template_parameters or []
    
    def validate_template_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against template schema."""
        if not self.template_schema:
            return {'valid': True, 'errors': []}
        
        errors = []
        required_params = [p['name'] for p in self.get_template_parameters() if p.get('required', False)]
        
        # Check required parameters
        for param in required_params:
            if param not in params:
                errors.append(f"Missing required parameter: {param}")
        
        # Check parameter types (basic validation)
        for param_def in self.get_template_parameters():
            param_name = param_def['name']
            if param_name in params:
                expected_type = param_def.get('type', 'string')
                value = params[param_name]
                
                if expected_type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"Parameter {param_name} must be a number")
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Parameter {param_name} must be a boolean")
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def render_template_query(self, params: Dict[str, Any]) -> str:
        """Render template with provided parameters."""
        if not self.is_template_space() or not self.base_query:
            return self.source_query or ""
        
        query = self.base_query
        for param_name, value in params.items():
            # Simple string replacement - in production, use proper template engine
            placeholder = f"{{{param_name}}}"
            if isinstance(value, str):
                query = query.replace(placeholder, f"'{value}'")
            else:
                query = query.replace(placeholder, str(value))
        
        return query
    
    def schedule_next_execution(self) -> Optional[datetime.datetime]:
        """Calculate next execution time based on schedule configuration."""
        if not self.is_scheduled_active or self.schedule_type == ScheduleType.NONE:
            return None
        
        from datetime import timedelta
        try:
            import croniter
        except ImportError:
            # croniter not available, skip CRON scheduling
            if self.schedule_type == ScheduleType.CRON:
                return None
        
        now = datetime.datetime.utcnow()
        
        if self.schedule_type == ScheduleType.INTERVAL:
            interval_mins = self.schedule_config.get('interval_minutes', 60)
            return now + timedelta(minutes=interval_mins)
        
        elif self.schedule_type == ScheduleType.CRON and 'croniter' in locals():
            cron_expr = self.schedule_config.get('cron_expression')
            if cron_expr:
                try:
                    cron = croniter.croniter(cron_expr, now)
                    return cron.get_next(datetime.datetime)
                except:
                    pass
        
        return None
    
    def can_be_accessed_by(self, user_id: int, access_level: AccessLevel = AccessLevel.VIEW) -> bool:
        """Check if user can access this space with given permission level."""
        # Owner has full access
        if self.owner_id == user_id:
            return True
            
        # Public spaces can be viewed by anyone
        if self.is_public and self.is_active and access_level == AccessLevel.VIEW:
            return True
            
        # Check explicit access grants via SpaceAccess model
        for access_grant in self.access_grants:
            if (access_grant.user_id == user_id and 
                access_grant.is_valid() and 
                self._access_level_sufficient(access_grant.access_level, access_level)):
                return True
            
        # Check shared_with array for basic sharing (backward compatibility)
        if self.shared_with and user_id in self.shared_with:
            return True
            
        return False
    
    def _access_level_sufficient(self, granted_level: str, required_level: AccessLevel) -> bool:
        """Check if granted access level is sufficient for required level."""
        level_hierarchy = {
            AccessLevel.VIEW: 1,
            AccessLevel.COMMENT: 2,
            AccessLevel.EDIT: 3,
            AccessLevel.ADMIN: 4
        }
        
        granted_value = level_hierarchy.get(AccessLevel(granted_level), 0)
        required_value = level_hierarchy.get(required_level, 0)
        
        return granted_value >= required_value
    
    def can_execute(self) -> bool:
        """Check if space can be executed (for templates and scheduled spaces)."""
        return (
            self.is_active and 
            (self.is_template_space() or self.is_scheduled_active) and
            (self.source_query or self.base_query)
        )
    
    def record_execution(self, success: bool = True) -> None:
        """Record execution attempt."""
        self.execution_count += 1
        self.last_execution = func.now()
        
        if self.is_scheduled_active:
            self.next_execution = self.schedule_next_execution()
    
    def increment_view_count(self, user_id: int = None) -> None:
        """Increment view count and update last accessed time."""
        self.view_count += 1
        self.last_accessed = func.now()
    
    def get_external_share_url(self) -> Optional[str]:
        """Get public sharing URL for external access."""
        if self.external_url:
            return self.external_url
        return None

class SpaceAccess(Base):
    """Model for space access permissions and granular sharing."""
    __tablename__ = "space_access"
    __table_args__ = table_args

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.spaces.id" if DB_SCHEMA != "public" else "spaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA != "public" else "users.id"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA != "public" else "users.id"), nullable=False, index=True)
    
    # Access details
    access_level = Column(String(20), default=AccessLevel.VIEW, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Usage tracking
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Optional constraints
    restrictions = Column(JSONB, nullable=True)  # Additional access restrictions
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    space = relationship("Space", backref="access_grants")
    user = relationship("User", foreign_keys=[user_id])
    grantor = relationship("User", foreign_keys=[granted_by])
    
    # Indexes
    __table_args__ = (
        Index('ix_space_access_space_user', 'space_id', 'user_id'),
        Index('ix_space_access_active', 'is_active', 'expires_at'),
        Index('ix_space_access_level', 'access_level', 'is_active'),
        table_args
    )
    
    def is_expired(self) -> bool:
        """Check if access grant has expired."""
        if not self.expires_at:
            return False
        return func.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if access grant is valid (active and not expired)."""
        return self.is_active and not self.is_expired()
    
    def record_access(self) -> None:
        """Record an access event."""
        self.access_count += 1
        self.last_accessed = func.now()

class Feedback(Base):
    """Feedback model for collecting user feedback on commands and results."""
    __tablename__ = "feedback"
    __table_args__ = table_args

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id" if DB_SCHEMA != "public" else "users.id"), nullable=False, index=True)
    
    # Feedback targets
    execution_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.command_executions.id" if DB_SCHEMA != "public" else "command_executions.id"), nullable=True, index=True)
    hot_command_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.hot_commands.id" if DB_SCHEMA != "public" else "hot_commands.id"), nullable=True, index=True)
    space_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.spaces.id" if DB_SCHEMA != "public" else "spaces.id"), nullable=True, index=True)
    
    # Feedback content
    feedback_type = Column(String(30), nullable=False, default=FeedbackType.COMMENT, index=True)
    status = Column(String(20), default="active", nullable=False, index=True)
    rating = Column(Integer, nullable=True)  # 1-5 scale
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Context
    domain = Column(String(50), nullable=True, index=True)
    category = Column(String(50), nullable=True, index=True)
    command_name = Column(String(100), nullable=True, index=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # Priority and helpfulness
    priority = Column(String(10), default=Priority.MEDIUM, nullable=False, index=True)
    helpful_count = Column(Integer, default=0, nullable=False)
    unhelpful_count = Column(Integer, default=0, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    hot_command = relationship("HotCommand", back_populates="feedback")
    space = relationship("Space", back_populates="feedback")
    execution = relationship("CommandExecution", backref="feedback")

# Additional indexes for performance
Index('ix_feedback_type_status', Feedback.feedback_type, Feedback.status)
Index('ix_spaces_owner_type', Space.owner_id, Space.space_type)
Index('ix_executions_status_created', CommandExecution.status, CommandExecution.created_at)
Index('ix_hot_commands_rating_usage', HotCommand.rating, HotCommand.usage_count)