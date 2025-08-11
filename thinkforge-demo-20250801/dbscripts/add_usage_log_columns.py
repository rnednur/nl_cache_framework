#!/usr/bin/env python3
"""
Add missing columns to usage_log table

This script adds the response, considered_entries, and is_confident columns 
to the usage_log table if they don't exist.
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
logger = logging.getLogger("add_usage_log_columns")

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

def add_usage_log_columns():
    """Add missing columns to the usage_log table if they don't exist."""
    try:
        logger.info(f"Connecting to database: {DATABASE_URL}")
        
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Connect to the database
        with engine.connect() as connection:
            # Check for existing columns
            columns_to_add = [
                ("response", "TEXT"),
                ("considered_entries", "JSONB"),
                ("is_confident", "BOOLEAN")
            ]
            
            for column_name, column_type in columns_to_add:
                # Check if column exists
                check_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = '{DB_SCHEMA}' 
                AND table_name = 'usage_log' 
                AND column_name = '{column_name}'
                """)
                
                result = connection.execute(check_query)
                column_exists = result.fetchone() is not None
                
                if column_exists:
                    logger.info(f"Column '{column_name}' already exists in the usage_log table.")
                else:
                    logger.info(f"Adding '{column_name}' column to the usage_log table...")
                    
                    # Add the column
                    add_column_query = text(f"""
                    ALTER TABLE {DB_SCHEMA}.usage_log 
                    ADD COLUMN {column_name} {column_type}
                    """)
                    
                    connection.execute(add_column_query)
                    connection.commit()
                    logger.info(f"Column '{column_name}' added successfully.")
        
        return True
    except Exception as e:
        logger.error(f"Error adding columns to usage_log table: {e}")
        return False

if __name__ == "__main__":
    if add_usage_log_columns():
        logger.info("Successfully added missing columns to the usage_log table.")
        sys.exit(0)
    else:
        logger.error("Failed to add missing columns to the usage_log table.")
        sys.exit(1) 