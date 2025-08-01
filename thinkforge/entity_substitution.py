"""
Handles entity extraction and substitution within templates.

Supports different template types (SQL, URL, API, Workflow) and entity types (string, number, date).
Uses regex for placeholder detection (e.g., :entity_name).
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import re
import urllib.parse
import datetime
import json
from .models import TemplateType # Import TemplateType

logger = logging.getLogger(__name__)

# Basic regex to find placeholders like :entity_name
PLACEHOLDER_REGEX = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


class Text2SQLEntitySubstitution:
    """Provides methods for extracting and substituting entities in templates."""

    def extract_placeholders(self, template: str) -> List[str]:
        """Extract all unique placeholder names (like ':param') from a template string.

        Args:
            template: The template string.

        Returns:
            A list of unique placeholder names found (without the leading colon).
        """
        if not template:
            return []
        return list(set(PLACEHOLDER_REGEX.findall(template)))

    def extract_entities(
        self, nl_query: str, entity_schema: Optional[Dict[str, Dict]] = None
    ) -> Dict[str, Any]:
        """Extract entities from a natural language query.

        Placeholder implementation: This currently uses simple regex examples.
        A production system would use a more sophisticated NER model or service.

        Args:
            nl_query: The natural language query string.
            entity_schema: Optional schema defining expected entities and their types/patterns.
                           Example: {'date_entity': {'type': 'date', 'pattern': '\\d{4}-\\d{2}-\\d{2}'}}

        Returns:
            A dictionary where keys are entity names and values are the extracted entity values.
        """
        entities = {}
        # Example: Extract a date like YYYY-MM-DD
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", nl_query)
        if date_match:
            entities["date_entity"] = date_match.group(1)

        # Example: Extract a number
        number_match = re.search(r"\b(\d+\.?\d*)\b", nl_query)
        if number_match:
             # Avoid capturing the date again if it was matched
             if "date_entity" not in entities or number_match.group(1) != entities["date_entity"]:
                entities["number_entity"] = float(number_match.group(1)) # Store as float

        # Example: Extract quoted string
        string_match = re.search(r'"([^"\']*)["\']', nl_query)
        if string_match:
            entities["string_entity"] = string_match.group(1)

        logger.debug(f"Extracted entities from '{nl_query[:50]}...': {entities}")
        # TODO: Integrate with a proper NER system based on entity_schema if provided.
        return entities

    def apply_substitution(
        self,
        template: str,
        entities: Dict[str, Any],
        stored_entity_info: Dict[str, Dict],
    ) -> str:
        """Apply entity substitutions to a template string.

        Replaces placeholders in the template based on the provided entity values
        and the stored entity information (which maps entity keys to placeholders).

        Args:
            template: The template string containing placeholders (e.g., ":user_id").
            entities: A dictionary of extracted entity values (e.g., {"user_id_from_query": 123}).
            stored_entity_info: A dictionary mapping the logical entity name used during storage
                                to its placeholder and type information.
                                Example: {'user_entity': {'placeholder': ':user_id', 'type': 'integer'}}

        Returns:
            The template string with placeholders replaced by entity values.

        Raises:
            ValueError: If a required entity value is missing or has an incorrect type.
        """
        if not template:
            return ""
        if not stored_entity_info:
            logger.warning("No entity replacement info provided; returning original template.")
            return template

        substituted_template = template

        for entity_key, info in stored_entity_info.items():
            placeholder = info.get("placeholder")
            entity_type = info.get("type", "string") # Default to string if type not specified

            if not placeholder:
                logger.warning(f"Placeholder missing for entity key '{entity_key}'. Skipping.")
                continue

            # Find the value from the extracted entities dictionary
            # Assume the key in `entities` matches `entity_key` from `stored_entity_info`
            if entity_key not in entities:
                 # Allow optional entities? For now, raise error.
                raise ValueError(
                    f"Required entity value for key '{entity_key}' (placeholder '{placeholder}') not found in extracted entities."
                )

            value = entities[entity_key]

            # Basic type checking and formatting (can be expanded)
            try:
                if entity_type == "integer":
                    formatted_value = str(int(value))
                elif entity_type == "number" or entity_type == "float":
                    formatted_value = str(float(value))
                elif entity_type == "boolean":
                    formatted_value = str(bool(value))
                elif entity_type == "date":
                    # Basic date formatting, assumes YYYY-MM-DD or datetime object
                    if isinstance(value, datetime.date):
                        formatted_value = value.strftime("%Y-%m-%d")
                    else:
                        # Attempt to parse if string
                        datetime.datetime.strptime(str(value), "%Y-%m-%d")
                        formatted_value = str(value)
                elif entity_type == "string":
                    # Basic sanitization for strings (e.g., escape quotes for SQL)
                    # This is highly context-dependent (SQL vs URL vs JSON)
                    # For now, just convert to string.
                    formatted_value = str(value)
                    # Example SQL sanitization (use proper library like SQLAlchemy normally):
                    # formatted_value = str(value).replace("'", "''")
                else:
                    logger.warning(f"Unsupported entity type '{entity_type}' for '{placeholder}'. Treating as string.")
                    formatted_value = str(value)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Failed to format entity '{entity_key}' with value '{value}' as type '{entity_type}' for placeholder '{placeholder}': {e}"
                )

            # Perform the replacement
            # Use re.sub for safer replacement than basic str.replace if placeholder might be substring
            substituted_template = substituted_template.replace(placeholder, formatted_value)
            # Potential improvement: Use regex sub with word boundaries if needed
            # substituted_template = re.sub(rf'\b{placeholder}\b', formatted_value, substituted_template)

        return substituted_template

    # --- Type-Specific Substitution Logic (Example) ---

    def apply_sql_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for SQL templates.

        Includes basic quoting for string types.
        WARNING: This is NOT safe against SQL injection. Use parameterized queries
        via SQLAlchemy or similar libraries in production.

        Args: (Same as apply_substitution)

        Returns:
            The substituted SQL query string.
        """
        substituted_template = template
        for entity_key, info in stored_entity_info.items():
            placeholder = info.get("placeholder")
            entity_type = info.get("type", "string")
            if not placeholder or entity_key not in entities:
                continue # Or raise error
            value = entities[entity_key]

            try:
                if entity_type == "string":
                    # Basic SQL string quoting (INSECURE!)
                    escaped_value = str(value).replace("'", "''")
                    formatted_value = "'" + escaped_value + "'"
                elif entity_type == "integer":
                    formatted_value = str(int(value))
                elif entity_type == "number" or entity_type == "float":
                    formatted_value = str(float(value))
                elif entity_type == "boolean":
                    # Adjust based on SQL dialect (e.g., TRUE/FALSE, 1/0)
                    formatted_value = "TRUE" if bool(value) else "FALSE"
                elif entity_type == "date":
                    if isinstance(value, datetime.date):
                        formatted_value = "'" + value.strftime('%Y-%m-%d') + "'"
                    else:
                        # Ensure value is a string before strptime
                        date_str = str(value)
                        datetime.datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_value = "'" + date_str + "'"
                else:
                    escaped_value = str(value).replace("'", "''")
                    formatted_value = "'" + escaped_value + "'"

                substituted_template = substituted_template.replace(
                    placeholder, formatted_value
                )
            except (ValueError, TypeError) as e:
                 raise ValueError(f"SQL formatting error for {entity_key}={value} ({entity_type}): {e}")

        return substituted_template

    def apply_url_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for URL templates.

        Includes URL encoding for substituted values.

        Args: (Same as apply_substitution)

        Returns:
            The substituted URL string.
        """
        substituted_template = template
        for entity_key, info in stored_entity_info.items():
            placeholder = info.get("placeholder")
            entity_type = info.get("type", "string") # Type might influence encoding
            if not placeholder or entity_key not in entities:
                continue # Or raise error
            value = entities[entity_key]

            try:
                # URL encode the value before substituting
                formatted_value = urllib.parse.quote_plus(str(value))
                substituted_template = substituted_template.replace(
                    placeholder, formatted_value
                )
            except Exception as e:
                 raise ValueError(f"URL encoding error for {entity_key}={value}: {e}")

        return substituted_template

    def apply_api_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for API templates.

        Args: (Same as apply_substitution)

        Returns:
            The substituted API spec (JSON string).
        """
        substituted_template = template
        for entity_key, info in stored_entity_info.items():
            placeholder = info.get("placeholder")
            entity_type = info.get("type", "string")
            if not placeholder or entity_key not in entities:
                continue
            value = entities[entity_key]

            try:
                # For API templates, we might need JSON-aware substitution
                if entity_type == "string":
                    # JSON string encoding for API payloads
                    formatted_value = json.dumps(str(value))
                elif entity_type in ["integer", "number", "float"]:
                    formatted_value = str(value)
                elif entity_type == "boolean":
                    formatted_value = "true" if bool(value) else "false"
                elif entity_type == "array":
                    if isinstance(value, list):
                        formatted_value = json.dumps(value)
                    else:
                        formatted_value = json.dumps([value])
                elif entity_type == "object":
                    if isinstance(value, dict):
                        formatted_value = json.dumps(value)
                    else:
                        formatted_value = json.dumps({"value": value})
                else:
                    formatted_value = json.dumps(str(value))

                substituted_template = substituted_template.replace(
                    placeholder, formatted_value
                )
            except (ValueError, TypeError) as e:
                raise ValueError(f"API formatting error for {entity_key}={value} ({entity_type}): {e}")

        return substituted_template

    def apply_dsl_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for DSL component templates.

        DSL templates contain structured components that can be composed to build queries.
        This method handles entity substitution within DSL component structures.

        Args: (Same as apply_substitution)

        Returns:
            The substituted DSL component (JSON string).
        """
        try:
            # Parse the DSL template as JSON
            dsl_data = json.loads(template) if isinstance(template, str) else template
            
            if not isinstance(dsl_data, dict) or 'component_type' not in dsl_data:
                raise ValueError("DSL template must be a JSON object with 'component_type' field")
            
            # Deep copy to avoid modifying the original
            substituted_data = json.loads(json.dumps(dsl_data))
            
            # Apply entity substitutions recursively through the DSL structure
            substituted_data = self._substitute_dsl_recursive(
                substituted_data, entities, stored_entity_info
            )
            
            return json.dumps(substituted_data, indent=2)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in DSL template: {e}")
        except Exception as e:
            raise ValueError(f"DSL substitution error: {e}")

    def _substitute_dsl_recursive(
        self, data: Any, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> Any:
        """Recursively substitute entities in DSL data structures."""
        if isinstance(data, dict):
            return {
                key: self._substitute_dsl_recursive(value, entities, stored_entity_info)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_dsl_recursive(item, entities, stored_entity_info)
                for item in data
            ]
        elif isinstance(data, str):
            # Apply placeholder substitution to string values
            substituted_string = data
            for entity_key, info in stored_entity_info.items():
                placeholder = info.get("placeholder")
                entity_type = info.get("type", "string")
                if not placeholder or entity_key not in entities:
                    continue
                value = entities[entity_key]
                
                try:
                    # Format value based on entity type for DSL context
                    if entity_type == "string":
                        formatted_value = str(value)
                    elif entity_type in ["integer", "int"]:
                        formatted_value = str(int(value))
                    elif entity_type in ["number", "float"]:
                        formatted_value = str(float(value))
                    elif entity_type == "boolean":
                        formatted_value = str(bool(value)).lower()
                    elif entity_type == "date":
                        if isinstance(value, datetime.date):
                            formatted_value = value.strftime('%Y-%m-%d')
                        else:
                            # Validate date format
                            datetime.datetime.strptime(str(value), "%Y-%m-%d")
                            formatted_value = str(value)
                    else:
                        formatted_value = str(value)
                    
                    substituted_string = substituted_string.replace(
                        placeholder, formatted_value
                    )
                except (ValueError, TypeError) as e:
                    raise ValueError(f"DSL entity formatting error for {entity_key}={value} ({entity_type}): {e}")
            
            return substituted_string
        else:
            return data

    def apply_mcp_tool_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for MCP tool templates.
        
        MCP tools require careful handling of server configurations, connection parameters,
        and tool specifications with proper JSON formatting.
        
        Args: (Same as apply_substitution)
        
        Returns:
            The substituted MCP tool configuration (JSON string).
        """
        try:
            # Parse the MCP template as JSON
            mcp_data = json.loads(template) if isinstance(template, str) else template
            
            if not isinstance(mcp_data, dict):
                raise ValueError("MCP template must be a JSON object")
            
            # Deep copy to avoid modifying the original
            substituted_data = json.loads(json.dumps(mcp_data))
            
            # Apply entity substitutions recursively through the MCP structure
            substituted_data = self._substitute_mcp_recursive(
                substituted_data, entities, stored_entity_info
            )
            
            return json.dumps(substituted_data, indent=2)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in MCP template: {e}")
        except Exception as e:
            raise ValueError(f"MCP substitution error: {e}")

    def _substitute_mcp_recursive(
        self, data: Any, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> Any:
        """Recursively substitute entities in MCP tool data structures."""
        if isinstance(data, dict):
            return {
                key: self._substitute_mcp_recursive(value, entities, stored_entity_info)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_mcp_recursive(item, entities, stored_entity_info)
                for item in data
            ]
        elif isinstance(data, str):
            # Apply placeholder substitution with MCP-specific formatting
            substituted_string = data
            for entity_key, info in stored_entity_info.items():
                placeholder = info.get("placeholder")
                entity_type = info.get("type", "string")
                if not placeholder or entity_key not in entities:
                    continue
                value = entities[entity_key]
                
                try:
                    # Format value for MCP context (often environment variables or config values)
                    if entity_type == "api_key":
                        # Handle sensitive configuration like API keys
                        formatted_value = str(value)
                    elif entity_type == "endpoint":
                        # Handle URL endpoints
                        formatted_value = str(value).rstrip('/')
                    elif entity_type == "port":
                        formatted_value = str(int(value))
                    elif entity_type == "timeout":
                        formatted_value = str(int(value))
                    elif entity_type == "boolean":
                        formatted_value = str(bool(value)).lower()
                    else:
                        formatted_value = str(value)
                    
                    substituted_string = substituted_string.replace(
                        placeholder, formatted_value
                    )
                except (ValueError, TypeError) as e:
                    raise ValueError(f"MCP entity formatting error for {entity_key}={value} ({entity_type}): {e}")
            
            return substituted_string
        else:
            return data

    def apply_agent_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for AI agent templates.
        
        Agent templates require careful handling of model configurations, system prompts,
        and execution parameters with proper JSON formatting.
        
        Args: (Same as apply_substitution)
        
        Returns:
            The substituted agent configuration (JSON string).
        """
        try:
            # Parse the agent template as JSON
            agent_data = json.loads(template) if isinstance(template, str) else template
            
            if not isinstance(agent_data, dict):
                raise ValueError("Agent template must be a JSON object")
            
            # Deep copy to avoid modifying the original
            substituted_data = json.loads(json.dumps(agent_data))
            
            # Apply entity substitutions recursively through the agent structure
            substituted_data = self._substitute_agent_recursive(
                substituted_data, entities, stored_entity_info
            )
            
            return json.dumps(substituted_data, indent=2)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Agent template: {e}")
        except Exception as e:
            raise ValueError(f"Agent substitution error: {e}")

    def _substitute_agent_recursive(
        self, data: Any, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> Any:
        """Recursively substitute entities in agent data structures."""
        if isinstance(data, dict):
            return {
                key: self._substitute_agent_recursive(value, entities, stored_entity_info)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_agent_recursive(item, entities, stored_entity_info)
                for item in data
            ]
        elif isinstance(data, str):
            # Apply placeholder substitution with agent-specific formatting
            substituted_string = data
            for entity_key, info in stored_entity_info.items():
                placeholder = info.get("placeholder")
                entity_type = info.get("type", "string")
                if not placeholder or entity_key not in entities:
                    continue
                value = entities[entity_key]
                
                try:
                    # Format value for agent context
                    if entity_type == "model_name":
                        formatted_value = str(value)
                    elif entity_type == "temperature":
                        formatted_value = str(float(value))
                    elif entity_type == "max_tokens":
                        formatted_value = str(int(value))
                    elif entity_type == "system_prompt":
                        # Ensure proper escaping for JSON string context
                        formatted_value = str(value)
                    elif entity_type == "boolean":
                        formatted_value = str(bool(value)).lower()
                    elif entity_type == "integer":
                        formatted_value = str(int(value))
                    else:
                        formatted_value = str(value)
                    
                    substituted_string = substituted_string.replace(
                        placeholder, formatted_value
                    )
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Agent entity formatting error for {entity_key}={value} ({entity_type}): {e}")
            
            return substituted_string
        else:
            return data

    def apply_function_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for function templates.
        
        Function templates require careful handling of code, parameter schemas,
        and execution configurations with proper JSON formatting.
        
        Args: (Same as apply_substitution)
        
        Returns:
            The substituted function definition (JSON string).
        """
        try:
            # Parse the function template as JSON
            function_data = json.loads(template) if isinstance(template, str) else template
            
            if not isinstance(function_data, dict):
                raise ValueError("Function template must be a JSON object")
            
            # Deep copy to avoid modifying the original
            substituted_data = json.loads(json.dumps(function_data))
            
            # Apply entity substitutions recursively through the function structure
            substituted_data = self._substitute_function_recursive(
                substituted_data, entities, stored_entity_info
            )
            
            return json.dumps(substituted_data, indent=2)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Function template: {e}")
        except Exception as e:
            raise ValueError(f"Function substitution error: {e}")

    def _substitute_function_recursive(
        self, data: Any, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> Any:
        """Recursively substitute entities in function data structures."""
        if isinstance(data, dict):
            return {
                key: self._substitute_function_recursive(value, entities, stored_entity_info)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_function_recursive(item, entities, stored_entity_info)
                for item in data
            ]
        elif isinstance(data, str):
            # Apply placeholder substitution with function-specific formatting
            substituted_string = data
            for entity_key, info in stored_entity_info.items():
                placeholder = info.get("placeholder")
                entity_type = info.get("type", "string")
                if not placeholder or entity_key not in entities:
                    continue
                value = entities[entity_key]
                
                try:
                    # Format value for function context
                    if entity_type == "code":
                        # Handle code blocks - preserve formatting
                        formatted_value = str(value)
                    elif entity_type == "language":
                        formatted_value = str(value).lower()
                    elif entity_type == "entry_point":
                        formatted_value = str(value)
                    elif entity_type == "timeout":
                        formatted_value = str(int(value))
                    elif entity_type == "memory_limit":
                        formatted_value = str(value)  # Could be "1GB", "512MB", etc.
                    elif entity_type == "boolean":
                        formatted_value = str(bool(value)).lower()
                    elif entity_type == "integer":
                        formatted_value = str(int(value))
                    elif entity_type == "array":
                        if isinstance(value, list):
                            formatted_value = json.dumps(value)
                        else:
                            formatted_value = json.dumps([str(value)])
                    else:
                        formatted_value = str(value)
                    
                    substituted_string = substituted_string.replace(
                        placeholder, formatted_value
                    )
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Function entity formatting error for {entity_key}={value} ({entity_type}): {e}")
            
            return substituted_string
        else:
            return data

    def apply_recipe_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for recipe templates.
        
        Recipe templates require careful handling of step configurations, tool references,
        and parameter passing between steps with proper JSON formatting.
        
        Args: (Same as apply_substitution)
        
        Returns:
            The substituted recipe definition (JSON string).
        """
        try:
            # Parse the recipe template as JSON
            recipe_data = json.loads(template) if isinstance(template, str) else template
            
            if not isinstance(recipe_data, dict):
                raise ValueError("Recipe template must be a JSON object")
            
            # Deep copy to avoid modifying the original
            substituted_data = json.loads(json.dumps(recipe_data))
            
            # Apply entity substitutions recursively through the recipe structure
            substituted_data = self._substitute_recipe_recursive(
                substituted_data, entities, stored_entity_info
            )
            
            return json.dumps(substituted_data, indent=2)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Recipe template: {e}")
        except Exception as e:
            raise ValueError(f"Recipe substitution error: {e}")

    def _substitute_recipe_recursive(
        self, data: Any, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> Any:
        """Recursively substitute entities in recipe data structures."""
        if isinstance(data, dict):
            return {
                key: self._substitute_recipe_recursive(value, entities, stored_entity_info)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_recipe_recursive(item, entities, stored_entity_info)
                for item in data
            ]
        elif isinstance(data, str):
            # Apply placeholder substitution with recipe-specific formatting
            substituted_string = data
            for entity_key, info in stored_entity_info.items():
                placeholder = info.get("placeholder")
                entity_type = info.get("type", "string")
                if not placeholder or entity_key not in entities:
                    continue
                value = entities[entity_key]
                
                try:
                    # Format value for recipe context
                    if entity_type == "tool_id":
                        # Handle tool ID references
                        formatted_value = str(int(value))
                    elif entity_type == "step_name":
                        # Handle step names and identifiers
                        formatted_value = str(value).replace(' ', '_').lower()
                    elif entity_type == "timeout":
                        formatted_value = str(int(value))
                    elif entity_type == "retry_count":
                        formatted_value = str(int(value))
                    elif entity_type == "complexity_level":
                        # Validate complexity levels
                        valid_levels = ['beginner', 'intermediate', 'advanced']
                        level = str(value).lower()
                        if level not in valid_levels:
                            raise ValueError(f"Invalid complexity level: {level}. Must be one of {valid_levels}")
                        formatted_value = level
                    elif entity_type == "execution_type":
                        # Handle execution types (sequential, parallel, conditional)
                        valid_types = ['sequential', 'parallel', 'conditional']
                        exec_type = str(value).lower()
                        if exec_type not in valid_types:
                            raise ValueError(f"Invalid execution type: {exec_type}. Must be one of {valid_types}")
                        formatted_value = exec_type
                    elif entity_type == "boolean":
                        formatted_value = str(bool(value)).lower()
                    elif entity_type == "integer":
                        formatted_value = str(int(value))
                    elif entity_type == "float":
                        formatted_value = str(float(value))
                    elif entity_type == "json":
                        # Handle JSON parameter objects
                        if isinstance(value, (dict, list)):
                            formatted_value = json.dumps(value)
                        else:
                            formatted_value = str(value)
                    else:
                        formatted_value = str(value)
                    
                    substituted_string = substituted_string.replace(
                        placeholder, formatted_value
                    )
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Recipe entity formatting error for {entity_key}={value} ({entity_type}): {e}")
            
            return substituted_string
        else:
            return data

    def apply_recipe_step_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for recipe step templates.
        
        Recipe step templates are reusable components that can be configured
        with specific parameters and composed into larger recipes.
        
        Args: (Same as apply_substitution)
        
        Returns:
            The substituted recipe step definition (JSON string).
        """
        try:
            # Parse the recipe step template as JSON
            step_data = json.loads(template) if isinstance(template, str) else template
            
            if not isinstance(step_data, dict):
                raise ValueError("Recipe step template must be a JSON object")
            
            # Deep copy to avoid modifying the original
            substituted_data = json.loads(json.dumps(step_data))
            
            # Apply entity substitutions recursively through the step structure
            substituted_data = self._substitute_recipe_step_recursive(
                substituted_data, entities, stored_entity_info
            )
            
            return json.dumps(substituted_data, indent=2)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Recipe step template: {e}")
        except Exception as e:
            raise ValueError(f"Recipe step substitution error: {e}")

    def _substitute_recipe_step_recursive(
        self, data: Any, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> Any:
        """Recursively substitute entities in recipe step data structures."""
        if isinstance(data, dict):
            return {
                key: self._substitute_recipe_step_recursive(value, entities, stored_entity_info)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_recipe_step_recursive(item, entities, stored_entity_info)
                for item in data
            ]
        elif isinstance(data, str):
            # Apply placeholder substitution with recipe step-specific formatting
            substituted_string = data
            for entity_key, info in stored_entity_info.items():
                placeholder = info.get("placeholder")
                entity_type = info.get("type", "string")
                if not placeholder or entity_key not in entities:
                    continue
                value = entities[entity_key]
                
                try:
                    # Format value for recipe step context
                    if entity_type == "step_type":
                        # Handle step types (action, condition, loop, transform)
                        valid_types = ['action', 'condition', 'loop', 'transform']
                        step_type = str(value).lower()
                        if step_type not in valid_types:
                            raise ValueError(f"Invalid step type: {step_type}. Must be one of {valid_types}")
                        formatted_value = step_type
                    elif entity_type == "error_handling":
                        # Handle error handling strategies
                        valid_strategies = ['fail', 'continue', 'retry']
                        strategy = str(value).lower()
                        if strategy not in valid_strategies:
                            raise ValueError(f"Invalid error handling strategy: {strategy}. Must be one of {valid_strategies}")
                        formatted_value = strategy
                    elif entity_type == "condition_expression":
                        # Handle conditional expressions for step logic
                        formatted_value = str(value)
                    elif entity_type == "loop_count":
                        formatted_value = str(int(value))
                    elif entity_type == "transform_function":
                        # Handle data transformation function names
                        formatted_value = str(value)
                    elif entity_type == "input_schema":
                        # Handle input parameter schemas
                        if isinstance(value, dict):
                            formatted_value = json.dumps(value)
                        else:
                            formatted_value = str(value)
                    elif entity_type == "output_schema":
                        # Handle output parameter schemas
                        if isinstance(value, dict):
                            formatted_value = json.dumps(value)
                        else:
                            formatted_value = str(value)
                    elif entity_type == "boolean":
                        formatted_value = str(bool(value)).lower()
                    elif entity_type == "integer":
                        formatted_value = str(int(value))
                    else:
                        formatted_value = str(value)
                    
                    substituted_string = substituted_string.replace(
                        placeholder, formatted_value
                    )
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Recipe step entity formatting error for {entity_key}={value} ({entity_type}): {e}")
            
            return substituted_string
        else:
            return data

    def apply_recipe_template_substitution(
        self, template: str, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> str:
        """Apply substitutions specifically for recipe template definitions.
        
        Recipe templates are parameterized blueprints that can be instantiated
        with specific configurations to create concrete recipes.
        
        Args: (Same as apply_substitution)
        
        Returns:
            The substituted recipe template definition (JSON string).
        """
        try:
            # Parse the recipe template as JSON
            template_data = json.loads(template) if isinstance(template, str) else template
            
            if not isinstance(template_data, dict):
                raise ValueError("Recipe template must be a JSON object")
            
            # Deep copy to avoid modifying the original
            substituted_data = json.loads(json.dumps(template_data))
            
            # Apply entity substitutions recursively through the template structure
            substituted_data = self._substitute_recipe_template_recursive(
                substituted_data, entities, stored_entity_info
            )
            
            return json.dumps(substituted_data, indent=2)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Recipe template: {e}")
        except Exception as e:
            raise ValueError(f"Recipe template substitution error: {e}")

    def _substitute_recipe_template_recursive(
        self, data: Any, entities: Dict[str, Any], stored_entity_info: Dict[str, Dict]
    ) -> Any:
        """Recursively substitute entities in recipe template data structures."""
        if isinstance(data, dict):
            return {
                key: self._substitute_recipe_template_recursive(value, entities, stored_entity_info)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_recipe_template_recursive(item, entities, stored_entity_info)
                for item in data
            ]
        elif isinstance(data, str):
            # Apply placeholder substitution with recipe template-specific formatting
            substituted_string = data
            for entity_key, info in stored_entity_info.items():
                placeholder = info.get("placeholder")
                entity_type = info.get("type", "string")
                if not placeholder or entity_key not in entities:
                    continue
                value = entities[entity_key]
                
                try:
                    # Format value for recipe template context
                    if entity_type == "parameter_type":
                        # Handle parameter type definitions
                        valid_types = ['string', 'integer', 'float', 'boolean', 'array', 'object']
                        param_type = str(value).lower()
                        if param_type not in valid_types:
                            raise ValueError(f"Invalid parameter type: {param_type}. Must be one of {valid_types}")
                        formatted_value = param_type
                    elif entity_type == "validation_rule":
                        # Handle parameter validation rules
                        if isinstance(value, dict):
                            formatted_value = json.dumps(value)
                        else:
                            formatted_value = str(value)
                    elif entity_type == "default_value":
                        # Handle default parameter values
                        if isinstance(value, (dict, list)):
                            formatted_value = json.dumps(value)
                        elif isinstance(value, bool):
                            formatted_value = str(value).lower()
                        else:
                            formatted_value = str(value)
                    elif entity_type == "use_case":
                        # Handle use case descriptions
                        formatted_value = str(value)
                    elif entity_type == "industry_tag":
                        # Handle industry classification tags
                        formatted_value = str(value).lower().replace(' ', '_')
                    elif entity_type == "boolean":
                        formatted_value = str(bool(value)).lower()
                    elif entity_type == "integer":
                        formatted_value = str(int(value))
                    elif entity_type == "array":
                        if isinstance(value, list):
                            formatted_value = json.dumps(value)
                        else:
                            formatted_value = json.dumps([str(value)])
                    else:
                        formatted_value = str(value)
                    
                    substituted_string = substituted_string.replace(
                        placeholder, formatted_value
                    )
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Recipe template entity formatting error for {entity_key}={value} ({entity_type}): {e}")
            
            return substituted_string
        else:
            return data

    # --- Combined Method (Potentially used by Controller) ---
    @staticmethod
    def extract_and_replace_entities(
        nl_query: str,
        template: str,
        entity_replacements: Dict[str, Dict[str, Any]],
        new_entity_values: Optional[Dict[str, Any]] = None,
        template_type: str = "sql", # Default or determine from context
    ):
        """Extracts entities from NL query OR uses provided values, then substitutes into template.

        Args:
            nl_query: The natural language query (used if new_entity_values is None).
            template: The template string with placeholders.
            entity_replacements: Information about placeholders (key -> {placeholder, type}).
            new_entity_values: Optional dictionary of pre-extracted entity values to use.
            template_type: The type of template ('sql', 'url', 'api') for type-specific handling.

        Returns:
            A tuple containing:
                - The substituted template string.
                - A dictionary mapping placeholders to the values used for substitution.

        Raises:
            ValueError: If required entities are missing or substitution fails.
        """
        substitutor = Text2SQLEntitySubstitution() # Create instance

        if new_entity_values is not None:
            entities_to_use = new_entity_values
            logger.debug("Using provided entity values for substitution.")
        else:
            # Extract entities if not provided
            logger.debug("Extracting entities from NL query for substitution.")
            entities_to_use = substitutor.extract_entities(nl_query)

        # Select substitution method based on type
        if template_type == TemplateType.SQL:
            substituted_template = substitutor.apply_sql_substitution(
                template, entities_to_use, entity_replacements
            )
        elif template_type == TemplateType.URL:
            substituted_template = substitutor.apply_url_substitution(
                 template, entities_to_use, entity_replacements
            )
        elif template_type == TemplateType.API:
             substituted_template = substitutor.apply_api_substitution(
                 template, entities_to_use, entity_replacements
             )
        elif template_type == TemplateType.DSL:
             substituted_template = substitutor.apply_dsl_substitution(
                 template, entities_to_use, entity_replacements
             )
        elif template_type == TemplateType.MCP_TOOL:
            substituted_template = substitutor.apply_mcp_tool_substitution(
                template, entities_to_use, entity_replacements
            )
        elif template_type == TemplateType.AGENT:
            substituted_template = substitutor.apply_agent_substitution(
                template, entities_to_use, entity_replacements
            )
        elif template_type == TemplateType.FUNCTION:
            substituted_template = substitutor.apply_function_substitution(
                template, entities_to_use, entity_replacements
            )
        elif template_type == TemplateType.RECIPE:
            substituted_template = substitutor.apply_recipe_substitution(
                template, entities_to_use, entity_replacements
            )
        elif template_type == TemplateType.RECIPE_STEP:
            substituted_template = substitutor.apply_recipe_step_substitution(
                template, entities_to_use, entity_replacements
            )
        elif template_type == TemplateType.RECIPE_TEMPLATE:
            substituted_template = substitutor.apply_recipe_template_substitution(
                template, entities_to_use, entity_replacements
            )
        else: # Default or WORKFLOW etc.
            substituted_template = substitutor.apply_substitution(
                template, entities_to_use, entity_replacements
            )

        # Create mapping of placeholder -> applied value for clarity/debugging
        applied_mapping = {}
        for entity_key, info in entity_replacements.items():
            placeholder = info.get("placeholder")
            if placeholder and entity_key in entities_to_use:
                applied_mapping[placeholder] = entities_to_use[entity_key]

        return substituted_template, applied_mapping
