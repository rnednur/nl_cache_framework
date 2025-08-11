#!/usr/bin/env python
"""
Test script for Swagger URL upload functionality

Usage:
    python test_swagger_upload.py [swagger_url]

Example:
    python test_swagger_upload.py https://petstore.swagger.io/v2/swagger.json
"""

import sys
import requests
import json
import logging
import time
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("swagger_test.log")
    ]
)

logger = logging.getLogger("swagger_test")

# Default Swagger URL if none is provided
DEFAULT_SWAGGER_URL = "https://petstore.swagger.io/v2/swagger.json"

def test_swagger_fetch(swagger_url):
    """Test fetching Swagger JSON from the provided URL."""
    logger.info(f"Testing fetch from Swagger URL: {swagger_url}")
    
    try:
        start_time = time.time()
        logger.info(f"Sending GET request with 10-second timeout")
        
        response = requests.get(swagger_url, timeout=10)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Request completed in {elapsed_time:.2f} seconds")
        
        if response.status_code != 200:
            logger.error(f"Failed with status code: {response.status_code}")
            return False, f"HTTP error: {response.status_code}"
        
        try:
            # Try to parse JSON
            swagger_data = response.json()
            logger.info(f"Successfully parsed JSON. Content size: {len(response.text)} bytes")
            
            # Check if it's valid Swagger/OpenAPI
            if 'swagger' not in swagger_data and 'openapi' not in swagger_data:
                logger.warning("Response doesn't appear to be a valid Swagger/OpenAPI document")
                return False, "Response doesn't appear to be a valid Swagger/OpenAPI document"
            
            # Count paths and methods
            paths = swagger_data.get('paths', {})
            path_count = len(paths)
            
            method_counts = {'get': 0, 'post': 0, 'put': 0, 'delete': 0, 'other': 0}
            for path, methods in paths.items():
                for method in methods:
                    normalized_method = method.lower()
                    if normalized_method in method_counts:
                        method_counts[normalized_method] += 1
                    else:
                        method_counts['other'] += 1
            
            logger.info(f"Found {path_count} paths with method counts: {method_counts}")
            return True, swagger_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            return False, f"JSON parse error: {str(e)}"
            
    except requests.exceptions.Timeout:
        logger.error("Request timed out after 10 seconds")
        return False, "Request timed out"
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return False, f"Connection error: {str(e)}"
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def test_server_upload(swagger_url, catalog_type=None, catalog_subtype=None, catalog_name=None):
    """Test uploading Swagger URL to the local server with optional catalog parameters."""
    logger.info(f"Testing upload to server with Swagger URL: {swagger_url}")
    
    try:
        server_url = "http://localhost:8000/v1/upload/swagger"
        
        start_time = time.time()
        logger.info(f"Sending POST request to {server_url} with 30-second timeout")
        
        # Create request body with the swagger URL
        request_body = {"swagger_url": swagger_url}
        
        # Add catalog parameters if provided
        if catalog_type:
            request_body["catalog_type"] = catalog_type
            logger.info(f"Using custom catalog_type: {catalog_type}")
        if catalog_subtype:
            request_body["catalog_subtype"] = catalog_subtype
            logger.info(f"Using custom catalog_subtype: {catalog_subtype}")
        if catalog_name:
            request_body["catalog_name"] = catalog_name
            logger.info(f"Using custom catalog_name: {catalog_name}")
        
        response = requests.post(
            server_url, 
            json=request_body,
            timeout=30
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Request completed in {elapsed_time:.2f} seconds")
        
        if response.status_code != 200:
            logger.error(f"Server returned error: {response.status_code}")
            try:
                error_data = response.json()
                logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                logger.error(f"Response text: {response.text[:500]}")
            return False, f"Server error: {response.status_code}"
        
        # Parse response
        result = response.json()
        logger.info(f"Server processed {result.get('processed', 0)} entries with {result.get('failed', 0)} failures")
        return True, result
        
    except requests.exceptions.Timeout:
        logger.error("Server request timed out")
        return False, "Server request timed out"
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to server: {str(e)}")
        return False, f"Connection error to server: {str(e)}"
        
    except Exception as e:
        logger.error(f"Unexpected error with server request: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def main():
    # Get Swagger URL from command-line argument or use default
    if len(sys.argv) > 1:
        swagger_url = sys.argv[1]
    else:
        swagger_url = DEFAULT_SWAGGER_URL
        logger.info(f"No URL provided, using default: {swagger_url}")
    
    # Set optional catalog parameters for testing
    catalog_type = os.environ.get("CATALOG_TYPE")
    catalog_subtype = os.environ.get("CATALOG_SUBTYPE")
    catalog_name = os.environ.get("CATALOG_NAME")
    
    # Test direct fetch
    logger.info("===== Testing direct fetch of Swagger JSON =====")
    fetch_success, fetch_result = test_swagger_fetch(swagger_url)
    
    if not fetch_success:
        logger.error(f"Direct fetch failed: {fetch_result}")
        logger.error("Aborting server test since direct fetch failed")
        sys.exit(1)
    
    # Test server upload if direct fetch was successful
    logger.info("\n===== Testing server upload of Swagger URL =====")
    upload_success, upload_result = test_server_upload(
        swagger_url, 
        catalog_type=catalog_type,
        catalog_subtype=catalog_subtype,
        catalog_name=catalog_name
    )
    
    if upload_success:
        logger.info("Server upload test completed successfully")
        logger.info(f"Result: {json.dumps(upload_result, indent=2)}")
    else:
        logger.error(f"Server upload failed: {upload_result}")
        sys.exit(1)
    
    logger.info("All tests completed successfully")

if __name__ == "__main__":
    main() 