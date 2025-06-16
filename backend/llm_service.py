import os
import logging
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from prompts import (
    QUERY_MATCHING_PROMPT,
    WORKFLOW_GENERATION_PROMPT,
    REASONING_TRACE_PROMPT
)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-pro")

class LLMService:
    """Service for making calls to LLM models through OpenRouter."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the LLM service.
        
        Args:
            api_key: Optional API key for OpenRouter. If not provided, uses the environment variable.
            model: Optional model identifier. If not provided, uses the environment variable.
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_MODEL
        
        if not self.api_key:
            logger.warning("OpenRouter API key not set. LLM calls will fail.")
        else:
            # Initialize OpenAI client with OpenRouter base URL
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=OPENROUTER_BASE_URL
            )
            logger.info(f"LLM service initialized with model: {self.model}")
    
    @staticmethod
    def is_configured() -> bool:
        """Check if the LLM service is properly configured.
        
        Returns:
            True if all required configuration is present, False otherwise.
        """
        return bool(OPENROUTER_API_KEY)
    
    def can_answer_with_context(
        self, 
        query: str, 
        context_entries: List[Dict[str, Any]], 
        similarity_threshold: float
    ) -> Dict[str, Any]:
        """Check if the given query can be fully answered with the provided context entries.
        
        Args:
            query: The natural language query to check.
            context_entries: List of context entries from the cache with similarity scores.
            similarity_threshold: The similarity threshold used for the original search.
            
        Returns:
            Dictionary containing:
                - can_answer (bool): Whether the query can be answered with the context.
                - explanation (str): Explanation of the decision.
                - updated_query (Optional[str]): If provided, an improved version of the template (sql query or url or api spec).
                - selected_entry_id (Optional[int]): ID of the entry determined to be most relevant.
        """
        if not self.api_key:
            logger.error("OpenRouter API key not set. Cannot make LLM call.")
            return {
                "can_answer": False,
                "explanation": "LLM service not properly configured."
            }
        
        # Prepare context information for the LLM
        context_text = ""
        for i, entry in enumerate(context_entries):
            similarity = entry.get("similarity", 0.0)
            context_text += f"Entry {i+1} (similarity: {similarity:.4f}):\n"
            context_text += f"Question: {entry.get('nl_query', '')}\n"
            context_text += f"Template: {entry.get('template', '')}\n"
            if entry.get("reasoning_trace"):
                context_text += f"Reasoning: {entry.get('reasoning_trace', '')}\n"
            context_text += f"ID: {entry.get('id')}\n\n"
        
        # Prepare prompt for the LLM using the imported prompt template
        prompt = QUERY_MATCHING_PROMPT.format(
            query=query,
            context_text=context_text,
            similarity_threshold=similarity_threshold
        )

        try:
            # Make the API call using the OpenAI client
            logger.info(f"Calling LLM with model: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # Extract content from the response
            content = response.choices[0].message.content
            logger.info(f"LLM response received successfully")
            
            # Parse the LLM response
            try:
                llm_output = json.loads(content)
                logger.info(f"Raw LLM output: {llm_output}")
                
                # Return all fields from LLM, don't filter based on can_answer
                result = {
                    "can_answer": llm_output.get("can_answer", False),
                    "explanation": llm_output.get("explanation", "No explanation provided."),
                    "updated_query": llm_output.get("updated_query"),  # Return as-is, even if None
                    "selected_entry_id": llm_output.get("selected_entry_id")  # Return as-is, even if None
                }
                logger.info(f"Processed LLM result: {result}")
                return result
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {e}")
                return {
                    "can_answer": False,
                    "explanation": f"Error parsing LLM response: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"LLM API request failed: {e}")
            return {
                "can_answer": False,
                "explanation": f"LLM service error: {str(e)}"
            }

    def generate_workflow(
        self,
        nl_query: str,
        compatible_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a workflow from a natural language query using available cache entries.
        
        Args:
            nl_query: The natural language query describing the desired workflow.
            compatible_entries: List of cache entries that can be used as workflow steps.
            
        Returns:
            Dictionary containing:
                - nodes: Array of workflow nodes
                - edges: Array of connections between nodes
                - workflow_template: The compiled workflow template
                - explanation: Explanation of how the workflow fulfills the request
        """
        if not self.api_key:
            logger.error("OpenRouter API key not set. Cannot generate workflow.")
            return self._generate_mock_workflow(nl_query, compatible_entries)
        
        try:
            # Create a description of available cache entries/steps
            entries_description = "\n\n".join([
                f"Step {i+1}:\nID: {entry['id']}\nDescription: {entry['nl_query']}\nType: {entry['template_type']}"
                for i, entry in enumerate(compatible_entries[:20])  # Limit to 20 entries to avoid token limits
            ])
            
            # Prepare prompt for workflow generation
            prompt = WORKFLOW_GENERATION_PROMPT.format(
                nl_query=nl_query,
                entries_description=entries_description
            )
            
            # Make the API call
            logger.info(f"Generating workflow for query: {nl_query}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a workflow designer that creates data processing workflows based on user requests."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            workflow_design = json.loads(response.choices[0].message.content)
            
            # Validate required fields
            required_fields = ["nodes", "edges", "workflow_template", "explanation"]
            if not all(field in workflow_design for field in required_fields):
                raise ValueError("LLM response missing required fields")
            
            return workflow_design
            
        except Exception as e:
            logger.error(f"Error generating workflow: {str(e)}")
            return self._generate_mock_workflow(nl_query, compatible_entries)

    def generate_reasoning_trace(
        self,
        nl_query: str,
        template: str,
        template_type: str
    ) -> str:
        """Generate a reasoning trace explaining how a template addresses a query.
        
        Args:
            nl_query: The natural language query.
            template: The template (SQL, URL, API spec, etc.).
            template_type: Type of template (sql, url, api, etc.).
            
        Returns:
            A string containing the reasoning trace.
        """
        if not self.api_key:
            logger.error("OpenRouter API key not set. Cannot generate reasoning trace.")
            return "LLM service not configured. Cannot generate reasoning trace."
        
        try:
            # Prepare prompt for reasoning trace generation
            prompt = REASONING_TRACE_PROMPT.format(
                nl_query=nl_query,
                template_type=template_type,
                template=template
            )
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that explains technical solutions clearly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating reasoning trace: {str(e)}")
            return f"Error generating reasoning trace: {str(e)}"

    def _generate_mock_workflow(
        self,
        nl_query: str,
        compatible_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a mock workflow for testing purposes.
        
        Args:
            nl_query: The natural language query.
            compatible_entries: List of available cache entries.
            
        Returns:
            A mock workflow design.
        """
        logger.warning("Using mock workflow generation since LLM service is not configured")
        
        # Create a simple mock workflow using the first two compatible entries
        mock_workflow = {
            "nodes": [
                {
                    "id": "step1",
                    "type": "cacheEntry",
                    "position": {"x": 100, "y": 100},
                    "data": {
                        "cacheEntryId": compatible_entries[0]["id"] if compatible_entries else 1,
                        "label": "First Step",
                        "description": compatible_entries[0]["nl_query"] if compatible_entries else "Mock Step 1"
                    }
                },
                {
                    "id": "step2",
                    "type": "cacheEntry",
                    "position": {"x": 400, "y": 100},
                    "data": {
                        "cacheEntryId": compatible_entries[1]["id"] if len(compatible_entries) > 1 else 2,
                        "label": "Second Step",
                        "description": compatible_entries[1]["nl_query"] if len(compatible_entries) > 1 else "Mock Step 2"
                    }
                }
            ],
            "edges": [
                {
                    "id": "e1-2",
                    "source": "step1",
                    "target": "step2",
                    "label": "Data Flow"
                }
            ],
            "workflow_template": {
                "steps": [
                    {
                        "id": "step1",
                        "cache_entry_id": compatible_entries[0]["id"] if compatible_entries else 1,
                        "description": "First step in the workflow"
                    },
                    {
                        "id": "step2",
                        "cache_entry_id": compatible_entries[1]["id"] if len(compatible_entries) > 1 else 2,
                        "description": "Second step in the workflow"
                    }
                ],
                "connections": [
                    {
                        "from": "step1",
                        "to": "step2",
                        "description": "Pass data from step1 to step2"
                    }
                ]
            },
            "explanation": "This is a mock workflow generated because the LLM service is not properly configured."
        }
        
        return mock_workflow 