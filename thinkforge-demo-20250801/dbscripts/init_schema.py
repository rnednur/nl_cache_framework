#!/usr/bin/env python3
"""
Database Schema Initialization Utility

This script creates or updates the database schema for the NL Cache Framework.
It reads the schema name from the environment variables and replaces it in the SQL scripts.

Usage:
    python dbscripts/init_schema.py [--create-schema]
"""

import os
import sys
import argparse
import logging
import subprocess
from dotenv import load_dotenv
import psycopg2

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("init_schema")

# Load environment variables
load_dotenv()

# Get database connection details
DB_USER = os.environ.get("POSTGRES_USER", "user")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "mcp_cache_db")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

# Full database URL (can be overridden by DATABASE_URL env var)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Path to SQL script
SQL_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "create_tables.sql")


def create_schema():
    """Create the schema if it doesn't exist."""
    try:
        logger.info(f"Connecting to database: {DATABASE_URL}")
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if schema exists
        cursor.execute(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{DB_SCHEMA}'")
        if cursor.fetchone() is None:
            logger.info(f"Schema '{DB_SCHEMA}' does not exist. Creating...")
            cursor.execute(f"CREATE SCHEMA {DB_SCHEMA}")
            logger.info(f"Schema '{DB_SCHEMA}' created successfully.")
        else:
            logger.info(f"Schema '{DB_SCHEMA}' already exists.")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        return False


def run_sql_script():
    """Run the SQL script with the correct schema name."""
    try:
        # Read the SQL script
        with open(SQL_SCRIPT_PATH, 'r') as f:
            sql_script = f.read()
        
        # Create a temporary file with the schema name replaced
        temp_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_create_tables.sql")
        with open(temp_script_path, 'w') as f:
            # Replace the schema name in the script
            f.write(sql_script.replace("\\set schema_name 'public'", f"\\set schema_name '{DB_SCHEMA}'"))
        
        # Run the script using psql
        psql_command = [
            "psql",
            f"--username={DB_USER}",
            f"--host={DB_HOST}",
            f"--port={DB_PORT}",
            f"--dbname={DB_NAME}",
            "--no-password",  # Use .pgpass file or environment variables
            "-f", temp_script_path
        ]
        
        # Set PGPASSWORD environment variable for the subprocess
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASSWORD
        
        logger.info(f"Running SQL script with schema: {DB_SCHEMA}")
        result = subprocess.run(psql_command, env=env, capture_output=True, text=True)
        
        # Clean up the temporary file
        os.unlink(temp_script_path)
        
        if result.returncode != 0:
            logger.error(f"Error executing SQL script: {result.stderr}")
            return False
        
        logger.info("SQL script executed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running SQL script: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Initialize database schema for NL Cache Framework")
    parser.add_argument("--create-schema", action="store_true", help="Create the schema if it doesn't exist")
    args = parser.parse_args()
    
    logger.info(f"Initializing database schema: {DB_SCHEMA}")
    
    if args.create_schema:
        if not create_schema():
            logger.error("Failed to create schema")
            sys.exit(1)
    
    if not run_sql_script():
        logger.error("Failed to run SQL script")
        sys.exit(1)
    
    logger.info(f"Database schema '{DB_SCHEMA}' initialized successfully")


if __name__ == "__main__":
    main() 