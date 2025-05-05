"""
MCP Server implementation using stdio for communication.

This script listens on standard input for JSON-RPC like messages conforming
to the Model Context Protocol, processes them, and writes responses to
standard output.

It relies on the nl_cache_framework and database configuration from the backend.
"""

import sys
import json
import logging
import os
from typing import Dict, Any, Optional

# --- Setup Logging ---
# Configure logging to file to avoid interfering with stdout
log_file_path = os.path.join(os.path.dirname(__file__), 'mcp_server.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path), # Log to file
        # logging.StreamHandler(sys.stderr) # Optionally log errors to stderr
    ]
)
logger = logging.getLogger("mcp_stdio_server")


# --- Dependency Setup ---
# Add project root to path to allow importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

try:
    from sqlalchemy.orm import Session
    # Import necessary components from the backend and framework
    from backend.database import SessionLocal # Get the session factory
    from nl_cache_framework import Text2SQLController, TemplateType
    # Import models for potential type checking or direct use if needed
    # from nl_cache_framework.models import Text2SQLCache, UsageLog
except ImportError as e:
    logger.error(f"Failed to import necessary modules: {e}. Ensure dependencies are installed and PYTHONPATH is correct.", exc_info=True)
    # Write an error message to stdout in case of import failure, then exit
    error_response = json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Server setup error: {e}"}, "id": None})
    print(error_response, flush=True)
    sys.exit(1)


# --- Tool Definitions (similar to what we had in app.py) ---
# We need the schemas for validation and listing
# Using dicts directly here, but could use Pydantic again if preferred
tools_registry: Dict[str, Dict[str, Any]] = {
    "search_nl_cache": {
        "description": "Searches the cache for existing entries similar to a given natural language query. Returns the closest matches found above a specified similarity threshold.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nl_query": {"type": "string", "description": "The natural language query to search for."},
                "threshold": {"type": "number", "description": "The minimum similarity score for a match.", "default": 0.85},
                "limit": {"type": "integer", "description": "The maximum number of similar entries to return.", "default": 1},
                "template_type": {"type": "string", "description": "Optional filter for template type (sql, api, url, workflow)."}
            },
            "required": ["nl_query"]
        },
        # Define output schema structure if needed for documentation/client
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "nl_query": {"type": "string"},
                    "template": {"type": "string"},
                    "template_type": {"type": "string"},
                    "similarity": {"type": "number"},
                    "reasoning_trace": {"type": ["string", "null"]},
                    "is_template": {"type": "boolean"},
                    "entity_replacements": {"type": ["object", "null"]}
                }
            }
        }
    },
    "add_cache_entry": {
        "description": "Adds a new natural language query and its corresponding template (SQL, API, URL, etc.) to the cache.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nl_query": {"type": "string", "description": "The natural language query."},
                "template": {"type": "string", "description": "The corresponding template (SQL, API JSON, URL, etc.)."},
                "template_type": {"type": "string", "enum": [t.value for t in TemplateType], "description": "The type of the template.", "default": "sql"},
                "reasoning_trace": {"type": ["string", "null"], "description": "Optional reasoning trace.", "default": None},
                "is_template": {"type": "boolean", "description": "Is this a template with placeholders?", "default": False},
                "entity_replacements": {"type": ["object", "null"], "description": "Placeholder definitions if is_template is true.", "default": None},
                "tags": {"type": ["array", "null"], "items": {"type": "string"}, "description": "Optional tags for categorization.", "default": []},
                "database_name": {"type": ["string", "null"], "description": "Optional target database name.", "default": None},
                "schema_name": {"type": ["string", "null"], "description": "Optional target schema name.", "default": None},
            },
            "required": ["nl_query", "template"]
        },
        "output_schema": { # Schema for the created entry
            "type": "object",
            "properties": {
                 "id": {"type": "integer"},
                 "nl_query": {"type": "string"},
                 "template": {"type": "string"},
                 "template_type": {"type": "string"},
                 "reasoning_trace": {"type": ["string", "null"]},
                 "is_template": {"type": "boolean"},
                 "entity_replacements": {"type": ["object", "null"]},
                 "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                 "created_at": {"type": "string", "format": "date-time"},
                 "updated_at": {"type": "string", "format": "date-time"},
                 "is_valid": {"type": "boolean"}
            }
        }
    },
    "get_cache_entry": {
        "description": "Retrieves a specific cache entry by its unique ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer", "description": "The unique ID of the cache entry to retrieve."}
            },
            "required": ["entry_id"]
        },
        "output_schema": { # Same as add_cache_entry output, but can be null
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                         "id": {"type": "integer"},
                         "nl_query": {"type": "string"},
                         "template": {"type": "string"},
                         "template_type": {"type": "string"},
                         "reasoning_trace": {"type": ["string", "null"]},
                         "is_template": {"type": "boolean"},
                         "entity_replacements": {"type": ["object", "null"]},
                         "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                         "created_at": {"type": "string", "format": "date-time"},
                         "updated_at": {"type": "string", "format": "date-time"},
                         "is_valid": {"type": "boolean"}
                    }
                },
                {"type": "null"}
            ]
        }
    },
    "update_cache_entry": {
        "description": "Updates an existing cache entry identified by its ID. Only provided fields are updated.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer", "description": "The unique ID of the cache entry to update."},
                "nl_query": {"type": "string", "description": "The natural language query."},
                "template": {"type": "string", "description": "The corresponding template (SQL, API JSON, URL, etc.)."},
                "template_type": {"type": "string", "enum": [t.value for t in TemplateType], "description": "The type of the template."},
                "reasoning_trace": {"type": ["string", "null"], "description": "Optional reasoning trace."},
                "is_template": {"type": "boolean", "description": "Is this a template with placeholders?"},
                "entity_replacements": {"type": ["object", "null"], "description": "Placeholder definitions if is_template is true."},
                "tags": {"type": ["array", "null"], "items": {"type": "string"}, "description": "Optional tags for categorization."},
                "database_name": {"type": ["string", "null"], "description": "Optional target database name."},
                "schema_name": {"type": ["string", "null"], "description": "Optional target schema name."},
                "is_valid": {"type": "boolean", "description": "Set the validity status."}
                # Add other updatable fields as needed
            },
            "required": ["entry_id"]
        },
        "output_schema": { # Schema for the updated entry
            "type": "object",
             "properties": {
                 "id": {"type": "integer"},
                 "nl_query": {"type": "string"},
                 "template": {"type": "string"},
                 "template_type": {"type": "string"},
                 "reasoning_trace": {"type": ["string", "null"]},
                 "is_template": {"type": "boolean"},
                 "entity_replacements": {"type": ["object", "null"]},
                 "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                 "created_at": {"type": "string", "format": "date-time"},
                 "updated_at": {"type": "string", "format": "date-time"},
                 "is_valid": {"type": "boolean"}
            }
        }
    },
    "delete_cache_entry": {
        "description": "Deletes a specific cache entry by its unique ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "integer", "description": "The unique ID of the cache entry to delete."}
            },
            "required": ["entry_id"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["deleted"]},
                "id": {"type": "integer"}
            }
        }
    }
}

# --- MCP Request Handlers ---

def handle_initialize(request: Dict[str, Any], db: Session) -> Dict[str, Any]:
    logger.info("Handling initialize request")
    # Simple acknowledgment for now
    return {"status": "initialized", "server_version": "0.1.0"}

def handle_list_tools(request: Dict[str, Any], db: Session) -> Dict[str, Any]:
    logger.info("Handling list_tools request")
    tools_list = []
    for name, details in tools_registry.items():
        tools_list.append({
            "name": name,
            "description": details["description"],
            "inputSchema": details["input_schema"],
        })
    return {"tools": tools_list}

def handle_call_tool(request: Dict[str, Any], db: Session) -> Dict[str, Any]:
    # Get parameters from the 'params' field of the request
    params = request.get('params', {})
    tool_name = params.get('tool_name')
    arguments = params.get('arguments', {})
    logger.info(f"Handling call_tool request for tool: {tool_name}")

    if not tool_name or tool_name not in tools_registry:
        raise ValueError(f"Tool '{tool_name}' not found or not provided.")

    # Initialize controller (used by multiple tools)
    controller = Text2SQLController(db_session=db)

    # --- Tool Specific Logic ---
    if tool_name == "search_nl_cache":
        # Basic validation (more robust validation using schema would be better)
        if 'nl_query' not in arguments:
            raise ValueError("Missing required argument 'nl_query' for search_nl_cache")

        # Extract arguments with defaults
        nl_query = arguments['nl_query']
        threshold = arguments.get('threshold', tools_registry[tool_name]['input_schema']['properties']['threshold']['default'])
        limit = arguments.get('limit', tools_registry[tool_name]['input_schema']['properties']['limit']['default'])
        template_type = arguments.get('template_type')

        # Call the controller
        cache_results = controller.search_query(
            nl_query=nl_query,
            similarity_threshold=threshold,
            limit=limit,
            template_type=template_type
        )
        # Controller returns a list of dicts, which matches our output schema structure
        # MCP expects the direct result of the tool call in the 'result' field
        return cache_results # Return the list directly

    elif tool_name == "add_cache_entry":
        # Basic validation
        if 'nl_query' not in arguments or 'template' not in arguments:
            raise ValueError("Missing required arguments 'nl_query' or 'template' for add_cache_entry")

        # Extract args, using defaults from schema where applicable
        schema_props = tools_registry[tool_name]['input_schema']['properties']
        try:
            template_type_val = arguments.get('template_type', schema_props['template_type']['default'])
            template_type = TemplateType(template_type_val)
        except ValueError:
             raise ValueError(f"Invalid template_type: {template_type_val}")

        new_entry_data = controller.add_query(
            nl_query=arguments['nl_query'],
            template=arguments['template'],
            template_type=template_type,
            reasoning_trace=arguments.get('reasoning_trace', schema_props['reasoning_trace']['default']),
            is_template=arguments.get('is_template', schema_props['is_template']['default']),
            entity_replacements=arguments.get('entity_replacements', schema_props['entity_replacements']['default']),
            tags=arguments.get('tags', schema_props['tags']['default']),
            database_name=arguments.get('database_name', schema_props['database_name']['default']),
            schema_name=arguments.get('schema_name', schema_props['schema_name']['default']),
            commit=True
        )
        # Convert to dict using the model's method for consistent output
        return new_entry_data.to_dict()

    elif tool_name == "get_cache_entry":
        if 'entry_id' not in arguments:
            raise ValueError("Missing required argument 'entry_id' for get_cache_entry")
        entry_id = arguments['entry_id']
        if not isinstance(entry_id, int):
             raise ValueError("Argument 'entry_id' must be an integer")
        
        # Using controller method if available, otherwise direct query
        # entry = controller.get_query_by_id(entry_id)
        # Direct query for now:
        from nl_cache_framework.models import Text2SQLCache # Import model locally if needed
        entry = db.query(Text2SQLCache).filter(Text2SQLCache.id == entry_id).first()

        return entry.to_dict() if entry else None # Return dict or null

    elif tool_name == "update_cache_entry":
        if 'entry_id' not in arguments:
            raise ValueError("Missing required argument 'entry_id' for update_cache_entry")
        entry_id = arguments['entry_id']
        if not isinstance(entry_id, int):
             raise ValueError("Argument 'entry_id' must be an integer")

        # Prepare updates dict, excluding entry_id
        updates = {k: v for k, v in arguments.items() if k != 'entry_id'}
        
        # Optional: Validate template_type if provided
        if 'template_type' in updates:
            try:
                 updates['template_type'] = TemplateType(updates['template_type'])
            except ValueError:
                 raise ValueError(f"Invalid template_type: {updates['template_type']}")

        updated_entry = controller.update_query(query_id=entry_id, updates=updates)

        if not updated_entry:
            # Raise error consistent with MCP expectations (ValueError maybe?)
            raise ValueError(f"Cache entry with ID {entry_id} not found")

        return updated_entry.to_dict()

    elif tool_name == "delete_cache_entry":
        if 'entry_id' not in arguments:
            raise ValueError("Missing required argument 'entry_id' for delete_cache_entry")
        entry_id = arguments['entry_id']
        if not isinstance(entry_id, int):
             raise ValueError("Argument 'entry_id' must be an integer")

        deleted = controller.delete_query(entry_id=entry_id, commit=True)

        if not deleted:
            raise ValueError(f"Cache entry with ID {entry_id} not found or could not be deleted")

        return {"status": "deleted", "id": entry_id}

    else:
        raise NotImplementedError(f"Tool '{tool_name}' is registered but not implemented.")

# --- Main Processing Loop ---
def main():
    logger.info("MCP stdio server started. Listening on stdin...")
    db: Optional[Session] = None # Hold the session
    try:
        db = SessionLocal() # Create a single session for the lifetime of the server process
        while True:
            line = sys.stdin.readline()
            if not line:
                logger.info("Stdin closed. Exiting.")
                break # End of input

            logger.debug(f"Received line: {line.strip()}")
            request_id = None # Keep track of request ID for response
            response = None

            try:
                data = json.loads(line)
                request_id = data.get('id')

                # Basic JSON-RPC structure check
                if data.get("jsonrpc") != "2.0" or 'method' not in data:
                    raise ValueError("Invalid JSON-RPC request")

                method = data['method']

                # Route to appropriate handler
                result = None
                if method == "initialize":
                    result = handle_initialize(data, db)
                elif method == "list_tools":
                    result = handle_list_tools(data, db)
                elif method == "call_tool":
                    result = handle_call_tool(data, db)
                else:
                    raise ValueError(f"Unknown method: {method}")

                response = {"jsonrpc": "2.0", "result": result, "id": request_id}

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}", exc_info=True)
                response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {e}"}, "id": None}
            except (ValueError, NotImplementedError, Exception) as e:
                # Catch specific handling errors or general exceptions
                logger.error(f"Error processing request: {e}", exc_info=True)
                error_code = -32603 # Internal error by default
                if isinstance(e, ValueError): # Could indicate invalid params/method
                    error_code = -32602 # Invalid params
                elif isinstance(e, NotImplementedError):
                     error_code = -32601 # Method not found (though we check registry first)
                
                response = {"jsonrpc": "2.0", "error": {"code": error_code, "message": str(e)}, "id": request_id}

            # Send response to stdout
            if response:
                response_json = json.dumps(response)
                logger.debug(f"Sending response: {response_json}")
                print(response_json, flush=True)

    except Exception as e:
        # Catch errors during initial setup or loop itself
        logger.error(f"Critical error in main loop: {e}", exc_info=True)
        # Try to send a final error response if possible
        try:
            error_response = json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Server error: {e}"}, "id": None})
            print(error_response, flush=True)
        except Exception as final_err:
            logger.error(f"Failed to send final error response: {final_err}")
    finally:
        if db:
            db.close()
            logger.info("Database session closed.")
        logger.info("MCP stdio server shutting down.")

if __name__ == "__main__":
    main()

"""
Example JSON-RPC requests over stdio (as comments):

{"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}
{"jsonrpc": "2.0", "method": "list_tools", "params": {}, "id": 2}
{"jsonrpc": "2.0", "method": "call_tool", "params": {"tool_name": "search_nl_cache", "arguments": {"nl_query": "find total sales last month"}}, "id": 3}
""" 