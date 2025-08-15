"""
LLM Step Processor for ThinkForge

This module handles the execution of custom LLM-powered steps in recipes.
It processes LLM step templates, validates inputs, executes prompts, and formats outputs.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import jsonschema
from jsonschema import validate, ValidationError

# Import the LLM service for actual execution
try:
    from backend.llm_service import LLMService
except ImportError:
    # Fallback for when running from different contexts
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))
        from llm_service import LLMService
    except ImportError:
        LLMService = None

logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """Supported output formats for LLM steps."""
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


class ValidationAction(str, Enum):
    """Actions to take when validation fails."""
    RETRY = "retry"
    FALLBACK = "fallback"
    FAIL = "fail"


@dataclass
class LLMStepConfig:
    """Configuration for an LLM step."""
    prompt_template: str
    input_parameters: List[str]
    output_format: OutputFormat
    expected_output: Dict[str, Any]
    model: str = "google/gemini-pro"
    temperature: float = 0.3
    max_tokens: int = 500
    system_prompt: Optional[str] = None


@dataclass
class ValidationRules:
    """Validation rules for LLM step outputs."""
    required_fields: List[str]
    validation_schema: Dict[str, Any]
    fallback_handling: Dict[str, Any]


@dataclass
class LLMStepResult:
    """Result of executing an LLM step."""
    success: bool
    output: Any
    raw_response: str
    error_message: Optional[str] = None
    validation_passed: bool = True
    execution_metadata: Dict[str, Any] = None


class LLMStepProcessor:
    """Processor for executing LLM steps in recipes."""
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize the LLM step processor.
        
        Args:
            llm_service: Optional LLM service instance. If not provided, creates one.
        """
        self.llm_service = llm_service or (LLMService() if LLMService else None)
        if not self.llm_service:
            logger.warning("LLM service not available. LLM steps will fail.")
    
    def execute_llm_step(
        self, 
        step_template: Dict[str, Any], 
        input_values: Dict[str, Any]
    ) -> LLMStepResult:
        """Execute an LLM step with the given input values.
        
        Args:
            step_template: The LLM step template JSON structure
            input_values: Dictionary of input parameter values
            
        Returns:
            LLMStepResult with execution results
        """
        try:
            # Parse and validate the step template
            step_config = self._parse_step_config(step_template)
            validation_rules = self._parse_validation_rules(step_template)
            
            # Validate input parameters
            validation_result = self._validate_input_parameters(
                step_config.input_parameters, 
                input_values
            )
            if not validation_result["valid"]:
                return LLMStepResult(
                    success=False,
                    output=None,
                    raw_response="",
                    error_message=f"Input validation failed: {validation_result['error']}"
                )
            
            # Format the prompt with input values
            formatted_prompt = self._format_prompt(step_config.prompt_template, input_values)
            
            # Execute the LLM call
            llm_response = self._execute_llm_call(
                formatted_prompt,
                step_config.model,
                step_config.temperature,
                step_config.max_tokens,
                step_config.system_prompt
            )
            
            if not llm_response["success"]:
                return LLMStepResult(
                    success=False,
                    output=None,
                    raw_response="",
                    error_message=llm_response["error"]
                )
            
            # Format the output according to the specified format
            formatted_output = self._format_output(
                llm_response["response"],
                step_config.output_format,
                step_config.expected_output
            )
            
            # Validate the output
            validation_passed = self._validate_output(
                formatted_output["output"],
                validation_rules
            )
            
            # Handle validation failures
            if not validation_passed and validation_rules:
                return self._handle_validation_failure(
                    formatted_output["output"],
                    validation_rules,
                    step_template,
                    input_values
                )
            
            return LLMStepResult(
                success=True,
                output=formatted_output["output"],
                raw_response=llm_response["response"],
                validation_passed=validation_passed,
                execution_metadata={
                    "model": step_config.model,
                    "temperature": step_config.temperature,
                    "max_tokens": step_config.max_tokens,
                    "formatted_prompt": formatted_prompt
                }
            )
            
        except Exception as e:
            logger.error(f"Error executing LLM step: {str(e)}")
            return LLMStepResult(
                success=False,
                output=None,
                raw_response="",
                error_message=f"Execution error: {str(e)}"
            )
    
    def _parse_step_config(self, step_template: Dict[str, Any]) -> LLMStepConfig:
        """Parse the step configuration from the template."""
        config = step_template.get("step_config", {})
        
        return LLMStepConfig(
            prompt_template=config.get("prompt_template", ""),
            input_parameters=config.get("input_parameters", []),
            output_format=OutputFormat(config.get("output_format", "json")),
            expected_output=config.get("expected_output", {}),
            model=config.get("model", "google/gemini-pro"),
            temperature=float(config.get("temperature", 0.3)),
            max_tokens=int(config.get("max_tokens", 500)),
            system_prompt=config.get("system_prompt")
        )
    
    def _parse_validation_rules(self, step_template: Dict[str, Any]) -> Optional[ValidationRules]:
        """Parse validation rules from the template."""
        rules = step_template.get("validation_rules")
        if not rules:
            return None
            
        return ValidationRules(
            required_fields=rules.get("required_fields", []),
            validation_schema=rules.get("validation_schema", {}),
            fallback_handling=rules.get("fallback_handling", {})
        )
    
    def _validate_input_parameters(
        self, 
        required_params: List[str], 
        input_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate that all required input parameters are provided."""
        missing_params = [param for param in required_params if param not in input_values]
        
        if missing_params:
            return {
                "valid": False,
                "error": f"Missing required parameters: {', '.join(missing_params)}"
            }
        
        return {"valid": True}
    
    def _format_prompt(self, template: str, input_values: Dict[str, Any]) -> str:
        """Format the prompt template with input values."""
        try:
            # Use string formatting to replace {parameter} placeholders
            return template.format(**input_values)
        except KeyError as e:
            raise ValueError(f"Missing parameter for prompt formatting: {e}")
        except Exception as e:
            raise ValueError(f"Error formatting prompt: {e}")
    
    def _execute_llm_call(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute the actual LLM call."""
        if not self.llm_service:
            return {
                "success": False,
                "error": "LLM service not available"
            }
        
        try:
            # Prepare messages for the LLM
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Make the API call using the LLM service's client
            response = self.llm_service.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            return {
                "success": False,
                "error": f"LLM API call failed: {str(e)}"
            }
    
    def _format_output(
        self, 
        raw_response: str, 
        output_format: OutputFormat, 
        expected_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format the LLM response according to the specified output format."""
        try:
            if output_format == OutputFormat.JSON:
                # Try to parse as JSON
                try:
                    parsed = json.loads(raw_response)
                    return {"success": True, "output": parsed}
                except json.JSONDecodeError:
                    # If direct parsing fails, try to extract JSON from the response
                    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            return {"success": True, "output": parsed}
                        except json.JSONDecodeError:
                            pass
                    
                    # Fallback: create structured output from text
                    return self._create_fallback_json(raw_response, expected_output)
            
            elif output_format == OutputFormat.STRUCTURED:
                # Try to parse as JSON first, fallback to structured text parsing
                try:
                    parsed = json.loads(raw_response)
                    return {"success": True, "output": parsed}
                except json.JSONDecodeError:
                    return self._parse_structured_text(raw_response, expected_output)
            
            else:  # TEXT format
                return {"success": True, "output": raw_response}
                
        except Exception as e:
            logger.error(f"Error formatting output: {str(e)}")
            return {"success": False, "output": raw_response, "error": str(e)}
    
    def _create_fallback_json(
        self, 
        raw_response: str, 
        expected_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a fallback JSON structure when direct parsing fails."""
        result = {}
        
        # Try to extract values for expected fields
        for field, field_type in expected_output.items():
            if isinstance(field_type, str):
                # Simple heuristic extraction based on field names
                if "classification" in field.lower() or "category" in field.lower():
                    # Look for classification keywords
                    for line in raw_response.split('\n'):
                        if any(word in line.lower() for word in ['class', 'category', 'type']):
                            result[field] = line.strip()
                            break
                    else:
                        result[field] = raw_response.split('\n')[0].strip()
                
                elif "confidence" in field.lower():
                    # Look for numeric confidence values
                    confidence_match = re.search(r'(\d+(?:\.\d+)?)', raw_response)
                    if confidence_match:
                        result[field] = float(confidence_match.group(1))
                    else:
                        result[field] = 0.8  # Default confidence
                
                else:
                    result[field] = raw_response.strip()
        
        return {"success": True, "output": result}
    
    def _parse_structured_text(
        self, 
        raw_response: str, 
        expected_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse structured text into the expected output format."""
        result = {}
        lines = raw_response.split('\n')
        
        for field in expected_output.keys():
            for line in lines:
                if field.lower() in line.lower():
                    # Extract value after colon or similar delimiter
                    if ':' in line:
                        value = line.split(':', 1)[1].strip()
                        result[field] = value
                    break
            else:
                # If field not found, use a default or the raw response
                result[field] = raw_response.strip()
        
        return {"success": True, "output": result}
    
    def _validate_output(
        self, 
        output: Any, 
        validation_rules: Optional[ValidationRules]
    ) -> bool:
        """Validate the formatted output against the validation rules."""
        if not validation_rules:
            return True
        
        try:
            # Check required fields
            if isinstance(output, dict):
                missing_fields = [
                    field for field in validation_rules.required_fields 
                    if field not in output
                ]
                if missing_fields:
                    logger.warning(f"Missing required fields in output: {missing_fields}")
                    return False
            
            # Validate against JSON schema if provided
            if validation_rules.validation_schema:
                validate(instance=output, schema=validation_rules.validation_schema)
            
            return True
            
        except ValidationError as e:
            logger.warning(f"Output validation failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error during output validation: {str(e)}")
            return False
    
    def _handle_validation_failure(
        self,
        output: Any,
        validation_rules: ValidationRules,
        step_template: Dict[str, Any],
        input_values: Dict[str, Any]
    ) -> LLMStepResult:
        """Handle validation failures according to the fallback rules."""
        fallback_handling = validation_rules.fallback_handling
        action = fallback_handling.get("on_validation_error", "fail")
        
        if action == ValidationAction.FALLBACK:
            fallback_response = fallback_handling.get("fallback_response", {})
            return LLMStepResult(
                success=True,
                output=fallback_response,
                raw_response="",
                validation_passed=False,
                error_message="Used fallback response due to validation failure"
            )
        
        elif action == ValidationAction.RETRY:
            max_retries = fallback_handling.get("max_retries", 1)
            # For now, we'll just return the original output
            # In a full implementation, you might implement retry logic
            logger.info(f"Would retry up to {max_retries} times")
            return LLMStepResult(
                success=False,
                output=output,
                raw_response="",
                validation_passed=False,
                error_message="Output validation failed and retry not implemented"
            )
        
        else:  # FAIL
            return LLMStepResult(
                success=False,
                output=output,
                raw_response="",
                validation_passed=False,
                error_message="Output validation failed"
            )
    
    def test_llm_step(
        self, 
        step_template: Dict[str, Any], 
        test_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Test an LLM step with example inputs.
        
        Args:
            step_template: The LLM step template
            test_inputs: Optional test input values. If not provided, uses examples from template.
            
        Returns:
            Test result with success status and output
        """
        try:
            # Use provided test inputs or extract from examples
            if test_inputs:
                input_values = test_inputs
            else:
                examples = step_template.get("examples", [])
                if examples:
                    input_values = examples[0].get("input_values", {})
                else:
                    # Create dummy inputs based on parameter names
                    step_config = self._parse_step_config(step_template)
                    input_values = {
                        param: f"test_{param}" for param in step_config.input_parameters
                    }
            
            # Execute the step
            result = self.execute_llm_step(step_template, input_values)
            
            return {
                "success": result.success,
                "output": result.output,
                "raw_response": result.raw_response,
                "validation_passed": result.validation_passed,
                "error_message": result.error_message,
                "test_inputs": input_values,
                "execution_metadata": result.execution_metadata
            }
            
        except Exception as e:
            return {
                "success": False,
                "error_message": f"Test execution failed: {str(e)}",
                "test_inputs": test_inputs
            }


def create_sample_llm_step_template() -> Dict[str, Any]:
    """Create a sample LLM step template for testing and demonstration."""
    return {
        "step_config": {
            "prompt_template": "Analyze this support ticket and classify its urgency level: {ticket_text}\n\nClassify as: low, medium, high, or critical\n\nProvide your response in JSON format with fields: urgency, reasoning, and suggested_action.",
            "input_parameters": ["ticket_text"],
            "output_format": "json",
            "expected_output": {
                "urgency": "string",
                "reasoning": "string", 
                "suggested_action": "string"
            },
            "model": "google/gemini-pro",
            "temperature": 0.2,
            "max_tokens": 300,
            "system_prompt": "You are a customer support triage assistant. Analyze support tickets and classify their urgency accurately."
        },
        "validation_rules": {
            "required_fields": ["urgency", "reasoning"],
            "validation_schema": {
                "type": "object",
                "properties": {
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "reasoning": {"type": "string"},
                    "suggested_action": {"type": "string"}
                },
                "required": ["urgency", "reasoning"]
            },
            "fallback_handling": {
                "on_validation_error": "fallback",
                "max_retries": 2,
                "fallback_response": {
                    "urgency": "medium",
                    "reasoning": "Unable to classify - requires manual review",
                    "suggested_action": "Forward to human agent"
                }
            }
        },
        "examples": [
            {
                "name": "Server outage ticket",
                "description": "Critical system failure requiring immediate attention",
                "input_values": {
                    "ticket_text": "URGENT: Production server is down, all customers affected, revenue impact significant"
                },
                "expected_output": {
                    "urgency": "critical",
                    "reasoning": "Production system failure with customer and revenue impact",
                    "suggested_action": "Escalate immediately to engineering team"
                }
            }
        ]
    }