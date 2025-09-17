"""
Pydantic schemas for spaces API endpoints.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

# Import enums from models
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from thinkforge.hotcommands_models import (
    SpaceType, ContentType, AccessLevel, StorageBackend, ScheduleType
)


class SpaceBase(BaseModel):
    """Base space schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Unique space name")
    display_name: Optional[str] = Field(None, max_length=255, description="Human-readable display name")
    description: Optional[str] = Field(None, description="Space description")
    space_type: SpaceType = Field(SpaceType.PERSONAL, description="Type of space")
    content_type: ContentType = Field(ContentType.QUERY_RESULT, description="Type of content stored")
    domain: Optional[str] = Field(None, max_length=50, description="Domain category")
    category: Optional[str] = Field(None, max_length=50, description="Category within domain")
    tags: List[str] = Field([], description="List of tags for categorization")
    is_public: bool = Field(False, description="Whether space is publicly accessible")


class SpaceCreate(SpaceBase):
    """Schema for creating a new space."""
    # Template functionality
    is_template: bool = Field(False, description="Whether this space is a template")
    template_parameters: Optional[List[Dict[str, Any]]] = Field(None, description="Template parameter definitions")
    template_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for parameter validation")
    base_query: Optional[str] = Field(None, description="Base query template")
    source_query: Optional[str] = Field(None, description="Original source query")
    
    # Content
    content_data: Optional[Dict[str, Any]] = Field(None, description="Initial content data")
    content_metadata: Optional[Dict[str, Any]] = Field(None, description="Content metadata")
    
    # Storage
    storage_backend: StorageBackend = Field(StorageBackend.LOCAL, description="Storage backend to use")
    
    # Scheduling
    schedule_type: ScheduleType = Field(ScheduleType.NONE, description="Type of scheduling")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration")
    
    # Sharing
    shared_with: Optional[List[int]] = Field(None, description="List of user IDs to share with")
    team_id: Optional[str] = Field(None, max_length=100, description="Team identifier")
    
    # Expiration
    expires_at: Optional[datetime] = Field(None, description="When the space expires")
    auto_cleanup: bool = Field(False, description="Whether to auto-cleanup on expiration")
    retention_days: Optional[int] = Field(None, gt=0, description="Days to retain the space")
    
    @validator('template_parameters')
    def validate_template_parameters(cls, v, values):
        """Validate template parameters format."""
        if v and values.get('is_template'):
            for param in v:
                if not isinstance(param, dict) or 'name' not in param:
                    raise ValueError("Template parameters must contain 'name' field")
                if not isinstance(param['name'], str):
                    raise ValueError("Parameter name must be a string")
        return v
    
    @validator('schedule_config')
    def validate_schedule_config(cls, v, values):
        """Validate schedule configuration."""
        schedule_type = values.get('schedule_type')
        if schedule_type == ScheduleType.CRON and v:
            if 'cron_expression' not in v:
                raise ValueError("CRON schedule requires cron_expression")
        elif schedule_type == ScheduleType.INTERVAL and v:
            if 'interval_minutes' not in v or not isinstance(v['interval_minutes'], int):
                raise ValueError("Interval schedule requires interval_minutes as integer")
        elif schedule_type == ScheduleType.WEBHOOK and v:
            if 'webhook_url' not in v:
                raise ValueError("Webhook schedule requires webhook_url")
        return v


class SpaceUpdate(BaseModel):
    """Schema for updating an existing space."""
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    space_type: Optional[SpaceType] = None
    content_type: Optional[ContentType] = None
    domain: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    
    # Template updates
    template_parameters: Optional[List[Dict[str, Any]]] = None
    template_schema: Optional[Dict[str, Any]] = None
    base_query: Optional[str] = None
    source_query: Optional[str] = None
    
    # Content updates
    content_data: Optional[Dict[str, Any]] = None
    content_metadata: Optional[Dict[str, Any]] = None
    
    # Scheduling updates
    schedule_type: Optional[ScheduleType] = None
    schedule_config: Optional[Dict[str, Any]] = None
    is_scheduled_active: Optional[bool] = None
    
    # Sharing updates
    shared_with: Optional[List[int]] = None
    team_id: Optional[str] = Field(None, max_length=100)
    
    # Expiration updates
    expires_at: Optional[datetime] = None
    auto_cleanup: Optional[bool] = None
    retention_days: Optional[int] = Field(None, gt=0)


class SpaceResponse(BaseModel):
    """Schema for space response data."""
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    space_type: SpaceType
    content_type: ContentType
    is_template: bool
    is_active: bool
    is_public: bool
    
    # Owner and metadata
    owner_id: int
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]
    
    # Content information
    storage_path: Optional[str]
    storage_backend: StorageBackend
    storage_size_bytes: int
    external_url: Optional[str]
    
    # Template information
    template_parameters: Optional[List[Dict[str, Any]]]
    template_schema: Optional[Dict[str, Any]]
    base_query: Optional[str]
    source_query: Optional[str]
    
    # Categorization
    domain: Optional[str]
    category: Optional[str]
    tags: List[str]
    
    # Usage stats
    view_count: int
    share_count: int
    execution_count: int
    
    # Scheduling
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    next_execution: Optional[datetime]
    last_execution: Optional[datetime]
    is_scheduled_active: bool
    
    # Sharing
    shared_with: Optional[List[int]]
    team_id: Optional[str]
    
    # Expiration
    expires_at: Optional[datetime]
    auto_cleanup: bool
    retention_days: Optional[int]
    
    class Config:
        from_attributes = True


class SpaceListResponse(BaseModel):
    """Schema for paginated space list."""
    spaces: List[SpaceResponse]
    total: int
    skip: int
    limit: int


class SpaceAccessBase(BaseModel):
    """Base schema for space access."""
    user_id: int
    access_level: AccessLevel


class SpaceAccessCreate(SpaceAccessBase):
    """Schema for creating space access."""
    expires_at: Optional[datetime] = None
    restrictions: Optional[Dict[str, Any]] = None


class SpaceAccessResponse(BaseModel):
    """Schema for space access response."""
    id: int
    space_id: int
    user_id: int
    granted_by: int
    access_level: AccessLevel
    is_active: bool
    access_count: int
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]
    restrictions: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SpaceShareRequest(BaseModel):
    """Schema for sharing a space."""
    user_id: int = Field(..., gt=0, description="ID of user to share with")
    access_level: AccessLevel = Field(AccessLevel.VIEW, description="Level of access to grant")
    expires_at: Optional[datetime] = Field(None, description="When access expires")
    restrictions: Optional[Dict[str, Any]] = Field(None, description="Additional access restrictions")


class TemplateExecuteRequest(BaseModel):
    """Schema for executing a template space."""
    parameters: Dict[str, Any] = Field(..., description="Parameters for template execution")
    save_result: bool = Field(False, description="Whether to save execution result")
    result_name: Optional[str] = Field(None, description="Name for saved result")
    storage_backend: StorageBackend = Field(StorageBackend.LOCAL, description="Storage backend for results")
    
    @validator('parameters')
    def validate_parameters(cls, v):
        """Ensure parameters is a dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Parameters must be a dictionary")
        return v


class SpaceScheduleConfig(BaseModel):
    """Schema for space scheduling configuration."""
    schedule_type: ScheduleType
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    webhook_url: Optional[str] = None
    timezone: Optional[str] = "UTC"
    enabled: bool = True
    max_executions: Optional[int] = Field(None, gt=0, description="Maximum number of executions")
    
    @validator('cron_expression')
    def validate_cron_expression(cls, v, values):
        """Validate CRON expression format."""
        if values.get('schedule_type') == ScheduleType.CRON and v:
            # Basic CRON validation (5 or 6 fields)
            parts = v.strip().split()
            if len(parts) not in [5, 6]:
                raise ValueError("CRON expression must have 5 or 6 fields")
        return v
    
    @validator('interval_minutes')
    def validate_interval_minutes(cls, v, values):
        """Validate interval minutes."""
        if values.get('schedule_type') == ScheduleType.INTERVAL and v:
            if v < 1 or v > 10080:  # Max 1 week
                raise ValueError("Interval must be between 1 and 10080 minutes")
        return v


class SpaceExecutionResult(BaseModel):
    """Schema for space execution result."""
    execution_id: str
    space_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    result_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    row_count: Optional[int]
    storage_path: Optional[str]
    public_url: Optional[str]
    parameters_used: Optional[Dict[str, Any]]


class SpaceContentUpload(BaseModel):
    """Schema for content upload response."""
    storage_path: str
    public_url: Optional[str]
    size_bytes: int
    content_type: str
    upload_time: datetime


class SpaceExportRequest(BaseModel):
    """Schema for space export request."""
    format: str = Field(..., pattern="^(json|csv|html|pdf)$", description="Export format")
    include_metadata: bool = Field(True, description="Whether to include metadata")
    template_parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for template execution")


class SpaceExportResponse(BaseModel):
    """Schema for space export response."""
    export_url: str
    format: str
    expires_at: datetime
    size_bytes: int


class SpaceAnalytics(BaseModel):
    """Schema for space analytics data."""
    space_id: int
    total_views: int
    unique_viewers: int
    total_executions: int
    avg_execution_time_ms: Optional[float]
    last_30_days_views: int
    last_30_days_executions: int
    top_parameters: Optional[List[Dict[str, Any]]]  # For templates
    performance_metrics: Optional[Dict[str, Any]]


class SpaceSearchRequest(BaseModel):
    """Schema for advanced space search."""
    query: Optional[str] = Field(None, description="Search query")
    space_types: Optional[List[SpaceType]] = None
    content_types: Optional[List[ContentType]] = None
    domains: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_template: Optional[bool] = None
    is_scheduled: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_modified_after: Optional[datetime] = None
    last_modified_before: Optional[datetime] = None
    min_views: Optional[int] = Field(None, ge=0)
    max_views: Optional[int] = Field(None, ge=0)
    owner_ids: Optional[List[int]] = None
    shared_with_me: bool = False
    my_spaces: bool = False


class SpaceTemplate(BaseModel):
    """Schema for space template information."""
    parameters: List[Dict[str, Any]]
    parameter_schema: Dict[str, Any]  # Renamed to avoid conflict with BaseModel.schema
    base_query: str
    sample_parameters: Optional[Dict[str, Any]]
    parameter_descriptions: Optional[Dict[str, str]]


class SpaceBulkOperation(BaseModel):
    """Schema for bulk operations on spaces."""
    space_ids: List[int] = Field(..., min_items=1, max_items=100)
    operation: str = Field(..., pattern="^(delete|archive|share|export)$", description="Operation to perform")
    operation_params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the operation")
    
    @validator('space_ids')
    def validate_space_ids(cls, v):
        """Ensure at least one space ID is provided."""
        if not v or len(v) == 0:
            raise ValueError("At least one space ID must be provided")
        if len(v) > 100:
            raise ValueError("Maximum 100 spaces allowed per bulk operation")
        return v


class SpaceBulkOperationResult(BaseModel):
    """Schema for bulk operation results."""
    operation: str
    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]]
    results: Optional[Dict[str, Any]]


class CacheToSpaceRequest(BaseModel):
    """Schema for converting cache entry to space."""
    cache_id: int = Field(..., gt=0, description="ID of cache entry to convert")
    space_name: str = Field(..., min_length=1, max_length=100, description="Name for the new space")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name for the space")
    description: Optional[str] = Field(None, description="Description for the space")
    make_template: bool = Field(False, description="Whether to convert to template if parameters detected")
    copy_content: bool = Field(True, description="Whether to copy content data from cache entry")


class SpaceFromCacheResponse(BaseModel):
    """Schema for cache-to-space conversion response."""
    space: SpaceResponse
    cache_entry_id: int
    conversion_notes: List[str]
    template_created: bool