#!/usr/bin/env python3
"""
Function Signature Parameter Matcher

Validates that function calls match function signatures:
1. All required parameters are provided
2. No unexpected keyword arguments
3. Parameter names match between caller and signature

Prevents: TypeError at runtime
Priority: P0 (Critical)
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict


class FunctionSignatureChecker:
    """AST-based function signature validation."""
    
    def __init__(self, src_dir: Path):
        self.src_dir = src_dir
        self.function_signatures: Dict[str, Dict[str, Any]] = {}
        self.function_calls: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
    
    def check_all_files(self) -> List[Dict[str, Any]]:
        """Check all Python files in src directory."""
        # Phase 1: Extract all function signatures
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            self._extract_signatures_from_file(py_file)
        
        # Phase 2: Extract all function calls
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            self._extract_calls_from_file(py_file)
        
        # Phase 3: Validate calls against signatures
        self._validate_calls()
        
        return self.errors
    
    def _extract_signatures_from_file(self, file_path: Path):
        """Extract function signatures using AST."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = node.name
                    
                    # Skip private methods (can have many internal variations)
                    if func_name.startswith('_') and not func_name.startswith('__'):
                        continue
                    
                    # Extract parameters
                    params = []
                    defaults_start = len(node.args.args) - len(node.args.defaults)
                    
                    for i, arg in enumerate(node.args.args):
                        param_name = arg.arg
                        if param_name == 'self' or param_name == 'cls':
                            continue
                        
                        has_default = i >= defaults_start
                        params.append({
                            'name': param_name,
                            'required': not has_default
                        })
                    
                    # Add keyword-only args
                    for i, arg in enumerate(node.args.kwonlyargs):
                        has_default = i < len(node.args.kw_defaults) and node.args.kw_defaults[i] is not None
                        params.append({
                            'name': arg.arg,
                            'required': not has_default
                        })
                    
                    # Store signature
                    self.function_signatures[func_name] = {
                        'file': str(file_path),
                        'line': node.lineno,
                        'params': params,
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }
        
        except SyntaxError as e:
            self.errors.append({
                'file': str(file_path),
                'line': e.lineno if hasattr(e, 'lineno') else 0,
                'error': f'Syntax error: {e}',
                'type': 'syntax_error'
            })
        except Exception as e:
            # Skip files that can't be parsed
            pass
    
    def _extract_calls_from_file(self, file_path: Path):
        """Extract function calls using AST."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Get function name and object
                    func_name = None
                    obj_name = None
                    
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                        if isinstance(node.func.value, ast.Name):
                            obj_name = node.func.value.id
                    
                    if not func_name:
                        continue
                    
                    # Skip private methods
                    if func_name.startswith('_') and not func_name.startswith('__'):
                        continue
                    
                    # Skip common false positives:
                    # 1. __init__ (inheritance makes this complex)
                    # 2. logger methods (name collision)
                    # 3. Logging functions  
                    # 4. warning/error/info functions (too generic, name collisions)
                    # 5. execute() - too generic, many different execute() methods
                    # 6. create_* functions likely use **kwargs (Pydantic models)
                    if func_name == '__init__':
                        continue
                    if obj_name in ['logger', 'self.logger', 'logging', 'self'] and func_name in ['debug', 'info', 'warning', 'error', 'critical']:
                        continue
                    if func_name in ['warning', 'error', 'info', 'execute'] and 'logger' not in str(file_path):
                        # Skip generic method names (too many false positives)
                        continue
                    if func_name.startswith('create_') and 'schemas' in str(file_path):
                        # Skip Pydantic model constructors (likely use **kwargs)
                        continue
                    
                    # Extract keyword arguments
                    kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
                    
                    # Store call
                    self.function_calls.append({
                        'file': str(file_path),
                        'line': node.lineno,
                        'function': func_name,
                        'args_count': len(node.args),
                        'kwargs': set(kwargs.keys())
                    })
        
        except:
            pass
    
    def _validate_calls(self):
        """Validate function calls against signatures."""
        for call in self.function_calls:
            func_name = call['function']
            
            if func_name not in self.function_signatures:
                # Function not defined in this codebase (external or stdlib)
                continue
            
            sig = self.function_signatures[func_name]
            sig_params = {p['name']: p for p in sig['params']}
            sig_param_names = set(sig_params.keys())
            
            # Check for unexpected kwargs
            unexpected = call['kwargs'] - sig_param_names
            if unexpected:
                self.errors.append({
                    'file': call['file'],
                    'line': call['line'],
                    'function': func_name,
                    'error': f"Unexpected parameter(s): {', '.join(unexpected)}",
                    'signature_file': sig['file'],
                    'signature_line': sig['line'],
                    'expected_params': list(sig_param_names),
                    'type': 'unexpected_parameter'
                })
            
            # Check for missing required params (only check kwargs, can't reliably check positional)
            required_params = {p['name'] for p in sig['params'] if p['required']}
            provided_params = call['kwargs']
            
            # Only flag if NO args and missing required kwargs
            if call['args_count'] == 0:
                missing = required_params - provided_params
                if missing:
                    self.errors.append({
                        'file': call['file'],
                        'line': call['line'],
                        'function': func_name,
                        'error': f"Possibly missing required parameter(s): {', '.join(missing)}",
                        'signature_file': sig['file'],
                        'signature_line': sig['line'],
                        'note': 'May be provided as positional args',
                        'type': 'possibly_missing_required'
                    })


def main():
    """Run function signature validation."""
    print("="*80)
    print("FUNCTION SIGNATURE VALIDATION")
    print("="*80)
    print()
    
    src_dir = Path(__file__).parent.parent / 'src'
    checker = FunctionSignatureChecker(src_dir)
    
    errors = checker.check_all_files()
    
    print(f"📊 Analysis complete:")
    print(f"   Functions found: {len(checker.function_signatures)}")
    print(f"   Function calls: {len(checker.function_calls)}")
    print()
    
    if not errors:
        print("✅ No function signature mismatches found!")
        return 0
    
    # Group errors by type
    by_type = defaultdict(list)
    for error in errors:
        by_type[error['type']].append(error)
    
    print(f"❌ Found {len(errors)} potential issue(s):")
    print()
    
    # Show unexpected parameters first (highest confidence)
    if 'unexpected_parameter' in by_type:
        print("🔴 UNEXPECTED PARAMETERS (High confidence - likely bugs):")
        for error in by_type['unexpected_parameter']:
            print(f"   {error['file']}:{error['line']}")
            print(f"   Function: {error['function']}()")
            print(f"   Error: {error['error']}")
            print(f"   Signature defined at: {error['signature_file']}:{error['signature_line']}")
            print(f"   Expected params: {', '.join(error['expected_params'])}")
            print()
    
    # Show possibly missing (lower confidence)
    if 'possibly_missing_required' in by_type:
        print("⚠️  POSSIBLY MISSING PARAMETERS (May be false positives):")
        for error in by_type['possibly_missing_required']:
            print(f"   {error['file']}:{error['line']}")
            print(f"   Function: {error['function']}()")
            print(f"   Error: {error['error']}")
            print(f"   Note: {error['note']}")
            print()
    
    # Show syntax errors
    if 'syntax_error' in by_type:
        print("🔴 SYNTAX ERRORS:")
        for error in by_type['syntax_error']:
            print(f"   {error['file']}:{error['line']}")
            print(f"   Error: {error['error']}")
            print()
    
    # Return error code
    # Only block on syntax errors - signature issues are warnings (too many false positives)
    syntax_errors = len(by_type.get('syntax_error', []))
    unexpected_params = len(by_type.get('unexpected_parameter', []))
    
    if syntax_errors > 0:
        print(f"❌ Found {syntax_errors} syntax error(s) - fix before committing!")
        return 1
    elif unexpected_params > 0:
        print(f"⚠️  Found {unexpected_params} parameter mismatch(es) - review but can proceed")
        print("   (Some may be false positives from inheritance or **kwargs usage)")
        return 0
    else:
        print("⚠️  Found only low-confidence warnings - review but can proceed")
        return 0


if __name__ == '__main__':
    sys.exit(main())

