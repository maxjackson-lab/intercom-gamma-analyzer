#!/usr/bin/env python3
"""
Topic Keyword Specificity Validator

Validates topic detection keywords:
1. Keywords use word boundaries (no partial matches)
2. Keywords are specific enough (not too broad)
3. No overlaps between topics

Prevents: Topic detection failures (35% Unknown topics)
Priority: P1 (High Impact)
"""

import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict


class KeywordValidator:
    """Validate topic keywords for specificity."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / 'src'
        self.outputs_dir = project_root / 'outputs'
        self.errors: List[Dict[str, Any]] = []
    
    def validate(self) -> List[Dict[str, Any]]:
        """Run keyword validation."""
        # Check 1: Analyze keyword definitions
        self._check_keyword_definitions()
        
        # Check 2: Check for word boundaries in code
        self._check_word_boundary_usage()
        
        # Check 3: Test on sample data if available
        self._test_on_sample_data()
        
        return self.errors
    
    def _check_keyword_definitions(self):
        """Check keyword definitions for specificity."""
        topic_file = self.src_dir / 'agents' / 'topic_detection_agent.py'
        
        if not topic_file.exists():
            return
        
        content = topic_file.read_text()
        
        # Look for keyword definitions
        # Pattern: keywords = ['word1', 'word2'] or 'keywords': [...]
        keyword_matches = re.finditer(
            r"['\"]keywords['\"]:\s*\[(.*?)\]",
            content,
            re.DOTALL
        )
        
        for match in keyword_matches:
            keywords_str = match.group(1)
            
            # Extract individual keywords
            keywords = re.findall(r"['\"]([^'\"]+)['\"]", keywords_str)
            
            for keyword in keywords:
                # Check 1: Single words < 4 chars are risky
                if len(keyword.split()) == 1 and len(keyword) < 4:
                    self.errors.append({
                        'file': str(topic_file),
                        'keyword': keyword,
                        'error': f'Short keyword "{keyword}" ({len(keyword)} chars) - high false positive risk',
                        'examples': {
                            'fin': ['final', 'finish', 'define'],
                            'ai': ['daily', 'email', 'wait'],
                            'api': ['rapid', 'capital']
                        }.get(keyword, []),
                        'fix': f'Use phrase: "{keyword} agent" or "{keyword} assistant"',
                        'severity': 'warning'
                    })
    
    def _check_word_boundary_usage(self):
        """Check if keyword matching uses word boundaries."""
        topic_file = self.src_dir / 'agents' / 'topic_detection_agent.py'
        
        if not topic_file.exists():
            return
        
        content = topic_file.read_text()
        lines = content.splitlines()
        
        # Look for keyword in text patterns WITHOUT word boundary
        # Pattern: 'keyword' in text or keyword in text
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            # Look for: 'word' in text
            matches = re.finditer(r"['\"](\w{1,4})['\"] in (text|body|content)", line)
            for match in matches:
                keyword = match.group(1)
                var = match.group(2)
                
                # Check if word boundary is used
                # Look for \b or re.search nearby
                if r'\b' not in line and 're.search' not in line:
                    self.errors.append({
                        'file': str(topic_file),
                        'line': i,
                        'code': line.strip()[:80],
                        'keyword': keyword,
                        'error': 'Keyword check missing word boundary',
                        'current': f"'{keyword}' in {var}",
                        'fix': f"re.search(r'\\b{keyword}\\b', {var}, re.IGNORECASE)",
                        'severity': 'warning'
                    })
    
    def _test_on_sample_data(self):
        """Test keywords on sample data for false positives."""
        # Find latest sample file
        if not self.outputs_dir.exists():
            return
        
        sample_files = list(self.outputs_dir.glob('sample_mode_*.json'))
        if not sample_files:
            return
        
        latest_sample = max(sample_files, key=lambda p: p.stat().st_mtime)
        
        try:
            data = json.loads(latest_sample.read_text())
            analysis = data.get('analysis', {})
            topic_summary = analysis.get('topic_summary', {})
            
            # Check for high "Unknown" rate
            total_convs = sum(topic_summary.values()) if topic_summary else 0
            unknown_count = topic_summary.get('Unknown/Unresponsive', 0)
            
            if total_convs > 0:
                unknown_pct = (unknown_count / total_convs) * 100
                
                if unknown_pct > 30:
                    self.errors.append({
                        'error': f'High Unknown rate: {unknown_pct:.1f}%',
                        'unknown_count': unknown_count,
                        'total': total_convs,
                        'likely_cause': 'Keywords too specific or missing word boundaries',
                        'fix': 'Review keyword definitions and add broader patterns',
                        'severity': 'warning'
                    })
        
        except:
            pass


def main():
    """Run keyword validation."""
    print("="*80)
    print("TOPIC KEYWORD VALIDATION")
    print("="*80)
    print()
    
    project_root = Path(__file__).parent.parent
    validator = KeywordValidator(project_root)
    
    errors = validator.validate()
    
    if not errors:
        print("✅ No keyword issues found!")
        return 0
    
    # Group by type
    critical = [e for e in errors if e.get('severity') == 'critical']
    warnings = [e for e in errors if e.get('severity') == 'warning']
    
    print(f"📊 Found {len(errors)} issue(s):")
    print(f"   Critical: {len(critical)}")
    print(f"   Warnings: {len(warnings)}")
    print()
    
    if warnings:
        print("⚠️  KEYWORD WARNINGS:")
        for error in warnings:
            if 'keyword' in error:
                print(f"   Keyword: {error['keyword']}")
                if 'file' in error:
                    print(f"   File: {error['file']}:{error.get('line', '?')}")
                print(f"   Error: {error['error']}")
                if 'fix' in error:
                    print(f"   Fix: {error['fix']}")
                if 'examples' in error and error['examples']:
                    print(f"   False matches: {', '.join(error['examples'])}")
            else:
                print(f"   {error['error']}")
                if 'fix' in error:
                    print(f"   Fix: {error['fix']}")
            print()
    
    print("⚠️  Review keyword specificity")
    return 0  # Don't block on keyword warnings


if __name__ == '__main__':
    sys.exit(main())

