#!/usr/bin/env python3
"""
Check current template_type enum values in the database

This script connects to the database and compares the current template_type enum values
with what is defined in the Python TemplateType enum to identify missing values.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib.parse

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("check_template_types")

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

# Expected template types from the Python TemplateType enum (lowercase)
EXPECTED_TEMPLATE_TYPES = {
    'sql', 'url', 'api', 'workflow', 'graphql', 'regex', 'script', 'nosql', 
    'cli', 'prompt', 'configuration', 'reasoning_steps', 'dsl', 'mcp_tool', 
    'agent', 'function', 'recipe', 'recipe_step', 'recipe_template'
}

def get_current_enum_values():
    """Get the current template_type enum values from the database."""
    try:
        logger.info(f"Connecting to database: {DATABASE_URL}")
        
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Connect to the database
        with engine.connect() as connection:
            # Query current enum values
            query = text(f"""
            SELECT enumlabel 
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            JOIN pg_namespace n ON t.typnamespace = n.oid
            WHERE n.nspname = '{DB_SCHEMA}' 
            AND t.typname = 'template_type'
            ORDER BY enumlabel
            """)
            
            result = connection.execute(query)
            current_values = {row[0] for row in result.fetchall()}
            
            return current_values
    except Exception as e:
        logger.error(f"Error getting current enum values: {e}")
        return set()

def main():
    """Main function to check and compare template types."""
    try:
        # Get current values from database
        current_values = get_current_enum_values()
        
        if not current_values:
            logger.error("Could not retrieve current enum values from database")
            return False
        
        logger.info("=== TEMPLATE TYPE ENUM ANALYSIS ===")
        logger.info(f"Database schema: {DB_SCHEMA}")
        logger.info(f"Current enum values in database: {len(current_values)}")
        logger.info(f"Expected enum values from code: {len(EXPECTED_TEMPLATE_TYPES)}")
        
        # Print current values
        logger.info("\nCurrent values in database:")
        for value in sorted(current_values):
            logger.info(f"  ✓ {value}")
        
        # Find missing values
        missing_values = EXPECTED_TEMPLATE_TYPES - current_values
        if missing_values:
            logger.info(f"\nMissing values (need migration): {len(missing_values)}")
            for value in sorted(missing_values):
                logger.info(f"  ✗ {value}")
        else:
            logger.info("\n✅ All expected template types are present in the database")
        
        # Find extra values (shouldn't happen, but good to check)
        extra_values = current_values - EXPECTED_TEMPLATE_TYPES
        if extra_values:
            logger.info(f"\nExtra values in database (not in code): {len(extra_values)}")
            for value in sorted(extra_values):
                logger.info(f"  ? {value}")
        
        # Summary
        logger.info("\n=== SUMMARY ===")
        if missing_values:
            logger.info(f"❌ Migration needed: {len(missing_values)} template types are missing")
            logger.info("Run: python add_missing_template_types.py")
        else:
            logger.info("✅ No migration needed: all template types are present")
        
        return len(missing_values) == 0
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)