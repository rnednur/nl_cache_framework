-- Define schema name (replace during deployment with actual schema name)
-- This variable can be searched and replaced during script execution
\set schema_name 'public'

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS :"schema_name";

-- Create enum type for template types
CREATE TYPE :"schema_name".template_type AS ENUM ('sql', 'url', 'api', 'workflow', 'graphql', 'regex', 'script', 'nosql', 'cli', 'prompt', 'configuration', 'reasoning_steps');

-- Create enum type for status
CREATE TYPE :"schema_name".status_type AS ENUM ('pending', 'active', 'archive');

-- Create text2sql_cache table
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
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_text2sql_cache_nl_query ON :"schema_name".text2sql_cache(nl_query);
CREATE INDEX idx_text2sql_cache_template_type ON :"schema_name".text2sql_cache(template_type);
CREATE INDEX idx_text2sql_cache_is_template ON :"schema_name".text2sql_cache(is_template);
CREATE INDEX idx_text2sql_cache_catalog_type ON :"schema_name".text2sql_cache(catalog_type);
CREATE INDEX idx_text2sql_cache_catalog_subtype ON :"schema_name".text2sql_cache(catalog_subtype);
CREATE INDEX idx_text2sql_cache_catalog_name ON :"schema_name".text2sql_cache(catalog_name);
CREATE INDEX idx_text2sql_cache_status ON :"schema_name".text2sql_cache(status);

-- Create usage_log table
CREATE TABLE :"schema_name".usage_log (
    id SERIAL PRIMARY KEY,
    cache_entry_id INTEGER REFERENCES :"schema_name".text2sql_cache(id) ON DELETE SET NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prompt TEXT,
    success_status BOOLEAN,
    similarity_score FLOAT,
    error_message TEXT,
    catalog_type VARCHAR,
    catalog_subtype VARCHAR,
    catalog_name VARCHAR,
    llm_used BOOLEAN DEFAULT FALSE
);

-- Create index for usage_log
CREATE INDEX idx_usage_log_cache_entry_id ON :"schema_name".usage_log(cache_entry_id);
CREATE INDEX idx_usage_log_timestamp ON :"schema_name".usage_log(timestamp);

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

-- Create index for cache_audit_log
CREATE INDEX idx_cache_audit_log_cache_entry_id ON :"schema_name".cache_audit_log(cache_entry_id);
CREATE INDEX idx_cache_audit_log_timestamp ON :"schema_name".cache_audit_log(timestamp);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION :"schema_name".update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_text2sql_cache_updated_at
    BEFORE UPDATE ON :"schema_name".text2sql_cache
    FOR EACH ROW
    EXECUTE FUNCTION :"schema_name".update_updated_at_column(); 



-- Note: The following ALTER statements are kept for reference but are not needed for new database setups
-- ALTER TABLE text2sql_cache DROP COLUMN IF EXISTS catalog_id;
-- ALTER TABLE text2sql_cache ADD COLUMN IF NOT EXISTS catalog_type VARCHAR;
-- ALTER TABLE text2sql_cache ADD COLUMN IF NOT EXISTS catalog_subtype VARCHAR;
-- ALTER TABLE text2sql_cache ADD COLUMN IF NOT EXISTS catalog_name VARCHAR;

-- New column for LLM integration 
-- ALTER TABLE usage_log ADD COLUMN IF NOT EXISTS llm_used BOOLEAN DEFAULT FALSE;    