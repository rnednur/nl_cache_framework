#!/usr/bin/env python
"""
Embedding Repair Script

This script updates all cache entries to ensure they have valid vector embeddings.
It uses a specified sentence transformer model to generate embeddings
for all entries in the Text2SQLCache table.

Usage:
    python fix_embeddings.py [--model MODEL_NAME] [--dry-run]

Options:
    --model MODEL_NAME  Specify the sentence transformer model to use
                        Default: all-MiniLM-L6-v2 (smaller and more reliable than the default)
    --dry-run          Test run without making changes to the database
"""

import argparse
import logging
import os
import sys
import numpy as np
from tqdm import tqdm
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the database and framework components
try:
    from database import get_db, engine, SessionLocal
    from nl_cache_framework import Text2SQLSimilarity
    from nl_cache_framework.models import Text2SQLCache
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure the application is properly installed")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("embedding_repair.log"),
    ]
)
logger = logging.getLogger("embedding_repair")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Fix embeddings for cache entries")
    parser.add_argument(
        "--model", 
        type=str, 
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model to use (default: all-MiniLM-L6-v2)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without making changes"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Log the start with model information
    logger.info(f"Starting embedding repair with model: {args.model}")
    logger.info(f"Dry run: {args.dry_run}")
    
    try:
        # Initialize the similarity utility with the specified model
        logger.info(f"Loading sentence transformer model: {args.model}")
        similarity_util = Text2SQLSimilarity(model_name=args.model)
        
        # Get a database session
        with SessionLocal() as db:
            # Count total entries
            total_entries = db.query(func.count(Text2SQLCache.id)).scalar()
            logger.info(f"Found {total_entries} cache entries in the database")
            
            # Process entries in batches to avoid memory issues
            batch_size = 100
            num_batches = (total_entries + batch_size - 1) // batch_size
            
            # Track statistics
            processed = 0
            updated = 0
            failed = 0
            
            # Process each batch
            for batch_num in range(num_batches):
                offset = batch_num * batch_size
                logger.info(f"Processing batch {batch_num+1}/{num_batches} (offset: {offset})")
                
                # Get a batch of entries
                entries = db.query(Text2SQLCache).order_by(Text2SQLCache.id).offset(offset).limit(batch_size).all()
                
                # Process each entry in the batch
                for entry in tqdm(entries, desc=f"Batch {batch_num+1}"):
                    processed += 1
                    
                    # Skip entries with existing valid embeddings (optional)
                    # if entry.vector_embedding is not None and len(entry.vector_embedding) > 0:
                    #     logger.debug(f"Skipping entry {entry.id} with existing embedding")
                    #     continue
                    
                    try:
                        # Get the query text
                        query_text = entry.nl_query
                        if not query_text or not query_text.strip():
                            logger.warning(f"Entry {entry.id} has empty query text, skipping")
                            failed += 1
                            continue
                        
                        # Generate new embedding
                        embedding = similarity_util.get_embedding([query_text])
                        
                        if embedding is None or embedding.size == 0:
                            logger.warning(f"Failed to generate embedding for entry {entry.id}")
                            failed += 1
                            continue
                            
                        # Update the entry with the new embedding (only in non-dry-run mode)
                        if not args.dry_run:
                            entry.embedding = embedding[0]  # Use the property setter
                            db.add(entry)
                            
                        updated += 1
                        
                        # Log every 100 entries
                        if processed % 100 == 0:
                            logger.info(f"Processed {processed}/{total_entries} entries")
                            
                    except Exception as e:
                        logger.error(f"Error processing entry {entry.id}: {e}")
                        failed += 1
                
                # Commit the batch (only in non-dry-run mode)
                if not args.dry_run:
                    db.commit()
                    logger.info(f"Committed batch {batch_num+1}")
                else:
                    logger.info(f"Dry run - no changes committed for batch {batch_num+1}")
            
            # Log final statistics
            logger.info("Embedding repair complete")
            logger.info(f"Total entries: {total_entries}")
            logger.info(f"Processed: {processed}")
            logger.info(f"Updated: {updated}")
            logger.info(f"Failed: {failed}")
            
            if args.dry_run:
                logger.info("This was a dry run. No changes were made to the database.")
                logger.info("To apply changes, run without the --dry-run flag.")
                
    except Exception as e:
        logger.error(f"Error during embedding repair: {e}", exc_info=True)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 