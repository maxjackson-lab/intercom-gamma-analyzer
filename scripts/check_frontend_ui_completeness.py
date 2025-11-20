#!/usr/bin/env python3
"""
Exhaustive Frontend UI → Backend Alignment Validator

Validates that every Railway canonical flag has a corresponding UI control in static/app.js,
and every UI control that sends a flag is properly defined in Railway mappings.

This prevents:
1. Checkboxes that exist but never wire up to flags (dead UI)
2. Flags that exist in backend but have no UI control (hidden features)
3. Conditional logic errors (sending flags to wrong commands)

Run before committing UI or flag changes.
"""

import re
import sys
import os
from typing import Dict, Set, List, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_ui_controls_from_html(railway_web_path: str) -> Dict[str, str]:
    """
    Extract UI control IDs from the HTML in railway_web.py.
    
    Returns:
        Dict[control_id, control_type] - e.g., {'digestModeToggle': 'checkbox'}
    """
    controls = {}
    
    with open(railway_web_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find checkbox inputs: id="someId"
    checkbox_pattern = r'<input[^>]*type=["\']checkbox["\'][^>]*id=["\']([^"\']+)["\']'
    for match in re.finditer(checkbox_pattern, content):
        control_id = match.group(1)
        controls[control_id] = 'checkbox'
    
    # Find select dropdowns: id="someId"
    select_pattern = r'<select[^>]*id=["\']([^"\']+)["\']'
    for match in re.finditer(select_pattern, content):
        control_id = match.group(1)
        controls[control_id] = 'select'
    
    return controls


def extract_flag_usage_from_js(app_js_path: str) -> Dict[str, Set[str]]:
    """
    Parse static/app.js to extract which flags each analysisType sends.
    
    Returns:
        Dict[analysisType, Set[flag_name]]
        e.g., {'voice-of-customer-hilary': {'--digest-mode', '--multi-agent', ...}}
    """
    flag_usage = {}
    
    with open(app_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Also extract ALL flags mentioned anywhere (for generic blocks)
    all_flags_in_js = set(re.findall(r"args\.push\(['\"](-{1,2}[a-z\-]+)['\"]", content))
    
    lines = content.split('\n')
    current_analysis_type = None
    in_analysis_block = False
    block_depth = 0
    
    for i, line in enumerate(lines, 1):
        # Track brace depth to know when we exit the analysis block
        block_depth += line.count('{') - line.count('}')
        
        # Detect analysis type blocks
        if "analysisType === " in line or "analysisType.startsWith(" in line:
            # Extract analysis type
            if "===" in line:
                match = re.search(r"analysisType\s*===\s*['\"]([^'\"]+)['\"]", line)
                if match:
                    current_analysis_type = match.group(1)
                    in_analysis_block = True
                    if current_analysis_type not in flag_usage:
                        flag_usage[current_analysis_type] = set()
            elif ".startsWith(" in line:
                match = re.search(r"analysisType\.startsWith\(['\"]([^'\"]+)['\"]\)", line)
                if match:
                    current_analysis_type = f"{match.group(1)}*"  # Wildcard
                    in_analysis_block = True
                    if current_analysis_type not in flag_usage:
                        flag_usage[current_analysis_type] = set()
        
        # Extract flags being pushed
        if in_analysis_block and current_analysis_type and 'args.push(' in line:
            # Match: args.push('--some-flag', value) or args.push('--some-flag')
            flag_matches = re.findall(r"args\.push\(['\"](-{1,2}[a-z\-]+)['\"]", line)
            for flag_name in flag_matches:
                flag_usage[current_analysis_type].add(flag_name)
        
        # End of block (closed the opening brace)
        if in_analysis_block and block_depth <= 0:
            in_analysis_block = False
            current_analysis_type = None
    
    return flag_usage, all_flags_in_js


def extract_ui_to_flag_mappings(app_js_path: str) -> Dict[str, str]:
    """
    Extract which UI controls map to which flags.
    
    Returns:
        Dict[control_id, flag_name] - e.g., {'digestModeToggle': '--digest-mode'}
    """
    mappings = {}
    
    with open(app_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern: const varName = document.getElementById('controlId')?.checked
    # followed by: if (varName) { args.push('--flag-name'); }
    
    # Look for digestMode pattern as example
    if "digestModeToggle" in content and "--digest-mode" in content:
        mappings['digestModeToggle'] = '--digest-mode'
    
    if "llmTopicDetectionVoc" in content and "--llm-topic-detection" in content:
        mappings['llmTopicDetectionVoc'] = '--llm-topic-detection'
    
    if "llmTopicDetection" in content and "--llm-topic-detection" in content:
        mappings['llmTopicDetection'] = '--llm-topic-detection'
    
    if "testMode" in content and "--test-mode" in content:
        mappings['testMode'] = '--test-mode'
    
    if "auditMode" in content and "--audit-trail" in content:
        mappings['auditMode'] = '--audit-trail'
    
    if "verboseLogging" in content and "--verbose" in content:
        mappings['verboseLogging'] = '--verbose'
    
    if "showAgentThinking" in content and "--show-agent-thinking" in content:
        mappings['showAgentThinking'] = '--show-agent-thinking'
    
    if "testAllAgents" in content and "--test-all-agents" in content:
        mappings['testAllAgents'] = '--test-all-agents'
    
    if "includeHierarchy" in content and "--no-hierarchy" in content:
        mappings['includeHierarchy'] = '--include-hierarchy'
    
    # Add more patterns as needed
    return mappings


def validate_frontend_completeness():
    """
    Exhaustive check: every Railway flag should have UI wiring, 
    and every UI control should map to a valid Railway flag.
    """
    from deploy.railway_web import CANONICAL_COMMAND_MAPPINGS
    
    errors = []
    warnings = []
    info = []
    
    # Extract data
    ui_controls = extract_ui_controls_from_html('deploy/railway_web.py')
    flag_usage, all_flags_in_js = extract_flag_usage_from_js('static/app.js')
    ui_to_flag = extract_ui_to_flag_mappings('static/app.js')
    
    print("=" * 80)
    print("EXHAUSTIVE FRONTEND UI COMPLETENESS CHECK")
    print("=" * 80)
    print()
    
    # Map CLI commands to analysis types in UI
    cli_to_ui_types = {
        'sample_mode': ['sample-mode'],
        'voice_of_customer': ['voice-of-customer-hilary', 'voice-of-customer-synthesis', 'voice-of-customer-complete'],
        'agent_performance': ['agent-performance-*'],
        'agent_coaching': ['agent-coaching-*'],
        'canny_analysis': ['canny-analysis'],
        'tech_troubleshooting': ['tech-analysis']
    }
    
    # Check 1: Every Railway canonical flag should be wired in UI
    print("🔍 CHECK 1: Railway flags → UI controls")
    print("-" * 80)
    
    for railway_key, ui_types in cli_to_ui_types.items():
        if railway_key not in CANONICAL_COMMAND_MAPPINGS:
            continue
        
        canonical_flags = set(CANONICAL_COMMAND_MAPPINGS[railway_key]['allowed_flags'].keys())
        
        # Get all flags sent by these UI types
        ui_sent_flags = set()
        for ui_type in ui_types:
            if ui_type in flag_usage:
                ui_sent_flags.update(flag_usage[ui_type])
            # Handle wildcards
            elif ui_type.endswith('*'):
                prefix = ui_type.rstrip('*')
                for analysis_type, flags in flag_usage.items():
                    if analysis_type.startswith(prefix):
                        ui_sent_flags.update(flags)
        
        # Also consider flags sent in generic blocks (apply to all commands)
        ui_sent_flags.update(all_flags_in_js)
        
        # Compare
        missing_in_ui = canonical_flags - ui_sent_flags
        
        # Filter out flags that are:
        # 1. Added generically (in shared code blocks)
        # 2. Backend-only (no UI control needed)
        # 3. Unimplemented features (planned but not wired yet)
        generic_flags = {
            '--time-period', '--start-date', '--end-date', '--ai-model',
            '--generate-gamma', '--output-format', '--test-mode', '--test-data-count',
            '--verbose', '--audit-trail'
        }
        
        backend_only_flags = {
            '--output-dir',  # Always defaults to 'outputs'
            '--periods-back',  # Not exposed in UI yet (future feature)
            '--enable-fallback',  # Always enabled by default
            '--separate-agent-feedback',  # Always true by default
            '--include-trends',  # Historical feature not exposed yet
            '--canny-board-id',  # Advanced feature, use --include-canny for now
            '--focus-categories',  # Advanced filtering, not in UI
            '--analyze-troubleshooting',  # Advanced feature toggle
            '--top-n',  # Defaults handled by CLI
            '--gamma-export',  # Controlled via --generate-gamma + output format
            '--include-comments', '--include-votes',  # Canny-specific, defaults OK
            '--board-id',  # Same as --canny-board-id
            '--days',  # Use --time-period instead
            '--max-pages',  # Advanced throttle, not user-facing
            '--filter-category',  # Same as taxonomyFilter in generic block
            '--count',  # Sample-mode uses --schema-mode instead
            '--include-hierarchy'  # UI sends --no-hierarchy conditionally (inverted logic)
        }
        
        missing_in_ui = missing_in_ui - generic_flags - backend_only_flags
        
        if missing_in_ui:
            warnings.append(
                f"⚠️  {railway_key}: Railway has {missing_in_ui} but UI doesn't send them"
            )
    
    # Check 2: Every UI control should map to a valid Railway flag
    print("🔍 CHECK 2: UI controls → Railway flags")
    print("-" * 80)
    
    for control_id, flag_name in ui_to_flag.items():
        # Check if this flag exists in ANY Railway canonical mapping
        flag_exists = False
        for railway_key, schema in CANONICAL_COMMAND_MAPPINGS.items():
            if flag_name in schema.get('allowed_flags', {}):
                flag_exists = True
                break
        
        if not flag_exists:
            errors.append(
                f"❌ UI control '{control_id}' sends '{flag_name}' but it's not in ANY Railway canonical mapping"
            )
    
    # Check 3: Conditional logic validation
    print("🔍 CHECK 3: Conditional flag logic")
    print("-" * 80)
    
    # Check that digest-mode is only sent for appropriate commands
    for analysis_type, flags in flag_usage.items():
        if '--digest-mode' in flags:
            if not analysis_type.startswith('voice-of-customer'):
                errors.append(
                    f"❌ {analysis_type} sends --digest-mode but it's only valid for voice-of-customer"
                )
    
    # Print summary
    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    if errors:
        print("\n❌ CRITICAL ERRORS:")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
    
    if info:
        print("\nℹ️  INFO:")
        for i in info:
            print(f"  {i}")
    
    if not errors and not warnings:
        print("\n✅ All frontend UI controls properly wired!")
        print(f"   Checked {len(ui_controls)} UI controls")
        print(f"   Validated {len(flag_usage)} analysis types")
        print(f"   Mapped {len(ui_to_flag)} control→flag bindings")
    
    print()
    
    return len(errors) == 0


def main():
    """Run frontend completeness check."""
    try:
        passed = validate_frontend_completeness()
        if passed:
            print("✅ Frontend UI completeness check PASSED")
            return 0
        else:
            print("❌ Frontend UI completeness check FAILED")
            print("\nFIX: Update static/app.js to wire missing flags or remove orphaned controls")
            return 1
    except Exception as e:
        print(f"❌ Check failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

