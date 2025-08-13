#!/usr/bin/env python3
"""
Basic usage example for notebook-sandbox package.
Demonstrates core functionality without wrapper services.
"""

import asyncio
import json
from pathlib import Path

from notebook_sandbox import (
    NotebookExecutor,
    PythonNotebookGenerator,
    MockToolResolver,
    ResourceConfig,
    SecurityConfig
)
from notebook_sandbox.generators.base_generator import GenerationRequest, NotebookMetadata

async def main():
    """Basic usage demonstration."""
    
    print("🚀 Notebook Sandbox - Basic Usage Example")
    print("=" * 50)
    
    # 1. Setup configuration
    print("\n1. Setting up configuration...")
    
    resource_config = ResourceConfig(
        max_memory_mb=256,
        max_cpu_time=60,
        max_wall_time=120
    )
    
    security_config = SecurityConfig(
        strict_mode=True,
        allow_network_access=False,
        allow_file_system_access=False
    )
    
    print(f"   ✓ Resource limits: {resource_config.max_memory_mb}MB memory, {resource_config.max_cpu_time}s CPU")
    print(f"   ✓ Security: strict_mode={security_config.strict_mode}")
    
    # 2. Initialize components
    print("\n2. Initializing components...")
    
    # Setup paths
    base_dir = Path("/tmp/notebook-sandbox-demo")
    notebook_dir = base_dir / "notebooks"
    output_dir = base_dir / "output"
    
    notebook_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize executor
    executor = NotebookExecutor(
        notebook_dir=notebook_dir,
        output_dir=output_dir,
        resource_config=resource_config,
        security_config=security_config
    )
    
    # Initialize generator with mock tool resolver
    tool_resolver = MockToolResolver()
    generator = PythonNotebookGenerator(tool_resolver=tool_resolver)
    
    print(f"   ✓ Notebook directory: {notebook_dir}")
    print(f"   ✓ Output directory: {output_dir}")
    print(f"   ✓ Tool resolver: {type(tool_resolver).__name__}")
    
    # 3. Generate a notebook from workflow description
    print("\n3. Generating notebook from workflow...")
    
    # Define a simple workflow
    workflow_content = {
        "steps": [
            {
                "id": "step_1",
                "name": "Load Data",
                "description": "Load customer data from CSV file",
                "type": "data_load"
            },
            {
                "id": "step_2", 
                "name": "Data Analysis",
                "description": "Analyze customer data and generate statistics",
                "type": "analysis"
            },
            {
                "id": "step_3",
                "name": "Generate Report",
                "description": "Create summary report with visualizations",
                "type": "reporting"
            }
        ]
    }
    
    # Create generation request
    metadata = NotebookMetadata(
        title="Customer Data Analysis",
        description="Automated analysis of customer data with reporting",
        tags=["analysis", "reporting", "demo"]
    )
    
    request = GenerationRequest(
        content=workflow_content,
        workflow_name="customer_analysis",
        metadata=metadata
    )
    
    # Generate notebook
    result = await generator.generate(request)
    
    if result.success:
        print(f"   ✓ Notebook generated successfully")
        print(f"   ✓ Cell count: {result.cell_count}")
        print(f"   ✓ Warnings: {len(result.warnings)}")
        
        # Save the generated notebook
        notebook_filename = "customer_analysis_demo.ipynb"
        notebook_path = notebook_dir / notebook_filename
        
        with open(notebook_path, 'w', encoding='utf-8') as f:
            f.write(result.notebook_content)
        
        print(f"   ✓ Saved to: {notebook_path}")
    else:
        print(f"   ❌ Generation failed: {result.error}")
        return
    
    # 4. Validate the generated notebook
    print("\n4. Validating notebook...")
    
    validation_result = executor.validate_notebook(notebook_filename)
    
    if validation_result["valid"]:
        print(f"   ✓ Validation passed")
        print(f"   ✓ No security issues found")
    else:
        print(f"   ⚠️ Validation issues: {validation_result['issue_count']}")
        for issue in validation_result["issues"][:3]:  # Show first 3 issues
            print(f"      - {issue['severity'].upper()}: {issue['message']}")
    
    # 5. Create a simple test notebook
    print("\n5. Creating simple test notebook...")
    
    simple_notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Simple Test Notebook\n", "\n", "This is a basic test to verify execution works."]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Simple calculation\n",
                    "import math\n",
                    "\n",
                    "result = math.sqrt(16)\n",
                    "print(f'Square root of 16 is: {result}')\n",
                    "\n",
                    "# Create some data\n",
                    "data = [1, 2, 3, 4, 5]\n",
                    "squared = [x**2 for x in data]\n",
                    "print(f'Original: {data}')\n",
                    "print(f'Squared: {squared}')"
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }
    
    # Save simple notebook
    simple_filename = "simple_test.ipynb"
    simple_path = notebook_dir / simple_filename
    
    with open(simple_path, 'w', encoding='utf-8') as f:
        json.dump(simple_notebook, f, indent=2)
    
    print(f"   ✓ Created: {simple_path}")
    
    # 6. Execute the simple notebook
    print("\n6. Executing simple test notebook...")
    
    try:
        execution_result = executor.execute_notebook(simple_filename, validate_first=True)
        
        if execution_result.success:
            print(f"   ✓ Execution completed successfully")
            print(f"   ✓ Execution time: {execution_result.execution_time:.2f}s")
            print(f"   ✓ Cells executed: {execution_result.cells_executed}")
            print(f"   ✓ Output saved to: {execution_result.output_path}")
        else:
            print(f"   ❌ Execution failed: {execution_result.error}")
    
    except Exception as e:
        print(f"   ❌ Execution error: {str(e)}")
    
    # 7. List all notebooks
    print("\n7. Listing all notebooks...")
    
    notebooks = executor.list_notebooks()
    print(f"   ✓ Found {len(notebooks)} notebooks:")
    
    for notebook in notebooks:
        print(f"      - {notebook['filename']} ({notebook['size']} bytes)")
    
    print("\n✅ Basic usage example completed!")
    print(f"\nFiles created in: {base_dir}")
    print("You can inspect the generated notebooks and outputs.")

if __name__ == "__main__":
    asyncio.run(main())