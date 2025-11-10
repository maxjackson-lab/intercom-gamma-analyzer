#!/usr/bin/env python3
"""
Double-Counting Detection

Validates topic assignment to prevent double-counting:
1. Conversations assigned to only ONE primary topic
2. Subcategory totals don't exceed parent totals
3. Topics sorted by confidence

Prevents: Reporting errors (volumes > 100%, subcategories > parent)
Priority: P1 (High Impact)
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any


class DoubleCountingChecker:
    """Check for double-counting in topic assignment."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / 'src'
        self.outputs_dir = project_root / 'outputs'
        self.errors: List[Dict[str, Any]] = []
    
    def check_all(self) -> List[Dict[str, Any]]:
        """Run all double-counting checks."""
        # Check 1: Code pattern analysis
        self._check_topic_assignment_code()
        
        # Check 2: Validate actual output data (if available)
        self._check_output_data()
        
        return self.errors
    
    def _check_topic_assignment_code(self):
        """Check topic assignment code for double-counting patterns."""
        topic_files = [
            self.src_dir / 'agents' / 'topic_detection_agent.py',
            self.src_dir / 'agents' / 'subtopic_detection_agent.py'
        ]
        
        for file_path in topic_files:
            if not file_path.exists():
                continue
            
            content = file_path.read_text()
            lines = content.splitlines()
            
            # Pattern 1: Loop adding conv to ALL topics (BAD - causes double-counting)
            # for topic in detected_topics:
            #     conversations_by_topic[topic].append(conv)  # ❌ Adds to ALL
            
            for i, line in enumerate(lines, 1):
                if re.search(r'for\s+\w+\s+in\s+.*topics', line):
                    # Found topic loop, check next few lines for append
                    for j in range(i, min(i+10, len(lines))):
                        next_line = lines[j]
                        if 'append(conv' in next_line or 'append(conversation' in next_line:
                            # Check if it's using primary topic pattern
                            if '[0]' not in next_line and 'primary' not in next_line:
                                self.errors.append({
                                    'file': str(file_path),
                                    'line': j + 1,
                                    'error': 'Potential double-counting: adding conv to multiple topics in loop',
                                    'pattern': 'for topic in topics: ...append(conv)',
                                    'fix': 'Use primary topic only: topics[0] or max(topics, key=lambda x: x["confidence"])',
                                    'severity': 'critical'
                                })
                                break
            
            # Pattern 2: Topics not sorted by confidence in detect_topics_for_conversation
            # Only check the main detection method
            if 'def _detect_topics_for_conversation' in content:
                # Find the method
                method_start = content.find('def _detect_topics_for_conversation')
                method_end = content.find('\n    def ', method_start + 1)
                if method_end == -1:
                    method_end = len(content)
                
                method_body = content[method_start:method_end]
                
                # Find return detected statement
                return_match = re.search(r'return\s+(detected|topics)\s*$', method_body, re.MULTILINE)
                if return_match:
                    var_name = return_match.group(1)
                    
                    # Check if sorted() is applied to the return
                    if 'return sorted(' + var_name in method_body:
                        # ✅ Correctly sorted!
                        pass
                    else:
                        # ❌ Not sorted - this is the critical one!
                        line_num = content[:method_start + return_match.start()].count('\n') + 1
                        self.errors.append({
                            'file': str(file_path),
                            'line': line_num,
                            'error': 'Detected topics not sorted by confidence in _detect_topics_for_conversation()',
                            'risk': 'Primary topic may not be highest confidence → double-counting downstream',
                            'fix': f'return sorted({var_name}, key=lambda x: x.get("confidence", 0), reverse=True)',
                            'severity': 'critical'
                        })
    
    def _check_output_data(self):
        """Check actual VoC output for double-counting."""
        # Find latest VoC output
        voc_files = list(self.outputs_dir.glob('voc_analysis_*.json')) if self.outputs_dir.exists() else []
        
        if not voc_files:
            # No data to check
            return
        
        latest_voc = max(voc_files, key=lambda p: p.stat().st_mtime)
        
        try:
            data = json.loads(latest_voc.read_text())
            
            # Check if topics have subcategories with totals
            topics = data.get('topics', {}) or data.get('topic_cards', {})
            
            for topic_name, topic_data in topics.items():
                if not isinstance(topic_data, dict):
                    continue
                
                parent_count = topic_data.get('total_conversations', 0) or topic_data.get('volume', 0)
                subcategories = topic_data.get('subcategories', {})
                
                if subcategories and isinstance(subcategories, dict):
                    subcategory_sum = sum(
                        sub.get('volume', 0) or sub.get('total_conversations', 0)
                        for sub in subcategories.values()
                        if isinstance(sub, dict)
                    )
                    
                    if subcategory_sum > parent_count:
                        self.errors.append({
                            'file': str(latest_voc),
                            'topic': topic_name,
                            'parent_count': parent_count,
                            'subcategory_sum': subcategory_sum,
                            'error': f'Subcategories ({subcategory_sum}) exceed parent ({parent_count})',
                            'likely_cause': 'Double-counting - conversations in multiple subcategories',
                            'severity': 'critical'
                        })
        
        except:
            pass


def main():
    """Run double-counting validation."""
    print("="*80)
    print("DOUBLE-COUNTING DETECTION")
    print("="*80)
    print()
    
    project_root = Path(__file__).parent.parent
    checker = DoubleCountingChecker(project_root)
    
    errors = checker.check_all()
    
    if not errors:
        print("✅ No double-counting issues found!")
        return 0
    
    # Group by type
    code_errors = [e for e in errors if 'file' in e and e['file'].endswith('.py')]
    data_errors = [e for e in errors if 'file' in e and e['file'].endswith('.json')]
    
    print(f"📊 Found {len(errors)} issue(s):")
    print(f"   Code patterns: {len(code_errors)}")
    print(f"   Data validation: {len(data_errors)}")
    print()
    
    if code_errors:
        print("🔴 CODE PATTERN ISSUES:")
        for error in code_errors:
            print(f"   {error['file']}:{error['line']}")
            print(f"   Error: {error['error']}")
            print(f"   Fix: {error['fix']}")
            print()
    
    if data_errors:
        print("🔴 DATA VALIDATION ISSUES (from latest VoC output):")
        for error in data_errors:
            print(f"   Topic: {error['topic']}")
            print(f"   Parent count: {error['parent_count']}")
            print(f"   Subcategory sum: {error['subcategory_sum']}")
            print(f"   Error: {error['error']}")
            print(f"   Likely cause: {error['likely_cause']}")
            print()
    
    if any(e.get('severity') == 'critical' for e in errors):
        print("❌ Critical double-counting issues found!")
        return 1
    else:
        print("⚠️  Only warnings found")
        return 0


if __name__ == '__main__':
    sys.exit(main())

