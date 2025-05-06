import os
import csv
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API base URL from environment or default to localhost
API_BASE_URL = os.getenv('NEXT_PUBLIC_API_BASE_URL', 'http://localhost:8000')


def load_csv_to_cache(csv_file_path: str):
    """
    Read a CSV file with text_query and sql_command columns and send them to the backend API
    for insertion into the Text2SQLCache table.
    """
    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return

    inserted_count = 0
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            try:
                payload = {
                    'nl_query': row['text_query'],
                    'template': row['sql_command'],
                    'template_type': 'SQL',
                    'status': 'ACTIVE',
                    'is_template': False
                }
                response = requests.post(f"{API_BASE_URL}/v1/cache_entries", json=payload)
                if response.status_code == 201:
                    inserted_count += 1
                    logger.info(f"Successfully inserted entry for query: {row['text_query']}")
                else:
                    logger.error(f"Failed to insert row {row}: {response.text}")
            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
        logger.info(f"Successfully inserted {inserted_count} entries into the cache via API.")


if __name__ == "__main__":
    csv_file_path = input("Enter the path to your CSV file: ")
    load_csv_to_cache(csv_file_path) 