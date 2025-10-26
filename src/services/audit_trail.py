"""
Audit Trail Service

Provides detailed, human-readable narration of the analysis process
for validation and debugging by data engineers.

Generates a comprehensive audit report showing:
- What data was fetched and from where
- What decisions were made and why
- What transformations were applied
- What metrics were calculated and how
- What AI calls were made and what they returned
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class AuditTrail:
    """Records and narrates the analysis process for auditing"""
    
    def __init__(self, output_dir: str = "outputs"):
        self.steps = []
        self.start_time = datetime.now()
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        self.warnings = []
        self.decisions = []
        self.data_quality_issues = []
        self.tool_calls = []
    
    def step(self, phase: str, action: str, details: Dict[str, Any] = None):
        """
        Record a step in the analysis process.
        
        Args:
            phase: Phase of analysis (e.g., "Data Fetching", "Topic Detection")
            action: What happened (e.g., "Fetched 5000 conversations")
            details: Additional details (counts, decisions, etc.)
        """
        timestamp = datetime.now()
        step_data = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': (timestamp - self.start_time).total_seconds(),
            'phase': phase,
            'action': action,
            'details': details or {}
        }
        self.steps.append(step_data)
        
        # Also log it
        self.logger.info(f"[AUDIT] {phase}: {action}")
        if details:
            self.logger.debug(f"[AUDIT] Details: {details}")
    
    def decision(self, question: str, answer: str, reasoning: str, data: Dict[str, Any] = None):
        """
        Record a decision made during analysis.
        
        Args:
            question: What decision needed to be made
            answer: What was decided
            reasoning: Why this decision was made
            data: Supporting data for the decision
        """
        decision_data = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer': answer,
            'reasoning': reasoning,
            'supporting_data': data or {}
        }
        self.decisions.append(decision_data)
        self.logger.info(f"[DECISION] {question} → {answer}")
        self.logger.debug(f"[DECISION] Because: {reasoning}")
    
    def warning(self, issue: str, impact: str, resolution: str):
        """
        Record a warning or data quality issue.
        
        Args:
            issue: What the problem is
            impact: How it affects the analysis
            resolution: What was done about it
        """
        warning_data = {
            'timestamp': datetime.now().isoformat(),
            'issue': issue,
            'impact': impact,
            'resolution': resolution
        }
        self.warnings.append(warning_data)
        self.logger.warning(f"[AUDIT WARNING] {issue}")
    
    def data_quality_check(self, check_name: str, passed: bool, details: Dict[str, Any]):
        """
        Record a data quality check.

        Args:
            check_name: Name of the check
            passed: Whether the check passed
            details: Check results and metrics
        """
        check_data = {
            'timestamp': datetime.now().isoformat(),
            'check_name': check_name,
            'passed': passed,
            'details': details
        }
        self.data_quality_issues.append(check_data)

        status = "✅ PASSED" if passed else "❌ FAILED"
        self.logger.info(f"[DATA QUALITY] {check_name}: {status}")

    def tool_call(self, tool_name: str, arguments: Dict[str, Any], result: Any, success: bool, execution_time_ms: float, error_message: str = None):
        """
        Record a tool execution in the audit trail.

        Args:
            tool_name: Name of the tool that was called (e.g., "lookup_admin_profile")
            arguments: Arguments passed to the tool
            result: Result data returned by the tool (if successful)
            success: Whether the tool execution succeeded
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if execution failed
        """
        tool_call_data = {
            'timestamp': datetime.now().isoformat(),
            'tool_name': tool_name,
            'arguments': arguments,
            'result': result,
            'success': success,
            'execution_time_ms': execution_time_ms,
            'error_message': error_message
        }
        self.tool_calls.append(tool_call_data)

        # Log the tool call
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"[TOOL CALL] {tool_name} - {status} ({execution_time_ms:.1f}ms)")
        if not success and error_message:
            self.logger.warning(f"[TOOL CALL] {tool_name} - ERROR: {error_message}")
        self.logger.debug(f"[TOOL CALL] Arguments: {arguments}")
    
    def generate_report(self) -> str:
        """
        Generate human-readable audit report.
        
        Returns:
            Markdown-formatted audit report
        """
        report_lines = []
        
        # Header
        report_lines.append("# Analysis Audit Trail")
        report_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Total Duration:** {(datetime.now() - self.start_time).total_seconds():.1f} seconds")
        report_lines.append(f"**Total Steps:** {len(self.steps)}")
        report_lines.append(f"**Decisions Made:** {len(self.decisions)}")
        report_lines.append(f"**Warnings:** {len(self.warnings)}")
        report_lines.append("\n---\n")
        
        # Executive Summary
        report_lines.append("## 📊 Executive Summary\n")
        if self.steps:
            phases = {}
            for step in self.steps:
                phase = step['phase']
                phases[phase] = phases.get(phase, 0) + 1
            
            report_lines.append("**Phases Completed:**")
            for phase, count in phases.items():
                report_lines.append(f"- {phase}: {count} steps")

            # Add tool call summary to executive summary
            if self.tool_calls:
                report_lines.append("\n**Tool Calls:**")
                successful = sum(1 for tc in self.tool_calls if tc['success'])
                failed = len(self.tool_calls) - successful
                report_lines.append(f"- Total: {len(self.tool_calls)} ({successful} successful, {failed} failed)")

                # List unique tools used
                tools_used = set(tc['tool_name'] for tc in self.tool_calls)
                report_lines.append(f"- Tools Used: {', '.join(tools_used)}")

        report_lines.append("\n---\n")
        
        # Data Quality Checks
        if self.data_quality_issues:
            report_lines.append("## ✅ Data Quality Checks\n")
            for check in self.data_quality_issues:
                status = "✅ PASSED" if check['passed'] else "❌ FAILED"
                report_lines.append(f"### {status} {check['check_name']}\n")
                report_lines.append(f"**When:** {check['timestamp']}\n")
                
                if check['details']:
                    report_lines.append("**Results:**")
                    for key, value in check['details'].items():
                        report_lines.append(f"- {key}: {value}")
                report_lines.append("")
            
            report_lines.append("---\n")
        
        # Decisions
        if self.decisions:
            report_lines.append("## 🤔 Key Decisions\n")
            for i, decision in enumerate(self.decisions, 1):
                report_lines.append(f"### Decision #{i}: {decision['question']}\n")
                report_lines.append(f"**Answer:** {decision['answer']}\n")
                report_lines.append(f"**Reasoning:** {decision['reasoning']}\n")
                
                if decision['supporting_data']:
                    report_lines.append("**Supporting Data:**")
                    for key, value in decision['supporting_data'].items():
                        report_lines.append(f"- {key}: {value}")
                report_lines.append("")
            
            report_lines.append("---\n")
        
        # Warnings
        if self.warnings:
            report_lines.append("## ⚠️ Warnings and Issues\n")
            for i, warning in enumerate(self.warnings, 1):
                report_lines.append(f"### Warning #{i}: {warning['issue']}\n")
                report_lines.append(f"**Impact:** {warning['impact']}\n")
                report_lines.append(f"**Resolution:** {warning['resolution']}\n")
                report_lines.append("")
            
            report_lines.append("---\n")

        # Tool Calls Section
        if self.tool_calls:
            report_lines.append("## 🔧 Tool Calls\n")

            # Summary
            successful_count = sum(1 for tc in self.tool_calls if tc['success'])
            failed_count = len(self.tool_calls) - successful_count
            total_time = sum(tc['execution_time_ms'] for tc in self.tool_calls)

            report_lines.append(f"**Total Tool Calls:** {len(self.tool_calls)}")
            report_lines.append(f"**Successful:** {successful_count}")
            report_lines.append(f"**Failed:** {failed_count}")
            report_lines.append(f"**Total Execution Time:** {total_time:.1f}ms\n")

            # Individual tool calls
            for i, tc in enumerate(self.tool_calls, 1):
                status = "✅ SUCCESS" if tc['success'] else "❌ FAILED"
                report_lines.append(f"### Tool Call #{i}: {tc['tool_name']} - {status}\n")
                report_lines.append(f"**When:** {tc['timestamp']}")
                report_lines.append(f"**Execution Time:** {tc['execution_time_ms']:.1f}ms\n")

                # Arguments
                report_lines.append("**Arguments:**")
                for key, value in tc['arguments'].items():
                    report_lines.append(f"  - {key}: `{value}`")

                # Result or error
                if tc['success']:
                    report_lines.append("\n**Result:**")
                    if isinstance(tc['result'], dict):
                        for key, value in tc['result'].items():
                            report_lines.append(f"  - {key}: `{value}`")
                    else:
                        report_lines.append(f"  - {tc['result']}")
                else:
                    report_lines.append(f"\n**Error:** {tc['error_message']}")

                report_lines.append("")

            report_lines.append("---\n")

        # Detailed Step-by-Step
        report_lines.append("## 📋 Detailed Step-by-Step Process\n")
        
        current_phase = None
        for i, step in enumerate(self.steps, 1):
            # Add phase header when phase changes
            if step['phase'] != current_phase:
                current_phase = step['phase']
                report_lines.append(f"\n### Phase: {current_phase}\n")
            
            elapsed = f"{step['elapsed_seconds']:.1f}s"
            report_lines.append(f"**Step {i}** ({elapsed}): {step['action']}")
            
            # Add details if present
            if step['details']:
                for key, value in step['details'].items():
                    # Format based on value type
                    if isinstance(value, (int, float)):
                        report_lines.append(f"  - {key}: `{value:,}` " if isinstance(value, int) else f"  - {key}: `{value:.2f}`")
                    elif isinstance(value, list) and len(value) > 5:
                        report_lines.append(f"  - {key}: `{len(value)}` items")
                    else:
                        report_lines.append(f"  - {key}: `{value}`")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_report(self, filename: str = None) -> str:
        """
        Save audit report to file.
        
        Args:
            filename: Optional filename (auto-generated if not provided)
            
        Returns:
            Path to saved report
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"audit_trail_{timestamp}.md"
        
        filepath = self.output_dir / filename
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_report()
        
        with open(filepath, 'w') as f:
            f.write(report)
        
        self.logger.info(f"Audit trail saved to: {filepath}")
        return str(filepath)
    
    def save_json(self, filename: str = None) -> str:
        """
        Save audit trail as JSON for programmatic analysis.
        
        Args:
            filename: Optional filename (auto-generated if not provided)
            
        Returns:
            Path to saved JSON file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"audit_trail_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        audit_data = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'steps': self.steps,
            'decisions': self.decisions,
            'warnings': self.warnings,
            'data_quality_checks': self.data_quality_issues,
            'tool_calls': self.tool_calls
        }
        
        with open(filepath, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        self.logger.info(f"Audit trail JSON saved to: {filepath}")
        return str(filepath)
    
    def print_summary(self):
        """Log a quick summary (uses logging instead of print for proper output handling)"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        self.logger.info("=" * 80)
        self.logger.info("📋 AUDIT TRAIL SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Duration: {duration:.1f}s")
        self.logger.info(f"Steps: {len(self.steps)}")
        self.logger.info(f"Decisions: {len(self.decisions)}")
        self.logger.info(f"Warnings: {len(self.warnings)}")
        self.logger.info(f"Data Quality Checks: {len(self.data_quality_issues)}")
        self.logger.info(f"Tool Calls: {len(self.tool_calls)}")
        if self.tool_calls:
            successful = sum(1 for tc in self.tool_calls if tc['success'])
            self.logger.info(f"  Successful: {successful}")
            self.logger.info(f"  Failed: {len(self.tool_calls) - successful}")
        
        if self.warnings:
            self.logger.warning("⚠️ WARNINGS:")
            for w in self.warnings[:5]:
                self.logger.warning(f"  - {w['issue']}")
        
        self.logger.info("=" * 80)


class AuditableAnalysis:
    """
    Mixin class to add audit trail capabilities to any analyzer.
    
    Usage:
        class MyAnalyzer(AuditableAnalysis):
            def __init__(self):
                self.init_audit_trail()
            
            def analyze(self):
                self.audit.step("Analysis", "Starting analysis", {'count': 100})
                # ... do work ...
                self.audit.decision("Should we filter?", "Yes", "Because X > Y")
    """
    
    def init_audit_trail(self, output_dir: str = "outputs"):
        """Initialize audit trail for this analyzer"""
        self.audit = AuditTrail(output_dir)
        self.audit_enabled = True
    
    def disable_audit(self):
        """Disable audit trail (for performance)"""
        self.audit_enabled = False
    
    def enable_audit(self):
        """Enable audit trail"""
        self.audit_enabled = True
    
    def save_audit_report(self) -> Optional[str]:
        """Save audit report if enabled"""
        if self.audit_enabled and hasattr(self, 'audit'):
            markdown_path = self.audit.save_report()
            json_path = self.audit.save_json()
            return markdown_path
        return None

    def record_tool_calls_from_agent(self, agent_result: Any):
        """
        Convenience method to record all tool calls from an AgentResult

        Args:
            agent_result: AgentResult object containing tool_calls_made list
        """
        if hasattr(agent_result, 'data') and 'tool_calls_summary' in agent_result.data:
            tool_calls = agent_result.data['tool_calls_summary'].get('calls', [])
            for tc in tool_calls:
                self.audit.tool_call(
                    tool_name=tc['tool_name'],
                    arguments=tc['arguments'],
                    result=tc.get('result'),
                    success=tc['success'],
                    execution_time_ms=tc['execution_time_ms'],
                    error_message=tc.get('error_message')
                )
            self.logger.info(f"Recorded {len(tool_calls)} tool calls from {agent_result.agent_name}")

