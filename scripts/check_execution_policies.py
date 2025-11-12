#!/usr/bin/env python3
"""
SSE/Background Execution Policy Enforcer

Validates that long-running tasks use background execution:
1. Multi-agent analysis → background
2. Week+ with Gamma → background
3. Deep schema dump → background
4. Schema-dump always → background

Prevents: SSE timeout failures
Priority: P1 (High Impact)
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any


class ExecutionPolicyChecker:
    """Check execution mode policies."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.app_js = project_root / 'static' / 'app.js'
        self.errors: List[Dict[str, Any]] = []
    
    def check(self) -> List[Dict[str, Any]]:
        """Check execution policies."""
        if not self.app_js.exists():
            return [{
                'error': 'static/app.js not found',
                'severity': 'critical'
            }]
        
        content = self.app_js.read_text()
        
        # Check 1: shouldUseBackgroundExecution function exists
        if 'shouldUseBackgroundExecution' not in content:
            self.errors.append({
                'file': 'static/app.js',
                'error': 'shouldUseBackgroundExecution() function not found',
                'severity': 'critical',
                'fix': 'Add function to determine execution mode'
            })
            return self.errors
        
        # Check 2: Multi-agent policy
        if not re.search(r'hasMultiAgent.*return true', content, re.DOTALL):
            self.errors.append({
                'file': 'static/app.js',
                'policy': 'multi_agent',
                'error': 'Missing background policy for multi-agent analysis',
                'fix': 'Add: if (hasMultiAgent) return true;',
                'severity': 'critical'
            })
        
        # Check 3: Long period + Gamma policy
        if not re.search(r'isLongPeriod.*hasGamma.*return true', content, re.DOTALL):
            self.errors.append({
                'file': 'static/app.js',
                'policy': 'long_period_gamma',
                'error': 'Missing background policy for long period + Gamma',
                'fix': 'Add: if (isLongPeriod && hasGamma) return true;',
                'severity': 'warning'
            })
        
        # Check 4: Schema-dump always uses background (critical - from Nov 10 fix)
        if not re.search(r"analysisType === ['\"]schema-dump['\"]", content):
            # schema-dump not in UI at all
            pass
        else:
            # If schema-dump exists, verify it's handled
            if not re.search(r"isSampleMode.*schemaMode.*\['deep', 'comprehensive'\]", content):
                self.errors.append({
                    'file': 'static/app.js',
                    'policy': 'schema_dump_background',
                    'error': 'schema-dump deep/comprehensive should use background',
                    'fix': 'Add schema mode check to shouldUseBackgroundExecution()',
                    'severity': 'warning'
                })
        
        # Check 5: SSE disconnect handling (in railway_web.py)
        railway_web = self.project_root / 'deploy' / 'railway_web.py'
        if railway_web.exists():
            railway_content = railway_web.read_text()
            
            # Look for client disconnect handling
            if 'request.is_disconnected()' in railway_content:
                # Check that it doesn't cancel execution
                disconnect_section = re.search(
                    r'if await request\.is_disconnected\(\):.*?break',
                    railway_content,
                    re.DOTALL
                )
                
                if disconnect_section:
                    section_text = disconnect_section.group(0)
                    
                    # BAD: Calls cancel_execution
                    if 'cancel_execution' in section_text and 'DON\'T' not in section_text:
                        self.errors.append({
                            'file': 'deploy/railway_web.py',
                            'error': 'SSE disconnect calls cancel_execution()',
                            'severity': 'critical',
                            'fix': 'Remove cancel_execution() call - let job continue in background'
                        })
                    
                    # GOOD: Sets status to RUNNING
                    if 'ExecutionStatus.RUNNING' not in section_text and 'CANCELLED' in section_text:
                        self.errors.append({
                            'file': 'deploy/railway_web.py',
                            'error': 'SSE disconnect sets status to CANCELLED instead of RUNNING',
                            'severity': 'warning',
                            'fix': 'Set status to RUNNING to indicate job continues'
                        })
        
        return self.errors


def main():
    """Run execution policy validation."""
    print("="*80)
    print("SSE/BACKGROUND EXECUTION POLICY VALIDATION")
    print("="*80)
    print()
    
    project_root = Path(__file__).parent.parent
    checker = ExecutionPolicyChecker(project_root)
    
    errors = checker.check()
    
    if not errors:
        print("✅ All execution policies are correctly implemented!")
        return 0
    
    # Group by severity
    critical = [e for e in errors if e.get('severity') == 'critical']
    warnings = [e for e in errors if e.get('severity') == 'warning']
    
    print(f"📊 Found {len(errors)} policy issue(s):")
    print(f"   Critical: {len(critical)}")
    print(f"   Warnings: {len(warnings)}")
    print()
    
    if critical:
        print("🔴 CRITICAL POLICY VIOLATIONS:")
        for error in critical:
            print(f"   File: {error['file']}")
            if 'policy' in error:
                print(f"   Policy: {error['policy']}")
            print(f"   Error: {error['error']}")
            print(f"   Fix: {error['fix']}")
            print()
    
    if warnings:
        print("⚠️  POLICY WARNINGS:")
        for error in warnings:
            print(f"   File: {error['file']}")
            if 'policy' in error:
                print(f"   Policy: {error['policy']}")
            print(f"   Error: {error['error']}")
            print(f"   Fix: {error['fix']}")
            print()
    
    if critical:
        print("❌ Critical policy violations found!")
        print("   These will cause timeout failures in production")
        return 1
    else:
        print("⚠️  Only warnings found")
        return 0


if __name__ == '__main__':
    sys.exit(main())




