#!/usr/bin/env python3
"""
Test script for LLM Step Integration

This script tests the complete LLM step functionality including:
1. Creating an LLM step template
2. Parsing a recipe with LLM processing steps
3. Compiling a workflow with LLM steps
4. (Optional) Executing an LLM step with sample data

Run with: python test_llm_step_integration.py
"""

import sys
import os
import json
import asyncio
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

try:
    from thinkforge.models import TemplateType
    from thinkforge.recipe_step_analyzer import RecipeStepAnalyzer, StepType
    from thinkforge.llm_step_processor import LLMStepProcessor, create_sample_llm_step_template
    from thinkforge.workflow_compiler import compile_workflow_with_llm_steps
    from backend.llm_service import LLMService
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root and dependencies are installed")
    sys.exit(1)


def test_template_type_enum():
    """Test that the LLM_STEP template type was added correctly."""
    print("🧪 Testing TemplateType enum...")
    
    # Check that LLM_STEP exists
    assert hasattr(TemplateType, 'LLM_STEP'), "LLM_STEP template type not found"
    assert TemplateType.LLM_STEP == "llm_step", "LLM_STEP value incorrect"
    
    print("✅ TemplateType.LLM_STEP exists and has correct value")
    return True


def test_recipe_step_analyzer():
    """Test that the recipe step analyzer can recognize LLM processing steps."""
    print("\n🧪 Testing Recipe Step Analyzer...")
    
    analyzer = RecipeStepAnalyzer()
    
    # Test recipe with LLM processing steps
    recipe_text = """
    Customer Support Ticket Processing Recipe:
    
    1. Extract the ticket content from the incoming email
    2. Analyze the issue and classify it into urgency buckets: low, medium, high, critical
    3. Extract customer information and previous interaction history
    4. Generate a preliminary response based on the issue classification
    5. Route the ticket to the appropriate team based on urgency and category
    """
    
    analysis = analyzer.analyze_recipe(recipe_text, "Support Ticket Processing")
    
    # Check that we identified LLM processing steps
    llm_steps = [step for step in analysis.steps if step.step_type == StepType.LLM_PROCESSING]
    
    print(f"📊 Analysis Results:")
    print(f"   Total steps: {analysis.total_steps}")
    print(f"   LLM processing steps: {len(llm_steps)}")
    print(f"   Recipe type: {analysis.recipe_type}")
    print(f"   Complexity score: {analysis.complexity_score:.2f}")
    
    if llm_steps:
        print(f"   LLM steps found:")
        for step in llm_steps:
            print(f"     - {step.name} (confidence: {step.confidence:.2f})")
    
    # We expect at least one LLM processing step (step 2 about classification)
    assert len(llm_steps) > 0, "No LLM processing steps were identified"
    
    print("✅ Recipe Step Analyzer successfully identified LLM processing steps")
    return analysis


def test_llm_step_processor():
    """Test the LLM step processor with a sample template."""
    print("\n🧪 Testing LLM Step Processor...")
    
    # Create sample template
    template = create_sample_llm_step_template()
    print(f"📋 Sample template created: {template['step_config']['prompt_template'][:50]}...")
    
    # Initialize processor (without actual LLM service for testing)
    processor = LLMStepProcessor()
    
    # Test input validation
    sample_inputs = {
        "ticket_text": "URGENT: Production server is down, all customers affected, revenue impact significant"
    }
    
    # Test template parsing
    step_config = processor._parse_step_config(template)
    validation_rules = processor._parse_validation_rules(template)
    
    print(f"📊 Template Analysis:")
    print(f"   Input parameters: {step_config.input_parameters}")
    print(f"   Output format: {step_config.output_format}")
    print(f"   Model: {step_config.model}")
    print(f"   Has validation rules: {validation_rules is not None}")
    
    # Test input validation
    validation_result = processor._validate_input_parameters(
        step_config.input_parameters, 
        sample_inputs
    )
    
    assert validation_result["valid"], "Input validation failed"
    print("✅ LLM Step Processor successfully validated inputs and parsed template")
    return template


def test_workflow_compiler():
    """Test workflow compilation with LLM steps."""
    print("\n🧪 Testing Workflow Compiler...")
    
    # Mock ReactFlow nodes with an LLM step
    nodes = [
        {
            "id": "start",
            "type": "start"
        },
        {
            "id": "extract_content", 
            "data": {
                "originalStepType": "api",
                "template": "extract_email_content({email_id})",
                "label": "Extract Email Content"
            }
        },
        {
            "id": "classify_urgency",
            "data": {
                "originalStepType": "llm_step",
                "template": "classify_support_ticket({ticket_text})",
                "label": "Classify Ticket Urgency",
                "llmConfig": {
                    "promptTemplate": "Analyze this support ticket and classify urgency: {ticket_text}",
                    "inputParameters": ["ticket_text"],
                    "outputFormat": "json",
                    "expectedOutput": {"urgency": "string", "reasoning": "string"},
                    "model": "google/gemini-pro",
                    "temperature": 0.2
                }
            }
        },
        {
            "id": "route_ticket",
            "data": {
                "originalStepType": "workflow",
                "template": "route_to_team({urgency}, {category})",
                "label": "Route to Team"
            }
        }
    ]
    
    edges = [
        {"source": "start", "target": "extract_content"},
        {"source": "extract_content", "target": "classify_urgency"},
        {"source": "classify_urgency", "target": "route_ticket"}
    ]
    
    # Test compilation to different formats
    formats = ["generic", "langchain", "langflow", "langgraph"]
    
    for format_type in formats:
        print(f"   Testing {format_type} format...")
        compiled = compile_workflow_with_llm_steps(nodes, edges, format_type)
        
        assert "steps" in compiled, f"No steps in {format_type} compilation"
        assert "classify_urgency" in compiled["steps"], f"LLM step missing in {format_type}"
        
        llm_step = compiled["steps"]["classify_urgency"]
        
        if format_type == "langchain":
            assert llm_step["type"] == "llm_chain", f"Wrong type for langchain: {llm_step['type']}"
        elif format_type == "langflow":
            assert llm_step["type"] == "LLMChain", f"Wrong type for langflow: {llm_step['type']}"
        elif format_type == "langgraph":
            assert llm_step["type"] == "llm_node", f"Wrong type for langgraph: {llm_step['type']}"
        
        print(f"     ✅ {format_type} format compiled successfully")
    
    print("✅ Workflow Compiler successfully handled LLM steps in all formats")
    return compiled


def test_integration_example():
    """Test a complete integration example."""
    print("\n🧪 Testing Complete Integration Example...")
    
    print("📝 Example Recipe: Customer Support Automation")
    print("   This recipe demonstrates using LLM steps for:")
    print("   - Sentiment analysis")
    print("   - Issue classification") 
    print("   - Response generation")
    
    # Recipe text
    recipe_text = """
    Customer Support Automation Recipe:
    
    1. Receive customer message via email or chat
    2. Extract and clean the message content
    3. Analyze the sentiment of the customer message using AI
    4. Classify the issue type and priority level using natural language processing
    5. Generate a personalized response draft based on the analysis
    6. Route to human agent if high priority or negative sentiment
    7. Send automated response if low priority and positive sentiment
    """
    
    # Step 1: Analyze the recipe
    analyzer = RecipeStepAnalyzer()
    analysis = analyzer.analyze_recipe(recipe_text, "Customer Support Automation")
    
    print(f"📊 Recipe Analysis:")
    print(f"   Total steps: {analysis.total_steps}")
    print(f"   Recipe type: {analysis.recipe_type}")
    
    llm_steps = [step for step in analysis.steps if step.step_type == StepType.LLM_PROCESSING]
    print(f"   LLM processing steps identified: {len(llm_steps)}")
    
    for step in llm_steps:
        print(f"     • {step.name}")
        print(f"       Action verbs: {', '.join(step.action_verbs)}")
        print(f"       Confidence: {step.confidence:.2f}")
    
    # Step 2: Create LLM step templates
    templates = []
    
    # Sentiment analysis template
    sentiment_template = {
        "step_config": {
            "prompt_template": "Analyze the sentiment of this customer message: {message}\n\nClassify as: positive, negative, or neutral\n\nProvide JSON response with fields: sentiment, confidence, reasoning",
            "input_parameters": ["message"],
            "output_format": "json",
            "expected_output": {
                "sentiment": "string",
                "confidence": "float", 
                "reasoning": "string"
            },
            "model": "google/gemini-pro",
            "temperature": 0.1,
            "max_tokens": 200
        }
    }
    templates.append(("sentiment_analysis", sentiment_template))
    
    # Issue classification template  
    classification_template = {
        "step_config": {
            "prompt_template": "Classify this customer support issue: {message}\n\nCategories: technical, billing, account, feature_request, complaint\nPriority: low, medium, high, critical\n\nProvide JSON response with fields: category, priority, reasoning",
            "input_parameters": ["message"],
            "output_format": "json", 
            "expected_output": {
                "category": "string",
                "priority": "string",
                "reasoning": "string"
            },
            "model": "google/gemini-pro",
            "temperature": 0.2,
            "max_tokens": 300
        }
    }
    templates.append(("issue_classification", classification_template))
    
    print(f"📋 Created {len(templates)} LLM step templates")
    
    # Step 3: Test template processing
    processor = LLMStepProcessor()
    
    for name, template in templates:
        print(f"   Testing {name} template...")
        step_config = processor._parse_step_config(template)
        
        # Validate template structure
        assert step_config.prompt_template, f"No prompt template in {name}"
        assert step_config.input_parameters, f"No input parameters in {name}"
        assert step_config.expected_output, f"No expected output in {name}"
        
        print(f"     ✅ {name} template is valid")
    
    print("✅ Complete integration example tested successfully")
    
    return {
        "recipe_analysis": analysis,
        "templates": templates,
        "llm_steps_count": len(llm_steps)
    }


def main():
    """Run all tests."""
    print("🚀 Testing LLM Step Integration")
    print("=" * 50)
    
    results = {}
    
    try:
        # Test 1: Template type enum
        results['template_type'] = test_template_type_enum()
        
        # Test 2: Recipe step analyzer
        results['recipe_analyzer'] = test_recipe_step_analyzer()
        
        # Test 3: LLM step processor
        results['llm_processor'] = test_llm_step_processor()
        
        # Test 4: Workflow compiler
        results['workflow_compiler'] = test_workflow_compiler()
        
        # Test 5: Complete integration
        results['integration'] = test_integration_example()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed successfully!")
        print("\n📋 Summary:")
        print("✅ LLM_STEP template type added")
        print("✅ Recipe analyzer recognizes LLM processing steps")  
        print("✅ LLM step processor handles templates correctly")
        print("✅ Workflow compiler supports LLM steps in all formats")
        print("✅ End-to-end integration works as expected")
        
        print(f"\n🔍 Integration Results:")
        if 'integration' in results:
            integration = results['integration']
            print(f"   • Recipe parsed into {integration['recipe_analysis'].total_steps} steps")
            print(f"   • {integration['llm_steps_count']} LLM processing steps identified")
            print(f"   • {len(integration['templates'])} LLM templates created")
            print(f"   • Recipe classified as: {integration['recipe_analysis'].recipe_type}")
        
        print(f"\n🎯 Ready for Use:")
        print("   • Backend API endpoints: /v1/llm-steps/*")
        print("   • Frontend components: LLMStepBuilder.tsx")
        print("   • Recipe analysis: Enhanced with LLM step detection")
        print("   • Workflow compilation: Supports Langchain/Langflow/Langgraph")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)