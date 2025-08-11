#!/usr/bin/env python3
"""
Demo Data Import Script for ThinkForge

This script imports demo data from JSON files exported by export_demo_data.py
into a ThinkForge installation.
"""

import json
import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from thinkforge.models import Text2SQLCache, UsageLog, Base
    from thinkforge.controller import Text2SQLController
    from database import SessionLocal, engine
    from sqlalchemy.exc import IntegrityError
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Make sure you're running this from the project root and have installed dependencies")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_datetime(date_string):
    """Parse ISO datetime string."""
    if date_string:
        try:
            return datetime.fromisoformat(date_string)
        except:
            return None
    return None

def import_cache_entries(session, import_dir, regenerate_embeddings=True):
    """Import cache entries from JSON file."""
    logger.info("Importing cache entries...")
    
    cache_file = import_dir / 'cache_entries.json'
    if not cache_file.exists():
        logger.warning(f"Cache entries file not found: {cache_file}")
        return 0
    
    with open(cache_file, 'r') as f:
        entries_data = json.load(f)
    
    imported_count = 0
    skipped_count = 0
    controller = None
    
    if regenerate_embeddings:
        controller = Text2SQLController(db_session=session)
        logger.info("Will regenerate embeddings for imported entries")
    
    for entry_data in entries_data:
        try:
            # Check if entry already exists (by nl_query and template_type)
            existing = session.query(Text2SQLCache).filter_by(
                nl_query=entry_data['nl_query'],
                template_type=entry_data['template_type']
            ).first()
            
            if existing:
                logger.debug(f"Skipping existing entry: {entry_data['nl_query'][:50]}...")
                skipped_count += 1
                continue
            
            # Create new cache entry
            cache_entry = Text2SQLCache(
                nl_query=entry_data['nl_query'],
                template=entry_data['template'],
                template_type=entry_data['template_type'],
                is_template=entry_data['is_template'],
                reasoning_trace=entry_data.get('reasoning_trace'),
                entity_replacements=entry_data.get('entity_replacements'),
                tags=entry_data.get('tags'),
                catalog_type=entry_data.get('catalog_type'),
                catalog_subtype=entry_data.get('catalog_subtype'),
                catalog_name=entry_data.get('catalog_name'),
                status=entry_data.get('status', 'active'),
                usage_count=entry_data.get('usage_count', 0),
                created_at=parse_datetime(entry_data.get('created_at')) or datetime.now(),
                updated_at=parse_datetime(entry_data.get('updated_at')) or datetime.now(),
                
                # Tool-specific fields
                tool_capabilities=entry_data.get('tool_capabilities'),
                tool_dependencies=entry_data.get('tool_dependencies'),
                execution_config=entry_data.get('execution_config'),
                health_status=entry_data.get('health_status'),
                last_tested=parse_datetime(entry_data.get('last_tested')),
                
                # Recipe-specific fields
                recipe_steps=entry_data.get('recipe_steps'),
                required_tools=entry_data.get('required_tools'),
                execution_time_estimate=entry_data.get('execution_time_estimate'),
                complexity_level=entry_data.get('complexity_level'),
                success_rate=entry_data.get('success_rate'),
                last_executed=parse_datetime(entry_data.get('last_executed')),
                execution_count=entry_data.get('execution_count', 0)
            )
            
            session.add(cache_entry)
            session.flush()  # Get the ID
            
            # Regenerate embedding if requested
            if regenerate_embeddings and controller:
                try:
                    embedding = controller._get_embedding(entry_data['nl_query'])
                    if embedding is not None:
                        cache_entry.embedding = embedding.tolist()
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for entry {cache_entry.id}: {e}")
            
            imported_count += 1
            
            if imported_count % 50 == 0:
                logger.info(f"Imported {imported_count} cache entries...")
                session.commit()
        
        except Exception as e:
            logger.error(f"Failed to import cache entry: {e}")
            session.rollback()
            continue
    
    session.commit()
    logger.info(f"Cache entries import completed: {imported_count} imported, {skipped_count} skipped")
    return imported_count

def import_usage_logs(session, import_dir):
    """Import usage logs from JSON file."""
    logger.info("Importing usage logs...")
    
    logs_file = import_dir / 'usage_logs.json'
    if not logs_file.exists():
        logger.warning(f"Usage logs file not found: {logs_file}")
        return 0
    
    with open(logs_file, 'r') as f:
        logs_data = json.load(f)
    
    imported_count = 0
    skipped_count = 0
    
    for log_data in logs_data:
        try:
            # Check if log already exists (by timestamp and prompt)
            existing = session.query(UsageLog).filter_by(
                timestamp=parse_datetime(log_data['timestamp']),
                prompt=log_data.get('prompt')
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # Create new usage log
            usage_log = UsageLog(
                cache_entry_id=log_data.get('cache_entry_id'),
                timestamp=parse_datetime(log_data['timestamp']) or datetime.now(),
                prompt=log_data.get('prompt'),
                success_status=log_data.get('success_status', False),
                similarity_score=log_data.get('similarity_score', 0.0),
                error_message=log_data.get('error_message'),
                catalog_type=log_data.get('catalog_type'),
                catalog_subtype=log_data.get('catalog_subtype'),
                catalog_name=log_data.get('catalog_name'),
                llm_used=log_data.get('llm_used', False),
                response=log_data.get('response'),
                considered_entries=log_data.get('considered_entries'),
                is_confident=log_data.get('is_confident')
            )
            
            session.add(usage_log)
            imported_count += 1
            
            if imported_count % 100 == 0:
                logger.info(f"Imported {imported_count} usage logs...")
                session.commit()
        
        except Exception as e:
            logger.error(f"Failed to import usage log: {e}")
            session.rollback()
            continue
    
    session.commit()
    logger.info(f"Usage logs import completed: {imported_count} imported, {skipped_count} skipped")
    return imported_count

def verify_metadata(import_dir):
    """Verify the import directory contains valid demo data."""
    metadata_file = import_dir / 'demo_metadata.json'
    if not metadata_file.exists():
        logger.error(f"Demo metadata file not found: {metadata_file}")
        return False
    
    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"Import data metadata:")
        logger.info(f"  Export Version: {metadata.get('export_version')}")
        logger.info(f"  Export Date: {metadata.get('export_timestamp')}")
        logger.info(f"  Cache Entries: {metadata.get('exported_data', {}).get('cache_entries', 0)}")
        logger.info(f"  Usage Logs: {metadata.get('exported_data', {}).get('usage_logs', 0)}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to read metadata: {e}")
        return False

def main():
    """Main import function."""
    parser = argparse.ArgumentParser(description='Import ThinkForge demo data')
    parser.add_argument('import_dir', help='Directory containing exported demo data')
    parser.add_argument('--no-embeddings', action='store_true', 
                       help='Skip regenerating embeddings (faster but less accurate)')
    parser.add_argument('--create-tables', action='store_true',
                       help='Create database tables before import')
    
    args = parser.parse_args()
    
    import_dir = Path(args.import_dir)
    if not import_dir.exists():
        logger.error(f"Import directory does not exist: {import_dir}")
        sys.exit(1)
    
    # Verify metadata
    if not verify_metadata(import_dir):
        sys.exit(1)
    
    logger.info(f"Starting ThinkForge demo data import from {import_dir}")
    
    # Create tables if requested
    if args.create_tables:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
    
    # Create database session
    session = SessionLocal()
    
    try:
        # Import cache entries
        cache_count = import_cache_entries(
            session, import_dir, 
            regenerate_embeddings=not args.no_embeddings
        )
        
        # Import usage logs
        log_count = import_usage_logs(session, import_dir)
        
        logger.info("Demo data import completed successfully!")
        logger.info(f"Imported: {cache_count} cache entries, {log_count} usage logs")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()