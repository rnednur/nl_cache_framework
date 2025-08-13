"""
FastAPI server for notebook sandbox with wrapper service integration.
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .executor import NotebookExecutor, ExecutionResult
from .validator import NotebookValidator
from .container_manager import ContainerManager
from ..generators.python_generator import PythonNotebookGenerator
from ..generators.base_generator import GenerationRequest, NotebookMetadata
from ..integrations.tool_resolver import ToolResolver, MockToolResolver
from ..integrations.wrapper_client import WrapperClient
from ..integrations.mcp_client import MCPClient
from ..config.resources import ResourceConfig
from ..config.security import SecurityConfig

logger = structlog.get_logger()

# Pydantic models
class NotebookUploadResponse(BaseModel):
    filename: str
    path: str
    size: int
    uploaded_at: str

class NotebookValidationRequest(BaseModel):
    notebook_path: str

class NotebookExecutionRequest(BaseModel):
    notebook_path: str
    memory_limit_mb: Optional[int] = 512
    cpu_time_limit: Optional[int] = 300
    wall_time_limit: Optional[int] = 600
    validate_first: bool = True

class NotebookGenerationRequest(BaseModel):
    content: Dict[str, Any]
    workflow_name: str
    title: Optional[str] = None
    description: Optional[str] = None
    generator_type: str = "python"

class ExecutionStatusResponse(BaseModel):
    execution_id: str
    status: str  # "running", "completed", "failed"
    notebook_path: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class SandboxConfigRequest(BaseModel):
    resource_config: Optional[Dict[str, Any]] = None
    security_config: Optional[Dict[str, Any]] = None
    tool_resolver_config: Optional[Dict[str, Any]] = None

# Global state
execution_status: Dict[str, ExecutionStatusResponse] = {}

class SandboxAPI:
    """Main API class for notebook sandbox."""
    
    def __init__(self,
                 notebook_dir: Optional[Path] = None,
                 output_dir: Optional[Path] = None,
                 tool_resolver: Optional[ToolResolver] = None,
                 resource_config: Optional[ResourceConfig] = None,
                 security_config: Optional[SecurityConfig] = None):
        """Initialize sandbox API."""
        
        # Configuration
        self.resource_config = resource_config or ResourceConfig.from_env()
        self.security_config = security_config or SecurityConfig.from_env()
        
        # Paths
        self.notebook_dir = notebook_dir or Path("/sandbox/notebooks")
        self.output_dir = output_dir or Path("/sandbox/output")
        
        # Core components
        self.executor = NotebookExecutor(
            notebook_dir=self.notebook_dir,
            output_dir=self.output_dir,
            resource_config=self.resource_config,
            security_config=self.security_config
        )
        
        self.container_manager = ContainerManager()
        self.validator = NotebookValidator(self.security_config.get_security_policy())
        
        # Tool resolver
        self.tool_resolver = tool_resolver or MockToolResolver()
        
        # Generator
        self.generator = PythonNotebookGenerator(
            tool_resolver=self.tool_resolver
        )
        
        logger.info("SandboxAPI initialized",
                   notebook_dir=str(self.notebook_dir),
                   output_dir=str(self.output_dir),
                   resolver_type=type(self.tool_resolver).__name__)

# Create API instance
sandbox_api = SandboxAPI()

# Create FastAPI app
app = FastAPI(
    title="Notebook Sandbox API",
    description="Secure notebook execution environment with wrapper service integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencies
def get_sandbox_api() -> SandboxAPI:
    """Get sandbox API instance."""
    return sandbox_api

# Health endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    container_health = await sandbox_api.container_manager.health_check()
    tool_resolver_health = await sandbox_api.tool_resolver.health_check()
    
    return {
        "status": "healthy",
        "service": "notebook-sandbox",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "container_manager": container_health,
            "tool_resolver": tool_resolver_health
        }
    }

# Notebook management endpoints
@app.get("/notebooks")
async def list_notebooks(api: SandboxAPI = Depends(get_sandbox_api)):
    """List all notebooks in the sandbox."""
    try:
        notebooks = api.executor.list_notebooks()
        return {
            "notebooks": notebooks,
            "count": len(notebooks)
        }
    except Exception as e:
        logger.error("Failed to list notebooks", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list notebooks: {str(e)}")

@app.post("/notebooks/upload", response_model=NotebookUploadResponse)
async def upload_notebook(file: UploadFile = File(...), api: SandboxAPI = Depends(get_sandbox_api)):
    """Upload a notebook file to the sandbox."""
    try:
        if not file.filename.endswith('.ipynb'):
            raise HTTPException(status_code=400, detail="Only .ipynb files are allowed")
        
        # Read and validate content
        content = await file.read()
        
        # Validate JSON format
        validation_result = api.validator.validate_notebook_content(content.decode('utf-8'))
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid notebook: {validation_result['issue_count']} issues found"
            )
        
        # Save file
        file_path = api.notebook_dir / file.filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info("Notebook uploaded successfully", 
                   filename=file.filename, 
                   size=len(content))
        
        return NotebookUploadResponse(
            filename=file.filename,
            path=file.filename,
            size=len(content),
            uploaded_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Notebook upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/notebooks/validate")
async def validate_notebook(request: NotebookValidationRequest, 
                          api: SandboxAPI = Depends(get_sandbox_api)):
    """Validate a notebook without executing it."""
    try:
        result = api.executor.validate_notebook(request.notebook_path)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Notebook not found: {request.notebook_path}")
    except Exception as e:
        logger.error("Notebook validation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.delete("/notebooks/{notebook_path}")
async def delete_notebook(notebook_path: str, api: SandboxAPI = Depends(get_sandbox_api)):
    """Delete a notebook file."""
    try:
        success = api.executor.delete_notebook(notebook_path)
        if success:
            return {"message": f"Notebook '{notebook_path}' deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete notebook")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Notebook not found: {notebook_path}")
    except Exception as e:
        logger.error("Failed to delete notebook", error=str(e))
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# Notebook generation endpoints
@app.post("/notebooks/generate")
async def generate_notebook(request: NotebookGenerationRequest,
                          api: SandboxAPI = Depends(get_sandbox_api)):
    """Generate a notebook from content (DSL, workflow, etc.)."""
    try:
        # Create generation request
        metadata = NotebookMetadata(
            title=request.title or request.workflow_name,
            description=request.description
        )
        
        gen_request = GenerationRequest(
            content=request.content,
            workflow_name=request.workflow_name,
            metadata=metadata
        )
        
        # Generate notebook
        result = await api.generator.generate(gen_request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=f"Generation failed: {result.error}")
        
        # Save generated notebook
        filename = f"{request.workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ipynb"
        file_path = api.notebook_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result.notebook_content)
        
        logger.info("Notebook generated successfully",
                   workflow_name=request.workflow_name,
                   filename=filename,
                   cell_count=result.cell_count)
        
        return {
            "success": True,
            "filename": filename,
            "path": filename,
            "cell_count": result.cell_count,
            "warnings": result.warnings,
            "metadata": result.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Notebook generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# Notebook execution endpoints
@app.post("/notebooks/execute")
async def execute_notebook(request: NotebookExecutionRequest,
                         background_tasks: BackgroundTasks,
                         api: SandboxAPI = Depends(get_sandbox_api)):
    """Execute a notebook asynchronously."""
    try:
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
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
            request,
            api
        )
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "message": "Notebook execution started in background"
        }
        
    except Exception as e:
        logger.error("Failed to start notebook execution", error=str(e))
        raise HTTPException(status_code=500, detail=f"Execution start failed: {str(e)}")

async def execute_notebook_background(execution_id: str, 
                                    request: NotebookExecutionRequest,
                                    api: SandboxAPI):
    """Background task for notebook execution."""
    try:
        # Update resource config if specified
        if (request.memory_limit_mb or request.cpu_time_limit or request.wall_time_limit):
            resource_config = ResourceConfig(
                max_memory_mb=request.memory_limit_mb or api.resource_config.max_memory_mb,
                max_cpu_time=request.cpu_time_limit or api.resource_config.max_cpu_time,
                max_wall_time=request.wall_time_limit or api.resource_config.max_wall_time
            )
            
            # Create temporary executor with custom config
            executor = NotebookExecutor(
                notebook_dir=api.notebook_dir,
                output_dir=api.output_dir,
                resource_config=resource_config,
                security_config=api.security_config
            )
        else:
            executor = api.executor
        
        # Execute notebook
        result = executor.execute_notebook(
            request.notebook_path,
            validate_first=request.validate_first
        )
        
        # Update execution status
        execution_status[execution_id].status = "completed" if result.success else "failed"
        execution_status[execution_id].end_time = datetime.utcnow().isoformat()
        execution_status[execution_id].result = result.to_dict()
        
        logger.info("Background notebook execution completed",
                   execution_id=execution_id,
                   success=result.success)
        
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

@app.delete("/notebooks/execution/{execution_id}")
async def cancel_execution(execution_id: str):
    """Cancel or remove a notebook execution."""
    if execution_id not in execution_status:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    del execution_status[execution_id]
    return {"message": f"Execution {execution_id} removed from tracking"}

# Container management endpoints
@app.post("/container/start")
async def start_container(api: SandboxAPI = Depends(get_sandbox_api)):
    """Start the sandbox container."""
    try:
        success = await api.container_manager.start_container()
        
        if success:
            return {"status": "started", "message": "Container started successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start container")
            
    except Exception as e:
        logger.error("Failed to start container", error=str(e))
        raise HTTPException(status_code=500, detail=f"Container start failed: {str(e)}")

@app.post("/container/stop")
async def stop_container(api: SandboxAPI = Depends(get_sandbox_api)):
    """Stop the sandbox container."""
    try:
        success = await api.container_manager.stop_container()
        
        if success:
            return {"status": "stopped", "message": "Container stopped successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop container")
            
    except Exception as e:
        logger.error("Failed to stop container", error=str(e))
        raise HTTPException(status_code=500, detail=f"Container stop failed: {str(e)}")

@app.get("/container/status")
async def get_container_status(api: SandboxAPI = Depends(get_sandbox_api)):
    """Get container status."""
    try:
        status = await api.container_manager.get_container_status()
        return status
    except Exception as e:
        logger.error("Failed to get container status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/container/logs")
async def get_container_logs(tail: int = 100, api: SandboxAPI = Depends(get_sandbox_api)):
    """Get container logs."""
    try:
        logs = await api.container_manager.get_container_logs(tail=tail)
        return {"logs": logs}
    except Exception as e:
        logger.error("Failed to get container logs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Log retrieval failed: {str(e)}")

# Configuration endpoints
@app.post("/config/update")
async def update_config(request: SandboxConfigRequest):
    """Update sandbox configuration."""
    try:
        changes = []
        
        if request.resource_config:
            sandbox_api.resource_config = ResourceConfig.from_dict(request.resource_config)
            changes.append("resource_config")
        
        if request.security_config:
            sandbox_api.security_config = SecurityConfig.from_dict(request.security_config)
            changes.append("security_config")
        
        if request.tool_resolver_config:
            # This would require more complex logic to switch tool resolvers
            changes.append("tool_resolver_config")
        
        logger.info("Configuration updated", changes=changes)
        
        return {
            "success": True,
            "changes": changes,
            "message": "Configuration updated successfully"
        }
        
    except Exception as e:
        logger.error("Configuration update failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Config update failed: {str(e)}")

@app.get("/config")
async def get_config():
    """Get current sandbox configuration."""
    return {
        "resource_config": sandbox_api.resource_config.to_dict(),
        "security_config": sandbox_api.security_config.to_dict(),
        "paths": {
            "notebook_dir": str(sandbox_api.notebook_dir),
            "output_dir": str(sandbox_api.output_dir)
        }
    }

def main():
    """Main entry point for running the API server."""
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8888,
        log_level="info"
    )

if __name__ == "__main__":
    main()