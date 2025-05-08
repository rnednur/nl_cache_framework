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

# Import database configuration
from database import get_db, engine, SessionLocal

# Import LLM service for enhanced completions
from llm_service import LLMService

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

# Create a singleton instance of Text2SQLController to be reused across requests
controller_instance = None
db_for_controller = None
similarity_util = None

def get_controller(db_session):
    """Get a shared instance of Text2SQLController"""
    global controller_instance, db_for_controller, similarity_util
    if similarity_util is None:
        logger.info("Initializing shared similarity utility")
        from nl_cache_framework import Text2SQLSimilarity
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
    tags: Optional[List[str]] = Field(None, description="List of tags for categorization")
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


@app.get("/v1/cache/stats")
async def get_cache_stats(db: Session = Depends(get_db)):
    """Get statistics about the cache entries.

    Returns:
        JSON response with counts of total entries and breakdown by template type.

    Raises:
        HTTPException(500): If an error occurs while fetching stats.
    """
    try:
        controller = get_controller(db)
        total_count = controller.get_cache_count()
        valid_count = controller.get_valid_cache_count()
        template_count = controller.get_template_count()
        type_counts = controller.get_template_type_counts()
        return {
            "total_entries": total_count,
            "valid_entries": valid_count,
            "template_entries": template_count,
            "by_template_type": type_counts
        }
    except Exception as e:
        logger.error(f"Error in /v1/cache/stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing stats: {str(e)}")


@app.get("/v1/cache/catalogs")
async def get_catalog_values(db: Session = Depends(get_db)):
    """Get distinct catalog types, subtypes, and names from the cache entries.

    Returns:
        JSON response with lists of distinct catalog_type, catalog_subtype, and catalog_name values.

    Raises:
        HTTPException(500): If an error occurs while fetching catalog values.
    """
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


@app.post("/v1/complete")
async def complete(
    request: CompleteRequest, 
    catalog_type: Optional[str] = None, 
    catalog_subtype: Optional[str] = None, 
    catalog_name: Optional[str] = None, 
    similarity_threshold: Optional[float] = None, 
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
    entity_sub = Text2SQLEntitySubstitution()

    response_data = {}
    final_result = ""
    cache_hit = False
    similarity_score = 0.0
    explanation = None

    # Use provided similarity threshold or default
    threshold = similarity_threshold if similarity_threshold is not None else SIMILARITY_THRESHOLD

    # Check cache
    try:
        # Get multiple results to allow LLM to choose from them if use_llm is enabled
        limit = 5 if use_llm else 1  
        cache_results = controller.search_query(
            nl_query=query, 
            similarity_threshold=threshold, 
            limit=limit,
            catalog_type=catalog_type,
            catalog_subtype=catalog_subtype,
            catalog_name=catalog_name
        )
    except Exception as e:
        # Log controller search error specifically
        logger.error(f"Cache search failed for query '{query[:50]}...': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error searching cache")

    # Process results
    if not cache_results or len(cache_results) == 0:
        # No matches found
        logger.info(f"No cache matches for query: {query[:50]}...")
        response_data = {
            "cache_template": "No cached template found for this query.",
            "cache_hit": False,
            "similarity_score": 0.0,
            "template_id": None,
            "cached_query": None,
            "user_query": query,
            "updated_template": None,
            "llm_explanation": "No similar query found in cache.",
        }
    else:
        # LLM-based enhancement if requested and we have multiple results
        updated_query = None
        if use_llm and len(cache_results) > 0:
            # Check if LLM service is configured
            if not LLMService.is_configured():
                logger.warning("LLM enhancement requested but service not configured")
                response_data = {
                    "warning": "LLM enhancement was requested but the service is not configured. Set OPENROUTER_API_KEY in .env file.",
                }
                # Continue with standard processing without LLM
                best_match = cache_results[0]
                similarity_score = best_match.get("similarity", 0.0)
            else:
                try:
                    logger.info(f"Using LLM enhancement for query: {query[:50]}...")
                    # Initialize LLM service with the correct model from environment variable
                    llm_service = LLMService(model=os.getenv("OPENROUTER_MODEL", "google/gemini-pro"))
                    llm_result = llm_service.can_answer_with_context(
                        query=query,
                        context_entries=cache_results,
                        similarity_threshold=threshold
                    )
                    
                    can_answer = llm_result.get("can_answer", False)
                    explanation = llm_result.get("explanation", "")
                    selected_entry_id = llm_result.get("selected_entry_id")
                    updated_query = llm_result.get("updated_query")
                    
                    if can_answer and selected_entry_id:
                        # Find the selected entry
                        selected_entry = next(
                            (entry for entry in cache_results if entry.get("id") == selected_entry_id), 
                            None
                        )
                        if selected_entry:
                            # Use the selected entry as our best match
                            best_match = selected_entry
                            similarity_score = selected_entry.get("similarity", 0.0)
                            logger.info(
                                f"LLM selected cache entry: {selected_entry_id} for query: {query[:50]}..."
                            )
                        else:
                            # Fall back to first result if entry not found
                            best_match = cache_results[0]
                            similarity_score = best_match.get("similarity", 0.0)
                    else:
                        # LLM determined we can't answer or failed - use first result
                        best_match = cache_results[0]
                        similarity_score = best_match.get("similarity", 0.0)
                except Exception as e:
                    logger.error(f"LLM processing failed: {e}", exc_info=True)
                    # Fall back to best match without LLM
                    best_match = cache_results[0]
                    similarity_score = best_match.get("similarity", 0.0)
        else:
            # Without LLM, just use the top result
            best_match = cache_results[0]
            similarity_score = best_match.get("similarity", 0.0)
        
        # We have a match - either from LLM selection or top result
        cache_hit = True
        logger.info(
            f"Cache hit for query: {query[:50]}... (score: {similarity_score:.4f})"
        )

        # If we have an updated query from LLM, log it
        if updated_query:
            logger.info(f"Updated query from LLM: {updated_query}")

        # Get the template
        template_id = best_match.get("id")
        template = best_match.get("template", "")
        is_template = best_match.get("is_template", False)

        # For templates with entity substitutions
        if is_template:
            # Entity substitution
            try:
                # Extract entities from the query
                # If LLM provided an updated query, use it for entity extraction
                extraction_query = updated_query if updated_query else query
                extracted_entities = entity_sub.extract_entities(
                    extraction_query, best_match.get("entity_replacements", {})
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

    # Prepare final response
    if cache_hit:
        response_data = {
            "cache_template": final_result,
            "cache_hit": True,
            "similarity_score": similarity_score,
            "template_id": template_id,
            "cached_query": best_match.get("nl_query", ""),
            "user_query": query,
            "updated_template": updated_query if updated_query else final_result,
            "llm_explanation": explanation if explanation else "Retrieved from cache based on similarity.",
        }
    else:
        response_data = {
            "cache_template": "No cached template found for this query.",
            "cache_hit": False,
            "similarity_score": 0.0,
            "template_id": None,
            "cached_query": None,
            "user_query": query,
            "updated_template": None,
            "llm_explanation": "No similar query found in cache.",
        }

    # Record the usage in UsageLog with detailed information for both hits and misses
    try:
        from datetime import datetime
        template_id = None
        if cache_hit and 'best_match' in locals():
            template_id = best_match.get("id")
        
        usage_log = UsageLog(
            cache_entry_id=template_id,
            prompt=query,
            timestamp=datetime.utcnow(),
            success_status=cache_hit,
            similarity_score=similarity_score if cache_hit else 0.0,
            error_message=None,
            catalog_type=catalog_type,
            catalog_subtype=catalog_subtype,
            catalog_name=catalog_name,
            llm_used=use_llm
        )
        db.add(usage_log)
        # Commit to ensure the log is saved
        db.commit()
    except Exception as log_error:
        logger.warning(f"Failed to log cache usage with details: {log_error}")
        try:
            db.rollback()  # Rollback on logging error to keep the database consistent
        except:
            pass  # Swallow potential rollback errors

    return response_data


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
            "is_valid": entry.status == "active"
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
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        "is_valid": entry.status == "active"
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
async def list_usage_logs(page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    """List usage log entries"""
    logger.info("Received request for /v1/usage_logs")
    try:
        total_count = db.query(UsageLog).count()
        logs = db.query(UsageLog).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "logs": [{
                "id": log.id,
                "cache_entry_id": log.cache_entry_id,
                "timestamp": log.timestamp,
                "prompt": log.prompt,
                "success_status": log.success_status,
                "similarity_score": log.similarity_score,
                "error_message": log.error_message,
                "catalog_type": log.catalog_type,
                "catalog_subtype": log.catalog_subtype,
                "catalog_name": log.catalog_name
            } for log in logs]
        }
    except Exception as e:
        logger.error(f"Error fetching usage logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching usage logs: {str(e)}")


@app.post("/v1/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    template_type: str = "sql",
    db: Session = Depends(get_db)
):
    """
    Upload and process a CSV file to create cache entries.
    
    The CSV should have at least 'nl_query' and 'template' columns.
    Additional columns can include 'tags', 'catalog_type', etc.
    """
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Read the CSV file content
        contents = await file.read()
        csv_text = contents.decode('utf-8')
        csv_io = io.StringIO(csv_text)
        reader = csv.DictReader(csv_io)
        
        # Validate CSV structure
        required_fields = ['nl_query', 'template']
        first_row = next(reader, None)
        csv_io.seek(0)  # Reset to start for full processing
        reader = csv.DictReader(csv_io)  # Re-initialize reader
        
        if not first_row or not all(field in first_row for field in required_fields):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain at least these columns: {', '.join(required_fields)}"
            )
        
        # Process each row
        controller = get_controller(db)
        processed_count = 0
        failed_count = 0
        results = []
        
        for row in reader:
            try:
                # Skip empty rows
                if not row['nl_query'].strip() or not row['template'].strip():
                    continue
                
                # Extract fields with defaults
                nl_query = row['nl_query'].strip()
                template = row['template'].strip()
                is_template = row.get('is_template', 'false').lower() == 'true'
                
                # Handle optional fields
                tags = row.get('tags', '').split(',') if row.get('tags') else None
                tags = [tag.strip() for tag in tags] if tags else None
                
                reasoning_trace = row.get('reasoning_trace', None)
                entity_replacements = None  # Would need to parse JSON if provided
                
                catalog_type = row.get('catalog_type', None)
                catalog_subtype = row.get('catalog_subtype', None)
                catalog_name = row.get('catalog_name', None)
                
                # Add to cache with embeddings
                try:
                    template_type_enum = TemplateType(template_type.lower())
                except ValueError:
                    template_type_enum = TemplateType.sql
                
                new_entry = controller.add_query(
                    nl_query=nl_query,
                    template=template,
                    template_type=template_type_enum,
                    reasoning_trace=reasoning_trace,
                    is_template=is_template,
                    entity_replacements=entity_replacements,
                    tags=tags,
                    catalog_type=catalog_type,
                    catalog_subtype=catalog_subtype,
                    catalog_name=catalog_name,
                )
                
                results.append({
                    "id": new_entry.get("id"),
                    "nl_query": nl_query,
                    "status": "success"
                })
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
                results.append({
                    "nl_query": row.get('nl_query', 'unknown'),
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    # Ensure reload is False for production or when using multiple workers
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
