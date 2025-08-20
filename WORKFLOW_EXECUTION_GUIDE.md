# ThinkForge Workflow Execution Framework

This guide explains how to use ThinkForge's workflow execution framework to create and execute complex workflows that integrate with your nl2sql framework and other external systems.

## Architecture Overview

The workflow execution framework consists of several key components:

### Core Components

1. **Execution Wrappers** (`thinkforge/execution_wrappers.py`)
   - `SQLExecutionWrapper`: Integrates with nl2sql framework for database operations
   - `APIExecutionWrapper`: Handles HTTP API calls with authentication
   - `ToolExecutionWrapper`: Routes to appropriate tool handlers
   - `WorkflowExecutionWrapper`: Orchestrates multi-step workflow execution

2. **Step Templates** (`thinkforge/step_templates.py`)
   - Standardized execution templates for different step types
   - Built-in error handling and progress monitoring
   - Template factory for easy step creation

3. **Execution Configuration** (`thinkforge/execution_config.py`)
   - Hierarchical configuration management
   - Database, API, and tool-specific configurations
   - Environment-based configuration loading

4. **Workflow Compiler** (`thinkforge/workflow_compiler.py`)
   - Compiles ReactFlow workflows to executable templates
   - Generates Python, Bash, and Jupyter notebook code
   - Supports multiple workflow formats (Langchain, Langflow, etc.)

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .  # Install ThinkForge in development mode
```

### 2. Set Up Your NL2SQL Client

```python
from thinkforge.execution_wrappers import SQLExecutionWrapper

class YourNL2SQLClient:
    async def execute(self, sql: str, database_config: dict = None):
        # Your database execution logic here
        return results

# Initialize SQL wrapper with your client
nl2sql_client = YourNL2SQLClient()
sql_wrapper = SQLExecutionWrapper(nl2sql_client)
```

### 3. Configure Execution Environment

```python
from thinkforge.execution_config import ExecutionConfigManager

config_manager = ExecutionConfigManager()

# Database configuration
config_manager.set_config("database", {
    "host": "your-db-host",
    "port": 5432,
    "database": "your_database",
    "username": "your_user",
    "password": "your_password"
})

# API configuration
config_manager.set_config("api", {
    "base_url": "https://your-api.com",
    "authentication": {"type": "bearer", "token": "your_token"},
    "headers": {"Content-Type": "application/json"}
})
```

### 4. Create and Execute a Workflow

```python
from thinkforge.execution_wrappers import WorkflowExecutionWrapper

# Define workflow configuration
workflow_config = {
    "id": "data_analysis_workflow",
    "steps": [
        {
            "id": "extract_data",
            "template": "SELECT * FROM customers WHERE region = {region}",
            "template_type": "sql",
            "dependencies": []
        },
        {
            "id": "enrich_data",
            "template": "/customers/enrich",
            "template_type": "api",
            "dependencies": ["extract_data"]
        }
    ]
}

# Execute workflow
executor = WorkflowExecutionWrapper(nl2sql_client=your_nl2sql_client)
results = await executor.execute_workflow(
    workflow_config=workflow_config,
    entity_values={"region": "North America"}
)
```

## Detailed Usage

### SQL Step Execution

The `SQLExecutionWrapper` integrates with your nl2sql framework for enhanced SQL generation and execution:

```python
from thinkforge.execution_wrappers import SQLExecutionWrapper

# Initialize with your nl2sql client
sql_wrapper = SQLExecutionWrapper(
    nl2sql_client=your_nl2sql_client,
    thinkforge_controller=your_controller  # Optional, for cache lookup
)

# Execute SQL step
step_config = {
    "id": "customer_analysis",
    "template": "SELECT customer_id, revenue FROM customers WHERE status = {status}",
    "template_type": "sql",
    "execution_config": {
        "database": {"schema": "analytics"}
    }
}

result = await sql_wrapper.execute_sql_step(
    step_config=step_config,
    entity_values={"status": "active"}
)

if result.success:
    print(f"Query returned {len(result.data)} rows")
else:
    print(f"Query failed: {result.error}")
```

### API Step Execution

Handle HTTP API calls with proper authentication and error handling:

```python
from thinkforge.execution_wrappers import APIExecutionWrapper

api_wrapper = APIExecutionWrapper()

step_config = {
    "id": "external_enrichment",
    "template": "/data/enrich",
    "template_type": "api",
    "execution_config": {
        "base_url": "https://api.external-service.com",
        "method": "POST",
        "authentication": {"type": "bearer", "token": "your_token"},
        "payload_template": {"data": "{previous_step_output}"}
    }
}

result = await api_wrapper.execute_api_step(step_config)
```

### Multi-Step Workflow Execution

Orchestrate complex workflows with dependency resolution:

```python
from thinkforge.execution_wrappers import WorkflowExecutionWrapper

workflow_config = {
    "id": "customer_pipeline",
    "steps": [
        {
            "id": "extract_customers",
            "template": "SELECT * FROM customers WHERE created_date >= {start_date}",
            "template_type": "sql",
            "dependencies": []
        },
        {
            "id": "extract_orders",
            "template": "SELECT * FROM orders WHERE order_date >= {start_date}",
            "template_type": "sql", 
            "dependencies": []
        },
        {
            "id": "calculate_metrics",
            "template": """
def calculate_customer_metrics(customers, orders):
    # Your Python calculation logic
    return metrics
            """,
            "template_type": "function",
            "dependencies": ["extract_customers", "extract_orders"]
        },
        {
            "id": "save_results",
            "template": "INSERT INTO customer_metrics (customer_id, metric_value) VALUES {values}",
            "template_type": "sql",
            "dependencies": ["calculate_metrics"]
        }
    ]
}

# Execute with progress monitoring
def progress_callback(event):
    print(f"Step {event['step_id']}: {event['status']}")

executor = WorkflowExecutionWrapper(nl2sql_client=your_client)
results = await executor.execute_workflow(
    workflow_config=workflow_config,
    entity_values={"start_date": "2024-01-01"},
    progress_callback=progress_callback
)
```

### Using Step Templates

For standardized execution with built-in error handling:

```python
from thinkforge.step_templates import StepExecutor

# Initialize step executor
executor = StepExecutor(nl2sql_client=your_client)

# Execute individual steps
result = await executor.execute_step(
    step_config=step_config,
    entity_values=entity_values,
    progress_callback=progress_callback
)
```

### Workflow Code Generation

Generate executable code from visual workflows:

```python
from thinkforge.workflow_compiler import (
    compile_workflow_template,
    generate_executable_python_code
)

# Convert ReactFlow nodes/edges to executable workflow
workflow_template = compile_workflow_template(nodes, edges)

# Generate Python code
python_code = generate_executable_python_code(
    workflow_template=workflow_template,
    async_execution=True
)

# Save executable workflow
with open("generated_workflow.py", "w") as f:
    f.write(python_code)
```

## Configuration Management

### Environment Variables

Set up configuration via environment variables:

```bash
export THINKFORGE_DB_HOST=localhost
export THINKFORGE_DB_PORT=5432
export THINKFORGE_DB_NAME=analytics
export THINKFORGE_DB_USER=analyst
export THINKFORGE_DB_PASSWORD=secure_password

export THINKFORGE_API_BASE_URL=https://api.example.com
export THINKFORGE_API_TIMEOUT=30
```

### Configuration Files

Create `thinkforge_config.yaml`:

```yaml
global:
  database:
    host: localhost
    port: 5432
    database: analytics
    username: analyst
    password: secure_password
    ssl: true
    connection_timeout: 30
    query_timeout: 300
  
  api:
    base_url: https://api.example.com
    timeout: 30
    retry_attempts: 3
    authentication:
      type: bearer
      token: your_api_token
  
  workflow:
    parallel_limit: 5
    step_timeout: 300
    failure_strategy: stop
    retry_attempts: 3
    progress_reporting: true

workflow:
  customer_analysis:
    database:
      schema: customer_data
    
step:
  critical_sql_step:
    database:
      query_timeout: 600
```

### Programmatic Configuration

```python
from thinkforge.execution_config import ExecutionConfigManager

config_manager = ExecutionConfigManager()

# Global configuration
config_manager.set_config("database", database_config)

# Workflow-specific configuration
config_manager.set_config(
    "database", 
    workflow_specific_config,
    scope=ConfigScope.WORKFLOW,
    scope_id="customer_analysis"
)

# Step-specific configuration
config_manager.set_config(
    "tool",
    step_specific_config,
    scope=ConfigScope.STEP,
    scope_id="critical_processing_step"
)
```

## Error Handling and Monitoring

### Built-in Error Handling

All execution wrappers include comprehensive error handling:

```python
result = await sql_wrapper.execute_sql_step(step_config)

if not result.success:
    print(f"Step failed: {result.error}")
    print(f"Execution time: {result.execution_time}s")
    print(f"Error details: {result.metadata.get('error_traceback')}")
```

### Progress Monitoring

Monitor workflow execution in real-time:

```python
def progress_callback(event):
    step_id = event.get('step_id')
    status = event.get('status')
    timestamp = event.get('timestamp')
    
    if status == 'starting':
        print(f"[{timestamp}] Starting step: {step_id}")
    elif status == 'completed':
        duration = event.get('duration', 0)
        print(f"[{timestamp}] Completed step: {step_id} ({duration:.2f}s)")
    elif status == 'failed':
        error = event.get('error', 'Unknown error')
        print(f"[{timestamp}] Failed step: {step_id} - {error}")

# Use with workflow execution
results = await executor.execute_workflow(
    workflow_config=workflow_config,
    progress_callback=progress_callback
)
```

### Execution Results

All execution operations return standardized `ExecutionResult` objects:

```python
class ExecutionResult:
    success: bool              # Whether execution succeeded
    data: Any                 # Result data
    error: Optional[str]      # Error message if failed
    execution_time: float     # Execution duration in seconds
    step_id: Optional[str]    # Step identifier
    template_type: str        # Type of template executed
    metadata: Dict[str, Any]  # Additional metadata
    timestamp: datetime       # Execution timestamp
```

## Integration with LLM Services

Enhance workflow generation with LLM integration:

```python
from thinkforge.controller import Text2SQLController

controller = Text2SQLController(db_session)

# Generate workflow with execution context
execution_context = {
    "available_databases": ["analytics", "sales", "customer"],
    "available_apis": [
        {"base_url": "https://api.crm.com", "status": "available"},
        {"base_url": "https://api.analytics.com", "status": "available"}
    ],
    "runtime_environment": "python3",
    "available_libraries": ["pandas", "numpy", "requests"],
    "resource_limits": {"memory_mb": 2048, "cpu_cores": 4}
}

workflow_design = controller.design_workflow_with_llm(
    nl_query="Analyze customer behavior and send personalized recommendations",
    compatible_entries=cache_entries,
    execution_context=execution_context
)

# Get execution plan with resource estimates
execution_plan = workflow_design["execution_plan"]
print(f"Estimated duration: {execution_plan['estimated_duration']} seconds")
print(f"Resource requirements: {execution_plan['resource_requirements']}")
```

## Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
python -m pytest tests/test_workflow_execution_integration.py -v

# Run specific test
python -m pytest tests/test_workflow_execution_integration.py::TestSQLExecutionIntegration::test_sql_step_execution_success -v

# Run example integration
python tests/test_workflow_execution_integration.py
```

## Examples

See complete examples in the `examples/` directory:

- `workflow_execution_example.py`: Comprehensive workflow execution example
- Generated workflow code examples
- Integration patterns with nl2sql frameworks

## Best Practices

1. **Configuration Management**
   - Use hierarchical configuration (global → workflow → step)
   - Store sensitive data in environment variables
   - Validate configurations before execution

2. **Error Handling**
   - Always check `ExecutionResult.success` before using data
   - Implement retry logic for transient failures
   - Log execution details for debugging

3. **Resource Management**
   - Set appropriate timeouts for long-running operations
   - Use parallel execution for independent steps
   - Monitor resource usage in production

4. **Security**
   - Never log sensitive data (passwords, tokens)
   - Use secure authentication methods
   - Validate all user inputs and SQL queries

5. **Performance**
   - Cache frequently used configurations
   - Use connection pooling for database operations
   - Optimize workflow step ordering for efficiency

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
   ```python
   # Check database configuration
   db_config = config_manager.get_database_config()
   print(f"Database config: {db_config}")
   
   # Validate configuration
   errors = config_manager.validate_config("sql", execution_config)
   if errors:
       print(f"Configuration errors: {errors}")
   ```

2. **API Authentication Issues**
   ```python
   # Check API configuration
   api_config = config_manager.get_api_config()
   print(f"API config: {api_config}")
   
   # Test API connectivity
   result = await api_wrapper.execute_api_step(test_config)
   ```

3. **Workflow Execution Failures**
   ```python
   # Enable detailed logging
   import logging
   logging.getLogger('thinkforge').setLevel(logging.DEBUG)
   
   # Check execution readiness
   execution_plan = controller._generate_execution_plan(workflow_template, execution_context)
   readiness = execution_plan["execution_readiness"]
   
   if not readiness["ready"]:
       print(f"Execution issues: {readiness['issues']}")
       print(f"Warnings: {readiness['warnings']}")
   ```

### Debug Mode

Enable debug mode for detailed execution logs:

```python
import logging

# Enable debug logging
logging.getLogger('thinkforge').setLevel(logging.DEBUG)

# Add console handler
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logging.getLogger('thinkforge').addHandler(handler)
```

## Contributing

When contributing to the workflow execution framework:

1. Add comprehensive tests for new features
2. Update this documentation
3. Follow the existing code patterns
4. Ensure backward compatibility
5. Add type hints for all public APIs

## Support

For questions and support:

1. Check the examples in `examples/`
2. Review the test cases in `tests/`
3. Enable debug logging for detailed information
4. Create issues for bugs or feature requests