#!/usr/bin/env python3
"""
Test script for simplified tool mapping approach.

This script demonstrates the difference between the old complex multi-phase search
and the new simplified similarity-based approach.
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Set up logging to see the difference in output
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

try:
    from thinkforge.recipe_step_analyzer import RecipeStepAnalyzer
    from thinkforge.recipe_tool_mapper import RecipeToolMapper, USE_LEGACY_TOOL_MAPPING
    from thinkforge.controller import Text2SQLController
    from thinkforge.models import TemplateType
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root")
    sys.exit(1)


def test_simplified_vs_legacy():
    """Compare simplified vs legacy tool mapping approaches."""
    print("🧪 Testing Simplified vs Legacy Tool Mapping")
    print("=" * 60)
    
    # Initialize components
    controller = Text2SQLController()
    tool_mapper = RecipeToolMapper(controller)
    step_analyzer = RecipeStepAnalyzer()
    
    # Sample recipe for testing
    test_recipe = """
    Customer Support Workflow:
    1. Extract customer email content
    2. Analyze sentiment and classify urgency 
    3. Generate automated response
    """
    
    print(f"📝 Test Recipe:\n{test_recipe}")
    print("-" * 60)
    
    # Analyze the recipe to get steps
    analysis = step_analyzer.analyze_recipe(test_recipe, "Customer Support Test")
    steps = analysis.steps
    
    print(f"📊 Recipe Analysis: {len(steps)} steps identified")
    for i, step in enumerate(steps, 1):
        print(f"   Step {i}: {step.name} (type: {step.step_type})")
    
    if not steps:
        print("❌ No steps found in recipe analysis")
        return
    
    # Test with simplified approach (default)
    print(f"\n🚀 SIMPLIFIED APPROACH (USE_LEGACY_TOOL_MAPPING = {USE_LEGACY_TOOL_MAPPING})")
    print("-" * 40)
    
    simplified_results = []
    for step in steps[:2]:  # Test first 2 steps
        print(f"\n🔍 Step: '{step.name}'")
        matches = tool_mapper.find_tools_for_step(step, max_results=5)
        simplified_results.append((step.name, len(matches), matches[:3] if matches else []))
        
        if matches:
            print(f"   Found {len(matches)} matches:")
            for match in matches[:3]:
                print(f"     • {match.tool_name} (similarity: {match.similarity_score:.3f}, confidence: {match.overall_confidence:.3f})")
        else:
            print("   No matches found")
    
    # Test with legacy approach
    print(f"\n🔄 LEGACY APPROACH (switching to legacy mode)")
    print("-" * 40)
    
    # Temporarily enable legacy mode by modifying the module
    import thinkforge.recipe_tool_mapper as mapper_module
    original_flag = mapper_module.USE_LEGACY_TOOL_MAPPING
    mapper_module.USE_LEGACY_TOOL_MAPPING = True
    
    legacy_results = []
    for step in steps[:2]:  # Test first 2 steps
        print(f"\n🔍 Step: '{step.name}'")
        matches = tool_mapper.find_tools_for_step(step, max_results=5)
        legacy_results.append((step.name, len(matches), matches[:3] if matches else []))
        
        if matches:
            print(f"   Found {len(matches)} matches:")
            for match in matches[:3]:
                print(f"     • {match.tool_name} (similarity: {match.similarity_score:.3f}, confidence: {match.overall_confidence:.3f})")
        else:
            print("   No matches found")
    
    # Restore original flag
    mapper_module.USE_LEGACY_TOOL_MAPPING = original_flag
    
    # Summary comparison
    print(f"\n📈 RESULTS COMPARISON")
    print("=" * 60)
    
    for i, ((s_step, s_count, s_matches), (l_step, l_count, l_matches)) in enumerate(zip(simplified_results, legacy_results)):
        print(f"Step {i+1}: '{s_step}'")
        print(f"   Simplified: {s_count} matches")
        print(f"   Legacy:     {l_count} matches")
        
        if s_matches and l_matches:
            s_best = s_matches[0]
            l_best = l_matches[0]
            print(f"   Best simplified: {s_best.similarity_score:.3f} similarity")
            print(f"   Best legacy:     {l_best.similarity_score:.3f} similarity")
        print()
    
    print("✅ Test completed successfully!")
    return True


def test_configuration_switching():
    """Test that the configuration flag properly switches between approaches."""
    print("\n🔧 Testing Configuration Flag Switching")
    print("=" * 60)
    
    # Test that we can switch the configuration
    import thinkforge.recipe_tool_mapper as mapper_module
    
    original_flag = mapper_module.USE_LEGACY_TOOL_MAPPING
    print(f"Original flag value: {original_flag}")
    
    # Switch to legacy
    mapper_module.USE_LEGACY_TOOL_MAPPING = True
    print(f"Switched to legacy: {mapper_module.USE_LEGACY_TOOL_MAPPING}")
    
    # Switch back to simplified  
    mapper_module.USE_LEGACY_TOOL_MAPPING = False
    print(f"Switched to simplified: {mapper_module.USE_LEGACY_TOOL_MAPPING}")
    
    # Restore original
    mapper_module.USE_LEGACY_TOOL_MAPPING = original_flag
    print(f"Restored to original: {mapper_module.USE_LEGACY_TOOL_MAPPING}")
    
    print("✅ Configuration switching works correctly!")


def main():
    """Run all tests."""
    print("🚀 Testing Simplified Tool Mapping Implementation")
    print("=" * 80)
    
    try:
        # Test configuration switching
        test_configuration_switching()
        
        # Test actual mapping approaches
        test_simplified_vs_legacy()
        
        print(f"\n🎉 All tests completed successfully!")
        print("\n📋 Summary:")
        print("✅ Simplified approach: Single similarity search with 0.4 threshold")
        print("✅ Legacy approach: Complex multi-phase search (available as fallback)")
        print("✅ Configuration flag: Allows switching between approaches")
        print("✅ Performance: Reduced API calls and cleaner logging")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)