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
        string_match = re.search(r'"([^'"]*)["']', nl_query)
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
        """Apply substitutions specifically for API templates (assumed JSON string).

        Substitutes values directly into the JSON string template.
        WARNING: Assumes template is valid JSON. More robust parsing could be used.

        Args: (Same as apply_substitution)

        Returns:
            The substituted API template string (JSON).
        """
        # This is a basic implementation assuming the template is a JSON string
        # and placeholders are simple :key instances.
        # A more robust method would parse the JSON and substitute values in the structure.
        substituted_template = template
        for entity_key, info in stored_entity_info.items():
            placeholder = info.get("placeholder")
            # Type could be used for JSON type checking (string vs number vs boolean)
            # entity_type = info.get("type", "string")
            if not placeholder or entity_key not in entities:
                continue # Or raise error
            value = entities[entity_key]

            try:
                # For JSON, we need to be careful about quotes for strings vs raw numbers/booleans
                # Simple approach: replace placeholder with JSON representation of value
                # json.dumps adds quotes for strings.
                formatted_value = json.dumps(value)

                # Need to replace the placeholder *including* potential quotes if it was
                # already quoted in the template. E.g., "param": ":value"
                # This simple string replacement might break JSON structure.
                # A better way: parse JSON, modify, dump back.
                # For now, just replace the placeholder text directly.
                substituted_template = substituted_template.replace(placeholder, formatted_value)

            except Exception as e:
                 raise ValueError(f"API/JSON substitution error for {entity_key}={value}: {e}")

        # Validate if the result is still valid JSON? (Optional)
        # try:
        #     json.loads(substituted_template)
        # except json.JSONDecodeError as e:
        #     logger.error(f"API substitution resulted in invalid JSON: {e}")
        #     # Handle error: maybe return original or raise specific error

        return substituted_template


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
