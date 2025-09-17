"""
Hot Commands Controller for ThinkForge Framework Integration
Provides intelligent slash command processing with semantic understanding
"""

import logging
import json
import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc
from pydantic import BaseModel

from .hotcommands_models import (
    User, HotCommand, CommandExecution, Space, Feedback,
    CommandStatus, CommandQueryType, ExecutionStatus, SpaceType, ContentType, FeedbackType
)
from .models import Text2SQLCache, TemplateType, Status
from .controller import Text2SQLController
from .similarity import Text2SQLSimilarity
from .entity_substitution import Text2SQLEntitySubstitution

logger = logging.getLogger(__name__)

class CommandRequest(BaseModel):
    """Request model for command execution."""
    command: str
    parameters: Optional[Dict[str, Any]] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    session_id: Optional[str] = None
    user_id: int

class CommandResponse(BaseModel):
    """Response model for command execution."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: int
    result_rows: Optional[int] = None
    sql_query: Optional[str] = None
    metadata: Dict[str, Any] = {}

class CommandSuggestion(BaseModel):
    """Model for command suggestions."""
    command_name: str
    display_name: Optional[str]
    description: Optional[str]
    similarity_score: float
    usage_count: int
    rating: float

class HotCommandsController:
    """
    Hot Commands Controller that extends ThinkForge with intelligent slash command functionality.
    
    This controller provides:
    - Semantic command matching and routing
    - Parameter extraction and substitution
    - Command caching and optimization
    - Usage analytics and feedback integration
    """
    
    def __init__(self, db_session: Session, nl2sql_controller: Text2SQLController):
        self.db = db_session
        self.nl2sql_controller = nl2sql_controller
        self.entity_substitution = Text2SQLEntitySubstitution()
        self.similarity_util = Text2SQLSimilarity()
        
    def create_hot_command(
        self, 
        user_id: int,
        command_name: str,
        query_text: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        query_type: str = CommandQueryType.NL2SQL,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        is_public: bool = False,
        cache_entry_id: Optional[int] = None
    ) -> HotCommand:
        """Create a new hot command."""
        try:
            # Check if command name already exists for user
            existing = self.db.query(HotCommand).filter(
                and_(
                    HotCommand.user_id == user_id,
                    HotCommand.command_name == command_name,
                    HotCommand.deleted_at.is_(None)
                )
            ).first()
            
            if existing:
                raise ValueError(f"Command '{command_name}' already exists for user")
            
            # Validate query text by attempting to process it
            try:
                if query_type == CommandQueryType.NL2SQL:
                    # Test with ThinkForge NL2SQL controller
                    test_result = self.nl2sql_controller.process_nl_query(
                        query_text, 
                        domain=domain,
                        category=category,
                        dry_run=True
                    )
                    logger.info(f"Query validation successful for: {command_name}")
            except Exception as e:
                logger.warning(f"Query validation warning for {command_name}: {e}")
            
            # If connected to cache entry, inherit metadata
            cache_entry = None
            if cache_entry_id:
                cache_entry = self.db.query(Text2SQLCache).filter(
                    Text2SQLCache.id == cache_entry_id
                ).first()
                
                if cache_entry:
                    # Inherit metadata from cache entry
                    display_name = display_name or cache_entry.nl_query[:100]
                    description = description or cache_entry.reasoning_trace
                    domain = domain or cache_entry.catalog_type
                    category = category or cache_entry.catalog_subtype
                    
                    # Use cache entry template if no query_text provided
                    if not query_text:
                        query_text = cache_entry.nl_query
            
            # Create new hot command
            hot_command = HotCommand(
                user_id=user_id,
                command_name=command_name,
                display_name=display_name or command_name.replace('_', ' ').title(),
                description=description,
                query_text=query_text,
                query_type=query_type,
                domain=domain,
                category=category,
                tags=tags or [],
                parameters=parameters or {},
                is_public=is_public,
                status=CommandStatus.ACTIVE,
                cache_entry_id=cache_entry_id
            )
            
            # Add inherited metadata from cache entry
            if cache_entry:
                hot_command.source_template_type = cache_entry.template_type
                hot_command.source_reasoning = cache_entry.reasoning_trace
                hot_command.source_tags = cache_entry.tags
                hot_command.source_execution_stats = {
                    "execution_count": cache_entry.execution_count or 0,
                    "success_rate": cache_entry.success_rate or 0.0,
                    "last_executed": cache_entry.last_executed.isoformat() if cache_entry.last_executed else None,
                    "complexity_level": cache_entry.complexity_level,
                    "health_status": cache_entry.health_status
                }
            
            self.db.add(hot_command)
            self.db.commit()
            
            # Update user command count
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                user.command_count += 1
                self.db.commit()
            
            logger.info(f"Created hot command: {command_name} for user {user_id}")
            return hot_command
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating hot command: {e}")
            raise
    
    def execute_command(self, request: CommandRequest) -> CommandResponse:
        """Execute a command with intelligent routing and caching."""
        start_time = datetime.datetime.now()
        
        try:
            # Parse command - check if it's a hot command or slash command
            command_text = request.command.strip()
            
            if command_text.startswith('/'):
                # Remove leading slash for processing
                command_name = command_text[1:].split()[0]
                command_args = command_text[1:].split()[1:] if len(command_text[1:].split()) > 1 else []
            else:
                # Treat as natural language query
                return self._execute_nl_query(request, start_time)
            
            # Try to find hot command first
            hot_command = self._find_hot_command(command_name, request.user_id, request.domain, request.category)
            
            if hot_command:
                return self._execute_hot_command(hot_command, request, command_args, start_time)
            else:
                # Try built-in slash commands or suggest alternatives
                return self._handle_unknown_command(command_name, request, start_time)
                
        except Exception as e:
            execution_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Command execution error: {e}")
            
            # Log failed execution
            self._log_execution(request, ExecutionStatus.ERROR, execution_time, error_message=str(e))
            
            return CommandResponse(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"error_type": type(e).__name__}
            )
    
    def _find_hot_command(
        self, 
        command_name: str, 
        user_id: int,
        domain: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[HotCommand]:
        """Find hot command using exact match or semantic similarity."""
        
        # First try exact match for user's commands
        query = self.db.query(HotCommand).filter(
            and_(
                HotCommand.user_id == user_id,
                HotCommand.command_name == command_name,
                HotCommand.status == CommandStatus.ACTIVE,
                HotCommand.deleted_at.is_(None)
            )
        )
        
        exact_match = query.first()
        if exact_match:
            return exact_match
        
        # Try exact match for public commands
        public_query = self.db.query(HotCommand).filter(
            and_(
                HotCommand.command_name == command_name,
                HotCommand.status == CommandStatus.ACTIVE,
                HotCommand.is_public == True,
                HotCommand.deleted_at.is_(None)
            )
        )
        
        # Filter by domain/category if specified
        if domain:
            public_query = public_query.filter(HotCommand.domain == domain)
        if category:
            public_query = public_query.filter(HotCommand.category == category)
            
        public_match = public_query.first()
        if public_match:
            return public_match
        
        # If no exact match, try semantic similarity
        return self._find_similar_command(command_name, user_id, domain, category)
    
    def _find_similar_command(
        self,
        command_name: str,
        user_id: int, 
        domain: Optional[str] = None,
        category: Optional[str] = None,
        similarity_threshold: float = 0.7
    ) -> Optional[HotCommand]:
        """Find similar commands using semantic similarity."""
        
        try:
            # Get candidate commands
            query = self.db.query(HotCommand).filter(
                and_(
                    or_(
                        HotCommand.user_id == user_id,
                        HotCommand.is_public == True
                    ),
                    HotCommand.status == CommandStatus.ACTIVE,
                    HotCommand.deleted_at.is_(None)
                )
            )
            
            if domain:
                query = query.filter(HotCommand.domain == domain)
            if category:
                query = query.filter(HotCommand.category == category)
            
            candidates = query.all()
            
            if not candidates:
                return None
            
            # Compute similarities
            best_match = None
            best_score = 0.0
            
            for candidate in candidates:
                # Compare with command name and description
                name_similarity = self.similarity_util.compute_string_similarity(command_name, candidate.command_name)
                desc_similarity = 0.0
                
                if candidate.description:
                    desc_similarity = self.similarity_util.compute_string_similarity(command_name, candidate.description)
                
                # Weighted similarity score
                similarity_score = max(name_similarity, desc_similarity * 0.8)
                
                if similarity_score > best_score and similarity_score >= similarity_threshold:
                    best_score = similarity_score
                    best_match = candidate
            
            if best_match:
                logger.info(f"Found similar command: {best_match.command_name} (similarity: {best_score:.3f})")
                
            return best_match
            
        except Exception as e:
            logger.error(f"Error in semantic command matching: {e}")
            return None
    
    def _execute_hot_command(
        self, 
        hot_command: HotCommand,
        request: CommandRequest,
        command_args: List[str],
        start_time: datetime.datetime
    ) -> CommandResponse:
        """Execute a hot command with parameter substitution."""
        
        try:
            # Merge parameters from command args and request
            parameters = dict(request.parameters or {})
            
            # Parse command line arguments into parameters
            if command_args and hot_command.parameter_schema:
                schema_keys = list(hot_command.parameter_schema.keys())
                for i, arg in enumerate(command_args):
                    if i < len(schema_keys):
                        parameters[schema_keys[i]] = arg
            
            # Apply default values
            if hot_command.default_values:
                for key, value in hot_command.default_values.items():
                    if key not in parameters:
                        parameters[key] = value
            
            # Execute based on query type
            if hot_command.query_type == CommandQueryType.NL2SQL:
                result = self._execute_nl2sql_command(hot_command, parameters, request)
            elif hot_command.query_type == CommandQueryType.DIRECT_SQL:
                result = self._execute_sql_command(hot_command, parameters, request)
            elif hot_command.query_type == CommandQueryType.TOOL_CALL:
                result = self._execute_tool_command(hot_command, parameters, request)
            elif hot_command.query_type == CommandQueryType.WORKFLOW:
                result = self._execute_workflow_command(hot_command, parameters, request)
            else:
                raise ValueError(f"Unsupported query type: {hot_command.query_type}")
            
            execution_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
            
            # Update command statistics
            hot_command.usage_count += 1
            hot_command.last_used = datetime.datetime.now()
            
            if result.success:
                # Update success rate
                total_executions = self.db.query(CommandExecution).filter(
                    CommandExecution.hot_command_id == hot_command.id
                ).count() + 1
                
                successful_executions = self.db.query(CommandExecution).filter(
                    and_(
                        CommandExecution.hot_command_id == hot_command.id,
                        CommandExecution.status == ExecutionStatus.SUCCESS
                    )
                ).count() + (1 if result.success else 0)
                
                hot_command.success_rate = successful_executions / total_executions
                
                # Update average execution time
                if hot_command.avg_execution_time:
                    hot_command.avg_execution_time = (
                        hot_command.avg_execution_time * (total_executions - 1) + execution_time
                    ) / total_executions
                else:
                    hot_command.avg_execution_time = execution_time
            
            self.db.commit()
            
            # Log execution
            self._log_execution(
                request, 
                ExecutionStatus.SUCCESS if result.success else ExecutionStatus.ERROR,
                execution_time,
                hot_command_id=hot_command.id,
                result_data=result.data,
                result_rows=result.result_rows,
                error_message=result.error
            )
            
            result.execution_time_ms = execution_time
            return result
            
        except Exception as e:
            execution_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Error executing hot command {hot_command.command_name}: {e}")
            
            self._log_execution(
                request,
                ExecutionStatus.ERROR,
                execution_time,
                hot_command_id=hot_command.id,
                error_message=str(e)
            )
            
            return CommandResponse(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"command_name": hot_command.command_name, "error_type": type(e).__name__}
            )
    
    def _execute_nl2sql_command(
        self, 
        hot_command: HotCommand,
        parameters: Dict[str, Any],
        request: CommandRequest
    ) -> CommandResponse:
        """Execute NL2SQL command using ThinkForge controller."""
        
        # Substitute parameters in query text
        substituted_query = self.entity_substitution.substitute_entities(
            hot_command.query_text, parameters
        )
        
        # Execute using ThinkForge NL2SQL controller
        result = self.nl2sql_controller.process_nl_query(
            substituted_query,
            domain=request.domain or hot_command.domain,
            category=request.category or hot_command.category
        )
        
        return CommandResponse(
            success=True,
            data=result.get('results'),
            sql_query=result.get('sql_query'),
            result_rows=len(result.get('results', [])),
            metadata={
                "query_type": "nl2sql",
                "original_query": hot_command.query_text,
                "substituted_query": substituted_query,
                "confidence": result.get('confidence', 0.0)
            }
        )
    
    def _execute_sql_command(
        self, 
        hot_command: HotCommand,
        parameters: Dict[str, Any],
        request: CommandRequest
    ) -> CommandResponse:
        """Execute direct SQL command."""
        
        # Substitute parameters in SQL query
        substituted_sql = self.entity_substitution.substitute_entities(
            hot_command.query_text, parameters
        )
        
        # Execute SQL directly
        # Note: This would need proper SQL execution engine
        # For now, return mock response
        return CommandResponse(
            success=True,
            data=[{"message": "SQL execution not implemented yet"}],
            sql_query=substituted_sql,
            result_rows=1,
            metadata={
                "query_type": "direct_sql",
                "original_sql": hot_command.query_text
            }
        )
    
    def _execute_tool_command(
        self, 
        hot_command: HotCommand,
        parameters: Dict[str, Any],
        request: CommandRequest
    ) -> CommandResponse:
        """Execute tool call command."""
        
        # This would integrate with ThinkForge's tool execution system
        return CommandResponse(
            success=True,
            data=[{"message": "Tool execution not implemented yet"}],
            metadata={
                "query_type": "tool_call",
                "tool_name": hot_command.query_text
            }
        )
    
    def _execute_workflow_command(
        self, 
        hot_command: HotCommand,
        parameters: Dict[str, Any],
        request: CommandRequest
    ) -> CommandResponse:
        """Execute workflow command."""
        
        # This would integrate with ThinkForge's workflow execution system
        return CommandResponse(
            success=True,
            data=[{"message": "Workflow execution not implemented yet"}],
            metadata={
                "query_type": "workflow",
                "workflow_name": hot_command.query_text
            }
        )
    
    def _execute_nl_query(self, request: CommandRequest, start_time: datetime.datetime) -> CommandResponse:
        """Execute natural language query using ThinkForge."""
        
        try:
            result = self.nl2sql_controller.process_nl_query(
                request.command,
                domain=request.domain,
                category=request.category
            )
            
            execution_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
            
            # Log execution
            self._log_execution(
                request,
                ExecutionStatus.SUCCESS,
                execution_time,
                result_data=result.get('results'),
                result_rows=len(result.get('results', []))
            )
            
            return CommandResponse(
                success=True,
                data=result.get('results'),
                sql_query=result.get('sql_query'),
                result_rows=len(result.get('results', [])),
                execution_time_ms=execution_time,
                metadata={
                    "query_type": "natural_language",
                    "confidence": result.get('confidence', 0.0)
                }
            )
            
        except Exception as e:
            execution_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
            
            self._log_execution(
                request,
                ExecutionStatus.ERROR,
                execution_time,
                error_message=str(e)
            )
            
            return CommandResponse(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"query_type": "natural_language", "error_type": type(e).__name__}
            )
    
    def _handle_unknown_command(
        self, 
        command_name: str, 
        request: CommandRequest, 
        start_time: datetime.datetime
    ) -> CommandResponse:
        """Handle unknown command by suggesting alternatives."""
        
        execution_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
        
        # Get command suggestions
        suggestions = self.get_command_suggestions(command_name, request.user_id, request.domain)
        
        self._log_execution(
            request,
            ExecutionStatus.ERROR,
            execution_time,
            error_message=f"Unknown command: /{command_name}"
        )
        
        return CommandResponse(
            success=False,
            error=f"Unknown command: /{command_name}",
            execution_time_ms=execution_time,
            metadata={
                "error_type": "unknown_command",
                "suggestions": [s.dict() for s in suggestions[:5]]  # Top 5 suggestions
            }
        )
    
    def get_command_suggestions(
        self, 
        query: str, 
        user_id: int,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[CommandSuggestion]:
        """Get command suggestions based on similarity."""
        
        try:
            # Get candidate commands
            query_obj = self.db.query(HotCommand).filter(
                and_(
                    or_(
                        HotCommand.user_id == user_id,
                        HotCommand.is_public == True
                    ),
                    HotCommand.status == CommandStatus.ACTIVE,
                    HotCommand.deleted_at.is_(None)
                )
            )
            
            if domain:
                query_obj = query_obj.filter(HotCommand.domain == domain)
            
            candidates = query_obj.order_by(desc(HotCommand.usage_count)).limit(limit * 2).all()
            
            suggestions = []
            for candidate in candidates:
                # Compute similarity
                name_sim = self.similarity_util.compute_string_similarity(query, candidate.command_name)
                desc_sim = 0.0
                
                if candidate.description:
                    desc_sim = self.similarity_util.compute_string_similarity(query, candidate.description)
                
                similarity_score = max(name_sim, desc_sim * 0.8)
                
                if similarity_score > 0.3:  # Lower threshold for suggestions
                    suggestions.append(CommandSuggestion(
                        command_name=candidate.command_name,
                        display_name=candidate.display_name,
                        description=candidate.description,
                        similarity_score=similarity_score,
                        usage_count=candidate.usage_count,
                        rating=candidate.rating
                    ))
            
            # Sort by similarity score and usage
            suggestions.sort(key=lambda x: (x.similarity_score * 0.7 + (x.usage_count / 100) * 0.3), reverse=True)
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting command suggestions: {e}")
            return []
    
    def _log_execution(
        self,
        request: CommandRequest,
        status: ExecutionStatus,
        execution_time_ms: int,
        hot_command_id: Optional[int] = None,
        result_data: Optional[Any] = None,
        result_rows: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Log command execution for analytics."""
        
        try:
            execution = CommandExecution(
                user_id=request.user_id,
                hot_command_id=hot_command_id,
                session_id=request.session_id,
                command_name=request.command.split()[0] if request.command else "unknown",
                parameters=request.parameters,
                raw_input=request.command,
                domain=request.domain,
                category=request.category,
                status=status.value,
                execution_time_ms=execution_time_ms,
                result_rows=result_rows,
                result_data=result_data if isinstance(result_data, dict) else None,
                error_message=error_message
            )
            
            self.db.add(execution)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging execution: {e}")
            # Don't raise - logging failures shouldn't break command execution
    
    # ==========================================
    # Cache Entry Integration Methods
    # ==========================================
    
    def get_available_cache_entries(
        self,
        user_id: int,
        template_type: Optional[str] = None,
        catalog_type: Optional[str] = None,
        catalog_subtype: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get available cache entries that can be converted to hot commands."""
        
        try:
            query = self.db.query(Text2SQLCache).filter(
                Text2SQLCache.status == Status.ACTIVE
            )
            
            # Filter by template type
            if template_type:
                query = query.filter(Text2SQLCache.template_type == template_type)
            
            # Filter by catalog
            if catalog_type:
                query = query.filter(Text2SQLCache.catalog_type == catalog_type)
            if catalog_subtype:
                query = query.filter(Text2SQLCache.catalog_subtype == catalog_subtype)
            
            # Order by execution stats and recency
            query = query.order_by(
                desc(Text2SQLCache.execution_count),
                desc(Text2SQLCache.success_rate),
                desc(Text2SQLCache.updated_at)
            )
            
            cache_entries = query.offset(offset).limit(limit).all()
            
            # Check which entries already have hot commands
            cache_ids = [entry.id for entry in cache_entries]
            existing_commands = {}
            if cache_ids:
                existing = self.db.query(HotCommand).filter(
                    HotCommand.cache_entry_id.in_(cache_ids),
                    HotCommand.deleted_at.is_(None)
                ).all()
                existing_commands = {cmd.cache_entry_id: cmd for cmd in existing}
            
            # Format response
            results = []
            for entry in cache_entries:
                existing_cmd = existing_commands.get(entry.id)
                
                results.append({
                    "id": entry.id,
                    "nl_query": entry.nl_query,
                    "template_type": entry.template_type,
                    "catalog_type": entry.catalog_type,
                    "catalog_subtype": entry.catalog_subtype,
                    "catalog_name": entry.catalog_name,
                    "reasoning_trace": entry.reasoning_trace,
                    "tags": entry.tags,
                    "execution_count": entry.execution_count or 0,
                    "success_rate": entry.success_rate or 0.0,
                    "complexity_level": entry.complexity_level,
                    "health_status": entry.health_status,
                    "last_executed": entry.last_executed.isoformat() if entry.last_executed else None,
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat(),
                    "has_hot_command": existing_cmd is not None,
                    "hot_command_name": existing_cmd.command_name if existing_cmd else None,
                    "hot_command_id": existing_cmd.id if existing_cmd else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving cache entries: {e}")
            return []
    
    def create_hot_command_from_cache(
        self,
        user_id: int,
        cache_entry_id: int,
        command_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_public: bool = False,
        tags: Optional[List[str]] = None
    ) -> HotCommand:
        """Create a hot command from an existing cache entry."""
        
        try:
            # Get cache entry
            cache_entry = self.db.query(Text2SQLCache).filter(
                Text2SQLCache.id == cache_entry_id,
                Text2SQLCache.status == Status.ACTIVE
            ).first()
            
            if not cache_entry:
                raise ValueError(f"Cache entry {cache_entry_id} not found or inactive")
            
            # Check if command name already exists for user
            existing = self.db.query(HotCommand).filter(
                and_(
                    HotCommand.user_id == user_id,
                    HotCommand.command_name == command_name,
                    HotCommand.deleted_at.is_(None)
                )
            ).first()
            
            if existing:
                raise ValueError(f"Command '{command_name}' already exists for user")
            
            # Determine query type based on template type
            query_type = self._map_template_type_to_query_type(cache_entry.template_type)
            
            # Create hot command using cache entry data
            hot_command = self.create_hot_command(
                user_id=user_id,
                command_name=command_name,
                query_text=cache_entry.nl_query,
                display_name=display_name or cache_entry.nl_query[:100],
                description=description or cache_entry.reasoning_trace,
                query_type=query_type,
                domain=cache_entry.catalog_type,
                category=cache_entry.catalog_subtype,
                tags=tags or (list(cache_entry.tags.keys()) if cache_entry.tags else []),
                is_public=is_public,
                cache_entry_id=cache_entry_id
            )
            
            logger.info(f"Created hot command '{command_name}' from cache entry {cache_entry_id}")
            return hot_command
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating hot command from cache entry: {e}")
            raise
    
    def _map_template_type_to_query_type(self, template_type: str) -> str:
        """Map ThinkForge template type to Hot Commands query type."""
        
        mapping = {
            TemplateType.SQL: CommandQueryType.NL2SQL,
            TemplateType.DUCKDB_SQL: CommandQueryType.NL2SQL,
            TemplateType.NOSQL: CommandQueryType.NL2SQL,
            TemplateType.API: CommandQueryType.TOOL_CALL,
            TemplateType.MCP_TOOL: CommandQueryType.TOOL_CALL,
            TemplateType.FUNCTION: CommandQueryType.TOOL_CALL,
            TemplateType.WORKFLOW: CommandQueryType.WORKFLOW,
            TemplateType.RECIPE: CommandQueryType.WORKFLOW,
            TemplateType.RECIPE_STEP: CommandQueryType.WORKFLOW,
            TemplateType.CLI: CommandQueryType.DIRECT_SQL,
            TemplateType.SCRIPT: CommandQueryType.DIRECT_SQL,
            TemplateType.PROMPT: CommandQueryType.NL2SQL
        }
        
        return mapping.get(template_type, CommandQueryType.NL2SQL)
    
    def get_cache_entry_details(self, cache_entry_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache entry."""
        
        try:
            cache_entry = self.db.query(Text2SQLCache).filter(
                Text2SQLCache.id == cache_entry_id
            ).first()
            
            if not cache_entry:
                return None
            
            # Check if there's already a hot command for this cache entry
            existing_command = self.db.query(HotCommand).filter(
                HotCommand.cache_entry_id == cache_entry_id,
                HotCommand.deleted_at.is_(None)
            ).first()
            
            return {
                "id": cache_entry.id,
                "nl_query": cache_entry.nl_query,
                "template": cache_entry.template,
                "template_type": cache_entry.template_type,
                "is_template": cache_entry.is_template,
                "entity_replacements": cache_entry.entity_replacements,
                "reasoning_trace": cache_entry.reasoning_trace,
                "tags": cache_entry.tags,
                "catalog_type": cache_entry.catalog_type,
                "catalog_subtype": cache_entry.catalog_subtype,
                "catalog_name": cache_entry.catalog_name,
                "status": cache_entry.status,
                "tool_capabilities": cache_entry.tool_capabilities,
                "execution_config": cache_entry.execution_config,
                "health_status": cache_entry.health_status,
                "recipe_steps": cache_entry.recipe_steps,
                "required_tools": cache_entry.required_tools,
                "execution_time_estimate": cache_entry.execution_time_estimate,
                "complexity_level": cache_entry.complexity_level,
                "success_rate": cache_entry.success_rate,
                "last_executed": cache_entry.last_executed.isoformat() if cache_entry.last_executed else None,
                "execution_count": cache_entry.execution_count,
                "created_at": cache_entry.created_at.isoformat(),
                "updated_at": cache_entry.updated_at.isoformat(),
                "has_hot_command": existing_command is not None,
                "hot_command": {
                    "id": existing_command.id,
                    "command_name": existing_command.command_name,
                    "display_name": existing_command.display_name,
                    "is_public": existing_command.is_public,
                    "usage_count": existing_command.usage_count,
                    "created_at": existing_command.created_at.isoformat()
                } if existing_command else None
            }
            
        except Exception as e:
            logger.error(f"Error retrieving cache entry details: {e}")
            return None