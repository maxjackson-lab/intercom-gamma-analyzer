#!/usr/bin/env python3
"""
Analyze Agent Observability Data

Shows what LLM calls succeeded/failed, patterns in errors, and agent performance.

Usage:
    python scripts/analyze_observability.py <observability.json>
    
Example:
    python scripts/analyze_observability.py outputs/executions/.../agent_thinking_*.observability.json
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def analyze_observability(json_file: Path):
    """Analyze observability JSON and show insights"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    events = data.get('events', [])
    
    print("="*80)
    print("AGENT OBSERVABILITY ANALYSIS")
    print("="*80)
    print()
    
    # Overall stats
    print(f"📊 OVERALL STATISTICS:")
    print(f"   Total Events: {summary.get('total_events', 0)}")
    print(f"   Success Rate: {summary.get('success_rate', 0):.1%}")
    print(f"   Errors: {summary.get('error_count', 0)}")
    print(f"   Total Tokens: {summary.get('total_tokens', 0):,}")
    print()
    
    # Events by type
    print(f"📋 EVENTS BY TYPE:")
    for event_type, count in summary.get('events_by_type', {}).items():
        print(f"   {event_type}: {count}")
    print()
    
    # Events by agent
    print(f"🤖 EVENTS BY AGENT:")
    for agent, count in sorted(summary.get('events_by_agent', {}).items(), key=lambda x: x[1], reverse=True):
        print(f"   {agent}: {count}")
    print()
    
    # Error analysis
    errors = summary.get('errors', [])
    if errors:
        print(f"❌ ERROR ANALYSIS ({len(errors)} errors):")
        print()
        
        # Group by error type
        error_types = Counter(e.get('error_type', 'unknown') for e in errors)
        print(f"   Error Types:")
        for error_type, count in error_types.most_common():
            print(f"      {error_type}: {count}")
        print()
        
        # Group by agent
        error_agents = Counter(e.get('agent', 'unknown') for e in errors)
        print(f"   Errors by Agent:")
        for agent, count in error_agents.most_common():
            print(f"      {agent}: {count}")
        print()
        
        # Show sample errors
        print(f"   Sample Errors (first 5):")
        for i, error in enumerate(errors[:5], 1):
            print(f"      {i}. [{error.get('agent', 'unknown')}] {error.get('error_type', 'unknown')}")
            print(f"         {error.get('error_message', 'No message')[:200]}")
            if error.get('context'):
                print(f"         Context: {error.get('context')}")
            print()
    
    # Prompt/Response analysis
    prompts = [e for e in events if e.get('event_type') == 'prompt']
    responses = [e for e in events if e.get('event_type') == 'response']
    
    if prompts and responses:
        print(f"💬 LLM CALL ANALYSIS:")
        print(f"   Prompts sent: {len(prompts)}")
        print(f"   Responses received: {len(responses)}")
        
        if len(prompts) != len(responses):
            print(f"   ⚠️  MISMATCH: {len(prompts) - len(responses)} prompts without responses!")
            print(f"      This indicates LLM calls that failed or timed out")
        print()
        
        # Token usage
        total_tokens = sum(r.get('tokens_used', 0) for r in responses)
        avg_tokens = total_tokens / len(responses) if responses else 0
        print(f"   Token Usage:")
        print(f"      Total: {total_tokens:,}")
        print(f"      Average per call: {avg_tokens:.0f}")
        print()
        
        # Model distribution
        models = Counter(r.get('model', 'unknown') for r in responses)
        print(f"   Models Used:")
        for model, count in models.most_common():
            print(f"      {model}: {count}")
        print()
    
    # Agent performance
    print(f"⚡ AGENT PERFORMANCE:")
    agent_stats = defaultdict(lambda: {'prompts': 0, 'responses': 0, 'errors': 0, 'tokens': 0})
    
    for event in events:
        agent = event.get('agent', 'unknown')
        event_type = event.get('event_type')
        
        if event_type == 'prompt':
            agent_stats[agent]['prompts'] += 1
        elif event_type == 'response':
            agent_stats[agent]['responses'] += 1
            agent_stats[agent]['tokens'] += event.get('tokens_used', 0)
        elif event_type == 'error':
            agent_stats[agent]['errors'] += 1
    
    for agent, stats in sorted(agent_stats.items(), key=lambda x: x[1]['prompts'], reverse=True):
        success_rate = stats['responses'] / stats['prompts'] if stats['prompts'] > 0 else 0
        print(f"   {agent}:")
        print(f"      Prompts: {stats['prompts']}")
        print(f"      Responses: {stats['responses']} ({success_rate:.1%} success)")
        print(f"      Errors: {stats['errors']}")
        print(f"      Tokens: {stats['tokens']:,}")
        print()
    
    # Recommendations
    print("="*80)
    print("RECOMMENDATIONS:")
    print("="*80)
    
    if errors:
        print("❌ ERRORS DETECTED:")
        print("   1. Review error messages above")
        print("   2. Check if errors are timeouts (increase timeout)")
        print("   3. Check if errors are rate limits (reduce concurrency)")
        print("   4. Check if errors are validation (fix prompts/schemas)")
        print()
    
    if prompts and len(prompts) != len(responses):
        missing = len(prompts) - len(responses)
        print(f"⚠️  {missing} PROMPTS WITHOUT RESPONSES:")
        print("   1. Check for timeouts (LLM took too long)")
        print("   2. Check for rate limits (429 errors)")
        print("   3. Check for network issues")
        print()
    
    if summary.get('success_rate', 1.0) < 0.95:
        print(f"⚠️  LOW SUCCESS RATE ({summary.get('success_rate', 0):.1%}):")
        print("   1. Review error patterns above")
        print("   2. Check LLM provider status")
        print("   3. Verify API keys are valid")
        print()
    
    print("✅ Analysis complete!")
    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_observability.py <observability.json>")
        print()
        print("Example:")
        print("  python scripts/analyze_observability.py outputs/executions/.../agent_thinking_*.observability.json")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    
    analyze_observability(json_file)

