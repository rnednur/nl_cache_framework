#!/usr/bin/env python3
"""
API server for notebook sandbox environment.
Provides REST endpoints for notebook execution and management.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

from run_notebook import NotebookExecutor

# Configure structured logging
logger = structlog.get_logger()

app = FastAPI(
    title="ThinkForge Notebook Sandbox API",
    description="Secure notebook execution environment for ThinkForge workflows",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global notebook executor
executor = NotebookExecutor()

# Pydantic models
class NotebookValidationRequest(BaseModel):
    notebook_path: str

class NotebookExecutionRequest(BaseModel):
    notebook_path: str
    memory_limit_mb: Optional[int] = 512
    cpu_time_limit: Optional[int] = 300
    wall_time_limit: Optional[int] = 600

class NotebookUploadResponse(BaseModel):
    filename: str
    path: str
    size: int
    uploaded_at: str

class NotebookListResponse(BaseModel):
    notebooks: List[Dict[str, Any]]
    count: int

class ExecutionStatusResponse(BaseModel):
    execution_id: str
    status: str  # "running", "completed", "failed"
    notebook_path: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

# In-memory execution tracking
execution_status: Dict[str, ExecutionStatusResponse] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "notebook-sandbox",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/notebooks", response_model=NotebookListResponse)
async def list_notebooks():
    """List all available notebooks in the sandbox."""
    try:
        notebook_dir = Path("/sandbox/notebooks")
        notebooks = []
        
        if notebook_dir.exists():
            for notebook_file in notebook_dir.glob("*.ipynb"):
                stat = notebook_file.stat()
                notebooks.append({
                    "filename": notebook_file.name,
                    "path": str(notebook_file.relative_to(notebook_dir)),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        return NotebookListResponse(notebooks=notebooks, count=len(notebooks))
    
    except Exception as e:
        logger.error("Failed to list notebooks", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list notebooks: {str(e)}")

@app.post("/notebooks/upload", response_model=NotebookUploadResponse)
async def upload_notebook(file: UploadFile = File(...)):
    """Upload a notebook file to the sandbox."""
    try:
        if not file.filename.endswith('.ipynb'):
            raise HTTPException(status_code=400, detail="Only .ipynb files are allowed")
        
        notebook_dir = Path("/sandbox/notebooks")
        notebook_dir.mkdir(exist_ok=True)
        
        file_path = notebook_dir / file.filename
        
        # Read and validate the notebook content
        content = await file.read()
        try:
            notebook_data = json.loads(content.decode('utf-8'))
            if "cells" not in notebook_data:
                raise HTTPException(status_code=400, detail="Invalid notebook format: missing 'cells' key")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info("Notebook uploaded successfully", filename=file.filename, size=len(content))
        
        return NotebookUploadResponse(
            filename=file.filename,
            path=str(file_path.relative_to(notebook_dir)),
            size=len(content),
            uploaded_at=datetime.utcnow().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload notebook", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/notebooks/validate")
async def validate_notebook(request: NotebookValidationRequest):
    """Validate a notebook without executing it."""
    try:
        validation_result = executor.validate_notebook(request.notebook_path)
        return validation_result
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Notebook not found: {request.notebook_path}")
    except Exception as e:
        logger.error("Notebook validation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.post("/notebooks/execute")
async def execute_notebook(request: NotebookExecutionRequest, background_tasks: BackgroundTasks):
    """Execute a notebook asynchronously."""
    try:
        # Generate execution ID
        execution_id = f"exec_{int(datetime.utcnow().timestamp())}"
        
        # Initialize execution status
        execution_status[execution_id] = ExecutionStatusResponse(
            execution_id=execution_id,
            status="running",
            notebook_path=request.notebook_path,
            start_time=datetime.utcnow().isoformat()
        )
        
        # Start background execution
        background_tasks.add_task(
            execute_notebook_background,
            execution_id,
            request
        )
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "message": "Notebook execution started in background"
        }
    
    except Exception as e:
        logger.error("Failed to start notebook execution", error=str(e))
        raise HTTPException(status_code=500, detail=f"Execution start failed: {str(e)}")

async def execute_notebook_background(execution_id: str, request: NotebookExecutionRequest):
    """Background task for notebook execution."""
    try:
        # Create executor with custom limits if provided
        custom_executor = NotebookExecutor(
            max_memory_mb=request.memory_limit_mb,
            max_cpu_time=request.cpu_time_limit,
            max_wall_time=request.wall_time_limit
        )
        
        # Execute notebook
        result = custom_executor.execute_notebook(request.notebook_path)
        
        # Update execution status
        execution_status[execution_id].status = "completed" if result["success"] else "failed"
        execution_status[execution_id].end_time = datetime.utcnow().isoformat()
        execution_status[execution_id].result = result
        
        logger.info("Background notebook execution completed", 
                   execution_id=execution_id,
                   success=result["success"])
    
    except Exception as e:
        execution_status[execution_id].status = "failed"
        execution_status[execution_id].end_time = datetime.utcnow().isoformat()
        execution_status[execution_id].result = {"error": str(e)}
        
        logger.error("Background notebook execution failed", 
                    execution_id=execution_id,
                    error=str(e))

@app.get("/notebooks/execution/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str):
    """Get the status of a notebook execution."""
    if execution_id not in execution_status:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return execution_status[execution_id]

@app.get("/notebooks/executions")
async def list_executions():
    """List all execution statuses."""
    return {
        "executions": list(execution_status.values()),
        "count": len(execution_status)
    }

@app.delete("/notebooks/{notebook_path}")
async def delete_notebook(notebook_path: str):
    """Delete a notebook file."""
    try:
        notebook_dir = Path("/sandbox/notebooks")
        file_path = notebook_dir / notebook_path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Notebook not found: {notebook_path}")
        
        if not file_path.is_file() or not file_path.suffix == '.ipynb':
            raise HTTPException(status_code=400, detail="Invalid notebook file")
        
        file_path.unlink()
        
        logger.info("Notebook deleted successfully", notebook_path=notebook_path)
        
        return {"message": f"Notebook '{notebook_path}' deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete notebook", error=str(e))
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@app.get("/outputs")
async def list_outputs():
    """List all execution output files."""
    try:
        output_dir = Path("/sandbox/output")
        outputs = []
        
        if output_dir.exists():
            for output_file in output_dir.glob("*"):
                if output_file.is_file():
                    stat = output_file.stat()
                    outputs.append({
                        "filename": output_file.name,
                        "path": str(output_file.relative_to(output_dir)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return {"outputs": outputs, "count": len(outputs)}
    
    except Exception as e:
        logger.error("Failed to list outputs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list outputs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Start the API server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8888,
        log_level="info"
    )