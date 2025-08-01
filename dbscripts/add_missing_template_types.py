#!/usr/bin/env python3
"""
Add missing template_type enum values to the database

This script adds the template type enum values that are defined in the Python TemplateType enum
but are missing from the database enum. The missing values are:
- mcp_tool (Model Context Protocol tools)
- agent (AI agent definitions)  
- function (Reusable function definitions)
- recipe (Complete automation recipes)
- recipe_step (Individual recipe steps)
- recipe_template (Parameterized recipe templates)

It uses SQLAlchemy to connect to the database and execute the SQL commands.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib.parse

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("add_missing_template_types")

# Load environment variables
load_dotenv()

# Get database connection details
DB_USER = os.environ.get("POSTGRES_USER", "user")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
DB_PASSWORD_encoded = urllib.parse.quote_plus(DB_PASSWORD)
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "mcp_cache_db")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

# Full database URL (can be overridden by DATABASE_URL env var)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# List of template types to add
TEMPLATE_TYPES_TO_ADD = [
    ("mcp_tool", "Model Context Protocol (MCP) tools for extensible AI functionality"),
    ("agent", "AI Agent definitions for autonomous task execution"),
    ("function", "Reusable function definitions for various programming languages"),
    ("recipe", "Complete automation recipes defining multi-step workflows"),
    ("recipe_step", "Individual recipe steps that can be composed into larger workflows"),
    ("recipe_template", "Parameterized recipe templates for common automation patterns")
]

def check_enum_value_exists(connection, schema, enum_name, enum_value):
    """Check if an enum value already exists in the PostgreSQL enum type."""
    check_query = text(f"""
    SELECT enumlabel 
    FROM pg_enum e
    JOIN pg_type t ON e.enumtypid = t.oid
    JOIN pg_namespace n ON t.typnamespace = n.oid
    WHERE n.nspname = '{schema}' 
    AND t.typname = '{enum_name}'
    AND e.enumlabel = '{enum_value}'
    """)
    
    result = connection.execute(check_query)
    return result.fetchone() is not None

def add_enum_value(connection, schema, enum_name, enum_value):
    """Add a new value to a PostgreSQL enum type."""
    # Note: ALTER TYPE ... ADD VALUE cannot be run inside a transaction block
    # We need to use autocommit mode for this operation
    connection.execute(text("COMMIT"))  # End any current transaction
    
    add_value_query = text(f"""
    ALTER TYPE {schema}.{enum_name} ADD VALUE IF NOT EXISTS '{enum_value}'
    """)
    
    connection.execute(add_value_query)
    logger.info(f"Added enum value '{enum_value}' to {schema}.{enum_name}")

def add_missing_template_types():
    """Add missing template type enum values to the database."""
    try:
        logger.info(f"Connecting to database: {DATABASE_URL}")
        
        # Create engine with autocommit for enum operations
        engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
        
        # Connect to the database
        with engine.connect() as connection:
            logger.info(f"Checking and adding missing template_type enum values...")
            
            added_count = 0
            for enum_value, description in TEMPLATE_TYPES_TO_ADD:
                if check_enum_value_exists(connection, DB_SCHEMA, "template_type", enum_value):
                    logger.info(f"Enum value '{enum_value}' already exists in template_type.")
                else:
                    logger.info(f"Adding enum value '{enum_value}' ({description})...")
                    add_enum_value(connection, DB_SCHEMA, "template_type", enum_value)
                    added_count += 1
            
            if added_count > 0:
                logger.info(f"Successfully added {added_count} new enum values to template_type.")
                
                # Update the enum type comment to document all values
                comment_query = text(f"""
                COMMENT ON TYPE {DB_SCHEMA}.template_type IS 
                'Enum for template types: sql, url, api, workflow, graphql, regex, script, nosql, cli, prompt, configuration, reasoning_steps, dsl, mcp_tool, agent, function, recipe, recipe_step, recipe_template'
                """)
                connection.execute(comment_query)
                logger.info("Updated template_type enum documentation.")
            else:
                logger.info("All required enum values already exist. No changes needed.")
        
        return True
    except Exception as e:
        logger.error(f"Error adding missing template type enum values: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if add_missing_template_types():
        logger.info("Successfully processed template_type enum values.")
        sys.exit(0)
    else:
        logger.error("Failed to add missing template_type enum values.")
        sys.exit(1)