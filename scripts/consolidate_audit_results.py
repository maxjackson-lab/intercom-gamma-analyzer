#!/usr/bin/env python3
import argparse
import json
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

def parse_audit_data(report_path: Path) -> Dict[str, Any]:
    """Parses the audit data (markdown or JSON) to extract scores and issues."""
    if report_path.suffix == '.json':
        return parse_audit_json(report_path)
    else:
        return parse_audit_markdown(report_path)

def parse_audit_json(report_path: Path) -> Dict[str, Any]:
    """Parses the JSON audit report."""
    try:
        data = json.loads(report_path.read_text(encoding='utf-8'))
        agents = []
        
        for agent_name, info in data.items():
            # Handle both dict (new format) and potentially other structures
            if not isinstance(info, dict):
                continue
                
            score = info.get('quality_score', 0.0)
            if score is None:
                score = 0.0
                
            issues = info.get('issues_found', [])
            # Add specific flags if present
            flags = []
            if info.get('hallucination_flags'):
                flags.append("Hallucinations detected")
            
            # Combine issues and flags
            all_issues = issues + flags
            issues_str = "; ".join(all_issues) if all_issues else "None"
            
            status_text = "PASS" if info.get('passed', False) else "FAIL"
            
            agents.append({
                "name": agent_name,
                "score": float(score),
                "status": status_text,
                "issues": issues_str,
                "flags": flags  # Keep flags separate for enrichment
            })
            
        return {"agents": agents}
    except Exception as e:
        print(f"Warning: Failed to parse JSON audit report: {e}")
        return {"agents": []}

def parse_audit_markdown(report_path: Path) -> Dict[str, Any]:
    """Parses the markdown audit report to extract scores and issues."""
    content = report_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    agents = []
    parsing_table = False
    headers = []
    
    # Column indices (defaults)
    idx_map = {
        'agent': 0,
        'status': 1,
        'score': 2,
        'issues': 3
    }
    
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
            
        # Split by pipe and clean
        parts = [p.strip() for p in line.strip('|').split('|')]
        
        # Check for header row
        if not parsing_table and ("Agent" in parts[0] or "Status" in parts or "Pass/Fail" in parts):
            parsing_table = True
            # Dynamically map columns
            for i, part in enumerate(parts):
                header = part.lower()
                if "agent" in header:
                    idx_map['agent'] = i
                elif "status" in header or "pass/fail" in header or "state" in header:
                    idx_map['status'] = i
                elif "score" in header:
                    idx_map['score'] = i
                elif "findings" in header or "issues" in header:
                    idx_map['issues'] = i
            continue
            
        if "---" in parts[0]:
            continue
            
        if parsing_table and len(parts) >= 3:
            try:
                agent_name = parts[idx_map['agent']]
                
                # Robust score parsing
                score_str = parts[idx_map['score']]
                # Remove non-numeric chars except dot
                clean_score = re.sub(r'[^\d.]', '', score_str)
                quality_score = float(clean_score) if clean_score else 0.0
                
                status_raw = parts[idx_map['status']].lower()
                issues = parts[idx_map['issues']] if len(parts) > idx_map['issues'] else ""
                
                # Normalize status
                if "pass" in status_raw or "✅" in status_raw:
                    status_text = "PASS"
                elif "fail" in status_raw or "❌" in status_raw:
                    status_text = "FAIL"
                else:
                    status_text = "RISK"
                
                agents.append({
                    "name": agent_name,
                    "score": quality_score,
                    "status": status_text,
                    "issues": issues,
                    "flags": [] # No structured flags in markdown usually
                })
            except (ValueError, IndexError) as e:
                print(f"Warning: Failed to parse line '{line}': {e}")
                continue
            
    return {"agents": agents}

def parse_observability(obs_path: Path) -> Dict[str, Any]:
    """Parses the observability JSON to extract key metrics and error analysis."""
    try:
        data = json.loads(obs_path.read_text(encoding='utf-8'))
        summary = data.get("summary", {})
        events = data.get("events", [])
        
        # Error Classification
        raw_errors = summary.get("errors", [])
        error_breakdown = {
            "timeout": 0,
            "rate_limit": 0,
            "prompt_refusal": 0,
            "other": 0,
            "by_agent": {}
        }
        
        for error in raw_errors:
            # Handle both string errors and object errors
            err_str = str(error).lower()
            if isinstance(error, dict):
                err_str = str(error.get('message', '')).lower() + str(error.get('type', '')).lower()
            
            # Classify
            if "timeout" in err_str or "timed out" in err_str:
                error_breakdown["timeout"] += 1
            elif "429" in err_str or "rate limit" in err_str:
                error_breakdown["rate_limit"] += 1
            elif "refusal" in err_str or "refused" in err_str:
                error_breakdown["prompt_refusal"] += 1
            else:
                error_breakdown["other"] += 1
                
            # Attempt to attribute to agent if possible (requires agent field in error or context)
            # For now, simple count. If error object has 'agent', use it.
            if isinstance(error, dict) and 'agent' in error:
                agent = error['agent']
                error_breakdown["by_agent"][agent] = error_breakdown["by_agent"].get(agent, 0) + 1

        # Attempt to find conversation count
        sample_size = "Unknown"
        # Strategy 1: Look for explicit count in summary
        if "conversation_count" in summary:
            sample_size = summary["conversation_count"]
        # Strategy 2: Look for context in events
        else:
            for event in events:
                ctx = event.get("context", {})
                if "conversation_count" in ctx:
                    sample_size = ctx["conversation_count"]
                    break
        
        return {
            "total_events": summary.get("total_events", 0),
            "success_rate": summary.get("success_rate", 0.0),
            "total_errors": summary.get("error_count", 0),
            "total_tokens": summary.get("total_tokens", 0),
            "agent_performance": summary.get("events_by_agent", {}),
            "error_analysis": {
                "errors": len(raw_errors),
                "breakdown": error_breakdown
            },
            "sample_size": sample_size
        }
    except Exception as e:
        print(f"Warning: Failed to parse observability: {e}")
        return {
            "total_events": 0,
            "success_rate": 0.0,
            "total_errors": 0,
            "total_tokens": 0,
            "agent_performance": {},
            "error_analysis": {"errors": 0, "breakdown": {}},
            "sample_size": "Unknown"
        }

def parse_thinking_log(log_path: Path) -> List[Dict[str, str]]:
    """Parses the thinking log for structured insights."""
    if not log_path.exists():
        return []
        
    content = log_path.read_text(encoding='utf-8')
    insights = []
    
    # Look for Customer Quote patterns
    # Pattern 1: "Customer Quote": "..."
    # Pattern 2: Customer Quote: ...
    
    # Simple block extraction - look for "Customer Quote" and grab following lines
    quote_matches = re.finditer(r'Customer Quote:?\s*"?([^"\n]+)"?', content)
    
    for match in quote_matches:
        quote = match.group(1)
        # Search for Topic and Severity nearby (hacky but robust enough for logs)
        # We limit search to next 500 chars
        start_idx = match.end()
        search_window = content[start_idx:start_idx+500]
        
        topic_match = re.search(r'Topic:?\s*([^\n]+)', search_window)
        severity_match = re.search(r'Severity:?\s*([^\n]+)', search_window)
        
        topic = topic_match.group(1).strip() if topic_match else "Unknown"
        severity = severity_match.group(1).strip() if severity_match else "Unknown"
        
        insights.append({
            "quote": quote,
            "topic": topic,
            "severity": severity
        })
        
        if len(insights) >= 3: # Limit to top 3
            break
            
    return insights

def generate_consolidated_report(
    audit_data: Dict[str, Any], 
    obs_data: Dict[str, Any], 
    insights: List[Dict[str, str]],
    files: Dict[str, str]
) -> str:
    """Generates the consolidated markdown report."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sample_size = obs_data.get('sample_size', 'Unknown')
    
    report = f"""# Agent Audit Results
**Last Updated:** {timestamp}
**Sample Size:** {sample_size} Conversations

## Executive Scorecard

| Agent Name | Status | Quality Score | Key Findings / Issues |
|------------|--------|---------------|-----------------------|
"""
    
    for agent in audit_data['agents']:
        status_icon = "✅" if agent['status'] == "PASS" else "❌" if agent['status'] == "FAIL" else "⚠️"
        
        issues = agent['issues']
        # Append structured flags if not already present
        flags = agent.get('flags', [])
        for flag in flags:
            if flag not in issues:
                issues += f"; {flag}" if issues and issues != "None" else flag
                
        report += f"| {agent['name']} | {status_icon} {agent['status']} | {agent['score']} | {issues} |\n"

    report += """
## Context Loss Map

| Stage | Count | Notes |
|-------|-------|-------|
"""
    # Try to get dynamic counts from observability or sample_size
    ingestion_count = sample_size if sample_size != "Unknown" else "--"
    
    report += f"| **Ingestion** | {ingestion_count} | Conversations fetched from Intercom |\n"
    report += f"| **Segmentation** | -- | (Check logs for drop-offs) |\n"
    report += f"| **Topic Detection** | -- | (Check for inflation >100) |\n"
    report += f"| **Sentiment Analysis** | -- | (Check for silent failures) |\n"
    report += f"| **Formatting** | -- | (Final report inclusion) |\n"
    
    if sample_size == "Unknown" or str(sample_size) == "--":
         report += "\n> **Note:** Automated context metrics are not yet available.\n"

    report += "\n## Actionable Insights (Sample)\n\n"
    
    if insights:
        report += "*Extracted from `agent_thinking.log`*\n\n"
        for insight in insights:
            report += f"> **Customer Quote**: \"{insight['quote']}\"\n"
            report += f"> *Topic*: {insight['topic']}\n"
            report += f"> *Severity*: {insight['severity']}\n\n"
    else:
        report += "*No structured actionable insights extracted from logs. Ensure log format includes 'Customer Quote:', 'Topic:', and 'Severity:' markers.*\n"

    report += """
## Recommended Remediation

### 🚨 Critical Priority (< 0.6 Score)
"""
    # List failing agents
    failing = [a for a in audit_data['agents'] if a['score'] < 0.6]
    if failing:
        for a in failing:
            report += f"- **{a['name']}** ({a['score']}): {a['issues']}\n"
    else:
        report += "- None\n"

    report += "\n### ⚠️ High Priority (Hallucinations / Errors)\n"
    # List risk agents OR agents with specific flags
    risk = [a for a in audit_data['agents'] if (0.6 <= a['score'] < 0.8) or a.get('flags')]
    if risk:
        for a in risk:
            issues = a['issues']
            report += f"- **{a['name']}** ({a['score']}): {issues}\n"
    else:
        report += "- None\n"
        
    # Observability Summary
    obs_summary = f"""
## Observability Analysis Summary

- **Total Events**: {obs_data['total_events']}
- **Overall Success Rate**: {obs_data['success_rate']*100:.1f}%
- **Total Errors**: {obs_data['total_errors']}
- **Total Tokens**: {obs_data['total_tokens']:,}

### Failure Patterns
"""
    
    err_breakdown = obs_data['error_analysis'].get('breakdown', {})
    if obs_data['total_errors'] == 0:
        obs_summary += "- No errors recorded.\n"
    else:
        obs_summary += f"- **Timeouts**: {err_breakdown.get('timeout', 0)}\n"
        obs_summary += f"- **Rate Limits**: {err_breakdown.get('rate_limit', 0)}\n"
        obs_summary += f"- **Prompt Refusals**: {err_breakdown.get('prompt_refusal', 0)}\n"
        obs_summary += f"- **Other**: {err_breakdown.get('other', 0)}\n"
        
        if err_breakdown.get('by_agent'):
            obs_summary += "\n**Errors by Agent:**\n"
            for agent, count in err_breakdown['by_agent'].items():
                obs_summary += f"- {agent}: {count}\n"

    report += obs_summary

    report += f"""
## Raw Data References

- **Thinking Log**: `{files.get('log', 'N/A')}`
- **Observability Data**: `{files.get('obs', 'N/A')}`
- **Audit Report**: `{files.get('audit', 'N/A')}`
"""

    return report

def main():
    parser = argparse.ArgumentParser(description="Consolidate Phase 1 Audit Results")
    parser.add_argument("--audit-report", required=True, type=Path, help="Path to agent_audit_report_*.md or agent_audit_results_*.json")
    parser.add_argument("--observability", required=True, type=Path, help="Path to agent_thinking_*.observability.json")
    parser.add_argument("--thinking-log", type=Path, help="Path to agent_thinking_*.log")
    parser.add_argument("--output", type=Path, default=Path("docs/AGENT_AUDIT_RESULTS.md"), help="Output path")
    
    args = parser.parse_args()
    
    if not args.audit_report.exists():
        print(f"Error: Audit report not found at {args.audit_report}")
        sys.exit(1)
        
    if not args.observability.exists():
        print(f"Error: Observability file not found at {args.observability}")
        sys.exit(1)
        
    print(f"Processing audit report: {args.audit_report}")
    print(f"Processing observability: {args.observability}")
    
    # Determine thinking log path if not provided
    log_path = args.thinking_log
    if not log_path:
        potential_log = Path(str(args.observability).replace(".observability.json", ".log"))
        if potential_log.exists():
            log_path = potential_log
            
    if log_path:
        print(f"Processing thinking log: {log_path}")
    
    try:
        audit_data = parse_audit_data(args.audit_report)
        obs_data = parse_observability(args.observability)
        insights = parse_thinking_log(log_path) if log_path else []
        
        file_refs = {
            "audit": str(args.audit_report),
            "obs": str(args.observability),
            "log": str(log_path) if log_path else "N/A"
        }
        
        consolidated_report = generate_consolidated_report(audit_data, obs_data, insights, file_refs)
        
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(consolidated_report, encoding='utf-8')
        print(f"Successfully wrote consolidated report to {args.output}")
        
    except Exception as e:
        print(f"Error consolidating results: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
