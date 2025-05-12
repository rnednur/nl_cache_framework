-- Migration script to add 'reasoning_steps' to template_type enum
-- This script should be run on an existing database to update the enum

-- Define schema name (replace during deployment with actual schema name)
\set schema_name 'public'

-- Temporarily disable the constraint check
ALTER TABLE :"schema_name".text2sql_cache ALTER COLUMN template_type DROP NOT NULL;

-- Add reasoning_steps to the enum
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'reasoning_steps';

-- Re-enable the constraint check
ALTER TABLE :"schema_name".text2sql_cache ALTER COLUMN template_type SET NOT NULL; 