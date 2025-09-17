# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ThinkForge is a natural language cache framework that maps NL queries to structured outputs (SQL, API calls, URLs, workflows) using semantic similarity search. The system uses vector embeddings to find relevant cached entries and supports entity extraction/substitution for dynamic templates.

The framework includes recipe analysis capabilities that parse natural language workflows into structured steps and map them to available tools using advanced similarity search and confidence scoring algorithms.

## Architecture

### Core Components
- **Backend**: FastAPI server (`backend/`) with ThinkForge framework (`thinkforge/`)
- **Frontend**: React + Vite app (`frontend-react/`) - current implementation
- **Database**: PostgreSQL with optional pgvector extension for vector operations
- **Framework Library**: Core business logic in `thinkforge/` module

### Key Modules
- `thinkforge/controller.py` - Main orchestration and business logic
- `thinkforge/models.py` - SQLAlchemy ORM models with enums
- `thinkforge/similarity.py` - Vector embeddings and similarity computation  
- `thinkforge/entity_substitution.py` - Dynamic parameter replacement
- `thinkforge/workflow_compiler.py` - Multi-step workflow execution
- `thinkforge/recipe_step_analyzer.py` - Natural language recipe parsing
- `thinkforge/recipe_tool_mapper.py` - Recipe step to tool mapping via similarity
- `thinkforge/confidence_engine.py` - Tool matching confidence scoring
- `thinkforge/hotcommands_controller.py` - Hot commands functionality
- `thinkforge/spaces_service.py` - Collaborative spaces management
- `thinkforge/llm_step_processor.py` - LLM-powered step processing
- `thinkforge/execution_engine.py` - Template execution and orchestration

## Development Commands

### Backend Development
```bash
# Install backend dependencies and setup
cd backend && pip install -r requirements.txt

# Install thinkforge package in development mode (from root)
pip install -e .

# Start backend server (recommended)
cd backend && bash start.sh

# Alternative: Run backend server directly
python backend/app.py
# or with uvicorn for development with auto-reload
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# Initialize database schema
python dbscripts/init_schema.py

# Run individual components for testing
python -m thinkforge.controller  # Test controller functionality
python -m thinkforge.similarity  # Test similarity computations
```

### Frontend Development  
```bash
# Current React frontend (primary)
cd frontend-react
npm install
npm run dev      # Start dev server on port 3000
npm run build    # Build for production
npm run lint     # Run ESLint

# Root-level commands (runs frontend-react)
npm run dev      # Starts Vite dev server on port 3001
npm run build    # TypeScript compile + Vite build
npm run lint     # ESLint check

# Legacy Next.js frontend (reference only)
cd frontend
npm install && npm run dev  # Port 3000
```

### Testing
```bash
# Run all tests using the test runner
python tests/run_tests.py

# Run individual test files directly
python tests/test_controller.py
python tests/api_integration_test.py
python tests/simple_test.py

# Test specific components interactively
python -c "from thinkforge.similarity import Text2SQLSimilarity; s = Text2SQLSimilarity(); print('Similarity utility working')"
python -c "from thinkforge.controller import Text2SQLController; print('Controller module loads correctly')"

# Run pytest if configured (alternative method)
python -m pytest tests/ -v
```

### Docker Operations
```bash
# Full stack
docker-compose up

# Backend only
docker build -f backend/Dockerfile -t thinkforge-backend .
docker run -p 8000:8000 thinkforge-backend
```

## Database Schema

### Primary Tables
- **text2sql_cache**: Main cache entries with embeddings, templates, and metadata
  - Supports multiple `template_type` values: sql, url, api, workflow, graphql, etc.
  - Contains `vector_embedding` (JSONB) and optional `pg_vector` field
  - Has `status` field (active/pending/archive) and entity replacement data

- **usage_log**: Analytics tracking with cache hits/misses, similarity scores, LLM usage
- **cache_audit_log**: Field-level change history with user attribution
- **hotcommands**: Custom user commands and shortcuts
- **spaces**: Collaborative workspaces with access control
- **users**: User management and authentication

### Template Types
The system supports these template types (defined in `TemplateType` enum):
- **Core Types**: `sql`, `url`, `api`, `workflow`, `graphql`, `regex`, `script`, `nosql`, `cli`
- **AI/LLM Types**: `prompt`, `reasoning_steps`, `dsl`, `llm_step`
- **Tool Types**: `mcp_tool`, `agent`, `function` (for tool registry)
- **Recipe Types**: `recipe`, `recipe_step`, `recipe_template` (for workflow compilation)
- **Other**: `configuration`

## API Structure

### Core Endpoints
- `POST /v1/complete` - Main completion with similarity search and LLM enhancement
- `GET/POST/PUT/DELETE /v1/cache[/{id}]` - CRUD operations for cache entries
- `GET /v1/cache/search` - Similarity search functionality
- `POST /v1/cache/{id}/apply` - Apply entity substitution to templates
- `GET /v1/cache/stats` - Usage statistics and analytics
- `POST /v1/upload/csv` - Bulk import from CSV files with column mapping
- `POST /v1/upload/swagger` - Import from OpenAPI specs with execution_config extraction

### Recipe & Workflow Endpoints
- `POST /v1/recipes/analyze-natural-language` - Parse natural language recipes into structured steps
- `POST /v1/recipes/rewrite-step` - Reanalyze single recipe step with new description
- `POST /v1/recipes/{id}/compile` - Compile recipes to workflow formats (Langchain, Langflow, etc.)
- `POST /v1/workflows/generate` - Generate workflows from natural language using LLM
- `GET /v1/cache/compatible` - Get cache entries compatible as workflow steps

### Hot Commands & Spaces Endpoints
- `GET/POST/PUT/DELETE /v1/hotcommands[/{id}]` - Manage custom user commands
- `POST /v1/hotcommands/{id}/execute` - Execute hot commands
- `GET/POST/PUT/DELETE /v1/spaces[/{id}]` - Manage collaborative spaces
- `POST /v1/spaces/{id}/share` - Share spaces with other users

### LLM Integration Endpoints
- `POST /v1/llm/process-step` - Process individual steps with LLM
- `POST /v1/llm/enhance-template` - Enhance templates with LLM reasoning

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=thinkforge

# AI/ML
DEFAULT_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
SIMILARITY_THRESHOLD=0.85
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=google/gemini-pro

# Application
PORT=8000
DB_SCHEMA=public
USE_PG_VECTOR=false
DEBUG=true
```

## Development Workflow

### Adding New Features
1. Update models in `thinkforge/models.py` if schema changes needed
2. Add business logic to `thinkforge/controller.py`
3. Create API endpoints in `backend/app.py`
4. Add frontend components in `frontend-react/src/`
5. Update database schema via `dbscripts/` if needed
6. Write tests in `tests/` directory

### Entity Substitution System
- Templates use placeholders like `{entity_name}` for dynamic values
- `entity_substitution.py` handles extraction and replacement
- Different substitution logic for each template type (SQL, URL, API, etc.)
- Entity mappings stored in `entity_replacements` JSONB field

### Similarity Search Architecture  
- Uses sentence-transformers for generating embeddings
- Cosine similarity comparison via numpy operations
- Optional pgvector extension for database-level vector operations
- Fallback to string similarity (SequenceMatcher) for non-vector comparisons

## Frontend Architecture

### Current React App (`frontend-react/`)
- Uses React Router for navigation
- Tailwind CSS + Radix UI components
- Chart.js/Recharts for analytics visualizations
- Key pages: Cache management, Test completion, Usage logs, Statistics, Hot Commands, Spaces
- API client in `src/services/api.ts`
- Theme provider with dark/light mode support

### Legacy Next.js App (`frontend/`)
- Preserved for reference, similar functionality
- Uses Next.js App Router pattern

## Testing Strategy

- Unit tests focus on controller logic and similarity computations
- Integration tests cover API endpoints and database operations  
- Manual testing via frontend test completion interface
- Test runner script: `tests/run_tests.py`

## Recipe Analysis Architecture

### Recipe Processing Pipeline
1. **Step Analyzer** (`RecipeStepAnalyzer`) - Parses natural language into structured steps with action verbs and entities
2. **Tool Mapper** (`RecipeToolMapper`) - Maps steps to available tools via multi-phase similarity search
3. **Confidence Engine** (`ConfidenceEngine`) - Scores tool matches for reliability using weighted scoring
4. **Recipe Compiler** (`RecipeCompiler`) - Compiles recipes to executable workflow formats

### Tool Mapping Strategy
- **Multi-phase Search**: Semantic → Broad → Keyword → Ultra-broad fallback
- **Similarity Thresholds**: Uses proven thresholds from `/v1/complete` endpoint (0.6 initial, 0.4 fallback)
- **Tool Type Expansion**: Includes function, api, mcp_tool, agent, sql, url, workflow, script, cli types
- **OR-Logic Catalog Filtering**: Matches approach used by other successful endpoints

### Workflow Compilation Formats
- **Langchain**: LCEL (LangChain Expression Language) format
- **Langflow**: JSON format for visual workflow execution
- **Langgraph**: Stateful graph execution format
- **Generic**: Generic workflow format with execution plan

## Tool Registry & Execution

### Tool Types & Execution Config
- Tools stored in `text2sql_cache` table with `template_type` and `execution_config`
- `execution_config` contains runtime parameters (URLs, timeouts, headers) for API tools
- Swagger/OpenAPI import automatically extracts and populates execution configuration
- Frontend displays execution config with endpoint URLs, methods, and parameters

### Tool Capabilities
- `tool_capabilities`: Array of capabilities/features the tool provides
- `tool_dependencies`: JSON object defining required dependencies
- `health_status`: Current operational status (healthy/degraded/unhealthy/unknown)

## Hot Commands System

### Purpose & Architecture
- Custom user-defined commands and shortcuts for frequently used operations
- Stored in `hotcommands` table with execution templates and metadata
- Supports templating with variable substitution
- Integration with ThinkForge similarity search for command discovery

### Command Types
- Direct SQL queries with parameter substitution
- API calls with dynamic endpoints and payloads
- Multi-step workflows combining multiple operations
- Shell commands with safety restrictions

## Spaces System

### Collaborative Features
- Shared workspaces for teams and projects
- Access control with role-based permissions (owner, editor, viewer)
- Template sharing and collaboration
- Space-specific analytics and usage tracking

### Storage Backends
- Local filesystem storage
- Cloud storage (S3, GCS, Azure Blob)
- Space-specific configuration and templates

## Important Notes

- The project has both `frontend/` (Next.js, legacy) and `frontend-react/` (current Vite-based)
- Vector embeddings can use either JSONB storage or pgvector extension
- LLM integration is optional for template generation and enhancement (requires OPENROUTER_API_KEY)
- Supports multiple embedding models via sentence-transformers
- Template validation ensures quality before caching
- Usage logging tracks performance metrics and user patterns
- Recipe analysis uses real similarity search against database tools
- Execution config enables actual tool invocation with proper parameters
- Hot commands provide user customization and workflow automation
- Spaces enable team collaboration and shared template libraries

## Troubleshooting

### Backend Issues
- If database connection fails, check PostgreSQL service and environment variables
- If embeddings fail to generate, verify sentence-transformers model availability
- For LLM integration issues, verify OPENROUTER_API_KEY is set correctly

### Recipe Analysis Issues
- If recipe analysis shows "0 tools available", check that catalog filtering uses OR logic not strict equality
- Ensure similarity thresholds match proven `/v1/complete` approach (0.6 initial, lower fallback)
- Verify tool type matching includes broad types (function, api, mcp_tool, agent, sql, url, workflow, script, cli)
- Check that semantic search preserves original query context instead of transforming to keywords

### Frontend Issues
- CatalogSelect component should support hierarchical filtering with catalogType/catalogSubtype props
- API calls should use query parameters for filtering: `/v1/catalog/values?catalog_type=X&catalog_subtype=Y`
- Dropdown cascading should clear child selections when parent values change
- For development server issues, try clearing Vite cache: `./clear_vite_cache.sh`

### Testing Issues
- Run database initialization before tests: `python dbscripts/init_schema.py`
- Ensure all dependencies installed: `pip install -r backend/requirements.txt`
- For frontend tests, ensure Node.js dependencies: `cd frontend-react && npm install`