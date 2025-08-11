# Database Migration Scripts

This directory contains database migration scripts for the ThinkForge NL Cache Framework. These scripts help maintain database schema consistency and add new features over time.

## Migration Files

### Schema Creation
- **`create_tables.sql`** - Initial database schema creation with all tables and indexes
- **`temp_create_tables.sql`** - Temporary schema creation script
- **`init_schema.py`** - Python script for database initialization

### Template Type Enum Migrations
- **`add_reasoning_steps_type.sql`** - Adds 'reasoning_steps' to template_type enum
- **`add_missing_template_types.sql`** - Adds missing template types (mcp_tool, agent, function, recipe, recipe_step, recipe_template)
- **`add_missing_template_types.py`** - Python version of the template type migration

### Column Additions
- **`add_tool_columns.sql`** - Adds tool-specific and recipe-specific columns to text2sql_cache table
- **`add_usage_log_columns.py`** - Adds response, considered_entries, and is_confident columns to usage_log table
- **`add_llm_used_column.py`** - Adds llm_used column to usage_log table

## Current Template Type Enum Values

The `template_type` enum currently supports these values:

### Core Types
- `sql` - SQL query templates
- `url` - URL templates for API calls
- `api` - API templates from Swagger/OpenAPI specs
- `workflow` - Workflow templates with JSON step definitions
- `graphql` - GraphQL query templates
- `regex` - Regular expression templates
- `script` - Executable script templates
- `nosql` - NoSQL query templates
- `cli` - Command-line interface templates
- `prompt` - LLM prompt templates
- `configuration` - Configuration file templates
- `reasoning_steps` - Step-by-step reasoning templates
- `dsl` - Domain Specific Language components

### Tool Hub Types
- `mcp_tool` - Model Context Protocol (MCP) tools
- `agent` - AI Agent definitions
- `function` - Reusable function definitions

### Recipe Hub Types
- `recipe` - Complete automation recipes
- `recipe_step` - Individual recipe steps
- `recipe_template` - Parameterized recipe templates

## Running Migrations

### Prerequisites
1. Ensure your `.env` file contains the correct database connection parameters:
   ```bash
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=mcp_cache_db
   DB_SCHEMA=public
   ```

2. Install required Python packages:
   ```bash
   pip install sqlalchemy python-dotenv psycopg2-binary
   ```

### Running SQL Migrations
For SQL-based migrations, use `psql` command:

```bash
# Set schema variable and run migration
psql -h localhost -U your_user -d mcp_cache_db -v schema_name=public -f add_missing_template_types.sql
```

### Running Python Migrations
For Python-based migrations:

```bash
# Make script executable
chmod +x add_missing_template_types.py

# Run the migration
python add_missing_template_types.py
```

## Migration Best Practices

### SQL Migrations
- Use parameterized schema names with `\set schema_name 'public'`
- Always use `IF NOT EXISTS` clauses to make migrations idempotent
- Add appropriate comments to document changes
- Use proper indexing for new columns

### Python Migrations
- Include comprehensive logging
- Check for existing changes before applying
- Use proper error handling and rollback mechanisms
- Follow the established patterns from existing scripts
- Use `IF NOT EXISTS` equivalent checks

### Enum Migrations
- PostgreSQL enum values cannot be added in transactions
- Use `ALTER TYPE ... ADD VALUE IF NOT EXISTS` for idempotency
- Consider the order of enum values (they are sorted alphabetically by default)
- Update enum documentation comments after adding values

## Schema Information

### Main Tables
- `text2sql_cache` - Main cache table storing NL queries and templates
- `usage_log` - Logs cache usage events
- `cache_audit_log` - Tracks changes to cache entries

### Key Indexes
- Template type, catalog fields, and timestamp indexes for performance
- Status and validity indexes for filtering
- Health status and complexity level indexes for tool/recipe management

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the database user has sufficient privileges
2. **Enum Already Exists**: Scripts are idempotent, re-running is safe
3. **Connection Issues**: Verify database connection parameters in `.env`
4. **Transaction Issues**: Enum additions require autocommit mode

### Verification

After running migrations, verify changes:

```sql
-- Check enum values
SELECT enumlabel FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
WHERE t.typname = 'template_type'
ORDER BY enumlabel;

-- Check table columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'text2sql_cache'
ORDER BY ordinal_position;
```

## Development Notes

When adding new template types:
1. Update the `TemplateType` enum in `thinkforge/models.py`
2. Create appropriate migration scripts (both SQL and Python versions)
3. Update this README with the new template type descriptions
4. Test migrations on a development database first
5. Consider backward compatibility for existing data