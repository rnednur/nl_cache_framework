#!/usr/bin/env python3
"""
Migration script to add execution_config to existing API tools.

This script processes existing API tools that don't have execution_config
and attempts to generate it from their template data.
"""

import json
import sys
import os
import argparse
from typing import Dict, Any, Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from thinkforge.models import Text2SQLCache
from sqlalchemy.orm import Session


def extract_execution_config_from_template(template: str) -> Optional[Dict[str, Any]]:
    """
    Extract execution configuration from an API template.
    
    Args:
        template: JSON string containing API template
    
    Returns:
        Dictionary with execution config or None if extraction fails
    """
    try:
        template_data = json.loads(template)
        
        # Extract basic info
        method = template_data.get('method', 'GET')
        path = template_data.get('path', '')
        
        if not path:
            return None
        
        # Try to infer base URL from path if it's a full URL
        if path.startswith('http'):
            # Full URL provided
            base_url = '/'.join(path.split('/')[:-1])  # Remove last path segment
            full_endpoint = path
        else:
            # Relative path - we'll need to set a placeholder base URL
            base_url = "https://api.example.com"  # Placeholder
            full_endpoint = f"{base_url}{path}" if not path.startswith('/') else f"{base_url}{path}"
        
        execution_config = {
            'base_url': base_url,
            'full_endpoint': full_endpoint,
            'method': method.upper(),
            'timeout': 30,
            'headers': {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        }
        
        return execution_config
        
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing template: {e}")
        return None


def migrate_api_tools(db: Session, dry_run: bool = True) -> None:
    """
    Migrate existing API tools to add execution_config.
    
    Args:
        db: Database session
        dry_run: If True, only print what would be done without making changes
    """
    print("Starting migration of API tools...")
    
    # Find all API tools without execution_config
    api_tools = db.query(Text2SQLCache).filter(
        Text2SQLCache.template_type == 'api',
        Text2SQLCache.execution_config.is_(None)
    ).all()
    
    print(f"Found {len(api_tools)} API tools without execution_config")
    
    updated_count = 0
    failed_count = 0
    
    for tool in api_tools:
        print(f"\nProcessing tool ID {tool.id}: {tool.nl_query[:100]}...")
        
        # Extract execution config from template
        execution_config = extract_execution_config_from_template(tool.template)
        
        if execution_config:
            print(f"  Generated execution_config:")
            print(f"    Method: {execution_config['method']}")
            print(f"    Full Endpoint: {execution_config['full_endpoint']}")
            print(f"    Base URL: {execution_config['base_url']}")
            
            if not dry_run:
                try:
                    tool.execution_config = execution_config
                    db.commit()
                    updated_count += 1
                    print(f"  ✅ Updated tool {tool.id}")
                except Exception as e:
                    print(f"  ❌ Failed to update tool {tool.id}: {e}")
                    db.rollback()
                    failed_count += 1
            else:
                print(f"  🔍 Would update tool {tool.id} (dry run)")
                updated_count += 1
        else:
            print(f"  ⚠️ Could not generate execution_config for tool {tool.id}")
            failed_count += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"  Total tools processed: {len(api_tools)}")
    print(f"  Successfully {'would be updated' if dry_run else 'updated'}: {updated_count}")
    print(f"  Failed: {failed_count}")
    
    if dry_run:
        print(f"\n🚨 This was a DRY RUN. Use --apply to actually make changes.")


def migrate_single_tool(db: Session, tool_id: int, dry_run: bool = True) -> None:
    """
    Migrate a single tool by ID.
    
    Args:
        db: Database session
        tool_id: ID of the tool to migrate
        dry_run: If True, only print what would be done
    """
    tool = db.query(Text2SQLCache).filter(Text2SQLCache.id == tool_id).first()
    
    if not tool:
        print(f"❌ Tool with ID {tool_id} not found")
        return
    
    if tool.template_type != 'api':
        print(f"❌ Tool {tool_id} is not an API tool (type: {tool.template_type})")
        return
    
    if tool.execution_config:
        print(f"⚠️ Tool {tool_id} already has execution_config")
        return
    
    print(f"Processing tool {tool_id}: {tool.nl_query}")
    
    execution_config = extract_execution_config_from_template(tool.template)
    
    if execution_config:
        print(f"Generated execution_config:")
        print(json.dumps(execution_config, indent=2))
        
        if not dry_run:
            try:
                tool.execution_config = execution_config
                db.commit()
                print(f"✅ Successfully updated tool {tool_id}")
            except Exception as e:
                print(f"❌ Failed to update tool {tool_id}: {e}")
                db.rollback()
        else:
            print(f"🔍 Would update tool {tool_id} (dry run)")
    else:
        print(f"❌ Could not generate execution_config for tool {tool_id}")


def main():
    parser = argparse.ArgumentParser(description='Migrate API tools to add execution_config')
    parser.add_argument('--apply', action='store_true', help='Actually apply changes (default is dry run)')
    parser.add_argument('--tool-id', type=int, help='Migrate specific tool by ID')
    
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    else:
        print("🚨 APPLY MODE - Changes will be made to the database")
    
    try:
        db = SessionLocal()
        try:
            if args.tool_id:
                migrate_single_tool(db, args.tool_id, dry_run)
            else:
                migrate_api_tools(db, dry_run)
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 