import os
import csv
import logging
import requests
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API base URL from environment or default to localhost
API_BASE_URL = os.getenv('NEXT_PUBLIC_API_BASE_URL', 'http://localhost:8000')


def load_csv_to_cache(csv_file_path: str, template_type: str = 'sql'):
    """
    Read a CSV file and send rows to the backend API for insertion into the Text2SQLCache table.
    
    Args:
        csv_file_path: Path to the CSV file
        template_type: Type of template (sql, url, api, etc.)
        
    The CSV file should contain at least 'text_query' or 'nl_query' and 'sql_command' or 'template' columns.
    Any additional columns present in the CSV will be passed to the create endpoint if they match
    valid cache entry fields (e.g., catalog_type, catalog_subtype, catalog_name, reasoning_trace, tags).
    """
    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return

    # Column name mappings to handle different naming conventions
    field_mappings = {
        'text_query': 'nl_query',
        'sql_command': 'template',
        'sql_query': 'template',
        'query': 'nl_query',
        'command': 'template',
        'reason': 'reasoning_trace',
        'explanation': 'reasoning_trace',
        'type': 'template_type',
        'status': 'status'
    }
    
    # Fields that should be converted to boolean
    boolean_fields = ['is_template']
    
    # Fields that should be converted to lists
    list_fields = ['tags']
    
    inserted_count = 0
    failed_count = 0
    
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        # Validate that required columns exist
        required_columns_found = False
        header = csv_reader.fieldnames
        
        if not header:
            logger.error("CSV file has no headers")
            return
            
        logger.info(f"CSV headers: {header}")
        for source_col in ['text_query', 'nl_query']:
            for target_col in ['sql_command', 'template', 'sql_query']:
                if source_col in header and target_col in header:
                    required_columns_found = True
                    break
        
        if not required_columns_found:
            logger.error("CSV must contain at least a query column (text_query, nl_query) "
                         "and a template column (sql_command, template, sql_query)")
            return
        
        for row in csv_reader:
            try:
                # Initialize payload with default values
                payload = {
                    'template_type': template_type.lower(),
                    'status': 'active',
                    'is_template': False
                }
                
                # Process all fields from the CSV row
                for key, value in row.items():
                    # Skip empty values
                    if not value or value.strip() == '':
                        continue
                        
                    # Map the field name if necessary
                    field_name = field_mappings.get(key.lower(), key.lower())
                    
                    # Convert boolean fields
                    if field_name in boolean_fields:
                        payload[field_name] = value.lower() in ['true', 'yes', 'y', '1']
                    
                    # Convert list fields (comma-separated values)
                    elif field_name in list_fields:
                        payload[field_name] = [item.strip() for item in value.split(',') if item.strip()]
                    
                    # Use as-is for other fields
                    else:
                        payload[field_name] = value
                        
                # Ensure required fields are present
                if 'nl_query' not in payload:
                    if 'text_query' in row:
                        payload['nl_query'] = row['text_query']
                    else:
                        raise ValueError("No natural language query found in row")
                        
                if 'template' not in payload:
                    if 'sql_command' in row:
                        payload['template'] = row['sql_command']
                    elif 'sql_query' in row:
                        payload['template'] = row['sql_query']
                    else:
                        raise ValueError("No template found in row")
                
                logger.info(f"Inserting payload: {payload}")
                response = requests.post(f"{API_BASE_URL}/v1/cache", json=payload)
                
                if response.status_code in (200, 201):
                    inserted_count += 1
                    logger.info(f"Successfully inserted entry for query: {payload.get('nl_query')}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to insert row with status {response.status_code}: {response.text}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing row: {e}")
        
        logger.info(f"CSV import complete. Inserted: {inserted_count}, Failed: {failed_count}")
        
    return {"success": inserted_count, "failed": failed_count}


def generate_sample_csv_template(output_path: str = "sample_cache_entries.csv"):
    """
    Generate a sample CSV template file with example entries to help users understand
    the expected format for cache entry imports.
    
    Args:
        output_path: Path where the sample CSV will be created
    
    Returns:
        Path to the created file
    """
    try:
        headers = [
            "nl_query", "template", "template_type", "reasoning_trace", 
            "is_template", "tags", "catalog_type", "catalog_subtype", 
            "catalog_name", "status"
        ]
        
        # Example rows
        sample_rows = [
            {
                "nl_query": "Get all customers from New York",
                "template": "SELECT * FROM customers WHERE state = 'NY'",
                "template_type": "sql",
                "reasoning_trace": "This SQL query filters the customers table to show only those from New York state using the state column.",
                "is_template": "false",
                "tags": "customers,query,new york",
                "catalog_type": "customer_data",
                "catalog_subtype": "geographical",
                "catalog_name": "customer_location_query",
                "status": "active"
            },
            {
                "nl_query": "Show orders for customer with ID {{customer_id}}",
                "template": "SELECT * FROM orders WHERE customer_id = {{customer_id}}",
                "template_type": "sql",
                "reasoning_trace": "This template allows querying orders for a specific customer by substituting the customer ID.",
                "is_template": "true",
                "tags": "orders,template,parameterized",
                "catalog_type": "order_data",
                "catalog_subtype": "customer_specific",
                "catalog_name": "customer_orders_query",
                "status": "active"
            },
            {
                "nl_query": "Get weather data for {{city}}",
                "template": "https://api.weather.example.com/data?location={{city}}&format=json",
                "template_type": "url",
                "reasoning_trace": "This URL template fetches weather data for a specified city.",
                "is_template": "true",
                "tags": "weather,api,city",
                "catalog_type": "external_data",
                "catalog_subtype": "weather",
                "catalog_name": "city_weather_api",
                "status": "active"
            }
        ]
        
        # Create CSV file
        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for row in sample_rows:
                writer.writerow(row)
                
        logger.info(f"Sample CSV template created at: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error creating sample CSV template: {e}")
        return None


if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Import CSV data into ThinkForge cache")
    parser.add_argument("--csv", "-c", dest="csv_file", help="Path to CSV file to import", required=False)
    parser.add_argument("--template-type", "-t", dest="template_type", 
                        choices=["sql", "api", "url", "workflow", "graphql", "regex", "script", "nosql", 
                                "cli", "prompt", "configuration", "reasoning_steps"],
                        default="sql", help="Template type for entries")
    parser.add_argument("--api-url", "-a", dest="api_url", 
                       help=f"API base URL (default: {API_BASE_URL})")
    parser.add_argument("--generate-sample", "-g", dest="generate_sample", 
                       action="store_true", help="Generate a sample CSV template")
    parser.add_argument("--sample-output", "-o", dest="sample_output",
                       default="sample_cache_entries.csv", help="Output path for sample CSV template")
    
    args = parser.parse_args()
    
    # Update API base URL if provided
    if args.api_url:
        API_BASE_URL = args.api_url
        logger.info(f"Using custom API URL: {API_BASE_URL}")
    
    # Generate sample template if requested
    if args.generate_sample:
        output_path = generate_sample_csv_template(args.sample_output)
        logger.info(f"You can use this sample as a template: {output_path}")
        exit(0)
    
    # Get CSV file path from arguments or prompt
    csv_file_path = args.csv_file
    if not csv_file_path:
        csv_file_path = input("Enter the path to your CSV file: ")
    
    # Validate and import CSV
    if not csv_file_path or not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
    else:
        logger.info(f"Importing CSV file: {csv_file_path} with template type: {args.template_type}")
        result = load_csv_to_cache(csv_file_path, args.template_type)
        if result:
            logger.info(f"Import complete. Successful: {result['success']}, Failed: {result['failed']}") 