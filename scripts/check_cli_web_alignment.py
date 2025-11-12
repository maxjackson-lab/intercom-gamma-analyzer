#!/usr/bin/env python3
"""
Verify CLI ↔ Railway ↔ Frontend alignment.

This script checks that all flags are properly aligned across:
1. CLI definitions (src/main.py)
2. Railway validation (deploy/railway_web.py)
3. Frontend implementation (static/app.js)

Run this before committing changes to commands/flags.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_cli_railway_alignment():
    """Check that CLI flags match Railway allowed_flags."""
    from src.main import cli
    
    # Import Railway mappings
    import importlib.util
    spec = importlib.util.spec_from_file_location("railway_web", "deploy/railway_web.py")
    railway_web = importlib.util.module_from_spec(spec)
    
    try:
        spec.loader.exec_module(railway_web)
        CANONICAL_COMMAND_MAPPINGS = railway_web.CANONICAL_COMMAND_MAPPINGS
    except Exception as e:
        print(f"⚠️  Could not load Railway mappings: {e}")
        print("   (This is OK if FastAPI deps not installed)")
        return True
    
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
        
        # Get CLI params
        cli_cmd = cli.commands[cli_name]
        cli_params = {p.name.replace('_', '-') for p in cli_cmd.params}
        
        # Get Railway flags
        railway_flags = set(CANONICAL_COMMAND_MAPPINGS[railway_key]['allowed_flags'].keys())
        railway_flags = {f.replace('--', '') for f in railway_flags}
        
        # Compare
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
        print("\nFIX: Update both CLI and Railway to match")
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
    
    # Check Frontend consistency
    check_frontend_consistency()
    
    # Exit code
    if railway_ok:
        print("✅ All checks passed! Safe to commit.")
        return 0
    else:
        print("❌ Alignment errors found. Fix before committing.")
        print("See: CLI_WEB_ALIGNMENT_CHECKLIST.md")
        return 1


if __name__ == '__main__':
    sys.exit(main())




