-- Add LLM_STEP template type to the database
-- This script adds the 'llm_step' template type to support custom LLM-powered steps in recipes

-- Check if the template type already exists to avoid duplicates
DO $$
BEGIN
    -- Add the llm_step template type if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints 
        WHERE constraint_name LIKE '%template_type%' 
        AND check_clause LIKE '%llm_step%'
    ) THEN
        -- First, drop the existing constraint
        ALTER TABLE text2sql_cache DROP CONSTRAINT IF EXISTS text2sql_cache_template_type_check;
        
        -- Add the new constraint with llm_step included
        ALTER TABLE text2sql_cache ADD CONSTRAINT text2sql_cache_template_type_check 
        CHECK (template_type IN (
            'sql', 'url', 'api', 'workflow', 'graphql', 'regex', 'script', 
            'nosql', 'cli', 'prompt', 'reasoning_steps', 'dsl', 'mcp_tool', 
            'agent', 'function', 'recipe', 'recipe_step', 'recipe_template', 
            'configuration', 'llm_step'
        ));
        
        RAISE NOTICE 'Added llm_step template type to text2sql_cache table';
    ELSE
        RAISE NOTICE 'llm_step template type already exists';
    END IF;
END $$;