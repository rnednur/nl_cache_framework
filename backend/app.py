from fastapi import FastAPI, Depends, HTTPException, Request, Body, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, Tuple, List, Dict, Any, Union
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
import traceback

# Import database configuration
from database import get_db, engine, SessionLocal

# Import LLM service for enhanced completions
from llm_service import LLMService

# Import prompts
from prompts import REASONING_TRACE_PROMPT

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
    from thinkforge.recipe_step_analyzer import RecipeStepAnalyzer, ParsedStep
    from thinkforge.recipe_tool_mapper import RecipeToolMapper, StepMapping, ToolMatch
    from thinkforge.confidence_engine import ConfidenceEngine
    from thinkforge.llm_step_processor import LLMStepProcessor, LLMStepResult, create_sample_llm_step_template
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
    use_llm: Optional[bool] = Field(False, description="If True, use LLM to enhance search results")
    catalog_type: Optional[str] = Field(None, description="Optional catalog type to filter cache entries")
    catalog_subtype: Optional[str] = Field(None, description="Optional catalog subtype to filter cache entries")
    catalog_name: Optional[str] = Field(None, description="Optional catalog name to filter cache entries")
    template_type: Optional[str] = Field(None, description="Optional template type to filter cache entries")
    similarity_threshold: Optional[float] = Field(None, description="Similarity threshold for cache matching")
    limit: Optional[int] = Field(None, description="Limit for the number of top similarity results")

class EntitySubstitutionRequest(BaseModel):
    entity_values: Dict[str, Any] = Field(..., description="Entity values for substitution")

# Workflow generation models
class GenerateWorkflowRequest(BaseModel):
    nl_query: str
    catalog_type: Optional[str] = None
    catalog_subtype: Optional[str] = None
    catalog_name: Optional[str] = None
    
class GenerateWorkflowResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    workflow_template: Dict[str, Any]
    explanation: str

# Recipe analysis models
class RecipeAnalysisRequest(BaseModel):
    recipe_text: str = Field(..., description="Natural language recipe text to analyze")
    recipe_name: Optional[str] = Field(None, description="Optional name for the recipe")
    similarity_threshold: Optional[float] = Field(0.6, description="Minimum similarity threshold for tool matching")
    max_matches_per_step: Optional[int] = Field(5, description="Maximum tool matches per step")
    catalog_type: Optional[str] = Field(None, description="Filter tools by catalog type")
    catalog_subtype: Optional[str] = Field(None, description="Filter tools by catalog subtype")
    catalog_name: Optional[str] = Field(None, description="Filter tools by catalog name")

class MappedToolInfo(BaseModel):
    id: Optional[int] = Field(None, description="Tool ID if found in database")
    cache_entry_id: Optional[int] = Field(None, description="Cache entry ID if tool exists")
    name: str = Field(..., description="Tool name")
    type: str = Field(..., description="Tool type (api, function, mcp_tool, agent)")
    confidence: float = Field(..., description="Overall confidence score (0.0-1.0)")
    reasoning: str = Field(..., description="Human-readable reasoning for the match")
    exists: bool = Field(..., description="Whether tool exists in database")
    needs_creation: bool = Field(..., description="Whether tool needs to be created")
    similarity_score: Optional[float] = Field(None, description="Semantic similarity score")
    context_score: Optional[float] = Field(None, description="Contextual compatibility score")
    compatibility_score: Optional[float] = Field(None, description="Technical compatibility score")

class ParsedRecipeStep(BaseModel):
    id: str = Field(..., description="Step identifier")
    name: str = Field(..., description="Step name")
    description: str = Field(..., description="Step description")
    step_type: str = Field(..., description="Step type (action, condition, loop, transform, validation, integration)")
    confidence: float = Field(..., description="Step parsing confidence (0.0-1.0)")
    action_verbs: List[str] = Field(default_factory=list, description="Extracted action verbs")
    entities: List[str] = Field(default_factory=list, description="Extracted entities")
    mapped_tool: Optional[MappedToolInfo] = Field(None, description="Best matched tool if found")
    alternative_tools: List[MappedToolInfo] = Field(default_factory=list, description="Alternative tool matches")
    requires_review: bool = Field(False, description="Whether step requires manual review")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")

class RecipeAnalysisResponse(BaseModel):
    recipe_name: str = Field(..., description="Recipe name")
    description: str = Field(..., description="Recipe description")
    steps: List[ParsedRecipeStep] = Field(..., description="Parsed recipe steps")
    total_steps: int = Field(..., description="Total number of steps")
    complexity_score: float = Field(..., description="Recipe complexity score (0.0-1.0)")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in minutes")
    required_capabilities: List[str] = Field(default_factory=list, description="Required capabilities")
    recipe_type: str = Field(..., description="Classified recipe type")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional analysis metadata")

class StepRewriteRequest(BaseModel):
    step_id: str = Field(..., description="ID of the step to rewrite")
    new_description: str = Field(..., description="New natural language description for the step")
    similarity_threshold: Optional[float] = Field(0.6, description="Minimum similarity threshold for tool matching")
    max_matches: Optional[int] = Field(5, description="Maximum tool matches to return")
    catalog_type: Optional[str] = Field(None, description="Filter tools by catalog type")
    catalog_subtype: Optional[str] = Field(None, description="Filter tools by catalog subtype")
    catalog_name: Optional[str] = Field(None, description="Filter tools by catalog name")

class StepRewriteResponse(BaseModel):
    original_step: ParsedRecipeStep = Field(..., description="Original step before rewrite")
    rewritten_step: ParsedRecipeStep = Field(..., description="Rewritten and reanalyzed step")
    analysis_changes: Dict[str, Any] = Field(default_factory=dict, description="Summary of changes made")

# LLM Step models
class LLMStepCreateRequest(BaseModel):
    nl_query: str = Field(..., description="Natural language description of the LLM step")
    prompt_template: str = Field(..., description="LLM prompt template with {parameter} placeholders")
    input_parameters: List[str] = Field(..., description="List of required input parameter names")
    output_format: str = Field("json", description="Expected output format: json, text, or structured")
    expected_output: Dict[str, Any] = Field(..., description="Schema defining expected output structure")
    model: str = Field("google/gemini-pro", description="LLM model identifier")
    temperature: float = Field(0.3, description="Model temperature (0.0 to 1.0)")
    max_tokens: int = Field(500, description="Maximum tokens in response")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt for context")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Output validation configuration")
    examples: Optional[List[Dict[str, Any]]] = Field(None, description="Example inputs and outputs")
    catalog_type: Optional[str] = Field(None, description="Catalog type identifier")
    catalog_subtype: Optional[str] = Field(None, description="Catalog subtype identifier")
    catalog_name: Optional[str] = Field(None, description="Catalog name identifier")

class LLMStepExecuteRequest(BaseModel):
    input_values: Dict[str, Any] = Field(..., description="Input parameter values for the LLM step")

class LLMStepExecuteResponse(BaseModel):
    success: bool = Field(..., description="Whether execution was successful")
    output: Any = Field(None, description="Formatted output from LLM step")
    raw_response: str = Field("", description="Raw LLM response")
    validation_passed: bool = Field(True, description="Whether output passed validation")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    execution_metadata: Optional[Dict[str, Any]] = Field(None, description="Execution metadata")

class LLMStepTestRequest(BaseModel):
    test_inputs: Optional[Dict[str, Any]] = Field(None, description="Optional test input values")

class LLMStepTestResponse(BaseModel):
    success: bool = Field(..., description="Whether test was successful")
    output: Any = Field(None, description="Test output")
    raw_response: str = Field("", description="Raw LLM response from test")
    validation_passed: bool = Field(True, description="Whether output passed validation")
    error_message: Optional[str] = Field(None, description="Error message if test failed")
    test_inputs: Optional[Dict[str, Any]] = Field(None, description="Input values used in test")
    execution_metadata: Optional[Dict[str, Any]] = Field(None, description="Test execution metadata")

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

# Include sandbox API routes
try:
    from sandbox_api import include_sandbox_routes
    include_sandbox_routes(app)
except ImportError as e:
    print(f"Warning: Sandbox API not available: {e}")
    pass

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
                # Rollback the current transaction to prevent InFailedSqlTransaction errors
                try:
                    db.rollback()
                except:
                    pass
                type_counts[template_type_enum.value] = 0
        
        # If template_type filter is specified, only return that type count
        if template_type:
            # Handle comma-separated template types
            if ',' in template_type:
                allowed_types = [t.strip() for t in template_type.split(',')]
                for ttype in type_counts.keys():
                    if ttype not in allowed_types:
                        type_counts[ttype] = 0
            else:
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
            # Rollback the current transaction to prevent further failures
            try:
                db.rollback()
            except:
                pass
            
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
            # Rollback the current transaction to prevent further failures
            try:
                db.rollback()
            except:
                pass
        
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
async def get_catalog_values(
    catalog_type: Optional[str] = Query(None, description="Filter subtypes by catalog type"),
    catalog_subtype: Optional[str] = Query(None, description="Filter names by catalog subtype"),
    db: Session = Depends(get_db)
):
    """Get distinct catalog values with optional hierarchical filtering"""
    try:
        # Always get all catalog types
        catalog_types_query = db.query(Text2SQLCache.catalog_type).distinct().filter(
            Text2SQLCache.catalog_type.is_not(None)
        )
        catalog_types = [t[0] for t in catalog_types_query.all() if t[0]]
        
        # Filter subtypes by catalog_type if provided
        catalog_subtypes_query = db.query(Text2SQLCache.catalog_subtype).distinct().filter(
            Text2SQLCache.catalog_subtype.is_not(None)
        )
        if catalog_type:
            catalog_subtypes_query = catalog_subtypes_query.filter(
                Text2SQLCache.catalog_type == catalog_type
            )
        catalog_subtypes = [t[0] for t in catalog_subtypes_query.all() if t[0]]
        
        # Filter names by catalog_type and/or catalog_subtype if provided
        catalog_names_query = db.query(Text2SQLCache.catalog_name).distinct().filter(
            Text2SQLCache.catalog_name.is_not(None)
        )
        if catalog_type:
            catalog_names_query = catalog_names_query.filter(
                Text2SQLCache.catalog_type == catalog_type
            )
        if catalog_subtype:
            catalog_names_query = catalog_names_query.filter(
                Text2SQLCache.catalog_subtype == catalog_subtype
            )
        catalog_names = [t[0] for t in catalog_names_query.all() if t[0]]
        
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
    catalog_type: Optional[str] = Query(None),
    catalog_subtype: Optional[str] = Query(None),
    catalog_name: Optional[str] = Query(None),
    similarity_threshold: Optional[float] = Query(None),
    limit: Optional[int] = Query(None),
    use_llm: Optional[bool] = Query(False),
    db: Session = Depends(get_db)
):
    """Process a completion request, utilizing the NL cache.

    Looks up the prompt in the cache. If a match is found (above threshold),
    it returns the cached template (potentially with entity substitution).
    If no match is found, it returns a placeholder response indicating
    that external LLM processing would be needed.

    Args:
        request: The request containing the prompt.
        catalog_type: Optional catalog type to filter cache entries (can be in query params or body).
        catalog_subtype: Optional catalog subtype to filter cache entries (can be in query params or body).
        catalog_name: Optional catalog name to filter cache entries (can be in query params or body).
        similarity_threshold: Optional similarity threshold for cache matching (can be in query params or body).
        limit: Optional limit for the number of top similarity results to use (can be in query params or body).
        use_llm: If True, use LLM to enhance search results with semantic analysis (can be in query params or body).
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

    # Extract parameters from request object, with query parameters taking precedence
    use_llm = use_llm if use_llm is not None else (request.use_llm or False)
    catalog_type = catalog_type if catalog_type is not None else request.catalog_type
    catalog_subtype = catalog_subtype if catalog_subtype is not None else request.catalog_subtype
    catalog_name = catalog_name if catalog_name is not None else request.catalog_name
    template_type = request.template_type
    similarity_threshold = similarity_threshold if similarity_threshold is not None else request.similarity_threshold
    limit = limit if limit is not None else request.limit

    # DEBUG: Log the endpoint parameters
    logger.info(f"=== /v1/complete ENDPOINT DEBUG ===")
    logger.info(f"Request prompt: {query[:100]}...")
    logger.info(f"use_llm parameter: {use_llm} (type: {type(use_llm)})")
    logger.info(f"catalog_type: {catalog_type}")
    logger.info(f"catalog_subtype: {catalog_subtype}")
    logger.info(f"catalog_name: {catalog_name}")
    logger.info(f"template_type: {template_type}")
    logger.info(f"similarity_threshold: {similarity_threshold}")
    logger.info(f"limit: {limit}")

    # --- Cache Interaction ---
    controller = get_controller(db)

    # Use provided similarity threshold or default
    threshold = similarity_threshold if similarity_threshold is not None else SIMILARITY_THRESHOLD

    try:
        logger.info(f"Calling controller.process_completion with use_llm={use_llm}")
        response_data = controller.process_completion(
            query=query,
            similarity_threshold=threshold,
            use_llm=use_llm,
            catalog_type=catalog_type,
            catalog_subtype=catalog_subtype,
            catalog_name=catalog_name,
            template_type=template_type,
            limit=limit
        )
        logger.info(f"Response from controller: {list(response_data.keys())}")
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
        # Handle comma-separated template types
        if ',' in template_type:
            template_types = [t.strip() for t in template_type.split(',')]
            query = query.filter(Text2SQLCache.template_type.in_(template_types))
        else:
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
            "usage_count": 0,  # Placeholder for now, could be calculated from usage logs
            # Add missing fields
            "execution_config": entry.execution_config,
            "tool_capabilities": entry.tool_capabilities,
            "tool_dependencies": entry.tool_dependencies,
            "health_status": entry.health_status,
            "last_tested": entry.last_tested.isoformat() if entry.last_tested else None,
            "recipe_steps": entry.recipe_steps,
            "required_tools": entry.required_tools,
            "execution_time_estimate": entry.execution_time_estimate,
            "complexity_level": entry.complexity_level,
            "success_rate": entry.success_rate,
            "last_executed": entry.last_executed.isoformat() if entry.last_executed else None,
            "execution_count": entry.execution_count
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
        "status": entry.status,
        # Add missing fields
        "execution_config": entry.execution_config,
        "tool_capabilities": entry.tool_capabilities,
        "tool_dependencies": entry.tool_dependencies,
        "health_status": entry.health_status,
        "last_tested": entry.last_tested.isoformat() if entry.last_tested else None,
        "recipe_steps": entry.recipe_steps,
        "required_tools": entry.required_tools,
        "execution_time_estimate": entry.execution_time_estimate,
        "complexity_level": entry.complexity_level,
        "success_rate": entry.success_rate,
        "last_executed": entry.last_executed.isoformat() if entry.last_executed else None,
        "execution_count": entry.execution_count
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
                "response": getattr(log, "response", None),
                "success_status": log.success_status,
                "similarity_score": log.similarity_score,
                "error_message": log.error_message,
                "catalog_type": log.catalog_type,
                "catalog_subtype": log.catalog_subtype,
                "catalog_name": log.catalog_name,
                "llm_used": getattr(log, "llm_used", False),
                "considered_entries": getattr(log, "considered_entries", []),
                "is_confident": getattr(log, "is_confident", None)
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
        
        # Extract server information for building URLs
        base_url = ""
        if 'servers' in swagger_data and swagger_data['servers']:
            # OpenAPI 3.0 format
            base_url = swagger_data['servers'][0]['url']
        else:
            # Swagger 2.0 format
            host = swagger_data.get('host', '')
            schemes = swagger_data.get('schemes', ['https'])
            base_path = swagger_data.get('basePath', '')
            if host:
                base_url = f"{schemes[0]}://{host}{base_path}"
        
        logger.info(f"Extracted base URL from Swagger: {base_url}")

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
                        
                        # Now update the entry with execution_config
                        if new_entry and new_entry.get('id') and base_url:
                            entry_id = new_entry['id']
                            full_url = base_url.rstrip('/') + path
                            
                            # Create execution config with URL information
                            execution_config = {
                                'base_url': base_url,
                                'full_endpoint': full_url,
                                'method': method.upper(),
                                'timeout': 30,
                                'headers': {
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json'
                                }
                            }
                            
                            # Update the cache entry with execution config
                            cache_entry = db.query(Text2SQLCache).filter(Text2SQLCache.id == entry_id).first()
                            if cache_entry:
                                cache_entry.execution_config = execution_config
                                db.commit()
                                logger.info(f"Updated entry {entry_id} with execution_config: {full_url}")
                        
                        
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
        
        # Prepare prompt for reasoning trace generation using the imported prompt template
        prompt = REASONING_TRACE_PROMPT.format(
            nl_query=nl_query,
            template_type=template_type,
            template=template
        )
        
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


@app.post("/v1/workflows/generate", response_model=GenerateWorkflowResponse)
def generate_workflow(
    request: GenerateWorkflowRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a workflow from a natural language query using LLM.
    The LLM will analyze the query, determine necessary steps, and create a workflow.
    """
    try:
        # Directly query the database for compatible cache entries
        # Base query for all cache entries that can be used as steps
        query = db.query(Text2SQLCache).filter(Text2SQLCache.status == "active")
        
        # Apply catalog filters if specified
        if request.catalog_type:
            query = query.filter(or_(
                Text2SQLCache.catalog_type == request.catalog_type,
                Text2SQLCache.catalog_type == None  # Also include entries with NULL catalog_type
            ))
        
        if request.catalog_subtype:
            query = query.filter(or_(
                Text2SQLCache.catalog_subtype == request.catalog_subtype,
                Text2SQLCache.catalog_subtype == None  # Also include entries with NULL catalog_subtype
            ))
        
        if request.catalog_name:
            query = query.filter(or_(
                Text2SQLCache.catalog_name == request.catalog_name,
                Text2SQLCache.catalog_name == None  # Also include entries with NULL catalog_name
            ))
        
        # Execute query, limited to a reasonable number to prevent overloading the UI
        cache_entries = query.limit(100).all()
        
        # Process entries for the workflow design
        compatible_entries = []
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
            compatible_entries.append(item)
        
        # Use LLMService directly instead of controller.design_workflow_with_llm
        from llm_service import LLMService
        llm_service = LLMService()
        
        if not llm_service.is_configured():
            raise Exception("LLM service is not properly configured. Please check your environment variables.")
            
        # Prepare the prompt for the LLM
        system_prompt = "You are a workflow designer that creates data processing workflows based on user requests."
        
        # Create a description of available cache entries/steps
        entries_description = "\n\n".join([
            f"Step {i+1}:\nID: {entry['id']}\nDescription: {entry['nl_query']}\nType: {entry['template_type']}"
            for i, entry in enumerate(compatible_entries[:20])  # Limit to 20 entries to avoid token limits
        ])
        
        user_prompt = f"""
        Create a workflow to fulfill this request: "{request.nl_query}"
        
        Available steps:
        {entries_description}
        
        Respond with a JSON object containing:
        1. "nodes": Array of nodes with id, type, position, data
        2. "edges": Array of connections between nodes
        3. "workflow_template": The compiled workflow template
        4. "explanation": Explanation of how the workflow fulfills the request
        """
        
        # Call LLM to design the workflow
        response = llm_service.client.chat.completions.create(
            model=llm_service.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse the LLM response
        workflow_design = json.loads(response.choices[0].message.content)
        
        # Ensure the response has the required format
        if not all(key in workflow_design for key in ["nodes", "edges", "workflow_template", "explanation"]):
            raise Exception("LLM response does not contain all required fields")
        
        return workflow_design
        
    except Exception as e:
        logging.error(f"Error generating workflow: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate workflow: {str(e)}")


# Recipe compilation endpoints
class RecipeCompilationRequest(BaseModel):
    """Request model for recipe compilation."""
    target_format: str = Field(..., description="Target format: langchain, langgraph, langflow, generic")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Compilation parameters")


class RecipeCompilationResponse(BaseModel):
    """Response model for recipe compilation."""
    success: bool
    format: str
    workflow_definition: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


@app.post("/v1/recipes/{recipe_id}/compile", response_model=RecipeCompilationResponse)
async def compile_recipe(
    recipe_id: int,
    request: RecipeCompilationRequest,
    db: Session = Depends(get_db)
):
    """Compile a recipe to the specified workflow format."""
    try:
        # Import here to avoid circular imports
        from thinkforge.recipe_compiler import RecipeCompiler, WorkflowFormat
        
        # Get the recipe
        recipe = db.query(Text2SQLCache).filter(Text2SQLCache.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        # Validate recipe type
        if recipe.template_type not in ['recipe', 'recipe_step', 'recipe_template', 'workflow']:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid recipe type: {recipe.template_type}. Must be recipe, recipe_step, recipe_template, or workflow"
            )
        
        # Create tool resolver function
        def tool_resolver(tool_id: int) -> Optional[Dict[str, Any]]:
            tool = db.query(Text2SQLCache).filter(Text2SQLCache.id == tool_id).first()
            if tool:
                return tool.to_dict()
            return None
        
        # Initialize compiler
        compiler = RecipeCompiler(tool_resolver=tool_resolver)
        
        # Validate target format
        try:
            target_format = WorkflowFormat(request.target_format.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target format: {request.target_format}. Must be one of: langchain, langgraph, langflow, generic"
            )
        
        # Compile the recipe
        result = compiler.compile_recipe(recipe, target_format, request.parameters)
        
        return RecipeCompilationResponse(
            success=result.success,
            format=result.format.value,
            workflow_definition=result.workflow_definition,
            metadata=result.metadata,
            errors=result.errors,
            warnings=result.warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recipe compilation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")


@app.get("/v1/recipes/{recipe_id}/formats")
async def get_supported_formats(recipe_id: int, db: Session = Depends(get_db)):
    """Get supported compilation formats for a recipe."""
    try:
        # Get the recipe
        recipe = db.query(Text2SQLCache).filter(Text2SQLCache.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        # Check if it's a compilable recipe type
        if recipe.template_type not in ['recipe', 'recipe_step', 'recipe_template', 'workflow']:
            return {
                "supported_formats": [],
                "reason": f"Recipe type '{recipe.template_type}' is not compilable"
            }
        
        # Return supported formats
        return {
            "supported_formats": [
                {
                    "format": "langchain",
                    "name": "LangChain LCEL",
                    "description": "LangChain Expression Language format for chain execution"
                },
                {
                    "format": "langgraph", 
                    "name": "LangGraph",
                    "description": "LangGraph format for stateful graph execution"
                },
                {
                    "format": "langflow",
                    "name": "Langflow",
                    "description": "Langflow JSON format for visual workflow execution"
                },
                {
                    "format": "generic",
                    "name": "Generic Workflow",
                    "description": "Generic workflow format with execution plan"
                }
            ],
            "recipe_metadata": {
                "id": recipe.id,
                "name": recipe.nl_query,
                "type": recipe.template_type,
                "complexity_level": recipe.complexity_level,
                "step_count": len(recipe.recipe_steps) if recipe.recipe_steps else 0,
                "tool_count": len(recipe.required_tools) if recipe.required_tools else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supported formats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get supported formats: {str(e)}")


@app.post("/v1/recipes/analyze-natural-language", response_model=RecipeAnalysisResponse)
async def analyze_recipe_natural_language(
    request: RecipeAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze natural language recipe text and map steps to available tools using semantic similarity.
    
    This endpoint performs real similarity search against the database to find matching tools
    for each recipe step, replacing the mock data approach.
    """
    try:
        logger.info(f"Analyzing recipe: {request.recipe_name or 'Unnamed'}")
        
        # Initialize the Text2SQL controller for similarity search
        controller = Text2SQLController(db_session=db)
        
        # Initialize the recipe analysis components
        step_analyzer = RecipeStepAnalyzer()
        tool_mapper = RecipeToolMapper(db_session=db, controller=controller)
        confidence_engine = ConfidenceEngine()
        
        # Analyze the recipe text to extract structured steps
        recipe_analysis = step_analyzer.analyze_recipe(
            recipe_text=request.recipe_text,
            recipe_name=request.recipe_name or "Generated Recipe"
        )
        
        # Prepare catalog filters
        catalog_filters = {}
        if request.catalog_type:
            catalog_filters['catalog_type'] = request.catalog_type
        if request.catalog_subtype:
            catalog_filters['catalog_subtype'] = request.catalog_subtype
        if request.catalog_name:
            catalog_filters['catalog_name'] = request.catalog_name
        
        # Map recipe steps to available tools using real similarity search
        step_mappings = tool_mapper.map_recipe_to_tools(
            steps=recipe_analysis.steps,
            similarity_threshold=request.similarity_threshold,
            max_matches_per_step=request.max_matches_per_step,
            catalog_filters=catalog_filters if catalog_filters else None
        )
        
        # Convert results to API response format
        parsed_steps = []
        for mapping in step_mappings:
            step = mapping.step
            
            # Convert best match to API format
            mapped_tool = None
            if mapping.best_match:
                tool_match = mapping.best_match
                mapped_tool = MappedToolInfo(
                    id=tool_match.tool_id,
                    cache_entry_id=tool_match.tool_id,  # Cache entry ID is the same as tool ID
                    name=tool_match.tool_name,
                    type=tool_match.tool_type,
                    confidence=tool_match.overall_confidence,
                    reasoning=tool_match.reasoning,
                    exists=True,  # If we found it in search, it exists
                    needs_creation=False,
                    similarity_score=tool_match.similarity_score,
                    context_score=tool_match.context_score,
                    compatibility_score=tool_match.compatibility_score
                )
            
            # Convert alternative matches
            alternative_tools = []
            for alt_match in mapping.matches[1:4]:  # Top 3 alternatives
                alternative_tools.append(MappedToolInfo(
                    id=alt_match.tool_id,
                    cache_entry_id=alt_match.tool_id,
                    name=alt_match.tool_name,
                    type=alt_match.tool_type,
                    confidence=alt_match.overall_confidence,
                    reasoning=alt_match.reasoning,
                    exists=True,
                    needs_creation=False,
                    similarity_score=alt_match.similarity_score,
                    context_score=alt_match.context_score,
                    compatibility_score=alt_match.compatibility_score
                ))
            
            # Create parsed step
            parsed_step = ParsedRecipeStep(
                id=step.id,
                name=step.name,
                description=step.description,
                step_type=step.step_type.value,
                confidence=step.confidence,
                action_verbs=step.action_verbs,
                entities=step.entities,
                mapped_tool=mapped_tool,
                alternative_tools=alternative_tools,
                requires_review=mapping.requires_manual_review,
                suggestions=mapping.suggestions
            )
            parsed_steps.append(parsed_step)
        
        # Create response
        response = RecipeAnalysisResponse(
            recipe_name=recipe_analysis.recipe_name,
            description=recipe_analysis.description,
            steps=parsed_steps,
            total_steps=recipe_analysis.total_steps,
            complexity_score=recipe_analysis.complexity_score,
            estimated_duration=recipe_analysis.estimated_duration,
            required_capabilities=recipe_analysis.required_capabilities,
            recipe_type=recipe_analysis.recipe_type,
            analysis_metadata={
                "analyzer_version": "1.0",
                "similarity_threshold": request.similarity_threshold,
                "max_matches_per_step": request.max_matches_per_step,
                "processing_time": time.time()  # Simple timestamp
            }
        )
        
        logger.info(f"Successfully analyzed recipe with {len(parsed_steps)} steps")
        return response
        
    except Exception as e:
        error_msg = f"Recipe analysis failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/v1/recipes/rewrite-step", response_model=StepRewriteResponse)
async def rewrite_recipe_step(
    request: StepRewriteRequest,
    db: Session = Depends(get_db)
):
    """
    Rewrite and reanalyze a single recipe step with new natural language description.
    
    This endpoint allows users to refine individual steps and get better tool matches
    by providing a clearer or more specific description.
    """
    try:
        logger.info(f"Rewriting step {request.step_id} with new description: {request.new_description[:100]}...")
        
        # Initialize analysis components
        controller = Text2SQLController(db_session=db)
        step_analyzer = RecipeStepAnalyzer()
        tool_mapper = RecipeToolMapper(db_session=db, controller=controller)
        
        # Parse the new step description
        parsed_step = step_analyzer._parse_single_step(request.new_description, 1)
        if not parsed_step:
            raise HTTPException(status_code=400, detail="Failed to parse the new step description")
        
        # Override the step ID to match the request
        parsed_step.id = request.step_id
        
        # Prepare catalog filters
        catalog_filters = {}
        if request.catalog_type:
            catalog_filters['catalog_type'] = request.catalog_type
        if request.catalog_subtype:
            catalog_filters['catalog_subtype'] = request.catalog_subtype
        if request.catalog_name:
            catalog_filters['catalog_name'] = request.catalog_name
        
        # Find tool matches for the rewritten step
        tool_matches = tool_mapper.find_tools_for_step(
            step=parsed_step,
            max_results=request.max_matches,
            catalog_filters=catalog_filters if catalog_filters else None
        )
        
        # Filter matches by threshold
        filtered_matches = [m for m in tool_matches if m.overall_confidence >= request.similarity_threshold]
        
        # Convert best match to API format
        mapped_tool = None
        if filtered_matches:
            best_match = filtered_matches[0]
            mapped_tool = MappedToolInfo(
                id=best_match.tool_id,
                cache_entry_id=best_match.tool_id,
                name=best_match.tool_name,
                type=best_match.tool_type,
                confidence=best_match.overall_confidence,
                reasoning=best_match.reasoning,
                exists=True,
                needs_creation=False,
                similarity_score=best_match.similarity_score,
                context_score=best_match.context_score,
                compatibility_score=best_match.compatibility_score
            )
        
        # Convert alternative matches
        alternative_tools = []
        for alt_match in filtered_matches[1:4]:  # Top 3 alternatives
            alternative_tools.append(MappedToolInfo(
                id=alt_match.tool_id,
                cache_entry_id=alt_match.tool_id,
                name=alt_match.tool_name,
                type=alt_match.tool_type,
                confidence=alt_match.overall_confidence,
                reasoning=alt_match.reasoning,
                exists=True,
                needs_creation=False,
                similarity_score=alt_match.similarity_score,
                context_score=alt_match.context_score,
                compatibility_score=alt_match.compatibility_score
            ))
        
        # Generate suggestions for the rewritten step
        suggestions = []
        if not filtered_matches:
            suggestions.append("No matching tools found. Consider creating a custom tool or refining the description.")
        elif len(filtered_matches) == 1:
            if filtered_matches[0].overall_confidence < 0.5:
                suggestions.append("Low confidence match found. Consider reviewing the tool or refining the description.")
            else:
                suggestions.append("Good match found! Review the suggested tool for compatibility.")
        else:
            suggestions.append(f"Multiple matches found ({len(filtered_matches)}). Review alternatives for the best fit.")
        
        # Create the rewritten step
        rewritten_step = ParsedRecipeStep(
            id=parsed_step.id,
            name=parsed_step.name,
            description=parsed_step.description,
            step_type=parsed_step.step_type.value,
            confidence=parsed_step.confidence,
            action_verbs=parsed_step.action_verbs,
            entities=parsed_step.entities,
            mapped_tool=mapped_tool,
            alternative_tools=alternative_tools,
            requires_review=not filtered_matches or (filtered_matches and filtered_matches[0].overall_confidence < 0.7),
            suggestions=suggestions
        )
        
        # For this endpoint, we'll create a placeholder "original step" since we don't have the full context
        # In a real implementation, you might want to pass the original step data
        original_step = ParsedRecipeStep(
            id=request.step_id,
            name="Original Step",
            description="[Original step description not provided]",
            step_type="unknown",
            confidence=0.0,
            action_verbs=[],
            entities=[],
            mapped_tool=None,
            alternative_tools=[],
            requires_review=True,
            suggestions=["Original step data not available"]
        )
        
        # Calculate analysis changes
        analysis_changes = {
            "description_changed": True,
            "new_step_type": parsed_step.step_type.value,
            "new_confidence": parsed_step.confidence,
            "new_action_verbs": parsed_step.action_verbs,
            "new_entities": parsed_step.entities,
            "tools_found": len(filtered_matches),
            "best_match_confidence": filtered_matches[0].overall_confidence if filtered_matches else 0.0,
            "catalog_filters_applied": bool(catalog_filters),
            "processing_timestamp": time.time()
        }
        
        response = StepRewriteResponse(
            original_step=original_step,
            rewritten_step=rewritten_step,
            analysis_changes=analysis_changes
        )
        
        logger.info(f"Successfully rewrote step {request.step_id} with {len(filtered_matches)} tool matches")
        return response
        
    except Exception as e:
        error_msg = f"Step rewrite failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)


# Workflow Execution API Endpoints
from thinkforge.execution_engine import WorkflowExecutor, ExecutionStatus, ExecutionContext
from thinkforge.tool_invoker import ToolInvoker
from thinkforge.notebook_generator import PythonNotebookGenerator
import asyncio


class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution."""
    input_variables: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input variables for workflow")
    background: bool = Field(default=False, description="Execute in background")


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution."""
    run_id: str
    workflow_id: int
    status: str
    message: str
    execution_url: str


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""
    workflow_id: int
    run_id: str
    status: str
    current_step: Optional[str]
    progress: Dict[str, Any]
    step_results: Dict[str, Any]
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


class NotebookGenerationRequest(BaseModel):
    """Request model for notebook generation."""
    workflow_name: Optional[str] = Field(default=None, description="Name for the generated notebook")
    include_documentation: bool = Field(default=True, description="Include markdown documentation cells")
    add_setup_cells: bool = Field(default=True, description="Include environment setup cells")


class NotebookGenerationResponse(BaseModel):
    """Response model for notebook generation."""
    success: bool
    notebook: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    metadata: Dict[str, Any]
    error: Optional[str] = None


# Global workflow executor instance
workflow_executor: Optional[WorkflowExecutor] = None


def get_workflow_executor(db: Session = Depends(get_db)) -> WorkflowExecutor:
    """Get or create the global workflow executor instance."""
    global workflow_executor
    if workflow_executor is None:
        tool_invoker = ToolInvoker(db)
        workflow_executor = WorkflowExecutor(db, tool_invoker)
    return workflow_executor


@app.post("/v1/workflows/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: int,
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    executor: WorkflowExecutor = Depends(get_workflow_executor)
):
    """
    Start execution of a workflow.
    
    Args:
        workflow_id: ID of the workflow to execute
        request: Execution parameters
        background_tasks: FastAPI background tasks
        db: Database session
        executor: Workflow executor instance
    
    Returns:
        Execution response with run ID and status
    """
    try:
        # Verify workflow exists
        workflow = db.query(Text2SQLCache).filter_by(id=workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Verify it's a workflow type
        if workflow.template_type not in ['workflow', 'recipe', 'recipe_template']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cache entry {workflow_id} is not a workflow (type: {workflow.template_type})"
            )

        if request.background:
            # Execute in background
            async def background_execution():
                try:
                    await executor.execute_workflow(
                        workflow_id=workflow_id,
                        input_variables=request.input_variables
                    )
                except Exception as e:
                    logger.error(f"Background workflow execution failed: {e}")
            
            background_tasks.add_task(background_execution)
            
            # Return immediately with a placeholder run_id
            import uuid
            run_id = str(uuid.uuid4())
            
            return WorkflowExecutionResponse(
                run_id=run_id,
                workflow_id=workflow_id,
                status="queued",
                message="Workflow execution started in background",
                execution_url=f"/v1/workflows/{workflow_id}/execution/{run_id}"
            )
        else:
            # Execute synchronously
            context = await executor.execute_workflow(
                workflow_id=workflow_id,
                input_variables=request.input_variables
            )
            
            return WorkflowExecutionResponse(
                run_id=context.run_id,
                workflow_id=workflow_id,
                status=context.status.value,
                message="Workflow execution completed",
                execution_url=f"/v1/workflows/{workflow_id}/execution/{context.run_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@app.get("/v1/workflows/{workflow_id}/execution/{run_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(
    workflow_id: int,
    run_id: str,
    executor: WorkflowExecutor = Depends(get_workflow_executor)
):
    """
    Get the status of a workflow execution.
    
    Args:
        workflow_id: ID of the workflow
        run_id: Execution run ID
        executor: Workflow executor instance
    
    Returns:
        Execution status and progress
    """
    try:
        status_dict = executor.get_execution_status(run_id)
        
        if not status_dict:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return ExecutionStatusResponse(
            workflow_id=status_dict["workflow_id"],
            run_id=status_dict["run_id"],
            status=status_dict["status"],
            current_step=status_dict.get("current_step"),
            progress=status_dict["progress"],
            step_results=status_dict["step_results"],
            started_at=status_dict.get("started_at"),
            completed_at=status_dict.get("completed_at"),
            error_message=status_dict.get("error_message")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@app.post("/v1/workflows/{workflow_id}/execution/{run_id}/pause")
async def pause_execution(
    workflow_id: int,
    run_id: str,
    executor: WorkflowExecutor = Depends(get_workflow_executor)
):
    """Pause a running workflow execution."""
    try:
        success = await executor.pause_execution(run_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found or not running")
        
        return {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "status": "paused",
            "message": "Workflow execution paused"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause: {str(e)}")


@app.post("/v1/workflows/{workflow_id}/execution/{run_id}/resume")
async def resume_execution(
    workflow_id: int,
    run_id: str,
    executor: WorkflowExecutor = Depends(get_workflow_executor)
):
    """Resume a paused workflow execution."""
    try:
        success = await executor.resume_execution(run_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found or not paused")
        
        return {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "status": "running",
            "message": "Workflow execution resumed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume: {str(e)}")


@app.delete("/v1/workflows/{workflow_id}/execution/{run_id}")
async def cancel_execution(
    workflow_id: int,
    run_id: str,
    executor: WorkflowExecutor = Depends(get_workflow_executor)
):
    """Cancel a workflow execution."""
    try:
        success = await executor.cancel_execution(run_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "status": "cancelled",
            "message": "Workflow execution cancelled"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel: {str(e)}")


@app.get("/v1/workflows/executions")
async def list_active_executions(
    executor: WorkflowExecutor = Depends(get_workflow_executor)
):
    """List all active workflow executions."""
    try:
        executions = executor.list_active_executions()
        
        return {
            "active_executions": executions,
            "total": len(executions)
        }

    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")


@app.post("/v1/workflows/{workflow_id}/generate-notebook", response_model=NotebookGenerationResponse)
async def generate_workflow_notebook(
    workflow_id: int,
    request: NotebookGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a Jupyter notebook from a workflow DSL.
    
    Converts a workflow's DSL template into an executable Jupyter notebook
    with Python code cells for each step, including setup, execution,
    and validation code with proper variable passing between steps.
    
    Args:
        workflow_id: ID of the workflow to convert
        request: Notebook generation parameters
        db: Database session
    
    Returns:
        Generated notebook in Jupyter format ready for execution
    """
    try:
        # Get the workflow from the cache
        workflow = db.query(Text2SQLCache).filter_by(id=workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Verify it's a workflow type
        if workflow.template_type not in ['workflow', 'recipe', 'recipe_template']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cache entry {workflow_id} is not a workflow (type: {workflow.template_type})"
            )
        
        # Parse the workflow DSL template
        try:
            workflow_dsl = json.loads(workflow.template)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid workflow DSL JSON: {str(e)}"
            )
        
        # Initialize the notebook generator
        generator = PythonNotebookGenerator()
        
        # Determine workflow name
        workflow_name = request.workflow_name or workflow.nl_query or f"Workflow_{workflow_id}"
        
        # Generate the notebook
        notebook = generator.generate_notebook(
            workflow_dsl=workflow_dsl,
            workflow_name=workflow_name,
            include_documentation=request.include_documentation,
            add_setup_cells=request.add_setup_cells
        )
        
        # Calculate metadata
        workflow_dict = workflow_dsl.get("workflow", {})
        steps = workflow_dict.get("steps", [])
        
        metadata = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "total_cells": len(notebook["cells"]),
            "total_steps": len(steps),
            "step_types": list(set(step.get("type", "unknown") for step in steps)),
            "generated_at": datetime.datetime.now().isoformat(),
            "generator_version": "1.0.0",
            "notebook_format": f"v{notebook['nbformat']}.{notebook['nbformat_minor']}"
        }
        
        # Log successful generation
        logger.info(f"Generated notebook for workflow {workflow_id}: {len(notebook['cells'])} cells, {len(steps)} steps")
        
        return NotebookGenerationResponse(
            success=True,
            notebook=notebook,
            download_url=f"/v1/workflows/{workflow_id}/download-notebook",
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Notebook generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return NotebookGenerationResponse(
            success=False,
            metadata={"workflow_id": workflow_id, "error_type": type(e).__name__},
            error=error_msg
        )


@app.get("/v1/workflows/{workflow_id}/download-notebook")
async def download_workflow_notebook(
    workflow_id: int,
    workflow_name: Optional[str] = Query(None, description="Custom name for the notebook"),
    include_documentation: bool = Query(True, description="Include documentation cells"),
    add_setup_cells: bool = Query(True, description="Include setup cells"),
    db: Session = Depends(get_db)
):
    """
    Download a workflow as a Jupyter notebook file.
    
    Returns the notebook as a downloadable .ipynb file.
    """
    try:
        # Get the workflow from the cache
        workflow = db.query(Text2SQLCache).filter_by(id=workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Verify it's a workflow type  
        if workflow.template_type not in ['workflow', 'recipe', 'recipe_template']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cache entry {workflow_id} is not a workflow (type: {workflow.template_type})"
            )
        
        # Parse the workflow DSL template
        try:
            workflow_dsl = json.loads(workflow.template)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid workflow DSL JSON: {str(e)}"
            )
        
        # Initialize the notebook generator
        generator = PythonNotebookGenerator()
        
        # Determine workflow name
        name = workflow_name or workflow.nl_query or f"Workflow_{workflow_id}"
        filename = f"{name.replace(' ', '_').replace('/', '_')}.ipynb"
        
        # Generate the notebook
        notebook = generator.generate_notebook(
            workflow_dsl=workflow_dsl,
            workflow_name=name,
            include_documentation=include_documentation,
            add_setup_cells=add_setup_cells
        )
        
        # Convert to JSON string
        notebook_json = json.dumps(notebook, indent=2)
        
        # Return as downloadable file
        from fastapi.responses import Response
        
        return Response(
            content=notebook_json,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/x-ipynb+json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Notebook download failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)


# ============================================================================
# LLM Step Management Endpoints
# ============================================================================

@app.post("/v1/llm-steps/create", response_model=Dict[str, Any])
async def create_llm_step(
    request: LLMStepCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new LLM step template that can be used in recipes.
    
    Creates a cache entry with template_type='llm_step' containing the LLM step configuration.
    """
    try:
        logger.info(f"Creating LLM step: {request.nl_query[:100]}...")
        
        # Build the LLM step template JSON
        step_template = {
            "step_config": {
                "prompt_template": request.prompt_template,
                "input_parameters": request.input_parameters,
                "output_format": request.output_format,
                "expected_output": request.expected_output,
                "model": request.model,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "system_prompt": request.system_prompt
            }
        }
        
        # Add validation rules if provided
        if request.validation_rules:
            step_template["validation_rules"] = request.validation_rules
        
        # Add examples if provided
        if request.examples:
            step_template["examples"] = request.examples
        
        # Create the cache entry
        cache_entry = Text2SQLCache(
            nl_query=request.nl_query,
            template=json.dumps(step_template),
            template_type=TemplateType.LLM_STEP,
            is_template=True,  # LLM steps are templates by nature
            status="active",
            catalog_type=request.catalog_type,
            catalog_subtype=request.catalog_subtype,
            catalog_name=request.catalog_name,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )
        
        db.add(cache_entry)
        db.commit()
        db.refresh(cache_entry)
        
        logger.info(f"Created LLM step with ID {cache_entry.id}")
        
        return {
            "id": cache_entry.id,
            "nl_query": cache_entry.nl_query,
            "template": step_template,
            "template_type": cache_entry.template_type,
            "status": cache_entry.status,
            "created_at": cache_entry.created_at,
            "message": "LLM step created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating LLM step: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating LLM step: {str(e)}")


@app.post("/v1/llm-steps/{step_id}/execute", response_model=LLMStepExecuteResponse)
async def execute_llm_step(
    step_id: int,
    request: LLMStepExecuteRequest,
    db: Session = Depends(get_db)
):
    """
    Execute an LLM step with the provided input values.
    
    Retrieves the LLM step template and executes it with the given parameters.
    """
    try:
        logger.info(f"Executing LLM step {step_id} with inputs: {list(request.input_values.keys())}")
        
        # Get the LLM step from the cache
        cache_entry = db.query(Text2SQLCache).filter_by(id=step_id).first()
        if not cache_entry:
            raise HTTPException(status_code=404, detail="LLM step not found")
        
        if cache_entry.template_type != TemplateType.LLM_STEP:
            raise HTTPException(
                status_code=400, 
                detail=f"Cache entry {step_id} is not an LLM step (type: {cache_entry.template_type})"
            )
        
        # Parse the LLM step template
        try:
            step_template = json.loads(cache_entry.template)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid LLM step template JSON: {str(e)}"
            )
        
        # Initialize the LLM step processor
        llm_service = LLMService()
        processor = LLMStepProcessor(llm_service)
        
        # Execute the LLM step
        result = processor.execute_llm_step(step_template, request.input_values)
        
        # Log the execution in usage logs
        usage_log = UsageLog(
            cache_entry_id=step_id,
            timestamp=datetime.datetime.now(),
            prompt=step_template.get("step_config", {}).get("prompt_template", ""),
            success_status=result.success,
            similarity_score=1.0,  # Direct execution, so 100% match
            catalog_type=cache_entry.catalog_type,
            catalog_subtype=cache_entry.catalog_subtype,
            catalog_name=cache_entry.catalog_name,
            llm_used=True,
            error_message=result.error_message,
            response=str(result.output) if result.output else None
        )
        db.add(usage_log)
        db.commit()
        
        return LLMStepExecuteResponse(
            success=result.success,
            output=result.output,
            raw_response=result.raw_response,
            validation_passed=result.validation_passed,
            error_message=result.error_message,
            execution_metadata=result.execution_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing LLM step {step_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error executing LLM step: {str(e)}")


@app.post("/v1/llm-steps/{step_id}/test", response_model=LLMStepTestResponse)
async def test_llm_step(
    step_id: int,
    request: LLMStepTestRequest,
    db: Session = Depends(get_db)
):
    """
    Test an LLM step with example or provided input values.
    
    Useful for validating LLM step configuration before using it in recipes.
    """
    try:
        logger.info(f"Testing LLM step {step_id}")
        
        # Get the LLM step from the cache
        cache_entry = db.query(Text2SQLCache).filter_by(id=step_id).first()
        if not cache_entry:
            raise HTTPException(status_code=404, detail="LLM step not found")
        
        if cache_entry.template_type != TemplateType.LLM_STEP:
            raise HTTPException(
                status_code=400, 
                detail=f"Cache entry {step_id} is not an LLM step (type: {cache_entry.template_type})"
            )
        
        # Parse the LLM step template
        try:
            step_template = json.loads(cache_entry.template)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid LLM step template JSON: {str(e)}"
            )
        
        # Initialize the LLM step processor
        llm_service = LLMService()
        processor = LLMStepProcessor(llm_service)
        
        # Run the test
        test_result = processor.test_llm_step(step_template, request.test_inputs)
        
        return LLMStepTestResponse(
            success=test_result["success"],
            output=test_result.get("output"),
            raw_response=test_result.get("raw_response", ""),
            validation_passed=test_result.get("validation_passed", True),
            error_message=test_result.get("error_message"),
            test_inputs=test_result.get("test_inputs"),
            execution_metadata=test_result.get("execution_metadata")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing LLM step {step_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error testing LLM step: {str(e)}")


@app.get("/v1/llm-steps/templates")
async def get_llm_step_templates():
    """
    Get pre-built LLM step templates for common use cases.
    
    Returns a collection of example LLM step templates that users can customize.
    """
    try:
        # Get the sample template
        sample_template = create_sample_llm_step_template()
        
        # Create additional templates for common use cases
        templates = {
            "support_ticket_classifier": {
                "name": "Support Ticket Classifier",
                "description": "Analyze support tickets and classify their urgency level",
                "template": sample_template
            },
            "sentiment_analyzer": {
                "name": "Sentiment Analyzer", 
                "description": "Analyze text sentiment and provide confidence scores",
                "template": {
                    "step_config": {
                        "prompt_template": "Analyze the sentiment of this text: {text}\n\nClassify as: positive, negative, or neutral\n\nProvide your response in JSON format with fields: sentiment, confidence, and reasoning.",
                        "input_parameters": ["text"],
                        "output_format": "json",
                        "expected_output": {
                            "sentiment": "string",
                            "confidence": "float",
                            "reasoning": "string"
                        },
                        "model": "google/gemini-pro",
                        "temperature": 0.1,
                        "max_tokens": 200,
                        "system_prompt": "You are a sentiment analysis expert. Analyze text sentiment accurately and provide confidence scores."
                    },
                    "validation_rules": {
                        "required_fields": ["sentiment", "confidence"],
                        "validation_schema": {
                            "type": "object",
                            "properties": {
                                "sentiment": {
                                    "type": "string",
                                    "enum": ["positive", "negative", "neutral"]
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0
                                },
                                "reasoning": {"type": "string"}
                            },
                            "required": ["sentiment", "confidence"]
                        }
                    }
                }
            },
            "content_summarizer": {
                "name": "Content Summarizer",
                "description": "Generate concise summaries of long text content",
                "template": {
                    "step_config": {
                        "prompt_template": "Summarize the following content in {max_sentences} sentences or less: {content}\n\nFocus on the key points and main ideas.",
                        "input_parameters": ["content", "max_sentences"],
                        "output_format": "text",
                        "expected_output": {
                            "summary": "string"
                        },
                        "model": "google/gemini-pro",
                        "temperature": 0.3,
                        "max_tokens": 400,
                        "system_prompt": "You are a content summarization expert. Create concise, informative summaries that capture key information."
                    }
                }
            },
            "entity_extractor": {
                "name": "Entity Extractor",
                "description": "Extract named entities from text (people, places, organizations, etc.)",
                "template": {
                    "step_config": {
                        "prompt_template": "Extract named entities from this text: {text}\n\nIdentify people, places, organizations, dates, and other important entities.\n\nProvide your response in JSON format with fields: people, places, organizations, dates, other.",
                        "input_parameters": ["text"],
                        "output_format": "json",
                        "expected_output": {
                            "people": "array",
                            "places": "array", 
                            "organizations": "array",
                            "dates": "array",
                            "other": "array"
                        },
                        "model": "google/gemini-pro",
                        "temperature": 0.1,
                        "max_tokens": 300,
                        "system_prompt": "You are a named entity recognition expert. Extract entities accurately and categorize them properly."
                    }
                }
            }
        }
        
        return {
            "templates": templates,
            "count": len(templates),
            "categories": ["classification", "analysis", "extraction", "summarization"]
        }
        
    except Exception as e:
        logger.error(f"Error getting LLM step templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting templates: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    # Ensure reload is False for production or when using multiple workers
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
