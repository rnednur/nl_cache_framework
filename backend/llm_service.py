import os
import logging
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

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
                - updated_query (Optional[str]): If provided, an improved version of the query.
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
        
        # Prepare prompt for the LLM
        prompt = f"""You are an expert in determining whether a user's question can be answered using existing cached entries by translating or adapting the query when possible.

Original user question: "{query}"

Cached entries (sorted by similarity):
{context_text}

Similarity threshold: {similarity_threshold}

Your task is to determine if the original question can be fully and accurately answered using any of these cached entries, even if slight modifications are needed. 
Consider:
1. Does the user question ask for the same fundamental information as any cached entry, even if parameters (like numbers, dates, or specific terms) differ?
2. Are there any minor differences in intent, scope, or specificity that can be resolved by adapting the cached entry or reformulating the user question?
3. If there's a close match, could the user question be slightly reformulated or the parameters adjusted to match the cached entry while preserving the core intent?

Output a JSON object with the following fields:
- can_answer: true/false
- explanation: brief explanation of your decision
- updated_query: [if can_answer=true or if adaptation is possible] an updated version of the sql query that better matches the input question and cached entry, adjusting parameters if needed
- selected_entry_id: [if can_answer=true] the ID of the most appropriate entry

Return ONLY the JSON object and nothing else."""

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
                return {
                    "can_answer": llm_output.get("can_answer", False),
                    "explanation": llm_output.get("explanation", "No explanation provided."),
                    "updated_query": llm_output.get("updated_query") if llm_output.get("can_answer") else None,
                    "selected_entry_id": llm_output.get("selected_entry_id") if llm_output.get("can_answer") else None
                }
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