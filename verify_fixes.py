#!/usr/bin/env python3
"""
Quick verification script to test the 8 verification comments have been implemented correctly.
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test 1: Verify AgentContext import by checking source code directly
print("=" * 80)
print("Test 1: Verify AgentContext import from base_agent")
print("=" * 80)
try:
    # Check source code directly instead of importing
    files_to_check = [
        'src/agents/correlation_agent.py',
        'src/agents/quality_insights_agent.py',
        'src/agents/churn_risk_agent.py',
        'src/agents/confidence_meta_agent.py'
    ]
    
    for filepath in files_to_check:
        with open(filepath, 'r') as f:
            content = f.read()
            # Check that AgentContext is imported from base_agent
            assert 'from src.agents.base_agent import' in content, \
                f"{filepath}: Missing import from base_agent"
            assert 'AgentContext' in content.split('from src.agents.base_agent import')[1].split('\n')[0], \
                f"{filepath}: AgentContext not imported from base_agent"
            # Check that it's NOT imported from old location
            assert 'from src.context.agent_context import AgentContext' not in content, \
                f"{filepath}: Still importing from old location src.context.agent_context"
    
    print("✅ PASS: All agents import AgentContext from base_agent (verified via source code)")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 2: Verify ConfidenceLevel enum values
print("\n" + "=" * 80)
print("Test 2: Verify ConfidenceLevel only has HIGH, MEDIUM, LOW")
print("=" * 80)
try:
    # Check base_agent.py for ConfidenceLevel enum definition
    with open('src/agents/base_agent.py', 'r') as f:
        content = f.read()
        # Check enum definition
        assert 'class ConfidenceLevel(Enum):' in content, \
            "ConfidenceLevel enum not found in base_agent.py"
        assert 'HIGH = "high"' in content, "HIGH not in ConfidenceLevel"
        assert 'MEDIUM = "medium"' in content, "MEDIUM not in ConfidenceLevel"
        assert 'LOW = "low"' in content, "LOW not in ConfidenceLevel"
        # Check that NONE and VERY_LOW are NOT present after enum definition
        enum_section = content.split('class ConfidenceLevel(Enum):')[1].split('\n\n')[0]
        assert 'NONE' not in enum_section, "NONE should not be in ConfidenceLevel"
        assert 'VERY_LOW' not in enum_section, "VERY_LOW should not be in ConfidenceLevel"
    
    # Check _calculate_confidence_level methods
    files_to_check = [
        'src/agents/correlation_agent.py',
        'src/agents/quality_insights_agent.py',
        'src/agents/churn_risk_agent.py'
    ]
    
    for filepath in files_to_check:
        with open(filepath, 'r') as f:
            content = f.read()
            # Find _calculate_confidence_level method
            method_start = content.find('def _calculate_confidence_level')
            if method_start == -1:
                raise AssertionError(f"{filepath}: Missing _calculate_confidence_level method")
            method_end = content.find('\n    def ', method_start + 1)
            if method_end == -1:
                method_end = len(content)
            method_code = content[method_start:method_end]
            
            # Check that only HIGH, MEDIUM, LOW are returned
            assert 'ConfidenceLevel.HIGH' in method_code, f"{filepath}: Should return HIGH"
            assert 'ConfidenceLevel.MEDIUM' in method_code, f"{filepath}: Should return MEDIUM"
            assert 'ConfidenceLevel.LOW' in method_code, f"{filepath}: Should return LOW"
            assert 'ConfidenceLevel.NONE' not in method_code, f"{filepath}: Should not return NONE"
            assert 'ConfidenceLevel.VERY_LOW' not in method_code, f"{filepath}: Should not return VERY_LOW"
    
    print("✅ PASS: ConfidenceLevel enum has correct values and agents return only valid levels")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 3: Verify validate_input/validate_output signatures
print("\n" + "=" * 80)
print("Test 3: Verify validate_input/validate_output signatures return bool and raise ValueError")
print("=" * 80)
try:
    files_to_check = [
        'src/agents/correlation_agent.py',
        'src/agents/quality_insights_agent.py',
        'src/agents/churn_risk_agent.py',
        'src/agents/confidence_meta_agent.py'
    ]
    
    for filepath in files_to_check:
        with open(filepath, 'r') as f:
            content = f.read()
            
            # Check validate_input signature
            assert 'def validate_input(self, context: AgentContext) -> bool:' in content, \
                f"{filepath}: validate_input should return bool"
            # Check that it raises ValueError
            validate_input_start = content.find('def validate_input')
            validate_input_end = content.find('\n    def ', validate_input_start + 1)
            if validate_input_end == -1:
                validate_input_end = content.find('\n    async def ', validate_input_start + 1)
            validate_input_code = content[validate_input_start:validate_input_end]
            assert 'raise ValueError' in validate_input_code, \
                f"{filepath}: validate_input should raise ValueError"
            
            # Check validate_output signature  
            assert 'def validate_output(self, result: Dict[str, Any]) -> bool:' in content, \
                f"{filepath}: validate_output should return bool"
            # Check that it raises ValueError
            validate_output_start = content.find('def validate_output')
            validate_output_end = content.find('\n    def ', validate_output_start + 1)
            if validate_output_end == -1:
                validate_output_end = content.find('\n    async def ', validate_output_start + 1)
            validate_output_code = content[validate_output_start:validate_output_end]
            assert 'raise ValueError' in validate_output_code, \
                f"{filepath}: validate_output should raise ValueError"
            
            # Check that old Tuple[bool, Optional[str]] signature is NOT present
            assert 'Tuple[bool, Optional[str]]' not in validate_input_code, \
                f"{filepath}: validate_input should not return Tuple"
            assert 'Tuple[bool, Optional[str]]' not in validate_output_code, \
                f"{filepath}: validate_output should not return Tuple"
    
    print("✅ PASS: All agents have correct validate_input/validate_output signatures")
except Exception as e:
    print(f"❌ FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verify ChurnRiskAgent prompt doesn't have prescriptive guidance
print("\n" + "=" * 80)
print("Test 4: Verify ChurnRiskAgent prompt doesn't have prescriptive guidance")
print("=" * 80)
try:
    with open('src/agents/churn_risk_agent.py', 'r') as f:
        content = f.read()
        
        # Find _analyze_conversation_with_llm method
        method_start = content.find('def _analyze_conversation_with_llm')
        if method_start == -1:
            raise AssertionError("ChurnRiskAgent: Missing _analyze_conversation_with_llm method")
        method_end = content.find('\n    def ', method_start + 1)
        if method_end == -1:
            method_end = content.find('\n    async def ', method_start + 1)
        if method_end == -1:
            method_end = len(content)
        method_code = content[method_start:method_end]
        
        # Check that "Suggested response approach" is NOT in the prompt
        assert "Suggested response approach" not in method_code, \
            "ChurnRiskAgent still has prescriptive 'Suggested response approach' in prompt"
        
        # Check that the new non-prescriptive items are present
        assert "Assessment of churn intent" in method_code, \
            "ChurnRiskAgent missing 'Assessment of churn intent'"
        assert "Key concerns expressed by the customer" in method_code, \
            "ChurnRiskAgent missing 'Key concerns expressed by the customer'"
    
    print("✅ PASS: ChurnRiskAgent prompt is observational (no prescriptive guidance)")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 5: Verify resolution outlier sorting uses numeric field
print("\n" + "=" * 80)
print("Test 5: Verify resolution outlier sorting uses numeric field")
print("=" * 80)
try:
    with open('src/agents/quality_insights_agent.py', 'r') as f:
        content = f.read()
        
        # Find _detect_resolution_outliers method
        method_start = content.find('def _detect_resolution_outliers')
        if method_start == -1:
            raise AssertionError("QualityInsightsAgent: Missing _detect_resolution_outliers method")
        method_end = content.find('\n    def ', method_start + 1)
        if method_end == -1:
            method_end = content.find('\n    async def ', method_start + 1)
        if method_end == -1:
            method_end = len(content)
        method_code = content[method_start:method_end]
        
        # Check that 'deviation' field is present in outlier dict
        assert "'deviation': deviation" in method_code, \
            "QualityInsightsAgent missing 'deviation' field in outlier dict"
        
        # Check that sorting uses 'deviation' key
        assert "key=lambda x: x['deviation']" in method_code, \
            "QualityInsightsAgent not sorting by 'deviation' field"
    
    print("✅ PASS: Resolution outlier sorting uses numeric 'deviation' field")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 6: Verify agent resolution correlation uses segmentation data
print("\n" + "=" * 80)
print("Test 6: Verify agent resolution correlation uses segmentation data")
print("=" * 80)
try:
    with open('src/agents/correlation_agent.py', 'r') as f:
        content = f.read()
        
        # Find _calculate_agent_resolution_correlation method
        method_start = content.find('def _calculate_agent_resolution_correlation')
        if method_start == -1:
            raise AssertionError("CorrelationAgent: Missing _calculate_agent_resolution_correlation method")
        method_end = content.find('\n    def ', method_start + 1)
        if method_end == -1:
            method_end = content.find('\n    async def ', method_start + 1)
        if method_end == -1:
            method_end = len(content)
        method_code = content[method_start:method_end]
        
        # Check that conversation_assignments is extracted from segmentation_data
        assert "conversation_assignments = segmentation_data.get('conversation_assignments'" in method_code, \
            "CorrelationAgent not extracting conversation_assignments from segmentation_data"
        
        # Check that it checks for conv_id in conversation_assignments
        assert "conv_id in conversation_assignments" in method_code, \
            "CorrelationAgent not checking conversation_assignments"
    
    print("✅ PASS: Agent resolution correlation uses segmentation data")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 7: Verify tier×topic correlation uses O(N) optimization
print("\n" + "=" * 80)
print("Test 7: Verify tier×topic correlation uses O(N) optimization")
print("=" * 80)
try:
    with open('src/agents/correlation_agent.py', 'r') as f:
        content = f.read()
        
        # Find _calculate_tier_topic_correlation method
        method_start = content.find('def _calculate_tier_topic_correlation')
        if method_start == -1:
            raise AssertionError("CorrelationAgent: Missing _calculate_tier_topic_correlation method")
        method_end = content.find('\n    def ', method_start + 1)
        if method_end == -1:
            method_end = content.find('\n    async def ', method_start + 1)
        if method_end == -1:
            method_end = len(content)
        method_code = content[method_start:method_end]
        
        # Check that conv_by_id is created
        assert "conv_by_id = {conv.get('id'): conv for conv" in method_code, \
            "CorrelationAgent missing conv_by_id pre-indexing"
        
        # Check that it uses conv_by_id for lookup
        assert "conv_id in conv_by_id" in method_code, \
            "CorrelationAgent not using conv_by_id for O(1) lookup"
        
        # Check that the comment mentions O(N) optimization
        assert "O(N)" in method_code, \
            "CorrelationAgent missing O(N) optimization comment"
    
    print("✅ PASS: Tier×topic correlation uses O(N) optimization with pre-indexing")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

# Test 8: Verify TopicOrchestrator passes actual client, not enum
print("\n" + "=" * 80)
print("Test 8: Verify TopicOrchestrator passes actual client, not enum")
print("=" * 80)
try:
    with open('src/agents/topic_orchestrator.py', 'r') as f:
        content = f.read()
        
        # Find execute_weekly_analysis method
        method_start = content.find('async def execute_weekly_analysis')
        if method_start == -1:
            raise AssertionError("TopicOrchestrator: Missing execute_weekly_analysis method")
        # Don't need to find method_end as we're checking the whole file
        
        # Check that it gets client from factory
        assert "client = self.ai_factory.get_ai_model(ai_model)" in content, \
            "TopicOrchestrator not getting client from factory"
        
        # Check that it assigns client, not ai_model
        assert "self.correlation_agent.ai_client = client" in content, \
            "TopicOrchestrator not assigning client to correlation_agent"
        assert "self.quality_insights_agent.ai_client = client" in content, \
            "TopicOrchestrator not assigning client to quality_insights_agent"
        assert "self.churn_risk_agent.ai_client = client" in content, \
            "TopicOrchestrator not assigning client to churn_risk_agent"
        assert "self.confidence_meta_agent.ai_client = client" in content, \
            "TopicOrchestrator not assigning client to confidence_meta_agent"
    
    print("✅ PASS: TopicOrchestrator passes actual client from factory, not enum")
except Exception as e:
    print(f"❌ FAIL: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("🎉 ALL VERIFICATION TESTS PASSED! 🎉")
print("=" * 80)
print("\nAll 8 verification comments have been successfully implemented:")
print("1. ✅ AgentContext imported from base_agent")
print("2. ✅ ConfidenceLevel only uses HIGH, MEDIUM, LOW")
print("3. ✅ TopicOrchestrator passes actual client, not enum")
print("4. ✅ ChurnRiskAgent prompt is observational")
print("5. ✅ Resolution outlier sorting uses numeric field")
print("6. ✅ Agent resolution correlation uses segmentation data")
print("7. ✅ validate_input/validate_output have correct signatures")
print("8. ✅ Tier×topic correlation uses O(N) optimization")

