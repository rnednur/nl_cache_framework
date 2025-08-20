"""
End-to-End Workflow Execution Tests with NL2SQL Framework Integration

This module tests the complete workflow execution pipeline including:
- SQL step execution with nl2sql framework integration
- API step execution with proper authentication
- Multi-step workflow orchestration
- Error handling and progress monitoring
- Resource management and execution planning
"""

import asyncio
import pytest
import json
import logging
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import ThinkForge components
from thinkforge.execution_wrappers import (
    SQLExecutionWrapper,
    APIExecutionWrapper,
    WorkflowExecutionWrapper,
    ExecutionResult
)
from thinkforge.step_templates import (
    SQLStepTemplate,
    APIStepTemplate,
    StepExecutor
)
from thinkforge.execution_config import ExecutionConfigManager
from thinkforge.controller import Text2SQLController

logger = logging.getLogger(__name__)


class MockNL2SQLClient:
    """Mock NL2SQL client for testing."""
    
    def __init__(self):
        self.executed_queries = []
        self.mock_results = {}
        self.should_fail = False
        self.failure_message = "Mock database error"
    
    async def execute(self, sql: str, database_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Mock SQL execution."""
        self.executed_queries.append({
            "sql": sql,
            "database_config": database_config,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if self.should_fail:
            raise Exception(self.failure_message)
        
        # Return mock results based on SQL
        if "SELECT" in sql.upper():
            return self.mock_results.get("select", [
                {"id": 1, "name": "Test Data", "value": 100},
                {"id": 2, "name": "Sample Data", "value": 200}
            ])
        elif "INSERT" in sql.upper():
            return {"inserted_rows": 1, "last_insert_id": 123}
        else:
            return {"affected_rows": 1}
    
    def set_mock_result(self, query_type: str, result: Any) -> None:
        """Set mock result for a query type."""
        self.mock_results[query_type] = result


class MockThinkForgeController:
    """Mock ThinkForge controller for testing."""
    
    def __init__(self):
        self.cache_entries = {}
        self.next_id = 1
    
    def get_query_by_id(self, query_id: int) -> Optional[Dict[str, Any]]:
        """Mock cache entry retrieval."""
        return self.cache_entries.get(query_id)
    
    def add_cache_entry(self, entry: Dict[str, Any]) -> int:
        """Add a mock cache entry."""
        entry_id = self.next_id
        self.next_id += 1
        entry["id"] = entry_id
        self.cache_entries[entry_id] = entry
        return entry_id


@pytest.fixture
def mock_nl2sql_client():
    """Create a mock NL2SQL client."""
    return MockNL2SQLClient()


@pytest.fixture
def mock_controller():
    """Create a mock ThinkForge controller."""
    return MockThinkForgeController()


@pytest.fixture
def execution_config_manager():
    """Create an execution configuration manager for testing."""
    config_manager = ExecutionConfigManager()
    
    # Set up test database configuration
    config_manager.set_config(
        "database",
        {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass"
        }
    )
    
    # Set up test API configuration
    config_manager.set_config(
        "api",
        {
            "base_url": "https://api.example.com",
            "authentication": {"type": "bearer", "token": "test_token"},
            "headers": {"Content-Type": "application/json"}
        }
    )
    
    return config_manager


class TestSQLExecutionIntegration:
    """Test SQL execution integration with nl2sql framework."""
    
    @pytest.mark.asyncio
    async def test_sql_step_execution_success(self, mock_nl2sql_client, mock_controller):
        """Test successful SQL step execution."""
        # Add SQL cache entry
        cache_id = mock_controller.add_cache_entry({
            "template": "SELECT * FROM users WHERE id = {user_id}",
            "template_type": "sql",
            "is_template": True,
            "entity_replacements": {
                "user_id": {"type": "integer", "description": "User ID"}
            },
            "execution_config": {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "test_db"
                }
            }
        })
        
        # Set up SQL wrapper
        sql_wrapper = SQLExecutionWrapper(mock_nl2sql_client, mock_controller)
        
        # Execute step
        step_config = {
            "id": "sql_step_1",
            "cache_id": cache_id,
            "template_type": "sql"
        }
        
        entity_values = {"user_id": 123}
        
        result = await sql_wrapper.execute_sql_step(step_config, entity_values)
        
        # Assertions
        assert result.success is True
        assert result.template_type == "sql"
        assert result.step_id == "sql_step_1"
        assert len(mock_nl2sql_client.executed_queries) == 1
        
        executed_query = mock_nl2sql_client.executed_queries[0]
        assert "SELECT * FROM users WHERE id = 123" in executed_query["sql"]
    
    @pytest.mark.asyncio
    async def test_sql_step_execution_failure(self, mock_nl2sql_client, mock_controller):
        """Test SQL step execution with database error."""
        # Configure client to fail
        mock_nl2sql_client.should_fail = True
        mock_nl2sql_client.failure_message = "Database connection timeout"
        
        # Add SQL cache entry
        cache_id = mock_controller.add_cache_entry({
            "template": "SELECT * FROM users",
            "template_type": "sql",
            "is_template": False
        })
        
        # Set up SQL wrapper
        sql_wrapper = SQLExecutionWrapper(mock_nl2sql_client, mock_controller)
        
        # Execute step
        step_config = {
            "id": "sql_step_2",
            "cache_id": cache_id,
            "template_type": "sql"
        }
        
        result = await sql_wrapper.execute_sql_step(step_config)
        
        # Assertions
        assert result.success is False
        assert "Database connection timeout" in result.error
        assert result.step_id == "sql_step_2"
    
    @pytest.mark.asyncio
    async def test_sql_template_execution(self, mock_nl2sql_client):
        """Test SQL step template execution."""
        template = SQLStepTemplate(mock_nl2sql_client)
        
        step_config = {
            "id": "template_test",
            "template": "SELECT COUNT(*) as total FROM products WHERE category = {category}",
            "template_type": "sql",
            "execution_config": {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "ecommerce"
                }
            }
        }
        
        entity_values = {"category": "electronics"}
        
        result = await template.execute(step_config, entity_values)
        
        # Assertions
        assert result.success is True
        assert result.template_type == "sql"
        assert "electronics" in mock_nl2sql_client.executed_queries[0]["sql"]


class TestAPIExecutionIntegration:
    """Test API execution integration."""
    
    @pytest.mark.asyncio
    async def test_api_step_execution_success(self, mock_controller):
        """Test successful API step execution."""
        # Add API cache entry
        cache_id = mock_controller.add_cache_entry({
            "template": "/users/{user_id}/profile",
            "template_type": "api",
            "is_template": True,
            "entity_replacements": {
                "user_id": {"type": "integer", "description": "User ID"}
            },
            "execution_config": {
                "base_url": "https://api.example.com",
                "method": "GET",
                "headers": {"Authorization": "Bearer test_token"}
            }
        })
        
        # Mock the tool invoker
        with patch('thinkforge.execution_wrappers.ToolInvoker') as mock_tool_invoker:
            mock_instance = mock_tool_invoker.return_value
            mock_instance.invoke_tool = AsyncMock(return_value={
                "success": True,
                "output": {"id": 123, "name": "John Doe", "email": "john@example.com"}
            })
            
            # Set up API wrapper
            api_wrapper = APIExecutionWrapper(mock_controller)
            
            # Execute step
            step_config = {
                "id": "api_step_1",
                "cache_id": cache_id,
                "template_type": "api"
            }
            
            entity_values = {"user_id": 123}
            
            result = await api_wrapper.execute_api_step(step_config, entity_values)
            
            # Assertions
            assert result.success is True
            assert result.template_type == "api"
            assert result.step_id == "api_step_1"
            assert result.data["id"] == 123
    
    @pytest.mark.asyncio
    async def test_api_template_execution(self):
        """Test API step template execution."""
        with patch('thinkforge.step_templates.ToolExecutionWrapper') as mock_wrapper:
            mock_instance = mock_wrapper.return_value
            mock_instance.execute_tool_step = AsyncMock(return_value=ExecutionResult(
                success=True,
                data={"status": "created", "id": 456},
                template_type="api"
            ))
            
            template = APIStepTemplate()
            
            step_config = {
                "id": "api_template_test",
                "template": "/orders",
                "template_type": "api",
                "execution_config": {
                    "base_url": "https://api.shop.com",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"}
                }
            }
            
            entity_values = {"product_id": 789, "quantity": 2}
            
            result = await template.execute(step_config, entity_values)
            
            # Assertions
            assert result.success is True
            assert result.data["status"] == "created"


class TestWorkflowExecution:
    """Test complete workflow execution."""
    
    @pytest.mark.asyncio
    async def test_multi_step_workflow_execution(self, mock_nl2sql_client, mock_controller):
        """Test execution of a multi-step workflow."""
        # Add cache entries for workflow steps
        sql_cache_id = mock_controller.add_cache_entry({
            "template": "SELECT id, email FROM users WHERE status = 'active'",
            "template_type": "sql",
            "is_template": False
        })
        
        api_cache_id = mock_controller.add_cache_entry({
            "template": "/notifications/send",
            "template_type": "api",
            "is_template": False,
            "execution_config": {
                "base_url": "https://api.notifications.com",
                "method": "POST"
            }
        })
        
        # Mock successful results
        mock_nl2sql_client.set_mock_result("select", [
            {"id": 1, "email": "user1@example.com"},
            {"id": 2, "email": "user2@example.com"}
        ])
        
        # Set up workflow configuration
        workflow_config = {
            "id": "notification_workflow",
            "steps": [
                {
                    "id": "fetch_users",
                    "cache_id": sql_cache_id,
                    "template_type": "sql",
                    "dependencies": []
                },
                {
                    "id": "send_notifications",
                    "cache_id": api_cache_id,
                    "template_type": "api",
                    "dependencies": ["fetch_users"]
                }
            ]
        }
        
        # Mock API execution
        with patch('thinkforge.execution_wrappers.ToolInvoker') as mock_tool_invoker:
            mock_instance = mock_tool_invoker.return_value
            mock_instance.invoke_tool = AsyncMock(return_value={
                "success": True,
                "output": {"notifications_sent": 2, "status": "completed"}
            })
            
            # Execute workflow
            workflow_wrapper = WorkflowExecutionWrapper(mock_controller, mock_nl2sql_client)
            
            results = await workflow_wrapper.execute_workflow(workflow_config)
            
            # Assertions
            assert results["success"] is True
            assert results["status"] == "completed"
            assert len(results["steps"]) == 2
            
            # Check step execution order
            step_names = [step["step_id"] for step in results["steps"]]
            assert step_names == ["fetch_users", "send_notifications"]
            
            # Verify SQL was executed
            assert len(mock_nl2sql_client.executed_queries) == 1
    
    @pytest.mark.asyncio
    async def test_workflow_execution_with_failure(self, mock_nl2sql_client, mock_controller):
        """Test workflow execution with step failure."""
        # Configure SQL client to fail
        mock_nl2sql_client.should_fail = True
        mock_nl2sql_client.failure_message = "Database unavailable"
        
        # Add cache entry
        cache_id = mock_controller.add_cache_entry({
            "template": "SELECT * FROM critical_data",
            "template_type": "sql",
            "is_template": False
        })
        
        # Set up workflow configuration
        workflow_config = {
            "id": "failing_workflow",
            "steps": [
                {
                    "id": "failing_step",
                    "cache_id": cache_id,
                    "template_type": "sql",
                    "dependencies": []
                }
            ]
        }
        
        # Execute workflow
        workflow_wrapper = WorkflowExecutionWrapper(mock_controller, mock_nl2sql_client)
        
        results = await workflow_wrapper.execute_workflow(workflow_config)
        
        # Assertions
        assert results["success"] is False
        assert results["status"] == "failed"
        assert "Database unavailable" in results["error"]
        assert results["failed_step"] == "failing_step"
    
    @pytest.mark.asyncio
    async def test_parallel_workflow_execution(self, mock_nl2sql_client, mock_controller):
        """Test parallel workflow execution."""
        # Add cache entries for parallel steps
        sql_cache_id_1 = mock_controller.add_cache_entry({
            "template": "SELECT COUNT(*) FROM orders",
            "template_type": "sql",
            "is_template": False
        })
        
        sql_cache_id_2 = mock_controller.add_cache_entry({
            "template": "SELECT COUNT(*) FROM users",
            "template_type": "sql",
            "is_template": False
        })
        
        # Set up workflow configuration with parallel steps
        workflow_config = {
            "id": "parallel_workflow",
            "steps": [
                {
                    "id": "count_orders",
                    "cache_id": sql_cache_id_1,
                    "template_type": "sql",
                    "dependencies": []
                },
                {
                    "id": "count_users",
                    "cache_id": sql_cache_id_2,
                    "template_type": "sql",
                    "dependencies": []
                }
            ]
        }
        
        # Execute workflow
        workflow_wrapper = WorkflowExecutionWrapper(mock_controller, mock_nl2sql_client)
        
        start_time = datetime.utcnow()
        results = await workflow_wrapper.execute_workflow(workflow_config)
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Assertions
        assert results["success"] is True
        assert results["status"] == "completed"
        assert len(results["steps"]) == 2
        
        # Both SQL queries should have been executed
        assert len(mock_nl2sql_client.executed_queries) == 2
        
        # Parallel execution should be faster than sequential
        assert execution_time < 1.0  # Should complete quickly in parallel


class TestStepExecutorIntegration:
    """Test the high-level step executor."""
    
    @pytest.mark.asyncio
    async def test_step_executor_routing(self, mock_nl2sql_client):
        """Test step executor routing to appropriate templates."""
        executor = StepExecutor(mock_nl2sql_client)
        
        # Test SQL step routing
        sql_step_config = {
            "id": "sql_test",
            "template": "SELECT 1",
            "template_type": "sql",
            "execution_config": {}
        }
        
        with patch.object(executor, '_get_template') as mock_get_template:
            mock_template = Mock()
            mock_template.execute = AsyncMock(return_value=ExecutionResult(
                success=True,
                data=[{"result": 1}],
                template_type="sql"
            ))
            mock_get_template.return_value = mock_template
            
            result = await executor.execute_step(sql_step_config)
            
            # Assertions
            assert result.success is True
            assert result.template_type == "sql"
            mock_get_template.assert_called_once_with("sql")
    
    @pytest.mark.asyncio
    async def test_step_executor_with_progress_callback(self, mock_nl2sql_client):
        """Test step executor with progress monitoring."""
        progress_events = []
        
        def progress_callback(event):
            progress_events.append(event)
        
        executor = StepExecutor(mock_nl2sql_client)
        
        step_config = {
            "id": "progress_test",
            "template": "SELECT COUNT(*) FROM large_table",
            "template_type": "sql",
            "execution_config": {}
        }
        
        with patch.object(executor, '_get_template') as mock_get_template:
            mock_template = Mock()
            mock_template.execute = AsyncMock(return_value=ExecutionResult(
                success=True,
                data=[{"count": 1000000}],
                template_type="sql"
            ))
            mock_get_template.return_value = mock_template
            
            result = await executor.execute_step(
                step_config, 
                progress_callback=progress_callback
            )
            
            # Check that template.execute was called with progress callback
            mock_template.execute.assert_called_once()
            call_args = mock_template.execute.call_args
            assert call_args[1]["progress_callback"] == progress_callback


class TestExecutionConfigIntegration:
    """Test execution configuration integration."""
    
    def test_config_manager_database_config(self, execution_config_manager):
        """Test database configuration retrieval."""
        db_config = execution_config_manager.get_database_config()
        
        assert db_config is not None
        assert db_config.host == "localhost"
        assert db_config.port == 5432
        assert db_config.database == "test_db"
        assert db_config.username == "test_user"
    
    def test_config_manager_api_config(self, execution_config_manager):
        """Test API configuration retrieval."""
        api_config = execution_config_manager.get_api_config()
        
        assert api_config is not None
        assert api_config.base_url == "https://api.example.com"
        assert api_config.authentication["type"] == "bearer"
        assert api_config.authentication["token"] == "test_token"
    
    def test_config_merging(self, execution_config_manager):
        """Test execution configuration merging."""
        base_config = {
            "timeout": 30,
            "retry_attempts": 3
        }
        
        merged_config = execution_config_manager.merge_execution_config(
            base_config=base_config,
            template_type="sql",
            workflow_id="test_workflow",
            step_id="test_step"
        )
        
        # Should include original config plus database config
        assert merged_config["timeout"] == 30
        assert merged_config["retry_attempts"] == 3
        assert "database" in merged_config
        assert merged_config["database"]["host"] == "localhost"


class TestErrorHandlingAndResilience:
    """Test error handling and resilience features."""
    
    @pytest.mark.asyncio
    async def test_execution_wrapper_error_recovery(self, mock_nl2sql_client, mock_controller):
        """Test error recovery in execution wrappers."""
        # Configure intermittent failures
        call_count = 0
        original_execute = mock_nl2sql_client.execute
        
        async def failing_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first two attempts
                raise Exception("Temporary database error")
            return await original_execute(*args, **kwargs)
        
        mock_nl2sql_client.execute = failing_execute
        
        # Add cache entry
        cache_id = mock_controller.add_cache_entry({
            "template": "SELECT 1",
            "template_type": "sql",
            "is_template": False
        })
        
        # Execute with retry logic (would need to be implemented in wrapper)
        sql_wrapper = SQLExecutionWrapper(mock_nl2sql_client, mock_controller)
        
        step_config = {
            "id": "retry_test",
            "cache_id": cache_id,
            "template_type": "sql"
        }
        
        # This test demonstrates where retry logic would be implemented
        result = await sql_wrapper.execute_sql_step(step_config)
        
        # For now, this will fail - demonstrating where enhancement is needed
        assert result.success is False
        assert "Temporary database error" in result.error
    
    @pytest.mark.asyncio
    async def test_workflow_partial_failure_handling(self, mock_nl2sql_client, mock_controller):
        """Test workflow handling of partial failures."""
        # Add cache entries
        success_cache_id = mock_controller.add_cache_entry({
            "template": "SELECT 'success' as status",
            "template_type": "sql",
            "is_template": False
        })
        
        failure_cache_id = mock_controller.add_cache_entry({
            "template": "SELECT * FROM nonexistent_table",
            "template_type": "sql",
            "is_template": False
        })
        
        # Configure client to fail for specific query
        original_execute = mock_nl2sql_client.execute
        
        async def selective_execute(sql, database_config=None):
            if "nonexistent_table" in sql:
                raise Exception("Table does not exist")
            return await original_execute(sql, database_config)
        
        mock_nl2sql_client.execute = selective_execute
        
        # Set up workflow with mixed success/failure
        workflow_config = {
            "id": "partial_failure_workflow",
            "steps": [
                {
                    "id": "success_step",
                    "cache_id": success_cache_id,
                    "template_type": "sql",
                    "dependencies": []
                },
                {
                    "id": "failure_step",
                    "cache_id": failure_cache_id,
                    "template_type": "sql",
                    "dependencies": ["success_step"]
                }
            ]
        }
        
        # Execute workflow
        workflow_wrapper = WorkflowExecutionWrapper(mock_controller, mock_nl2sql_client)
        
        results = await workflow_wrapper.execute_workflow(workflow_config)
        
        # Assertions
        assert results["success"] is False
        assert results["status"] == "failed"
        assert results["failed_step"] == "failure_step"
        assert len(results["steps"]) == 2  # Both steps attempted
        
        # First step should have succeeded
        assert results["steps"][0]["success"] is True
        # Second step should have failed
        assert results["steps"][1]["success"] is False


if __name__ == "__main__":
    # Run tests if executed directly
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Configure logging for test output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run async tests
    async def run_tests():
        """Run all tests."""
        print("Running ThinkForge Workflow Execution Integration Tests...")
        
        # Initialize test fixtures
        mock_client = MockNL2SQLClient()
        mock_controller = MockThinkForgeController()
        
        # Test SQL execution
        print("\n=== Testing SQL Execution ===")
        sql_test = TestSQLExecutionIntegration()
        await sql_test.test_sql_step_execution_success(mock_client, mock_controller)
        print("✓ SQL step execution success test passed")
        
        # Reset for next test
        mock_client = MockNL2SQLClient()
        await sql_test.test_sql_step_execution_failure(mock_client, mock_controller)
        print("✓ SQL step execution failure test passed")
        
        # Test workflow execution
        print("\n=== Testing Workflow Execution ===")
        workflow_test = TestWorkflowExecution()
        mock_client = MockNL2SQLClient()
        mock_controller = MockThinkForgeController()
        
        await workflow_test.test_multi_step_workflow_execution(mock_client, mock_controller)
        print("✓ Multi-step workflow execution test passed")
        
        print("\n=== All Tests Completed Successfully ===")
    
    # Run the tests
    asyncio.run(run_tests())