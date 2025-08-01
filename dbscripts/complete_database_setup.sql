-- =============================================================================
-- COMPLETE DATABASE SETUP SCRIPT
-- This script creates all database objects including types, tables, indexes, 
-- triggers, and includes all necessary migrations in one comprehensive file.
-- =============================================================================

-- Define schema name (replace during deployment with actual schema name)
-- This variable can be searched and replaced during script execution
\set schema_name 'public'

-- =============================================================================
-- SCHEMA CREATION
-- =============================================================================

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS :"schema_name";

-- =============================================================================
-- ENUM TYPES CREATION
-- =============================================================================

-- Create enum type for template types with all possible values
CREATE TYPE :"schema_name".template_type AS ENUM (
    'sql', 
    'url', 
    'api', 
    'workflow', 
    'graphql', 
    'regex', 
    'script', 
    'nosql', 
    'cli', 
    'prompt', 
    'configuration', 
    'reasoning_steps', 
    'dsl',
    'mcp_tool',
    'agent',
    'function',
    'recipe',
    'recipe_step',
    'recipe_template'
);

-- Create enum type for status
CREATE TYPE :"schema_name".status_type AS ENUM ('pending', 'active', 'archive');

-- =============================================================================
-- MAIN TABLES CREATION
-- =============================================================================

-- Create text2sql_cache table with all columns
CREATE TABLE :"schema_name".text2sql_cache (
    id SERIAL PRIMARY KEY,
    nl_query VARCHAR NOT NULL,
    template TEXT NOT NULL,
    template_type :"schema_name".template_type NOT NULL DEFAULT 'sql',
    vector_embedding JSONB,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    entity_replacements JSONB,
    reasoning_trace TEXT,
    tags JSONB,
    catalog_type VARCHAR,
    catalog_subtype VARCHAR,
    catalog_name VARCHAR,
    status :"schema_name".status_type NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Tool-specific metadata fields
    tool_capabilities JSONB,
    tool_dependencies JSONB,
    execution_config JSONB,
    health_status VARCHAR,
    last_tested TIMESTAMP,
    -- Recipe-specific metadata fields
    recipe_steps JSONB,
    required_tools JSONB,
    execution_time_estimate INTEGER,
    complexity_level VARCHAR,
    success_rate FLOAT,
    last_executed TIMESTAMP,
    execution_count INTEGER DEFAULT 0
);

-- Create usage_log table
CREATE TABLE :"schema_name".usage_log (
    id SERIAL PRIMARY KEY,
    cache_entry_id INTEGER REFERENCES :"schema_name".text2sql_cache(id) ON DELETE SET NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prompt TEXT,
    response TEXT,
    success_status BOOLEAN,
    similarity_score FLOAT,
    error_message TEXT,
    catalog_type VARCHAR,
    catalog_subtype VARCHAR,
    catalog_name VARCHAR,
    llm_used BOOLEAN DEFAULT FALSE,
    considered_entries JSONB,
    is_confident BOOLEAN
);

-- Create cache_audit_log table
CREATE TABLE :"schema_name".cache_audit_log (
    id SERIAL PRIMARY KEY,
    cache_entry_id INTEGER REFERENCES :"schema_name".text2sql_cache(id) ON DELETE CASCADE,
    changed_field VARCHAR NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_reason TEXT,
    changed_by VARCHAR,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES CREATION
-- =============================================================================

-- Indexes for text2sql_cache table
CREATE INDEX idx_text2sql_cache_nl_query ON :"schema_name".text2sql_cache(nl_query);
CREATE INDEX idx_text2sql_cache_template_type ON :"schema_name".text2sql_cache(template_type);
CREATE INDEX idx_text2sql_cache_is_template ON :"schema_name".text2sql_cache(is_template);
CREATE INDEX idx_text2sql_cache_catalog_type ON :"schema_name".text2sql_cache(catalog_type);
CREATE INDEX idx_text2sql_cache_catalog_subtype ON :"schema_name".text2sql_cache(catalog_subtype);
CREATE INDEX idx_text2sql_cache_catalog_name ON :"schema_name".text2sql_cache(catalog_name);
CREATE INDEX idx_text2sql_cache_status ON :"schema_name".text2sql_cache(status);
CREATE INDEX idx_text2sql_cache_health_status ON :"schema_name".text2sql_cache(health_status);
CREATE INDEX idx_text2sql_cache_complexity_level ON :"schema_name".text2sql_cache(complexity_level);
CREATE INDEX idx_text2sql_cache_last_tested ON :"schema_name".text2sql_cache(last_tested);
CREATE INDEX idx_text2sql_cache_last_executed ON :"schema_name".text2sql_cache(last_executed);

-- Indexes for usage_log table
CREATE INDEX idx_usage_log_cache_entry_id ON :"schema_name".usage_log(cache_entry_id);
CREATE INDEX idx_usage_log_timestamp ON :"schema_name".usage_log(timestamp);

-- Indexes for cache_audit_log table
CREATE INDEX idx_cache_audit_log_cache_entry_id ON :"schema_name".cache_audit_log(cache_entry_id);
CREATE INDEX idx_cache_audit_log_timestamp ON :"schema_name".cache_audit_log(timestamp);

-- =============================================================================
-- TRIGGERS AND FUNCTIONS
-- =============================================================================

-- Create trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION :"schema_name".update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for text2sql_cache table
CREATE TRIGGER update_text2sql_cache_updated_at
    BEFORE UPDATE ON :"schema_name".text2sql_cache
    FOR EACH ROW
    EXECUTE FUNCTION :"schema_name".update_updated_at_column();

-- =============================================================================
-- COMMENTS AND DOCUMENTATION
-- =============================================================================

-- Add comments to document the enum types
COMMENT ON TYPE :"schema_name".template_type IS 'Enum for template types: sql, url, api, workflow, graphql, regex, script, nosql, cli, prompt, configuration, reasoning_steps, dsl, mcp_tool, agent, function, recipe, recipe_step, recipe_template';
COMMENT ON TYPE :"schema_name".status_type IS 'Enum for entry status: pending, active, archive';

-- Add comments to document the new columns in text2sql_cache
COMMENT ON COLUMN :"schema_name".text2sql_cache.tool_capabilities IS 'JSON array of capabilities that the tool provides (e.g., [''image_processing'', ''pdf_conversion''])';
COMMENT ON COLUMN :"schema_name".text2sql_cache.tool_dependencies IS 'JSON object describing tool dependencies and requirements';
COMMENT ON COLUMN :"schema_name".text2sql_cache.execution_config IS 'JSON object for execution parameters and constraints';
COMMENT ON COLUMN :"schema_name".text2sql_cache.health_status IS 'Current health status of the tool (''healthy'', ''degraded'', ''unhealthy'', ''unknown'')';
COMMENT ON COLUMN :"schema_name".text2sql_cache.last_tested IS 'Timestamp of when the tool was last validated or tested';
COMMENT ON COLUMN :"schema_name".text2sql_cache.recipe_steps IS 'JSON array of recipe steps with execution order, dependencies, and parameters';
COMMENT ON COLUMN :"schema_name".text2sql_cache.required_tools IS 'JSON array of tool cache entry IDs that this recipe depends on for execution';
COMMENT ON COLUMN :"schema_name".text2sql_cache.execution_time_estimate IS 'Estimated execution time in seconds for the complete recipe';
COMMENT ON COLUMN :"schema_name".text2sql_cache.complexity_level IS 'Recipe complexity level (''beginner'', ''intermediate'', ''advanced'') for user guidance';
COMMENT ON COLUMN :"schema_name".text2sql_cache.success_rate IS 'Historical success rate percentage (0-100) based on execution history';
COMMENT ON COLUMN :"schema_name".text2sql_cache.last_executed IS 'Timestamp of when the recipe was last executed';
COMMENT ON COLUMN :"schema_name".text2sql_cache.execution_count IS 'Total number of times this recipe has been executed';

-- =============================================================================
-- MIGRATION NOTES (FOR REFERENCE)
-- =============================================================================

/*
-- Migration notes for existing databases:

-- If you have an existing database and need to add missing enum values:
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'mcp_tool';
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'agent';
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'function';
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'recipe';
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'recipe_step';
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'recipe_template';

-- If you need to add missing columns to existing tables:
ALTER TABLE :"schema_name".text2sql_cache 
ADD COLUMN IF NOT EXISTS tool_capabilities JSONB,
ADD COLUMN IF NOT EXISTS tool_dependencies JSONB,
ADD COLUMN IF NOT EXISTS execution_config JSONB,
ADD COLUMN IF NOT EXISTS health_status VARCHAR,
ADD COLUMN IF NOT EXISTS last_tested TIMESTAMP,
ADD COLUMN IF NOT EXISTS recipe_steps JSONB,
ADD COLUMN IF NOT EXISTS required_tools JSONB,
ADD COLUMN IF NOT EXISTS execution_time_estimate INTEGER,
ADD COLUMN IF NOT EXISTS complexity_level VARCHAR,
ADD COLUMN IF NOT EXISTS success_rate FLOAT,
ADD COLUMN IF NOT EXISTS last_executed TIMESTAMP,
ADD COLUMN IF NOT EXISTS execution_count INTEGER DEFAULT 0;

-- If you need to add missing columns to usage_log:
ALTER TABLE :"schema_name".usage_log 
ADD COLUMN IF NOT EXISTS llm_used BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS considered_entries JSONB,
ADD COLUMN IF NOT EXISTS is_confident BOOLEAN;
*/

-- =============================================================================
-- SCRIPT COMPLETION
-- =============================================================================

-- Display completion message
DO $$
BEGIN
    RAISE NOTICE 'Database setup completed successfully!';
    RAISE NOTICE 'Created schema: %', :'schema_name';
    RAISE NOTICE 'Created tables: text2sql_cache, usage_log, cache_audit_log';
    RAISE NOTICE 'Created indexes and triggers for optimal performance';
END $$; 