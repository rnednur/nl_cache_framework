-- Migration script to add tool-related columns to text2sql_cache table
-- This script adds the missing columns that are defined in the SQLAlchemy model

-- Add tool-specific metadata fields
ALTER TABLE public.text2sql_cache 
ADD COLUMN IF NOT EXISTS tool_capabilities JSONB,
ADD COLUMN IF NOT EXISTS tool_dependencies JSONB,
ADD COLUMN IF NOT EXISTS execution_config JSONB,
ADD COLUMN IF NOT EXISTS health_status VARCHAR,
ADD COLUMN IF NOT EXISTS last_tested TIMESTAMP;

-- Add recipe-specific metadata fields
ALTER TABLE public.text2sql_cache 
ADD COLUMN IF NOT EXISTS recipe_steps JSONB,
ADD COLUMN IF NOT EXISTS required_tools JSONB,
ADD COLUMN IF NOT EXISTS execution_time_estimate INTEGER,
ADD COLUMN IF NOT EXISTS complexity_level VARCHAR,
ADD COLUMN IF NOT EXISTS success_rate FLOAT,
ADD COLUMN IF NOT EXISTS last_executed TIMESTAMP,
ADD COLUMN IF NOT EXISTS execution_count INTEGER DEFAULT 0;

-- Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_text2sql_cache_health_status ON public.text2sql_cache(health_status);
CREATE INDEX IF NOT EXISTS idx_text2sql_cache_complexity_level ON public.text2sql_cache(complexity_level);
CREATE INDEX IF NOT EXISTS idx_text2sql_cache_last_tested ON public.text2sql_cache(last_tested);
CREATE INDEX IF NOT EXISTS idx_text2sql_cache_last_executed ON public.text2sql_cache(last_executed);

-- Add comments to document the new columns
COMMENT ON COLUMN public.text2sql_cache.tool_capabilities IS 'JSON array of capabilities that the tool provides (e.g., [''image_processing'', ''pdf_conversion''])';
COMMENT ON COLUMN public.text2sql_cache.tool_dependencies IS 'JSON object describing tool dependencies and requirements';
COMMENT ON COLUMN public.text2sql_cache.execution_config IS 'JSON object for execution parameters and constraints';
COMMENT ON COLUMN public.text2sql_cache.health_status IS 'Current health status of the tool (''healthy'', ''degraded'', ''unhealthy'', ''unknown'')';
COMMENT ON COLUMN public.text2sql_cache.last_tested IS 'Timestamp of when the tool was last validated or tested';
COMMENT ON COLUMN public.text2sql_cache.recipe_steps IS 'JSON array of recipe steps with execution order, dependencies, and parameters';
COMMENT ON COLUMN public.text2sql_cache.required_tools IS 'JSON array of tool cache entry IDs that this recipe depends on for execution';
COMMENT ON COLUMN public.text2sql_cache.execution_time_estimate IS 'Estimated execution time in seconds for the complete recipe';
COMMENT ON COLUMN public.text2sql_cache.complexity_level IS 'Recipe complexity level (''beginner'', ''intermediate'', ''advanced'') for user guidance';
COMMENT ON COLUMN public.text2sql_cache.success_rate IS 'Historical success rate percentage (0-100) based on execution history';
COMMENT ON COLUMN public.text2sql_cache.last_executed IS 'Timestamp of when the recipe was last executed';
COMMENT ON COLUMN public.text2sql_cache.execution_count IS 'Total number of times this recipe has been executed'; 