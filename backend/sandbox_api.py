"""
Backend API integration for notebook sandbox.
Provides endpoints for DSL-to-notebook conversion and execution.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import structlog

from thinkforge.sandbox_manager import SandboxManager
from thinkforge.notebook_generator import PythonNotebookGenerator

logger = structlog.get_logger()

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# Pydantic models
class DSLExecutionRequest(BaseModel):
    dsl_content: Dict[str, Any]
    workflow_name: str
    memory_limit_mb: Optional[int] = 512
    cpu_time_limit: Optional[int] = 300
    wall_time_limit: Optional[int] = 600

class NotebookGenerationRequest(BaseModel):
    dsl_content: Dict[str, Any]
    workflow_name: str

class ExecutionStatusResponse(BaseModel):
    execution_id: str
    status: str
    workflow_name: str
    notebook_path: Optional[str] = None
    validation_result: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# In-memory execution tracking
active_executions: Dict[str, ExecutionStatusResponse] = {}

@router.get("/health")
async def sandbox_health():
    """Check sandbox service health."""
    try:
        async with SandboxManager() as sandbox:
            # Try to connect to sandbox API
            notebooks = await sandbox.list_notebooks()
            return {
                "status": "healthy",
                "sandbox_connected": True,
                "notebook_count": notebooks.get("count", 0)
            }
    except Exception as e:
        logger.error("Sandbox health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "sandbox_connected": False,
            "error": str(e)
        }

@router.post("/generate-notebook")
async def generate_notebook_from_dsl(request: NotebookGenerationRequest):
    """Generate a Jupyter notebook from DSL content."""
    try:
        generator = PythonNotebookGenerator()
        notebook_content = generator.generate_from_dsl(request.dsl_content)
        
        logger.info("Notebook generated successfully", 
                   workflow_name=request.workflow_name)
        
        return {
            "workflow_name": request.workflow_name,
            "notebook_content": notebook_content,
            "cells_generated": notebook_content.count('"cell_type"'),
            "success": True
        }
    
    except Exception as e:
        logger.error("Failed to generate notebook", 
                    workflow_name=request.workflow_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Notebook generation failed: {str(e)}")

@router.post("/execute-dsl")
async def execute_dsl_workflow(request: DSLExecutionRequest, background_tasks: BackgroundTasks):
    """Execute a DSL workflow in the sandbox environment."""
    try:
        # Generate execution ID
        import uuid
        execution_id = str(uuid.uuid4())
        
        # Initialize execution tracking
        active_executions[execution_id] = ExecutionStatusResponse(
            execution_id=execution_id,
            status="starting",
            workflow_name=request.workflow_name
        )
        
        # Start background execution
        background_tasks.add_task(
            execute_dsl_background,
            execution_id,
            request
        )
        
        logger.info("DSL execution started", 
                   execution_id=execution_id,
                   workflow_name=request.workflow_name)
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "workflow_name": request.workflow_name,
            "message": "DSL workflow execution started in background"
        }
    
    except Exception as e:
        logger.error("Failed to start DSL execution", 
                    workflow_name=request.workflow_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Execution start failed: {str(e)}")

async def execute_dsl_background(execution_id: str, request: DSLExecutionRequest):
    """Background task for DSL workflow execution."""
    try:
        # Update status
        active_executions[execution_id].status = "generating_notebook"
        
        async with SandboxManager() as sandbox:
            # Execute DSL workflow
            result = await sandbox.execute_dsl_workflow(
                request.dsl_content,
                request.workflow_name
            )
            
            # Update execution status with results
            active_executions[execution_id].status = "completed"
            active_executions[execution_id].notebook_path = result["notebook_path"]
            active_executions[execution_id].validation_result = result["validation_result"]
            active_executions[execution_id].execution_result = result["execution_result"]
            
            logger.info("DSL background execution completed", 
                       execution_id=execution_id,
                       success=result.get("execution_result", {}).get("result", {}).get("success", False))
    
    except Exception as e:
        active_executions[execution_id].status = "failed"
        active_executions[execution_id].error = str(e)
        
        logger.error("DSL background execution failed", 
                    execution_id=execution_id,
                    error=str(e))

@router.get("/execution/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str):
    """Get the status of a DSL workflow execution."""
    if execution_id not in active_executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return active_executions[execution_id]

@router.get("/executions")
async def list_executions():
    """List all active DSL workflow executions."""
    return {
        "executions": list(active_executions.values()),
        "count": len(active_executions)
    }

@router.delete("/execution/{execution_id}")
async def cancel_execution(execution_id: str):
    """Cancel or remove a DSL workflow execution."""
    if execution_id not in active_executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    execution = active_executions[execution_id]
    
    # If still running, we can't actually cancel it, but we can remove from tracking
    if execution.status in ["starting", "generating_notebook", "executing"]:
        logger.warning("Cannot cancel running execution, removing from tracking", 
                      execution_id=execution_id)
    
    del active_executions[execution_id]
    
    return {"message": f"Execution {execution_id} removed from tracking"}

@router.post("/start-sandbox")
async def start_sandbox():
    """Start the sandbox container."""
    try:
        async with SandboxManager() as sandbox:
            success = await sandbox.start_sandbox()
            
            if success:
                return {"status": "started", "message": "Sandbox container started successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to start sandbox container")
    
    except Exception as e:
        logger.error("Failed to start sandbox", error=str(e))
        raise HTTPException(status_code=500, detail=f"Sandbox start failed: {str(e)}")

@router.post("/stop-sandbox")
async def stop_sandbox():
    """Stop the sandbox container."""
    try:
        async with SandboxManager() as sandbox:
            success = await sandbox.stop_sandbox()
            
            if success:
                return {"status": "stopped", "message": "Sandbox container stopped successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to stop sandbox container")
    
    except Exception as e:
        logger.error("Failed to stop sandbox", error=str(e))
        raise HTTPException(status_code=500, detail=f"Sandbox stop failed: {str(e)}")

@router.get("/notebooks")
async def list_sandbox_notebooks():
    """List all notebooks in the sandbox."""
    try:
        async with SandboxManager() as sandbox:
            result = await sandbox.list_notebooks()
            return result
    
    except Exception as e:
        logger.error("Failed to list sandbox notebooks", error=str(e))
        raise HTTPException(status_code=500, detail=f"List notebooks failed: {str(e)}")

@router.delete("/notebooks/{notebook_path}")
async def delete_sandbox_notebook(notebook_path: str):
    """Delete a notebook from the sandbox."""
    try:
        async with SandboxManager() as sandbox:
            success = await sandbox.delete_notebook(notebook_path)
            
            if success:
                return {"message": f"Notebook '{notebook_path}' deleted successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to delete notebook")
    
    except Exception as e:
        logger.error("Failed to delete sandbox notebook", 
                    notebook_path=notebook_path,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Delete notebook failed: {str(e)}")

# Include this router in the main FastAPI app
def include_sandbox_routes(app):
    """Include sandbox routes in the main FastAPI application."""
    app.include_router(router)