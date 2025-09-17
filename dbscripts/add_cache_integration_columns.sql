-- Add cache entry integration columns to hot_commands table
-- Run this script to update the existing database schema

-- Add cache entry integration columns
ALTER TABLE hot_commands 
ADD COLUMN IF NOT EXISTS cache_entry_id INTEGER,
ADD COLUMN IF NOT EXISTS source_template_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS source_reasoning TEXT,
ADD COLUMN IF NOT EXISTS source_tags JSONB,
ADD COLUMN IF NOT EXISTS source_execution_stats JSONB;

-- Add foreign key constraint for cache_entry_id
-- Note: This assumes the text2sql_cache table exists in the same schema
ALTER TABLE hot_commands 
ADD CONSTRAINT fk_hot_commands_cache_entry 
FOREIGN KEY (cache_entry_id) REFERENCES text2sql_cache(id);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS ix_hot_commands_cache_entry ON hot_commands(cache_entry_id);
CREATE INDEX IF NOT EXISTS ix_hot_commands_source_type ON hot_commands(source_template_type);

-- Display success message
SELECT 'Cache integration columns added successfully!' as result;