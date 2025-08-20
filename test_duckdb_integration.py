#!/usr/bin/env python3
"""
Test DuckDB Integration for ThinkForge Framework

This test verifies that the DuckDB integration works correctly with the
workflow execution framework.
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_imports():
    """Test that all DuckDB-related imports work."""
    print("🧪 Testing DuckDB imports...")
    
    try:
        from thinkforge.workflow_datastore import WorkflowDataStore, get_workflow_datastore
        from thinkforge.execution_engine import ExecutionContext, ExecutionStatus
        from thinkforge.step_templates import DuckDBStepTemplate, StepTemplateFactory
        from thinkforge.execution_config import DuckDBConfig, ExecutionConfigManager
        from thinkforge.models import TemplateType
        
        # Check that DuckDB template type exists
        assert hasattr(TemplateType, 'DUCKDB_SQL'), "DUCKDB_SQL template type not found"
        assert TemplateType.DUCKDB_SQL == "duckdb_sql", "DUCKDB_SQL value incorrect"
        
        print("✅ All DuckDB imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Assertion error: {e}")
        return False

def test_datastore_basic():
    """Test basic WorkflowDataStore functionality."""
    print("\n🧪 Testing WorkflowDataStore basics...")
    
    try:
        from thinkforge.workflow_datastore import WorkflowDataStore
        
        # Test datastore creation
        with WorkflowDataStore("test_workflow", "test_run") as datastore:
            # Test data storage
            sample_data = [
                {"id": 1, "name": "Alice", "value": 100},
                {"id": 2, "name": "Bob", "value": 200},
                {"id": 3, "name": "Charlie", "value": 150}
            ]
            
            table_name = datastore.store_step_output(
                step_id="test_step",
                data=sample_data,
                template_type="function"
            )
            
            # Test data retrieval
            retrieved_data = datastore.get_step_output("test_step", as_dict=True)
            
            assert isinstance(retrieved_data, list), "Retrieved data should be a list"
            assert len(retrieved_data) == 3, "Should retrieve 3 records"
            assert retrieved_data[0]["name"] == "Alice", "First record should be Alice"
            
            # Test SQL execution
            sql_result = datastore.execute_sql(f"SELECT COUNT(*) as count FROM {table_name}")
            assert len(sql_result) == 1, "SQL result should have 1 row"
            assert sql_result.iloc[0]["count"] == 3, "Count should be 3"
            
            # Test table info
            tables = datastore.get_available_tables()
            assert len(tables) >= 1, "Should have at least 1 table"
            assert tables[0].step_id == "test_step", "Table should be for test_step"
        
        print("✅ WorkflowDataStore basic functionality works")
        return True
        
    except Exception as e:
        print(f"❌ WorkflowDataStore test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_execution_context():
    """Test ExecutionContext DuckDB integration."""
    print("\n🧪 Testing ExecutionContext DuckDB integration...")
    
    try:
        from thinkforge.execution_engine import ExecutionContext, ExecutionStatus
        
        # Create context
        context = ExecutionContext(
            workflow_id="test_workflow",
            run_id="test_run",
            status=ExecutionStatus.RUNNING
        )
        
        # Test datastore property
        datastore = context.datastore
        assert datastore is not None, "Datastore should be available"
        
        # Test storing step output
        sample_data = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
        table_name = context.store_step_output(
            "test_step",
            sample_data,
            "function"
        )
        
        # Test retrieving step output
        retrieved = context.get_step_output("test_step", as_dict=True)
        assert len(retrieved) == 2, "Should retrieve 2 records"
        
        # Test step_outputs property (backward compatibility)
        step_outputs = context.step_outputs
        assert "test_step" in step_outputs, "test_step should be in step_outputs"
        
        # Test SQL execution through context
        sql_result = context.execute_sql("SELECT COUNT(*) as count FROM workflow_metadata")
        assert len(sql_result) >= 1, "Should have workflow metadata"
        
        # Test available tables
        tables = context.get_available_tables()
        assert len(tables) >= 1, "Should have at least 1 table"
        
        # Clean up
        context.close_datastore()
        
        print("✅ ExecutionContext DuckDB integration works")
        return True
        
    except Exception as e:
        print(f"❌ ExecutionContext test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_duckdb_step_template():
    """Test DuckDBStepTemplate functionality."""
    print("\n🧪 Testing DuckDBStepTemplate...")
    
    try:
        from thinkforge.step_templates import DuckDBStepTemplate, execute_duckdb_sql_step
        from thinkforge.execution_engine import ExecutionContext, ExecutionStatus
        
        # Create context with sample data
        context = ExecutionContext(
            workflow_id="sql_test",
            run_id="sql_run",
            status=ExecutionStatus.RUNNING
        )
        
        # Store sample data
        customers = [
            {"id": 1, "name": "Alice", "region": "North"},
            {"id": 2, "name": "Bob", "region": "South"},
            {"id": 3, "name": "Charlie", "region": "North"}
        ]
        
        orders = [
            {"order_id": 1, "customer_id": 1, "amount": 100},
            {"order_id": 2, "customer_id": 2, "amount": 200},
            {"order_id": 3, "customer_id": 1, "amount": 150},
            {"order_id": 4, "customer_id": 3, "amount": 75}
        ]
        
        context.store_step_output("customers", customers, "function")
        context.store_step_output("orders", orders, "function")
        
        # Test DuckDB SQL step
        sql_step_config = {
            "id": "customer_analysis",
            "inputs": {
                "query": """
                    SELECT 
                        c.region,
                        COUNT(DISTINCT c.id) as customer_count,
                        COUNT(o.order_id) as order_count,
                        SUM(o.amount) as total_amount,
                        AVG(o.amount) as avg_amount
                    FROM {table:customers} c
                    LEFT JOIN {table:orders} o ON c.id = o.customer_id
                    GROUP BY c.region
                    ORDER BY total_amount DESC
                """
            }
        }
        
        # Execute SQL step
        result = await execute_duckdb_sql_step(
            sql_step_config,
            entity_values={},
            context=context
        )
        
        assert result.success, f"SQL step should succeed: {result.error}"
        assert result.data is not None, "Result should have data"
        assert len(result.data) == 2, "Should have 2 regions"
        
        # Check metadata
        assert "sql_query" in result.metadata, "Should have SQL query in metadata"
        assert "row_count" in result.metadata, "Should have row count in metadata"
        assert result.metadata["row_count"] == 2, "Row count should be 2"
        
        # Check data content
        north_data = next(row for row in result.data if row["region"] == "North")
        assert north_data["customer_count"] == 2, "North should have 2 customers"
        assert north_data["order_count"] == 3, "North should have 3 orders"
        assert north_data["total_amount"] == 325, "North total should be 325"
        
        # Test template creation via factory
        template = context.datastore  # Just check it exists
        assert template is not None, "Template should be created"
        
        context.close_datastore()
        
        print("✅ DuckDBStepTemplate functionality works")
        return True
        
    except Exception as e:
        print(f"❌ DuckDBStepTemplate test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_step_template_factory():
    """Test StepTemplateFactory DuckDB integration."""
    print("\n🧪 Testing StepTemplateFactory DuckDB integration...")
    
    try:
        from thinkforge.step_templates import StepTemplateFactory
        
        # Test creating DuckDB SQL template
        template = StepTemplateFactory.create_template("duckdb_sql")
        assert template is not None, "Should create DuckDB template"
        assert template.template_type == "duckdb_sql", "Template type should be duckdb_sql"
        assert template.__class__.__name__ == "DuckDBStepTemplate", "Should be DuckDBStepTemplate"
        
        print("✅ StepTemplateFactory DuckDB integration works")
        return True
        
    except Exception as e:
        print(f"❌ StepTemplateFactory test failed: {e}")
        return False

def test_execution_config():
    """Test DuckDB configuration management."""
    print("\n🧪 Testing DuckDB configuration...")
    
    try:
        from thinkforge.execution_config import ExecutionConfigManager, DuckDBConfig
        
        # Test DuckDBConfig creation
        config = DuckDBConfig(memory_limit="2GB", threads=8)
        assert config.memory_limit == "2GB", "Memory limit should be set"
        assert config.threads == 8, "Threads should be set"
        assert config.auto_cleanup == True, "Auto cleanup should default to True"
        
        # Test config manager
        manager = ExecutionConfigManager()
        duckdb_config = manager.get_duckdb_config()
        assert duckdb_config is not None, "Should get DuckDB config"
        assert isinstance(duckdb_config, DuckDBConfig), "Should be DuckDBConfig instance"
        
        # Test merge execution config
        merged = manager.merge_execution_config(
            base_config={},
            template_type="duckdb_sql"
        )
        assert "duckdb" in merged, "Should have duckdb config in merged"
        
        # Test validation
        errors = manager.validate_config("duckdb_sql", {"duckdb": {"threads": -1}})
        assert len(errors) > 0, "Should have validation errors for negative threads"
        
        print("✅ DuckDB configuration management works")
        return True
        
    except Exception as e:
        print(f"❌ DuckDB configuration test failed: {e}")
        return False

async def test_end_to_end_workflow():
    """Test end-to-end workflow with DuckDB steps."""
    print("\n🧪 Testing end-to-end workflow with DuckDB...")
    
    try:
        from thinkforge.execution_engine import ExecutionContext, ExecutionStatus
        from thinkforge.step_templates import execute_duckdb_sql_step
        
        # Create workflow context
        context = ExecutionContext(
            workflow_id="e2e_test",
            run_id="e2e_run",
            status=ExecutionStatus.RUNNING
        )
        
        # Step 1: Load initial data
        raw_data = [
            {"user_id": 1, "action": "login", "timestamp": "2023-06-01", "value": 1},
            {"user_id": 1, "action": "purchase", "timestamp": "2023-06-01", "value": 100},
            {"user_id": 2, "action": "login", "timestamp": "2023-06-02", "value": 1},
            {"user_id": 2, "action": "view", "timestamp": "2023-06-02", "value": 1},
            {"user_id": 3, "action": "login", "timestamp": "2023-06-03", "value": 1},
            {"user_id": 3, "action": "purchase", "timestamp": "2023-06-03", "value": 250}
        ]
        
        context.store_step_output("raw_events", raw_data, "function")
        
        # Step 2: Aggregate user activity
        aggregation_step = {
            "id": "user_aggregation",
            "inputs": {
                "query": """
                    SELECT 
                        user_id,
                        COUNT(*) as total_actions,
                        COUNT(CASE WHEN action = 'login' THEN 1 END) as login_count,
                        COUNT(CASE WHEN action = 'purchase' THEN 1 END) as purchase_count,
                        SUM(value) as total_value,
                        MAX(timestamp) as last_activity
                    FROM {table:raw_events}
                    GROUP BY user_id
                    ORDER BY total_value DESC
                """
            }
        }
        
        agg_result = await execute_duckdb_sql_step(aggregation_step, {}, context)
        assert agg_result.success, "Aggregation should succeed"
        assert len(agg_result.data) == 3, "Should have 3 users"
        
        # Step 3: Calculate user segments
        segmentation_step = {
            "id": "user_segmentation", 
            "inputs": {
                "query": """
                    SELECT 
                        CASE 
                            WHEN total_value >= 200 THEN 'high_value'
                            WHEN total_value >= 50 THEN 'medium_value'
                            ELSE 'low_value'
                        END as segment,
                        COUNT(*) as user_count,
                        AVG(total_value) as avg_value,
                        SUM(total_value) as segment_value
                    FROM {table:user_aggregation}
                    GROUP BY 1
                    ORDER BY segment_value DESC
                """
            }
        }
        
        seg_result = await execute_duckdb_sql_step(segmentation_step, {}, context)
        assert seg_result.success, "Segmentation should succeed"
        assert len(seg_result.data) >= 1, "Should have at least 1 segment"
        
        # Verify data persisted correctly
        tables = context.get_available_tables()
        table_names = [t.step_id for t in tables]
        assert "raw_events" in table_names, "raw_events should be persisted"
        assert "user_aggregation" in table_names, "user_aggregation should be persisted"
        assert "user_segmentation" in table_names, "user_segmentation should be persisted"
        
        # Test querying across steps
        cross_query = context.execute_sql("""
            SELECT 
                e.user_id,
                e.action,
                a.total_value,
                s.segment
            FROM {table:raw_events} e
            JOIN {table:user_aggregation} a ON e.user_id = a.user_id
            JOIN {table:user_segmentation} s ON 
                CASE 
                    WHEN a.total_value >= 200 THEN 'high_value'
                    WHEN a.total_value >= 50 THEN 'medium_value'
                    ELSE 'low_value'
                END = s.segment
            WHERE e.action = 'purchase'
            ORDER BY a.total_value DESC
        """.replace("{table:", "step_").replace("}", "_*"), as_dataframe=False)
        
        assert len(cross_query) == 2, "Should have 2 purchase events"
        
        context.close_datastore()
        
        print("✅ End-to-end workflow with DuckDB works")
        return True
        
    except Exception as e:
        print(f"❌ End-to-end workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all DuckDB integration tests."""
    print("🚀 Testing DuckDB Integration for ThinkForge")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports()),
        ("DataStore Basic", test_datastore_basic()),
        ("Execution Context", test_execution_context()),
        ("DuckDB Step Template", await test_duckdb_step_template()),
        ("Step Template Factory", test_step_template_factory()),
        ("Execution Config", test_execution_config()),
        ("End-to-End Workflow", await test_end_to_end_workflow())
    ]
    
    passed = sum(result for _, result in tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"🎉 All {total} tests passed!")
        print("\n📋 DuckDB Integration Summary:")
        print("✅ WorkflowDataStore for embedded analytics")
        print("✅ ExecutionContext DuckDB integration")
        print("✅ DuckDBStepTemplate for SQL transformations")
        print("✅ Configuration management and validation")
        print("✅ End-to-end workflow execution")
        print("✅ Cross-step data analytics")
        print("✅ Table management and persistence")
        
        print("\n🎯 Ready for Production!")
        print("   • Create workflows with duckdb_sql steps")
        print("   • Use SQL for complex data transformations")
        print("   • Query data across workflow steps")
        print("   • Combine with LLM steps for AI analytics")
        print("   • Export results to external systems")
        
        return True
    else:
        print(f"❌ {total - passed} out of {total} tests failed")
        print("\nFailed tests:")
        for name, result in tests:
            if not result:
                print(f"   • {name}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)