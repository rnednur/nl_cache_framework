"""
API Integration Test Script

This script demonstrates using the NL Cache Framework with API templates
by making actual API calls. It uses the httpbin.org service for testing.

Usage:
    python -m tests.api_integration_test
"""

import requests
import time
import uuid
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nl_cache_framework import Text2SQLController, TemplateType
from nl_cache_framework.models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database setup - using SQLite in-memory for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def main():
    """Run the API integration test"""
    logger.info("Starting API integration test")

    # Create a session
    db_session = SessionLocal()

    try:
        # Initialize controller
        controller = Text2SQLController(db_session=db_session)

        # Step 1: Add an API template for httpbin
        logger.info("Adding API template...")
        nl_query = "Get data from httpbin with test parameter :param"
        template = """
        {
            "method": "GET",
            "url": "https://httpbin.org/get",
            "params": {
                "test_param": ":param"
            },
            "headers": {
                "Accept": "application/json"
            }
        }
        """
        entity_replacements = {
            "param_placeholder": {"placeholder": ":param", "type": "string"}
        }

        result = controller.add_query(
            nl_query=nl_query,
            template=template,
            template_type=TemplateType.API,
            entity_replacements=entity_replacements,
            is_template=True,
            tags=["api", "httpbin", "test"],
        )

        template_id = result["id"]
        logger.info(f"Added API template with ID: {template_id}")

        # Step 2: Search for the template
        logger.info("Searching for API template...")
        search_results = controller.search_query(
            nl_query="Get data from httpbin with parameter",
            template_type=TemplateType.API,
            search_method="string",
            similarity_threshold=0.7,
        )

        if search_results:
            logger.info(f"Found {len(search_results)} matching templates")
            for i, result in enumerate(search_results):
                logger.info(
                    f"Match {i+1}: {result['nl_query']} (similarity: {result['similarity']:.2f})"
                )
        else:
            logger.error("No matching templates found")
            return

        # Step 3: Apply entity substitution
        logger.info("Applying entity substitution...")
        new_values = {"param_placeholder": "nl_cache_test_value"}

        substitution_result = controller.apply_entity_substitution(
            template_id=template_id, new_entity_values=new_values
        )

        # Step 4: Make the actual API call
        logger.info("Making API call with substituted template...")
        api_spec = json.loads(substitution_result["substituted_template"])

        logger.info(
            f"API Call: {api_spec['method']} {api_spec['url']} with params={api_spec['params']}"
        )

        # Execute the API call
        response = requests.request(
            method=api_spec["method"],
            url=api_spec["url"],
            params=api_spec["params"],
            headers=api_spec["headers"],
        )

        logger.info(f"API Response status: {response.status_code}")
        response_data = response.json()
        logger.info(f"API Response data: {json.dumps(response_data, indent=2)}")

        # Verify the response contains our parameter
        if response_data["args"]["test_param"] == "nl_cache_test_value":
            logger.info("✅ API call successful with correct parameters")
        else:
            logger.error(f"❌ API call parameter mismatch: {response_data['args']}")

        # Step 5: Get all API templates
        logger.info("Retrieving all API templates...")
        api_templates = controller.get_query_by_template_type(
            template_type=TemplateType.API
        )
        logger.info(f"Found {len(api_templates)} API templates")

        logger.info("API integration test completed successfully")

    except Exception as e:
        logger.exception(f"Error during API integration test: {str(e)}")
    finally:
        db_session.close()


if __name__ == "__main__":
    main()
