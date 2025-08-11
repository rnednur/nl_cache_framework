#!/usr/bin/env python3
"""
Demo Data Export Script for ThinkForge

This script exports all database data to JSON files that can be easily imported
into a new ThinkForge installation for demo purposes.
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from thinkforge.models import Text2SQLCache, UsageLog, CacheAuditLog
    from database import SessionLocal, engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Make sure you're running this from the project root and have installed dependencies")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def export_cache_entries(session, output_dir):
    """Export all cache entries to JSON."""
    logger.info("Exporting cache entries...")
    
    cache_entries = session.query(Text2SQLCache).all()
    exported_entries = []
    
    for entry in cache_entries:
        entry_data = {
            'id': entry.id,
            'nl_query': entry.nl_query,
            'template': entry.template,
            'template_type': entry.template_type,
            'is_template': entry.is_template,
            'reasoning_trace': entry.reasoning_trace,
            'entity_replacements': entry.entity_replacements,
            'tags': entry.tags,
            'catalog_type': entry.catalog_type,
            'catalog_subtype': entry.catalog_subtype,
            'catalog_name': entry.catalog_name,
            'status': entry.status,
            'usage_count': entry.usage_count,
            'created_at': serialize_datetime(entry.created_at),
            'updated_at': serialize_datetime(entry.updated_at),
            'embedding': None,  # Skip embeddings for demo data
            
            # Tool-specific fields
            'tool_capabilities': entry.tool_capabilities,
            'tool_dependencies': entry.tool_dependencies,
            'execution_config': entry.execution_config,
            'health_status': entry.health_status,
            'last_tested': serialize_datetime(entry.last_tested) if entry.last_tested else None,
            
            # Recipe-specific fields
            'recipe_steps': entry.recipe_steps,
            'required_tools': entry.required_tools,
            'execution_time_estimate': entry.execution_time_estimate,
            'complexity_level': entry.complexity_level,
            'success_rate': entry.success_rate,
            'last_executed': serialize_datetime(entry.last_executed) if entry.last_executed else None,
            'execution_count': entry.execution_count
        }
        exported_entries.append(entry_data)
    
    # Write to JSON file
    output_file = output_dir / 'cache_entries.json'
    with open(output_file, 'w') as f:
        json.dump(exported_entries, f, indent=2, default=serialize_datetime)
    
    logger.info(f"Exported {len(exported_entries)} cache entries to {output_file}")
    return len(exported_entries)

def export_usage_logs(session, output_dir, limit=1000):
    """Export recent usage logs to JSON."""
    logger.info(f"Exporting recent {limit} usage logs...")
    
    usage_logs = session.query(UsageLog).order_by(UsageLog.timestamp.desc()).limit(limit).all()
    exported_logs = []
    
    for log in usage_logs:
        log_data = {
            'id': log.id,
            'cache_entry_id': log.cache_entry_id,
            'timestamp': serialize_datetime(log.timestamp),
            'prompt': log.prompt,
            'success_status': log.success_status,
            'similarity_score': log.similarity_score,
            'error_message': log.error_message,
            'catalog_type': log.catalog_type,
            'catalog_subtype': log.catalog_subtype,
            'catalog_name': log.catalog_name,
            'llm_used': log.llm_used,
            'response': log.response,
            'considered_entries': log.considered_entries,
            'is_confident': log.is_confident
        }
        exported_logs.append(log_data)
    
    # Write to JSON file
    output_file = output_dir / 'usage_logs.json'
    with open(output_file, 'w') as f:
        json.dump(exported_logs, f, indent=2, default=serialize_datetime)
    
    logger.info(f"Exported {len(exported_logs)} usage logs to {output_file}")
    return len(exported_logs)

def create_demo_metadata(output_dir, cache_count, log_count):
    """Create metadata file for the demo export."""
    metadata = {
        'export_timestamp': datetime.now().isoformat(),
        'export_version': '1.0',
        'thinkforge_version': 'demo',
        'database_schema_version': '1.0',
        'exported_data': {
            'cache_entries': cache_count,
            'usage_logs': log_count
        },
        'description': 'ThinkForge demo data export containing cache entries, tools, recipes, and usage logs',
        'import_instructions': 'Use import_demo_data.py to import this data into a new ThinkForge installation'
    }
    
    output_file = output_dir / 'demo_metadata.json'
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Created demo metadata file: {output_file}")

def main():
    """Main export function."""
    # Create output directory
    output_dir = Path('demo_data_export')
    output_dir.mkdir(exist_ok=True)
    
    logger.info(f"Starting ThinkForge demo data export to {output_dir}")
    
    # Create database session
    session = SessionLocal()
    
    try:
        # Export cache entries
        cache_count = export_cache_entries(session, output_dir)
        
        # Export usage logs
        log_count = export_usage_logs(session, output_dir)
        
        # Create metadata
        create_demo_metadata(output_dir, cache_count, log_count)
        
        # Create README for the export
        readme_content = f"""# ThinkForge Demo Data Export

This directory contains exported data from a ThinkForge installation for demo purposes.

## Contents

- `cache_entries.json`: {cache_count} cache entries including tools, recipes, and templates
- `usage_logs.json`: {log_count} recent usage logs
- `demo_metadata.json`: Export metadata and version information

## Import Instructions

To import this data into a new ThinkForge installation:

1. Set up a new ThinkForge installation
2. Run the import script:
   ```bash
   python scripts/import_demo_data.py demo_data_export/
   ```

## Export Details

- Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Total Cache Entries: {cache_count}
- Total Usage Logs: {log_count}

This export excludes vector embeddings (they will be regenerated on import) and 
sensitive configuration data for security purposes.
"""
        
        readme_file = output_dir / 'README.md'
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        logger.info("Demo data export completed successfully!")
        logger.info(f"Export location: {output_dir.absolute()}")
        logger.info(f"Archive this directory to share the demo data")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()