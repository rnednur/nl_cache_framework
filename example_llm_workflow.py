#!/usr/bin/env python3
"""
Example: LLM Workflow Integration

This example demonstrates how LLM steps work within the ThinkForge workflow execution framework.
It shows a complete customer support workflow with LLM-powered sentiment analysis and issue classification.
"""

import asyncio
import json
from typing import Dict, Any

# Sample workflow configuration with LLM steps
CUSTOMER_SUPPORT_WORKFLOW = {
    "name": "Customer Support Automation",
    "steps": {
        "extract_content": {
            "id": "extract_content",
            "templateType": "api",
            "inputs": {
                "template": "GET /api/tickets/{ticket_id}/content",
                "method": "GET"
            },
            "dependencies": [],
            "outputKey": "ticket_content",
            "metadata": {
                "label": "Extract Ticket Content",
                "catalogType": "api",
                "catalogSubtype": "ticket_management"
            }
        },
        "analyze_sentiment": {
            "id": "analyze_sentiment", 
            "templateType": "llm_step",
            "inputs": {
                "prompt_template": "Analyze the sentiment of this customer support ticket: {ticket_text}\n\nClassify as: positive, negative, or neutral\n\nProvide JSON response with fields: sentiment, confidence, reasoning",
                "input_parameters": ["ticket_text"],
                "output_format": "json",
                "expected_output": {
                    "sentiment": "string",
                    "confidence": "float",
                    "reasoning": "string"
                },
                "model": "google/gemini-pro",
                "temperature": 0.1,
                "max_tokens": 200,
                "system_prompt": "You are a customer support sentiment analyzer. Provide accurate, unbiased sentiment analysis."
            },
            "dependencies": ["extract_content"],
            "outputKey": "sentiment_analysis",
            "metadata": {
                "label": "Analyze Customer Sentiment",
                "llmConfig": {
                    "promptTemplate": "Analyze the sentiment of this customer support ticket: {ticket_text}\n\nClassify as: positive, negative, or neutral\n\nProvide JSON response with fields: sentiment, confidence, reasoning",
                    "inputParameters": ["ticket_text"],
                    "outputFormat": "json",
                    "expectedOutput": {
                        "sentiment": "string",
                        "confidence": "float", 
                        "reasoning": "string"
                    },
                    "model": "google/gemini-pro",
                    "temperature": 0.1,
                    "maxTokens": 200,
                    "systemPrompt": "You are a customer support sentiment analyzer. Provide accurate, unbiased sentiment analysis."
                }
            }
        },
        "classify_issue": {
            "id": "classify_issue",
            "templateType": "llm_step", 
            "inputs": {
                "prompt_template": "Classify this customer support issue: {ticket_text}\n\nCategories: technical, billing, account, feature_request, complaint\nPriority: low, medium, high, critical\n\nProvide JSON response with fields: category, priority, reasoning, suggested_team",
                "input_parameters": ["ticket_text"],
                "output_format": "json",
                "expected_output": {
                    "category": "string",
                    "priority": "string", 
                    "reasoning": "string",
                    "suggested_team": "string"
                },
                "model": "google/gemini-pro",
                "temperature": 0.2,
                "max_tokens": 300
            },
            "dependencies": ["extract_content"],
            "outputKey": "issue_classification",
            "metadata": {
                "label": "Classify Issue Type and Priority"
            }
        },
        "route_ticket": {
            "id": "route_ticket",
            "templateType": "workflow",
            "inputs": {
                "template": json.dumps({
                    "steps": [
                        {
                            "id": "route_decision",
                            "cache_entry_id": 123,
                            "description": "Route ticket to appropriate team based on classification"
                        }
                    ]
                })
            },
            "dependencies": ["analyze_sentiment", "classify_issue"],
            "outputKey": "routing_result",
            "metadata": {
                "label": "Route to Team"
            }
        }
    },
    "executionPlan": [
        {
            "mode": "sequential",
            "steps": ["extract_content"]
        },
        {
            "mode": "parallel", 
            "steps": ["analyze_sentiment", "classify_issue"]
        },
        {
            "mode": "sequential",
            "steps": ["route_ticket"]
        }
    ]
}

# Sample ReactFlow nodes for workflow compilation 
REACTFLOW_NODES = [
    {
        "id": "start",
        "type": "start"
    },
    {
        "id": "extract_content",
        "data": {
            "originalStepType": "api",
            "template": "GET /api/tickets/{ticket_id}/content",
            "label": "Extract Ticket Content"
        }
    },
    {
        "id": "analyze_sentiment",
        "data": {
            "originalStepType": "llm_step",
            "template": "analyze_sentiment({ticket_text})",
            "label": "Analyze Customer Sentiment",
            "llmConfig": {
                "promptTemplate": "Analyze the sentiment of this customer support ticket: {ticket_text}\\n\\nClassify as: positive, negative, or neutral\\n\\nProvide JSON response with fields: sentiment, confidence, reasoning",
                "inputParameters": ["ticket_text"],
                "outputFormat": "json",
                "expectedOutput": {
                    "sentiment": "string",
                    "confidence": "float",
                    "reasoning": "string"
                },
                "model": "google/gemini-pro",
                "temperature": 0.1,
                "maxTokens": 200,
                "systemPrompt": "You are a customer support sentiment analyzer."
            }
        }
    },
    {
        "id": "classify_issue", 
        "data": {
            "originalStepType": "llm_step",
            "template": "classify_issue({ticket_text})",
            "label": "Classify Issue Type",
            "llmConfig": {
                "promptTemplate": "Classify this customer support issue: {ticket_text}\\n\\nCategories: technical, billing, account, feature_request, complaint\\nPriority: low, medium, high, critical\\n\\nProvide JSON response.",
                "inputParameters": ["ticket_text"],
                "outputFormat": "json",
                "expectedOutput": {
                    "category": "string",
                    "priority": "string",
                    "reasoning": "string"
                },
                "model": "google/gemini-pro",
                "temperature": 0.2
            }
        }
    },
    {
        "id": "route_ticket",
        "data": {
            "originalStepType": "workflow",
            "template": "route_to_team({sentiment}, {category}, {priority})",
            "label": "Route to Team"
        }
    }
]

REACTFLOW_EDGES = [
    {"source": "start", "target": "extract_content"},
    {"source": "extract_content", "target": "analyze_sentiment"},
    {"source": "extract_content", "target": "classify_issue"},
    {"source": "analyze_sentiment", "target": "route_ticket"},
    {"source": "classify_issue", "target": "route_ticket"}
]

def demonstrate_llm_integration():
    """Demonstrate LLM step integration features."""
    print("🚀 LLM Step Integration Demo")
    print("=" * 50)
    
    try:
        # Import required modules
        from thinkforge.models import TemplateType
        from thinkforge.step_templates import StepTemplateFactory, LLMStepTemplate
        from thinkforge.execution_config import ExecutionConfigManager, LLMConfig
        from thinkforge.workflow_compiler import compile_workflow_with_llm_steps
        
        print("✅ Successfully imported LLM integration modules")
        
        # 1. Demonstrate LLM template type
        print(f"\n📋 LLM Template Type: {TemplateType.LLM_STEP}")
        
        # 2. Create LLM step template
        print("\n🧪 Creating LLM Step Template...")
        llm_template = StepTemplateFactory.create_template("llm_step")
        print(f"   Template Type: {llm_template.template_type}")
        print(f"   Template Class: {llm_template.__class__.__name__}")
        
        # 3. Demonstrate LLM configuration
        print("\n⚙️  LLM Configuration Management...")
        config_manager = ExecutionConfigManager()
        
        # Sample LLM config
        sample_llm_config = LLMConfig(
            api_key="test_key_123",
            model="google/gemini-pro",
            temperature=0.3,
            max_tokens=500
        )
        print(f"   Model: {sample_llm_config.model}")
        print(f"   Temperature: {sample_llm_config.temperature}")
        print(f"   Max Tokens: {sample_llm_config.max_tokens}")
        
        # 4. Demonstrate template building
        print("\n🔧 LLM Template Building...")
        step_config = {
            "id": "demo_llm_step",
            "inputs": {
                "prompt_template": "Analyze this text: {text}",
                "input_parameters": ["text"],
                "output_format": "json",
                "expected_output": {"sentiment": "string", "confidence": "float"}
            }
        }
        
        execution_config = {"model": "custom/model", "temperature": 0.2}
        
        built_template = llm_template._build_llm_template(step_config, execution_config)
        print(f"   Prompt Template: {built_template['step_config']['prompt_template'][:50]}...")
        print(f"   Model Override: {built_template['step_config']['model']}")
        
        # 5. Demonstrate workflow compilation with LLM steps
        print("\n🔄 Workflow Compilation with LLM Steps...")
        
        # Compile to different formats
        formats = ["generic", "langchain", "langflow", "langgraph"]
        for fmt in formats:
            compiled = compile_workflow_with_llm_steps(REACTFLOW_NODES, REACTFLOW_EDGES, fmt)
            llm_steps = [
                step_id for step_id, step in compiled["steps"].items() 
                if step.get("templateType") == "llm_step" or step.get("type") in ["llm_node", "LLMChain", "llm_chain"]
            ]
            print(f"   {fmt.upper()} format: {len(llm_steps)} LLM steps compiled")
        
        # 6. Show example workflow structure
        print("\n📊 Example Customer Support Workflow:")
        print(f"   Total Steps: {len(CUSTOMER_SUPPORT_WORKFLOW['steps'])}")
        
        llm_step_count = sum(
            1 for step in CUSTOMER_SUPPORT_WORKFLOW['steps'].values()
            if step['templateType'] == 'llm_step'
        )
        print(f"   LLM Steps: {llm_step_count}")
        
        for step_id, step in CUSTOMER_SUPPORT_WORKFLOW['steps'].items():
            if step['templateType'] == 'llm_step':
                label = step['metadata'].get('label', step_id)
                print(f"     • {label}")
        
        print("\n🎯 LLM Integration Features:")
        print("   ✅ LLMStepTemplate class wraps LLMStepProcessor")
        print("   ✅ StepTemplateFactory supports 'llm_step' type")
        print("   ✅ LLM configuration management with environment fallback")
        print("   ✅ Template building from step config and metadata")
        print("   ✅ Input preparation and output conversion")
        print("   ✅ Workflow compilation to multiple formats")
        print("   ✅ Convenience function execute_llm_step() available")
        
        print("\n🚀 Ready for Production Use!")
        print("   - Create workflows with LLM-powered steps")
        print("   - Sentiment analysis, classification, content generation")
        print("   - Seamless integration with existing workflow framework")
        print("   - Support for multiple LLM providers via OpenRouter")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demonstrate_execution_flow():
    """Demonstrate LLM step execution flow (without actual LLM calls)."""
    print("\n" + "=" * 50)
    print("🔄 LLM Step Execution Flow Demo")
    print("=" * 50)
    
    try:
        from thinkforge.step_templates import LLMStepTemplate
        
        # Create LLM template
        llm_template = LLMStepTemplate()
        
        # Sample step configuration
        step_config = {
            "id": "sentiment_analysis",
            "inputs": {
                "prompt_template": "Analyze sentiment of: {message}\n\nReturn JSON with sentiment and confidence.",
                "input_parameters": ["message"],
                "output_format": "json",
                "expected_output": {"sentiment": "string", "confidence": "float"},
                "model": "google/gemini-pro",
                "temperature": 0.1
            },
            "metadata": {
                "label": "Customer Message Sentiment Analysis"
            }
        }
        
        # Sample input data
        entity_values = {
            "message": "Thank you so much for the quick resolution! Your support team is amazing."
        }
        
        # Sample context (previous step outputs)
        context = {
            "step_outputs": {
                "extract_content": {
                    "ticket_id": "12345",
                    "customer_id": "cust_789"
                }
            }
        }
        
        execution_config = {
            "model": "google/gemini-pro",
            "temperature": 0.1,
            "max_tokens": 200
        }
        
        # Demonstrate template building
        print("🔧 Building LLM Template...")
        llm_template_built = llm_template._build_llm_template(step_config, execution_config)
        print(f"   Prompt: {llm_template_built['step_config']['prompt_template']}")
        print(f"   Model: {llm_template_built['step_config']['model']}")
        print(f"   Temperature: {llm_template_built['step_config']['temperature']}")
        
        # Demonstrate input preparation
        print("\n📝 Preparing Input Values...")
        input_values = llm_template._prepare_input_values(step_config, entity_values, context)
        print(f"   Input Parameters: {list(input_values.keys())}")
        print(f"   Message: {input_values['message'][:50]}...")
        
        # Show what would happen in execution
        print("\n⚡ Execution Flow:")
        print("   1. Parse step configuration ✅")
        print("   2. Build LLM template with execution config ✅")
        print("   3. Prepare input values from entity_values and context ✅")
        print("   4. Execute LLM call via LLMStepProcessor ⏸️  (skipped - no API key)")
        print("   5. Format and validate output ⏸️  (skipped)")
        print("   6. Convert to ExecutionResult ⏸️  (skipped)")
        
        print("\n✅ LLM Step execution flow is ready!")
        print("   Add OPENROUTER_API_KEY to enable actual LLM calls")
        
        return True
        
    except Exception as e:
        print(f"❌ Execution flow demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the complete LLM integration demonstration."""
    print("🎯 ThinkForge LLM Step Integration")
    print("Demonstrating AI-powered workflow automation\n")
    
    # Run synchronous demo
    demo_success = demonstrate_llm_integration()
    
    # Run async execution flow demo
    if demo_success:
        execution_success = asyncio.run(demonstrate_execution_flow())
    else:
        execution_success = False
    
    print("\n" + "=" * 50)
    if demo_success and execution_success:
        print("🎉 LLM Integration Demo Completed Successfully!")
        print("\n📚 Next Steps:")
        print("   1. Set OPENROUTER_API_KEY environment variable")
        print("   2. Create workflows with LLM steps using the workflow builder")
        print("   3. Test end-to-end execution with real LLM calls")
        print("   4. Monitor performance and costs via LLM service")
    else:
        print("❌ Demo completed with errors - check logs above")
    
    return demo_success and execution_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)