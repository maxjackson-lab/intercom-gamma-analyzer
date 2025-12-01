"""
Agent Audit Framework - Validation and Hallucination Detection.

This module provides a framework for auditing agent outputs to detect:
- Hallucinations (generic language, contradictions, unsupported claims, fabricated data)
- Quality issues (low specificity, missing evidence)
- Logic errors (inconsistent data, missing fields)
"""

import re
import json
import logging
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.agents.base_agent import AgentResult, ConfidenceLevel
from src.utils.output_manager import get_output_file_path

logger = logging.getLogger(__name__)
console = Console()

class AgentAuditResult(BaseModel):
    """Structured result of an agent audit."""
    agent_name: str
    quality_score: float = Field(ge=0.0, le=1.0)
    passed: bool
    hallucination_flags: List[Dict[str, Any]] = Field(default_factory=list)
    validation_checks: Dict[str, bool] = Field(default_factory=dict)
    issues_found: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)

class HallucinationDetector:
    """Detects potential hallucinations in agent outputs."""
    
    GENERIC_PATTERNS = [
        r"customers? (are|seem|appear) frustrated",
        r"users? (want|need|request) more",
        r"people (are|seem) confused",
        r"various issues?",
        r"multiple problems?",
        r"general (feedback|inquiries|questions)",
        r"trending up",  # suspicious if no historical data
        r"trending down",
        r"high volume",  # suspicious if no numbers
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def detect_generic_language(self, text: str) -> List[str]:
        """Check for vague patterns that suggest hallucination or laziness."""
        flags = []
        if not text:
            return flags
        for pattern in self.GENERIC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(f"Generic pattern found: '{pattern}'")
        return flags

    def detect_contradictions(self, data: Dict[str, Any]) -> List[str]:
        """Find logical inconsistencies in the data."""
        flags = []
        
        # Heuristic 1: Sentiment vs Metrics mismatch
        # If sentiment is very positive but pain points are numerous or metrics are poor
        if 'sentiment_insight' in data and 'positive' in data['sentiment_insight'].lower():
             if len(data.get('pain_points', [])) > 5:
                 flags.append("Contradiction: Positive sentiment but many pain points")
        
        # Heuristic 2: Metric bounds (redundant with specific auditor checks but good as backup)
        for key, val in data.items():
            if isinstance(val, (int, float)) and 'rate' in key:
                if val < 0 or val > 1.0:
                    flags.append(f"Contradiction: Rate metric {key} out of bounds ({val})")
                    
        return flags

    def detect_unsupported_claims(self, text: str, evidence: List[str]) -> List[str]:
        """Identify claims without evidence."""
        flags = []
        if not text:
            return flags
        # Simple heuristic: checks for quantitative claims without numbers
        if "significant increase" in text.lower() and not re.search(r"\d+%", text):
            flags.append("Claim 'significant increase' without percentage evidence")
        return flags

    def detect_fabricated_data(self, text: str, valid_ids: List[str]) -> List[str]:
        """Check for IDs or URLs that don't exist in the input."""
        flags = []
        if not text or not valid_ids:
            return flags
            
        # Extract potential conversation IDs (digits or specific format)
        # Assuming conversation IDs are numeric or specific format found in text
        # This is a simple regex for numeric IDs of length 5+
        found_ids = re.findall(r'\b\d{5,}\b', text)
        
        # Filter out numbers that are likely just quantities/counts (usually smaller, but 5 digits might be ID)
        # A better approach is to check if ANY found ID is NOT in valid_ids
        valid_set = set(str(vid) for vid in valid_ids)
        
        for fid in found_ids:
            if fid not in valid_set:
                # Be careful about false positives (e.g. ticket counts)
                # Only flag if it explicitly looks like a reference, but for now we just flag
                # could add check if it follows "conversation" or "ticket"
                if re.search(fr"(conversation|ticket|id)\s+#?{fid}", text, re.IGNORECASE):
                     flags.append(f"Fabricated Data: Referenced conversation ID {fid} not in input")
                     
        return flags

    def calculate_hallucination_score(self, flags: List[Dict]) -> float:
        """Aggregate score (0.0 = clean, 1.0 = severe hallucination)."""
        if not flags:
            return 0.0
        # Simple count-based score for now, capped at 1.0
        # Contradictions and fabrications are weighted heavier
        score = 0.0
        for flag in flags:
            ftype = flag.get('type', '')
            if 'contradiction' in ftype.lower() or 'fabricated' in ftype.lower():
                score += 0.5
            else:
                score += 0.2
        return min(1.0, score)

class BaseAgentAuditor(ABC):
    """Abstract base class for agent-specific auditors."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.detector = HallucinationDetector()
        self.logger = logging.getLogger(f"auditor.{agent_name}")

    @abstractmethod
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        """Run audit on agent result."""
        pass

    def validate_output_structure(self, data: Dict, required_fields: List[str]) -> Dict[str, bool]:
        """Check required fields are present."""
        checks = {}
        if not isinstance(data, dict):
            return {f"has_{field}": False for field in required_fields}
            
        for field in required_fields:
            checks[f"has_{field}"] = field in data and data[field] is not None
        return checks

    def calculate_quality_score(self, specificity: float, evidence: float, consistency: float, completeness: float) -> float:
        """Aggregate quality score (0.0-1.0)."""
        # Weighted average
        score = (specificity * 0.3) + (evidence * 0.3) + (consistency * 0.2) + (completeness * 0.2)
        return round(max(0.0, min(1.0, score)), 2)
        
    def check_common_issues(self, result: AgentResult) -> List[str]:
        """Check for common agent failures (success=False, low confidence)."""
        issues = []
        if not result.success:
            issues.append(f"Agent execution failed: {result.error_message}")
        
        conf = result.confidence
        # Support both float and ConfidenceLevel enum
        if hasattr(result, 'confidence_level'):
             # If confidence is float but we have level, check level
             pass
        elif isinstance(conf, (int, float)) and conf < 0.5:
            issues.append(f"Very low confidence: {conf}")
            
        return issues

# --- Agent-Specific Auditors ---

class SegmentationAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['segmentation_summary', 'agent_assignments'])
        issues = self.check_common_issues(result)
        flags = []
        
        # Validation Logic
        summary = data.get('segmentation_summary', {})
        if summary.get('total_conversations', 0) > 0:
            if summary.get('paid_count', 0) == 0 and summary.get('free_count', 0) == 0:
                issues.append("No conversations classified as Paid or Free")
        
        # Check for vendor assignment (if applicable)
        assignments = data.get('agent_assignments', {})
        if assignments:
            vendors = set()
            for details in assignments.values():
                if isinstance(details, dict):
                    vendors.add(details.get('vendor', 'unknown'))
            if len(vendors) == 1 and 'unknown' in vendors:
                issues.append("All agents assigned to 'unknown' vendor")

        # Score calculation
        completeness = 1.0 if all(checks.values()) else 0.5
        consistency = 1.0 if not issues else 0.5
        specificity = 1.0 # Segmentation is categorical
        evidence = 1.0 # Hard to judge without deep data inspection
        
        # Penalize quality if failed
        if not result.success:
            consistency = 0.0
            completeness = 0.0
        
        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6 and not issues,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=["Check vendor email mapping"] if issues else []
        )

class TopicDetectionAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['topic_distribution', 'topics_by_conversation'])
        issues = self.check_common_issues(result)
        flags = []
        
        dist = data.get('topic_distribution', {})
        if dist:
            unknown = dist.get('Unknown', {}).get('percentage', 0)
            if unknown > 50:
                issues.append(f"High 'Unknown' topic rate: {unknown}%")
        
        # Check for detection method
        topics_by_conv = data.get('topics_by_conversation', {})
        methods = set()
        for conv_topics in topics_by_conv.values():
            for t in conv_topics:
                methods.add(t.get('method', 'unknown'))
        
        checks['method_tracking'] = len(methods) > 0
        
        completeness = 1.0 if all(checks.values()) else 0.5
        consistency = 0.8 if dist and dist.get('Unknown', {}).get('percentage', 0) < 30 else 0.4
        specificity = 1.0
        evidence = 1.0
        
        if not result.success:
             consistency = 0.0
        
        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=["Improve keyword list", "Check LLM fallback"] if issues else []
        )

class SubTopicDetectionAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['subtopics_by_topic'])
        issues = self.check_common_issues(result)
        flags = []
        
        subtopics = data.get('subtopics_by_topic', {})
        for topic, subs in subtopics.items():
            if len(subs) < 2 and len(subs) > 0:
                issues.append(f"Topic '{topic}' has very few subtopics ({len(subs)})")
            for sub in subs:
                name = sub.get('name', '').lower()
                # Check for generic names
                generic_flags = self.detector.detect_generic_language(name)
                if generic_flags:
                    flags.append({'type': 'generic_subtopic', 'text': name, 'detail': generic_flags[0]})
                    
        completeness = 1.0 if all(checks.values()) else 0.5
        specificity = 1.0 - (len(flags) * 0.1)
        consistency = 1.0
        evidence = 1.0
        
        if not result.success:
            consistency = 0.0
        
        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=["Ensure subtopics are distinct"] if flags else []
        )

class TopicSentimentAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['sentiment_insight', 'pain_level'])
        issues = self.check_common_issues(result)
        flags = []
        
        insight = data.get('sentiment_insight', '')
        if len(insight) < 20:
            issues.append("Sentiment insight is too short")
        
        # Hallucination checks
        generic_flags = self.detector.detect_generic_language(insight)
        for flag in generic_flags:
            flags.append({'type': 'generic_sentiment', 'text': insight, 'detail': flag})
            
        contradiction_flags = self.detector.detect_contradictions(data)
        for flag in contradiction_flags:
            flags.append({'type': 'contradiction', 'text': insight, 'detail': flag})
            
        # Fabricated data check if context available
        if input_context and 'valid_ids' in input_context:
            fab_flags = self.detector.detect_fabricated_data(insight, input_context['valid_ids'])
            for flag in fab_flags:
                flags.append({'type': 'fabricated_data', 'text': insight, 'detail': flag})

        # Validate pain_level
        pain_level = data.get('pain_level')
        normalized_pain = str(pain_level).upper() if pain_level else None
        
        if not pain_level:
             issues.append("Missing pain_level field")
             # Backward compatibility check: see if positive/negative words exist
             if "positive" not in insight.lower() and "negative" not in insight.lower():
                 pass # Already flagged as missing field
        elif normalized_pain not in ['SEVERE', 'MODERATE', 'LOW']:
             issues.append(f"Invalid pain_level value: {pain_level}")

        # Check consistency between pain_level and narrative
        if normalized_pain == 'SEVERE' and not any(w in insight.lower() for w in ['severe', 'furious', 'hate', 'critical', 'trust', 'broken', 'blocked']):
             flags.append({'type': 'inconsistency', 'text': insight, 'detail': "SEVERE pain level but mild narrative"})

        hallucination_score = self.detector.calculate_hallucination_score(flags)
        
        completeness = 1.0 if all(checks.values()) else 0.5
        specificity = 1.0 - hallucination_score
        consistency = 1.0 - (0.5 if contradiction_flags else 0.0)
        evidence = 1.0 - (0.5 if any('fabricated' in f['type'] for f in flags) else 0.0)
        
        if not result.success:
             consistency = 0.0
        
        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=["Be more specific in sentiment analysis"] if flags else []
        )

class ExampleExtractionAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['examples_by_topic'])
        issues = self.check_common_issues(result)
        flags = []
        
        examples = data.get('examples_by_topic', {})
        total_examples = sum(len(v) for v in examples.values())
        if total_examples == 0:
            issues.append("No examples extracted")
        
        for topic, topic_examples in examples.items():
            for ex in topic_examples:
                if 'id' not in ex or 'quote' not in ex:
                    issues.append(f"Malformed example in topic {topic}")
                elif len(ex.get('quote', '')) < 10:
                    issues.append(f"Quote too short in topic {topic}")

        completeness = 1.0 if all(checks.values()) and total_examples > 0 else 0.0
        specificity = 1.0
        consistency = 1.0
        evidence = 1.0
        
        if not result.success:
            consistency = 0.0

        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=[]
        )

class FinPerformanceAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['total_fin_conversations', 'resolution_rate', 'handoff_rate'])
        issues = self.check_common_issues(result)
        flags = []
        
        res_rate = data.get('resolution_rate', 0)
        if res_rate == 1.0:
            issues.append("Suspicious 100% resolution rate")
        if res_rate == 0.0 and data.get('total_fin_conversations', 0) > 10:
            issues.append("Suspicious 0% resolution rate with significant volume")
            
        metrics = ['resolution_rate', 'handoff_rate']
        for m in metrics:
            val = data.get(m)
            if val is not None and (val < 0 or val > 1):
                issues.append(f"Metric {m} out of bounds: {val}")
                
        # Detect contradictions
        contradiction_flags = self.detector.detect_contradictions(data)
        for flag in contradiction_flags:
            flags.append({'type': 'contradiction', 'text': 'metrics', 'detail': flag})

        hallucination_score = self.detector.calculate_hallucination_score(flags)

        completeness = 1.0 if all(checks.values()) else 0.5
        consistency = 1.0 if not issues and not contradiction_flags else 0.6
        specificity = 1.0
        evidence = 1.0 # Quantitative data
        
        if not result.success:
            consistency = 0.0
            
        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6 and not issues,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=["Verify metric calculations"] if issues else []
        )

class BpoPerformanceAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['vendor_overview', 'pressure_points'])
        issues = self.check_common_issues(result)
        flags = []
        
        overview = data.get('vendor_overview', {})
        if not overview:
            issues.append("No vendor overview data")
        
        pressure_points = data.get('pressure_points', [])
        for point in pressure_points:
            generic_flags = self.detector.detect_generic_language(point)
            for flag in generic_flags:
                flags.append({'type': 'generic_pressure_point', 'text': point, 'detail': flag})

        completeness = 1.0 if all(checks.values()) else 0.5
        specificity = 1.0 - (len(flags) * 0.2)
        consistency = 1.0
        evidence = 1.0
        
        if not result.success:
            consistency = 0.0

        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=["Ensure pressure points are specific"] if flags else []
        )

class CorrelationAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['correlations'])
        issues = self.check_common_issues(result)
        flags = []
        
        correlations = data.get('correlations', [])
        for corr in correlations:
            if 'correlation' in corr:
                val = corr['correlation']
                if val < -1 or val > 1:
                    issues.append(f"Correlation value out of bounds: {val}")
            else:
                issues.append("Missing 'correlation' value in result")

        completeness = 1.0 if all(checks.values()) else 0.5
        consistency = 1.0 if not issues else 0.6
        specificity = 1.0
        evidence = 1.0
        
        if not result.success:
            consistency = 0.0

        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6 and not issues,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=[]
        )

class QualityInsightsAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['fcr_rate', 'reopen_rate', 'anomalies'])
        issues = self.check_common_issues(result)
        flags = []
        
        metrics = ['fcr_rate', 'reopen_rate']
        for m in metrics:
            val = data.get(m)
            if val is not None and (val < 0 or val > 1):
                issues.append(f"Metric {m} out of bounds: {val}")
        
        anomalies = data.get('anomalies', [])
        for anomaly in anomalies:
            desc = anomaly.get('description', '')
            generic_flags = self.detector.detect_generic_language(desc)
            for flag in generic_flags:
                flags.append({'type': 'generic_anomaly', 'text': desc, 'detail': flag})

        completeness = 1.0 if all(checks.values()) else 0.5
        specificity = 1.0 - (len(flags) * 0.2)
        consistency = 1.0 if not issues else 0.6
        evidence = 1.0
        
        if not result.success:
            consistency = 0.0

        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=[]
        )

class ChurnRiskAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['churn_signals'])
        issues = self.check_common_issues(result)
        flags = []
        
        signals = data.get('churn_signals', {})
        high_risk = signals.get('high_risk_conversations', [])
        # Simple check: churn risk shouldn't be excessively high without reason
        # If input context available, could check against total conversations
        
        # Check rationale for generic reasons
        for conv in high_risk:
            reason = conv.get('reason', '')
            generic_flags = self.detector.detect_generic_language(reason)
            for flag in generic_flags:
                flags.append({'type': 'generic_churn_reason', 'text': reason, 'detail': flag})
        
        if input_context and 'valid_ids' in input_context:
            for conv in high_risk:
                conv_id = conv.get('conversation_id')
                if conv_id and str(conv_id) not in [str(v) for v in input_context['valid_ids']]:
                    flags.append({'type': 'fabricated_data', 'text': f"ID: {conv_id}", 'detail': f"Conversation ID {conv_id} not found in input"})

        hallucination_score = self.detector.calculate_hallucination_score(flags)

        completeness = 1.0 if all(checks.values()) else 0.5
        specificity = 1.0 - hallucination_score
        consistency = 1.0
        evidence = 1.0
        
        if not result.success:
            consistency = 0.0

        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=[]
        )

class ConfidenceMetaAuditor(BaseAgentAuditor):
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        data = result.data if isinstance(result.data, dict) else {}
        checks = self.validate_output_structure(data, ['overall_confidence', 'limitations'])
        issues = self.check_common_issues(result)
        flags = []
        
        conf = data.get('overall_confidence')
        if conf is not None and (conf < 0 or conf > 1):
            issues.append(f"Confidence score out of bounds: {conf}")
            
        limitations = data.get('limitations', [])
        if not limitations and conf and conf < 0.9:
            issues.append("Low confidence but no limitations listed")

        completeness = 1.0 if all(checks.values()) else 0.5
        consistency = 1.0 if not issues else 0.6
        specificity = 1.0
        evidence = 1.0
        
        if not result.success:
            consistency = 0.0

        quality_score = self.calculate_quality_score(specificity, evidence, consistency, completeness)
        
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=quality_score,
            passed=quality_score >= 0.6 and not issues,
            hallucination_flags=flags,
            validation_checks=checks,
            issues_found=issues,
            recommendations=[]
        )

class DefaultAuditor(BaseAgentAuditor):
    """Fallback auditor for agents without specific implementation."""
    def audit(self, result: AgentResult, input_context: Optional[Dict] = None) -> AgentAuditResult:
        checks = {'has_data': result.data is not None}
        # Comment 2: Mark as not passed / neutral
        return AgentAuditResult(
            agent_name=self.agent_name,
            quality_score=0.4, # Below 0.6 threshold
            passed=False,
            hallucination_flags=[],
            validation_checks=checks,
            issues_found=["No specific auditor implemented - Audit skipped"],
            recommendations=["Implement specific auditor for this agent"]
        )

class AuditOrchestrator:
    """Orchestrates the audit process for all agents."""
    
    def __init__(self):
        self.auditors = {
            'SegmentationAgent': SegmentationAuditor,
            'TopicDetectionAgent': TopicDetectionAuditor,
            'SubTopicDetectionAgent': SubTopicDetectionAuditor,
            'TopicSentimentAgent': TopicSentimentAuditor,
            'ExampleExtractionAgent': ExampleExtractionAuditor,
            'FinPerformanceAgent': FinPerformanceAuditor,
            'BpoPerformanceAgent': BpoPerformanceAuditor,
            'CorrelationAgent': CorrelationAuditor,
            'QualityInsightsAgent': QualityInsightsAuditor,
            'ChurnRiskAgent': ChurnRiskAuditor,
            'ConfidenceMetaAgent': ConfidenceMetaAuditor,
        }
        self.default_auditor = DefaultAuditor

    def audit_agent(self, agent_name: str, result: Union[AgentResult, Dict], context: Optional[Dict] = None) -> AgentAuditResult:
        """Run audit for a specific agent."""
        # Handle if result is dict (deserialized) or AgentResult object
        if isinstance(result, dict):
            try:
                # Comment 3: Detect status wrapper
                if 'status' in result and 'elapsed' in result and 'data' not in result:
                     # This looks like a status wrapper without data
                     pass

                # Construct minimal AgentResult
                res_obj = AgentResult(
                    agent_name=agent_name,
                    success=result.get('success', result.get('status') == 'success'),
                    data=result.get('data', result), # Fallback if data key missing
                    confidence=result.get('confidence', 0.0),
                    confidence_level=result.get('confidence_level', ConfidenceLevel.LOW)
                )
            except Exception:
                # If structure doesn't match, wrap data
                res_obj = AgentResult(
                    agent_name=agent_name,
                    success=True, 
                    data=result,
                    confidence=0.5,
                    confidence_level=ConfidenceLevel.LOW
                )
        else:
            res_obj = result
            
        # Comment 3: Runtime assertion for data type
        if not isinstance(res_obj.data, dict):
            # Log warning instead of crash, but mark as issue in DefaultAuditor if used
            # Or better, create a failed AuditResult
            logger.warning(f"Agent {agent_name} result data is not a dict: {type(res_obj.data)}")
            # Proceed, but validators will likely fail or handle it gracefully

        auditor_cls = self.auditors.get(agent_name, self.default_auditor)
        auditor = auditor_cls(agent_name)
        return auditor.audit(res_obj, context)

    def audit_all(self, agent_results: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, AgentAuditResult]:
        """
        Run audit on a dictionary of agent results.
        
        Args:
            agent_results: Dictionary mapping agent name to AgentResult object or dict.
                           MUST be full agent results (data included), not just status wrappers.
            context: Optional context with metadata (conversations, etc.)
        """
        results = {}
        for name, result in agent_results.items():
            # Comment 3: Check for wrapper dicts without data
            if isinstance(result, dict) and 'status' in result and 'data' not in result:
                # This is a status wrapper, skip or warn
                logger.warning(f"Skipping audit for {name}: Result appears to be a status wrapper without data.")
                results[name] = AgentAuditResult(
                    agent_name=name,
                    quality_score=0.0,
                    passed=False,
                    issues_found=["Skipped: Missing full result data for audit"],
                    validation_checks={}
                )
                continue

            results[name] = self.audit_agent(name, result, context)
        return results

    def generate_report(self, audit_results: Dict[str, AgentAuditResult]) -> str:
        """Generate a markdown report of the audit."""
        lines = [
            "# Agent Audit Report",
            f"\nGenerated: {datetime.now().isoformat() if 'datetime' in globals() else ''}",
            "\n## Scorecard\n",
            "| Agent | Score | Pass/Fail | Issues |",
            "|-------|-------|-----------|--------|"
        ]
        
        total_score = 0
        count = 0
        passed_count = 0
        
        for name, res in audit_results.items():
            status = "✅ PASS" if res.passed else "❌ FAIL"
            # Comment 2: Handle Not Audited explicitly
            if "No specific auditor implemented" in (res.issues_found[0] if res.issues_found else ""):
                status = "⚠️  N/A"
                
            issues = ", ".join(res.issues_found[:2]) if res.issues_found else "None"
            lines.append(f"| {name} | {res.quality_score} | {status} | {issues} |")
            
            # Only count actual audits in average? Or penalize?
            # Use all for average
            total_score += res.quality_score
            count += 1
            if res.passed:
                passed_count += 1
            
        avg = total_score / count if count > 0 else 0
        lines.append(f"\n**Overall Quality Score**: {avg:.2f}")
        lines.append(f"**Pass Rate**: {passed_count}/{count} ({passed_count/count*100:.1f}%)" if count > 0 else "")
        
        lines.append("\n## Detailed Findings\n")
        for name, res in audit_results.items():
            lines.append(f"### {name}")
            status_icon = '✅ PASS' if res.passed else '❌ FAIL'
            if "No specific auditor" in (res.issues_found[0] if res.issues_found else ""):
                 status_icon = "⚠️  NOT AUDITED"
                 
            lines.append(f"- **Score**: {res.quality_score}")
            lines.append(f"- **Status**: {status_icon}")
            
            if res.hallucination_flags:
                lines.append("- **Hallucination Flags**:")
                for flag in res.hallucination_flags:
                    lines.append(f"  - {flag.get('type', 'Unknown')}: {flag.get('detail', '')} in '{flag.get('text', '')[:50]}...'")
            
            if res.issues_found:
                lines.append("- **Issues**:")
                for issue in res.issues_found:
                    lines.append(f"  - {issue}")
            
            if res.recommendations:
                lines.append("- **Recommendations**:")
                for rec in res.recommendations:
                    lines.append(f"  - {rec}")
            lines.append("")
            
        return "\n".join(lines)

    def export_json(self, audit_results: Dict[str, AgentAuditResult]) -> str:
        """Export results as JSON string."""
        data = {k: v.dict() for k, v in audit_results.items()}
        return json.dumps(data, indent=2, default=str)
