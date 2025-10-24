#!/bin/bash
# End-to-end testing script for Intercom Analysis Tool
# Tests all recent changes to verify they actually work

set -e  # Exit on any error

echo "=================================="
echo "🧪 End-to-End Testing Suite"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Import Test
echo "Test 1: Python Imports"
echo "----------------------"
if python3 -c "
from src.agents.topic_orchestrator import TopicOrchestrator
from src.utils.agent_output_display import AgentOutputDisplay
from src.utils.time_utils import generate_descriptive_filename
from src.config.modes import get_analysis_mode_config
print('✅ All imports successful')
" 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: All Python imports work"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Import errors detected"
    ((TESTS_FAILED++))
fi
echo ""

# Test 2: Config Loading
echo "Test 2: Configuration Loading"
echo "------------------------------"
if python3 -c "
from src.config.modes import get_analysis_mode_config
config = get_analysis_mode_config()
enable_display = config.get_visibility_setting('enable_agent_output_display', True)
print(f'Agent output display enabled: {enable_display}')
print('✅ Config loaded successfully')
" 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: Configuration loads correctly"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Config loading failed"
    ((TESTS_FAILED++))
fi
echo ""

# Test 3: Descriptive Filename Generation
echo "Test 3: Descriptive Filename Generation"
echo "----------------------------------------"
if python3 -c "
from datetime import datetime
from src.utils.time_utils import generate_descriptive_filename

# Test various scenarios
filename1 = generate_descriptive_filename('voc', '2024-10-17', '2024-10-24', week_id='2024-W42')
filename2 = generate_descriptive_filename('canny', '2024-10-01', '2024-10-31')
filename3 = generate_descriptive_filename('topic', '2024-10-20', '2024-10-21', file_type='md')

print(f'VoC filename: {filename1}')
print(f'Canny filename: {filename2}')
print(f'Topic filename: {filename3}')

# Verify they are not using timestamps
assert 'Week_2024-W42' in filename1, 'Week ID not in filename'
assert filename1.endswith('.json'), 'Wrong file extension'

print('✅ All filename tests passed')
" 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: Descriptive filenames work correctly"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Filename generation failed"
    ((TESTS_FAILED++))
fi
echo ""

# Test 4: Agent Display Module
echo "Test 4: Agent Display Module"
echo "-----------------------------"
if python3 -c "
from src.utils.agent_output_display import AgentOutputDisplay

# Test initialization
display = AgentOutputDisplay(enabled=True)
assert display.enabled == True, 'Display not enabled'

# Test with mock data
mock_result = {
    'agent_name': 'TestAgent',
    'success': True,
    'confidence': 0.92,
    'confidence_level': 'HIGH',
    'execution_time': 2.34,
    'data': {'test': 'data'}
}

# This should not crash
display.display_agent_result('TestAgent', mock_result, show_full_data=False)
print('✅ Agent display module works')
" 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: Agent display module functional"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Agent display module broken"
    ((TESTS_FAILED++))
fi
echo ""

# Test 5: Tier Detection Logic
echo "Test 5: Tier Detection Logic"
echo "-----------------------------"
if python3 -c "
from src.agents.segmentation_agent import SegmentationAgent
from src.models.analysis_models import CustomerTier

agent = SegmentationAgent()

# Test with mock conversation with Stripe data
mock_conv = {
    'id': 'test_123',
    'contacts': {
        'contacts': [{
            'id': 'contact_123',
            'custom_attributes': {
                'stripe_subscription_status': 'active',
                'stripe_plan': 'Pro • Pro Monthly'
            }
        }]
    }
}

tier = agent._extract_customer_tier(mock_conv)
assert tier == CustomerTier.PRO, f'Expected PRO, got {tier.value}'
print(f'Tier detected: {tier.value}')
print('✅ Tier detection with Stripe data works')
" 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}: Tier detection logic correct"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Tier detection broken"
    ((TESTS_FAILED++))
fi
echo ""

# Test 6: Check for common errors
echo "Test 6: Static Analysis (Common Errors)"
echo "----------------------------------------"
if python3 -m py_compile src/agents/topic_orchestrator.py && \
   python3 -m py_compile src/services/gamma_generator.py && \
   python3 -m py_compile src/utils/agent_output_display.py; then
    echo -e "${GREEN}✅ PASS${NC}: No syntax errors in modified files"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Syntax errors detected"
    ((TESTS_FAILED++))
fi
echo ""

# Final Summary
echo "=================================="
echo "📊 Test Results Summary"
echo "=================================="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test locally: python -m src.main voice --month 11 --year 2024 --analysis-type topic-based"
    echo "2. Check outputs/ directory for descriptive filenames"
    echo "3. Deploy to Railway and test web UI"
    echo "4. Run with --generate-gamma to test Gamma link prominence"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo "Fix the failing tests before deploying to Railway"
    exit 1
fi

