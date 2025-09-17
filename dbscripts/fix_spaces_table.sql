-- Quick fix for spaces table missing is_template column
-- Run this directly in your PostgreSQL database

BEGIN;

-- Add missing is_template column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='spaces' AND column_name='is_template'
    ) THEN
        ALTER TABLE spaces ADD COLUMN is_template BOOLEAN DEFAULT FALSE NOT NULL;
        CREATE INDEX ix_spaces_is_template ON spaces (is_template);
        RAISE NOTICE 'Added is_template column to spaces table';
    ELSE
        RAISE NOTICE 'is_template column already exists';
    END IF;
END $$;

-- Add other essential missing columns
DO $$ 
BEGIN
    -- Template-related columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='template_parameters') THEN
        ALTER TABLE spaces ADD COLUMN template_parameters JSONB;
        RAISE NOTICE 'Added template_parameters column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='template_schema') THEN
        ALTER TABLE spaces ADD COLUMN template_schema JSONB;
        RAISE NOTICE 'Added template_schema column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='base_query') THEN
        ALTER TABLE spaces ADD COLUMN base_query TEXT;
        RAISE NOTICE 'Added base_query column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='source_query') THEN
        ALTER TABLE spaces ADD COLUMN source_query TEXT;
        RAISE NOTICE 'Added source_query column';
    END IF;
    
    -- Storage columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='storage_backend') THEN
        ALTER TABLE spaces ADD COLUMN storage_backend VARCHAR(20) DEFAULT 'local' NOT NULL;
        RAISE NOTICE 'Added storage_backend column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='storage_size_bytes') THEN
        ALTER TABLE spaces ADD COLUMN storage_size_bytes INTEGER DEFAULT 0 NOT NULL;
        RAISE NOTICE 'Added storage_size_bytes column';
    END IF;
    
    -- Storage additional columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='storage_path') THEN
        ALTER TABLE spaces ADD COLUMN storage_path VARCHAR(500);
        RAISE NOTICE 'Added storage_path column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='external_url') THEN
        ALTER TABLE spaces ADD COLUMN external_url VARCHAR(1000);
        RAISE NOTICE 'Added external_url column';
    END IF;
    
    -- Scheduling columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='schedule_type') THEN
        ALTER TABLE spaces ADD COLUMN schedule_type VARCHAR(20) DEFAULT 'none' NOT NULL;
        RAISE NOTICE 'Added schedule_type column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='schedule_config') THEN
        ALTER TABLE spaces ADD COLUMN schedule_config JSONB;
        RAISE NOTICE 'Added schedule_config column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='next_execution') THEN
        ALTER TABLE spaces ADD COLUMN next_execution TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added next_execution column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='last_execution') THEN
        ALTER TABLE spaces ADD COLUMN last_execution TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added last_execution column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='execution_count') THEN
        ALTER TABLE spaces ADD COLUMN execution_count INTEGER DEFAULT 0 NOT NULL;
        RAISE NOTICE 'Added execution_count column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='is_scheduled_active') THEN
        ALTER TABLE spaces ADD COLUMN is_scheduled_active BOOLEAN DEFAULT FALSE NOT NULL;
        RAISE NOTICE 'Added is_scheduled_active column';
    END IF;
    
    -- Access and sharing columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='access_permissions') THEN
        ALTER TABLE spaces ADD COLUMN access_permissions JSONB;
        RAISE NOTICE 'Added access_permissions column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='team_id') THEN
        ALTER TABLE spaces ADD COLUMN team_id VARCHAR(100);
        RAISE NOTICE 'Added team_id column';
    END IF;
    
    -- Expiration columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='expires_at') THEN
        ALTER TABLE spaces ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added expires_at column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='auto_cleanup') THEN
        ALTER TABLE spaces ADD COLUMN auto_cleanup BOOLEAN DEFAULT FALSE NOT NULL;
        RAISE NOTICE 'Added auto_cleanup column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='retention_days') THEN
        ALTER TABLE spaces ADD COLUMN retention_days INTEGER;
        RAISE NOTICE 'Added retention_days column';
    END IF;
    
    -- Usage tracking columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='view_count') THEN
        ALTER TABLE spaces ADD COLUMN view_count INTEGER DEFAULT 0 NOT NULL;
        RAISE NOTICE 'Added view_count column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='share_count') THEN
        ALTER TABLE spaces ADD COLUMN share_count INTEGER DEFAULT 0 NOT NULL;
        RAISE NOTICE 'Added share_count column';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='spaces' AND column_name='last_accessed') THEN
        ALTER TABLE spaces ADD COLUMN last_accessed TIMESTAMP WITH TIME ZONE;
        RAISE NOTICE 'Added last_accessed column';
    END IF;
END $$;

-- Update existing records to set appropriate is_template values
UPDATE spaces SET is_template = TRUE WHERE content_type = 'template';

COMMIT;

-- Verify the changes
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'spaces' 
AND column_name IN (
    'is_template', 'template_parameters', 'storage_backend', 'execution_count',
    'schedule_type', 'access_permissions', 'view_count', 'share_count', 'last_accessed'
)
ORDER BY column_name;

-- Show total column count for spaces table
SELECT COUNT(*) as total_columns 
FROM information_schema.columns 
WHERE table_name = 'spaces';