# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Recipe Hub is a Recipe-Driven Automation Framework for Langflow that transforms incident management into deterministic, explorable workflows. It's a sophisticated automation platform built with FastAPI (backend), Next.js (frontend), and PostgreSQL with pgvector for vector embeddings.

## Development Commands

### Backend (Python)
```bash
# Setup and start services
cp .env.example .env  # Configure environment variables
python setup_database.py  # Initialize PostgreSQL database
./start.sh  # Interactive startup script

# Manual service startup
python run_server.py  # Start FastAPI API server (port 8000)
python run_worker.py  # Start Celery background worker

# CLI tool
python -m cli.main --help  # Use flowctl CLI
python -m cli.main recipe new my_recipe  # Create new recipe

# Code quality
black .  # Format code
isort .  # Sort imports
mypy app/ cli/  # Type checking
pytest  # Run tests
pytest tests/  # Run specific test directory
```

### Frontend (Next.js)
```bash
cd frontend/app
npm run dev  # Development server (port 3000)
npm run build  # Production build
npm run start  # Start production server
npm run lint  # ESLint
```

## Architecture Overview

### Core Components
- **Recipe Hub**: Database-backed knowledge base for automation recipes with versioning
- **Tool Registry**: Declarative catalog of APIs, MCP verbs, agents, and subflows
- **Compiler/Validator**: Converts recipes + context into validated Langflow-compatible flows
- **LLM Adapter**: Dynamic recipe adaptation using OpenRouter/Claude with similarity search
- **Langflow Runner**: Executes flows with observability and interactive modes

### Key Directories
```
app/
├── api/endpoints/     # FastAPI route handlers (auth, users, recipes, tools, health)
├── core/             # Configuration, security, database setup
├── models/           # SQLAlchemy database models with soft delete and versioning
├── schemas/          # Pydantic data validation schemas
├── services/         # Business logic (compiler, embedding, LLM, recipe services)
└── tasks/           # Celery background tasks

cli/                 # flowctl CLI tool with Click commands
frontend/app/        # Next.js app with Radix UI, TanStack Query, Monaco Editor
tests/              # Pytest test suites with async support
```

### Database Models
- **Recipe/RecipeVersion**: Versioned recipes with JSON content, embeddings, status lifecycle
- **Tool/ToolVersion**: Tool registry with input/output schemas, RBAC, metrics
- **User**: Authentication with JWT, roles, permissions
- All models use SoftDeleteMixin, timestamps, and author tracking

### Technology Stack
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + pgvector + Celery + Redis
- **Frontend**: Next.js + TypeScript + Radix UI + TailwindCSS + TanStack Query
- **AI/ML**: OpenAI (OpenRouter), Sentence Transformers, LangChain, Langflow
- **Auth**: JWT with NextAuth, RBAC system
- **Observability**: OpenTelemetry, Prometheus metrics
- **Dev Tools**: Black, isort, mypy, pytest, ESLint

## Key Patterns

### Recipe Management
- Recipes are stored as Langflow-compatible JSON with semantic versioning
- Status lifecycle: Draft → Published → Deprecated → Archived
- Vector embeddings for similarity search using sentence-transformers
- Complete audit trail with RecipeVersion model

### Tool Registry
- Tools defined declaratively with JSON schemas for inputs/outputs
- Types: API endpoints, MCP verbs, agent workflows, subflows
- Security: sandbox flags, approval requirements, RBAC integration
- Performance tracking: usage metrics, cost monitoring

### Authentication & Authorization
- JWT-based with role-based access control (RBAC)
- User model with permissions and preferences
- Superuser administrative capabilities
- Frontend uses NextAuth with Prisma adapter

### Development Workflow
- Use `flowctl` CLI for recipe/tool management and testing
- Database-first approach with Alembic migrations
- Comprehensive test setup with pytest and async support
- Code quality enforced with Black, isort, mypy

## Configuration

### Environment Setup
- Copy `.env.example` to `.env` and configure:
  - Database connection (PostgreSQL with pgvector)
  - Redis connection for Celery
  - OpenRouter API key for LLM integration
  - JWT secret and other security settings

### Database
- Requires PostgreSQL with pgvector extension
- Run `python setup_database.py` to initialize
- Alembic for migrations in `migrations/` directory

### Services Dependencies
- PostgreSQL database with pgvector
- Redis for Celery task queue
- Langflow runtime for flow execution
- OpenRouter API for LLM services

## Important Notes

- Always run code quality tools (black, isort, mypy) before committing
- Use the CLI tool for recipe/tool operations rather than direct database manipulation
- Frontend communicates with backend API, not database directly
- All models use soft delete pattern - check `deleted_at` field
- Vector embeddings are automatically generated for recipes on save
- Recipe compilation is asynchronous via Celery tasks