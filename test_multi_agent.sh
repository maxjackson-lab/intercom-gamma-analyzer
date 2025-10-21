#!/bin/bash
# Test script for multi-agent analysis with proper Python path

cd "/Users/max.jackson/Intercom Analysis Tool "
export PYTHONPATH="/Users/max.jackson/Intercom Analysis Tool :$PYTHONPATH"

echo "Testing multi-agent analysis with single day..."
python3 src/main.py voice-of-customer --start-date 2025-10-14 --end-date 2025-10-14 --analysis-type topic-based

