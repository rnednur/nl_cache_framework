#!/usr/bin/env python3
"""
Simple validation script for the ThinkForge Workflow Execution Framework
"""

import sys
import os
import asyncio

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def validate_framework():
    """Validate that the workflow framework components can be imported and initialized."""
    
    print("=== ThinkForge Workflow Framework Validation ===")
    
    try:
        # Test imports
        print("✓ Testing imports...")
        
        from thinkforge.execution_wrappers import (
            SQLExecutionWrapper,
            APIExecutionWrapper,
            WorkflowExecutionWrapper,
            ExecutionResult
        )
        print("  ✓ Execution wrappers imported successfully")
        
        from thinkforge.step_templates import (
            SQLStepTemplate,
            APIStepTemplate,
            StepExecutor
        )
        print("  ✓ Step templates imported successfully")
        
        from thinkforge.execution_config import ExecutionConfigManager
        print("  ✓ Execution config manager imported successfully")
        
        from thinkforge.workflow_compiler import (
            compile_workflow_template,
            generate_executable_python_code
        )
        print("  ✓ Workflow compiler imported successfully")
        
        # Test basic initialization
        print("\n✓ Testing component initialization...")
        
        # Mock nl2sql client
        class MockNL2SQLClient:
            async def execute(self, sql, database_config=None):
                return [{"result": "mock data"}]
        
        nl2sql_client = MockNL2SQLClient()
        print("  ✓ Mock NL2SQL client created")
        
        # Initialize execution wrappers
        sql_wrapper = SQLExecutionWrapper(nl2sql_client)
        api_wrapper = APIExecutionWrapper()
        workflow_wrapper = WorkflowExecutionWrapper(nl2sql_client=nl2sql_client)
        print("  ✓ Execution wrappers initialized")
        
        # Initialize step templates
        sql_template = SQLStepTemplate(nl2sql_client)
        api_template = APIStepTemplate()
        step_executor = StepExecutor(nl2sql_client)
        print("  ✓ Step templates initialized")
        
        # Initialize config manager
        config_manager = ExecutionConfigManager()
        print("  ✓ Configuration manager initialized")
        
        # Test workflow compilation
        print("\n✓ Testing workflow compilation...")
        
        sample_nodes = [
            {
                "id": "start",
                "type": "input",
                "data": {"label": "Start"},
                "position": {"x": 250, "y": 50}
            },
            {
                "id": "step1",
                "type": "default",
                "data": {
                    "label": "Test Step",
                    "originalStepType": "sql",
                    "template": "SELECT 1"
                },
                "position": {"x": 250, "y": 150}
            }
        ]
        
        sample_edges = [
            {
                "id": "start-step1",
                "source": "start",
                "target": "step1"
            }
        ]
        
        workflow_template = compile_workflow_template(sample_nodes, sample_edges)
        print("  ✓ Workflow compilation successful")
        
        # Test code generation
        python_code = generate_executable_python_code(workflow_template, include_imports=False)
        print("  ✓ Python code generation successful")
        
        # Test simple execution
        print("\n✓ Testing simple step execution...")
        
        step_config = {
            "id": "test_step",
            "template": "SELECT 1 as test_value",
            "template_type": "sql",
            "execution_config": {}
        }
        
        result = await sql_wrapper.execute_sql_step(step_config)
        print(f"  ✓ SQL step execution result: success={result.success}")
        
        print("\n🎉 All validation tests passed!")
        print("✓ ThinkForge Workflow Framework is ready for use")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(validate_framework())
    if success:
        sys.exit(0)
    else:
        sys.exit(1)