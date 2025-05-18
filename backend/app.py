from fastapi import FastAPI, Depends, HTTPException, Request, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, Tuple, List, Dict, Any
import uuid
import logging
import os
import sys
import time
import datetime
from sqlalchemy import or_, func
import json
from pydantic import BaseModel, Field
import csv
import io
import requests

# Import database configuration
from database import get_db, engine, SessionLocal

# Import LLM service for enhanced completions
from llm_service import LLMService

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the ThinkForge framework
try:
    from thinkforge.controller import (
        Text2SQLController,
        TemplateType,
        Text2SQLEntitySubstitution,
    )
    from thinkforge.models import Text2SQLCache, UsageLog, Base
except ImportError as e:
    print(f"Error importing thinkforge: {e}")
    print("Make sure the framework is installed with: pip install -e .")
    print(f"Current sys.path: {sys.path}")
    raise

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_server")

# Add a file handler to write logs to a file
file_handler = logging.FileHandler('swagger_upload.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# Create database tables
Base.metadata.create_all(bind=engine)

# Load configuration
DEFAULT_MODEL_NAME = os.environ.get(
    "DEFAULT_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2"
)
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.85"))

# Create a singleton instance of Text2SQLController to be reused across requests
controller_instance = None
db_for_controller = None
similarity_util = None

def get_controller(db_session):
    """Get a shared instance of Text2SQLController"""
    global controller_instance, db_for_controller, similarity_util
    if similarity_util is None:
        logger.info("Initializing shared similarity utility")
        from thinkforge import Text2SQLSimilarity
        similarity_util = Text2SQLSimilarity(model_name=DEFAULT_MODEL_NAME)
    if controller_instance is None:
        logger.info("Initializing singleton Text2SQLController instance")
        controller_instance = Text2SQLController(
            db_session=db_session, similarity_model_name=DEFAULT_MODEL_NAME
        )
        controller_instance.similarity_util = similarity_util
        db_for_controller = db_session
    else:
        # Update the database session if it's different, but keep the same controller
        if db_for_controller != db_session:
            logger.info("Updating database session for existing Text2SQLController")
            controller_instance.session = db_session
            db_for_controller = db_session
    return controller_instance

# Pydantic models for request/response schema
class CacheEntryCreate(BaseModel):
    nl_query: str = Field(..., description="The natural language query")
    template: str = Field(..., description="The template (SQL, URL, API spec, etc.)")
    template_type: str = Field(default="sql", description="Type of template (sql, url, api, workflow)")
    reasoning_trace: Optional[str] = Field(None, description="Optional explanation of the template")
    is_template: bool = Field(default=False, description="Flag indicating if this entry contains placeholders")
    entity_replacements: Optional[Dict[str, Any]] = Field(None, description="JSON defining placeholder substitutions")
    tags: Optional[Dict[str, List[str]]] = Field(None, description="Dictionary of tags for categorization, with name as key and list of values")
    database_name: Optional[str] = Field(None, description="Target database identifier")
    schema_name: Optional[str] = Field(None, description="Target schema identifier")
    catalog_type: Optional[str] = Field(None, description="Catalog type identifier")
    catalog_subtype: Optional[str] = Field(None, description="Catalog subtype identifier")
    catalog_name: Optional[str] = Field(None, description="Catalog name identifier")

class CompleteRequest(BaseModel):
    prompt: str = Field(..., description="The natural language prompt to complete")

class EntitySubstitutionRequest(BaseModel):
    entity_values: Dict[str, Any] = Field(..., description="Entity values for substitution")

# Initialize FastAPI application
app = FastAPI(
    title="ThinkForge MCP Server",
    description="Model Context Protocol server for ThinkForge",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
# Use an absolute path based on the current file's location
# static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/static"))
# app.mount("/static", StaticFiles(directory=static_dir), name="static")

"""
Main FastAPI application for the NL Cache Model Context Protocol (MCP) Server.

Provides endpoints for:
- Query completion via cache (/v1/complete)
- Cache management (/v1/cache)
- API/UI interaction (/api/*, /)
- Health checks (/health)

Dependencies:
- NL Cache Framework (nl_cache_framework)
- SQLAlchemy compatible database (for cache persistence)

Configuration is primarily through environment variables (see backend/README.md or project root).
"""

# Routes
# @app.get("/")
# async def root():
#     """UI Home page"""
#     # Construct path relative to this file (app.py)
#     template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/templates/index.html"))
#     return FileResponse(template_path)


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    db_status = "unknown"
    try:
        # Simple query to check DB connection using the injected session
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return {
        "status": "healthy",
        "service": "thinkforge-mcp",
        "dependencies": {
            "database": db_status,
        },
    }


@app.get("/v1/cache/stats")
async def get_cache_stats(
    template_type: Optional[str] = None,
    catalog_type: Optional[str] = None,
    catalog_subtype: Optional[str] = None,
    catalog_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get statistics about the cache entries.

    Returns:
        JSON response with counts of total entries and breakdown by template type.

    Raises:
        HTTPException(500): If an error occurs while fetching stats.
    """
    try:
        controller = get_controller(db)
        
        # Base query for filtering
        base_query = db.query(Text2SQLCache)
        filtered_query = base_query
        
        # Apply filters if provided
        if catalog_type:
            filtered_query = filtered_query.filter(Text2SQLCache.catalog_type == catalog_type)
        if catalog_subtype:
            filtered_query = filtered_query.filter(Text2SQLCache.catalog_subtype == catalog_subtype)
        if catalog_name:
            filtered_query = filtered_query.filter(Text2SQLCache.catalog_name == catalog_name)
            
        # Get basic stats with filters
        total_count = filtered_query.count()
        valid_count = filtered_query.filter(Text2SQLCache.status == "active").count()
        template_count = filtered_query.filter(Text2SQLCache.is_template == True).count()
        
        # Handle type counts with error handling for each template type
        type_counts = {}
        for template_type_enum in TemplateType:
            try:
                count = filtered_query.filter(
                    Text2SQLCache.template_type == template_type_enum
                ).count()
                type_counts[template_type_enum.value] = count
            except Exception as e:
                logger.warning(f"Error getting count for template type {template_type_enum}: {str(e)}")
                type_counts[template_type_enum.value] = 0
        
        # If template_type filter is specified, only return that type count
        if template_type:
            for ttype in type_counts.keys():
                if ttype != template_type:
                    type_counts[ttype] = 0
        
        # Get recent usage data (last 30 days)
        recent_usage = []
        try:
            thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
            usage_query = db.query(
                func.date_trunc('day', UsageLog.timestamp).label('date'),
                func.count(UsageLog.id).label('count')
            ).filter(
                UsageLog.timestamp >= thirty_days_ago
            )
            
            # Apply catalog filters to usage logs if specified
            if catalog_type:
                usage_query = usage_query.filter(UsageLog.catalog_type == catalog_type)
            if catalog_subtype:
                usage_query = usage_query.filter(UsageLog.catalog_subtype == catalog_subtype)
            if catalog_name:
                usage_query = usage_query.filter(UsageLog.catalog_name == catalog_name)
                
            usage_data = usage_query.group_by(
                func.date_trunc('day', UsageLog.timestamp)
            ).order_by(
                func.date_trunc('day', UsageLog.timestamp)
            ).all()
            
            recent_usage = [
                {"date": str(entry.date.date()), "count": entry.count}
                for entry in usage_data
            ]
        except Exception as e:
            logger.warning(f"Error getting recent usage data: {str(e)}")
            
        # Get popular entries
        popular_entries = []
        try:
            # Start with the cache entries query that already has catalog filters
            popular_query = db.query(
                Text2SQLCache.id,
                Text2SQLCache.nl_query,
                func.count(UsageLog.id).label('usage_count')
            ).join(
                UsageLog, UsageLog.cache_entry_id == Text2SQLCache.id, isouter=True
            )
            
            # Apply catalog filters if specified (for UsageLog table)
            if catalog_type:
                popular_query = popular_query.filter(
                    or_(
                        Text2SQLCache.catalog_type == catalog_type,
                        UsageLog.catalog_type == catalog_type
                    )
                )
            if catalog_subtype:
                popular_query = popular_query.filter(
                    or_(
                        Text2SQLCache.catalog_subtype == catalog_subtype,
                        UsageLog.catalog_subtype == catalog_subtype
                    )
                )
            if catalog_name:
                popular_query = popular_query.filter(
                    or_(
                        Text2SQLCache.catalog_name == catalog_name,
                        UsageLog.catalog_name == catalog_name
                    )
                )
                
            popular_data = popular_query.group_by(
                Text2SQLCache.id, Text2SQLCache.nl_query
            ).order_by(
                func.count(UsageLog.id).desc()
            ).limit(5).all()
            
            popular_entries = [
                {"id": entry.id, "nl_query": entry.nl_query, "usage_count": entry.usage_count or 0}
                for entry in popular_data
            ]
        except Exception as e:
            logger.warning(f"Error getting popular entries: {str(e)}")
        
        return {
            "total_entries": total_count,
            "valid_entries": valid_count,
            "template_entries": template_count,
            "by_template_type": type_counts,
            "recent_usage": recent_usage,
            "popular_entries": popular_entries
        }
    except Exception as e:
        logger.error(f"Error in /v1/cache/stats: {str(e)}", exc_info=True)
        # Return fallback data on any error
        return {
            "total_entries": 0,
            "valid_entries": 0,
            "template_entries": 0,
            "by_template_type": {ttype.value: 0 for ttype in TemplateType},
            "recent_usage": [],
            "popular_entries": []
        }


@app.get("/v1/cache/catalogs")
async def get_catalog_values(db: Session = Depends(get_db)):
    """Get unique catalog values for filtering cache entries"""
    try:
        controller = get_controller(db)
        catalog_types = controller.get_distinct_values("catalog_type")
        catalog_subtypes = controller.get_distinct_values("catalog_subtype")
        catalog_names = controller.get_distinct_values("catalog_name")
        return {
            "catalog_types": [ct for ct in catalog_types if ct],
            "catalog_subtypes": [cs for cs in catalog_subtypes if cs],
            "catalog_names": [cn for cn in catalog_names if cn]
        }
    except Exception as e:
        logger.error(f"Error in /v1/cache/catalogs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching catalog values: {str(e)}")


@app.get("/v1/cache/compatible")
async def get_compatible_cache_entries(
    catalog_type: Optional[str] = None,
    catalog_subtype: Optional[str] = None,
    catalog_name: Optional[str] = None,
    exclude_ids: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get cache entries that can be used as workflow steps.
    Optionally filter by catalog fields and exclude certain IDs.
    """
    # Base query for all cache entries that can be used as steps
    # Generally, any active cache entry can be a step in a workflow
    query = db.query(Text2SQLCache).filter(Text2SQLCache.status == "active")
    
    # Apply catalog filters if specified
    # Include entries with matching catalog_type OR where catalog_type is NULL
    if catalog_type:
        query = query.filter(or_(
            Text2SQLCache.catalog_type == catalog_type,
            Text2SQLCache.catalog_type == None  # Also include entries with NULL catalog_type
        ))
    
    if catalog_subtype:
        query = query.filter(or_(
            Text2SQLCache.catalog_subtype == catalog_subtype,
            Text2SQLCache.catalog_subtype == None  # Also include entries with NULL catalog_subtype
        ))
    
    if catalog_name:
        query = query.filter(or_(
            Text2SQLCache.catalog_name == catalog_name,
            Text2SQLCache.catalog_name == None  # Also include entries with NULL catalog_name
        ))
    
    # If exclude_ids is provided, exclude those entries
    if exclude_ids:
        try:
            ids_to_exclude = [int(id_str) for id_str in exclude_ids.split(',') if id_str.strip()]
            if ids_to_exclude:
                query = query.filter(Text2SQLCache.id.notin_(ids_to_exclude))
        except ValueError:
            # If any ID is not a valid integer, log but continue
            logger.warning(f"Invalid ID format in exclude_ids: {exclude_ids}")
    
    # Execute query, limited to a reasonable number to prevent overloading the UI
    cache_entries = query.limit(100).all()
    
    # Process entries for response
    result = []
    for entry in cache_entries:
        # Convert SQLAlchemy model to dictionary
        item = {
            "id": entry.id,
            "nl_query": entry.nl_query,
            "template": entry.template,
            "template_type": entry.template_type,
            "catalog_type": entry.catalog_type,
            "catalog_subtype": entry.catalog_subtype,
            "catalog_name": entry.catalog_name,
            "status": entry.status
        }
        result.append(item)
    
    return result


@app.get("/v1/catalog/values")
async def get_catalog_values(db: Session = Depends(get_db)):
    """Get distinct catalog values for filtering"""
    try:
        # Query for distinct catalog types
        catalog_types = db.query(Text2SQLCache.catalog_type).distinct().filter(
            Text2SQLCache.catalog_type.is_not(None)
        ).all()
        catalog_types = [t[0] for t in catalog_types if t[0]]
        
        # Query for distinct catalog subtypes
        catalog_subtypes = db.query(Text2SQLCache.catalog_subtype).distinct().filter(
            Text2SQLCache.catalog_subtype.is_not(None)
        ).all()
        catalog_subtypes = [t[0] for t in catalog_subtypes if t[0]]
        
        # Query for distinct catalog names
        catalog_names = db.query(Text2SQLCache.catalog_name).distinct().filter(
            Text2SQLCache.catalog_name.is_not(None)
        ).all()
        catalog_names = [t[0] for t in catalog_names if t[0]]
        
        return {
            "catalog_types": catalog_types,
            "catalog_subtypes": catalog_subtypes,
            "catalog_names": catalog_names
        }
    except Exception as e:
        logger.error(f"Error fetching catalog values: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching catalog values: {str(e)}")


@app.post("/v1/complete")
async def complete(
    request: CompleteRequest, 
    catalog_type: Optional[str] = None, 
    catalog_subtype: Optional[str] = None, 
    catalog_name: Optional[str] = None, 
    similarity_threshold: Optional[float] = None,
    limit: Optional[int] = None, 
    use_llm: bool = False,
    db: Session = Depends(get_db)
):
    """Process a completion request, utilizing the NL cache.

    Looks up the prompt in the cache. If a match is found (above threshold),
    it returns the cached template (potentially with entity substitution).
    If no match is found, it returns a placeholder response indicating
    that external LLM processing would be needed.

    Args:
        request: The request containing the prompt.
        catalog_type: Optional catalog type to filter cache entries.
        catalog_subtype: Optional catalog subtype to filter cache entries.
        catalog_name: Optional catalog name to filter cache entries.
        similarity_threshold: Optional similarity threshold for cache matching.
        limit: Optional limit for the number of top similarity results to use.
        use_llm: If True, use LLM to enhance search results with semantic analysis.
        db: The SQLAlchemy Session dependency.

    Returns:
        JSON response containing the completion, cache status, and similarity score (if cached).

    Raises:
        HTTPException(400): If the prompt is empty.
        HTTPException(500): If an internal server error occurs during cache search or processing.
    """
    query = request.prompt

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # --- Cache Interaction ---
    controller = get_controller(db)

    # Use provided similarity threshold or default
    threshold = similarity_threshold if similarity_threshold is not None else SIMILARITY_THRESHOLD

    try:
        response_data = controller.process_completion(
            query=query,
            similarity_threshold=threshold,
            use_llm=use_llm,
            catalog_type=catalog_type,
            catalog_subtype=catalog_subtype,
            catalog_name=catalog_name,
            limit=limit
        )
        return response_data
    except Exception as e:
        logger.error(f"Error processing completion request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing completion: {str(e)}")


@app.get("/v1/cache/search")
async def search_cache(
    nl_query: str,
    template_type: Optional[str] = None,
    threshold: float = 0.8,
    limit: int = 5,
    catalog_type: Optional[str] = None,
    catalog_subtype: Optional[str] = None,
    catalog_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Search the cache for similar queries"""
    if not nl_query or not nl_query.strip():
        raise HTTPException(status_code=400, detail="nl_query parameter is required")

    controller = get_controller(db)

    try:
        results = controller.search_query(
            nl_query=nl_query,
            template_type=template_type,
            similarity_threshold=threshold,
            limit=limit,
            catalog_type=catalog_type,
            catalog_subtype=catalog_subtype,
            catalog_name=catalog_name,
        )

        logger.info(
            f"Cache search for: {nl_query[:50]}... returned {len(results)} results"
        )
        return results
    except Exception as e:
        logger.error(f"Error searching cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search cache: {str(e)}")


@app.post("/v1/cache/{entry_id}/apply")
async def apply_entity_substitution(
    entry_id: int, request: EntitySubstitutionRequest, db: Session = Depends(get_db)
):
    """Apply entity substitution to a template"""
    entity_values = request.entity_values

    if not entity_values:
        raise HTTPException(status_code=400, detail="entity_values are required")

    controller = get_controller(db)

    try:
        result = controller.apply_entity_substitution(
            template_id=entry_id, new_entity_values=entity_values
        )

        logger.info(f"Applied entity substitution to cache entry: {entry_id}")
        return result
    except Exception as e:
        logger.error(f"Error applying entity substitution: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to apply entity substitution: {str(e)}"
        )


@app.get("/v1/cache")
async def list_cache_entries(
    template_type: Optional[str] = None,
    search_query: Optional[str] = None,
    catalog_type: Optional[str] = None,
    catalog_subtype: Optional[str] = None,
    catalog_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """List cache entries with pagination and filtering"""
    # Base query
    query = db.query(Text2SQLCache)
    
    # Apply template type filter
    if template_type:
        query = query.filter(Text2SQLCache.template_type == template_type)
    
    # Apply catalog filters if specified
    if catalog_type:
        query = query.filter(Text2SQLCache.catalog_type == catalog_type)
    
    if catalog_subtype:
        query = query.filter(Text2SQLCache.catalog_subtype == catalog_subtype)
    
    if catalog_name:
        query = query.filter(Text2SQLCache.catalog_name == catalog_name)
    
    # Apply search query filter
    if search_query:
        # Search in nl_query, template and tags
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Text2SQLCache.nl_query.ilike(search_pattern),
                Text2SQLCache.template.ilike(search_pattern),
                # Note: This is a simple implementation; searching in JSON/Array fields 
                # would require a more sophisticated approach depending on the database
            )
        )
    
    # Count total for pagination
    total_count = query.count()
    total_pages = (total_count + page_size - 1) // page_size
    
    # Apply pagination
    query = query.order_by(Text2SQLCache.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    cache_entries = query.all()
    
    # Process entries for response
    items = []
    for entry in cache_entries:
        # Convert SQLAlchemy model to dictionary
        item = {
            "id": entry.id,
            "nl_query": entry.nl_query,
            "template": entry.template,
            "template_type": entry.template_type,  # template_type is already a string
            "is_template": entry.is_template,
            "entity_replacements": entry.entity_replacements,
            "tags": entry.tags,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            "is_valid": entry.status == "active",
            "catalog_type": entry.catalog_type,
            "catalog_subtype": entry.catalog_subtype,
            "catalog_name": entry.catalog_name,
            "status": entry.status,
            "usage_count": 0  # Placeholder for now, could be calculated from usage logs
        }
        items.append(item)
    
    return {
        "items": items,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@app.post("/v1/cache")
async def create_cache_entry(entry: CacheEntryCreate, db: Session = Depends(get_db)):
    """Create a new cache entry using the controller"""
    try:
        # Validate template_type
        try:
            template_type = TemplateType(entry.template_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid template type: {entry.template_type}. Valid options: {[t.value for t in TemplateType]}"
            )

        # Validate API template is valid JSON
        # if entry.template_type == TemplateType.api.value:
        #     try:
        #         json.loads(entry.template)
        #     except json.JSONDecodeError:
        #         raise HTTPException(
        #             status_code=400,
        #             detail="API template must be valid JSON"
        #         )

        # Use controller to add the query
        controller = get_controller(db)
        
        new_entry_data = controller.add_query(
            nl_query=entry.nl_query,
            template=entry.template,
            template_type=template_type,
            reasoning_trace=entry.reasoning_trace,
            is_template=entry.is_template,
            entity_replacements=entry.entity_replacements,
            tags=entry.tags,
            # database_name=entry.database_name,
            # schema_name=entry.schema_name,
            catalog_type=entry.catalog_type if hasattr(entry, 'catalog_type') else None,
            catalog_subtype=entry.catalog_subtype if hasattr(entry, 'catalog_subtype') else None,
            catalog_name=entry.catalog_name if hasattr(entry, 'catalog_name') else None,
        )

        # Return the created entry - new_entry_data is already a dictionary
        return new_entry_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cache entry via controller: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating cache entry: {str(e)}")


@app.get("/v1/cache/{entry_id}")
async def get_cache_entry(entry_id: int, db: Session = Depends(get_db)):
    """Get a specific cache entry by ID"""
    entry = db.query(Text2SQLCache).filter(Text2SQLCache.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Cache entry with ID {entry_id} not found")
    
    return {
        "id": entry.id,
        "nl_query": entry.nl_query,
        "template": entry.template,
        "template_type": entry.template_type,  # template_type is already a string
        "is_template": entry.is_template,
        "entity_replacements": entry.entity_replacements,
        "tags": entry.tags,
        "reasoning_trace": entry.reasoning_trace,
        # "database_name": entry.database_name,
        # "schema_name": entry.schema_name,
        "catalog_type": entry.catalog_type,
        "catalog_subtype": entry.catalog_subtype, 
        "catalog_name": entry.catalog_name,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        "is_valid": entry.status == "active",
        "status": entry.status
    }


@app.put("/v1/cache/{entry_id}")
async def update_cache_entry(entry_id: int, request: Request, db: Session = Depends(get_db)):
    """Update an existing cache entry using the controller"""
    try:
        data = await request.json()

        # Use controller to update the query
        controller = get_controller(db)
        updated_entry = controller.update_query(query_id=entry_id, updates=data)

        if not updated_entry:
             raise HTTPException(status_code=404, detail=f"Cache entry with ID {entry_id} not found")

        # Return the updated entry directly since it's already a dictionary
        return updated_entry

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cache entry {entry_id} via controller: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating cache entry: {str(e)}")


@app.delete("/v1/cache/{entry_id}")
async def delete_cache_entry_api(entry_id: int, db: Session = Depends(get_db)):
    """Delete a cache entry using the controller"""
    try:
        # Use controller to delete the query
        controller = get_controller(db)
        deleted = controller.delete_query(query_id=entry_id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Cache entry with ID {entry_id} not found or could not be deleted")

        return {"message": f"Cache entry with ID {entry_id} has been deleted"}

    except HTTPException: # Re-raise specific exceptions if controller raises them
        raise
    except Exception as e:
        logger.error(f"Error deleting cache entry {entry_id} via controller: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting cache entry: {str(e)}")


@app.post("/v1/cache/{entry_id}/test")
async def test_cache_entry(entry_id: int, db: Session = Depends(get_db)):
    """Test a cache entry for validity"""
    entry = db.query(Text2SQLCache).filter(Text2SQLCache.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Cache entry with ID {entry_id} not found")
    
    try:
        # Perform validation based on template_type
        is_valid = True
        validation_message = "Cache entry is valid"
        
        if entry.template_type == TemplateType.sql:
            # Very basic SQL syntax validation
            template = entry.template.strip().lower()
            if not (template.startswith("select") or template.startswith("with")):
                is_valid = False
                validation_message = "SQL template must start with SELECT or WITH"
        
        elif entry.template_type == TemplateType.url:
            # Basic URL validation
            template = entry.template.strip()
            if not (template.startswith("http://") or template.startswith("https://")):
                is_valid = False
                validation_message = "URL template must start with http:// or https://"
        
        elif entry.template_type == TemplateType.api:
            # Basic JSON validation
            try:
                json.loads(entry.template)
            except json.JSONDecodeError:
                is_valid = False
                validation_message = "API template must be valid JSON"
        
        elif entry.template_type == TemplateType.reasoning_steps:
            # Basic validation for reasoning steps - should have content
            if not entry.template.strip():
                is_valid = False
                validation_message = "Reasoning Steps template cannot be empty"
        
        # Update validity in database
        entry.status = "active" if is_valid else "inactive"
        entry.updated_at = datetime.datetime.now()
        db.commit()
        
        return {
            "is_valid": is_valid,
            "message": validation_message
        }
    except Exception as e:
        logger.error(f"Error testing cache entry: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing cache entry: {str(e)}")


@app.get("/v1/test")
async def test_endpoint():
    """Simple test endpoint to check API accessibility"""
    logger.info("Received request for /v1/test")
    return {"status": "ok", "message": "Test endpoint reached"}


@app.get("/v1/usage_logs")
async def list_usage_logs(
    page: int = 1, 
    page_size: int = 10, 
    order_by: str = "timestamp", 
    order_desc: bool = True, 
    db: Session = Depends(get_db)
):
    """List usage log entries with sorting options"""
    logger.info(f"Received request for /v1/usage_logs with order_by={order_by}, order_desc={order_desc}")
    try:
        # Build the base query
        query = db.query(UsageLog)
        
        # Apply sorting
        if order_by == "timestamp":
            if order_desc:
                query = query.order_by(UsageLog.timestamp.desc())
            else:
                query = query.order_by(UsageLog.timestamp.asc())
        elif order_by == "id":
            if order_desc:
                query = query.order_by(UsageLog.id.desc())
            else:
                query = query.order_by(UsageLog.id.asc())
                
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        logs = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "items": [{
                "id": log.id,
                "cache_entry_id": log.cache_entry_id,
                "timestamp": log.timestamp,
                "prompt": log.prompt,
                "success_status": log.success_status,
                "similarity_score": log.similarity_score,
                "error_message": log.error_message,
                "catalog_type": log.catalog_type,
                "catalog_subtype": log.catalog_subtype,
                "catalog_name": log.catalog_name,
                "llm_used": getattr(log, "llm_used", False)
            } for log in logs]
        }
    except Exception as e:
        logger.error(f"Error fetching usage logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching usage logs: {str(e)}")


@app.post("/v1/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    template_type: str = "sql",
    catalog_type: Optional[str] = None,
    catalog_subtype: Optional[str] = None,
    catalog_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Upload and process a CSV file to create cache entries.
    
    The CSV should have at least 'nl_query' (or 'text_query') and 'template' (or 'sql_command') columns.
    Any additional columns present in the CSV will be processed if they match valid cache entry fields.
    
    Optional parameters:
    - template_type: Default template type to use if not specified in CSV (default: 'sql')
    - catalog_type: Default catalog type to assign if not in CSV
    - catalog_subtype: Default catalog subtype to assign if not in CSV
    - catalog_name: Default catalog name to assign if not in CSV
    
    Supported columns include:
    - nl_query, text_query: Natural language query
    - template, sql_command, sql_query: Template content
    - template_type, type: Type of template (sql, url, api, etc.)
    - reasoning_trace, reason, explanation: Explanation of the template
    - tags: Comma-separated list of tags
    - is_template: Boolean flag for template entries
    - catalog_type, catalog_subtype, catalog_name: Catalog identifiers
    - entity_replacements: JSON string of entity replacements
    - status: Entry status (active, pending, archive)
    """
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Read the CSV file content
        contents = await file.read()
        csv_text = contents.decode('utf-8')
        csv_io = io.StringIO(csv_text)
        reader = csv.DictReader(csv_io)
        
        # Column name mappings
        field_mappings = {
            'text_query': 'nl_query',
            'sql_command': 'template',
            'sql_query': 'template',
            'query': 'nl_query',
            'command': 'template',
            'reason': 'reasoning_trace',
            'explanation': 'reasoning_trace',
            'type': 'template_type',
        }
        
        # Boolean fields
        boolean_fields = ['is_template']
        
        # Check if required columns exist by checking headers
        header = reader.fieldnames
        logger.info(f"CSV headers: {header}")
        
        if not header:
            raise HTTPException(status_code=400, detail="CSV file has no headers")
        
        # Map header names using field_mappings
        mapped_headers = []
        for h in header:
            mapped_h = field_mappings.get(h.lower(), h.lower())
            mapped_headers.append(mapped_h)
        
        # Check for required fields after mapping
        has_query = any(h in mapped_headers for h in ['nl_query'])
        has_template = any(h in mapped_headers for h in ['template'])
        
        if not (has_query and has_template) and not all(h in header for h in ['nl_query', 'template']):
            # Try original field names as fallback
            has_query = any(h in header for h in ['text_query', 'nl_query', 'query'])
            has_template = any(h in header for h in ['sql_command', 'template', 'sql_query', 'command'])
            
            if not (has_query and has_template):
                raise HTTPException(
                    status_code=400,
                    detail="CSV must contain at least one query column (nl_query, text_query) "
                           "and one template column (template, sql_command)"
                )
        
        # Process each row
        controller = get_controller(db)
        processed_count = 0
        failed_count = 0
        results = []
        
        # Reset reader to first row
        csv_io.seek(0)
        reader = csv.DictReader(csv_io)
        
        for row in reader:
            try:
                entry_data = {}
                
                # Process each field from the row
                for key, value in row.items():
                    # Skip empty values
                    if not value or str(value).strip() == '':
                        continue
                    
                    # Get the mapped field name
                    field_name = field_mappings.get(key.lower(), key.lower())
                    
                    # Handle boolean fields
                    if field_name in boolean_fields:
                        entry_data[field_name] = str(value).lower() in ['true', 'yes', 'y', '1']
                    
                    # Handle tags as a list if it's comma-separated
                    elif field_name == 'tags' and isinstance(value, str):
                        entry_data[field_name] = [tag.strip() for tag in value.split(',') if tag.strip()]
                    
                    # Try to parse entity_replacements as JSON if provided
                    elif field_name == 'entity_replacements' and isinstance(value, str):
                        try:
                            entry_data[field_name] = json.loads(value)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in entity_replacements: {value}")
                            # Skip this field if JSON is invalid
                    
                    # Use the value as-is
                    else:
                        entry_data[field_name] = value
                
                # Ensure we have the required fields
                if 'nl_query' not in entry_data:
                    for field in ['text_query', 'query']:
                        if field in row and row[field].strip():
                            entry_data['nl_query'] = row[field].strip()
                            break
                    if 'nl_query' not in entry_data:
                        raise ValueError("No natural language query found in row")
                
                if 'template' not in entry_data:
                    for field in ['sql_command', 'sql_query', 'command']:
                        if field in row and row[field].strip():
                            entry_data['template'] = row[field].strip()
                            break
                    if 'template' not in entry_data:
                        raise ValueError("No template found in row")
                
                # Use template type from CSV or fall back to endpoint param
                template_type_value = entry_data.get('template_type', template_type).lower()
                
                try:
                    template_type_enum = TemplateType(template_type_value)
                except ValueError:
                    logger.warning(f"Invalid template type '{template_type_value}', defaulting to 'sql'")
                    template_type_enum = TemplateType.sql
                
                # Use catalog values from CSV if present, otherwise use function parameters as defaults
                entry_catalog_type = entry_data.get('catalog_type') or catalog_type
                entry_catalog_subtype = entry_data.get('catalog_subtype') or catalog_subtype
                entry_catalog_name = entry_data.get('catalog_name') or catalog_name
                
                # Extract fields for add_query method
                new_entry = controller.add_query(
                    nl_query=entry_data.get('nl_query'),
                    template=entry_data.get('template'),
                    template_type=template_type_enum,
                    reasoning_trace=entry_data.get('reasoning_trace'),
                    is_template=entry_data.get('is_template', False),
                    entity_replacements=entry_data.get('entity_replacements'),
                    tags=entry_data.get('tags'),
                    catalog_type=entry_catalog_type,
                    catalog_subtype=entry_catalog_subtype,
                    catalog_name=entry_catalog_name,
                    status=entry_data.get('status', 'active'),
                )
                
                results.append({
                    "id": new_entry.get("id"),
                    "nl_query": entry_data.get('nl_query'),
                    "status": "success"
                })
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
                results.append({
                    "nl_query": row.get('nl_query', row.get('text_query', 'unknown')),
                    "status": "error",
                    "error": str(e)
                })
                failed_count += 1
        
        return {
            "status": "completed",
            "processed": processed_count,
            "failed": failed_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing CSV file: {str(e)}")


@app.post("/v1/upload/swagger")
async def upload_swagger(
    swagger_url: str = Body(..., embed=True),
    template_type: str = "api",
    catalog_type: Optional[str] = Body(None, embed=True),
    catalog_subtype: Optional[str] = Body(None, embed=True),
    catalog_name: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    Process a Swagger URL to generate natural language queries and API templates using an LLM.
    Only GET, PUT, and POST operations are processed.
    
    Optional parameters:
    - catalog_type: Catalog type to assign to all entries (default: 'api')
    - catalog_subtype: Catalog subtype to assign to all entries (default: method name)
    - catalog_name: Catalog name to assign to all entries (default: operationId)
    """
    logger.info(f"Received Swagger upload request for URL: {swagger_url}")
    try:
        # Fetch Swagger JSON
        logger.info(f"Attempting to fetch Swagger JSON from: {swagger_url} with 10-second timeout")
        response = requests.get(swagger_url, timeout=10)  # Add a 10-second timeout
        if response.status_code != 200:
            logger.error(f"Failed to fetch Swagger JSON. Status code: {response.status_code}")
            raise HTTPException(status_code=400, detail=f"Failed to fetch Swagger JSON from {swagger_url}")
        
        logger.info(f"Successfully fetched Swagger JSON. Content length: {len(response.text)}")
        
        try:
            swagger_data = response.json()
            logger.info(f"Successfully parsed Swagger JSON")
        except Exception as e:
            logger.error(f"Failed to parse Swagger JSON: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON in Swagger response: {str(e)}")
        
        controller = get_controller(db)
        processed_count = 0
        failed_count = 0
        results = []
        
        # Process paths for GET, PUT, POST operations
        paths_count = len(swagger_data.get('paths', {}))
        logger.info(f"Processing {paths_count} paths from Swagger definition")
        
        for path, methods in swagger_data.get('paths', {}).items():
            for method, details in methods.items():
                if method.lower() not in ['get', 'put', 'post']:
                    continue
                
                logger.debug(f"Processing {method.upper()} {path}")
                try:
                    # Generate natural language query and reasoning trace using LLM
                    operation_id = details.get('operationId', f"{method.upper()} {path}")
                    summary = details.get('summary', '')
                    nl_query = f"{method.upper()} operation for {operation_id}"
                    if summary:
                        nl_query += f": {summary}"
                    
                    # Create API template
                    template = {
                        'method': method.upper(),
                        'path': path,
                        'parameters': details.get('parameters', []),
                        'responses': details.get('responses', {})
                    }
                    template_str = json.dumps(template, indent=2)
                    
                    # Generate reasoning trace (simplified, ideally LLM-generated)
                    reasoning_trace = f"This template was generated from Swagger for {method.upper()} operation on {path}."
                    
                    # Add to cache
                    logger.info(f"Attempting to add to cache: {method.upper()} {path} with template_type={TemplateType.API}")
                    try:
                        # Use user-specified catalog values if provided, otherwise use defaults
                        entry_catalog_type = catalog_type or 'api'
                        entry_catalog_subtype = catalog_subtype or method.lower()
                        entry_catalog_name = catalog_name or operation_id
                        
                        new_entry = controller.add_query(
                            nl_query=nl_query,
                            template=template_str,
                            template_type=TemplateType.API,
                            reasoning_trace=reasoning_trace,
                            is_template=False,
                            catalog_type=entry_catalog_type,
                            catalog_subtype=entry_catalog_subtype,
                            catalog_name=entry_catalog_name
                        )
                        
                        logger.info(f"Successfully added to cache: {method.upper()} {path} with ID {new_entry.get('id', 'unknown')}")
                        
                        results.append({
                            "id": new_entry.get("id"),
                            "nl_query": nl_query,
                            "status": "success"
                        })
                        processed_count += 1
                    except Exception as add_error:
                        logger.error(f"Error adding query to cache: {str(add_error)}", exc_info=True)
                        results.append({
                            "nl_query": f"{method.upper()} {path}",
                            "status": "error",
                            "error": f"Cache error: {str(add_error)}"
                        })
                        failed_count += 1
                        continue
                        
                    logger.debug(f"Successfully processed {method.upper()} {path}")
                except Exception as e:
                    logger.error(f"Error processing {method} {path}: {str(e)}")
                    results.append({
                        "nl_query": f"{method.upper()} {path}",
                        "status": "error",
                        "error": str(e)
                    })
                    failed_count += 1
        
        logger.info(f"Swagger processing complete. Processed: {processed_count}, Failed: {failed_count}")
        return {
            "status": "completed",
            "processed": processed_count,
            "failed": failed_count,
            "results": results
        }
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching Swagger JSON from {swagger_url}")
        raise HTTPException(status_code=504, detail=f"Timeout while fetching Swagger JSON from {swagger_url}")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error while fetching Swagger JSON from {swagger_url}")
        raise HTTPException(status_code=502, detail=f"Connection error while fetching Swagger JSON from {swagger_url}")
    except Exception as e:
        logger.error(f"Error processing Swagger URL: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing Swagger URL: {str(e)}")


@app.post("/v1/generate/reasoning_trace")
async def generate_reasoning_trace(
    request: Request,
    db: Session = Depends(get_db)
):
    """Generate a reasoning trace for a cache entry using LLM.
    
    Takes natural language query and template and returns a reasoning trace that
    explains how the template addresses the query.
    """
    try:
        data = await request.json()
        nl_query = data.get('nl_query')
        template = data.get('template')
        template_type = data.get('template_type', 'sql')
        
        if not nl_query or not template:
            raise HTTPException(status_code=400, detail="nl_query and template are required")
        
        # Check if LLM service is available
        if not LLMService or not LLMService.is_configured():
            raise HTTPException(
                status_code=400, 
                detail="LLM service is not configured. Set OPENROUTER_API_KEY in .env file."
            )
        
        # Create LLM service instance
        llm_service = LLMService(model=os.environ.get("OPENROUTER_MODEL", "google/gemini-pro"))
        
        # Prepare prompt for reasoning trace generation
        prompt = f"""You are an expert in explaining how database queries, APIs, or other templates address natural language questions.

Natural Language Query: "{nl_query}"

Template ({template_type}): 
{template}

Provide a clear, concise explanation of how this template addresses the natural language query. 
Explain the logic, approach, and any transformations or calculations involved.
Focus on helping a non-technical user understand the relationship between their question and the provided solution.

Your explanation should be:
1. Clear and concise (2-4 paragraphs)
2. Technically accurate
3. Focused on how the template addresses the specific query
"""
        
        # Make the API call using the OpenAI client
        response = llm_service.client.chat.completions.create(
            model=llm_service.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that explains technical solutions clearly."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        # Extract content from the response
        reasoning_trace = response.choices[0].message.content
        
        return {"reasoning_trace": reasoning_trace}
    
    except Exception as e:
        logger.error(f"Error generating reasoning trace: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating reasoning trace: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    # Ensure reload is False for production or when using multiple workers
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
