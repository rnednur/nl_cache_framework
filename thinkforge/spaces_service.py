"""
Business logic service for spaces management in ThinkForge.
Integrates with ThinkForge controller and provides space execution capabilities.
"""

import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from .hotcommands_models import (
    Space, SpaceAccess, User, ContentType, StorageBackend, 
    ScheduleType, AccessLevel
)
from .storage_service import storage_service, StorageError
from .controller import Text2SQLController, TemplateType
from .models import Text2SQLCache
import asyncio
import re

logger = logging.getLogger(__name__)


class SpaceExecutionError(Exception):
    """Exception raised during space execution."""
    pass


class ThinkForgeSpacesService:
    """Service for managing spaces operations in ThinkForge."""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.controller = Text2SQLController()
        self.storage = storage_service
    
    async def execute_template(self, space: Space, parameters: Dict[str, Any], 
                             user_id: int) -> Dict[str, Any]:
        """Execute a template space with provided parameters."""
        if not space.is_template_space():
            raise SpaceExecutionError("Space is not a template")
        
        # Validate parameters
        validation_result = space.validate_template_params(parameters)
        if not validation_result['valid']:
            raise SpaceExecutionError(f"Invalid parameters: {', '.join(validation_result['errors'])}")
        
        # Render query from template
        try:
            rendered_query = space.render_template_query(parameters)
            if not rendered_query:
                raise SpaceExecutionError("Template rendering produced empty query")
        except Exception as e:
            raise SpaceExecutionError(f"Template rendering failed: {str(e)}")
        
        # Generate execution ID
        execution_id = f"tmpl_{space.id}_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()
        
        logger.info(f"Executing template {space.id} with execution_id {execution_id}")
        
        try:
            # Execute the rendered query using ThinkForge controller
            completion_result = await self.controller.complete(
                query=rendered_query,
                user_id=user_id,
                domain=space.domain,
                category=space.category
            )
            
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            # Prepare execution result
            execution_result = {
                'execution_id': execution_id,
                'space_id': space.id,
                'status': 'completed',
                'started_at': started_at,
                'completed_at': completed_at,
                'duration_ms': duration_ms,
                'result_data': completion_result.get('response', {}),
                'parameters_used': parameters,
                'rendered_query': rendered_query,
                'row_count': self._extract_row_count(completion_result),
                'cache_hit': completion_result.get('cache_hit', False),
                'similarity_score': completion_result.get('similarity_score', 0.0)
            }
            
            # Store result if space has external storage configured
            if space.storage_backend != StorageBackend.LOCAL or space.content_type == ContentType.WEBPAGE:
                storage_path, public_url = await self._store_execution_result(
                    space, execution_result, user_id
                )
                execution_result.update({
                    'storage_path': storage_path,
                    'public_url': public_url
                })
            
            return execution_result
            
        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            error_result = {
                'execution_id': execution_id,
                'space_id': space.id,
                'status': 'failed',
                'started_at': started_at,
                'completed_at': completed_at,
                'duration_ms': duration_ms,
                'error_message': str(e),
                'parameters_used': parameters,
                'rendered_query': rendered_query
            }
            
            logger.error(f"Template execution {execution_id} failed: {e}")
            raise SpaceExecutionError(f"Execution failed: {str(e)}")
    
    async def execute_space(self, space: Space, user_id: int) -> Dict[str, Any]:
        """Execute a regular space (re-run saved query)."""
        if not space.source_query and not space.base_query:
            raise SpaceExecutionError("No query available for execution")
        
        query = space.source_query or space.base_query
        execution_id = f"space_{space.id}_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()
        
        logger.info(f"Executing space {space.id} with execution_id {execution_id}")
        
        try:
            # Execute the query using ThinkForge controller
            completion_result = await self.controller.complete(
                query=query,
                user_id=user_id,
                domain=space.domain,
                category=space.category
            )
            
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            execution_result = {
                'execution_id': execution_id,
                'space_id': space.id,
                'status': 'completed',
                'started_at': started_at,
                'completed_at': completed_at,
                'duration_ms': duration_ms,
                'result_data': completion_result.get('response', {}),
                'query_executed': query,
                'row_count': self._extract_row_count(completion_result),
                'cache_hit': completion_result.get('cache_hit', False),
                'similarity_score': completion_result.get('similarity_score', 0.0)
            }
            
            # Update space content with new results
            if self.db:
                space.content_data = completion_result.get('response', {})
                if not space.content_metadata:
                    space.content_metadata = {}
                
                space.content_metadata.update({
                    'last_execution': execution_id,
                    'last_execution_time': completed_at.isoformat(),
                    'execution_duration_ms': duration_ms,
                    'row_count': execution_result.get('row_count', 0),
                    'cache_hit': completion_result.get('cache_hit', False)
                })
                
                self.db.commit()
            
            return execution_result
            
        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            logger.error(f"Space execution {execution_id} failed: {e}")
            raise SpaceExecutionError(f"Execution failed: {str(e)}")
    
    async def _store_execution_result(self, space: Space, execution_result: Dict[str, Any],
                                    user_id: int) -> Tuple[str, str]:
        """Store execution result to external storage."""
        try:
            # Generate content based on space content type
            if space.content_type == ContentType.WEBPAGE:
                content = self.storage.generate_html_report(
                    space_data={
                        'id': space.id,
                        'name': space.name,
                        'display_name': space.display_name,
                        'description': space.description,
                        'content_type': space.content_type,
                        'domain': space.domain
                    },
                    execution_result=execution_result
                )
                content_type = 'text/html'
            else:
                content = json.dumps(execution_result, default=str, indent=2)
                content_type = 'application/json'
            
            # Upload to storage
            storage_path, public_url = self.storage.upload_space_content(
                space.id, content, space.storage_backend, content_type
            )
            
            return storage_path, public_url
            
        except StorageError as e:
            logger.error(f"Failed to store execution result: {e}")
            raise SpaceExecutionError(f"Storage failed: {e}")
    
    def create_space_from_cache_entry(self, cache_entry_id: int, space_name: str, 
                                    owner_id: int, display_name: str = None,
                                    description: str = None, make_template: bool = False) -> Space:
        """Convert ThinkForge cache entry to reusable space."""
        if not self.db:
            raise SpaceExecutionError("Database session required for cache operations")
        
        # Get cache entry
        cache_entry = self.db.query(Text2SQLCache).filter(
            Text2SQLCache.id == cache_entry_id
        ).first()
        
        if not cache_entry:
            raise SpaceExecutionError(f"Cache entry {cache_entry_id} not found")
        
        # Determine content type based on template type
        content_type = self._map_template_type_to_content_type(cache_entry.template_type)
        
        # Create space
        space = Space(
            owner_id=owner_id,
            name=space_name,
            display_name=display_name or space_name.replace('_', ' ').title(),
            description=description or f"Space created from cache entry: {cache_entry.query}",
            content_type=content_type,
            source_query=cache_entry.template,
            domain=cache_entry.domain,
            category=cache_entry.category,
            tags=cache_entry.tags or [],
            content_data=cache_entry.execution_config,
            content_metadata={
                'cache_entry_id': cache_entry_id,
                'original_template_type': cache_entry.template_type,
                'similarity_score': getattr(cache_entry, 'similarity_score', None),
                'created_from_cache': True,
                'cache_query': cache_entry.query
            }
        )
        
        # If it has entity replacements or make_template is True, make it a template
        if (cache_entry.entity_replacements and cache_entry.entity_replacements != {}) or make_template:
            space.is_template = True
            space.content_type = ContentType.TEMPLATE
            space.base_query = cache_entry.template
            space.template_parameters = self._extract_template_parameters(cache_entry)
            space.template_schema = self._generate_parameter_schema(space.template_parameters)
        
        return space
    
    def _map_template_type_to_content_type(self, template_type: str) -> ContentType:
        """Map ThinkForge template type to Space content type."""
        mapping = {
            TemplateType.SQL: ContentType.QUERY_RESULT,
            TemplateType.URL: ContentType.QUERY_RESULT,
            TemplateType.API: ContentType.QUERY_RESULT,
            TemplateType.WORKFLOW: ContentType.QUERY_RESULT,
            TemplateType.SCRIPT: ContentType.QUERY_RESULT,
            TemplateType.GRAPHQL: ContentType.QUERY_RESULT,
            TemplateType.PROMPT: ContentType.QUERY_RESULT,
            TemplateType.REASONING_STEPS: ContentType.REPORT,
            TemplateType.DSL: ContentType.QUERY_RESULT,
        }
        return mapping.get(template_type, ContentType.QUERY_RESULT)
    
    def _extract_template_parameters(self, cache_entry: Text2SQLCache) -> List[Dict[str, Any]]:
        """Extract template parameters from cache entry."""
        parameters = []
        
        if cache_entry.entity_replacements:
            for entity_name, entity_data in cache_entry.entity_replacements.items():
                parameters.append({
                    'name': entity_name,
                    'type': self._infer_parameter_type(entity_data),
                    'required': True,
                    'description': f'Parameter {entity_name}',
                    'default_value': entity_data.get('value') if isinstance(entity_data, dict) else entity_data
                })
        
        # Also extract parameters from template using simple pattern matching
        import re
        template = cache_entry.template or ""
        
        # Find placeholder patterns like {param_name}
        placeholders = re.findall(r'\{(\w+)\}', template)
        for placeholder in placeholders:
            if not any(p['name'] == placeholder for p in parameters):
                parameters.append({
                    'name': placeholder,
                    'type': 'string',
                    'required': True,
                    'description': f'Template parameter {placeholder}'
                })
        
        return parameters
    
    def _infer_parameter_type(self, entity_data: Any) -> str:
        """Infer parameter type from entity data."""
        if isinstance(entity_data, dict):
            value = entity_data.get('value')
        else:
            value = entity_data
        
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, str):
            # Try to detect date patterns
            if re.match(r'\d{4}-\d{2}-\d{2}', value):
                return 'date'
            return 'string'
        else:
            return 'string'
    
    def _generate_parameter_schema(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate JSON schema for template parameters."""
        schema = {
            'type': 'object',
            'properties': {},
            'required': []
        }
        
        for param in parameters:
            param_name = param['name']
            param_type = param.get('type', 'string')
            
            property_schema = {
                'type': param_type,
                'description': param.get('description', f'Parameter {param_name}')
            }
            
            if 'default_value' in param:
                property_schema['default'] = param['default_value']
            
            schema['properties'][param_name] = property_schema
            
            if param.get('required', False):
                schema['required'].append(param_name)
        
        return schema
    
    def _extract_row_count(self, completion_result: Dict[str, Any]) -> int:
        """Extract row count from completion result."""
        response = completion_result.get('response', {})
        
        if isinstance(response, dict):
            # Try different possible locations for row count
            if 'rows' in response:
                rows = response['rows']
                if isinstance(rows, list):
                    return len(rows)
            elif 'data' in response:
                data = response['data']
                if isinstance(data, list):
                    return len(data)
            elif 'result' in response:
                result = response['result']
                if isinstance(result, list):
                    return len(result)
        
        return 0
    
    async def schedule_space_execution(self, space: Space) -> bool:
        """Schedule a space for automatic execution."""
        if space.schedule_type == ScheduleType.NONE:
            return False
        
        try:
            # Calculate next execution time
            next_execution = space.schedule_next_execution()
            if not next_execution:
                return False
            
            # In a full implementation, this would schedule with Celery or similar
            # For now, just update the next execution time
            if self.db:
                space.next_execution = next_execution
                space.is_scheduled_active = True
                self.db.commit()
            
            logger.info(f"Scheduled space {space.id} for execution at {next_execution}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule space {space.id}: {e}")
            return False
    
    def get_space_analytics(self, space: Space, days: int = 30) -> Dict[str, Any]:
        """Get analytics data for a space."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        analytics = {
            'space_id': space.id,
            'total_views': space.view_count,
            'total_executions': space.execution_count,
            'last_30_days_views': max(0, space.view_count - 10),  # Mock calculation
            'last_30_days_executions': max(0, space.execution_count - 5),  # Mock calculation
            'unique_viewers': max(1, space.view_count // 3),  # Mock calculation
            'avg_execution_time_ms': space.content_metadata.get('execution_duration_ms', 500) if space.content_metadata else 500,
            'performance_metrics': {
                'cache_hit_rate': 0.8,  # Mock
                'avg_similarity_score': 0.85,  # Mock
                'success_rate': 0.95  # Mock
            }
        }
        
        # Add template-specific analytics
        if space.is_template_space():
            analytics['top_parameters'] = [
                {'parameter': 'date_range', 'usage_count': 25, 'avg_value': '2024-01-01'},
                {'parameter': 'status', 'usage_count': 20, 'avg_value': 'active'},
                {'parameter': 'region', 'usage_count': 15, 'avg_value': 'US'}
            ]
        
        return analytics
    
    def create_space_from_execution(self, execution_data: Dict[str, Any], 
                                  space_name: str, owner_id: int,
                                  description: str = None) -> Space:
        """Create a space from execution result data."""
        space = Space(
            owner_id=owner_id,
            name=space_name,
            display_name=space_name.replace('_', ' ').title(),
            description=description or "Space created from execution result",
            content_type=ContentType.QUERY_RESULT,
            content_data=execution_data.get('result_data', {}),
            content_metadata={
                'created_from_execution': True,
                'execution_id': execution_data.get('execution_id'),
                'execution_time': execution_data.get('completed_at'),
                'row_count': execution_data.get('row_count', 0)
            },
            source_query=execution_data.get('query_executed') or execution_data.get('rendered_query')
        )
        
        return space
    
    def validate_space_access(self, space: Space, user_id: int, 
                            required_access: AccessLevel = AccessLevel.VIEW) -> bool:
        """Validate user access to space."""
        return space.can_be_accessed_by(user_id, required_access)
    
    def grant_space_access(self, space: Space, user_id: int, 
                         access_level: AccessLevel, granted_by: int,
                         expires_at: datetime = None) -> SpaceAccess:
        """Grant access to a space."""
        if not self.db:
            raise SpaceExecutionError("Database session required for access operations")
        
        # Check if access already exists
        existing_access = self.db.query(SpaceAccess).filter(
            and_(
                SpaceAccess.space_id == space.id,
                SpaceAccess.user_id == user_id
            )
        ).first()
        
        if existing_access:
            # Update existing access
            existing_access.access_level = access_level
            existing_access.granted_by = granted_by
            existing_access.is_active = True
            existing_access.expires_at = expires_at
            access = existing_access
        else:
            # Create new access
            access = SpaceAccess(
                space_id=space.id,
                user_id=user_id,
                access_level=access_level,
                granted_by=granted_by,
                expires_at=expires_at
            )
            self.db.add(access)
        
        # Update space share count
        space.share_count += 1
        self.db.commit()
        
        return access
    
    def revoke_space_access(self, space: Space, user_id: int) -> bool:
        """Revoke access to a space."""
        if not self.db:
            raise SpaceExecutionError("Database session required for access operations")
        
        access = self.db.query(SpaceAccess).filter(
            and_(
                SpaceAccess.space_id == space.id,
                SpaceAccess.user_id == user_id,
                SpaceAccess.is_active == True
            )
        ).first()
        
        if access:
            access.is_active = False
            self.db.commit()
            return True
        
        return False


# Global service instance function
def get_spaces_service(db: Session) -> ThinkForgeSpacesService:
    """Get spaces service instance with database session."""
    return ThinkForgeSpacesService(db)