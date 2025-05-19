"""
Prompt templates for LLM interactions.
These prompts are used by the LLMService to generate various types of responses.
"""

# Prompt for checking if a query can be answered using existing cache entries
QUERY_MATCHING_PROMPT = """
Given the following natural language query and a set of cached entries, determine if any of the entries can fully answer the query.

Query: {query}

Available cached entries:
{context_text}

Similarity threshold: {similarity_threshold}

Please analyze if any of the cached entries can fully answer the query. Consider:
1. Semantic similarity between the query and cached entries
2. Whether the cached entry's template can be used as-is or with minor modifications
3. If entity substitutions would be needed

Respond with a JSON object containing:
{{
    "can_answer": boolean,  // Whether any cached entry can answer the query
    "explanation": string,  // Explanation of your decision
    "updated_query": string | null,  // If provided, an improved version of the query
    "selected_entry_id": number | null  // ID of the entry that best matches, if any
}}
"""

# Prompt for generating a workflow from a natural language query
WORKFLOW_GENERATION_PROMPT = """
Create a workflow to fulfill this request: "{nl_query}"

Available steps:
{entries_description}

Design a workflow that:
1. Uses the most appropriate steps from the available options
2. Connects them in a logical sequence
3. Handles data flow between steps
4. Includes any necessary modifications to the steps

Respond with a JSON object containing:
{{
    "nodes": [
        {{
            "id": string,  // Unique identifier for the node
            "type": "cacheEntry",  // Type of node
            "position": {{"x": number, "y": number}},  // Position in the workflow diagram
            "data": {{
                "cacheEntryId": number,  // ID of the cache entry to use
                "label": string,  // Display label for the node
                "description": string  // Description of what this step does
            }}
        }}
    ],
    "edges": [
        {{
            "id": string,  // Unique identifier for the edge
            "source": string,  // ID of the source node
            "target": string,  // ID of the target node
            "label": string  // Description of the data flow
        }}
    ],
    "workflow_template": {{
        "steps": [
            {{
                "id": string,  // Step identifier
                "cache_entry_id": number,  // ID of the cache entry
                "description": string,  // What this step does
                "input_modifications": string | null,  // Any modifications needed for inputs
                "outputs": string[]  // What this step produces
            }}
        ],
        "connections": [
            {{
                "from": string,  // Source step ID
                "to": string,  // Target step ID
                "description": string  // How data flows between steps
            }}
        ]
    }},
    "explanation": string  // Explanation of how this workflow fulfills the request
}}
"""

# Prompt for generating a reasoning trace
REASONING_TRACE_PROMPT = """
Explain how the following template addresses the natural language query.

Query: {nl_query}

Template Type: {template_type}

Template:
{template}

Provide a clear explanation that:
1. Breaks down how the template works
2. Shows how it addresses the query's requirements
3. Explains any assumptions or context needed
4. Highlights any important features or considerations

Your explanation should be clear and technical, but accessible to someone familiar with {template_type}.
""" 