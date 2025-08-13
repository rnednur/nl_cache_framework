"""
Secure notebook execution with resource constraints.
Extracted and refactored from the original run_notebook.py.
"""

import os
import sys
import json
import time
import signal
import resource
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

from .validator import NotebookValidator
from ..config.resources import ResourceConfig
from ..config.security import SecurityConfig

logger = structlog.get_logger()

class ExecutionResult:
    """Represents the result of a notebook execution."""
    
    def __init__(self,
                 notebook_path: str,
                 success: bool = False,
                 error: Optional[str] = None,
                 execution_time: float = 0.0,
                 output_path: Optional[str] = None):
        self.notebook_path = notebook_path
        self.success = success
        self.error = error
        self.execution_time = execution_time
        self.output_path = output_path
        self.start_time = time.time()
        self.cells_executed = 0
        self.cells_failed = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "notebook_path": self.notebook_path,
            "success": self.success,
            "error": self.error,
            "execution_time": self.execution_time,
            "output_path": self.output_path,
            "start_time": self.start_time,
            "cells_executed": self.cells_executed,
            "cells_failed": self.cells_failed
        }

class NotebookExecutor:
    """Secure notebook execution with resource limits and timeout controls."""
    
    def __init__(self, 
                 notebook_dir: Optional[Path] = None,
                 output_dir: Optional[Path] = None,
                 resource_config: Optional[ResourceConfig] = None,
                 security_config: Optional[SecurityConfig] = None):
        """Initialize executor with configuration."""
        self.resource_config = resource_config or ResourceConfig()
        self.security_config = security_config or SecurityConfig()
        
        # Setup paths
        self.notebook_dir = notebook_dir or Path("/sandbox/notebooks")
        self.output_dir = output_dir or Path("/sandbox/output")
        
        # Ensure directories exist
        self.notebook_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize validator
        self.validator = NotebookValidator(self.security_config.get_security_policy())
        
        logger.info("NotebookExecutor initialized", 
                   notebook_dir=str(self.notebook_dir),
                   output_dir=str(self.output_dir),
                   resource_config=self.resource_config.to_dict())
    
    def set_resource_limits(self):
        """Set process resource limits for security."""
        try:
            # Memory limit (virtual memory)
            memory_limit = self.resource_config.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, 
                             (self.resource_config.max_cpu_time, self.resource_config.max_cpu_time))
            
            # File size limit
            file_size_limit = self.resource_config.max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_limit, file_size_limit))
            
            # Process limit
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            
            logger.info("Resource limits set successfully")
            
        except Exception as e:
            logger.error("Failed to set resource limits", error=str(e))
            raise
    
    def execute_notebook(self, notebook_path: str, validate_first: bool = True) -> ExecutionResult:
        """Execute a notebook file and return results."""
        notebook_file = self.notebook_dir / notebook_path
        
        if not notebook_file.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        # Validate notebook if requested
        if validate_first:
            validation_result = self.validator.validate_notebook(notebook_file)
            if not validation_result["valid"]:
                error_msg = f"Notebook validation failed: {validation_result['issue_count']} issues found"
                logger.error("Notebook validation failed", 
                           notebook_path=notebook_path,
                           issues=validation_result["issues"])
                return ExecutionResult(notebook_path, success=False, error=error_msg)
        
        # Generate output filename
        output_name = f"{notebook_file.stem}_executed.ipynb"
        output_file = self.output_dir / output_name
        
        # Setup execution command
        cmd = self._build_execution_command(notebook_file, output_file)
        
        start_time = time.time()
        result = ExecutionResult(notebook_path, output_path=str(output_file))
        
        try:
            logger.info("Starting notebook execution", 
                       notebook=notebook_path,
                       output=str(output_file))
            
            # Execute with timeout and resource limits
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=self.set_resource_limits
            )
            
            # Wait with timeout
            try:
                stdout, stderr = process.communicate(timeout=self.resource_config.max_wall_time)
                return_code = process.returncode
                
                result.execution_time = time.time() - start_time
                
                if return_code == 0:
                    result.success = True
                    self._analyze_execution_output(result, output_file)
                    logger.info("Notebook executed successfully", 
                              notebook=notebook_path,
                              execution_time=result.execution_time)
                else:
                    result.error = f"Execution failed with code {return_code}: {stderr}"
                    logger.error("Notebook execution failed", 
                               notebook=notebook_path,
                               return_code=return_code,
                               stderr=stderr[:1000])  # Limit error message length
                
            except subprocess.TimeoutExpired:
                process.kill()
                result.error = f"Execution timeout after {self.resource_config.max_wall_time} seconds"
                logger.error("Notebook execution timeout", 
                           notebook=notebook_path,
                           timeout=self.resource_config.max_wall_time)
        
        except Exception as e:
            result.error = f"Execution error: {str(e)}"
            logger.error("Notebook execution exception", 
                        notebook=notebook_path,
                        error=str(e))
        
        return result
    
    def _build_execution_command(self, notebook_file: Path, output_file: Path) -> list:
        """Build the jupyter nbconvert command for execution."""
        cmd = [
            "jupyter", "nbconvert",
            "--to", "notebook",
            "--execute",
            "--output", str(output_file),
            str(notebook_file),
            f"--ExecutePreprocessor.timeout={self.resource_config.max_wall_time}",
            "--ExecutePreprocessor.kernel_name=python3"
        ]
        
        # Add additional nbconvert options if configured
        if hasattr(self.resource_config, 'allow_errors') and self.resource_config.allow_errors:
            cmd.append("--allow-errors")
        
        return cmd
    
    def _analyze_execution_output(self, result: ExecutionResult, output_file: Path):
        """Analyze the executed notebook output for statistics."""
        try:
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    notebook_data = json.load(f)
                
                cells = notebook_data.get("cells", [])
                executed_cells = 0
                failed_cells = 0
                
                for cell in cells:
                    if cell.get("cell_type") == "code":
                        execution_count = cell.get("execution_count")
                        if execution_count is not None:
                            executed_cells += 1
                        
                        # Check for errors in outputs
                        outputs = cell.get("outputs", [])
                        for output in outputs:
                            if output.get("output_type") == "error":
                                failed_cells += 1
                                break
                
                result.cells_executed = executed_cells
                result.cells_failed = failed_cells
                
                logger.debug("Execution analysis completed",
                           executed_cells=executed_cells,
                           failed_cells=failed_cells)
        
        except Exception as e:
            logger.warning("Failed to analyze execution output", error=str(e))
    
    def validate_notebook(self, notebook_path: str) -> Dict[str, Any]:
        """Validate a notebook without executing it."""
        notebook_file = self.notebook_dir / notebook_path
        
        if not notebook_file.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        return self.validator.validate_notebook(notebook_file)
    
    def list_notebooks(self) -> list:
        """List all notebooks in the notebook directory."""
        notebooks = []
        for notebook_file in self.notebook_dir.glob("*.ipynb"):
            stat = notebook_file.stat()
            notebooks.append({
                "filename": notebook_file.name,
                "path": str(notebook_file.relative_to(self.notebook_dir)),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime
            })
        return notebooks
    
    def delete_notebook(self, notebook_path: str) -> bool:
        """Delete a notebook file."""
        notebook_file = self.notebook_dir / notebook_path
        
        if not notebook_file.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        if not notebook_file.is_file() or notebook_file.suffix != '.ipynb':
            raise ValueError("Invalid notebook file")
        
        try:
            notebook_file.unlink()
            logger.info("Notebook deleted", notebook_path=notebook_path)
            return True
        except Exception as e:
            logger.error("Failed to delete notebook", 
                        notebook_path=notebook_path,
                        error=str(e))
            raise

def main():
    """Command-line interface for notebook executor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure Notebook Executor")
    parser.add_argument("--notebook", "-n", required=True, 
                       help="Notebook file to execute")
    parser.add_argument("--validate-only", "-v", action="store_true", 
                       help="Only validate, don't execute")
    parser.add_argument("--memory-limit", "-m", type=int, default=512,
                       help="Memory limit in MB (default: 512)")
    parser.add_argument("--cpu-time", "-c", type=int, default=300,
                       help="CPU time limit in seconds (default: 300)")
    parser.add_argument("--wall-time", "-w", type=int, default=600,
                       help="Wall time limit in seconds (default: 600)")
    parser.add_argument("--notebook-dir", type=str, default="/sandbox/notebooks",
                       help="Notebook directory (default: /sandbox/notebooks)")
    parser.add_argument("--output-dir", type=str, default="/sandbox/output",
                       help="Output directory (default: /sandbox/output)")
    
    args = parser.parse_args()
    
    # Create resource configuration
    resource_config = ResourceConfig(
        max_memory_mb=args.memory_limit,
        max_cpu_time=args.cpu_time,
        max_wall_time=args.wall_time
    )
    
    # Initialize executor
    executor = NotebookExecutor(
        notebook_dir=Path(args.notebook_dir),
        output_dir=Path(args.output_dir),
        resource_config=resource_config
    )
    
    try:
        if args.validate_only:
            # Only validate notebook
            validation_result = executor.validate_notebook(args.notebook)
            print(json.dumps(validation_result, indent=2))
            
            if not validation_result["valid"]:
                logger.error("Notebook validation failed")
                sys.exit(1)
        else:
            # Execute notebook
            execution_result = executor.execute_notebook(args.notebook)
            print(json.dumps(execution_result.to_dict(), indent=2))
            
            if not execution_result.success:
                sys.exit(1)
    
    except Exception as e:
        logger.error("Execution failed", error=str(e))
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()