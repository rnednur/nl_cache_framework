#!/usr/bin/env python3
"""
ThinkForge Workflow Execution Example

This example demonstrates how to integrate ThinkForge's workflow execution framework
with your nl2sql framework for comprehensive workflow automation.

Example workflow: Customer Analysis Pipeline
1. Extract customer data using SQL (via nl2sql framework)
2. Enrich data with external API calls
3. Generate summary report
4. Send notification about completion
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# ThinkForge imports
from thinkforge.execution_wrappers import WorkflowExecutionWrapper
from thinkforge.step_templates import StepExecutor
from thinkforge.execution_config import ExecutionConfigManager
from thinkforge.workflow_compiler import (
    compile_workflow_template,
    generate_executable_python_code
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExampleNL2SQLClient:
    """
    Example implementation of an nl2sql client.
    Replace this with your actual nl2sql framework client.
    """
    
    def __init__(self, database_config: Optional[Dict[str, Any]] = None):
        self.database_config = database_config or {
            "host": "localhost",
            "port": 5432,
            "database": "analytics",
            "username": "analyst",
            "password": "secure_password"
        }
        logger.info("NL2SQL client initialized")
    
    async def execute(self, sql: str, database_config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute SQL query using your nl2sql framework.
        This is where you'd integrate with your actual database connectivity.
        """
        config = database_config or self.database_config
        
        logger.info(f"Executing SQL: {sql[:100]}...")
        logger.info(f"Database: {config.get('database', 'unknown')}")
        
        # Simulate database execution
        await asyncio.sleep(0.5)  # Simulate query time
        
        # Return mock results based on query type
        if "customers" in sql.lower():
            return [
                {"customer_id": 1, "name": "Acme Corp", "region": "North", "value": 150000},
                {"customer_id": 2, "name": "Tech Solutions", "region": "South", "value": 230000},
                {"customer_id": 3, "name": "Global Industries", "region": "East", "value": 180000}
            ]
        elif "orders" in sql.lower():
            return [
                {"order_id": 101, "customer_id": 1, "amount": 15000, "date": "2024-01-15"},
                {"order_id": 102, "customer_id": 2, "amount": 23000, "date": "2024-01-20"},
                {"order_id": 103, "customer_id": 3, "amount": 18000, "date": "2024-01-25"}
            ]
        else:
            return {"result": "Query executed successfully"}


async def setup_workflow_execution_environment():
    """Set up the execution environment with configuration and clients."""
    
    # Initialize nl2sql client
    nl2sql_client = ExampleNL2SQLClient()
    
    # Configure execution settings
    config_manager = ExecutionConfigManager()
    
    # Database configuration for SQL steps
    config_manager.set_config("database", {
        "host": "analytics-db.company.com",
        "port": 5432,
        "database": "customer_analytics",
        "username": "workflow_user",
        "password": "workflow_password",
        "schema": "public",
        "ssl": True,
        "connection_timeout": 30,
        "query_timeout": 300
    })
    
    # API configuration for external service calls
    config_manager.set_config("api", {
        "base_url": "https://api.enrichment-service.com",
        "authentication": {
            "type": "bearer",
            "token": "your_api_token_here"
        },
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "ThinkForge-Workflow/1.0"
        },
        "timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 2
    })
    
    # Workflow execution settings
    config_manager.set_config("workflow", {
        "parallel_limit": 3,
        "step_timeout": 600,
        "failure_strategy": "stop",
        "retry_attempts": 2,
        "retry_delay": 5,
        "progress_reporting": True
    })
    
    return nl2sql_client, config_manager


def create_customer_analysis_workflow():
    """Create a sample customer analysis workflow configuration."""
    
    return {
        "id": "customer_analysis_pipeline",
        "name": "Customer Analysis Pipeline",
        "description": "Extract, enrich, and analyze customer data",
        "steps": [
            {
                "id": "extract_customers",
                "name": "Extract Customer Data",
                "template_type": "sql",
                "template": """
                    SELECT 
                        customer_id,
                        name,
                        region,
                        total_value,
                        last_order_date,
                        status
                    FROM customers 
                    WHERE status = 'active'
                    AND last_order_date >= {start_date}
                    ORDER BY total_value DESC
                """,
                "dependencies": [],
                "execution_config": {
                    "database": {
                        "schema": "analytics"
                    }
                },
                "entity_replacements": {
                    "start_date": {
                        "type": "date",
                        "description": "Start date for customer analysis"
                    }
                }
            },
            {
                "id": "extract_orders",
                "name": "Extract Recent Orders",
                "template_type": "sql",
                "template": """
                    SELECT 
                        order_id,
                        customer_id,
                        order_date,
                        total_amount,
                        product_category
                    FROM orders 
                    WHERE order_date >= {start_date}
                    AND status = 'completed'
                """,
                "dependencies": [],
                "execution_config": {
                    "database": {
                        "schema": "sales"
                    }
                }
            },
            {
                "id": "enrich_customer_data",
                "name": "Enrich with External Data",
                "template_type": "api",
                "template": "/customers/enrich",
                "dependencies": ["extract_customers"],
                "execution_config": {
                    "method": "POST",
                    "payload_template": {
                        "customers": "{extract_customers_output}",
                        "enrichment_types": ["industry", "company_size", "credit_score"]
                    }
                }
            },
            {
                "id": "calculate_metrics",
                "name": "Calculate Customer Metrics",
                "template_type": "function",
                "template": """
def calculate_customer_metrics(customers, orders):
    '''Calculate advanced customer metrics'''
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Convert to DataFrames
    customers_df = pd.DataFrame(customers)
    orders_df = pd.DataFrame(orders)
    
    # Calculate metrics
    metrics = {}
    for customer in customers:
        customer_id = customer['customer_id']
        customer_orders = orders_df[orders_df['customer_id'] == customer_id]
        
        metrics[customer_id] = {
            'total_orders': len(customer_orders),
            'average_order_value': customer_orders['total_amount'].mean() if len(customer_orders) > 0 else 0,
            'last_order_days_ago': (datetime.now() - pd.to_datetime(customer_orders['order_date'].max())).days if len(customer_orders) > 0 else None,
            'customer_lifetime_value': customer_orders['total_amount'].sum() if len(customer_orders) > 0 else 0
        }
    
    return metrics
                """,
                "dependencies": ["extract_customers", "extract_orders"],
                "execution_config": {
                    "timeout": 120,
                    "memory_limit": "256MB"
                }
            },
            {
                "id": "generate_report",
                "name": "Generate Analysis Report",
                "template_type": "function",
                "template": """
def generate_analysis_report(customers, enriched_data, metrics):
    '''Generate comprehensive customer analysis report'''
    import json
    from datetime import datetime
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_customers': len(customers),
            'total_customer_value': sum(c['total_value'] for c in customers),
            'average_customer_value': sum(c['total_value'] for c in customers) / len(customers) if customers else 0
        },
        'top_customers': sorted(customers, key=lambda x: x['total_value'], reverse=True)[:5],
        'regional_breakdown': {},
        'metrics': metrics,
        'enriched_data_summary': {
            'enrichment_success_rate': len([e for e in enriched_data if e.get('success', False)]) / len(enriched_data) if enriched_data else 0
        }
    }
    
    # Calculate regional breakdown
    for customer in customers:
        region = customer['region']
        if region not in report['regional_breakdown']:
            report['regional_breakdown'][region] = {'count': 0, 'total_value': 0}
        report['regional_breakdown'][region]['count'] += 1
        report['regional_breakdown'][region]['total_value'] += customer['total_value']
    
    return report
                """,
                "dependencies": ["extract_customers", "enrich_customer_data", "calculate_metrics"],
                "execution_config": {
                    "timeout": 60
                }
            },
            {
                "id": "send_notification",
                "name": "Send Completion Notification",
                "template_type": "api",
                "template": "/notifications/workflow-complete",
                "dependencies": ["generate_report"],
                "execution_config": {
                    "method": "POST",
                    "base_url": "https://api.notifications.company.com",
                    "payload_template": {
                        "workflow_id": "customer_analysis_pipeline",
                        "status": "completed",
                        "summary": "{generate_report_output}",
                        "timestamp": "{current_timestamp}"
                    }
                }
            }
        ]
    }


async def execute_workflow_example():
    """Execute the complete workflow example."""
    
    logger.info("=== ThinkForge Workflow Execution Example ===")
    
    # Set up execution environment
    nl2sql_client, config_manager = await setup_workflow_execution_environment()
    
    # Create workflow configuration
    workflow_config = create_customer_analysis_workflow()
    
    logger.info(f"Created workflow: {workflow_config['name']}")
    logger.info(f"Steps: {len(workflow_config['steps'])}")
    
    # Initialize workflow executor
    workflow_executor = WorkflowExecutionWrapper(
        thinkforge_controller=None,  # Would use actual controller in production
        nl2sql_client=nl2sql_client
    )
    
    # Define entity values for the workflow
    entity_values = {
        "start_date": "2024-01-01",
        "current_timestamp": datetime.now().isoformat()
    }
    
    # Set up progress monitoring
    progress_events = []
    
    def progress_callback(event):
        progress_events.append(event)
        logger.info(f"Progress: {event.get('status', 'unknown')} - Step: {event.get('step_id', 'N/A')}")
    
    # Execute the workflow
    logger.info("Starting workflow execution...")
    start_time = datetime.now()
    
    try:
        results = await workflow_executor.execute_workflow(
            workflow_config=workflow_config,
            entity_values=entity_values,
            progress_callback=progress_callback
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Display results
        logger.info("=== Workflow Execution Results ===")
        logger.info(f"Status: {results['status']}")
        logger.info(f"Success: {results['success']}")
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info(f"Steps completed: {len(results['steps'])}")
        
        if results['success']:
            logger.info("✓ Workflow completed successfully!")
            
            # Show step-by-step results
            for i, step_result in enumerate(results['steps'], 1):
                step_id = step_result.get('step_id', f'step_{i}')
                success = step_result.get('success', False)
                duration = step_result.get('execution_time', 0)
                
                status_icon = "✓" if success else "✗"
                logger.info(f"  {status_icon} Step {i}: {step_id} ({duration:.2f}s)")
                
                if not success:
                    error = step_result.get('error', 'Unknown error')
                    logger.error(f"    Error: {error}")
        else:
            logger.error("✗ Workflow failed!")
            if 'error' in results:
                logger.error(f"Error: {results['error']}")
            if 'failed_step' in results:
                logger.error(f"Failed at step: {results['failed_step']}")
        
        # Display progress events
        logger.info(f"\n=== Progress Events ({len(progress_events)} total) ===")
        for event in progress_events:
            timestamp = event.get('timestamp', 'unknown')
            step_id = event.get('step_id', 'unknown')
            status = event.get('status', 'unknown')
            logger.info(f"  {timestamp}: {step_id} -> {status}")
        
    except Exception as e:
        logger.error(f"Workflow execution failed with exception: {e}")
        import traceback
        traceback.print_exc()


async def compile_workflow_to_code_example():
    """Example of compiling workflow to executable Python code."""
    
    logger.info("\n=== Workflow Code Generation Example ===")
    
    # Create a simple workflow for demonstration
    nodes = [
        {
            "id": "start",
            "type": "input",
            "data": {"label": "Start"},
            "position": {"x": 250, "y": 50}
        },
        {
            "id": "sql_step",
            "type": "default",
            "data": {
                "label": "Extract Data",
                "originalStepType": "sql",
                "template": "SELECT * FROM customers WHERE region = {region}"
            },
            "position": {"x": 250, "y": 150}
        },
        {
            "id": "api_step",
            "type": "default",
            "data": {
                "label": "Enrich Data",
                "originalStepType": "api",
                "template": "/enrich"
            },
            "position": {"x": 250, "y": 250}
        }
    ]
    
    edges = [
        {
            "id": "start-sql",
            "source": "start",
            "target": "sql_step"
        },
        {
            "id": "sql-api",
            "source": "sql_step",
            "target": "api_step"
        }
    ]
    
    # Compile to workflow template
    workflow_template = compile_workflow_template(nodes, edges)
    
    logger.info("Compiled workflow template:")
    logger.info(json.dumps(workflow_template, indent=2))
    
    # Generate executable Python code
    python_code = generate_executable_python_code(
        workflow_template=workflow_template,
        include_imports=True,
        async_execution=True
    )
    
    logger.info("\n=== Generated Python Code ===")
    logger.info(python_code)
    
    # Save to file for demonstration
    output_file = "generated_workflow.py"
    with open(output_file, 'w') as f:
        f.write(python_code)
    
    logger.info(f"\nExecutable workflow code saved to: {output_file}")


async def step_executor_example():
    """Example of using the high-level step executor."""
    
    logger.info("\n=== Step Executor Example ===")
    
    # Initialize step executor with nl2sql client
    nl2sql_client, _ = await setup_workflow_execution_environment()
    step_executor = StepExecutor(nl2sql_client=nl2sql_client)
    
    # Execute individual steps
    sql_step_config = {
        "id": "example_sql_step",
        "template": "SELECT COUNT(*) as customer_count FROM customers WHERE region = {region}",
        "template_type": "sql",
        "execution_config": {
            "database": {
                "schema": "analytics"
            }
        }
    }
    
    entity_values = {"region": "North"}
    
    logger.info("Executing SQL step...")
    result = await step_executor.execute_step(
        step_config=sql_step_config,
        entity_values=entity_values
    )
    
    logger.info(f"SQL Step Result:")
    logger.info(f"  Success: {result.success}")
    logger.info(f"  Data: {result.data}")
    logger.info(f"  Execution time: {result.execution_time:.2f}s")
    
    if not result.success:
        logger.error(f"  Error: {result.error}")


if __name__ == "__main__":
    # Run the complete example
    async def main():
        try:
            # Execute the main workflow example
            await execute_workflow_example()
            
            # Show code generation capabilities
            await compile_workflow_to_code_example()
            
            # Demonstrate step executor
            await step_executor_example()
            
            logger.info("\n=== Example Completed Successfully ===")
            
        except Exception as e:
            logger.error(f"Example failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the example
    asyncio.run(main())