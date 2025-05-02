from fastapi import FastAPI, Depends, HTTPException, Request, Body
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

# Import database configuration
from .database import get_db, engine, SessionLocal

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the NL cache framework
try:
    from nl_cache_framework import (
        Text2SQLController,
        TemplateType,
        Base,
        Text2SQLEntitySubstitution,
    )
    from nl_cache_framework.models import Text2SQLCache, UsageLog
except ImportError as e:
    print(f"Error importing nl_cache_framework: {e}")
    print("Make sure the framework is installed with: pip install -e .")
    print(f"Current sys.path: {sys.path}")
    raise

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_server")

# Create database tables
Base.metadata.create_all(bind=engine)

# Load configuration
DEFAULT_MODEL_NAME = os.environ.get(
    "DEFAULT_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2"
)
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.85"))

# Pydantic models for request/response schema
class CacheEntryCreate(BaseModel):
    nl_query: str = Field(..., description="The natural language query")
    template: str = Field(..., description="The template (SQL, URL, API spec, etc.)")
    template_type: str = Field(default="sql", description="Type of template (sql, url, api, workflow)")
    reasoning_trace: Optional[str] = Field(None, description="Optional explanation of the template")
    is_template: bool = Field(default=False, description="Flag indicating if this entry contains placeholders")
    entity_replacements: Optional[Dict[str, Any]] = Field(None, description="JSON defining placeholder substitutions")
    tags: Optional[List[str]] = Field(None, description="List of tags for categorization")
    database_name: Optional[str] = Field(None, description="Target database identifier")
    schema_name: Optional[str] = Field(None, description="Target schema identifier")
    catalog_id: Optional[int] = Field(None, description="Catalog identifier")

class CompleteRequest(BaseModel):
    prompt: str = Field(..., description="The natural language prompt to complete")

class EntitySubstitutionRequest(BaseModel):
    entity_values: Dict[str, Any] = Field(..., description="Entity values for substitution")

# Initialize FastAPI application
app = FastAPI(
    title="NL Cache MCP Server",
    description="Model Context Protocol server for NL cache framework",
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
        "service": "nl-cache-mcp",
        "dependencies": {
            "database": db_status,
        },
    }


@app.post("/v1/complete")
async def complete(request: CompleteRequest, db: Session = Depends(get_db)):
    """Process a completion request, utilizing the NL cache.

    Looks up the prompt in the cache. If a match is found (above threshold),
    it returns the cached template (potentially with entity substitution).
    If no match is found, it returns a placeholder response indicating
    that external LLM processing would be needed.

    Args:
        request: The request containing the prompt.
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
    controller = Text2SQLController(
        db_session=db, similarity_model_name=DEFAULT_MODEL_NAME
    )
    entity_sub = Text2SQLEntitySubstitution()

    response_data = {}
    final_result = ""
    cache_hit = False
    similarity_score = 0.0

    # Check cache
    try:
        cache_results = controller.search_query(
            nl_query=query, similarity_threshold=SIMILARITY_THRESHOLD, limit=1
        )
    except Exception as e:
        # Log controller search error specifically
        logger.error(f"Cache search failed for query '{query[:50]}...': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error searching cache")

    # Process results if we have any
    if cache_results and len(cache_results) > 0:
        # We have a match
        best_match = cache_results[0]
        cache_hit = True
        similarity_score = best_match.get("similarity", 0.0)
        logger.info(
            f"Cache hit for query: {query[:50]}... (score: {similarity_score:.4f})"
        )

        # Get the template
        template_id = best_match.get("id")
        template = best_match.get("template", "")
        is_template = best_match.get("is_template", False)

        # For templates with entity substitutions
        if is_template:
            # Entity substitution
            try:
                # Extract entities from the query
                extracted_entities = entity_sub.extract_entities(
                    query, best_match.get("entity_replacements", {})
                )

                # Apply substitution
                substitution_result = controller.apply_entity_substitution(
                    template_id=template_id,
                    new_entity_values=extracted_entities,
                )

                final_result = substitution_result.get("substituted_template", template)
                logger.debug(f"Applied entity substitution. Result: {final_result[:50]}...")

            except Exception as e:
                logger.error(f"Entity substitution failed: {e}", exc_info=True)
                # Fall back to the raw template
                final_result = template
                logger.warning(f"Falling back to raw template: {template[:50]}...")
        else:
            # Regular template, no substitution needed
            final_result = template

        # Record the usage in UsageLog
        try:
            usage_log = UsageLog(cache_entry_id=template_id)
            db.add(usage_log)
            # Without explicit commit, this will be committed in the outer function
        except Exception as e:
            logger.warning(f"Failed to log cache usage: {e}")

        # Prepare response for cache hit
        response_data = {
            "completion": final_result,
            "status": "cache_hit",
            "similarity_score": similarity_score,
        }

    else:
        # Cache miss
        logger.info(f"Cache miss for query: {query[:50]}...")
        final_result = "This query requires LLM processing. No cached result was found."
        response_data = {
            "completion": final_result,
            "status": "cache_miss",
        }

    # Commit happens implicitly if controller.add/update/delete is called with commit=True
    # or explicitly if needed after db.add(usage_log)
    # Let's add an explicit commit here for the usage log
    try:
        db.commit()
    except Exception as commit_error:
        db.rollback() # Rollback on commit error
        logger.error(f"Database commit error after processing completion: {commit_error}")
        # Depending on policy, might want to raise an error here

    return response_data


@app.get("/v1/cache/search")
async def search_cache(
    nl_query: str,
    template_type: Optional[str] = None,
    threshold: float = 0.8,
    limit: int = 5,
    catalog_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Search the cache for similar queries"""
    if not nl_query or not nl_query.strip():
        raise HTTPException(status_code=400, detail="nl_query parameter is required")

    controller = Text2SQLController(db_session=db)

    try:
        results = controller.search_query(
            nl_query=nl_query,
            template_type=template_type,
            similarity_threshold=threshold,
            limit=limit,
            catalog_id=catalog_id,
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

    controller = Text2SQLController(db_session=db)

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
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    """List cache entries with pagination and filtering"""
    # Base query
    query = db.query(Text2SQLCache)
    
    # Apply filters
    if template_type:
        query = query.filter(Text2SQLCache.template_type == template_type)
    
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
            "is_valid": entry.is_valid
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

        # Use controller to add the query
        controller = Text2SQLController(db_session=db)
        new_entry_data = controller.add_query(
            nl_query=entry.nl_query,
            template=entry.template,
            template_type=template_type,
            reasoning_trace=entry.reasoning_trace,
            is_template=entry.is_template,
            entity_replacements=entry.entity_replacements,
            tags=entry.tags,
            database_name=entry.database_name,
            schema_name=entry.schema_name,
            catalog_id=entry.catalog_id,
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
        "database_name": entry.database_name,
        "schema_name": entry.schema_name,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        "is_valid": entry.is_valid
    }


@app.put("/v1/cache/{entry_id}")
async def update_cache_entry(entry_id: int, request: Request, db: Session = Depends(get_db)):
    """Update an existing cache entry using the controller"""
    try:
        data = await request.json()

        # Use controller to update the query
        controller = Text2SQLController(db_session=db)
        updated_entry = controller.update_query(entry_id=entry_id, updates=data, commit=True)

        if not updated_entry:
             raise HTTPException(status_code=404, detail=f"Cache entry with ID {entry_id} not found")

        # Assuming controller.update_query returns the updated model instance:
        return {
            "id": updated_entry.id,
            "nl_query": updated_entry.nl_query,
            "template": updated_entry.template,
            "template_type": updated_entry.template_type.value if updated_entry.template_type else None,
            "is_template": updated_entry.is_template,
            "entity_replacements": updated_entry.entity_replacements,
            "tags": updated_entry.tags,
            "created_at": updated_entry.created_at.isoformat() if updated_entry.created_at else None,
            "updated_at": updated_entry.updated_at.isoformat() if updated_entry.updated_at else None,
            "is_valid": updated_entry.is_valid
        }

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
        controller = Text2SQLController(db_session=db)
        deleted = controller.delete_query(entry_id=entry_id, commit=True)

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
        
        # Update validity in database
        entry.is_valid = is_valid
        entry.updated_at = datetime.datetime.now()
        db.commit()
        
        return {
            "is_valid": is_valid,
            "message": validation_message
        }
    except Exception as e:
        logger.error(f"Error testing cache entry: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing cache entry: {str(e)}")


@app.get("/v1/cache/stats")
async def get_cache_stats(
    template_type: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """Get cache statistics"""
    base_query = db.query(Text2SQLCache)
    
    if template_type:
        base_query = base_query.filter(Text2SQLCache.template_type == template_type)
    
    total_count = base_query.count()
    valid_count = base_query.filter(Text2SQLCache.is_valid == True).count()
    template_count = base_query.filter(Text2SQLCache.is_template == True).count()
    
    # Get counts by template type
    type_counts = {}
    for t_type in TemplateType:
        count = base_query.filter(Text2SQLCache.template_type == t_type).count()
        type_counts[t_type.value] = count
    
    return {
        "total_entries": total_count,
        "valid_entries": valid_count,
        "template_entries": template_count,
        "by_template_type": type_counts
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    # Ensure reload is False for production or when using multiple workers
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
