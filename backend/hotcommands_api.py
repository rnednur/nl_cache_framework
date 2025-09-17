"""
Hot Commands API endpoints for ThinkForge integration
Provides REST API for intelligent slash command management with semantic processing
"""

from fastapi import Depends, HTTPException, Query as QueryParam
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import logging
import datetime
import sys
import os

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import database configuration
from database import get_db

# Import ThinkForge components
try:
    from thinkforge.hotcommands_controller import HotCommandsController, CommandRequest, CommandResponse, CommandSuggestion
    from thinkforge.hotcommands_models import (
        User, HotCommand, CommandExecution, Space, Feedback,
        CommandStatus, CommandQueryType, ExecutionStatus, SpaceType, ContentType, FeedbackType
    )
except ImportError as e:
    print(f"Error importing thinkforge components: {e}")
    print(f"Current sys.path: {sys.path}")
    raise

logger = logging.getLogger(__name__)

# ==========================================
# Pydantic Models for API Schema
# ==========================================

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool
    domains: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    command_count: int
    favorite_commands: Optional[List[str]] = None
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat()
        }

class HotCommandCreate(BaseModel):
    command_name: str = Field(..., pattern="^[a-zA-Z0-9_]+$", description="Command name (alphanumeric and underscore only)")
    display_name: Optional[str] = None
    description: Optional[str] = None
    query_text: str = Field(..., description="The query or command definition")
    query_type: str = Field(default="nl2sql", description="Type of query: nl2sql, direct_sql, tool_call, workflow")
    domain: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = []
    parameters: Optional[Dict[str, Any]] = {}
    is_public: bool = False
    cache_entry_id: Optional[int] = None

class HotCommandUpdate(BaseModel):
    command_name: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_]+$", description="Command name (alphanumeric and underscore only)")
    display_name: Optional[str] = None
    description: Optional[str] = None
    query_text: Optional[str] = None
    query_type: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    status: Optional[str] = None

class HotCommandResponse(BaseModel):
    id: int
    command_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    query_text: str
    query_type: str
    domain: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    parameters: Dict[str, Any] = {}
    status: str
    is_public: bool
    is_template: bool
    usage_count: int
    success_rate: float
    avg_execution_time: Optional[float] = None
    last_used: Optional[str] = None
    rating: float
    rating_count: int
    output_format: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    user_id: int
    cache_entry_id: Optional[int] = None
    source_template_type: Optional[str] = None
    source_reasoning: Optional[str] = None
    source_tags: Optional[Dict[str, Any]] = None
    source_execution_stats: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat()
        }

class ExecuteCommandRequest(BaseModel):
    command: str = Field(..., description="Command to execute (with or without leading slash)")
    parameters: Optional[Dict[str, Any]] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    session_id: Optional[str] = None

class SpaceCreate(BaseModel):
    name: str = Field(..., pattern="^[a-zA-Z0-9_]+$")
    display_name: Optional[str] = None
    description: Optional[str] = None
    space_type: str = Field(default="personal")
    content_type: str = Field(default="query_result")
    content_data: Optional[Dict[str, Any]] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = []
    is_public: bool = False

class SpaceResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    space_type: str
    content_type: str
    is_active: bool
    content_data: Optional[Dict[str, Any]] = None
    content_metadata: Dict[str, Any] = {}
    domain: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    is_public: bool
    view_count: int
    share_count: int
    last_accessed: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    owner_id: int
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat()
        }

class FeedbackCreate(BaseModel):
    feedback_type: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = None
    description: Optional[str] = None
    execution_id: Optional[int] = None
    hot_command_id: Optional[int] = None
    space_id: Optional[int] = None

class DashboardStats(BaseModel):
    total_commands: int
    total_executions: int
    avg_success_rate: float
    recent_activity: List[Dict[str, Any]]
    popular_commands: List[HotCommandResponse]
    domains_used: List[Dict[str, Any]]

class CacheEntryResponse(BaseModel):
    id: int
    nl_query: str
    template_type: str
    catalog_type: Optional[str] = None
    catalog_subtype: Optional[str] = None
    catalog_name: Optional[str] = None
    reasoning_trace: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    execution_count: int
    success_rate: float
    complexity_level: Optional[str] = None
    health_status: Optional[str] = None
    last_executed: Optional[str] = None
    created_at: str
    updated_at: str
    has_hot_command: bool
    hot_command_name: Optional[str] = None
    hot_command_id: Optional[int] = None

class CacheEntryDetailResponse(BaseModel):
    id: int
    nl_query: str
    template: str
    template_type: str
    is_template: bool
    entity_replacements: Optional[Dict[str, Any]] = None
    reasoning_trace: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    catalog_type: Optional[str] = None
    catalog_subtype: Optional[str] = None
    catalog_name: Optional[str] = None
    status: str
    tool_capabilities: Optional[List[str]] = None
    execution_config: Optional[Dict[str, Any]] = None
    health_status: Optional[str] = None
    recipe_steps: Optional[List[Dict[str, Any]]] = None
    required_tools: Optional[List[int]] = None
    execution_time_estimate: Optional[int] = None
    complexity_level: Optional[str] = None
    success_rate: Optional[float] = None
    last_executed: Optional[str] = None
    execution_count: Optional[int] = None
    created_at: str
    updated_at: str
    has_hot_command: bool
    hot_command: Optional[Dict[str, Any]] = None

class CreateFromCacheRequest(BaseModel):
    cache_entry_id: int
    command_name: str = Field(..., pattern="^[a-zA-Z0-9_]+$")
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False
    tags: Optional[List[str]] = None

# ==========================================
# API Endpoints
# ==========================================

def get_current_user_id() -> int:
    """Mock user authentication - in production, extract from JWT token"""
    return 1  # Demo user ID

def get_hotcommands_controller(db: Session = Depends(get_db)) -> HotCommandsController:
    """Get Hot Commands controller with ThinkForge integration"""
    # Get the NL2SQL controller from the main app
    from app import get_controller
    nl2sql_controller = get_controller(db)
    return HotCommandsController(db, nl2sql_controller)

def create_hotcommands_routes():
    """Create and return Hot Commands API routes"""
    routes = []
    
    # ==========================================
    # Hot Commands CRUD Operations
    # ==========================================
    
    def get_my_hot_commands(
        db: Session = Depends(get_db),
        controller: HotCommandsController = Depends(get_hotcommands_controller),
        domain: Optional[str] = QueryParam(None),
        category: Optional[str] = QueryParam(None),
        status: Optional[str] = QueryParam(None),
        limit: int = QueryParam(100, le=1000),
        offset: int = QueryParam(0)
    ) -> List[HotCommandResponse]:
        """Get current user's hot commands with optional filtering"""
        try:
            user_id = get_current_user_id()
            
            query = db.query(HotCommand).filter(
                HotCommand.user_id == user_id,
                HotCommand.deleted_at.is_(None)
            )
            
            if domain:
                query = query.filter(HotCommand.domain == domain)
            if category:
                query = query.filter(HotCommand.category == category)
            if status:
                query = query.filter(HotCommand.status == status)
                
            commands = query.offset(offset).limit(limit).all()
            
            return [HotCommandResponse.from_orm(cmd) for cmd in commands]
            
        except Exception as e:
            logger.error(f"Error retrieving hot commands: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_public_hot_commands(
        db: Session = Depends(get_db),
        domain: Optional[str] = QueryParam(None),
        category: Optional[str] = QueryParam(None),
        limit: int = QueryParam(50, le=1000),
        offset: int = QueryParam(0)
    ) -> List[HotCommandResponse]:
        """Get public hot commands"""
        try:
            query = db.query(HotCommand).filter(
                HotCommand.is_public == True,
                HotCommand.status == CommandStatus.ACTIVE,
                HotCommand.deleted_at.is_(None)
            )
            
            if domain:
                query = query.filter(HotCommand.domain == domain)
            if category:
                query = query.filter(HotCommand.category == category)
                
            commands = query.offset(offset).limit(limit).all()
            
            return [HotCommandResponse.from_orm(cmd) for cmd in commands]
            
        except Exception as e:
            logger.error(f"Error retrieving public hot commands: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def create_hot_command(
        command_data: HotCommandCreate,
        db: Session = Depends(get_db),
        controller: HotCommandsController = Depends(get_hotcommands_controller)
    ) -> HotCommandResponse:
        """Create a new hot command"""
        try:
            user_id = get_current_user_id()
            
            hot_command = controller.create_hot_command(
                user_id=user_id,
                **command_data.dict()
            )
            
            return HotCommandResponse.from_orm(hot_command)
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating hot command: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_hot_command(
        command_id: int,
        db: Session = Depends(get_db)
    ) -> HotCommandResponse:
        """Get a specific hot command by ID"""
        try:
            user_id = get_current_user_id()
            
            command = db.query(HotCommand).filter(
                HotCommand.id == command_id,
                HotCommand.deleted_at.is_(None)
            ).first()
            
            if not command:
                raise HTTPException(status_code=404, detail="Hot command not found")
            
            # Check access permissions
            if not command.is_public and command.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            return HotCommandResponse.from_orm(command)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving hot command: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_hot_command(
        command_id: int,
        command_data: HotCommandUpdate,
        db: Session = Depends(get_db)
    ) -> HotCommandResponse:
        """Update a hot command"""
        try:
            user_id = get_current_user_id()
            
            command = db.query(HotCommand).filter(
                HotCommand.id == command_id,
                HotCommand.user_id == user_id,
                HotCommand.deleted_at.is_(None)
            ).first()
            
            if not command:
                raise HTTPException(status_code=404, detail="Hot command not found")
            
            # Update fields (exclude cache_entry_id to avoid foreign key issues)
            update_data = command_data.dict(exclude_unset=True)
            excluded_fields = {'cache_entry_id'}  # Don't update cache_entry_id to avoid FK constraints
            
            logger.info(f"Updating hot command {command_id} with data: {update_data}")
            
            for field, value in update_data.items():
                if field not in excluded_fields:
                    if hasattr(command, field):
                        logger.info(f"Setting {field} = {value}")
                        setattr(command, field, value)
                    else:
                        logger.warning(f"Field {field} does not exist on HotCommand model")
            
            command.updated_at = datetime.datetime.now()
            db.commit()
            db.refresh(command)
            
            return HotCommandResponse.from_orm(command)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating hot command: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    
    def delete_hot_command(
        command_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, str]:
        """Delete a hot command (soft delete)"""
        try:
            user_id = get_current_user_id()
            
            command = db.query(HotCommand).filter(
                HotCommand.id == command_id,
                HotCommand.user_id == user_id,
                HotCommand.deleted_at.is_(None)
            ).first()
            
            if not command:
                raise HTTPException(status_code=404, detail="Hot command not found")
            
            # Soft delete
            command.deleted_at = datetime.datetime.now()
            db.commit()
            
            return {"message": "Hot command deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting hot command: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==========================================
    # Command Execution
    # ==========================================
    
    def execute_command(
        request: ExecuteCommandRequest,
        db: Session = Depends(get_db),
        controller: HotCommandsController = Depends(get_hotcommands_controller)
    ) -> CommandResponse:
        """Execute a command with intelligent routing and caching"""
        try:
            user_id = get_current_user_id()
            
            command_request = CommandRequest(
                command=request.command,
                parameters=request.parameters,
                domain=request.domain,
                category=request.category,
                session_id=request.session_id,
                user_id=user_id
            )
            
            response = controller.execute_command(command_request)
            return response
            
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_command_suggestions(
        query: str,
        db: Session = Depends(get_db),
        controller: HotCommandsController = Depends(get_hotcommands_controller),
        domain: Optional[str] = QueryParam(None),
        limit: int = QueryParam(10)
    ) -> List[CommandSuggestion]:
        """Get command suggestions based on similarity"""
        try:
            user_id = get_current_user_id()
            suggestions = controller.get_command_suggestions(query, user_id, domain, limit)
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting command suggestions: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==========================================
    # Spaces Management
    # ==========================================
    
    def get_my_spaces(
        db: Session = Depends(get_db),
        space_type: Optional[str] = QueryParam(None),
        limit: int = QueryParam(100, le=1000),
        offset: int = QueryParam(0)
    ) -> List[SpaceResponse]:
        """Get current user's spaces"""
        try:
            user_id = get_current_user_id()
            
            query = db.query(Space).filter(
                Space.owner_id == user_id,
                Space.deleted_at.is_(None)
            )
            
            if space_type:
                query = query.filter(Space.space_type == space_type)
                
            spaces = query.offset(offset).limit(limit).all()
            
            return [SpaceResponse.from_orm(space) for space in spaces]
            
        except Exception as e:
            logger.error(f"Error retrieving spaces: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def create_space(
        space_data: SpaceCreate,
        db: Session = Depends(get_db)
    ) -> SpaceResponse:
        """Create a new space"""
        try:
            user_id = get_current_user_id()
            
            space = Space(
                owner_id=user_id,
                **space_data.dict()
            )
            
            db.add(space)
            db.commit()
            db.refresh(space)
            
            return SpaceResponse.from_orm(space)
            
        except Exception as e:
            logger.error(f"Error creating space: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_hot_commands_metadata(
        db: Session = Depends(get_db)
    ) -> Dict[str, List[str]]:
        """Get available domains, categories, and other metadata for hot commands"""
        try:
            # Get distinct domains from existing hot commands
            domains_query = db.query(HotCommand.domain).filter(
                HotCommand.domain.isnot(None),
                HotCommand.deleted_at.is_(None)
            ).distinct()
            domains = [d[0] for d in domains_query.all() if d[0]]
            
            # Get distinct categories from existing hot commands
            categories_query = db.query(HotCommand.category).filter(
                HotCommand.category.isnot(None),
                HotCommand.deleted_at.is_(None)
            ).distinct()
            categories = [c[0] for c in categories_query.all() if c[0]]
            
            # Get distinct tags from existing hot commands
            tags_query = db.query(HotCommand.tags).filter(
                HotCommand.tags.isnot(None),
                HotCommand.deleted_at.is_(None)
            )
            all_tags = set()
            for tags_array in tags_query.all():
                if tags_array[0]:  # tags_array is a tuple containing the array
                    all_tags.update(tags_array[0])
            
            return {
                "domains": sorted(domains),
                "categories": sorted(categories),
                "tags": sorted(list(all_tags)),
                "query_types": ["nl2sql", "direct_sql", "tool_call", "workflow"],
                "template_types": ["sql", "workflow", "recipe", "api", "function", "script"]
            }
            
        except Exception as e:
            logger.error(f"Error retrieving hot commands metadata: {e}")
            # Return empty arrays on error - no hardcoded fallbacks
            return {
                "domains": [],
                "categories": [],
                "tags": [],
                "query_types": ["nl2sql", "direct_sql", "tool_call", "workflow"],
                "template_types": ["sql", "workflow", "recipe", "api", "function", "script"]
            }
    
    # ==========================================
    # Analytics and Dashboard
    # ==========================================
    
    def get_dashboard_stats(
        db: Session = Depends(get_db)
    ) -> DashboardStats:
        """Get dashboard statistics for current user"""
        try:
            user_id = get_current_user_id()
            
            # Get basic stats
            total_commands = db.query(HotCommand).filter(
                HotCommand.user_id == user_id,
                HotCommand.deleted_at.is_(None)
            ).count()
            
            total_executions = db.query(CommandExecution).filter(
                CommandExecution.user_id == user_id
            ).count()
            
            # Calculate average success rate
            successful_executions = db.query(CommandExecution).filter(
                CommandExecution.user_id == user_id,
                CommandExecution.status == ExecutionStatus.SUCCESS
            ).count()
            
            avg_success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
            
            # Get recent activity
            recent_executions = db.query(CommandExecution).filter(
                CommandExecution.user_id == user_id
            ).order_by(CommandExecution.created_at.desc()).limit(5).all()
            
            recent_activity = [
                {
                    "command_name": exec.command_name,
                    "execution_count": 1,  # Simplified for demo
                    "last_executed": exec.created_at.isoformat()
                }
                for exec in recent_executions
            ]
            
            # Get popular commands
            popular_commands_data = db.query(HotCommand).filter(
                HotCommand.user_id == user_id,
                HotCommand.deleted_at.is_(None)
            ).order_by(HotCommand.usage_count.desc()).limit(5).all()
            
            popular_commands = [HotCommandResponse.from_orm(cmd) for cmd in popular_commands_data]
            
            # Get domains used
            domains_used = [
                {"domain": "sales", "count": 45},
                {"domain": "analytics", "count": 28},
                {"domain": "finance", "count": 15}
            ]  # Simplified for demo
            
            return DashboardStats(
                total_commands=total_commands,
                total_executions=total_executions,
                avg_success_rate=avg_success_rate,
                recent_activity=recent_activity,
                popular_commands=popular_commands,
                domains_used=domains_used
            )
            
        except Exception as e:
            logger.error(f"Error retrieving dashboard stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==========================================
    # Cache Entry Integration Endpoints
    # ==========================================
    
    def get_available_cache_entries(
        db: Session = Depends(get_db),
        controller: HotCommandsController = Depends(get_hotcommands_controller),
        template_type: Optional[str] = QueryParam(None),
        catalog_type: Optional[str] = QueryParam(None),
        catalog_subtype: Optional[str] = QueryParam(None),
        limit: int = QueryParam(100, le=1000),
        offset: int = QueryParam(0)
    ) -> List[CacheEntryResponse]:
        """Get available cache entries that can be converted to hot commands"""
        try:
            user_id = get_current_user_id()
            
            entries = controller.get_available_cache_entries(
                user_id=user_id,
                template_type=template_type,
                catalog_type=catalog_type,
                catalog_subtype=catalog_subtype,
                limit=limit,
                offset=offset
            )
            
            return [CacheEntryResponse(**entry) for entry in entries]
            
        except Exception as e:
            logger.error(f"Error retrieving cache entries: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_cache_entry_details(
        cache_entry_id: int,
        db: Session = Depends(get_db),
        controller: HotCommandsController = Depends(get_hotcommands_controller)
    ) -> CacheEntryDetailResponse:
        """Get detailed information about a cache entry"""
        try:
            details = controller.get_cache_entry_details(cache_entry_id)
            
            if not details:
                raise HTTPException(status_code=404, detail="Cache entry not found")
                
            return CacheEntryDetailResponse(**details)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving cache entry details: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def create_hot_command_from_cache(
        request: CreateFromCacheRequest,
        db: Session = Depends(get_db),
        controller: HotCommandsController = Depends(get_hotcommands_controller)
    ) -> HotCommandResponse:
        """Create a hot command from an existing cache entry"""
        try:
            user_id = get_current_user_id()
            
            hot_command = controller.create_hot_command_from_cache(
                user_id=user_id,
                cache_entry_id=request.cache_entry_id,
                command_name=request.command_name,
                display_name=request.display_name,
                description=request.description,
                is_public=request.is_public,
                tags=request.tags
            )
            
            return HotCommandResponse.from_orm(hot_command)
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating hot command from cache: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Return all route functions
    return {
        'get_my_hot_commands': get_my_hot_commands,
        'get_public_hot_commands': get_public_hot_commands,
        'create_hot_command': create_hot_command,
        'get_hot_command': get_hot_command,
        'update_hot_command': update_hot_command,
        'delete_hot_command': delete_hot_command,
        'execute_command': execute_command,
        'get_command_suggestions': get_command_suggestions,
        'get_my_spaces': get_my_spaces,
        'create_space': create_space,
        'get_hot_commands_metadata': get_hot_commands_metadata,
        'get_dashboard_stats': get_dashboard_stats,
        'get_available_cache_entries': get_available_cache_entries,
        'get_cache_entry_details': get_cache_entry_details,
        'create_hot_command_from_cache': create_hot_command_from_cache
    }