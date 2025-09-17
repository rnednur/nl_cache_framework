# Recipe Hub - Recipe-Driven Automation Framework

A sophisticated automation framework that transforms incident management into deterministic, explorable workflows using Langflow.

## Architecture Overview

The Recipe Hub framework consists of:

- **Recipe Hub**: Database-backed knowledge base for automation recipes
- **Tool Registry**: Declarative catalog of APIs, agents, and workflows
- **Compiler/Validator**: Converts recipes to validated Langflow-compatible flows
- **LLM Adapter**: Dynamic recipe adaptation using similarity search
- **Langflow Runner**: Executes flows with observability and interactive modes

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Set up database (requires PostgreSQL running)
python setup_database.py

# Start the services
./start.sh

# Or start manually:
python run_server.py     # API server
python run_worker.py     # Background tasks

# Use CLI tools
python -m cli.main recipe new my_recipe
```

## Project Structure

```
recipe_hub/
├── app/                    # FastAPI backend
│   ├── api/               # API routes
│   ├── core/              # Configuration and security
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   └── schemas/           # Pydantic schemas
├── frontend/              # React web UI
├── cli/                   # flowctl CLI tool
├── migrations/            # Database migrations
├── tests/                 # Test suites
└── deployment/            # Docker and K8s configs
```

## Key Features

- 📝 **Recipe Authoring**: Schema-aware JSON editor with live validation
- 🔧 **Tool Registry**: Centralized catalog of automation tools and APIs
- 🤖 **LLM Integration**: Dynamic recipe adaptation based on ticket context
- ⚡ **Langflow Execution**: Native integration with Langflow runtime
- 📊 **Observability**: Full tracing and monitoring with OpenTelemetry
- 🛡️ **Security**: RBAC, policy enforcement, and sandbox execution
- 🔄 **Versioning**: Complete audit trail and rollback capabilities

## Documentation

- [Getting Started](docs/getting-started.md)
- [Recipe Specification](docs/recipe-spec.md)
- [Tool Registry](docs/tool-registry.md)
- [API Reference](docs/api-reference.md)
- [Deployment Guide](docs/deployment.md)

## License

MIT License - see LICENSE file for details.