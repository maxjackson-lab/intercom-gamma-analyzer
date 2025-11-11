#!/usr/bin/env python3
"""
Pydantic Model Instantiation Validator

Validates that all Pydantic model instantiations provide required fields:
1. Finds all Pydantic BaseModel subclasses
2. Extracts required fields (no default value)
3. Scans for model instantiations (ClassName(...))
4. Validates all required fields are provided

Prevents: Pydantic ValidationError at runtime
Priority: P0 (Critical)

Example Caught Issues:
- AgentContext created without analysis_type
- SnapshotData missing required fields
- Any BaseModel instantiation with missing required params
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict


class PydanticInstantiationChecker:
    """AST-based Pydantic model instantiation validation."""
    
    def __init__(self, src_dir: Path):
        self.src_dir = src_dir
        self.pydantic_models: Dict[str, Dict[str, Any]] = {}
        self.instantiations: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
    
    def check_all_files(self) -> List[Dict[str, Any]]:
        """Check all Python files in src directory."""
        # Phase 1: Find all Pydantic models and their required fields
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            self._extract_pydantic_models(py_file)
        
        # Phase 2: Find all model instantiations
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            self._extract_instantiations(py_file)
        
        # Phase 3: Validate instantiations
        self._validate_instantiations()
        
        return self.errors
    
    def _extract_pydantic_models(self, file_path: Path):
        """Extract Pydantic model definitions and required fields."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                
                # Check if it's a Pydantic model (inherits from BaseModel)
                is_pydantic = any(
                    (isinstance(base, ast.Name) and base.id == 'BaseModel') or
                    (isinstance(base, ast.Attribute) and base.attr == 'BaseModel')
                    for base in node.bases
                )
                
                if not is_pydantic:
                    continue
                
                # Extract required fields (annotated assignments without defaults)
                required_fields = set()
                optional_fields = set()
                
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        field_name = item.target.id
                        
                        # Check if field has a default value
                        has_default = item.value is not None
                        
                        # Check if it's Optional (has default None or Field(default=...))
                        is_optional = self._is_optional_type(item.annotation)
                        
                        if has_default or is_optional:
                            optional_fields.add(field_name)
                        else:
                            required_fields.add(field_name)
                
                # Store model info
                class_name = node.name
                self.pydantic_models[class_name] = {
                    'file': str(file_path),
                    'line': node.lineno,
                    'required_fields': required_fields,
                    'optional_fields': optional_fields
                }
        
        except SyntaxError:
            pass  # Skip files with syntax errors
        except Exception:
            pass  # Skip files we can't parse
    
    def _is_optional_type(self, annotation) -> bool:
        """Check if a type annotation indicates an optional field."""
        if isinstance(annotation, ast.Subscript):
            # Check for Optional[...] or Union[..., None]
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == 'Optional':
                    return True
        return False
    
    def _extract_instantiations(self, file_path: Path):
        """Extract all model instantiations from a file."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                
                # Get the class name being instantiated
                class_name = None
                if isinstance(node.func, ast.Name):
                    class_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    class_name = node.func.attr
                
                if not class_name or class_name not in self.pydantic_models:
                    continue
                
                # Extract provided keyword arguments
                provided_kwargs = set()
                for keyword in node.keywords:
                    if keyword.arg:  # Skip **kwargs
                        provided_kwargs.add(keyword.arg)
                
                # Store instantiation
                self.instantiations.append({
                    'file': str(file_path),
                    'line': node.lineno,
                    'class_name': class_name,
                    'provided_kwargs': provided_kwargs,
                    'has_kwargs_splat': any(kw.arg is None for kw in node.keywords)
                })
        
        except SyntaxError:
            pass
        except Exception:
            pass
    
    def _validate_instantiations(self):
        """Validate that instantiations provide all required fields."""
        for inst in self.instantiations:
            class_name = inst['class_name']
            model_info = self.pydantic_models[class_name]
            required = model_info['required_fields']
            provided = inst['provided_kwargs']
            has_kwargs = inst['has_kwargs_splat']
            
            # Skip validation if **kwargs is used (could provide anything)
            if has_kwargs:
                continue
            
            # Find missing required fields
            missing = required - provided
            
            if missing:
                # Format missing fields for display
                missing_list = sorted(missing)
                
                self.errors.append({
                    'type': 'missing_required_fields',
                    'severity': 'critical',
                    'file': inst['file'],
                    'line': inst['line'],
                    'class': class_name,
                    'missing': missing_list,
                    'provided': sorted(provided),
                    'model_file': model_info['file'],
                    'model_line': model_info['line']
                })


def main():
    """Run Pydantic instantiation validation."""
    print("="*80)
    print("PYDANTIC MODEL INSTANTIATION VALIDATOR")
    print("="*80)
    print()
    
    # Check if we're in the right directory
    src_dir = Path(__file__).parent.parent / 'src'
    if not src_dir.exists():
        print("❌ Error: src/ directory not found")
        return 1
    
    checker = PydanticInstantiationChecker(src_dir)
    
    print(f"📂 Scanning {src_dir}")
    print(f"   Looking for Pydantic models and instantiations...")
    print()
    
    errors = checker.check_all_files()
    
    # Report findings
    print(f"📊 Found {len(checker.pydantic_models)} Pydantic model(s)")
    print(f"📊 Found {len(checker.instantiations)} instantiation(s)")
    print()
    
    if not errors:
        print("✅ All Pydantic model instantiations provide required fields!")
        return 0
    
    # Group by severity
    critical = [e for e in errors if e.get('severity') == 'critical']
    warnings = [e for e in errors if e.get('severity') == 'warning']
    
    print(f"⚠️  Found {len(errors)} issue(s):")
    print(f"   Critical: {len(critical)}")
    print(f"   Warnings: {len(warnings)}")
    print()
    
    if critical:
        print("🔴 CRITICAL ISSUES (Will cause Pydantic ValidationError at runtime):")
        print()
        for i, error in enumerate(critical, 1):
            print(f"{i}. {error['file']}:{error['line']}")
            print(f"   Class: {error['class']}")
            print(f"   Missing required fields: {', '.join(error['missing'])}")
            print(f"   Provided fields: {', '.join(error['provided']) if error['provided'] else '(none)'}")
            print(f"   Model defined at: {error['model_file']}:{error['model_line']}")
            print()
            print(f"   Fix: Add missing fields to {error['class']} instantiation:")
            for field in error['missing']:
                print(f"        {field}=...,")
            print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for error in warnings:
            print(f"   {error['file']}:{error['line']}")
            print(f"   {error.get('message', 'Unknown warning')}")
            print()
    
    if critical:
        print("❌ Critical issues found! These will cause runtime errors.")
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())

