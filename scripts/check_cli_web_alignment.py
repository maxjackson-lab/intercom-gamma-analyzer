#!/usr/bin/env python3
"""
Verify CLI ↔ Railway ↔ Frontend alignment.

This script checks that all flags are properly aligned across:
1. CLI definitions (src/main.py)
2. Schema (src/cli/schema.py) - CANONICAL_COMMAND_MAPPINGS
3. Frontend implementation (static/app.js)

Note: WebCommandExecutor schema is now AUTO-GENERATED from CANONICAL_COMMAND_MAPPINGS,
so Layer 3 (executor whitelist) no longer requires manual verification.

Run this before committing changes to commands/flags.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.schema import CANONICAL_COMMAND_MAPPINGS, DEFAULT_ALLOWED_MODULES


def check_cli_railway_alignment():
    """Check that CLI flags match Railway allowed_flags."""
    from src.main import cli
    
    errors = []
    warnings = []
    
    # Map CLI command names to Railway keys
    cli_to_railway = {
        'sample-mode': 'sample_mode',
        'voice-of-customer': 'voice_of_customer',
        'agent-performance': 'agent_performance_team',
        'agent-coaching-report': 'agent_coaching',
        'canny-analysis': 'canny_analysis',
        'tech-analysis': 'tech_analysis'
    }
    
    for cli_name, railway_key in cli_to_railway.items():
        if cli_name not in cli.commands:
            warnings.append(f"CLI command '{cli_name}' not found (might be renamed)")
            continue
        
        if railway_key not in CANONICAL_COMMAND_MAPPINGS:
            warnings.append(f"Railway key '{railway_key}' not found for CLI command '{cli_name}'")
            continue
        
        # Get CLI params (include all option aliases)
        cli_cmd = cli.commands[cli_name]
        cli_params = set()
        for param in cli_cmd.params:
            for opt in getattr(param, 'opts', []):
                if opt.startswith('--'):
                    cli_params.add(opt.lstrip('-'))
        
        # Get Railway flags
        railway_flags = set(CANONICAL_COMMAND_MAPPINGS[railway_key]['allowed_flags'].keys())
        railway_flags = {f.replace('--', '') for f in railway_flags}
        
        # Compare CLI ↔ Railway
        cli_only = cli_params - railway_flags
        railway_only = railway_flags - cli_params
        
        if cli_only:
            errors.append(f"❌ {cli_name}: CLI has {cli_only} but Railway doesn't")
        if railway_only:
            errors.append(f"❌ {cli_name}: Railway has {railway_only} but CLI doesn't")
    
    # Print results
    if errors:
        print("=" * 80)
        print("❌ CLI ↔ RAILWAY ALIGNMENT ERRORS FOUND")
        print("=" * 80)
        for error in errors:
            print(f"  {error}")
        print("\nFIX: Update CLI and Railway canonical mappings")
        print("(WebCommandExecutor schema is auto-generated)")
        print("See: CLI_WEB_ALIGNMENT_CHECKLIST.md")
        return False
    
    if warnings:
        print("=" * 80)
        print("⚠️  WARNINGS (not critical)")
        print("=" * 80)
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    print("=" * 80)
    print("✅ CLI ↔ RAILWAY ALIGNMENT CHECK PASSED")
    print("=" * 80)
    print(f"Checked {len(cli_to_railway)} commands")
    print("All flags properly aligned!\n")
    
    return True


def check_executor_generation():
    """Verify that WebCommandExecutor schema auto-generation works."""
    print("=" * 80)
    print("ℹ️  WEBCOMMANDEXECUTOR AUTO-GENERATION CHECK")
    print("=" * 80)
    
    try:
        from src.cli.schema import generate_executor_schema
        schema = generate_executor_schema()
        
        # Verify structure
        python_schema = schema.get('python')
        assert python_schema is not None, "Missing 'python' key in generated schema"
        assert 'allowed_flags' in python_schema, "Missing 'allowed_flags' in generated schema"
        assert 'flag_schemas' in python_schema, "Missing 'flag_schemas' in generated schema"
        assert 'allowed_modules' in python_schema, "Missing 'allowed_modules' in generated schema"
        
        # Verify it's not empty
        allowed_flags = python_schema['allowed_flags']
        assert len(allowed_flags) > 0, "Generated schema has no flags"
        
        # Verify allowed_modules matches canonical set
        allowed_modules = python_schema['allowed_modules']
        assert set(allowed_modules) == set(DEFAULT_ALLOWED_MODULES), (
            f"allowed_modules mismatch: expected {DEFAULT_ALLOWED_MODULES}, got {allowed_modules}"
        )
        
        # Verify allowed_flags behaves like a set for membership checks
        allowed_flag_set = set(allowed_flags)
        assert len(allowed_flag_set) == len(allowed_flags), "allowed_flags must contain unique entries"
        
        # Verify flag schemas align with WebCommandExecutor expectations
        supported_types = {'enum', 'int', 'date', 'string'}
        for flag_name, schema_entry in python_schema['flag_schemas'].items():
            flag_type = schema_entry.get('type')
            assert flag_type in supported_types, (
                f"Flag '{flag_name}' has unsupported schema type '{flag_type}'"
            )
            
            requires_value = schema_entry.get('requires_value')
            assert isinstance(requires_value, bool), (
                f"Flag '{flag_name}' missing boolean 'requires_value'"
            )
            
            if flag_type == 'enum':
                values = schema_entry.get('values')
                assert isinstance(values, (list, tuple)) and values, (
                    f"Flag '{flag_name}' enum values must be a non-empty list/tuple"
                )
            elif flag_type == 'int':
                for bound_key in ('min', 'max'):
                    if bound_key in schema_entry:
                        assert isinstance(schema_entry[bound_key], int), (
                            f"Flag '{flag_name}' {bound_key} must be int"
                        )
            elif flag_type == 'date':
                # No additional structure, but keep branch for symmetry
                pass
        
        print(f"  ✅ Generated schema with {len(allowed_flags)} flags")
        print(f"  ✅ Generated {len(python_schema['flag_schemas'])} flag validation schemas")
        print(f"  ✅ allowed_modules exactly matches {DEFAULT_ALLOWED_MODULES}")
        print()
        return True
    except Exception as e:
        print(f"  ❌ Schema generation failed: {e}")
        print()
        return False


def check_frontend_consistency():
    """Check that frontend doesn't send flags conditionally that should always be sent."""
    print("=" * 80)
    print("ℹ️  FRONTEND CONSISTENCY CHECK")
    print("=" * 80)
    
    # Read static/app.js
    try:
        with open('static/app.js', 'r') as f:
            js_content = f.read()
        
        # Look for common patterns
        issues = []
        
        # Check for hardcoded flag additions that might conflict
        if "args.push('--ai-model')" in js_content and "analysisType !== 'sample-mode'" not in js_content:
            issues.append("⚠️  --ai-model might be added to sample-mode unconditionally")
        
        if issues:
            for issue in issues:
                print(f"  {issue}")
            print("\n  Review static/app.js for conditional flag logic")
        else:
            print("  ✅ No obvious issues found in frontend flag handling")
        
        print()
    except FileNotFoundError:
        print("  ⚠️  static/app.js not found")
        print()


def main():
    """Run all alignment checks."""
    print("\n" + "=" * 80)
    print("CLI ↔ WEB UI ↔ RAILWAY ALIGNMENT CHECKER")
    print("=" * 80)
    print()
    
    # Check CLI ↔ Railway alignment
    railway_ok = check_cli_railway_alignment()
    
    # Check WebCommandExecutor auto-generation
    executor_ok = check_executor_generation()
    
    # Check Frontend consistency
    check_frontend_consistency()
    
    # Exit code
    if railway_ok and executor_ok:
        print("✅ All checks passed! Safe to commit.")
        return 0
    else:
        print("❌ Alignment errors found. Fix before committing.")
        print("See: CLI_WEB_ALIGNMENT_CHECKLIST.md")
        return 1


if __name__ == '__main__':
    sys.exit(main())
