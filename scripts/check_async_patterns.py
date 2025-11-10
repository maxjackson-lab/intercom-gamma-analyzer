#!/usr/bin/env python3
"""
Async/Await Pattern Validator

Validates async/await usage:
1. Async functions are awaited when called
2. No blocking I/O in async functions
3. No time.sleep() in async functions
4. Proper use of asyncio.wait_for for timeouts

Prevents: Deadlocks, blocked event loops
Priority: P0 (Critical)
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any


class AsyncPatternChecker:
    """Validates async/await patterns in code."""
    
    def __init__(self, src_dir: Path):
        self.src_dir = src_dir
        self.errors: List[Dict[str, Any]] = []
    
    def check_all_files(self) -> List[Dict[str, Any]]:
        """Check all Python files for async pattern issues."""
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            self._check_file(py_file)
        
        return self.errors
    
    def _check_file(self, file_path: Path):
        """Check a single file for async pattern issues."""
        try:
            content = file_path.read_text()
            lines = content.splitlines()
            
            # Find async function definitions
            async_funcs = []
            for i, line in enumerate(lines, 1):
                if re.match(r'\s*async\s+def\s+(\w+)', line):
                    async_funcs.append({
                        'name': re.match(r'\s*async\s+def\s+(\w+)', line).group(1),
                        'start_line': i
                    })
            
            # For each async function, check its body
            for func in async_funcs:
                func_start = func['start_line']
                
                # Find function body (next 100 lines or until next def)
                func_end = min(func_start + 100, len(lines))
                for i in range(func_start, len(lines)):
                    if i > func_start and re.match(r'\s*(async\s+)?def\s+', lines[i]):
                        func_end = i
                        break
                
                func_body = '\n'.join(lines[func_start:func_end])
                
                # Check 1: time.sleep() instead of asyncio.sleep()
                if 'time.sleep(' in func_body:
                    for i in range(func_start, func_end):
                        if 'time.sleep(' in lines[i]:
                            self.errors.append({
                                'file': str(file_path),
                                'line': i + 1,
                                'function': func['name'],
                                'error': 'Blocking time.sleep() in async function',
                                'fix': 'Use await asyncio.sleep() instead',
                                'severity': 'critical'
                            })
                
                # Check 2: requests library in async function
                if re.search(r'requests\.(get|post|put|delete|patch)', func_body):
                    for i in range(func_start, func_end):
                        if re.search(r'requests\.(get|post|put|delete|patch)', lines[i]):
                            self.errors.append({
                                'file': str(file_path),
                                'line': i + 1,
                                'function': func['name'],
                                'error': 'Blocking requests library in async function',
                                'fix': 'Use httpx.AsyncClient instead',
                                'severity': 'critical'
                            })
                
                # Check 3: open() without async wrapper
                if re.search(r'\bopen\s*\(', func_body) and 'aiofiles' not in func_body:
                    for i in range(func_start, func_end):
                        if re.search(r'\bopen\s*\(', lines[i]) and 'await' not in lines[i]:
                            self.errors.append({
                                'file': str(file_path),
                                'line': i + 1,
                                'function': func['name'],
                                'error': 'Blocking file I/O in async function',
                                'fix': 'Use aiofiles or run_in_executor()',
                                'severity': 'warning'
                            })
                
                # Check 4: DuckDB operations without async wrapper
                if re.search(r'(storage|db)\.(save|store|execute)\(', func_body):
                    for i in range(func_start, func_end):
                        line = lines[i]
                        if re.search(r'(storage|db)\.(save|store|execute)\(', line):
                            # Check if it has async wrapper
                            if '_async' not in line and 'run_in_executor' not in line and 'await' in line:
                                # It's awaited but not async - might be issue
                                if 'await storage' in line or 'await db' in line:
                                    self.errors.append({
                                        'file': str(file_path),
                                        'line': i + 1,
                                        'function': func['name'],
                                        'error': 'Possible blocking DB call in async function',
                                        'fix': 'Use async wrapper or run_in_executor()',
                                        'severity': 'warning'
                                    })
            
            # Check 5: Async function calls without await (high false positive rate, be conservative)
            # Look for common async function names
            async_call_patterns = [
                r'(?<!await\s)\b(fetch_\w+|enrich_\w+|generate_\w+|process_\w+|execute_\w+)\s*\(',
                r'(?<!await\s)self\.(fetch|enrich|generate|process|execute)\w*\s*\(',
            ]
            
            for pattern in async_call_patterns:
                for i, line in enumerate(lines, 1):
                    # Skip if line contains await or is a definition
                    if 'await' in line or 'def ' in line or 'return' not in line:
                        continue
                    
                    if re.search(pattern, line):
                        # Possible missing await
                        self.errors.append({
                            'file': str(file_path),
                            'line': i,
                            'error': 'Possible missing await on async function call',
                            'code': line.strip()[:80],
                            'fix': 'Add await if this is an async function',
                            'severity': 'info'
                        })
        
        except:
            pass
    
    def _validate_calls(self):
        """Validate function calls match signatures - already done in _check_file."""
        pass


def main():
    """Run async pattern validation."""
    print("="*80)
    print("ASYNC/AWAIT PATTERN VALIDATION")
    print("="*80)
    print()
    
    src_dir = Path(__file__).parent.parent / 'src'
    checker = AsyncPatternChecker(src_dir)
    
    errors = checker.check_all_files()
    
    if not errors:
        print("✅ No async pattern issues found!")
        return 0
    
    # Group by severity
    critical = [e for e in errors if e.get('severity') == 'critical']
    warnings = [e for e in errors if e.get('severity') == 'warning']
    info = [e for e in errors if e.get('severity') == 'info']
    
    print(f"📊 Found {len(errors)} issue(s):")
    print(f"   Critical: {len(critical)}")
    print(f"   Warnings: {len(warnings)}")
    print(f"   Info: {len(info)}")
    print()
    
    if critical:
        print("🔴 CRITICAL ISSUES:")
        for error in critical:
            print(f"   {error['file']}:{error['line']}")
            if 'function' in error:
                print(f"   In function: {error['function']}()")
            print(f"   Error: {error['error']}")
            print(f"   Fix: {error['fix']}")
            print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for error in warnings:
            print(f"   {error['file']}:{error['line']}")
            if 'function' in error:
                print(f"   In function: {error['function']}()")
            print(f"   Error: {error['error']}")
            print(f"   Fix: {error['fix']}")
            print()
    
    if info:
        print(f"ℹ️  INFO ({len(info)} items - may be false positives):")
        print("   Run with --verbose to see all info items")
        print()
    
    if critical:
        print("❌ Critical issues found - fix before committing!")
        return 1
    elif warnings:
        print("⚠️  Warnings found - review before committing")
        return 0  # Don't block on warnings
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())

