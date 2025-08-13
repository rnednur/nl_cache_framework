# ThinkForge Notebook Sandbox

A secure Docker-based execution environment for ThinkForge-generated Python notebooks.

## Features

- **Secure Execution**: Resource-limited containers with restricted capabilities
- **REST API**: Easy integration with ThinkForge backend services
- **Jupyter Lab**: Interactive notebook development and debugging
- **Validation**: Pre-execution security and syntax validation
- **Monitoring**: Execution tracking and result management

## Architecture

```
ThinkForge Backend
      ↓
SandboxManager (Python)
      ↓ (HTTP API)
Notebook Sandbox Container
  ├── API Server (FastAPI)
  ├── Notebook Executor
  └── Jupyter Lab (optional)
```

## Quick Start

### 1. Build and Start Sandbox

```bash
cd docker/notebook-sandbox
docker compose -f docker-compose.sandbox.yml up -d
```

### 2. Check Health

```bash
curl http://localhost:8888/health
```

### 3. Upload and Execute Notebook

```python
import asyncio
from thinkforge.sandbox_manager import SandboxManager

async def main():
    async with SandboxManager() as sandbox:
        # Upload notebook
        with open("workflow.ipynb", "r") as f:
            notebook_content = f.read()
        
        result = await sandbox.upload_notebook(notebook_content, "workflow.ipynb")
        print(f"Uploaded: {result}")
        
        # Execute notebook
        execution_id = await sandbox.execute_notebook("workflow.ipynb")
        
        # Wait for completion
        final_result = await sandbox.wait_for_execution(execution_id)
        print(f"Execution result: {final_result}")

asyncio.run(main())
```

## API Endpoints

### Health and Status
- `GET /health` - Health check
- `GET /notebooks` - List uploaded notebooks
- `GET /outputs` - List execution outputs

### Notebook Management
- `POST /notebooks/upload` - Upload notebook file
- `POST /notebooks/validate` - Validate notebook
- `DELETE /notebooks/{path}` - Delete notebook

### Execution
- `POST /notebooks/execute` - Start notebook execution
- `GET /notebooks/execution/{id}` - Get execution status
- `GET /notebooks/executions` - List all executions

## Security Features

### Resource Limits
- **Memory**: 512MB default limit
- **CPU Time**: 300 seconds default limit
- **Wall Time**: 600 seconds default limit
- **File Size**: 100MB maximum per file
- **Process Count**: 10 maximum processes

### Container Security
- Non-root user execution
- Dropped Linux capabilities
- Read-only filesystem (where possible)
- Network isolation
- Temporary filesystem for /tmp

### Code Validation
- JSON structure validation
- Security pattern detection
- Import statement analysis
- Execution flow validation

## Configuration

### Environment Variables

```yaml
environment:
  - MAX_MEMORY_MB=512          # Memory limit in MB
  - MAX_CPU_TIME=300           # CPU time limit in seconds
  - MAX_WALL_TIME=600          # Wall clock time limit
  - MAX_FILE_SIZE_MB=100       # File size limit in MB
  - LOG_LEVEL=info             # Logging level
  - JUPYTER_TOKEN=""           # Jupyter authentication token
```

### Docker Compose Override

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  notebook-sandbox:
    environment:
      - MAX_MEMORY_MB=1024     # Increase memory limit
      - MAX_CPU_TIME=600       # Increase CPU time
    ulimits:
      memlock:
        soft: 268435456        # 256MB
        hard: 268435456
```

## Integration with ThinkForge

### Backend Integration

```python
# In backend/app.py
from thinkforge.sandbox_manager import SandboxManager

@app.post("/workflows/execute")
async def execute_workflow(workflow_data: dict):
    async with SandboxManager() as sandbox:
        # Convert DSL to notebook and execute
        result = await sandbox.execute_dsl_workflow(
            workflow_data["dsl"],
            workflow_data["name"]
        )
        return result
```

### Frontend Integration

```typescript
// In frontend services
interface SandboxExecution {
  execution_id: string;
  status: string;
  result?: any;
}

async function executeWorkflow(dslContent: any): Promise<SandboxExecution> {
  const response = await fetch('/api/workflows/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dsl: dslContent, name: 'workflow' })
  });
  
  return await response.json();
}
```

## Development

### Local Development

```bash
# Install development dependencies
pip install -r requirements-sandbox.txt

# Run API server locally
cd scripts
python api_server.py

# Run notebook executor
python run_notebook.py --notebook example.ipynb
```

### Testing

```bash
# Validate notebook
python run_notebook.py --notebook test.ipynb --validate-only

# Execute with custom limits
python run_notebook.py --notebook test.ipynb \
  --memory-limit 256 --cpu-time 60 --wall-time 120
```

### Debugging

```bash
# View logs
docker compose -f docker-compose.sandbox.yml logs -f

# Access container shell
docker compose -f docker-compose.sandbox.yml exec notebook-sandbox bash

# Monitor resource usage
docker stats thinkforge-notebook-sandbox
```

## Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   # Check Docker daemon
   docker info
   
   # Check port availability
   netstat -tlnp | grep 8888
   ```

2. **Execution timeout**
   ```bash
   # Increase limits in compose file
   environment:
     - MAX_WALL_TIME=1200
   ```

3. **Memory issues**
   ```bash
   # Check available memory
   free -h
   
   # Increase container memory
   environment:
     - MAX_MEMORY_MB=1024
   ```

4. **Permission errors**
   ```bash
   # Check volume permissions
   ls -la notebooks/ output/
   
   # Fix permissions
   sudo chown -R 1000:1000 notebooks/ output/
   ```

### Health Checks

```bash
# API health
curl http://localhost:8888/health

# Notebook execution test
curl -X POST http://localhost:8888/notebooks/validate \
  -H "Content-Type: application/json" \
  -d '{"notebook_path": "test.ipynb"}'
```

## Production Deployment

### Security Hardening

1. **Network Security**
   ```yaml
   networks:
     sandbox-network:
       driver: bridge
       internal: true  # No external access
   ```

2. **Resource Monitoring**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1.0'
         memory: 1G
       reservations:
         cpus: '0.5'
         memory: 512M
   ```

3. **Logging**
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

### Scaling

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  notebook-sandbox:
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

## License

This sandbox environment is part of the ThinkForge project and follows the same licensing terms.