#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.abspath('.'))

try:
    from thinkforge.models import TemplateType
    from thinkforge.step_templates import LLMStepTemplate, StepTemplateFactory
    
    print('✅ LLM_STEP in TemplateType:', hasattr(TemplateType, 'LLM_STEP'))
    print('✅ LLM_STEP value:', TemplateType.LLM_STEP)
    
    template = StepTemplateFactory.create_template('llm_step')
    print('✅ LLMStepTemplate created:', template.__class__.__name__)
    print('✅ Template type:', template.template_type)
    
    print('🎉 LLM integration working!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()