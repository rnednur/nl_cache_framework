#!/usr/bin/env python3
"""
Quick checker and fixer for spaces table issues
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_database_connection():
    """Check various database connection possibilities."""
    
    connection_attempts = [
        # Try DATABASE_URL first
        {
            'method': 'DATABASE_URL',
            'connection': os.getenv('DATABASE_URL')
        },
        # Try with postgres default user
        {
            'method': 'postgres user',
            'connection': {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'mcp_cache_db'),
                'user': 'postgres',
                'password': os.getenv('POSTGRES_PASSWORD', 'password')
            }
        },
        # Try with configured user
        {
            'method': 'configured user',
            'connection': {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'mcp_cache_db'),
                'user': os.getenv('POSTGRES_USER', 'user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'password')
            }
        }
    ]
    
    for attempt in connection_attempts:
        try:
            print(f"Trying connection with {attempt['method']}...")
            
            if attempt['method'] == 'DATABASE_URL' and attempt['connection']:
                conn = psycopg2.connect(attempt['connection'])
            else:
                conn = psycopg2.connect(**attempt['connection'])
            
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            print(f"✅ Connected successfully using {attempt['method']}")
            print(f"PostgreSQL version: {version}")
            
            return conn, attempt['method']
            
        except Exception as e:
            print(f"❌ Failed with {attempt['method']}: {e}")
            continue
    
    return None, None

def check_spaces_table(conn):
    """Check if spaces table exists and what columns it has."""
    try:
        cursor = conn.cursor()
        
        # Check if spaces table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'spaces'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("❌ Spaces table does not exist!")
            return False
        
        print("✅ Spaces table exists")
        
        # Check for is_template column
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'spaces' AND column_name = 'is_template';
        """)
        
        has_is_template = cursor.fetchone() is not None
        
        if has_is_template:
            print("✅ is_template column exists")
            return True
        else:
            print("❌ is_template column is missing!")
            return False
            
    except Exception as e:
        print(f"Error checking spaces table: {e}")
        return False

def apply_fix(conn):
    """Apply the fix for missing columns."""
    try:
        cursor = conn.cursor()
        
        print("Applying fix for missing is_template column...")
        
        # Read and execute the fix SQL
        sql_file = os.path.join(os.path.dirname(__file__), '..', 'fix_spaces_table.sql')
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Fix applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        return False

def main():
    print("ThinkForge Spaces Table Checker & Fixer")
    print("=" * 45)
    
    # Check database connection
    conn, method = check_database_connection()
    
    if not conn:
        print("\n💥 Could not connect to database!")
        print("\nTo fix this:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your .env file or environment variables")
        print("3. Ensure the database 'mcp_cache_db' exists")
        print("4. Verify user permissions")
        return
    
    # Check spaces table
    print(f"\nChecking spaces table...")
    needs_fix = not check_spaces_table(conn)
    
    if needs_fix:
        print("\n🔧 Applying fix...")
        if apply_fix(conn):
            print("\n🎉 Fix completed successfully!")
            print("You can now restart your application.")
        else:
            print("\n💥 Fix failed!")
    else:
        print("\n✅ No fix needed - spaces table is properly configured!")
    
    conn.close()

if __name__ == "__main__":
    main()