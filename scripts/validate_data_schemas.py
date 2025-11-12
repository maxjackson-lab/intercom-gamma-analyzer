#!/usr/bin/env python3
"""
Intercom Data Schema Validator

Validates conversation data structures from Intercom SDK:
1. conversation_parts is dict-wrapped (not list)
2. custom_attributes is dict (not null/other)
3. Rating is dict or int (not string)
4. Required fields are present

Prevents: Data pipeline crashes
Priority: P1 (High Impact)
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


class SchemaValidator:
    """Validates Intercom conversation schemas."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.outputs_dir = project_root / 'outputs'
        self.errors: List[Dict[str, Any]] = []
    
    def validate(self) -> List[Dict[str, Any]]:
        """Validate schemas from sample data."""
        # Find latest sample-mode output
        sample_file = self._find_latest_sample_file()
        
        if not sample_file:
            return [{
                'error': 'No sample data found',
                'fix': 'Run: python src/main.py sample-mode --count 50 --save-to-file',
                'severity': 'info'
            }]
        
        # Load and validate
        data = json.loads(sample_file.read_text())
        conversations = data.get('conversations', [])
        
        if not conversations:
            return [{
                'error': 'Sample file has no conversations',
                'file': str(sample_file),
                'severity': 'warning'
            }]
        
        print(f"📊 Validating {len(conversations)} conversations from {sample_file.name}")
        print()
        
        # Validate each conversation
        for i, conv in enumerate(conversations):
            self._validate_conversation(conv, i)
        
        return self.errors
    
    def _find_latest_sample_file(self) -> Path:
        """Find the most recent sample-mode output file."""
        if not self.outputs_dir.exists():
            return None
        
        sample_files = list(self.outputs_dir.glob('sample_mode_*.json'))
        if not sample_files:
            return None
        
        # Return most recent
        return max(sample_files, key=lambda p: p.stat().st_mtime)
    
    def _validate_conversation(self, conv: Dict, index: int):
        """Validate a single conversation structure."""
        conv_id = conv.get('id', f'index_{index}')
        
        # Check 1: conversation_parts structure
        if 'conversation_parts' in conv:
            parts = conv['conversation_parts']
            if isinstance(parts, list):
                self.errors.append({
                    'conversation_id': conv_id,
                    'field': 'conversation_parts',
                    'error': 'Expected dict, got list',
                    'value_type': type(parts).__name__,
                    'fix': 'Normalize in intercom_sdk_service.py _normalize_conversation()',
                    'severity': 'critical'
                })
            elif not isinstance(parts, dict):
                self.errors.append({
                    'conversation_id': conv_id,
                    'field': 'conversation_parts',
                    'error': f'Expected dict, got {type(parts).__name__}',
                    'severity': 'critical'
                })
        
        # Check 2: conversation_rating structure
        if 'conversation_rating' in conv:
            rating = conv['conversation_rating']
            if not isinstance(rating, (dict, int, float, type(None))):
                self.errors.append({
                    'conversation_id': conv_id,
                    'field': 'conversation_rating',
                    'error': f'Unexpected type: {type(rating).__name__}',
                    'expected': 'dict, int, float, or None',
                    'severity': 'warning'
                })
        
        # Check 3: custom_attributes structure
        if 'custom_attributes' in conv:
            attrs = conv['custom_attributes']
            if not isinstance(attrs, dict):
                self.errors.append({
                    'conversation_id': conv_id,
                    'field': 'custom_attributes',
                    'error': f'Expected dict, got {type(attrs).__name__}',
                    'severity': 'warning'
                })
        
        # Check 4: sla_applied structure
        if 'sla_applied' in conv:
            sla = conv['sla_applied']
            if sla is not None and not isinstance(sla, dict):
                self.errors.append({
                    'conversation_id': conv_id,
                    'field': 'sla_applied',
                    'error': f'Expected dict or None, got {type(sla).__name__}',
                    'severity': 'warning'
                })
        
        # Check 5: Required fields present
        required_fields = ['id', 'created_at']
        for field in required_fields:
            if field not in conv:
                self.errors.append({
                    'conversation_id': conv_id,
                    'field': field,
                    'error': f'Required field missing',
                    'severity': 'critical'
                })


def main():
    """Run schema validation."""
    print("="*80)
    print("INTERCOM DATA SCHEMA VALIDATION")
    print("="*80)
    print()
    
    project_root = Path(__file__).parent.parent
    validator = SchemaValidator(project_root)
    
    errors = validator.validate()
    
    if not errors:
        print("✅ No schema issues found!")
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
        print("🔴 CRITICAL SCHEMA ISSUES:")
        for error in critical:
            if 'conversation_id' in error:
                print(f"   Conversation: {error['conversation_id']}")
                print(f"   Field: {error['field']}")
            print(f"   Error: {error['error']}")
            if 'fix' in error:
                print(f"   Fix: {error['fix']}")
            print()
    
    if warnings:
        print(f"⚠️  WARNINGS ({len(warnings)} items):")
        # Show first 5
        for error in warnings[:5]:
            if 'conversation_id' in error:
                print(f"   {error['field']}: {error['error']}")
        if len(warnings) > 5:
            print(f"   ... and {len(warnings) - 5} more")
        print()
    
    if info:
        for error in info:
            print(f"ℹ️  {error['error']}")
            if 'fix' in error:
                print(f"   Fix: {error['fix']}")
            print()
    
    if critical:
        print("❌ Critical schema issues found!")
        print("   These indicate SDK data normalization is broken")
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())




