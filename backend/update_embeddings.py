import os
import sys
import logging
from sqlalchemy.orm import Session

# Add project root to path to allow importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import necessary components
from backend.database import SessionLocal
from nl_cache_framework import Text2SQLCache, Text2SQLSimilarity

DEFAULT_MODEL_NAME = os.environ.get("DEFAULT_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2")

def update_embeddings():
    """Update embeddings for all existing cache entries in the database."""
    db_session = SessionLocal()
    try:
        # Initialize similarity utility
        similarity_util = Text2SQLSimilarity(model_name=DEFAULT_MODEL_NAME)
        logger.info("Initialized similarity utility for embedding updates")

        # Fetch all cache entries without embeddings or with null embeddings
        entries_to_update = db_session.query(Text2SQLCache).filter(
            (Text2SQLCache.embedding == None) | (Text2SQLCache.embedding == [])
        ).all()
        total_entries = len(entries_to_update)
        logger.info(f"Found {total_entries} cache entries needing embedding updates")

        if total_entries == 0:
            logger.info("No entries need updating. Exiting.")
            return

        # Process in batches to avoid memory issues
        batch_size = 100
        for i in range(0, total_entries, batch_size):
            batch = entries_to_update[i:i + batch_size]
            batch_texts = [entry.nl_query for entry in batch]
            logger.info(f"Processing batch {i//batch_size + 1} of {total_entries//batch_size + 1}")

            # Generate embeddings for the batch
            embeddings = similarity_util.get_embedding(batch_texts)
            if embeddings is None or len(embeddings) != len(batch):
                logger.error(f"Failed to generate embeddings for batch starting at index {i}")
                continue

            # Update each entry with its embedding
            for entry, embedding in zip(batch, embeddings):
                entry.embedding = embedding
                logger.debug(f"Updated embedding for entry ID {entry.id}")

            # Commit the batch updates
            db_session.commit()
            logger.info(f"Committed updates for batch {i//batch_size + 1}")

        logger.info("Completed updating embeddings for all cache entries")
    except Exception as e:
        logger.error(f"Error updating embeddings: {str(e)}", exc_info=True)
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    update_embeddings() 