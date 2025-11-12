#!/bin/bash
# Quick Pre-Commit Checks (P0 Only)
# Fast validation for pre-commit hook
#
# Usage:
#   ./scripts/quick_checks.sh

set -e

echo "🔍 Running quick validation (P0 checks only)..."
echo ""

# Run P0 checks only
./scripts/run_all_checks.sh --p0

echo "✅ Quick checks complete!"




