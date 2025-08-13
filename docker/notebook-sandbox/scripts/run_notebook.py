#!/usr/bin/env python3
"""
Secure notebook execution runner for ThinkForge sandbox environment.
Handles execution of generated notebooks with proper resource constraints.
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

# Configure structured logging
logger = structlog.get_logger()

class NotebookExecutor:
    """Secure notebook execution with resource limits and timeout controls."""
    
    def __init__(self, 
                 max_memory_mb: int = 512,
                 max_cpu_time: int = 300,
                 max_wall_time: int = 600,
                 max_file_size_mb: int = 100):
        """Initialize executor with resource constraints."""
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        self.max_wall_time = max_wall_time
        self.max_file_size_mb = max_file_size_mb
        
        # Setup paths
        self.notebook_dir = Path("/sandbox/notebooks")
        self.output_dir = Path("/sandbox/output")
        
        # Ensure directories exist
        self.notebook_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("NotebookExecutor initialized", 
                   max_memory_mb=max_memory_mb,
                   max_cpu_time=max_cpu_time,
                   max_wall_time=max_wall_time)
    
    def set_resource_limits(self):
        """Set process resource limits for security."""
        try:
            # Memory limit (virtual memory)
            memory_limit = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time))
            
            # File size limit
            file_size_limit = self.max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_limit, file_size_limit))
            
            # Process limit
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            
            logger.info("Resource limits set successfully")
            
        except Exception as e:
            logger.error("Failed to set resource limits", error=str(e))
            raise
    
    def execute_notebook(self, notebook_path: str) -> Dict[str, Any]:
        """Execute a notebook file and return results."""
        notebook_file = self.notebook_dir / notebook_path
        
        if not notebook_file.exists():
            raise FileNotFoundError(f"Notebook not found: {notebook_path}")
        
        # Generate output filename
        output_name = f"{notebook_file.stem}_executed.ipynb"
        output_file = self.output_dir / output_name
        
        # Setup execution command
        cmd = [
            "jupyter", "nbconvert",
            "--to", "notebook",
            "--execute",
            "--inplace" if self.output_dir == self.notebook_dir else "--output",
            str(output_file) if self.output_dir != self.notebook_dir else str(notebook_file),
            str(notebook_file),
            "--ExecutePreprocessor.timeout={}".format(self.max_wall_time),
            "--ExecutePreprocessor.kernel_name=python3"
        ]
        
        start_time = time.time()
        execution_result = {
            "notebook_path": notebook_path,
            "output_path": str(output_file),
            "start_time": start_time,
            "success": False,
            "error": None,
            "execution_time": 0,
            "cells_executed": 0,
            "cells_failed": 0
        }
        
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
                stdout, stderr = process.communicate(timeout=self.max_wall_time)
                return_code = process.returncode
                
                execution_result["execution_time"] = time.time() - start_time
                
                if return_code == 0:
                    execution_result["success"] = True
                    logger.info("Notebook executed successfully", 
                              notebook=notebook_path,
                              execution_time=execution_result["execution_time"])
                else:
                    execution_result["error"] = f"Execution failed with code {return_code}: {stderr}"
                    logger.error("Notebook execution failed", 
                               notebook=notebook_path,
                               return_code=return_code,
                               stderr=stderr)
                
            except subprocess.TimeoutExpired:
                process.kill()
                execution_result["error"] = f"Execution timeout after {self.max_wall_time} seconds"
                logger.error("Notebook execution timeout", 
                           notebook=notebook_path,
                           timeout=self.max_wall_time)
        
        except Exception as e:
            execution_result["error"] = f"Execution error: {str(e)}"
            logger.error("Notebook execution exception", 
                        notebook=notebook_path,
                        error=str(e))
        
        return execution_result
    
    def validate_notebook(self, notebook_path: str) -> Dict[str, Any]:
        """Validate notebook structure and syntax before execution."""
        notebook_file = self.notebook_dir / notebook_path
        
        validation_result = {
            "notebook_path": notebook_path,
            "valid": False,
            "issues": [],
            "cell_count": 0,
            "code_cells": 0,
            "markdown_cells": 0
        }
        
        try:
            with open(notebook_file, 'r', encoding='utf-8') as f:
                notebook_data = json.load(f)
            
            # Basic structure validation
            if "cells" not in notebook_data:
                validation_result["issues"].append("Missing 'cells' key in notebook")
                return validation_result
            
            cells = notebook_data["cells"]
            validation_result["cell_count"] = len(cells)
            
            for i, cell in enumerate(cells):
                if "cell_type" not in cell:
                    validation_result["issues"].append(f"Cell {i} missing 'cell_type'")
                    continue
                
                cell_type = cell["cell_type"]
                if cell_type == "code":
                    validation_result["code_cells"] += 1
                elif cell_type == "markdown":
                    validation_result["markdown_cells"] += 1
                
                # Validate cell source
                if "source" not in cell:
                    validation_result["issues"].append(f"Cell {i} missing 'source'")
            
            # Check for security concerns in code cells
            for i, cell in enumerate(cells):
                if cell.get("cell_type") == "code":
                    source = "".join(cell.get("source", []))
                    
                    # Basic security checks
                    dangerous_patterns = [
                        "import os", "subprocess", "eval(", "exec(",
                        "__import__", "open(", "file(", "input(",
                        "raw_input(", "import sys"
                    ]
                    
                    for pattern in dangerous_patterns:
                        if pattern in source:
                            validation_result["issues"].append(
                                f"Cell {i} contains potentially unsafe code: {pattern}"
                            )
            
            if len(validation_result["issues"]) == 0:
                validation_result["valid"] = True
                logger.info("Notebook validation passed", 
                          notebook=notebook_path,
                          cells=validation_result["cell_count"])
            else:
                logger.warning("Notebook validation failed", 
                             notebook=notebook_path,
                             issues=validation_result["issues"])
        
        except json.JSONDecodeError as e:
            validation_result["issues"].append(f"Invalid JSON format: {str(e)}")
            logger.error("Notebook JSON parsing failed", 
                        notebook=notebook_path,
                        error=str(e))
        except Exception as e:
            validation_result["issues"].append(f"Validation error: {str(e)}")
            logger.error("Notebook validation exception", 
                        notebook=notebook_path,
                        error=str(e))
        
        return validation_result

def main():
    """Main execution entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ThinkForge Notebook Sandbox Executor")
    parser.add_argument("--notebook", "-n", help="Notebook file to execute")
    parser.add_argument("--validate-only", "-v", action="store_true", 
                       help="Only validate, don't execute")
    parser.add_argument("--memory-limit", "-m", type=int, default=512,
                       help="Memory limit in MB (default: 512)")
    parser.add_argument("--cpu-time", "-c", type=int, default=300,
                       help="CPU time limit in seconds (default: 300)")
    parser.add_argument("--wall-time", "-w", type=int, default=600,
                       help="Wall time limit in seconds (default: 600)")
    
    args = parser.parse_args()
    
    # Initialize executor
    executor = NotebookExecutor(
        max_memory_mb=args.memory_limit,
        max_cpu_time=args.cpu_time,
        max_wall_time=args.wall_time
    )
    
    if args.notebook:
        # Validate notebook
        validation_result = executor.validate_notebook(args.notebook)
        print(json.dumps(validation_result, indent=2))
        
        if not validation_result["valid"]:
            logger.error("Notebook validation failed, skipping execution")
            sys.exit(1)
        
        if not args.validate_only:
            # Execute notebook
            execution_result = executor.execute_notebook(args.notebook)
            print(json.dumps(execution_result, indent=2))
            
            if not execution_result["success"]:
                sys.exit(1)
    else:
        # Start Jupyter Lab server for interactive use
        logger.info("Starting Jupyter Lab server")
        cmd = [
            "jupyter", "lab",
            "--ip=0.0.0.0",
            "--port=8888",
            "--no-browser",
            "--allow-root",
            "--notebook-dir=/sandbox/notebooks",
            "--ServerApp.token=''",
            "--ServerApp.password=''",
            "--ServerApp.allow_origin='*'",
            "--ServerApp.disable_check_xsrf=True"
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            logger.info("Jupyter Lab server stopped")
        except Exception as e:
            logger.error("Failed to start Jupyter Lab", error=str(e))
            sys.exit(1)

if __name__ == "__main__":
    main()