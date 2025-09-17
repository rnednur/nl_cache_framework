#!/usr/bin/env python3
"""
Fix foreign key constraint issue
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/rnednur/code/nl_cache_framework/backend/.env')
load_dotenv()

def fix_foreign_key():
    """Remove problematic foreign key constraint"""
    
    # Get database connection
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'postgres')
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    try:
        print("🔗 Connecting to database...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Drop the foreign key constraint
        print("🗑️ Removing problematic foreign key constraint...")
        cursor.execute("""
            ALTER TABLE hot_commands 
            DROP CONSTRAINT IF EXISTS fk_hot_commands_cache_entry;
        """)
        
        # Keep the column but without the constraint for now
        print("✅ Foreign key constraint removed")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("🎉 Fixed! Now cache integration should work without foreign key issues.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_foreign_key()
    if success:
        print("Ready to test cache integration again!")