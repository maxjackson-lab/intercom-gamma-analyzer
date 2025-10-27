"""
Troubleshooting Analyzer

Analyzes agent troubleshooting behavior using AI to detect:
- How many diagnostic questions were asked
- Whether agent showed effort before escalating
- Premature escalations (escalated without trying)
- Consistency of troubleshooting approach

This is critical for coaching agents on proper support methodology.
"""

import logging
from typing import Dict, List, Optional, Any
import json

from src.utils.ai_client_helper import get_ai_client

logger = logging.getLogger(__name__)


class TroubleshootingAnalyzer:
    """Analyzes agent troubleshooting behavior and effort"""
    
    # Known policies (can be expanded)
    KNOWN_POLICIES = {
        'refund_window_days': 7,  # 7-day refund policy
        'requires_escalation': [
            'enterprise',
            'api authentication',
            'security issue',
            'account compromise',
            'billing dispute over $500'
        ]
    }
    
    def __init__(self, audit=None):
        self.ai_client = get_ai_client()
        self.logger = logging.getLogger(__name__)
        self.audit = audit
    
    async def analyze_conversation_troubleshooting(
        self, 
        conversation: Dict
    ) -> Dict[str, Any]:
        """
        Analyze troubleshooting effort in a single conversation.
        
        Returns:
            {
                'diagnostic_questions_count': int,
                'showed_effort': bool,
                'asked_for_details': bool,  # screenshots, error messages, etc.
                'tried_alternatives': bool,
                'showed_empathy': bool,
                'troubleshooting_score': float (0-1),
                'premature_escalation': bool,
                'controllable': bool,
                'issue_type': str,
                'reasoning': str
            }
        """
        try:
            full_text = conversation.get('full_text', '')
            customer_messages = conversation.get('customer_messages', [])
            admin_messages = conversation.get('admin_messages', [])
            
            # Skip if not enough data
            if not full_text or len(admin_messages) == 0:
                return self._default_analysis()
            
            # Check if escalated
            escalated = any(name in full_text.lower() for name in [
                'dae-ho', 'max jackson', 'hilary'
            ])
            
            # Get category/topic
            category = conversation.get('primary_category', 'Unknown')
            subcategory = conversation.get('subcategory', '')
            
            # Build AI analysis prompt
            prompt = self._build_analysis_prompt(
                full_text, 
                customer_messages,
                admin_messages,
                escalated,
                category,
                subcategory
            )
            
            # Get AI analysis
            response = await self.ai_client.complete(
                prompt=prompt,
                model="gpt-4o-mini",  # Fast and cheap for this task
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            analysis = json.loads(response)
            
            # Add metadata
            analysis['conversation_id'] = conversation.get('id')
            analysis['escalated'] = escalated
            analysis['category'] = f"{category}>{subcategory}" if subcategory else category
            
            # Log to audit if available
            if self.audit:
                self.audit.step("Troubleshooting Analysis", "analysis",
                              f"Analyzed conversation {conversation.get('id')}",
                              {
                                  'conversation_id': conversation.get('id'),
                                  'troubleshooting_score': analysis.get('troubleshooting_score', 0),
                                  'diagnostic_questions': analysis.get('diagnostic_questions_count', 0),
                                  'premature_escalation': analysis.get('premature_escalation', False),
                                  'issue_type': analysis.get('issue_type', 'unknown')
                              })
            
            self.logger.debug(
                f"Analyzed conversation {conversation.get('id')}: "
                f"Score {analysis.get('troubleshooting_score', 0):.2f}, "
                f"Questions: {analysis.get('diagnostic_questions_count', 0)}"
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze troubleshooting: {e}")
            return self._default_analysis()
    
    def _build_analysis_prompt(
        self,
        full_text: str,
        customer_messages: List[str],
        admin_messages: List[str],
        escalated: bool,
        category: str,
        subcategory: str
    ) -> str:
        """Build AI prompt for troubleshooting analysis"""
        
        # Truncate if too long (keep first and last messages)
        if len(full_text) > 4000:
            first_half = full_text[:1500]
            last_half = full_text[-1500:]
            full_text = f"{first_half}\n\n[... conversation truncated ...]\n\n{last_half}"
        
        return f"""
Analyze this support conversation to evaluate the agent's troubleshooting effort.

CONVERSATION:
{full_text}

CONTEXT:
- Category: {category} > {subcategory}
- Escalated to senior staff: {escalated}
- Known 7-day refund policy

ANALYZE AGENT BEHAVIOR:

1. DIAGNOSTIC QUESTIONS (Count how many):
   - Did agent ask what error messages appeared?
   - Did agent ask for screenshots/screen recordings?
   - Did agent ask what browser/device/OS?
   - Did agent ask when the issue started?
   - Did agent ask what steps customer tried?
   - Did agent ask to reproduce the issue?
   
2. TROUBLESHOOTING EFFORT:
   - Did agent try multiple solutions?
   - Did agent offer alternatives?
   - Did agent explain what to try next?
   - Or did agent immediately say "I'll escalate this"?
   
3. DETAILS REQUESTED:
   - Did agent ask for error messages, screenshots, or logs?
   
4. EMPATHY & TONE:
   - Did agent acknowledge customer frustration?
   - Was response personalized or copy-paste?
   - Did agent show they cared about solving it?
   
5. CONTROLLABLE ASSESSMENT:
   CONTROLLABLE (agent's fault) if:
   - Escalated without asking diagnostic questions
   - Didn't try any troubleshooting steps
   - Rude/dismissive tone
   - Gave wrong information
   - Customer had to reopen (incomplete resolution)
   
   UNCONTROLLABLE (product/policy) if:
   - Legitimate product bug (export fails, editor broken)
   - Missing feature customer needs
   - Policy limitation (refund beyond 7 days)
   - Enterprise/API question requiring escalation
   - Security issue requiring escalation

6. PREMATURE ESCALATION:
   - If escalated AND asked <2 diagnostic questions = PREMATURE
   - If escalated AND didn't try any solutions = PREMATURE
   - Exception: If issue requires escalation (enterprise, security, API)

Return JSON with this EXACT structure:
{{
    "diagnostic_questions_count": <0-10>,
    "showed_effort": <true/false>,
    "asked_for_details": <true/false>,
    "tried_alternatives": <true/false>,
    "showed_empathy": <true/false>,
    "troubleshooting_score": <0.0-1.0>,
    "premature_escalation": <true/false>,
    "controllable": <true/false>,
    "issue_type": "<premature_escalation|insufficient_troubleshooting|product_bug|policy_limitation|legitimate_escalation>",
    "reasoning": "<Brief explanation of your assessment>"
}}
"""
    
    def _default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when unable to analyze"""
        return {
            'diagnostic_questions_count': 0,
            'showed_effort': False,
            'asked_for_details': False,
            'tried_alternatives': False,
            'showed_empathy': False,
            'troubleshooting_score': 0.0,
            'premature_escalation': False,
            'controllable': False,
            'issue_type': 'unknown',
            'reasoning': 'Unable to analyze conversation'
        }
    
    async def analyze_agent_troubleshooting_pattern(
        self,
        conversations: List[Dict],
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Analyze overall troubleshooting pattern for an agent across conversations.
        
        Returns aggregate metrics:
        - Average troubleshooting score
        - % conversations with adequate troubleshooting
        - Premature escalation rate
        - Consistency score (variance in effort)
        """
        try:
            if self.audit:
                self.audit.step("Troubleshooting Pattern Analysis", "analysis",
                              f"Starting troubleshooting pattern analysis for agent: {agent_name}",
                              {
                                  'agent_name': agent_name,
                                  'total_conversations': len(conversations)
                              })
            
            analyses = []
            
            # Analyze each conversation (focus on escalated and low-CSAT ones)
            priority_convs = [
                c for c in conversations
                if self._is_priority_for_analysis(c)
            ]
            
            if self.audit:
                self.audit.step("Troubleshooting Pattern Analysis", "analysis",
                              f"Identified {len(priority_convs)} priority conversations for analysis",
                              {
                                  'priority_conversations': len(priority_convs),
                                  'analysis_limit': 10,
                                  'selection_criteria': ['escalated', 'low_csat', 'reopened']
                              })
            
            # Limit to 10 conversations for performance
            for conv in priority_convs[:10]:
                analysis = await self.analyze_conversation_troubleshooting(conv)
                analyses.append(analysis)
            
            if not analyses:
                return self._default_pattern_analysis(agent_name)
            
            # Calculate aggregate metrics
            avg_score = sum(a['troubleshooting_score'] for a in analyses) / len(analyses)
            avg_questions = sum(a['diagnostic_questions_count'] for a in analyses) / len(analyses)
            premature_escalations = sum(1 for a in analyses if a['premature_escalation'])
            premature_rate = premature_escalations / len(analyses)
            
            adequate_count = sum(1 for a in analyses if a['troubleshooting_score'] >= 0.6)
            adequate_rate = adequate_count / len(analyses)
            
            # Calculate consistency (lower variance = more consistent)
            scores = [a['troubleshooting_score'] for a in analyses]
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            consistency_score = 1.0 - min(variance * 2, 1.0)  # Normalize to 0-1
            
            # Identify patterns
            issues = []
            if premature_rate > 0.3:
                issues.append("High premature escalation rate")
            if avg_questions < 2:
                issues.append("Insufficient diagnostic questions")
            if avg_score < 0.5:
                issues.append("Low overall troubleshooting effort")
            if consistency_score < 0.6:
                issues.append("Inconsistent troubleshooting approach")
            
            # Strengths
            strengths = []
            if avg_score >= 0.7:
                strengths.append("Strong troubleshooting effort")
            if consistency_score >= 0.7:
                strengths.append("Consistent approach")
            if premature_rate < 0.2:
                strengths.append("Appropriate escalation judgment")
            
            result = {
                'agent_name': agent_name,
                'conversations_analyzed': len(analyses),
                'avg_troubleshooting_score': round(avg_score, 2),
                'avg_diagnostic_questions': round(avg_questions, 1),
                'premature_escalation_rate': round(premature_rate, 2),
                'adequate_troubleshooting_rate': round(adequate_rate, 2),
                'consistency_score': round(consistency_score, 2),
                'issues_identified': issues,
                'strengths': strengths,
                'detailed_analyses': analyses  # For examples
            }
            
            # Log aggregate findings to audit
            if self.audit:
                self.audit.step("Troubleshooting Pattern Analysis", "analysis",
                              f"Completed pattern analysis for {agent_name}",
                              {
                                  'agent_name': agent_name,
                                  'conversations_analyzed': len(analyses),
                                  'avg_score': f"{avg_score:.2f}",
                                  'avg_questions': f"{avg_questions:.1f}",
                                  'premature_escalation_rate': f"{premature_rate:.1%}",
                                  'consistency_score': f"{consistency_score:.2f}",
                                  'issues_count': len(issues),
                                  'strengths_count': len(strengths)
                              })
                
                # Record data quality check
                if len(analyses) < 3:
                    self.audit.data_quality_check(
                        "Troubleshooting Analysis Sample Size",
                        f"Only {len(analyses)} priority conversations analyzed for {agent_name}",
                        "limited"
                    )
                
                # Record pattern detection decisions
                if issues:
                    self.audit.decision(
                        f"What troubleshooting issues were detected for {agent_name}?",
                        f"{len(issues)} patterns identified: {', '.join(issues[:3])}",
                        f"Based on analysis of {len(analyses)} conversations with avg score {avg_score:.2f}",
                        {'all_issues': issues}
                    )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze agent pattern: {e}")
            return self._default_pattern_analysis(agent_name)
    
    def _is_priority_for_analysis(self, conv: Dict) -> bool:
        """Determine if conversation should be analyzed (focus on escalated/low-CSAT)"""
        # Prioritize escalated conversations
        if any(name in str(conv.get('full_text', '')).lower() 
               for name in ['dae-ho', 'max jackson', 'hilary']):
            return True
        
        # Prioritize low CSAT
        rating = conv.get('conversation_rating')
        if rating and rating <= 2:
            return True
        
        # Prioritize reopened
        if conv.get('count_reopens', 0) > 0:
            return True
        
        return False
    
    def _default_pattern_analysis(self, agent_name: str) -> Dict[str, Any]:
        """Return default pattern analysis"""
        return {
            'agent_name': agent_name,
            'conversations_analyzed': 0,
            'avg_troubleshooting_score': 0.0,
            'avg_diagnostic_questions': 0.0,
            'premature_escalation_rate': 0.0,
            'adequate_troubleshooting_rate': 0.0,
            'consistency_score': 0.0,
            'issues_identified': [],
            'strengths': [],
            'detailed_analyses': []
        }

