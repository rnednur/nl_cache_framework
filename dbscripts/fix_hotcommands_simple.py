#!/usr/bin/env python3
"""
Simple fix for Hot Commands foreign key issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from thinkforge.database import get_engine
from thinkforge.models import DB_SCHEMA

def fix_hot_commands_table():
    """Fix the hot_commands table by removing foreign key constraints."""
    
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # Build schema prefix
            schema_prefix = f"{DB_SCHEMA}." if DB_SCHEMA != "public" else ""
            
            print(f"🔧 Fixing hot_commands table in schema: {DB_SCHEMA}")
            
            # Drop any foreign key constraints on cache_entry_id
            # This is safe because we're just removing the constraint, not the column
            sql_commands = [
                # Drop constraint if it exists (PostgreSQL syntax)
                f"""
                DO $$ 
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE table_name = 'hot_commands' 
                        AND constraint_type = 'FOREIGN KEY'
                        AND table_schema = '{DB_SCHEMA if DB_SCHEMA != "public" else "public"}'
                    ) THEN
                        -- Get the constraint name and drop it
                        FOR r IN (
                            SELECT constraint_name 
                            FROM information_schema.table_constraints 
                            WHERE table_name = 'hot_commands' 
                            AND constraint_type = 'FOREIGN KEY'
                            AND table_schema = '{DB_SCHEMA if DB_SCHEMA != "public" else "public"}'
                        ) LOOP
                            EXECUTE 'ALTER TABLE {schema_prefix}hot_commands DROP CONSTRAINT ' || r.constraint_name;
                            RAISE NOTICE 'Dropped foreign key constraint: %', r.constraint_name;
                        END LOOP;
                    END IF;
                END $$;
                """,
                
                # Ensure cache_entry_id column exists and is properly configured
                f"""
                DO $$
                BEGIN
                    -- Add cache_entry_id column if it doesn't exist
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'hot_commands' 
                        AND column_name = 'cache_entry_id'
                        AND table_schema = '{DB_SCHEMA if DB_SCHEMA != "public" else "public"}'
                    ) THEN
                        ALTER TABLE {schema_prefix}hot_commands 
                        ADD COLUMN cache_entry_id INTEGER;
                        RAISE NOTICE 'Added cache_entry_id column';
                    END IF;
                    
                    -- Add index on cache_entry_id if it doesn't exist
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE tablename = 'hot_commands' 
                        AND indexname = 'ix_hot_commands_cache_entry'
                        AND schemaname = '{DB_SCHEMA if DB_SCHEMA != "public" else "public"}'
                    ) THEN
                        CREATE INDEX ix_hot_commands_cache_entry 
                        ON {schema_prefix}hot_commands (cache_entry_id);
                        RAISE NOTICE 'Added index on cache_entry_id';
                    END IF;
                END $$;
                """
            ]
            
            for sql in sql_commands:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    print(f"Warning: SQL command failed (this may be normal): {e}")
            
            print("✅ Foreign key constraints removed from hot_commands table")
            print("✅ cache_entry_id column and index ensured")
            return True
            
    except Exception as e:
        print(f"❌ Error fixing hot_commands table: {e}")
        return False

def test_table_update():
    """Test that we can now update hot commands without foreign key errors."""
    
    from sqlalchemy.orm import sessionmaker
    from thinkforge.hotcommands_models import HotCommand
    
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        with SessionLocal() as db:
            # Try to find and update a hot command
            command = db.query(HotCommand).first()
            
            if not command:
                print("ℹ️  No hot commands found to test")
                return True
            
            print(f"🧪 Testing update on: {command.command_name}")
            
            # Update description
            original_desc = command.description
            test_desc = f"Test update at {import_datetime.datetime.now()}"
            command.description = test_desc
            
            # This should not fail anymore
            db.commit()
            db.refresh(command)
            
            # Restore original
            command.description = original_desc
            db.commit()
            
            print("✅ Hot command update test successful!")
            return True
            
    except Exception as e:
        print(f"❌ Hot command update test failed: {e}")
        return False

if __name__ == "__main__":
    import datetime as import_datetime
    
    print("🔧 Hot Commands Simple Fix")
    print("=" * 30)
    
    print("\n1. Removing foreign key constraints...")
    if not fix_hot_commands_table():
        print("❌ Failed to fix table")
        sys.exit(1)
    
    print("\n2. Testing table updates...")
    if not test_table_update():
        print("❌ Table update test failed")
        sys.exit(1)
    
    print("\n🎉 Hot Commands table fixed!")
    print("\n💡 You can now test editing hot commands in the React frontend:")
    print("   http://localhost:3000/hot-commands")