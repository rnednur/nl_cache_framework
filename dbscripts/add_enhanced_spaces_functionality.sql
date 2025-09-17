-- Enhanced Spaces Functionality Migration for ThinkForge
-- This script adds enhanced spaces functionality including templates, scheduling, 
-- external storage, and granular access control

-- Set search path to use the configured schema
SET search_path TO ${DB_SCHEMA:-public};

-- Add missing columns to existing spaces table
-- Template functionality
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS is_template BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS template_parameters JSONB;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS template_schema JSONB;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS base_query TEXT;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS source_query TEXT;

-- External storage
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS storage_path VARCHAR(500);
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(20) NOT NULL DEFAULT 'local';
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS storage_size_bytes INTEGER NOT NULL DEFAULT 0;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS external_url VARCHAR(1000);

-- Scheduling and automation
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(20) NOT NULL DEFAULT 'none';
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS schedule_config JSONB;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS next_execution TIMESTAMP WITH TIME ZONE;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS last_execution TIMESTAMP WITH TIME ZONE;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS execution_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS is_scheduled_active BOOLEAN NOT NULL DEFAULT FALSE;

-- Enhanced sharing and permissions
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS access_permissions JSONB;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS team_id VARCHAR(100);

-- Expiration and cleanup
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS auto_cleanup BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS retention_days INTEGER;

-- Usage statistics enhancement
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS execution_count_new INTEGER NOT NULL DEFAULT 0;

-- Update content_type enum to include new types if they don't exist
DO $$ 
BEGIN
    -- Add new content types to the enum
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'template' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'content_type')) THEN
        ALTER TYPE content_type ADD VALUE 'template';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'webpage' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'content_type')) THEN
        ALTER TYPE content_type ADD VALUE 'webpage';
    END IF;
EXCEPTION
    WHEN others THEN
        -- If enum doesn't exist, we'll create constraints instead
        NULL;
END $$;

-- Create new SpaceAccess table for granular permissions
CREATE TABLE IF NOT EXISTS space_access (
    id SERIAL PRIMARY KEY,
    space_id INTEGER NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    granted_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Access details
    access_level VARCHAR(20) NOT NULL DEFAULT 'view',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Usage tracking
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    
    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Optional constraints
    restrictions JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CHECK (access_level IN ('view', 'comment', 'edit', 'admin')),
    
    -- Unique constraint to prevent duplicate access grants
    UNIQUE (space_id, user_id)
);

-- Add constraints for new columns
ALTER TABLE spaces ADD CONSTRAINT IF NOT EXISTS check_storage_backend 
    CHECK (storage_backend IN ('local', 's3', 'gcs', 'azure'));

ALTER TABLE spaces ADD CONSTRAINT IF NOT EXISTS check_schedule_type 
    CHECK (schedule_type IN ('none', 'interval', 'cron', 'webhook'));

-- Update existing content_type constraint to include new types
-- Note: We'll handle this with application-level validation if enum doesn't exist
DO $$
BEGIN
    -- Try to add constraint if enum doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'content_type') THEN
        ALTER TABLE spaces ADD CONSTRAINT IF NOT EXISTS check_enhanced_content_type 
            CHECK (content_type IN ('query_result', 'template', 'visualization', 'report', 'dashboard', 'dataset', 'webpage'));
    END IF;
EXCEPTION
    WHEN others THEN
        NULL;
END $$;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS ix_spaces_is_template ON spaces(is_template);
CREATE INDEX IF NOT EXISTS ix_spaces_storage_backend ON spaces(storage_backend);
CREATE INDEX IF NOT EXISTS ix_spaces_schedule_type ON spaces(schedule_type);
CREATE INDEX IF NOT EXISTS ix_spaces_next_execution ON spaces(next_execution);
CREATE INDEX IF NOT EXISTS ix_spaces_last_execution ON spaces(last_execution);
CREATE INDEX IF NOT EXISTS ix_spaces_is_scheduled_active ON spaces(is_scheduled_active);
CREATE INDEX IF NOT EXISTS ix_spaces_team_id ON spaces(team_id);
CREATE INDEX IF NOT EXISTS ix_spaces_expires_at ON spaces(expires_at);

-- SpaceAccess indexes
CREATE INDEX IF NOT EXISTS ix_space_access_space_id ON space_access(space_id);
CREATE INDEX IF NOT EXISTS ix_space_access_user_id ON space_access(user_id);
CREATE INDEX IF NOT EXISTS ix_space_access_granted_by ON space_access(granted_by);
CREATE INDEX IF NOT EXISTS ix_space_access_space_user ON space_access(space_id, user_id);
CREATE INDEX IF NOT EXISTS ix_space_access_active ON space_access(is_active, expires_at);
CREATE INDEX IF NOT EXISTS ix_space_access_level ON space_access(access_level, is_active);
CREATE INDEX IF NOT EXISTS ix_space_access_last_accessed ON space_access(last_accessed);

-- Update table comments
COMMENT ON TABLE space_access IS 'Granular access control for spaces with permission levels and expiration';
COMMENT ON COLUMN spaces.is_template IS 'Whether this space is a parameterized template';
COMMENT ON COLUMN spaces.template_parameters IS 'JSON array of parameter definitions for templates';
COMMENT ON COLUMN spaces.template_schema IS 'JSON schema for parameter validation';
COMMENT ON COLUMN spaces.base_query IS 'Base query template with parameter placeholders';
COMMENT ON COLUMN spaces.source_query IS 'Original source query without parameters';
COMMENT ON COLUMN spaces.storage_backend IS 'External storage backend (local, s3, gcs, azure)';
COMMENT ON COLUMN spaces.schedule_type IS 'Type of automated execution schedule';
COMMENT ON COLUMN spaces.schedule_config IS 'Configuration for scheduled execution (cron, interval, webhook)';
COMMENT ON COLUMN spaces.external_url IS 'Public URL for external sharing (e.g., webpage exports)';
COMMENT ON COLUMN spaces.team_id IS 'Team identifier for team-based spaces';
COMMENT ON COLUMN spaces.expires_at IS 'When the space expires and can be cleaned up';
COMMENT ON COLUMN spaces.auto_cleanup IS 'Whether to automatically clean up expired spaces';

-- Add column comments for SpaceAccess
COMMENT ON COLUMN space_access.access_level IS 'Permission level: view, comment, edit, admin';
COMMENT ON COLUMN space_access.restrictions IS 'Additional JSON-based access restrictions';
COMMENT ON COLUMN space_access.access_count IS 'Number of times this access grant has been used';
COMMENT ON COLUMN space_access.expires_at IS 'When this access grant expires';

-- Create trigger for SpaceAccess if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_space_access_last_accessed') THEN
        CREATE OR REPLACE FUNCTION update_last_accessed()
        RETURNS TRIGGER AS $trigger$
        BEGIN
           NEW.last_accessed = NOW();
           NEW.access_count = NEW.access_count + 1;
           RETURN NEW;
        END;
        $trigger$ language 'plpgsql';
        
        -- Note: This trigger would be activated by application logic, not automatically
    END IF;
EXCEPTION
    WHEN others THEN
        NULL;
END $$;

-- Sample data migration for existing spaces (mark them as non-template by default)
UPDATE spaces 
SET is_template = FALSE,
    storage_backend = 'local',
    schedule_type = 'none',
    execution_count = 0,
    is_scheduled_active = FALSE,
    auto_cleanup = FALSE,
    storage_size_bytes = 0
WHERE is_template IS NULL OR storage_backend IS NULL;

-- Grant permissions for new table
-- Uncomment and adjust as needed for your setup
-- GRANT ALL PRIVILEGES ON space_access TO your_app_user;
-- GRANT ALL PRIVILEGES ON SEQUENCE space_access_id_seq TO your_app_user;

COMMIT;