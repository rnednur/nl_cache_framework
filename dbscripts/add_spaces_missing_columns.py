#!/usr/bin/env python3
"""
Migration script to add missing columns to spaces table
This addresses the psycopg2.errors.UndefinedColumn error for spaces.is_template
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def get_db_connection():
    """Get database connection from environment variables."""
    try:
        # Try environment variables first
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return psycopg2.connect(db_url)
        
        # Fallback to individual environment variables
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'mcp_cache_db'),
            user=os.getenv('POSTGRES_USER', 'user'),
            password=os.getenv('POSTGRES_PASSWORD', 'password')
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def run_migration():
    """Run the spaces table migration."""
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        return False
    
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Starting spaces table migration...")
        
        # Read the SQL migration file
        sql_file_path = os.path.join(os.path.dirname(__file__), 'add_spaces_missing_columns.sql')
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
        
        # Execute the migration
        cursor.execute(sql_content)
        
        print("✅ Migration completed successfully!")
        
        # Verify the migration by checking if is_template column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'spaces' AND column_name = 'is_template';
        """)
        
        result = cursor.fetchone()
        if result:
            print("✅ Verified: is_template column exists in spaces table")
        else:
            print("❌ Warning: is_template column not found after migration")
        
        # Check for other key columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'spaces' 
            AND column_name IN ('template_parameters', 'storage_backend', 'schedule_type')
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        print(f"✅ Found {len(columns)} additional columns: {[col[0] for col in columns]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    print("ThinkForge Spaces Table Migration")
    print("=" * 40)
    
    success = run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now restart your application.")
    else:
        print("\n💥 Migration failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)