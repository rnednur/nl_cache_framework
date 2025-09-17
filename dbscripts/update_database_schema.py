#!/usr/bin/env python3
"""
Script to update database schema with cache integration columns
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from backend directory
load_dotenv('/Users/rnednur/code/nl_cache_framework/backend/.env')
# Also try main directory
load_dotenv()

def update_database_schema():
    """Add cache integration columns to hot_commands table"""
    
    # Get database connection details from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        # Try to build from individual components
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        db = os.getenv('POSTGRES_DB', 'postgres')
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        print(f"🔧 Built DATABASE_URL from components: postgresql://{user}:***@{host}:{port}/{db}")
    
    if not db_url:
        print("❌ Could not determine database connection details")
        return False
    
    try:
        # Connect to database
        print("🔗 Connecting to database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check if hot_commands table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'hot_commands'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("⚠️  hot_commands table doesn't exist yet. Schema will be created when server starts.")
            return True
        
        print("📝 Adding cache integration columns...")
        
        # Add new columns
        columns_to_add = [
            ("cache_entry_id", "INTEGER"),
            ("source_template_type", "VARCHAR(50)"),
            ("source_reasoning", "TEXT"),
            ("source_tags", "JSONB"),
            ("source_execution_stats", "JSONB")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"""
                    ALTER TABLE hot_commands 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                """)
                print(f"   ✅ Added column: {col_name}")
            except Exception as e:
                print(f"   ⚠️  Column {col_name}: {e}")
        
        # Add foreign key constraint (if text2sql_cache table exists)
        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'text2sql_cache'
                );
            """)
            
            if cursor.fetchone()[0]:
                cursor.execute("""
                    ALTER TABLE hot_commands 
                    DROP CONSTRAINT IF EXISTS fk_hot_commands_cache_entry;
                """)
                cursor.execute("""
                    ALTER TABLE hot_commands 
                    ADD CONSTRAINT fk_hot_commands_cache_entry 
                    FOREIGN KEY (cache_entry_id) REFERENCES text2sql_cache(id);
                """)
                print("   ✅ Added foreign key constraint")
            else:
                print("   ⚠️  text2sql_cache table not found, skipping foreign key constraint")
        except Exception as e:
            print(f"   ⚠️  Foreign key constraint: {e}")
        
        # Add indexes
        indexes_to_add = [
            ("ix_hot_commands_cache_entry", "cache_entry_id"),
            ("ix_hot_commands_source_type", "source_template_type")
        ]
        
        for index_name, column_name in indexes_to_add:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON hot_commands({column_name});
                """)
                print(f"   ✅ Added index: {index_name}")
            except Exception as e:
                print(f"   ⚠️  Index {index_name}: {e}")
        
        # Commit changes
        conn.commit()
        print("✅ Database schema updated successfully!")
        
        # Show updated table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'hot_commands' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print(f"\n📋 Updated hot_commands table structure ({len(columns)} columns):")
        for col_name, col_type in columns:
            if col_name in ['cache_entry_id', 'source_template_type', 'source_reasoning', 'source_tags', 'source_execution_stats']:
                print(f"   🆕 {col_name}: {col_type}")
            else:
                print(f"      {col_name}: {col_type}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database schema: {e}")
        return False

if __name__ == "__main__":
    success = update_database_schema()
    if success:
        print("\n🎉 Ready to test cache integration!")
        print("Restart the server and try the endpoints again.")
    else:
        print("\n💥 Schema update failed. Check database connection and permissions.")