#!/bin/bash
# Pre-commit/CI script to check for inconsistent imports
# This script ensures all imports use absolute imports with src. prefix

set -e

echo "🔍 Checking for inconsistent imports..."

# Check for incorrect import patterns in src/ directory
ERRORS=0

# Check for imports without src. prefix
INVALID_IMPORTS=$(grep -r "^from services\." src/ tests/ 2>/dev/null || true)
if [ ! -z "$INVALID_IMPORTS" ]; then
    echo "❌ ERROR: Found imports using 'from services.' instead of 'from src.services.'"
    echo "$INVALID_IMPORTS"
    ERRORS=$((ERRORS + 1))
fi

INVALID_IMPORTS=$(grep -r "^from analyzers\." src/ tests/ 2>/dev/null || true)
if [ ! -z "$INVALID_IMPORTS" ]; then
    echo "❌ ERROR: Found imports using 'from analyzers.' instead of 'from src.analyzers.'"
    echo "$INVALID_IMPORTS"
    ERRORS=$((ERRORS + 1))
fi

INVALID_IMPORTS=$(grep -r "^from models\." src/ tests/ 2>/dev/null || true)
if [ ! -z "$INVALID_IMPORTS" ]; then
    echo "❌ ERROR: Found imports using 'from models.' instead of 'from src.models.'"
    echo "$INVALID_IMPORTS"
    ERRORS=$((ERRORS + 1))
fi

INVALID_IMPORTS=$(grep -r "^from config\." src/ tests/ 2>/dev/null || true)
if [ ! -z "$INVALID_IMPORTS" ]; then
    echo "❌ ERROR: Found imports using 'from config.' instead of 'from src.config.'"
    echo "$INVALID_IMPORTS"
    ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "✅ All imports are consistent (using src. prefix)"
    exit 0
else
    echo ""
    echo "❌ Found $ERRORS types of inconsistent imports"
    echo ""
    echo "Please fix these imports by adding 'src.' prefix:"
    echo "  - 'from services.' → 'from src.services.'"
    echo "  - 'from analyzers.' → 'from src.analyzers.'"
    echo "  - 'from models.' → 'from src.models.'"
    echo "  - 'from config.' → 'from src.config.'"
    exit 1
fi

