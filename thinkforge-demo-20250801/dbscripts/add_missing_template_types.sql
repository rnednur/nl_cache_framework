-- Migration script to add missing template_type enum values
-- This script adds the new template types defined in the TemplateType enum but missing from the database

-- Define schema name (replace during deployment with actual schema name)
\set schema_name 'public'

-- Add new template type values to the enum
-- Note: PostgreSQL enum values cannot be added in a transaction, so each ADD VALUE is separate

-- Add MCP_TOOL type for Model Context Protocol tools
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'mcp_tool';

-- Add AGENT type for AI agent definitions
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'agent';

-- Add FUNCTION type for reusable function definitions
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'function';

-- Add RECIPE type for complete automation recipes
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'recipe';

-- Add RECIPE_STEP type for individual recipe steps
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'recipe_step';

-- Add RECIPE_TEMPLATE type for parameterized recipe templates
ALTER TYPE :"schema_name".template_type ADD VALUE IF NOT EXISTS 'recipe_template';

-- Optional: Add comments to document the new enum values
COMMENT ON TYPE :"schema_name".template_type IS 'Enum for template types: sql, url, api, workflow, graphql, regex, script, nosql, cli, prompt, configuration, reasoning_steps, dsl, mcp_tool, agent, function, recipe, recipe_step, recipe_template';