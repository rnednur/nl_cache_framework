-- Create enum type for template types
CREATE TYPE template_type AS ENUM ('sql', 'url', 'api', 'workflow');

-- Create text2sql_cache table
CREATE TABLE text2sql_cache (
    id SERIAL PRIMARY KEY,
    nl_query VARCHAR NOT NULL,
    template TEXT NOT NULL,
    template_type template_type NOT NULL DEFAULT 'sql',
    vector_embedding JSONB,
    is_template BOOLEAN NOT NULL DEFAULT FALSE,
    entity_replacements JSONB,
    reasoning_trace TEXT,
    tags JSONB,
    suggested_visualization VARCHAR,
    database_name VARCHAR,
    schema_name VARCHAR,
    catalog_id INTEGER,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    invalidation_reason VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_text2sql_cache_nl_query ON text2sql_cache(nl_query);
CREATE INDEX idx_text2sql_cache_template_type ON text2sql_cache(template_type);
CREATE INDEX idx_text2sql_cache_is_template ON text2sql_cache(is_template);
CREATE INDEX idx_text2sql_cache_database_name ON text2sql_cache(database_name);
CREATE INDEX idx_text2sql_cache_schema_name ON text2sql_cache(schema_name);
CREATE INDEX idx_text2sql_cache_is_valid ON text2sql_cache(is_valid);

-- Create usage_log table
CREATE TABLE usage_log (
    id SERIAL PRIMARY KEY,
    cache_entry_id INTEGER NOT NULL REFERENCES text2sql_cache(id),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for usage_log
CREATE INDEX idx_usage_log_cache_entry_id ON usage_log(cache_entry_id);
CREATE INDEX idx_usage_log_timestamp ON usage_log(timestamp);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_text2sql_cache_updated_at
    BEFORE UPDATE ON text2sql_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 