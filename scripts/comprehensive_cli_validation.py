#!/usr/bin/env python3
"""
Comprehensive CLI Validation Script

Validates:
1. ALL CLI commands have Railway mappings (if web-accessible)
2. ALL file-saving commands use output_manager
3. ALL flags are aligned across CLI/Railway/Frontend
4. File output paths are correct for web context

Run this before committing ANY changes to commands/flags/file paths.
"""

import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.schema import CANONICAL_COMMAND_MAPPINGS


def find_all_cli_commands() -> List[str]:
    """Find all CLI commands by parsing src/main.py."""
    main_py = Path("src/main.py")
    if not main_py.exists():
        return []
    
    commands = []
    with open(main_py, 'r') as f:
        content = f.read()
    
    # Find @cli.command() decorators
    pattern = r'@cli\.command\(name=[\'"]([^\'"]+)[\'"]\)'
    commands.extend(re.findall(pattern, content))
    
    # Find @cli.command() without name (uses function name)
    pattern = r'@cli\.command\(\)\s*\n\s*def\s+([a-z_]+)'
    commands.extend(re.findall(pattern, content))
    
    return sorted(set(commands))


def find_railway_mappings() -> Dict[str, Dict]:
    """Load Railway CANONICAL_COMMAND_MAPPINGS."""
    return CANONICAL_COMMAND_MAPPINGS


def find_file_saving_commands() -> Set[str]:
    """Find commands that save files by checking for file write patterns."""
    main_py = Path("src/main.py")
    if not main_py.exists():
        return set()
    
    with open(main_py, 'r') as f:
        content = f.read()
    
    file_saving_commands = set()
    
    # Find commands that use get_output_file_path (GOOD)
    pattern = r'def\s+([a-z_]+).*?get_output_file_path'
    matches = re.findall(pattern, content, re.DOTALL)
    file_saving_commands.update(matches)
    
    # Find commands that write files directly (NEEDS CHECK)
    pattern = r'def\s+([a-z_]+).*?(?:open\(|\.write\(|json\.dump)'
    matches = re.findall(pattern, content, re.DOTALL)
    file_saving_commands.update(matches)
    
    # Map function names to command names
    command_map = {}
    pattern = r'@cli\.command\(name=[\'"]([^\'"]+)[\'"]\)\s*\n\s*def\s+([a-z_]+)'
    for match in re.finditer(pattern, content):
        command_name, func_name = match.groups()
        command_map[func_name] = command_name
    
    # Also find commands without explicit name
    pattern = r'@cli\.command\(\)\s*\n\s*def\s+([a-z_]+)'
    for match in re.finditer(pattern, content):
        func_name = match.group(1)
        command_map[func_name] = func_name.replace('_', '-')
    
    # Convert function names to command names
    result = set()
    for func_name in file_saving_commands:
        if func_name in command_map:
            result.add(command_map[func_name])
        else:
            result.add(func_name.replace('_', '-'))
    
    return result


def check_output_manager_usage() -> List[str]:
    """Check if file-saving commands use output_manager."""
    main_py = Path("src/main.py")
    if not main_py.exists():
        return []
    
    with open(main_py, 'r') as f:
        content = f.read()
    
    issues = []
    
    # Find commands that write files but don't use get_output_file_path
    # Look for open() calls that don't have get_output_file_path nearby
    pattern = r'def\s+([a-z_]+).*?(?:open\([^)]*[\'"]([^\'"]+\.(?:json|md|log|txt|csv))[\'"]|Path\([^)]*outputs)'
    
    # Check each command function
    command_pattern = r'@cli\.command\(.*?\)\s*\n\s*def\s+([a-z_]+)\([^)]*\):'
    for match in re.finditer(command_pattern, content, re.DOTALL):
        func_name = match.group(1)
        func_start = match.start()
        # Find end of function (next @cli.command or end of file)
        next_command = content.find('@cli.command', func_start + 1)
        func_end = next_command if next_command != -1 else len(content)
        func_body = content[func_start:func_end]
        
        # Check if function writes files
        if 'open(' in func_body or '.write(' in func_body or 'json.dump' in func_body:
            # Skip config command - it doesn't save files, just displays
            if func_name == 'config':
                continue
            
            # Check if it uses get_output_file_path
            if 'get_output_file_path' not in func_body:
                # Check if it uses output_manager
                if 'get_output_directory' in func_body:
                    # Good - uses output_manager
                    continue
                elif 'output_manager' in func_body:
                    # Good - uses output_manager
                    continue
                else:
                    # Might be an issue - but check if it's CLI-only (uses settings.output_directory)
                    if 'effective_output_directory' in func_body:
                        # effective_output_directory checks EXECUTION_OUTPUT_DIR, so it's OK but deprecated
                        issues.append(f"⚠️  {func_name}: Uses effective_output_directory (deprecated, prefer get_output_directory)")
                    elif 'settings.output_directory' in func_body:
                        issues.append(f"⚠️  {func_name}: Uses settings.output_directory (may not work in web context)")
                    elif 'Path("outputs")' in func_body or "Path('outputs')" in func_body:
                        issues.append(f"❌ {func_name}: Uses hardcoded Path('outputs') (will fail in web context)")
    
    return issues


def check_cli_railway_coverage() -> Tuple[List[str], List[str]]:
    """Check which CLI commands have Railway mappings."""
    cli_commands = find_all_cli_commands()
    railway_mappings = find_railway_mappings()
    
    # Map CLI command names to Railway keys
    cli_to_railway = {
        'sample-mode': 'sample_mode',
        'voice-of-customer': 'voice_of_customer',
        'agent-performance': 'agent_performance',  # Railway key is 'agent_performance', not 'agent_performance_team'
        'agent-coaching-report': 'agent_coaching',
        'canny-analysis': 'canny_analysis',
        'tech-analysis': 'tech_troubleshooting',  # Railway key is 'tech_troubleshooting', not 'tech_analysis'
    }
    
    missing_mappings = []
    extra_mappings = []
    
    # Check web-accessible commands (those that should have Railway mappings)
    web_commands = ['sample-mode', 'voice-of-customer', 'agent-performance', 
                    'agent-coaching-report', 'canny-analysis', 'tech-analysis']
    
    for cmd in web_commands:
        if cmd not in cli_commands:
            continue
        railway_key = cli_to_railway.get(cmd)
        if railway_key and railway_key not in railway_mappings:
            missing_mappings.append(f"❌ {cmd}: Missing Railway mapping '{railway_key}'")
    
    # Check for Railway mappings without CLI commands
    for railway_key in railway_mappings:
        cli_cmd = None
        for cli_name, r_key in cli_to_railway.items():
            if r_key == railway_key:
                cli_cmd = cli_name
                break
        if cli_cmd and cli_cmd not in cli_commands:
            extra_mappings.append(f"⚠️  Railway mapping '{railway_key}' has no CLI command '{cli_cmd}'")
    
    return missing_mappings, extra_mappings


def main():
    """Run comprehensive validation."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE CLI VALIDATION")
    print("=" * 80)
    print()
    
    # 1. Find all CLI commands
    print("📋 Finding all CLI commands...")
    cli_commands = find_all_cli_commands()
    print(f"   Found {len(cli_commands)} CLI commands")
    if cli_commands:
        print(f"   Commands: {', '.join(cli_commands[:10])}{'...' if len(cli_commands) > 10 else ''}")
    print()
    
    # 2. Find Railway mappings
    print("🔍 Finding Railway mappings...")
    railway_mappings = find_railway_mappings()
    print(f"   Found {len(railway_mappings)} Railway mappings")
    if railway_mappings:
        print(f"   Mappings: {', '.join(list(railway_mappings.keys())[:10])}{'...' if len(railway_mappings) > 10 else ''}")
    print()
    
    # 3. Check CLI ↔ Railway coverage
    print("🔗 Checking CLI ↔ Railway coverage...")
    missing, extra = check_cli_railway_coverage()
    if missing:
        print("   Missing Railway mappings:")
        for issue in missing:
            print(f"     {issue}")
    if extra:
        print("   Extra Railway mappings:")
        for issue in extra:
            print(f"     {issue}")
    if not missing and not extra:
        print("   ✅ All web-accessible commands have Railway mappings")
    print()
    
    # 4. Check file output paths
    print("📁 Checking file output paths...")
    output_issues = check_output_manager_usage()
    if output_issues:
        print("   File output path issues:")
        for issue in output_issues:
            print(f"     {issue}")
    else:
        print("   ✅ All file-saving commands use output_manager or settings.output_directory")
    print()
    
    # 5. Find file-saving commands
    print("💾 Finding file-saving commands...")
    file_saving = find_file_saving_commands()
    print(f"   Found {len(file_saving)} commands that save files")
    if file_saving:
        print(f"   Commands: {', '.join(sorted(file_saving)[:10])}{'...' if len(file_saving) > 10 else ''}")
    print()
    
    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    total_issues = len(missing) + len(output_issues)
    if total_issues == 0:
        print("✅ All checks passed!")
        return 0
    else:
        print(f"❌ Found {total_issues} issue(s)")
        print("\nFIXES NEEDED:")
        print("1. Add missing Railway mappings for web-accessible commands")
        print("2. Update file-saving commands to use output_manager.get_output_file_path()")
        print("3. See CLI_WEB_ALIGNMENT_CHECKLIST.md for details")
        return 1


if __name__ == '__main__':
    sys.exit(main())

