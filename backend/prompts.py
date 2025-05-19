"""
This module contains all the prompts used for LLM interactions in the application.
"""

# Prompt used in llm_service.py to determine if a query can be answered with cached entries
QUERY_MATCHING_PROMPT = """You are an expert in determining whether a user's question can be answered using existing cached entries by translating or adapting the query when possible.

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

# Prompt used in app.py to generate reasoning traces
REASONING_TRACE_PROMPT = """You are an expert in explaining how database queries, APIs, or other templates address natural language questions.

Natural Language Query: "{nl_query}"

Template ({template_type}): 
{template}

Provide a clear, concise explanation of how this template addresses the natural language query. 
Explain the logic, approach, and any transformations or calculations involved.
Focus on helping a non-technical user understand the relationship between their question and the provided solution.

Your explanation should be:
1. Clear and concise (2-4 paragraphs)
2. Technically accurate
3. Focused on how the template addresses the specific query
""" 