import os
import csv
import logging
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from nl_cache_framework.models import Text2SQLCache, TemplateType, Status

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def load_csv_to_cache(csv_file_path: str, db: Session):
    """
    Read a CSV file with text_query and sql_command columns and insert them into the Text2SQLCache table.
    """
    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return

    inserted_count = 0
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            try:
                cache_entry = Text2SQLCache(
                    nl_query=row['text_query'],
                    template=row['sql_command'],
                    template_type=TemplateType.SQL,
                    status=Status.ACTIVE,
                    is_template=False
                )
                db.add(cache_entry)
                inserted_count += 1
            except Exception as e:
                logger.error(f"Error inserting row {row}: {e}")
        db.commit()
        logger.info(f"Successfully inserted {inserted_count} entries into the cache.")


if __name__ == "__main__":
    csv_file_path = input("Enter the path to your CSV file: ")
    db_gen = get_db()
    db = next(db_gen)
    load_csv_to_cache(csv_file_path, db) 