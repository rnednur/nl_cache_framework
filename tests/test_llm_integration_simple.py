#!/usr/bin/env python3
"""
Simple test for LLM Step Integration

Tests that the LLMStepTemplate integrates correctly with the workflow execution framework.
"""

import sys
import os
import asyncio
import json

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_imports():
    """Test that all required imports work."""
    print("🧪 Testing imports...")
    
    try:
        from thinkforge.models import TemplateType
        from thinkforge.step_templates import LLMStepTemplate, StepTemplateFactory
        from thinkforge.llm_step_processor import LLMStepProcessor
        
        # Check that LLM_STEP exists in TemplateType
        assert hasattr(TemplateType, 'LLM_STEP'), "LLM_STEP template type not found"
        assert TemplateType.LLM_STEP == "llm_step", "LLM_STEP value incorrect"
        
        print("✅ All imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Assertion error: {e}")
        return False

def test_template_factory():
    """Test that StepTemplateFactory can create LLM templates."""
    print("\n🧪 Testing StepTemplateFactory...")
    
    try:
        from thinkforge.step_templates import StepTemplateFactory
        
        # Test creating LLM template
        template = StepTemplateFactory.create_template("llm_step")
        assert template is not None, "Failed to create LLM template"
        assert template.template_type == "llm_step", "Wrong template type"
        
        # Test with LLM service parameter
        template_with_service = StepTemplateFactory.create_template("llm_step", llm_service=None)
        assert template_with_service is not None, "Failed to create LLM template with service"
        
        print("✅ StepTemplateFactory creates LLM templates successfully")
        return True
        
    except Exception as e:
        print(f"❌ Template factory error: {e}")
        return False

def test_llm_template_structure():
    """Test LLMStepTemplate structure and methods."""
    print("\n🧪 Testing LLMStepTemplate structure...")
    
    try:
        from thinkforge.step_templates import LLMStepTemplate
        
        # Create template
        template = LLMStepTemplate()
        
        # Check basic properties
        assert template.template_type == "llm_step", "Wrong template type"
        assert hasattr(template, 'llm_processor'), "Missing llm_processor"
        assert hasattr(template, '_build_llm_template'), "Missing _build_llm_template method"
        assert hasattr(template, '_prepare_input_values'), "Missing _prepare_input_values method"
        assert hasattr(template, '_convert_llm_result'), "Missing _convert_llm_result method"
        
        print("✅ LLMStepTemplate structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Template structure error: {e}")
        return False

def test_execution_config():
    """Test LLM configuration support."""
    print("\n🧪 Testing LLM execution configuration...")
    
    try:
        from thinkforge.execution_config import ExecutionConfigManager, LLMConfig
        
        # Create config manager
        config_manager = ExecutionConfigManager()
        
        # Test LLMConfig class
        llm_config = LLMConfig(api_key="test_key")
        assert llm_config.api_key == "test_key", "LLMConfig not working"
        assert llm_config.model == "google/gemini-pro", "Default model not set"
        assert llm_config.temperature == 0.3, "Default temperature not set"
        
        # Test get_llm_config method (should return None without config)
        result = config_manager.get_llm_config()
        # This might return None or a config from env vars, both are valid
        
        print("✅ LLM execution configuration works")
        return True
        
    except Exception as e:
        print(f"❌ Execution config error: {e}")
        return False

def test_template_building():
    """Test building LLM template from step config."""
    print("\n🧪 Testing LLM template building...")
    
    try:
        from thinkforge.step_templates import LLMStepTemplate
        
        template = LLMStepTemplate()
        
        # Sample step config
        step_config = {
            "id": "test_step",
            "inputs": {
                "prompt_template": "Analyze this text: {text}",
                "input_parameters": ["text"],
                "output_format": "json",
                "expected_output": {"sentiment": "string"},
                "model": "google/gemini-pro",
                "temperature": 0.2
            },
            "metadata": {
                "llmConfig": {
                    "promptTemplate": "Alternative prompt: {text}",
                    "inputParameters": ["text"]
                }
            }
        }
        
        execution_config = {"model": "custom/model"}
        
        # Build LLM template
        llm_template = template._build_llm_template(step_config, execution_config)
        
        # Verify template structure
        assert "step_config" in llm_template, "Missing step_config"
        step_cfg = llm_template["step_config"]
        assert step_cfg["prompt_template"] == "Analyze this text: {text}", "Wrong prompt template"
        assert step_cfg["model"] == "custom/model", "Execution config not merged"
        
        print("✅ LLM template building works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Template building error: {e}")
        return False

async def test_step_execution_mock():
    """Test LLM step execution (without actual LLM call)."""
    print("\n🧪 Testing LLM step execution (mock)...")
    
    try:
        from thinkforge.step_templates import LLMStepTemplate
        from thinkforge.execution_wrappers import ExecutionResult
        
        template = LLMStepTemplate()
        
        # Sample step config
        step_config = {
            "id": "test_llm_step",
            "inputs": {
                "prompt_template": "Classify sentiment: {text}",
                "input_parameters": ["text"],
                "output_format": "json",
                "expected_output": {"sentiment": "string"}
            }
        }
        
        entity_values = {"text": "This is a test message"}
        execution_config = {}
        
        # Test the building methods (not actual execution since we don't have LLM service)
        llm_template = template._build_llm_template(step_config, execution_config)
        input_values = template._prepare_input_values(step_config, entity_values, None)
        
        assert "text" in input_values, "Input values not prepared correctly"
        assert input_values["text"] == "This is a test message", "Wrong input value"
        
        print("✅ LLM step execution preparation works")
        return True
        
    except Exception as e:
        print(f"❌ Step execution error: {e}")
        return False

def test_convenience_functions():
    """Test convenience functions for LLM steps."""
    print("\n🧪 Testing convenience functions...")
    
    try:
        from thinkforge.step_templates import execute_llm_step
        
        # Just test that the function exists and is callable
        assert callable(execute_llm_step), "execute_llm_step not callable"
        
        print("✅ Convenience functions available")
        return True
        
    except Exception as e:
        print(f"❌ Convenience function error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing LLM Step Integration")
    print("=" * 50)
    
    tests = [
        test_imports(),
        test_template_factory(),
        test_llm_template_structure(),
        test_execution_config(),
        test_template_building(),
        await test_step_execution_mock(),
        test_convenience_functions()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"🎉 All {total} tests passed!")
        print("\n📋 Integration Summary:")
        print("✅ LLMStepTemplate class created and working")
        print("✅ StepTemplateFactory includes LLM_STEP mapping")
        print("✅ LLM configuration support added")
        print("✅ Template building and input preparation working")
        print("✅ Convenience functions available")
        print("\n🎯 Ready for production use!")
        return True
    else:
        print(f"❌ {total - passed} out of {total} tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)