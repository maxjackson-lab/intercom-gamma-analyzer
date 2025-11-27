"""
Analysis Validator

Validates analysis workflow integrity before output generation.
Prevents data loss by ensuring all required analysis components have successfully run.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AnalysisValidator:
    """
    Validates the integrity of Voice of Customer analysis results.
    """
    
    @staticmethod
    def validate_voc_analysis(
        workflow_results: Dict[str, Any],
        conversations_count: int,
        free_tier_conversations_count: int = 0,
        raise_on_critical: bool = False
    ) -> List[str]:
        """
        Validate VoC analysis workflow results for data integrity.
        
        Checks for:
        1. Topic Detection success and data presence
        2. Sentiment and Example coverage for high-volume topics (Data Loss prevention)
        3. Fin AI agent execution (dependent on free-tier volume)
        
        Args:
            workflow_results: Dictionary of agent results from the orchestrator
            conversations_count: Total number of conversations analyzed
            free_tier_conversations_count: Number of free tier conversations (triggers Fin validation)
            raise_on_critical: Whether to raise ValueError on critical failures
            
        Returns:
            List of warning messages. Prefix indicates severity:
            - "CRITICAL:": Blocking data loss issues
            - "DATA LOSS:": Missing data for specific topics
            - "QUALITY:": Quality issues (missing insights)
            - "WARNING:": Non-critical issues
            
        Raises:
            ValueError: If raise_on_critical is True and critical errors are found
        """
        warnings = []
        critical_errors = []
        HIGH_VOLUME_THRESHOLD = 5
        
        # 1. Topic Detection Integrity
        topic_agent = workflow_results.get('TopicDetectionAgent', {})
        if not topic_agent or not topic_agent.get('success', False):
            msg = "CRITICAL: TopicDetectionAgent failed or missing"
            critical_errors.append(msg)
            warnings.append(msg)
            # Cannot proceed with topic validation if detection failed
            if raise_on_critical:
                raise ValueError(msg)
            return warnings
            
        topic_data = topic_agent.get('data', {})
        topic_distribution = topic_data.get('topic_distribution', {})
        
        if not topic_distribution and conversations_count > 0:
            # It's possible no topics were found, but suspicious if we have conversations
            msg = f"WARNING: No topics detected in {conversations_count} conversations"
            warnings.append(msg)
            
        # 2. Sentiment & Insight Coverage (Anti-Data Loss)
        # Defensive check for results structure (Comment 3)
        topic_sentiments = workflow_results.get('TopicSentiments')
        topic_examples = workflow_results.get('TopicExamples')
        
        if not isinstance(topic_sentiments, dict):
            msg = "CRITICAL: TopicSentiments is not a dictionary"
            warnings.append(msg)
            critical_errors.append(msg)
            topic_sentiments = {} # safe fallback for iteration
            
        if not isinstance(topic_examples, dict):
            msg = "CRITICAL: TopicExamples is not a dictionary"
            warnings.append(msg)
            critical_errors.append(msg)
            topic_examples = {} # safe fallback for iteration
        
        for topic, stats in topic_distribution.items():
            # Handle both dict {'volume': N} and int format
            volume = stats.get('volume', 0) if isinstance(stats, dict) else stats
            
            # Skip topics below high volume threshold for critical checks (Comment 4)
            if volume < HIGH_VOLUME_THRESHOLD:
                # Optional: log a lower severity warning if missing coverage?
                # For now, we just skip critical checks for low volume topics
                continue
                
            # Check Sentiment Presence (Comment 3 defensive checks)
            if not isinstance(topic_sentiments.get(topic), dict):
                msg = f"DATA LOSS: Topic '{topic}' (vol={volume}) missing sentiment analysis"
                warnings.append(msg)
                critical_errors.append(msg)
            else:
                # Check Sentiment Quality
                sent_data = topic_sentiments[topic].get('data', {})
                insight = sent_data.get('sentiment_insight') or sent_data.get('sentiment_summary')
                if not insight:
                    msg = f"QUALITY: Topic '{topic}' missing verbatim 'sentiment_insight'"
                    warnings.append(msg)
                    
            # Check Examples Presence (Comment 3 defensive checks)
            if not isinstance(topic_examples.get(topic), dict):
                msg = f"DATA LOSS: Topic '{topic}' missing examples"
                warnings.append(msg)
                critical_errors.append(msg)
                
        # 3. Fin AI Agent Validation (Comment 1)
        fin_agent = workflow_results.get('FinPerformanceAgent')
        
        if free_tier_conversations_count > 0:
            if not fin_agent:
                msg = "CRITICAL: FinPerformanceAgent missing despite having free-tier conversations"
                warnings.append(msg)
                critical_errors.append(msg)
            elif not fin_agent.get('success', False):
                msg = f"CRITICAL: FinPerformanceAgent failed: {fin_agent.get('error_message')}"
                warnings.append(msg)
                critical_errors.append(msg)
        else:
            # If no free tier conversations, Fin agent is optional/not expected
            if not fin_agent:
                # Skip validation or log low severity
                pass 
            elif not fin_agent.get('success', False):
                msg = f"WARNING: FinPerformanceAgent failed (but no free tier conversations expected): {fin_agent.get('error_message')}"
                warnings.append(msg)
            
        # Handle Critical Errors
        if raise_on_critical and critical_errors:
            error_msg = f"Validation failed with {len(critical_errors)} critical errors: {'; '.join(critical_errors[:3])}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
            
        return warnings

