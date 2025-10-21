#!/bin/bash
# Quick test - yesterday's data only (~1k conversations)

cd "/Users/max.jackson/Intercom Analysis Tool "
export PYTHONPATH="/Users/max.jackson/Intercom Analysis Tool :$PYTHONPATH"

echo "🚀 Quick Test: Yesterday's conversations"
python3 src/main.py voice-of-customer --time-period yesterday --analysis-type topic-based

