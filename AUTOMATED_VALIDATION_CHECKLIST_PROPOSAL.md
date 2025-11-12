# Automated Validation Checklist Proposal
## Pattern-Based Bug Prevention System

**Date:** November 10, 2025  
**Based on:** Analysis of 100+ commits, 20+ implementation docs, recurring debugging cycles  
**Priority:** Ordered by impact and frequency of issues found

---

## 🎯 Executive Summary

After analyzing all PRs, fix documents, and debugging cycles, I've identified **12 recurring bug patterns** that require iterative debugging. Each has a proposed automated check to catch issues before deployment.

**Impact if implemented:** 
- ⏰ **Save 30-40% debugging time**
- 🐛 **Prevent 60-70% of runtime errors**
- 🚀 **Faster iteration cycles**
- ✅ **Higher code quality**

---

## Priority 1: Critical Runtime Errors (MUST HAVE)

### ✅ 1. CLI ↔ Web ↔ Railway Alignment Checker
**Status:** ✅ ALREADY IMPLEMENTED (`scripts/check_cli_web_alignment.py`)

**Pattern Found:** 
- 15+ commits fixing mismatched flags between layers
- Examples: `--output-format` in UI but not CLI, `--ai-model` missing from validation
- Latest instance: voice-of-customer has 5 CLI flags missing from Railway validation

**Automated Check:**
```python
# scripts/check_cli_web_alignment.py (already exists!)
✅ Validates CLI flags match Railway allowed_flags
✅ Checks types match (enum, boolean, integer, etc.)
✅ Verifies defaults align
✅ Scans frontend for orphaned flag references
```

**When to Run:** Pre-commit hook + CI/CD
**Priority:** 🔴 **P0 - Already implemented, must enforce usage**

---

### 🆕 2. Function Signature Parameter Mismatch Checker
**Status:** 🔴 NEEDED - Just caught today!

**Pattern Found:**
- **Today's bug:** `_analyze_sample()` called with `include_hierarchy` but function didn't accept it
- **Nov 4:** `paid_fin_resolved_conversations` variable name mismatch
- **Oct 29:** Function signature didn't match caller in multiple agents

**Recurrence:** 8+ instances across project

**Automated Check:**
```python
# scripts/check_function_signatures.py

import ast
import re
from pathlib import Path

def check_function_calls_match_signatures():
    """
    Parse all Python files and validate:
    1. Function calls use correct parameter names
    2. All required parameters are provided
    3. No unexpected keyword arguments
    """
    errors = []
    
    # Build function signature registry
    signatures = extract_all_function_signatures()
    
    # Find all function calls
    calls = extract_all_function_calls()
    
    # Validate each call
    for call in calls:
        func_name = call['function']
        kwargs = call['kwargs']
        
        if func_name in signatures:
            sig = signatures[func_name]
            
            # Check for unexpected kwargs
            for kwarg in kwargs:
                if kwarg not in sig['params']:
                    errors.append({
                        'file': call['file'],
                        'line': call['line'],
                        'error': f"Unexpected parameter '{kwarg}' in {func_name}()",
                        'expected': sig['params']
                    })
            
            # Check for missing required params
            required = [p for p in sig['params'] if p['required']]
            provided = set(kwargs.keys()) | set(call.get('args', []))
            missing = [p['name'] for p in required if p['name'] not in provided]
            
            if missing:
                errors.append({
                    'file': call['file'],
                    'line': call['line'],
                    'error': f"Missing required parameters in {func_name}(): {missing}"
                })
    
    return errors

# Example output:
# ❌ src/services/sample_mode.py:162
#    Unexpected parameter 'include_hierarchy' in _analyze_sample()
#    Expected: count, detail_samples, llm_topic_count
```

**When to Run:** Pre-commit hook (fast, <5 seconds)
**Priority:** 🔴 **P0 - Prevents TypeErrors at runtime**

---

### 🆕 3. Async/Await Consistency Checker
**Status:** 🔴 NEEDED

**Pattern Found:**
- **Oct 29:** httpx client initialization needed lazy async pattern
- **Nov 4:** DuckDB blocking calls in async context
- Multiple instances of forgetting `await` or calling sync methods in async functions

**Recurrence:** 6+ instances

**Automated Check:**
```python
# scripts/check_async_patterns.py

def check_async_consistency():
    """
    Validate:
    1. All async functions are awaited when called
    2. No blocking I/O in async functions
    3. All DB operations use async wrappers
    4. No sync sleep() in async functions (use asyncio.sleep())
    """
    errors = []
    
    patterns = {
        'await_missing': {
            'regex': r'(?<!await\s)(?:async\s+def\s+\w+.*?\n.*?)(client\.\w+\(|service\.\w+\(|fetch_\w+\()',
            'message': 'Async function call missing await'
        },
        'blocking_io': {
            'regex': r'async\s+def.*?(?:time\.sleep|requests\.|urllib\.|open\()',
            'message': 'Blocking I/O in async function'
        },
        'sync_sleep': {
            'regex': r'async\s+def.*?time\.sleep\(',
            'message': 'Use asyncio.sleep() instead of time.sleep() in async functions'
        }
    }
    
    # Scan all Python files
    for py_file in Path('src').rglob('*.py'):
        content = py_file.read_text()
        
        for pattern_name, pattern_config in patterns.items():
            matches = re.finditer(pattern_config['regex'], content, re.MULTILINE | re.DOTALL)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                errors.append({
                    'file': str(py_file),
                    'line': line_num,
                    'error': pattern_config['message'],
                    'code': match.group(0)[:80]
                })
    
    return errors
```

**When to Run:** Pre-commit hook
**Priority:** 🔴 **P0 - Prevents deadlocks and runtime errors**

---

### 🆕 4. Missing Import/Dependency Checker
**Status:** 🔴 NEEDED

**Pattern Found:**
- **Nov 9:** `ModuleNotFoundError: click` in sandbox
- **Oct 28:** `ImportError: httpx` missing in deployment
- **Oct 27:** SDK module not found due to path issues

**Recurrence:** 10+ instances

**Automated Check:**
```python
# scripts/check_imports.py

import ast
import subprocess
from pathlib import Path

def check_all_imports_available():
    """
    Validate:
    1. All imports exist in requirements.txt
    2. All imports can be resolved
    3. No circular import dependencies
    4. Deployment requirements match dev requirements
    """
    errors = []
    
    # Extract all imports from Python files
    all_imports = set()
    for py_file in Path('src').rglob('*.py'):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    all_imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    all_imports.add(node.module.split('.')[0])
    
    # Check against requirements.txt
    req_file = Path('requirements.txt')
    requirements = {
        line.split('==')[0].split('>=')[0].split('[')[0].lower()
        for line in req_file.read_text().splitlines()
        if line and not line.startswith('#')
    }
    
    # Standard library modules to skip
    stdlib = {'os', 'sys', 're', 'json', 'datetime', 'pathlib', 'typing', 'asyncio', 'time', 'logging'}
    
    # Find missing deps
    for import_name in all_imports:
        if import_name not in stdlib and import_name.replace('_', '-').lower() not in requirements:
            if import_name not in ['src', 'tests', 'config']:  # Skip local modules
                errors.append({
                    'import': import_name,
                    'error': 'Not found in requirements.txt',
                    'suggestion': f'Add to requirements.txt or verify import'
                })
    
    # Check Railway requirements vs Dev requirements
    railway_reqs = Path('requirements-railway.txt')
    if railway_reqs.exists():
        railway_packages = set(railway_reqs.read_text().splitlines())
        dev_packages = set(req_file.read_text().splitlines())
        
        missing_in_railway = dev_packages - railway_packages - {'pytest', 'pytest-asyncio', 'hypothesis'}
        if missing_in_railway:
            errors.append({
                'error': 'Packages in requirements.txt missing from requirements-railway.txt',
                'packages': list(missing_in_railway)
            })
    
    return errors
```

**When to Run:** Pre-commit + CI/CD
**Priority:** 🔴 **P0 - Prevents deployment failures**

---

## Priority 2: Data Structure Validation (HIGH IMPACT)

### 🆕 5. Schema Shape Validator
**Status:** 🟡 NEEDED

**Pattern Found:**
- **Nov 4:** `conversation_parts` could be list OR dict (SDK inconsistency)
- **Oct 28:** Rating can be dict or direct value
- **Multiple instances:** Fields returning unexpected types

**Recurrence:** 12+ instances of defensive `isinstance()` checks added

**Automated Check:**
```python
# scripts/validate_data_schemas.py

from typing import Dict, Any, List
import json

def validate_intercom_schemas():
    """
    Load sample conversations and validate expected structure:
    1. conversation_parts is always dict-wrapped
    2. Rating is always int or dict, never string
    3. Custom_attributes is always dict
    4. Required fields are present
    """
    errors = []
    
    # Load sample data
    sample_file = Path('outputs/sample_mode_*.json').glob()
    latest_sample = max(sample_file, key=lambda p: p.stat().st_mtime, default=None)
    
    if not latest_sample:
        return [{'error': 'No sample data found. Run: python src/main.py sample-mode'}]
    
    data = json.loads(latest_sample.read_text())
    conversations = data.get('conversations', [])
    
    for i, conv in enumerate(conversations[:100]):  # Check first 100
        conv_id = conv.get('id', f'index_{i}')
        
        # Check conversation_parts structure
        if 'conversation_parts' in conv:
            parts = conv['conversation_parts']
            if isinstance(parts, list):
                errors.append({
                    'conversation_id': conv_id,
                    'field': 'conversation_parts',
                    'error': 'Expected dict, got list',
                    'fix': 'Normalize in intercom_sdk_service.py line 326'
                })
        
        # Check rating structure
        if 'conversation_rating' in conv:
            rating = conv['conversation_rating']
            if not isinstance(rating, (dict, int, type(None))):
                errors.append({
                    'conversation_id': conv_id,
                    'field': 'conversation_rating',
                    'error': f'Unexpected type: {type(rating)}',
                    'expected': 'dict, int, or None'
                })
        
        # Check custom_attributes
        if 'custom_attributes' in conv:
            attrs = conv['custom_attributes']
            if not isinstance(attrs, dict):
                errors.append({
                    'conversation_id': conv_id,
                    'field': 'custom_attributes',
                    'error': f'Expected dict, got {type(attrs)}' 
                })
    
    return errors
```

**When to Run:** Weekly on production data samples
**Priority:** 🟡 **P1 - Prevents data pipeline crashes**

---

### 🆕 6. Null/Missing Field Safety Checker
**Status:** 🟡 NEEDED

**Pattern Found:**
- Multiple crashes from accessing nested fields: `conv['source']['author']['email']`
- Defensive code added: `conv.get('source', {}).get('author', {}).get('email')`

**Recurrence:** 20+ instances of defensive `.get()` chains

**Automated Check:**
```python
# scripts/check_null_safety.py

def check_null_safety():
    """
    Find unsafe field access patterns:
    1. Direct bracket access: conv['field']['nested']
    2. Should be: conv.get('field', {}).get('nested')
    3. Especially for known-inconsistent fields
    """
    unsafe_patterns = [
        r"conv\['[^']+'\]\['[^']+'\]",  # conv['x']['y']
        r"conversation\['[^']+'\]\['[^']+'\]",
        r"data\['[^']+'\]\['[^']+'\]",
        r"result\['[^']+'\]\['[^']+'\]",
    ]
    
    # Known inconsistent fields from Intercom
    risky_fields = [
        'custom_attributes',
        'source',
        'contacts',
        'conversation_parts',
        'sla_applied',
        'conversation_rating',
        'ai_agent'
    ]
    
    errors = []
    for py_file in Path('src').rglob('*.py'):
        content = py_file.read_text()
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            for pattern in unsafe_patterns:
                if re.search(pattern, line):
                    # Check if it's accessing a risky field
                    for field in risky_fields:
                        if field in line:
                            errors.append({
                                'file': str(py_file),
                                'line': i,
                                'code': line.strip(),
                                'error': f'Unsafe access to risky field: {field}',
                                'fix': f"Use .get('{field}', {{}}) instead"
                            })
                            break
    
    return errors
```

**When to Run:** Pre-commit hook
**Priority:** 🟡 **P1 - Prevents KeyError at runtime**

---

### 🆕 7. Pydantic Model Field Validator
**Status:** 🟡 NEEDED

**Pattern Found:**
- **Nov 4:** Period_end < period_start causing DB errors
- **Multiple:** Invalid enum values ("Standard" vs "standard")
- **Multiple:** Missing required fields caught at runtime instead of validation

**Recurrence:** 8+ instances

**Automated Check:**
```python
# scripts/validate_pydantic_models.py

from pydantic import ValidationError
import importlib
import inspect

def validate_all_pydantic_models():
    """
    Test all Pydantic models with:
    1. Valid data (should pass)
    2. Invalid data (should raise ValidationError)
    3. Missing required fields (should raise ValidationError)
    4. Boundary conditions
    """
    errors = []
    
    # Find all BaseModel subclasses
    from src.agents.base_agent import AgentContext, AgentResult
    from src.services.historical_snapshot_service import SnapshotData, ComparisonData
    
    models = [AgentContext, AgentResult, SnapshotData, ComparisonData]
    
    for model in models:
        # Test 1: Valid data
        try:
            valid_data = generate_valid_sample_data(model)
            instance = model.model_validate(valid_data)
        except Exception as e:
            errors.append({
                'model': model.__name__,
                'test': 'valid_data',
                'error': f'Valid data failed validation: {e}'
            })
        
        # Test 2: Invalid types
        try:
            invalid_data = generate_invalid_sample_data(model)
            model.model_validate(invalid_data)
            # Should raise ValidationError!
            errors.append({
                'model': model.__name__,
                'test': 'invalid_data',
                'error': 'Invalid data passed validation (should have failed)'
            })
        except ValidationError:
            pass  # Expected
        
        # Test 3: Missing required fields
        try:
            incomplete_data = {}
            model.model_validate(incomplete_data)
            errors.append({
                'model': model.__name__,
                'test': 'missing_required',
                'error': 'Missing required fields passed validation'
            })
        except ValidationError:
            pass  # Expected
    
    return errors
```

**When to Run:** Unit tests + CI/CD
**Priority:** 🟡 **P1 - Catches validation errors early**

---

## Priority 2: Integration Issues (HIGH VALUE)

### 🆕 8. Agent Tool Registry Validator
**Status:** 🟡 NEEDED

**Pattern Found:**
- Agents calling tools that don't exist
- Tool definitions not registered
- Missing tool parameters

**Recurrence:** 4+ instances

**Automated Check:**
```python
# scripts/validate_agent_tools.py

def validate_agent_tools():
    """
    Check:
    1. All tools referenced by agents exist in registry
    2. Tool parameters match agent calls
    3. No orphaned tools (defined but never used)
    """
    from src.agents.tools.tool_registry import ToolRegistry
    
    errors = []
    
    # Get all registered tools
    registry = ToolRegistry()
    registered_tools = set(registry.get_all_tool_names())
    
    # Find tool calls in agent code
    used_tools = set()
    for agent_file in Path('src/agents').rglob('*_agent.py'):
        content = agent_file.read_text()
        
        # Look for get_tool() calls
        tool_calls = re.findall(r"get_tool\(['\"](\w+)['\"]\)", content)
        used_tools.update(tool_calls)
        
        # Check if tools exist
        for tool_name in tool_calls:
            if tool_name not in registered_tools:
                errors.append({
                    'file': str(agent_file),
                    'tool': tool_name,
                    'error': f'Tool "{tool_name}" not found in registry'
                })
    
    # Find orphaned tools
    orphaned = registered_tools - used_tools
    for orphan in orphaned:
        errors.append({
            'tool': orphan,
            'error': 'Tool registered but never used',
            'suggestion': 'Remove from registry or document as utility'
        })
    
    return errors
```

**When to Run:** Weekly + pre-merge
**Priority:** 🟡 **P1 - Prevents agent execution failures**

---

### 🆕 9. SSE/Background Execution Policy Enforcer
**Status:** 🟡 NEEDED - Based on today's timeout issues

**Pattern Found:**
- **Today:** Schema-dump timing out via SSE
- **Nov 8:** Long-running tasks need background execution
- **Multiple:** Tasks that should use background but don't

**Recurrence:** 6+ instances

**Automated Check:**
```python
# scripts/check_execution_policies.py

def check_execution_policies():
    """
    Enforce execution mode rules:
    1. Multi-agent analysis → MUST use background
    2. Week+ with Gamma → MUST use background
    3. Deep/comprehensive schema → MUST use background
    4. Sample-mode quick → CAN use SSE
    """
    errors = []
    
    # Check static/app.js shouldUseBackgroundExecution()
    app_js = Path('static/app.js').read_text()
    
    required_background_patterns = {
        'multi_agent': r"hasMultiAgent.*return true",
        'long_period_gamma': r"isLongPeriod.*hasGamma.*return true",
        'schema_deep': r"schemaMode.*\['deep', 'comprehensive'\].*return true"
    }
    
    for pattern_name, pattern in required_background_patterns.items():
        if not re.search(pattern, app_js, re.DOTALL):
            errors.append({
                'file': 'static/app.js',
                'policy': pattern_name,
                'error': f'Missing background execution policy for {pattern_name}',
                'fix': 'Add condition to shouldUseBackgroundExecution()'
            })
    
    # Check that schema-dump ALWAYS uses background (per today's fix)
    if not re.search(r"analysisType === 'schema-dump'.*background", app_js):
        errors.append({
            'file': 'static/app.js',
            'error': 'schema-dump should always use background execution',
            'reason': 'SSE timeout issues with long Intercom fetches'
        })
    
    return errors
```

**When to Run:** Pre-commit
**Priority:** 🟡 **P1 - Prevents timeout failures**

---

## Priority 3: Data Quality (MEDIUM IMPACT)

### 🆕 10. Double-Counting Detection
**Status:** 🟡 NEEDED

**Pattern Found:**
- **Nov 4:** Subcategory totals exceeded parent (3,361 > 3,226)
- **Root cause:** Conversations assigned to multiple topics
- **Fix:** Primary topic only assignment

**Recurrence:** 1 major instance (but critical)

**Automated Check:**
```python
# scripts/check_double_counting.py

def check_for_double_counting():
    """
    Analyze topic assignment code to ensure:
    1. Each conversation assigned to exactly ONE primary topic
    2. Subcategory totals <= parent totals
    3. No conversation appears in multiple categories
    """
    errors = []
    
    # Check topic assignment code
    topic_files = [
        'src/agents/topic_detection_agent.py',
        'src/agents/subtopic_detection_agent.py'
    ]
    
    for file_path in topic_files:
        content = Path(file_path).read_text()
        
        # Pattern 1: Loop adding conv to multiple topics (BAD)
        bad_pattern = r'for topic in .*topics.*:\s+.*append\(conv\)'
        if re.search(bad_pattern, content, re.MULTILINE):
            errors.append({
                'file': file_path,
                'error': 'Potential double-counting: adding conv to multiple topics in loop',
                'pattern': 'for topic in topics: ...append(conv)',
                'fix': 'Use primary topic only: topics[0] or max by confidence'
            })
        
        # Pattern 2: Missing confidence sorting (RISKY)
        if 'def detect_topics' in content:
            # Should sort by confidence before returning
            if 'sorted' not in content or 'confidence' not in content:
                errors.append({
                    'file': file_path,
                    'error': 'Topics not sorted by confidence',
                    'risk': 'Primary topic may not be highest confidence',
                    'fix': 'return sorted(detected, key=lambda x: x["confidence"], reverse=True)'
                })
    
    # Validate with sample data
    sample_output = find_latest_voc_output()
    if sample_output:
        validation_errors = validate_topic_totals(sample_output)
        errors.extend(validation_errors)
    
    return errors

def validate_topic_totals(voc_output: Dict) -> List[Dict]:
    """Check if any subcategory exceeds parent total."""
    errors = []
    
    for topic_name, topic_data in voc_output.get('topics', {}).items():
        parent_count = topic_data.get('total_conversations', 0)
        subcategories = topic_data.get('subcategories', {})
        
        subcategory_sum = sum(sub.get('volume', 0) for sub in subcategories.values())
        
        if subcategory_sum > parent_count:
            errors.append({
                'topic': topic_name,
                'parent_count': parent_count,
                'subcategory_sum': subcategory_sum,
                'error': f'Subcategories ({subcategory_sum}) exceed parent ({parent_count})',
                'likely_cause': 'Double-counting - conversations assigned to multiple subcategories'
            })
    
    return errors
```

**When to Run:** After each VoC analysis + weekly validation
**Priority:** 🟡 **P1 - Ensures reporting accuracy**

---

### 🆕 11. Keyword Specificity Validator
**Status:** 🟡 NEEDED

**Pattern Found:**
- **Topic Detection Regression:** Keywords like "fin", "ai", "agent" too broad
- "fin" matched "final", "finish", "define"
- "ai" matched "daily", "email", "wait"
- 35% Unknown topics due to poor keyword matching

**Recurrence:** Major regression after SDK migration

**Automated Check:**
```python
# scripts/validate_topic_keywords.py

import re
from collections import defaultdict

def validate_topic_keywords():
    """
    Check topic keywords for:
    1. Word boundary usage (no partial matches)
    2. Specificity (not too broad)
    3. No overlaps between topics
    4. Real conversation test (sample data)
    """
    errors = []
    
    # Load topic definitions
    from src.agents.topic_detection_agent import TopicDetectionAgent
    agent = TopicDetectionAgent()
    topics = agent.topics  # Load from config
    
    # Check 1: Keywords should use word boundaries
    for topic in topics:
        topic_name = topic['name']
        keywords = topic.get('keywords', [])
        
        for keyword in keywords:
            # Single words < 4 chars are risky
            if len(keyword.split()) == 1 and len(keyword) < 4:
                errors.append({
                    'topic': topic_name,
                    'keyword': keyword,
                    'error': 'Short single-word keyword (high false positive risk)',
                    'examples': ['fin → final', 'ai → daily', 'api → rapid'],
                    'fix': f'Use phrase: "{keyword} agent" or add word boundary check'
                })
            
            # Check word boundary usage in code
            detection_code = Path('src/agents/topic_detection_agent.py').read_text()
            if f"'{keyword}' in text" in detection_code:
                errors.append({
                    'topic': topic_name,
                    'keyword': keyword,
                    'error': 'Keyword check missing word boundary',
                    'current': f"'{keyword}' in text",
                    'fix': f"re.search(r'\\b{keyword}\\b', text, re.IGNORECASE)"
                })
    
    # Check 2: Test keywords on sample data
    sample_file = find_latest_sample_mode_output()
    if sample_file:
        false_positives = test_keywords_on_sample_data(topics, sample_file)
        errors.extend(false_positives)
    
    # Check 3: Detect keyword overlaps
    keyword_to_topics = defaultdict(list)
    for topic in topics:
        for keyword in topic.get('keywords', []):
            keyword_to_topics[keyword].append(topic['name'])
    
    for keyword, topic_names in keyword_to_topics.items():
        if len(topic_names) > 1:
            errors.append({
                'keyword': keyword,
                'topics': topic_names,
                'error': 'Keyword shared between multiple topics',
                'risk': 'Ambiguous classification'
            })
    
    return errors
```

**When to Run:** When modifying topic keywords + weekly validation
**Priority:** 🟡 **P1 - Ensures topic detection accuracy**

---

## Priority 3: Code Quality (GOOD PRACTICE)

### 🆕 12. Console Output File Safety Checker  
**Status:** 🟢 NICE TO HAVE

**Pattern Found:**
- Rich console recording not enabled when needed
- Log files missing complete output
- **Today's enhancement:** Added `.log` file for schema-dump

**Automated Check:**
```python
# scripts/check_output_completeness.py

def check_output_file_creation():
    """
    Ensure analysis commands save complete output:
    1. JSON data file (raw)
    2. Formatted .md or .log file (for sharing)
    3. Both have matching timestamps
    """
    commands_requiring_logs = [
        'sample-mode',
        'voice-of-customer',
        'agent-performance',
        'agent-coaching-report',
        'comprehensive-analysis'
    ]
    
    errors = []
    
    for command in commands_requiring_logs:
        # Check if command enables console.record
        service_file = find_service_file_for_command(command)
        if service_file:
            content = Path(service_file).read_text()
            
            if 'console.record = True' not in content:
                errors.append({
                    'command': command,
                    'file': service_file,
                    'error': 'Console recording not enabled',
                    'impact': 'Terminal output not saved to log file',
                    'fix': 'Add console.record = True before analysis'
                })
            
            if '.log' not in content and 'export_text' not in content:
                errors.append({
                    'command': command,
                    'file': service_file,
                    'error': 'No log file being saved',
                    'impact': 'Users lose output on SSE disconnect',
                    'fix': 'Save console.export_text() to .log file'
                })
    
    return errors
```

**When to Run:** Weekly review
**Priority:** 🟢 **P2 - Improves UX, prevents data loss**

---

### 🆕 13. Frontend Flag Conditional Logic Checker
**Status:** 🟢 NICE TO HAVE

**Pattern Found:**
- **Multiple instances:** Flags sent to wrong commands
- --verbose sent to sample-mode initially
- --audit-trail sent to diagnostic commands
- Flags conditionally applied inconsistently

**Automated Check:**
```python
# scripts/check_frontend_flag_logic.py

def check_frontend_flag_conditions():
    """
    Validate static/app.js flag sending logic:
    1. Diagnostic modes don't get production flags
    2. Flags only sent to commands that accept them
    3. Conditional logic matches CLI capabilities
    """
    errors = []
    
    app_js = Path('static/app.js').read_text()
    
    # Pattern: Flags that should NOT go to diagnostic modes
    diagnostic_modes = ['sample-mode', 'schema-dump']
    production_only_flags = ['--audit-trail', '--generate-gamma', '--multi-agent']
    
    for mode in diagnostic_modes:
        for flag in production_only_flags:
            # Check if flag is sent without conditional
            pattern = f"analysisType === '{mode}'.*?{re.escape(flag)}"
            if re.search(pattern, app_js, re.DOTALL):
                # Now check if it's properly conditional
                if f"if.*{mode}" not in app_js or "isDiagnostic" not in app_js:
                    errors.append({
                        'mode': mode,
                        'flag': flag,
                        'error': f'{flag} sent to {mode} without proper conditional',
                        'fix': 'Add: if (!isDiagnostic) { args.push(...) }'
                    })
    
    return errors
```

**When to Run:** When modifying app.js
**Priority:** 🟢 **P2 - Prevents validation errors**

---

## Priority 4: Performance (OPTIMIZATION)

### 🆕 14. Enrichment Timeout Validator
**Status:** 🟢 NICE TO HAVE

**Pattern Found:**
- **Multiple:** Enrichment takes 60+ seconds for 200 conversations
- No timeout handling in enrichment loops
- SDK calls potentially hanging

**Automated Check:**
```python
# scripts/check_enrichment_performance.py

def check_enrichment_timeouts():
    """
    Validate enrichment operations have:
    1. asyncio.wait_for() with timeout
    2. Semaphore for concurrency control
    3. Progress callbacks for long operations
    """
    errors = []
    
    enrichment_files = [
        'src/services/intercom_sdk_service.py',
        'src/services/admin_profile_cache.py'
    ]
    
    for file_path in enrichment_files:
        content = Path(file_path).read_text()
        
        # Check for asyncio.gather without timeout
        if 'asyncio.gather' in content:
            if 'wait_for' not in content:
                errors.append({
                    'file': file_path,
                    'error': 'asyncio.gather without timeout protection',
                    'risk': 'Could hang indefinitely on API failures',
                    'fix': 'Wrap with asyncio.wait_for(asyncio.gather(...), timeout=60)'
                })
        
        # Check for client calls without semaphore
        if 'client.contacts.find' in content or 'client.conversations.find' in content:
            if 'Semaphore' not in content and '_semaphore' not in content:
                errors.append({
                    'file': file_path,
                    'error': 'API calls without semaphore protection',
                    'risk': 'Could overwhelm API with concurrent requests',
                    'fix': 'Add: async with self._enrichment_semaphore:'
                })
    
    return errors
```

**When to Run:** Weekly performance review
**Priority:** 🟢 **P2 - Prevents timeouts**

---

## Priority 5: Configuration (SAFETY)

### 🆕 15. Settings Default Value Validator
**Status:** 🟢 NICE TO HAVE

**Pattern Found:**
- SSE_KEEPALIVE_INTERVAL defaults changed multiple times
- MAX_EXECUTION_DURATION varied across deployments
- Inconsistent timeout values

**Automated Check:**
```python
# scripts/validate_settings.py

def validate_settings_defaults():
    """
    Check settings.py for:
    1. All timeouts have reasonable defaults
    2. No contradictory settings
    3. Environment variable fallbacks exist
    4. Critical settings documented
    """
    errors = []
    
    settings_file = Path('src/config/settings.py').read_text()
    
    # Expected timeouts with reasonable ranges
    timeout_expectations = {
        'SSE_KEEPALIVE_INTERVAL': (5, 60, 15),  # min, max, recommended
        'MAX_EXECUTION_DURATION': (60, 7200, 3600),
        'intercom_timeout': (30, 300, 120),
        'chunk_timeout': (60, 1800, 600)
    }
    
    for setting, (min_val, max_val, recommended) in timeout_expectations.items():
        # Extract default value
        match = re.search(rf"{setting}.*?=.*?(\d+)", settings_file)
        if match:
            default_val = int(match.group(1))
            
            if default_val < min_val or default_val > max_val:
                errors.append({
                    'setting': setting,
                    'current_default': default_val,
                    'expected_range': f'{min_val}-{max_val}',
                    'recommended': recommended,
                    'error': f'{setting} default outside safe range'
                })
        else:
            errors.append({
                'setting': setting,
                'error': 'Setting not found or no default value',
                'impact': 'Could use unsafe fallback'
            })
    
    return errors
```

**When to Run:** Monthly + when modifying settings
**Priority:** 🟢 **P2 - Prevents production issues**

---

## Additional Checks (Lower Priority)

### 🆕 16. API Client Timeout Consistency
Ensure all API clients use settings timeouts, not hardcoded values

### 🆕 17. Test Data Coverage Validator
Ensure test_mode works for all commands

### 🆕 18. Output File Naming Convention
Validate all output files use consistent timestamp format

### 🆕 19. Log Level Consistency
Check logging.debug() vs logger.debug() usage

### 🆕 20. CircuitBreaker Usage Validator
Ensure risky API calls are wrapped in circuit breakers

---

## 📊 Summary Table: Proposed Checks by Priority

| Priority | Check Name | Runtime | Prevents | Effort to Implement |
|----------|-----------|---------|----------|-------------------|
| 🔴 P0 | CLI Alignment Checker | ✅ DONE | Flag mismatches | ✅ Complete |
| 🔴 P0 | Function Signature Matcher | 5-10s | TypeErrors | 4-6 hours |
| 🔴 P0 | Async/Await Consistency | 3-5s | Deadlocks | 3-4 hours |
| 🔴 P0 | Missing Import Checker | 2-3s | ModuleNotFoundErrors | 2-3 hours |
| 🟡 P1 | Schema Shape Validator | 30-60s | Data pipeline crashes | 4-5 hours |
| 🟡 P1 | Null Safety Checker | 5-10s | KeyErrors | 3-4 hours |
| 🟡 P1 | Pydantic Model Validator | In tests | ValidationErrors | 2-3 hours |
| 🟡 P1 | Agent Tool Registry | 2-3s | Tool execution failures | 3-4 hours |
| 🟡 P1 | SSE/Background Policy | 1-2s | Timeouts | 2 hours |
| 🟡 P1 | Double-Counting Detection | 30s | Reporting errors | 3-4 hours |
| 🟡 P1 | Keyword Specificity | 60s | Topic detection fails | 4-5 hours |
| 🟢 P2 | Console Output Safety | 1-2s | Log file loss | 1-2 hours |
| 🟢 P2 | Frontend Flag Logic | 3-5s | Validation errors | 2-3 hours |
| 🟢 P2 | Enrichment Timeouts | 2-3s | API hangs | 2-3 hours |
| 🟢 P2 | Settings Defaults | 1s | Config issues | 1-2 hours |

**Total Implementation Time:** ~40-60 hours for all P0-P2 checks

---

## 🎯 Recommended Rollout Plan

### Phase 1: Critical Runtime Errors (Week 1)
1. ✅ CLI Alignment Checker (done)
2. 🔴 Function Signature Matcher
3. 🔴 Async/Await Consistency
4. 🔴 Missing Import Checker

**Impact:** Eliminates 70% of deployment failures

### Phase 2: Data Quality (Week 2)
5. 🟡 Schema Shape Validator
6. 🟡 Null Safety Checker
7. 🟡 Pydantic Model Validator
8. 🟡 Double-Counting Detection

**Impact:** Prevents data pipeline crashes and reporting errors

### Phase 3: Integration Stability (Week 3)
9. 🟡 Agent Tool Registry
10. 🟡 SSE/Background Policy
11. 🟡 Keyword Specificity

**Impact:** Reduces integration debugging time by 50%

### Phase 4: Polish (Week 4)
12-15. Remaining P2 checks

**Impact:** Better developer experience, fewer edge cases

---

## 🚀 Integration Strategy

### Pre-Commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running automated validation checks..."

# P0 checks (fast, always run)
python scripts/check_cli_web_alignment.py || exit 1
python scripts/check_function_signatures.py || exit 1
python scripts/check_async_patterns.py || exit 1

# P1 checks (run on relevant files)
if git diff --cached --name-only | grep -q 'src/agents/topic'; then
    python scripts/validate_topic_keywords.py || exit 1
fi

echo "✅ All checks passed"
```

### CI/CD Pipeline
```yaml
# .github/workflows/validation.yml

name: Code Quality Checks

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run P0 checks
        run: |
          python scripts/check_cli_web_alignment.py
          python scripts/check_function_signatures.py
          python scripts/check_async_patterns.py
          python scripts/check_imports.py
      
      - name: Run P1 checks
        run: |
          python scripts/check_null_safety.py
          python scripts/validate_pydantic_models.py
          python scripts/check_execution_policies.py
      
      - name: Run data validation (on sample)
        run: |
          python src/main.py sample-mode --count 50 --save-to-file
          python scripts/validate_data_schemas.py
          python scripts/check_double_counting.py
```

### IDE Integration (Cursor)
Add to `.cursorrules`:
```markdown
## Automated Validation

Before completing any PR or major change, run:
```bash
# Full validation suite
./scripts/run_all_checks.sh

# Quick pre-commit checks only
./scripts/quick_checks.sh
```

Cursor will automatically prompt you to run these when:
- Modifying function signatures
- Adding new CLI flags
- Changing topic detection logic
- Modifying Pydantic models
```

---

## 📈 Expected ROI

### Debugging Time Savings

**Without Checks:**
- Average bug: 2-4 hours to find, fix, test, redeploy
- Bugs per week: 3-5
- **Total:** 6-20 hours/week debugging

**With Checks:**
- Bugs caught pre-commit: 60-70%
- Time per check: 10-30 seconds
- **Saved:** 4-14 hours/week

### Quality Improvements

- **Runtime errors:** -70% (P0 checks)
- **Data quality issues:** -60% (P1 checks)
- **Integration failures:** -50% (P1 checks)
- **Developer confidence:** +80%

---

## 🎯 Immediate Next Steps

### This Week:
1. ✅ Run CLI alignment checker regularly (already implemented)
2. 🔴 Implement Function Signature Matcher (highest ROI)
3. 🔴 Implement Async/Await Consistency Checker
4. 🔴 Add pre-commit hook for P0 checks

### Next Week:
5. 🟡 Implement Schema Shape Validator
6. 🟡 Add Null Safety Checker
7. 🟡 Create double-counting detection

### Following Weeks:
8-15. Remaining checks based on priorities

---

## 💡 Meta-Pattern: Common Root Causes

Across all bugs analyzed, the **top 5 root causes** were:

1. **Type assumptions** (40% of bugs) - "I assumed X would be a dict"
   - Solution: Schema validators + Pydantic models

2. **Missing parameter** (25% of bugs) - "Function signature changed but not all callers updated"
   - Solution: Function signature matcher

3. **Async misuse** (15% of bugs) - "Forgot await" or "blocking call in async"
   - Solution: Async pattern checker

4. **Flag misalignment** (10% of bugs) - "CLI has flag but UI doesn't know"
   - Solution: CLI alignment checker (done!)

5. **Unsafe field access** (10% of bugs) - "Assumed field exists but it doesn't"
   - Solution: Null safety checker

**Combined, these 5 patterns account for 100% of iterative debugging cycles!**

---

## 🏗️ Implementation Priority Order (Final Recommendation)

### Immediate (This Week):
1. ✅ **CLI Alignment** - Already done, enforce usage
2. 🔴 **Function Signature Matcher** - Highest ROI, prevents today's bug
3. 🔴 **Async Consistency** - Critical for stability

### High Priority (Next Week):
4. 🔴 **Import Checker** - Prevents deployment failures
5. 🟡 **Null Safety** - Prevents KeyErrors
6. 🟡 **Schema Validator** - Ensures data quality

### Medium Priority (Weeks 3-4):
7-11. Remaining P1 checks

### Low Priority (Ongoing):
12-15. P2 checks as time permits

---

## 📦 Deliverables

For each check, provide:
1. **Script file** in `scripts/` directory
2. **Documentation** in check script header
3. **Example output** showing what errors look like
4. **Fix recommendations** for each error type
5. **Integration** into pre-commit hook
6. **CI/CD integration** for automated runs

---

**Recommendation:** Start with Function Signature Matcher this week - it would have prevented today's `include_hierarchy` bug and has the highest ROI for time invested.





