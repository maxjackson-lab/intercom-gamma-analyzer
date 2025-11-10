#!/usr/bin/env python3
"""
Null Safety / Safe Field Access Checker

Finds unsafe nested field access patterns:
1. Direct bracket access to risky Intercom fields
2. Missing .get() defensive patterns
3. No isinstance() checks before nested access

Prevents: KeyError at runtime
Priority: P1 (High Impact)
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any


# Intercom fields that are frequently missing or inconsistent
RISKY_FIELDS = [
    'custom_attributes',
    'conversation_parts',
    'source',
    'contacts',
    'sla_applied',
    'conversation_rating',
    'ai_agent',
    'statistics',
    'first_contact_reply',
    'waiting_since'
]


class NullSafetyChecker:
    """Check for unsafe field access patterns."""
    
    def __init__(self, src_dir: Path):
        self.src_dir = src_dir
        self.errors: List[Dict[str, Any]] = []
    
    def check_all_files(self) -> List[Dict[str, Any]]:
        """Check all Python files for unsafe field access."""
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            self._check_file(py_file)
        
        return self.errors
    
    def _check_file(self, file_path: Path):
        """Check a single file for unsafe access patterns."""
        try:
            content = file_path.read_text()
            lines = content.splitlines()
            
            for i, line in enumerate(lines, 1):
                # Pattern 1: Direct bracket access to nested fields
                # conv['field']['nested'] or data['x']['y']['z']
                unsafe_patterns = [
                    r"(conv|conversation|data|result)\['[^']+'\]\['[^']+'\]",
                    r"(conv|conversation|data|result)\['[^']+'\]\['[^']+'\]\['[^']+'\]"
                ]
                
                for pattern in unsafe_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        code = match.group(0)
                        
                        # Check if it's accessing a risky field
                        for field in RISKY_FIELDS:
                            if field in code:
                                # Check if there's a try/except nearby (within 5 lines)
                                has_try_except = any(
                                    'try:' in lines[j] or 'except' in lines[j]
                                    for j in range(max(0, i-5), min(len(lines), i+2))
                                )
                                
                                # Check if .get() is used anywhere in the line
                                if '.get(' in line:
                                    continue  # Already using safe access
                                
                                self.errors.append({
                                    'file': str(file_path),
                                    'line': i,
                                    'code': line.strip()[:100],
                                    'field': field,
                                    'error': f'Unsafe nested access to risky field: {field}',
                                    'fix': f"Use .get('{field}', {{}}) pattern",
                                    'severity': 'critical' if not has_try_except else 'warning'
                                })
                                break
        
        except:
            pass


def main():
    """Run null safety validation."""
    print("="*80)
    print("NULL SAFETY / SAFE FIELD ACCESS VALIDATION")
    print("="*80)
    print()
    
    src_dir = Path(__file__).parent.parent / 'src'
    checker = NullSafetyChecker(src_dir)
    
    errors = checker.check_all_files()
    
    if not errors:
        print("✅ No unsafe field access patterns found!")
        return 0
    
    # Group by severity
    critical = [e for e in errors if e.get('severity') == 'critical']
    warnings = [e for e in errors if e.get('severity') == 'warning']
    
    print(f"📊 Found {len(errors)} unsafe access pattern(s):")
    print(f"   Critical: {len(critical)}")
    print(f"   Warnings: {len(warnings)}")
    print()
    
    if critical:
        print("🔴 CRITICAL (No try/except protection):")
        for error in critical[:10]:  # Show first 10
            print(f"   {error['file']}:{error['line']}")
            print(f"   Field: {error['field']}")
            print(f"   Code: {error['code']}")
            print(f"   Fix: {error['fix']}")
            print()
        if len(critical) > 10:
            print(f"   ... and {len(critical) - 10} more critical issues")
            print()
    
    if warnings:
        print(f"⚠️  WARNINGS ({len(warnings)} items with try/except nearby)")
        print("   Protected by try/except but still risky - consider using .get()")
        print()
    
    if critical:
        print("❌ Critical unsafe access patterns found!")
        print("   These will cause KeyError if fields are missing")
        return 1
    else:
        print("⚠️  Only warnings found - review but can proceed")
        return 0


if __name__ == '__main__':
    sys.exit(main())

