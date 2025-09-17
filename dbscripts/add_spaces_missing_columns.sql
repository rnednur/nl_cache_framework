-- Migration script to add missing columns to spaces table
-- This addresses the psycopg2.errors.UndefinedColumn error for spaces.is_template

-- Add missing columns to spaces table
ALTER TABLE spaces 
ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT FALSE NOT NULL;

-- Add index for the new is_template column
CREATE INDEX IF NOT EXISTS ix_spaces_is_template ON spaces (is_template);

-- Update the is_template column for existing records based on content_type
UPDATE spaces 
SET is_template = TRUE 
WHERE content_type = 'template';

-- Add any other missing columns that might be referenced in the model
ALTER TABLE spaces 
ADD COLUMN IF NOT EXISTS template_parameters JSONB,
ADD COLUMN IF NOT EXISTS template_schema JSONB,
ADD COLUMN IF NOT EXISTS base_query TEXT,
ADD COLUMN IF NOT EXISTS source_query TEXT;

-- Add missing storage and scheduling columns if they don't exist
ALTER TABLE spaces 
ADD COLUMN IF NOT EXISTS storage_path VARCHAR(500),
ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(20) DEFAULT 'local' NOT NULL,
ADD COLUMN IF NOT EXISTS storage_size_bytes INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS external_url VARCHAR(1000);

-- Add scheduling columns
ALTER TABLE spaces 
ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(20) DEFAULT 'none' NOT NULL,
ADD COLUMN IF NOT EXISTS schedule_config JSONB,
ADD COLUMN IF NOT EXISTS next_execution TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_execution TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS is_scheduled_active BOOLEAN DEFAULT FALSE NOT NULL;

-- Add access and sharing columns
ALTER TABLE spaces 
ADD COLUMN IF NOT EXISTS access_permissions JSONB,
ADD COLUMN IF NOT EXISTS team_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS auto_cleanup BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS retention_days INTEGER;

-- Add usage tracking columns
ALTER TABLE spaces 
ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS share_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP WITH TIME ZONE;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS ix_spaces_storage_backend ON spaces (storage_backend);
CREATE INDEX IF NOT EXISTS ix_spaces_schedule_type ON spaces (schedule_type);
CREATE INDEX IF NOT EXISTS ix_spaces_expires_at ON spaces (expires_at);
CREATE INDEX IF NOT EXISTS ix_spaces_last_accessed ON spaces (last_accessed);
CREATE INDEX IF NOT EXISTS ix_spaces_team_id ON spaces (team_id);

-- Verify the changes
DO $$ 
BEGIN
    RAISE NOTICE 'Migration completed: Added missing columns to spaces table';
    RAISE NOTICE 'Columns added: is_template, template_parameters, template_schema, base_query, source_query';
    RAISE NOTICE 'Storage columns: storage_path, storage_backend, storage_size_bytes, external_url';
    RAISE NOTICE 'Scheduling columns: schedule_type, schedule_config, next_execution, last_execution, is_scheduled_active';
    RAISE NOTICE 'Access columns: access_permissions, team_id, expires_at, auto_cleanup, retention_days';
    RAISE NOTICE 'Usage columns: view_count, share_count, last_accessed';
END $$;