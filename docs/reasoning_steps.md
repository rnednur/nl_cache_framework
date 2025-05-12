# Reasoning Steps Template Type

The `reasoning_steps` template type is designed to capture step-by-step logical reasoning or problem-solving approaches. This can be used for documenting thought processes, mathematical proofs, or decision trees.

## Purpose

The primary purpose of this template type is to:

1. Document logical reasoning steps for complex problems
2. Store step-by-step solutions for common questions
3. Support educational use cases that require detailed explanation
4. Capture structured thinking approaches

## Format

Reasoning steps can be formatted in various ways, including:

- Numbered steps
- Markdown formatted text with headers for each step
- JSON structured format with steps and explanations
- Plain text with clear separations between steps

## Example

```
Step 1: Identify the entities in the problem
- Property types: houses and apartments
- Constraint: must have more than 1 room

Step 2: Determine the query structure
- Need to retrieve property names
- Need to filter based on property type
- Need to filter based on room count

Step 3: Construct the SQL query
- SELECT property_name FROM Properties
- WHERE property_type_code is either "House" or "Apartment"
- AND room_count > 1
```

## Integration with LLM Enhancement

When using LLM enhancement, reasoning steps can be used to:

1. Guide the LLM's response by providing a reasoning template
2. Store the LLM's reasoning traces for future reference
3. Help users understand how a particular solution was derived

## Creating Reasoning Steps Templates

When creating a reasoning steps template:

1. Break down the reasoning into clear, distinct steps
2. Use consistent formatting throughout
3. Reference specific entities in a way that makes substitution straightforward
4. Include explanations where appropriate

## Usage in API

When using the `/complete` endpoint, you can specify:

```json
{
  "prompt": "What are the names of properties that are either houses or apartments with more than 1 room?",
  "use_llm": true,
  "catalog_type": "real_estate",
  "template_type": "reasoning_steps"
}
``` 