# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ThinkForge is a natural language cache framework that maps NL queries to structured outputs (SQL, API calls, URLs, workflows) using semantic similarity search. The system uses vector embeddings to find relevant cached entries and supports entity extraction/substitution for dynamic templates.

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

## Development Commands

### Backend Development
```bash
# Install backend dependencies
cd backend && pip install -r requirements.txt

# Install thinkforge package in development mode
pip install -e .

# Run backend server
python backend/app.py
# or with uvicorn
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# Run database migrations
python dbscripts/init_schema.py
```

### Frontend Development  
```bash
# Current React frontend
cd frontend-react
npm install
npm run dev      # Start dev server on port 3000
npm run build    # Build for production
npm run lint     # Run ESLint

# Root-level commands (for frontend-react)
npm run dev      # Runs on port 3001
npm run build    # TypeScript compile + Vite build
npm run lint     # ESLint check
```

### Testing
```bash
# Run all tests
python tests/run_tests.py

# Individual test files
python tests/test_controller.py
python tests/api_integration_test.py
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

### Template Types
The system supports these template types (defined in `TemplateType` enum):
- `sql`, `url`, `api`, `workflow`, `graphql`, `regex`, `script`, `nosql`, `cli`
- `prompt`, `configuration`, `reasoning_steps`, `dsl`

## API Structure

### Core Endpoints
- `POST /v1/complete` - Main completion with similarity search
- `GET/POST/PUT/DELETE /v1/cache[/{id}]` - CRUD operations for cache entries
- `GET /v1/cache/search` - Similarity search functionality
- `POST /v1/cache/{id}/apply` - Apply entity substitution
- `GET /v1/cache/stats` - Usage statistics
- `POST /v1/upload/csv` - Bulk import from CSV files
- `POST /v1/upload/swagger` - Import from OpenAPI specs

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
- Key pages: Cache management, Test completion, Usage logs, Statistics
- API client in `src/services/api.ts`

### Legacy Next.js App (`frontend/`)
- Preserved for reference, similar functionality
- Uses Next.js App Router pattern

## Testing Strategy

- Unit tests focus on controller logic and similarity computations
- Integration tests cover API endpoints and database operations  
- Manual testing via frontend test completion interface
- No specific test framework configured - uses standard Python unittest

## Important Notes

- The project has both `frontend/` (Next.js) and `frontend-react/` (current Vite-based)
- Vector embeddings can use either JSONB storage or pgvector extension
- LLM integration is optional for template generation and enhancement
- Supports multiple embedding models via sentence-transformers
- Template validation ensures quality before caching
- Usage logging tracks performance metrics and user patterns