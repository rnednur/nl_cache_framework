# Recipe Hub - Comprehensive Feature Document

> **Recipe-Driven Automation Framework for Langflow**  
> Transform incident management into deterministic, explorable workflows

## Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
  - [Authentication & User Management](#authentication--user-management)
  - [Recipe Management System](#recipe-management-system)
  - [Tool Registry System](#tool-registry-system)
  - [Flow Compilation & Execution](#flow-compilation--execution)
  - [AI/ML Integration](#aiml-integration)
  - [Frontend Web Application](#frontend-web-application)
  - [System Health & Monitoring](#system-health--monitoring)
  - [Background Processing](#background-processing)
  - [CLI Tool (flowctl)](#cli-tool-flowctl)
- [Planned Features](#planned-features)
- [Future Enhancements](#future-enhancements)
- [Technical Architecture](#technical-architecture)

---

## Overview

Recipe Hub is a sophisticated automation platform that transforms incident management workflows into deterministic, explorable automation recipes. Built with enterprise-grade architecture using FastAPI, Next.js, and PostgreSQL with vector embeddings, it provides a comprehensive solution for creating, managing, and executing automation workflows.

**Key Value Propositions:**
- **Deterministic Workflows**: Convert ad-hoc incident responses into repeatable, versioned recipes
- **AI-Powered Adaptation**: Dynamic recipe modification based on context using LLM integration
- **Comprehensive Tool Registry**: Centralized catalog of APIs, agents, and automation tools
- **Vector-Based Discovery**: Semantic search for similar recipes and contextual recommendations
- **Enterprise Security**: Full RBAC, audit trails, and security validation

---

## Core Features

### Authentication & User Management

#### ✅ **JWT-Based Authentication System**
- **Location**: `app/core/security.py`, `app/api/endpoints/auth.py`
- **Features**:
  - Secure JWT token generation with configurable expiration (30 minutes default)
  - Bearer token authentication with refresh capability
  - Password hashing using bcrypt
  - Token refresh mechanism for seamless user experience

- **API Endpoints**:
  - `POST /auth/register` - User registration with email/username uniqueness
  - `POST /auth/login` - User authentication
  - `POST /auth/refresh` - Token refresh
  - `GET /auth/me` - Current user profile retrieval

#### ✅ **User Management System**
- **Location**: `app/models/user.py`, `app/api/endpoints/users.py`
- **Database Features**:
  - Soft delete functionality with audit trails
  - Role-based access control (RBAC) with flexible JSON roles
  - Granular permissions system with JSON permissions dictionary
  - User preferences storage for personalization
  - Superuser designation with administrative privileges

- **API Endpoints**:
  - `GET /users/` - List all users (superuser only)
  - `GET /users/{id}` - Get user details (self or superuser)
  - `PATCH /users/{id}` - Update user information (self or superuser)

#### ✅ **Authorization Framework**
- Permission-based access control functions
- Role-based access control with inheritance
- Resource ownership validation
- Superuser privilege escalation mechanisms

---

### Recipe Management System

#### ✅ **Recipe Database Models**
- **Location**: `app/models/recipe.py`
- **Recipe Model Features**:
  - **Metadata**: Name, version, title, description, tags
  - **Status Lifecycle**: Draft → Published → Deprecated → Archived
  - **Content Storage**: Langflow-compatible JSON format
  - **Vector Embeddings**: 384-dimensional embeddings for semantic search
  - **Usage Analytics**: Execution count, success rate, performance metrics
  - **Audit Trail**: Complete version history with author attribution

- **RecipeVersion Model**:
  - Complete version history tracking
  - Change summaries and migration notes
  - Author attribution per version
  - Backward compatibility management

#### ✅ **Recipe API Layer**
- **Location**: `app/api/endpoints/recipes.py`
- **Endpoints**:
  - `GET /recipes/` - List recipes with advanced filtering and access control
  - `POST /recipes/` - Create new recipe with validation and uniqueness checks
  - `GET /recipes/{id}` - Get recipe by ID with permission verification
  - `PATCH /recipes/{id}` - Update recipe with automatic versioning
  - `DELETE /recipes/{id}` - Soft delete with cleanup

#### ✅ **Recipe Service Layer**
- **Location**: `app/services/recipe_service.py`
- **Core Capabilities**:
  - Recipe creation with automatic embedding generation
  - Version management and complete audit trails
  - **Vector Similarity Search**: Find similar recipes using embeddings
  - Usage statistics calculation and reporting
  - Publication workflow management with status transitions

- **Advanced Search Features**:
  - Text-based search (title, description, content)
  - Tag-based filtering with multiple tag support
  - Status-based filtering for workflow management
  - Author-based filtering for ownership tracking
  - Vector similarity search with configurable similarity threshold

#### ✅ **CLI Recipe Commands**
- **Location**: `cli/commands/recipe.py`
- **Available Commands**:
  - `flowctl recipe list` - List recipes with filtering options
  - `flowctl recipe create <file>` - Create from YAML/JSON file
  - `flowctl recipe get <id>` - Retrieve recipe details
  - `flowctl recipe new <name>` - Interactive recipe creation wizard

---

### Tool Registry System

#### ✅ **Tool Database Models**
- **Location**: `app/models/tool.py`
- **Tool Model Features**:
  - **Tool Types**: API endpoints, MCP verbs, Agent workflows, Subflows, LLM integrations
  - **Schema Definition**: Input/output JSON schemas with validation
  - **Execution Configuration**: Timeout, retry logic, delay settings
  - **Security Settings**: RBAC roles, approval requirements, sandbox safety flags
  - **Performance Metrics**: Usage tracking, success rates, cost analysis
  - **Documentation**: Comprehensive docs with examples

- **ToolVersion Model**:
  - Backward compatibility tracking
  - Breaking change notifications
  - Deprecation management with replacement suggestions

#### ✅ **Tool API Layer**
- **Location**: `app/api/endpoints/tools.py`
- **Endpoints**:
  - `GET /tools/` - List tools with type and category filtering
  - `POST /tools/` - Create new tool with schema validation
  - `GET /tools/{id}` - Get tool details with access control
  - `PATCH /tools/{id}` - Update tool configuration
  - Tool deletion support with soft delete

#### ✅ **CLI Tool Commands**
- **Location**: `cli/commands/tool.py`
- **Available Commands**:
  - `flowctl tool list` - List available tools with filtering
  - `flowctl tool scaffold <name>` - Create tool template with boilerplate

---

### Flow Compilation & Execution

#### ✅ **Flow Database Models**
- **Location**: `app/models/flow.py`
- **Flow Model Features**:
  - **Unique Identification**: UUID-based flow identification
  - **Content Storage**: Langflow-compatible JSON with validation
  - **Validation Status**: Pending, Valid, Invalid, Warning states
  - **Security Approval**: Workflow-based approval process
  - **Cost Estimation**: Token usage and USD cost prediction
  - **Content Integrity**: SHA-256 hashing for tamper detection

- **FlowExecution Model**:
  - **Execution Modes**: Batch, Interactive, Shadow testing
  - **Status Tracking**: Pending → Running → Completed/Failed/Cancelled
  - **Performance Metrics**: Execution time, resource usage, cost tracking
  - **Observability**: Traces, spans, logs integration
  - **User Interaction**: Agent step tracking and user input handling
  - **Approval Workflow**: Multi-stage approval support

#### ✅ **Flow API Layer**
- **Location**: `app/api/endpoints/flows.py`
- **Endpoints**:
  - `GET /flows/` - List compiled flows with comprehensive filtering
  - `POST /flows/compile` - Compile recipe to Langflow-compatible flow
  - `POST /flows/` - Create flow directly with validation
  - `GET /flows/{id}` - Get flow details with execution history
  - `POST /flows/{id}/execute` - Execute flow with mode selection
  - `GET /flows/{id}/executions` - List flow executions with filtering
  - `POST /flows/{id}/validate` - Validate compiled flow integrity

#### ✅ **Compiler Service**
- **Location**: `app/services/compiler_service.py`
- **Core Compilation Features**:
  - **Recipe-to-Langflow Conversion**: Transform recipes into executable flows
  - **Variable Substitution**: Template syntax with context-aware replacement
  - **Tool Validation**: Dependency checking and compatibility verification
  - **LLM-Based Adaptation**: Dynamic recipe modification using AI
  - **Security Validation**: Policy enforcement and security scanning

- **Advanced Features**:
  - Similar recipe discovery for contextual enhancement
  - Content hash generation for integrity verification
  - Compilation metadata tracking
  - Version compatibility checking and migration

#### ✅ **CLI Flow Commands**
- **Location**: `cli/commands/flow.py`
- **Available Commands**:
  - `flowctl flow list` - List compiled flows with status
  - `flowctl flow compile <recipe_id>` - Compile recipe with context
  - `flowctl flow execute <flow_id>` - Execute compiled flow
  - `flowctl flow executions <flow_id>` - List execution history
  - `flowctl flow validate <flow_id>` - Validate flow integrity

---

### AI/ML Integration

#### ✅ **LLM Service**
- **Location**: `app/services/llm_service.py`
- **OpenRouter Integration**:
  - Multiple model support (default: Claude 3.5 Sonnet)
  - Configurable model selection and parameters
  - Cost tracking and token usage monitoring

- **Core AI Features**:
  - **Dynamic Recipe Adaptation**: Modify recipes based on incident context
  - **Recipe Summary Generation**: Human-readable workflow descriptions
  - **Syntax Validation**: AI-powered JSON schema validation
  - **Security Analysis**: Automated security consideration assessment

#### ✅ **Embedding Service**
- **Location**: `app/services/embedding_service.py`
- **Vector Embeddings**:
  - Sentence-transformers integration (MiniLM-L6-v2 model)
  - 384-dimensional embeddings for semantic representation
  - Batch processing support for efficiency
  - Cosine similarity calculations

- **Search Capabilities**:
  - Text preprocessing and optimization
  - Similarity threshold filtering
  - Top-K result retrieval with ranking

#### ✅ **Background AI Tasks**
- **Location**: `app/tasks/`
- **Embedding Tasks**:
  - Single recipe embedding generation
  - Batch embedding processing for large datasets
  - Similarity index maintenance and updates

- **LLM Tasks**:
  - Asynchronous recipe adaptation
  - Batch recipe analysis and improvement
  - Recipe summary generation
  - AI-powered validation and recommendations

---

### Frontend Web Application

#### ✅ **Main Application Pages**
- **Location**: `frontend/app/app/`
- **Core Pages**:
  - **Dashboard**: System overview with statistics, recent executions, popular recipes
  - **Recipes Page**: Comprehensive recipe management with filtering, pagination, CRUD
  - **Tools Page**: Tool registry management with category filtering and search
  - **Executions Page**: Flow execution monitoring with real-time status updates
  - **User Management**: User profiles and administrative functions

#### ✅ **UI Component Library**
- **Recipe Components**: Recipe cards, advanced filters, Monaco JSON editor, form builders
- **Tool Components**: Tool cards, category filters, schema editors, form builders
- **Execution Components**: Execution cards, status badges, progress indicators, flow compiler
- **Layout Components**: Responsive header, collapsible sidebar, main layout
- **Authentication Components**: Login/register forms, protected routes, session management

#### ✅ **Frontend Architecture**
- **Technology Stack**: React/Next.js with TypeScript
- **UI Framework**: Radix UI component library with TailwindCSS
- **State Management**: TanStack Query for server state and API integration
- **Real-time Features**: Execution monitoring with live updates
- **Responsive Design**: Mobile-first approach with adaptive layouts

---

### System Health & Monitoring

#### ✅ **Health Check System**
- **Location**: `app/api/endpoints/health.py`
- **Endpoints**:
  - `GET /health/` - Basic system health status
  - `GET /health/detailed` - Comprehensive health with dependency checks
  - `GET /health/ready` - Kubernetes readiness probe
  - `GET /health/live` - Kubernetes liveness probe

#### ✅ **Monitoring Capabilities**
- **Infrastructure Monitoring**:
  - Database connectivity validation
  - Redis connectivity and performance checks
  - Langflow integration health verification
  - External service dependency monitoring

- **Observability Stack**:
  - OpenTelemetry tracing integration
  - Prometheus metrics collection
  - Structured logging with correlation IDs
  - Performance monitoring and alerting

---

### Background Processing

#### ✅ **Celery Integration**
- **Location**: `app/worker.py`, `run_worker.py`
- **Features**:
  - Redis-based distributed task queue
  - Scalable worker processes
  - Task result tracking and persistence
  - Comprehensive error handling and retry logic
  - Dead letter queue for failed tasks

#### ✅ **Background Task Categories**
- **AI/ML Tasks**: Recipe embedding generation, LLM-based adaptation
- **System Tasks**: Database maintenance, cleanup operations
- **User Tasks**: Batch processing, report generation
- **Integration Tasks**: External API synchronization

---

### CLI Tool (flowctl)

#### ✅ **CLI Framework**
- **Location**: `cli/main.py`
- **Core Features**:
  - Configuration file support (YAML/JSON)
  - Environment variable integration
  - Command grouping with contextual help
  - Comprehensive error handling and user feedback
  - Interactive command wizards

#### ✅ **Command Categories**
- **Recipe Commands**: Create, list, get, new, validate, search
- **Tool Commands**: List, scaffold, test
- **Flow Commands**: Compile, execute, validate, list executions
- **System Commands**: Health checks, configuration management

---

## Planned Features

### 🔄 **In Development**

#### **Recipe Validation Enhancement**
- **Status**: CLI command exists but backend validation not implemented
- **Location**: `cli/commands/recipe.py:167`
- **Scope**: Comprehensive recipe syntax and semantic validation
- **Timeline**: Next sprint

#### **Tool Testing Framework**
- **Status**: CLI command exists but testing endpoint not implemented
- **Location**: `cli/commands/tool.py:95`
- **Scope**: Automated tool execution testing with mocking
- **Timeline**: Q2 2024

#### **Recipe Similarity Search CLI**
- **Status**: Backend implemented, CLI command pending
- **Location**: `cli/commands/recipe.py:184`
- **Scope**: Command-line interface for vector similarity search
- **Timeline**: Next release

#### **Flow Execution Queuing**
- **Status**: Architecture planned, Celery integration pending
- **Location**: `app/api/endpoints/flows.py:165`
- **Scope**: Asynchronous flow execution with queue management
- **Timeline**: Q2 2024

### 📋 **Roadmap Features**

#### **Recipe Versioning UI**
- Enhanced frontend for version management
- Visual diff capabilities
- Rollback functionality
- Migration assistant

#### **Advanced Analytics Dashboard**
- Recipe performance analytics
- Usage pattern analysis
- Cost optimization recommendations
- Success rate trending

#### **Real-time Collaboration**
- Multi-user recipe editing
- Comment system
- Change notifications
- Conflict resolution

#### **Enhanced Security Framework**
- Advanced policy engine
- Security scanning integration
- Compliance reporting
- Audit log visualization

---

## Future Enhancements

### 🚀 **Strategic Initiatives**

#### **Tool Marketplace Integration**
- **Vision**: Community-driven tool sharing platform
- **Features**:
  - Tool publishing and distribution
  - Rating and review system
  - Version compatibility matrix
  - Security certification process

#### **Recipe Template Library**
- **Vision**: Curated collection of automation templates
- **Features**:
  - Industry-specific templates
  - Best practice recipes
  - Template customization wizard
  - Community contributions

#### **Advanced Workflow Engine**
- **Vision**: Enhanced flow execution with advanced patterns
- **Features**:
  - Conditional branching and loops
  - Error handling strategies
  - Workflow orchestration
  - Event-driven automation

#### **Machine Learning Optimization**
- **Vision**: AI-powered workflow optimization
- **Features**:
  - Performance prediction
  - Resource optimization
  - Automated A/B testing
  - Anomaly detection

### 🔧 **Technical Enhancements**

#### **Scalability Improvements**
- Horizontal scaling architecture
- Caching layer optimization
- Database sharding strategy
- CDN integration for assets

#### **Developer Experience**
- GraphQL API layer
- SDK development (Python, JavaScript)
- Enhanced CLI with auto-completion
- Development environment containerization

#### **Integration Ecosystem**
- Webhook system for external integrations
- Plugin architecture for extensions
- Third-party service connectors
- API gateway integration

---

## Technical Architecture

### **Current Stack**
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + pgvector + Celery + Redis
- **Frontend**: Next.js + TypeScript + Radix UI + TailwindCSS + TanStack Query
- **AI/ML**: OpenAI (OpenRouter), Sentence Transformers, LangChain, Langflow
- **Auth**: JWT with NextAuth, RBAC system
- **Observability**: OpenTelemetry, Prometheus metrics
- **Dev Tools**: Black, isort, mypy, pytest, ESLint

### **Key Design Patterns**
- **Database-First Architecture**: SQLAlchemy models with comprehensive migrations
- **Service Layer Pattern**: Business logic separated from API controllers
- **Soft Delete Pattern**: All models support logical deletion with audit trails
- **Version Control Pattern**: Comprehensive versioning for recipes and tools
- **Event-Driven Architecture**: Celery tasks for asynchronous processing
- **Security-First Design**: RBAC, JWT, input validation, SQL injection prevention

### **Scalability Considerations**
- **Horizontal Scaling**: Stateless API design with external session storage
- **Database Optimization**: Vector indexing, query optimization, connection pooling
- **Caching Strategy**: Redis for session storage and task queuing
- **Background Processing**: Distributed task processing with Celery
- **Content Delivery**: Static asset optimization and CDN-ready architecture

---

**Last Updated**: July 28, 2025  
**Version**: 1.0.0  
**Maintainer**: Recipe Hub Development Team