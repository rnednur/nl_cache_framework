# Recipe Hub API Documentation

## Overview

The Recipe Hub API is a FastAPI-based backend that provides a comprehensive automation framework for creating, managing, and executing Langflow-compatible workflows. The API follows RESTful principles and uses JWT authentication.

**Base URL**: `http://localhost:8000/api/v1` (development)  
**Authentication**: JWT Bearer Token  
**Content-Type**: `application/json`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Users](#users)
3. [Recipes](#recipes)
4. [Tools](#tools)
5. [Flows](#flows)
6. [Health & Monitoring](#health--monitoring)
7. [Error Handling](#error-handling)
8. [Data Models](#data-models)

---

## Authentication

### Register User
**POST** `/auth/register`

Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "password": "securepassword123",
  "is_active": true,
  "is_superuser": false,
  "roles": ["user"],
  "permissions": {},
  "preferences": {}
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "is_active": true,
  "is_superuser": false,
  "roles": ["user"],
  "permissions": {},
  "preferences": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Login
**POST** `/auth/login`

Authenticate and receive access token.

**Request Body (form data):**
```
username: username
password: securepassword123
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Get Current User
**GET** `/auth/me`

Get current user information.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "is_active": true,
  "is_superuser": false,
  "roles": ["user"],
  "permissions": {},
  "preferences": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Refresh Token
**POST** `/auth/refresh`

Refresh the access token.

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Users

### List Users (Superuser Only)
**GET** `/users/`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100, max: 100)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "full_name": "Full Name",
    "is_active": true,
    "is_superuser": false,
    "roles": ["user"],
    "permissions": {},
    "preferences": {},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get User
**GET** `/users/{user_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "is_active": true,
  "is_superuser": false,
  "roles": ["user"],
  "permissions": {},
  "preferences": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update User
**PATCH** `/users/{user_id}`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "full_name": "Updated Name",
  "preferences": {
    "theme": "dark",
    "language": "en"
  }
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "full_name": "Updated Name",
  "is_active": true,
  "is_superuser": false,
  "roles": ["user"],
  "permissions": {},
  "preferences": {
    "theme": "dark",
    "language": "en"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## Recipes

### List Recipes
**GET** `/recipes/`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100, max: 100)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "voice_bearer_drop",
    "version": "1.0.0",
    "title": "Voice Bearer Drop Troubleshooting",
    "description": "Automated troubleshooting for voice bearer drops",
    "status": "published",
    "content": {
      "nodes": [
        {
          "id": "measure_optics",
          "agent": "netops_api.get_optics",
          "input": {"port": "cpri1", "device": "{{site_id}}"},
          "output_schema": {"rx_dbm": {"type": "number"}}
        }
      ]
    },
    "tags": ["RAN", "troubleshooting"],
    "required_plugins": ["mcp"],
    "schema_version": "1.0",
    "author_id": 1,
    "usage_count": 0,
    "success_rate": 0.0,
    "avg_execution_time": 0.0,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Create Recipe
**POST** `/recipes/`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "new_recipe",
  "version": "1.0.0",
  "title": "New Recipe Title",
  "description": "Recipe description",
  "status": "draft",
  "content": {
    "nodes": [
      {
        "id": "step1",
        "agent": "tool.example",
        "input": {"param": "value"},
        "output_schema": {"result": {"type": "string"}}
      }
    ]
  },
  "tags": ["automation"],
  "required_plugins": ["example_plugin"],
  "schema_version": "1.0"
}
```

**Response:** `201 Created`
```json
{
  "id": 2,
  "name": "new_recipe",
  "version": "1.0.0",
  "title": "New Recipe Title",
  "description": "Recipe description",
  "status": "draft",
  "content": {
    "nodes": [
      {
        "id": "step1",
        "agent": "tool.example",
        "input": {"param": "value"},
        "output_schema": {"result": {"type": "string"}}
      }
    ]
  },
  "tags": ["automation"],
  "required_plugins": ["example_plugin"],
  "schema_version": "1.0",
  "author_id": 1,
  "usage_count": 0,
  "success_rate": 0.0,
  "avg_execution_time": 0.0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Get Recipe
**GET** `/recipes/{recipe_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "voice_bearer_drop",
  "version": "1.0.0",
  "title": "Voice Bearer Drop Troubleshooting",
  "description": "Automated troubleshooting for voice bearer drops",
  "status": "published",
  "content": {
    "nodes": [
      {
        "id": "measure_optics",
        "agent": "netops_api.get_optics",
        "input": {"port": "cpri1", "device": "{{site_id}}"},
        "output_schema": {"rx_dbm": {"type": "number"}}
      }
    ]
  },
  "tags": ["RAN", "troubleshooting"],
  "required_plugins": ["mcp"],
  "schema_version": "1.0",
  "author_id": 1,
  "usage_count": 0,
  "success_rate": 0.0,
  "avg_execution_time": 0.0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update Recipe
**PATCH** `/recipes/{recipe_id}`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Updated Recipe Title",
  "description": "Updated description",
  "status": "published",
  "tags": ["RAN", "troubleshooting", "updated"]
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "voice_bearer_drop",
  "version": "1.0.0",
  "title": "Updated Recipe Title",
  "description": "Updated description",
  "status": "published",
  "content": {
    "nodes": [
      {
        "id": "measure_optics",
        "agent": "netops_api.get_optics",
        "input": {"port": "cpri1", "device": "{{site_id}}"},
        "output_schema": {"rx_dbm": {"type": "number"}}
      }
    ]
  },
  "tags": ["RAN", "troubleshooting", "updated"],
  "required_plugins": ["mcp"],
  "schema_version": "1.0",
  "author_id": 1,
  "usage_count": 0,
  "success_rate": 0.0,
  "avg_execution_time": 0.0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Delete Recipe
**DELETE** `/recipes/{recipe_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** `204 No Content`

---

## Tools

### List Tools
**GET** `/tools/`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100, max: 100)
- `tool_type` (string, optional): Filter by tool type
- `category` (string, optional): Filter by category

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "mcp.shift_traffic",
    "version": "1.0.0",
    "title": "Shift Traffic Tool",
    "description": "Shift traffic between network nodes",
    "tool_type": "api",
    "executable": "plugins.mcp.shift_traffic",
    "input_schema": {
      "type": "object",
      "properties": {
        "site_id": {"type": "string"},
        "target_node": {"type": "string"},
        "classes": {"type": "array", "items": {"type": "string"}}
      }
    },
    "output_schema": {
      "type": "object",
      "properties": {
        "success": {"type": "boolean"}
      }
    },
    "timeout": 120,
    "retry_count": 2,
    "retry_delay": 1.0,
    "rbac_roles": ["network_ops"],
    "requires_approval": false,
    "is_sandbox_safe": true,
    "tags": ["network", "traffic"],
    "category": "network_operations",
    "author_id": 1,
    "usage_count": 0,
    "success_rate": 0.0,
    "avg_execution_time": 0.0,
    "avg_cost_usd": 0.0,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Create Tool
**POST** `/tools/`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "example.tool",
  "version": "1.0.0",
  "title": "Example Tool",
  "description": "An example tool",
  "tool_type": "api",
  "executable": "plugins.example.tool",
  "input_schema": {
    "type": "object",
    "properties": {
      "param1": {"type": "string"}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "result": {"type": "string"}
    }
  },
  "timeout": 60,
  "retry_count": 1,
  "retry_delay": 1.0,
  "rbac_roles": ["user"],
  "requires_approval": false,
  "is_sandbox_safe": true,
  "tags": ["example"],
  "category": "utilities"
}
```

**Response:** `201 Created`
```json
{
  "id": 2,
  "name": "example.tool",
  "version": "1.0.0",
  "title": "Example Tool",
  "description": "An example tool",
  "tool_type": "api",
  "executable": "plugins.example.tool",
  "input_schema": {
    "type": "object",
    "properties": {
      "param1": {"type": "string"}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "result": {"type": "string"}
    }
  },
  "timeout": 60,
  "retry_count": 1,
  "retry_delay": 1.0,
  "rbac_roles": ["user"],
  "requires_approval": false,
  "is_sandbox_safe": true,
  "tags": ["example"],
  "category": "utilities",
  "author_id": 1,
  "usage_count": 0,
  "success_rate": 0.0,
  "avg_execution_time": 0.0,
  "avg_cost_usd": 0.0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Get Tool
**GET** `/tools/{tool_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "mcp.shift_traffic",
  "version": "1.0.0",
  "title": "Shift Traffic Tool",
  "description": "Shift traffic between network nodes",
  "tool_type": "api",
  "executable": "plugins.mcp.shift_traffic",
  "input_schema": {
    "type": "object",
    "properties": {
      "site_id": {"type": "string"},
      "target_node": {"type": "string"},
      "classes": {"type": "array", "items": {"type": "string"}}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "success": {"type": "boolean"}
    }
  },
  "timeout": 120,
  "retry_count": 2,
  "retry_delay": 1.0,
  "rbac_roles": ["network_ops"],
  "requires_approval": false,
  "is_sandbox_safe": true,
  "tags": ["network", "traffic"],
  "category": "network_operations",
  "author_id": 1,
  "usage_count": 0,
  "success_rate": 0.0,
  "avg_execution_time": 0.0,
  "avg_cost_usd": 0.0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update Tool
**PATCH** `/tools/{tool_id}`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "Updated Tool Title",
  "description": "Updated description",
  "timeout": 180,
  "tags": ["network", "traffic", "updated"]
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "mcp.shift_traffic",
  "version": "1.0.0",
  "title": "Updated Tool Title",
  "description": "Updated description",
  "tool_type": "api",
  "executable": "plugins.mcp.shift_traffic",
  "input_schema": {
    "type": "object",
    "properties": {
      "site_id": {"type": "string"},
      "target_node": {"type": "string"},
      "classes": {"type": "array", "items": {"type": "string"}}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "success": {"type": "boolean"}
    }
  },
  "timeout": 180,
  "retry_count": 2,
  "retry_delay": 1.0,
  "rbac_roles": ["network_ops"],
  "requires_approval": false,
  "is_sandbox_safe": true,
  "tags": ["network", "traffic", "updated"],
  "category": "network_operations",
  "author_id": 1,
  "usage_count": 0,
  "success_rate": 0.0,
  "avg_execution_time": 0.0,
  "avg_cost_usd": 0.0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## Flows

### List Flows
**GET** `/flows/`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100, max: 100)
- `recipe_id` (int, optional): Filter by recipe ID
- `validation_status` (string, optional): Filter by validation status

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "recipe_id": 1,
    "langflow_json": {
      "nodes": [
        {
          "id": "shift_voice",
          "type": "Tool",
          "agent": "mcp.shift_traffic",
          "input": {"site_id": "{{site_id}}", "target_node": "node2"},
          "next": {
            "success": "finish_ok",
            "default": "escalate"
          }
        }
      ]
    },
    "content_hash": "abc123...",
    "validation_status": "valid",
    "validation_errors": [],
    "validation_warnings": [],
    "security_approved": true,
    "policy_violations": [],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Compile Recipe to Flow
**POST** `/flows/compile`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "recipe_id": 1,
  "ticket_context": {
    "site_id": "eNB-123",
    "issue_type": "voice_bearer_drop",
    "severity": "high"
  },
  "variables": {
    "site_id": "eNB-123",
    "target_node": "node2"
  },
  "use_llm_adaptation": true
}
```

**Response:** `201 Created`
```json
{
  "id": 2,
  "recipe_id": 1,
  "langflow_json": {
    "nodes": [
      {
        "id": "shift_voice",
        "type": "Tool",
        "agent": "mcp.shift_traffic",
        "input": {"site_id": "eNB-123", "target_node": "node2"},
        "next": {
          "success": "finish_ok",
          "default": "escalate"
        }
      }
    ]
  },
  "content_hash": "def456...",
  "validation_status": "pending",
  "validation_errors": [],
  "validation_warnings": [],
  "security_approved": false,
  "policy_violations": [],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Get Flow
**GET** `/flows/{flow_id}`

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "id": 1,
  "recipe_id": 1,
  "langflow_json": {
    "nodes": [
      {
        "id": "shift_voice",
        "type": "Tool",
        "agent": "mcp.shift_traffic",
        "input": {"site_id": "{{site_id}}", "target_node": "node2"},
        "next": {
          "success": "finish_ok",
          "default": "escalate"
        }
      }
    ]
  },
  "content_hash": "abc123...",
  "validation_status": "valid",
  "validation_errors": [],
  "validation_warnings": [],
  "security_approved": true,
  "policy_violations": [],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Execute Flow
**POST** `/flows/{flow_id}/execute`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "execution_mode": "batch",
  "runtime_variables": {
    "site_id": "eNB-123",
    "target_node": "node2"
  },
  "timeout_seconds": 300,
  "max_tokens": 5000,
  "dry_run": false
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "flow_id": 1,
  "triggered_by_id": 1,
  "execution_mode": "batch",
  "runtime_variables": {
    "site_id": "eNB-123",
    "target_node": "node2"
  },
  "status": "queued",
  "started_at": null,
  "completed_at": null,
  "execution_time": null,
  "result": null,
  "error_message": null,
  "token_count": 0,
  "cost_usd": 0.0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### List Flow Executions
**GET** `/flows/{flow_id}/executions`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100, max: 100)
- `status` (string, optional): Filter by execution status

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "flow_id": 1,
    "triggered_by_id": 1,
    "execution_mode": "batch",
    "runtime_variables": {
      "site_id": "eNB-123",
      "target_node": "node2"
    },
    "status": "completed",
    "started_at": "2024-01-01T00:01:00Z",
    "completed_at": "2024-01-01T00:02:00Z",
    "execution_time": 60.0,
    "result": {
      "success": true,
      "message": "Traffic shifted successfully"
    },
    "error_message": null,
    "token_count": 150,
    "cost_usd": 0.003,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:02:00Z"
  }
]
```

### Validate Flow
**POST** `/flows/{flow_id}/validate`

**Headers:** `Authorization: Bearer <token>`

**Response:** `200 OK`
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Tool 'mcp.shift_traffic' has not been tested recently"],
  "security_approved": true,
  "policy_violations": [],
  "estimated_cost_usd": 0.005,
  "estimated_tokens": 200
}
```

---

## Health & Monitoring

### Basic Health Check
**GET** `/health/`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "recipe-hub-api"
}
```

### Detailed Health Check
**GET** `/health/detailed`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "recipe-hub-api",
  "checks": {
    "database": {
      "status": "healthy",
      "url": "localhost:5432/recipe_hub"
    },
    "redis": {
      "status": "healthy",
      "url": "localhost:6379"
    },
    "langflow": {
      "status": "healthy",
      "url": "http://localhost:7860"
    }
  }
}
```

### Readiness Check
**GET** `/health/ready`

**Response:** `200 OK`
```json
{
  "status": "ready"
}
```

### Liveness Check
**GET** `/health/live`

**Response:** `200 OK`
```json
{
  "status": "alive"
}
```

---

## Error Handling

The API uses standard HTTP status codes and returns error responses in the following format:

```json
{
  "detail": "Error message description"
}
```

### Common Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Request successful, no content to return
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Example Error Responses

**400 Bad Request:**
```json
{
  "detail": "Recipe name already exists"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Incorrect email or password"
}
```

**403 Forbidden:**
```json
{
  "detail": "Not enough permissions"
}
```

**404 Not Found:**
```json
{
  "detail": "Recipe not found"
}
```

**422 Unprocessable Entity:**
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Data Models

### Recipe Status Enum
```typescript
enum RecipeStatus {
  DRAFT = "draft",
  PUBLISHED = "published",
  ARCHIVED = "archived"
}
```

### Tool Type Enum
```typescript
enum ToolType {
  API = "api",
  MCP = "mcp",
  WORKFLOW = "workflow",
  AGENT = "agent"
}
```

### Flow Validation Status Enum
```typescript
enum ValidationStatus {
  PENDING = "pending",
  VALID = "valid",
  INVALID = "invalid",
  WARNING = "warning"
}
```

### Flow Execution Status Enum
```typescript
enum ExecutionStatus {
  QUEUED = "queued",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled"
}
```

### Flow Execution Mode Enum
```typescript
enum ExecutionMode {
  BATCH = "batch",
  INTERACTIVE = "interactive",
  SHADOW = "shadow"
}
```

---

## Frontend Integration Notes

### Authentication Flow
1. User registers/logs in via `/auth/register` or `/auth/login`
2. Store the JWT token securely (localStorage, sessionStorage, or secure cookie)
3. Include token in all subsequent requests: `Authorization: Bearer <token>`
4. Handle token expiration by calling `/auth/refresh` or redirecting to login

### Error Handling
- Implement global error handling for 401 responses (redirect to login)
- Handle 403 responses by showing appropriate permission messages
- Display validation errors (422) inline with form fields
- Show user-friendly messages for 500 errors

### Real-time Updates
- Consider implementing WebSocket connections for flow execution status updates
- Poll execution status for long-running flows
- Implement optimistic updates for better UX

### File Uploads
- The API currently doesn't support file uploads, but this can be added for recipe imports/exports
- Consider implementing drag-and-drop for JSON recipe files

### Pagination
- All list endpoints support pagination with `skip` and `limit` parameters
- Implement infinite scroll or pagination controls in the UI
- Consider caching paginated results for better performance

### Search and Filtering
- Implement client-side search for small datasets
- For larger datasets, consider adding server-side search endpoints
- Use URL query parameters to maintain filter state

### Security Considerations
- Never store sensitive data in localStorage
- Implement proper CSRF protection
- Sanitize user inputs before sending to API
- Validate all API responses before using data

---

## Development Setup

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/recipe_hub

# Redis
REDIS_URL=redis://localhost:6379

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Langflow
LANGFLOW_API_KEY=your-langflow-api-key
LANGFLOW_URL=http://localhost:7860

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# App Settings
DEBUG=true
APP_NAME=Recipe Hub API
APP_VERSION=1.0.0
API_V1_STR=/api/v1
```

### Running the API
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
- Interactive docs: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json` 