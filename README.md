# NL Cache Framework

A lightweight framework for managing natural language query caches built with Fastv1.

## Features

- Create, read, update, and delete cache entries for natural language queries
- Associate templates with queries
- Track usage statistics
- Simple REST API interface
- Automatic dependency installation

## Getting Started

### Prerequisites

- Python 3.8 or higher

### Installation

No installation needed. The application automatically installs required dependencies when run.

### Running the Server

```bash
# Navigate to the project root (the directory containing backend/ and frontend/)
# Ensure Python 3.8+ is installed and accessible as 'python3'

# Activate your virtual environment if you have one, otherwise the script creates one
# source venv/bin/activate 

# Run the start script
./backend/start.sh 
```

Alternatively, if you have manually installed dependencies and activated the environment:
```bash
# From the project root
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000`.

## API Endpoints

### Health Check

```
GET /health
```

Returns the health status of the server and its dependencies (e.g., database).

### Process NL Query

```
POST /v1/complete
```
Utilizes the cache to process a natural language prompt. Returns a cached template/result if a sufficiently similar query exists, otherwise indicates a cache miss.

Request Body:
```json
{
  "prompt": "Your natural language query here"
}
```

Response Body (Cache Hit):
```json
{
  "completion": "The processed template or result",
  "status": "cache_hit",
  "similarity_score": 0.95 
}
```

Response Body (Cache Miss):
```json
{
  "completion": "This query requires LLM processing. No cached result was found.",
  "status": "cache_miss"
}
```

### Search Cache Entries

```
GET /v1/cache/search
```
Searches the cache for entries similar to the provided natural language query.

Query Parameters:
- `nl_query` (required): The natural language query to search for.
- `template_type` (optional): Filter by template type (e.g., "sql", "url").
- `threshold` (optional): Minimum similarity score (default: 0.7).
- `limit` (optional): Maximum number of results to return (default: 5).

### List Cache Entries

```
GET /v1/cache
```

Query Parameters:
- `page`: Page number for pagination (default: 1)
- `page_size`: Number of entries per page (default: 10)
- `search_query`: Optional search term to filter entries by `nl_query` or `template` content.
- `template_type`: Optional filter by template type (e.g., "sql", "url", "api", "workflow").

### Create Cache Entry

```
POST /v1/cache
```

Request Body: See Data Model section below for possible fields. Requires at least `nl_query` and `template`.
```json
{
  "nl_query": "Show me total sales by region",
  "template": "SELECT region, SUM(sales) FROM orders GROUP BY region;",
  "template_type": "sql", 
  "tags": ["sales", "regional"],
  "database_name": "sales_db" 
}
```

### Get Cache Entry

```
GET /v1/cache/{entry_id}
```

Returns a specific cache entry by ID.

### Update Cache Entry

```
PUT /v1/cache/{entry_id}
```

Request Body: Same fields as create endpoint. Include only fields to be updated.

### Delete Cache Entry

```
DELETE /v1/cache/{entry_id}
```

Removes a cache entry by ID.

### Apply Entity Substitution (Test)

```
POST /v1/cache/{entry_id}/apply
```
Applies entity substitution to a template entry using provided text. Useful for testing substitution logic.

Request Body:
```json
{
  "text": "Show me sales for the 'West' region"
}
```

### Test Cache Entry (Experimental)

```
POST /v1/cache/{entry_id}/test
```
Endpoint for testing specific functionalities of a cache entry, potentially related to entity extraction or substitution.

### Get Cache Statistics

```
GET /v1/cache/stats
```

Returns statistics about the cache entries, including total count. Note: Per-entry usage count is now tracked separately.

## Data Model (`Text2SQLCache`)

Each cache entry contains:

- `id`: (Integer) Unique identifier for the cache entry.
- `nl_query`: (String) The original natural language query. (Required)
- `template`: (Text) The template (SQL, URL, API spec, etc.) corresponding to the NL query. (Required)
- `template_type`: (String) Type of the template. Defaults to `sql`. Allowed values: `sql`, `url`, `api`, `workflow`.
- `vector_embedding`: (Vector) Optional vector embedding of the `nl_query` (e.g., for similarity search).
- `is_template`: (Boolean) Flag indicating if this entry contains placeholders for entity substitution. Defaults to `false`.
- `entity_replacements`: (JSON) Optional JSON blob describing placeholders and their types for substitution. Example: `{"entity_key": {"placeholder": ":placeholder_name", "type": "string"}}`.
- `reasoning_trace`: (Text) Optional explanation of how the template was derived.
- `tags`: (JSON) Optional list of strings for categorization (e.g., `["sales", "summary"]`).
- `suggested_visualization`: (String) Optional hint for visualizing the result.
- `database_name`: (String) Optional identifier for the target database.
- `schema_name`: (String) Optional identifier for the target schema.
- `catalog_id`: (Integer) Optional identifier linking to an external data catalog.
- `is_valid`: (Boolean) Flag indicating if the cache entry is currently considered valid. Defaults to `true`.
- `invalidation_reason`: (String) Optional reason why the entry was marked as invalid.
- `created_at`: (DateTime) Timestamp when the entry was created (UTC).
- `updated_at`: (DateTime) Timestamp when the entry was last updated (UTC).

**Note:** Usage statistics (like hit count per entry) are tracked in a separate `UsageLog` table, linked by `cache_entry_id`. The `/v1/cache/stats` endpoint provides aggregate statistics.

## Development

The application uses SQLAlchemy with fallback to an in-memory SQLite database if no external database is configured. 

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 