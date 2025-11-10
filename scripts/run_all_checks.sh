#!/bin/bash
# Master Validation Runner
# Runs all automated validation checks in priority order
#
# Usage:
#   ./scripts/run_all_checks.sh           # Run all checks
#   ./scripts/run_all_checks.sh --p0      # Only P0 checks (fast)
#   ./scripts/run_all_checks.sh --p1      # P0 + P1 checks
#   ./scripts/run_all_checks.sh --quick   # Same as --p0

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine check level
CHECK_LEVEL="all"
if [ "$1" = "--p0" ] || [ "$1" = "--quick" ]; then
    CHECK_LEVEL="p0"
elif [ "$1" = "--p1" ]; then
    CHECK_LEVEL="p1"
fi

echo "================================================================================"
echo "AUTOMATED VALIDATION SUITE"
echo "================================================================================"
echo ""
echo "Check level: $CHECK_LEVEL"
echo ""

# Track results
P0_FAILED=0
P1_FAILED=0
P0_PASSED=0
P1_PASSED=0

# Helper function to run a check
run_check() {
    local priority=$1
    local name=$2
    local script=$3
    local description=$4
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}[$priority]${NC} $name"
    echo "Description: $description"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if python3 "$script"; then
        if [ "$priority" = "P0" ]; then
            P0_PASSED=$((P0_PASSED + 1))
        else
            P1_PASSED=$((P1_PASSED + 1))
        fi
        echo ""
    else
        local exit_code=$?
        if [ "$priority" = "P0" ]; then
            P0_FAILED=$((P0_FAILED + 1))
        else
            P1_FAILED=$((P1_FAILED + 1))
        fi
        echo ""
        echo -e "${RED}✗ Check failed with exit code: $exit_code${NC}"
        echo ""
        
        # P0 failures stop execution
        if [ "$priority" = "P0" ]; then
            echo -e "${RED}❌ CRITICAL CHECK FAILED - Stopping validation${NC}"
            echo ""
            exit 1
        fi
    fi
}

# P0 Checks (Critical - Always Run)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${RED}PRIORITY 0: CRITICAL RUNTIME CHECKS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_check "P0" "CLI ↔ Web ↔ Railway Alignment" \
    "scripts/check_cli_web_alignment.py" \
    "Validates CLI flags match Railway validation and frontend"

run_check "P0" "Function Signature Validation" \
    "scripts/check_function_signatures.py" \
    "Validates function calls match signatures"

run_check "P0" "Async/Await Pattern Validation" \
    "scripts/check_async_patterns.py" \
    "Validates async/await usage and prevents blocking"

run_check "P0" "Import/Dependency Validation" \
    "scripts/check_imports.py" \
    "Validates all imports exist in requirements"

# P1 Checks (High Impact - Run unless --p0)
if [ "$CHECK_LEVEL" != "p0" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${YELLOW}PRIORITY 1: DATA QUALITY & INTEGRATION CHECKS${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    run_check "P1" "Data Schema Validation" \
        "scripts/validate_data_schemas.py" \
        "Validates Intercom data structures"
    
    run_check "P1" "Null Safety Check" \
        "scripts/check_null_safety.py" \
        "Validates safe field access patterns"
    
    run_check "P1" "Pydantic Model Validation" \
        "scripts/validate_pydantic_models.py" \
        "Tests Pydantic models with valid/invalid data"
    
    run_check "P1" "Execution Policy Enforcement" \
        "scripts/check_execution_policies.py" \
        "Validates SSE/background execution policies"
    
    run_check "P1" "Double-Counting Detection" \
        "scripts/check_double_counting.py" \
        "Validates topic assignment uniqueness"
    
    run_check "P1" "Topic Keyword Validation" \
        "scripts/validate_topic_keywords.py" \
        "Validates keyword specificity and word boundaries"
fi

# Summary
echo ""
echo "================================================================================"
echo -e "${GREEN}VALIDATION SUMMARY${NC}"
echo "================================================================================"
echo ""
echo "P0 Checks (Critical):"
echo -e "   Passed: ${GREEN}$P0_PASSED${NC}"
echo -e "   Failed: ${RED}$P0_FAILED${NC}"
echo ""

if [ "$CHECK_LEVEL" != "p0" ]; then
    echo "P1 Checks (High Impact):"
    echo -e "   Passed: ${GREEN}$P1_PASSED${NC}"
    echo -e "   Failed: ${YELLOW}$P1_FAILED${NC}"
    echo ""
fi

# Exit code
TOTAL_CRITICAL_FAILURES=$P0_FAILED

if [ $TOTAL_CRITICAL_FAILURES -gt 0 ]; then
    echo -e "${RED}❌ $TOTAL_CRITICAL_FAILURES critical check(s) failed${NC}"
    echo "   Fix these issues before committing!"
    echo ""
    exit 1
elif [ $P1_FAILED -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $P1_FAILED high-impact check(s) failed${NC}"
    echo "   Review these issues but can proceed"
    echo ""
    exit 0
else
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    exit 0
fi

