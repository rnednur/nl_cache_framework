#!/usr/bin/env python3
"""
Enhanced Spaces Functionality Migration for ThinkForge
This script adds enhanced spaces functionality including templates, scheduling,
external storage, and granular access control.
"""

import os
import sys
import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to path to import database configuration
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

try:
    from database import get_db_url, get_schema_name
except ImportError:
    # Fallback to environment variables
    def get_db_url():
        return os.getenv('DATABASE_URL', 
                         f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
                         f"{os.getenv('POSTGRES_PASSWORD', 'password')}@"
                         f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
                         f"{os.getenv('POSTGRES_PORT', '5432')}/"
                         f"{os.getenv('POSTGRES_DB', 'mcp_cache_db')}")
    
    def get_schema_name():
        return os.getenv('DB_SCHEMA', 'public')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SpacesMigration:
    """Handles the enhanced spaces functionality migration."""
    
    def __init__(self):
        self.db_url = get_db_url()
        self.schema_name = get_schema_name()
        self.engine = create_engine(self.db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.inspector = inspect(self.engine)
        
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        return table_name in self.inspector.get_table_names(schema=self.schema_name)
    
    def check_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        columns = self.inspector.get_columns(table_name, schema=self.schema_name)
        return any(col['name'] == column_name for col in columns)
    
    def add_columns_to_spaces(self) -> None:
        """Add enhanced columns to the spaces table."""
        logger.info("Adding enhanced columns to spaces table...")
        
        # Define new columns to add
        new_columns = [
            # Template functionality
            ("is_template", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("template_parameters", "JSONB"),
            ("template_schema", "JSONB"),
            ("base_query", "TEXT"),
            ("source_query", "TEXT"),
            
            # External storage
            ("storage_path", "VARCHAR(500)"),
            ("storage_backend", "VARCHAR(20) NOT NULL DEFAULT 'local'"),
            ("storage_size_bytes", "INTEGER NOT NULL DEFAULT 0"),
            ("external_url", "VARCHAR(1000)"),
            
            # Scheduling and automation
            ("schedule_type", "VARCHAR(20) NOT NULL DEFAULT 'none'"),
            ("schedule_config", "JSONB"),
            ("next_execution", "TIMESTAMP WITH TIME ZONE"),
            ("last_execution", "TIMESTAMP WITH TIME ZONE"),
            ("execution_count", "INTEGER NOT NULL DEFAULT 0"),
            ("is_scheduled_active", "BOOLEAN NOT NULL DEFAULT FALSE"),
            
            # Enhanced sharing and permissions
            ("access_permissions", "JSONB"),
            ("team_id", "VARCHAR(100)"),
            
            # Expiration and cleanup
            ("expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("auto_cleanup", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("retention_days", "INTEGER")
        ]
        
        for column_name, column_def in new_columns:
            if not self.check_column_exists('spaces', column_name):
                try:
                    query = f"ALTER TABLE {self.schema_name}.spaces ADD COLUMN {column_name} {column_def};"
                    self.session.execute(text(query))
                    logger.info(f"Added column '{column_name}' to spaces table")
                except SQLAlchemyError as e:
                    logger.warning(f"Failed to add column '{column_name}': {e}")
                    # Continue with other columns
                    self.session.rollback()
            else:
                logger.info(f"Column '{column_name}' already exists in spaces table")
    
    def create_space_access_table(self) -> None:
        """Create the space_access table for granular permissions."""
        logger.info("Creating space_access table...")
        
        if self.check_table_exists('space_access'):
            logger.info("space_access table already exists")
            return
        
        create_table_sql = f"""
        CREATE TABLE {self.schema_name}.space_access (
            id SERIAL PRIMARY KEY,
            space_id INTEGER NOT NULL REFERENCES {self.schema_name}.spaces(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES {self.schema_name}.users(id) ON DELETE CASCADE,
            granted_by INTEGER NOT NULL REFERENCES {self.schema_name}.users(id) ON DELETE CASCADE,
            
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
        """
        
        try:
            self.session.execute(text(create_table_sql))
            logger.info("Created space_access table successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create space_access table: {e}")
            raise
    
    def add_constraints(self) -> None:
        """Add check constraints for new columns."""
        logger.info("Adding constraints for enhanced spaces...")
        
        constraints = [
            ("check_storage_backend", "storage_backend IN ('local', 's3', 'gcs', 'azure')"),
            ("check_schedule_type", "schedule_type IN ('none', 'interval', 'cron', 'webhook')")
        ]
        
        for constraint_name, constraint_def in constraints:
            try:
                # Check if constraint already exists
                check_sql = f"""
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_name = 'spaces' 
                AND table_schema = '{self.schema_name}'
                AND constraint_name = '{constraint_name}';
                """
                result = self.session.execute(text(check_sql)).fetchone()
                
                if not result:
                    alter_sql = f"""
                    ALTER TABLE {self.schema_name}.spaces 
                    ADD CONSTRAINT {constraint_name} CHECK ({constraint_def});
                    """
                    self.session.execute(text(alter_sql))
                    logger.info(f"Added constraint '{constraint_name}'")
                else:
                    logger.info(f"Constraint '{constraint_name}' already exists")
                    
            except SQLAlchemyError as e:
                logger.warning(f"Failed to add constraint '{constraint_name}': {e}")
                self.session.rollback()
    
    def create_indexes(self) -> None:
        """Create indexes for new columns."""
        logger.info("Creating indexes for enhanced spaces...")
        
        indexes = [
            ("ix_spaces_is_template", "spaces", ["is_template"]),
            ("ix_spaces_storage_backend", "spaces", ["storage_backend"]),
            ("ix_spaces_schedule_type", "spaces", ["schedule_type"]),
            ("ix_spaces_next_execution", "spaces", ["next_execution"]),
            ("ix_spaces_last_execution", "spaces", ["last_execution"]),
            ("ix_spaces_is_scheduled_active", "spaces", ["is_scheduled_active"]),
            ("ix_spaces_team_id", "spaces", ["team_id"]),
            ("ix_spaces_expires_at", "spaces", ["expires_at"]),
            
            # SpaceAccess indexes
            ("ix_space_access_space_id", "space_access", ["space_id"]),
            ("ix_space_access_user_id", "space_access", ["user_id"]),
            ("ix_space_access_granted_by", "space_access", ["granted_by"]),
            ("ix_space_access_space_user", "space_access", ["space_id", "user_id"]),
            ("ix_space_access_active", "space_access", ["is_active", "expires_at"]),
            ("ix_space_access_level", "space_access", ["access_level", "is_active"]),
            ("ix_space_access_last_accessed", "space_access", ["last_accessed"])
        ]
        
        for index_name, table_name, columns in indexes:
            try:
                # Check if index already exists
                check_sql = f"""
                SELECT 1 FROM pg_indexes 
                WHERE tablename = '{table_name}' 
                AND schemaname = '{self.schema_name}'
                AND indexname = '{index_name}';
                """
                result = self.session.execute(text(check_sql)).fetchone()
                
                if not result:
                    columns_str = ", ".join(columns)
                    create_sql = f"""
                    CREATE INDEX {index_name} ON {self.schema_name}.{table_name}({columns_str});
                    """
                    self.session.execute(text(create_sql))
                    logger.info(f"Created index '{index_name}'")
                else:
                    logger.info(f"Index '{index_name}' already exists")
                    
            except SQLAlchemyError as e:
                logger.warning(f"Failed to create index '{index_name}': {e}")
                self.session.rollback()
    
    def update_existing_data(self) -> None:
        """Update existing spaces with default values for new columns."""
        logger.info("Updating existing spaces with default values...")
        
        try:
            update_sql = f"""
            UPDATE {self.schema_name}.spaces 
            SET 
                is_template = COALESCE(is_template, FALSE),
                storage_backend = COALESCE(storage_backend, 'local'),
                schedule_type = COALESCE(schedule_type, 'none'),
                execution_count = COALESCE(execution_count, 0),
                is_scheduled_active = COALESCE(is_scheduled_active, FALSE),
                auto_cleanup = COALESCE(auto_cleanup, FALSE),
                storage_size_bytes = COALESCE(storage_size_bytes, 0)
            WHERE 
                is_template IS NULL OR 
                storage_backend IS NULL OR 
                schedule_type IS NULL OR
                execution_count IS NULL OR
                is_scheduled_active IS NULL OR
                auto_cleanup IS NULL OR
                storage_size_bytes IS NULL;
            """
            
            result = self.session.execute(text(update_sql))
            rows_updated = result.rowcount
            logger.info(f"Updated {rows_updated} existing spaces with default values")
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to update existing data: {e}")
            self.session.rollback()
            raise
    
    def add_table_comments(self) -> None:
        """Add comments to tables and columns."""
        logger.info("Adding table and column comments...")
        
        comments = [
            ("TABLE", "space_access", "Granular access control for spaces with permission levels and expiration"),
            ("COLUMN", "spaces.is_template", "Whether this space is a parameterized template"),
            ("COLUMN", "spaces.template_parameters", "JSON array of parameter definitions for templates"),
            ("COLUMN", "spaces.template_schema", "JSON schema for parameter validation"),
            ("COLUMN", "spaces.base_query", "Base query template with parameter placeholders"),
            ("COLUMN", "spaces.source_query", "Original source query without parameters"),
            ("COLUMN", "spaces.storage_backend", "External storage backend (local, s3, gcs, azure)"),
            ("COLUMN", "spaces.schedule_type", "Type of automated execution schedule"),
            ("COLUMN", "spaces.schedule_config", "Configuration for scheduled execution (cron, interval, webhook)"),
            ("COLUMN", "spaces.external_url", "Public URL for external sharing (e.g., webpage exports)"),
            ("COLUMN", "spaces.team_id", "Team identifier for team-based spaces"),
            ("COLUMN", "spaces.expires_at", "When the space expires and can be cleaned up"),
            ("COLUMN", "spaces.auto_cleanup", "Whether to automatically clean up expired spaces"),
            ("COLUMN", "space_access.access_level", "Permission level: view, comment, edit, admin"),
            ("COLUMN", "space_access.restrictions", "Additional JSON-based access restrictions"),
            ("COLUMN", "space_access.access_count", "Number of times this access grant has been used"),
            ("COLUMN", "space_access.expires_at", "When this access grant expires")
        ]
        
        for comment_type, object_name, comment_text in comments:
            try:
                if comment_type == "TABLE":
                    sql = f"COMMENT ON TABLE {self.schema_name}.{object_name} IS '{comment_text}';"
                else:  # COLUMN
                    sql = f"COMMENT ON COLUMN {self.schema_name}.{object_name} IS '{comment_text}';"
                
                self.session.execute(text(sql))
                logger.info(f"Added comment for {comment_type.lower()} {object_name}")
                
            except SQLAlchemyError as e:
                logger.warning(f"Failed to add comment for {object_name}: {e}")
                self.session.rollback()
    
    def run_migration(self) -> None:
        """Run the complete migration."""
        logger.info("Starting enhanced spaces functionality migration...")
        
        try:
            # Check if spaces table exists
            if not self.check_table_exists('spaces'):
                logger.error("Spaces table does not exist. Please run the base hot commands migration first.")
                return False
            
            # Run migration steps
            self.add_columns_to_spaces()
            self.create_space_access_table()
            self.add_constraints()
            self.create_indexes()
            self.update_existing_data()
            self.add_table_comments()
            
            # Commit all changes
            self.session.commit()
            logger.info("Enhanced spaces functionality migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.session.rollback()
            return False
        finally:
            self.session.close()

def main():
    """Main entry point for the migration script."""
    migration = SpacesMigration()
    success = migration.run_migration()
    
    if success:
        logger.info("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()