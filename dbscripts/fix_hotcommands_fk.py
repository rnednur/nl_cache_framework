#!/usr/bin/env python3
"""
Fix Hot Commands foreign key constraint issue
Removes foreign key constraints that reference non-existent tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, inspect
from thinkforge.database import get_engine, get_db_url
from thinkforge.models import DB_SCHEMA

def fix_foreign_key_constraints():
    """Remove problematic foreign key constraints from hot_commands table."""
    
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            # Check if hot_commands table exists
            inspector = inspect(conn)
            tables = inspector.get_table_names(schema=DB_SCHEMA if DB_SCHEMA != "public" else None)
            
            if 'hot_commands' not in tables:
                print("✅ hot_commands table does not exist yet - no foreign keys to fix")
                return True
            
            print(f"🔍 Checking hot_commands table in schema: {DB_SCHEMA}")
            
            # Get foreign key constraints
            fks = inspector.get_foreign_keys('hot_commands', schema=DB_SCHEMA if DB_SCHEMA != "public" else None)
            
            if not fks:
                print("✅ No foreign key constraints found on hot_commands table")
                return True
            
            print(f"Found {len(fks)} foreign key constraints:")
            for fk in fks:
                print(f"  - {fk['name']}: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            
            # Drop foreign key constraints that reference cache tables
            cache_table_patterns = ['text2sql_cache', 'cache_entries', 'cache_entry']
            
            for fk in fks:
                referred_table = fk['referred_table']
                constraint_name = fk['name']
                
                # Check if this FK references a cache table
                if any(pattern in referred_table.lower() for pattern in cache_table_patterns):
                    print(f"🔧 Dropping problematic foreign key: {constraint_name}")
                    
                    # Drop the foreign key constraint
                    schema_prefix = f"{DB_SCHEMA}." if DB_SCHEMA != "public" else ""
                    drop_sql = f"ALTER TABLE {schema_prefix}hot_commands DROP CONSTRAINT IF EXISTS {constraint_name}"
                    
                    try:
                        conn.execute(text(drop_sql))
                        conn.commit()
                        print(f"✅ Successfully dropped foreign key: {constraint_name}")
                    except Exception as e:
                        print(f"❌ Error dropping foreign key {constraint_name}: {e}")
                        return False
            
            print("✅ All problematic foreign key constraints removed")
            return True
            
    except Exception as e:
        print(f"❌ Error checking/fixing foreign keys: {e}")
        return False

def verify_table_structure():
    """Verify that the hot_commands table structure is correct."""
    
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            
            # Check columns
            columns = inspector.get_columns('hot_commands', schema=DB_SCHEMA if DB_SCHEMA != "public" else None)
            
            cache_entry_col = None
            for col in columns:
                if col['name'] == 'cache_entry_id':
                    cache_entry_col = col
                    break
            
            if cache_entry_col:
                print(f"✅ cache_entry_id column exists: {cache_entry_col['type']}, nullable: {cache_entry_col['nullable']}")
            else:
                print("❌ cache_entry_id column not found")
                return False
            
            # Check remaining foreign keys
            fks = inspector.get_foreign_keys('hot_commands', schema=DB_SCHEMA if DB_SCHEMA != "public" else None)
            print(f"Remaining foreign keys: {len(fks)}")
            for fk in fks:
                print(f"  - {fk['name']}: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error verifying table structure: {e}")
        return False

def test_hot_command_update():
    """Test updating a hot command to see if the foreign key issue is resolved."""
    
    from sqlalchemy.orm import sessionmaker
    from thinkforge.hotcommands_models import HotCommand
    
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        with SessionLocal() as db:
            # Find a hot command to test
            command = db.query(HotCommand).first()
            
            if not command:
                print("ℹ️  No hot commands found to test")
                return True
            
            print(f"🧪 Testing update on command: {command.command_name}")
            
            # Try to update the command
            original_description = command.description
            command.description = f"Test update - {original_description}"
            
            db.commit()
            db.refresh(command)
            
            # Restore original description
            command.description = original_description
            db.commit()
            
            print("✅ Hot command update test successful")
            return True
            
    except Exception as e:
        print(f"❌ Hot command update test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Hot Commands Foreign Key Fix")
    print("=" * 50)
    
    print("\n1. Checking and fixing foreign key constraints...")
    if not fix_foreign_key_constraints():
        print("❌ Failed to fix foreign key constraints")
        sys.exit(1)
    
    print("\n2. Verifying table structure...")
    if not verify_table_structure():
        print("❌ Table structure verification failed")
        sys.exit(1)
    
    print("\n3. Testing hot command update...")
    if not test_hot_command_update():
        print("❌ Hot command update test failed")
        sys.exit(1)
    
    print("\n🎉 All checks passed! Hot Commands foreign key issue should be resolved.")
    print("\n💡 You can now test editing hot commands in the frontend.")