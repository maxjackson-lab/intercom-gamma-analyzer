"""
AgentPerformanceAgent: Analyzes performance of specific agents or BPO teams.

Purpose:
- Track FCR, resolution time, escalation rate by agent
- Identify strengths and development opportunities
- Generate actionable feedback and process recommendations
- Support any time period for trend analysis
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import numpy as np

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.utils.ai_client_helper import get_ai_client

logger = logging.getLogger(__name__)


class AgentPerformanceAgent(BaseAgent):
    """Agent specialized in analyzing support agent/team performance"""
    
    # Agent/BPO email domain patterns
    AGENT_PATTERNS = {
        'horatio': {
            'domains': ['hirehoratio.co', '@horatio.com'],
            'patterns': [r'horatio', r'@hirehoratio\.co', r'@horatio\.com'],
            'name': 'Horatio'
        },
        'boldr': {
            'domains': ['boldrimpact.com', '@boldr'],
            'patterns': [r'boldr', r'@boldrimpact\.com', r'@boldr'],
            'name': 'Boldr'
        },
        'escalated': {
            'patterns': [r'dae-ho', r'max jackson', r'max\.jackson', r'hilary'],
            'name': 'Senior Staff'
        }
    }
    
    def __init__(self, agent_filter: str = 'horatio'):
        super().__init__(
            name=f"AgentPerformanceAgent_{agent_filter}",
            model="gpt-4o",
            temperature=0.3
        )
        self.agent_filter = agent_filter.lower()
        self.ai_client = get_ai_client()
    
    def get_agent_specific_instructions(self) -> str:
        """Agent performance analysis instructions"""
        agent_name = self.AGENT_PATTERNS.get(self.agent_filter, {}).get('name', self.agent_filter)
        
        return f"""
AGENT PERFORMANCE ANALYSIS - {agent_name.upper()}

1. Analyze performance objectively with data-driven insights:
   - First Contact Resolution rate
   - Resolution time (median, P90)
   - Escalation patterns
   - Category-specific performance

2. Identify specific strengths and development areas:
   - What topics does this agent handle well?
   - What topics require escalation most often?
   - Where are the knowledge gaps?

3. Generate actionable recommendations:
   - Process improvements
   - Training opportunities
   - Documentation needs
   - Workload optimization

4. Professional executive tone:
   - Data-driven, not judgmental
   - Specific examples with Intercom links
   - Comparative benchmarks where applicable
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe performance analysis task"""
        agent_name = self.AGENT_PATTERNS.get(self.agent_filter, {}).get('name', self.agent_filter)
        return f"""
Analyze performance of {agent_name} agents across {len(context.conversations)} conversations.

Focus areas:
1. Resolution efficiency (FCR, time to resolution)
2. Escalation patterns (what gets escalated and why)
3. Category performance (which topics handled well vs struggle)
4. Time period trends (if historical data available)
5. Actionable improvement recommendations
"""
    
    def format_context_data(self, context: AgentContext) -> str:
        """Format context for analysis"""
        return f"Conversations: {len(context.conversations)}"
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input"""
        if not context.conversations:
            raise ValueError("No conversations to analyze")
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """Validate performance results"""
        required = ['fcr_rate', 'median_resolution_hours', 'escalation_rate', 'performance_by_category']
        return all(k in result for k in required)
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute agent performance analysis"""
        start_time = datetime.now()
        
        try:
            self.validate_input(context)
            
            conversations = context.conversations
            agent_name = self.AGENT_PATTERNS.get(self.agent_filter, {}).get('name', self.agent_filter)
            
            self.logger.info(f"AgentPerformanceAgent: Analyzing {agent_name} performance ({len(conversations)} conversations)")
            
            # Calculate operational metrics
            metrics = self._calculate_performance_metrics(conversations)
            
            # Analyze by category
            category_performance = self._analyze_category_performance(conversations)
            
            # Extract example conversations
            examples = self._extract_performance_examples(conversations, metrics, category_performance)
            
            # Generate LLM insights
            self.logger.info("Generating performance insights with LLM...")
            llm_insights = await self._generate_performance_insights(
                agent_name, metrics, category_performance, examples
            )
            
            # Prepare result
            result_data = {
                'agent_name': agent_name,
                'agent_filter': self.agent_filter,
                'fcr_rate': metrics['fcr_rate'],
                'median_resolution_hours': metrics['median_resolution_hours'],
                'escalation_rate': metrics['escalation_rate'],
                'total_conversations': len(conversations),
                'performance_by_category': category_performance,
                'operational_metrics': metrics,
                'examples': examples,
                'llm_insights': llm_insights,
                'time_period': {
                    'start': context.start_date.isoformat(),
                    'end': context.end_date.isoformat()
                }
            }
            
            self.validate_output(result_data)
            
            confidence = min(1.0, len(conversations) / 100)
            confidence_level = (ConfidenceLevel.HIGH if len(conversations) >= 100
                              else ConfidenceLevel.MEDIUM if len(conversations) >= 30
                              else ConfidenceLevel.LOW)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"AgentPerformanceAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   {agent_name} FCR: {metrics['fcr_rate']:.1%}")
            self.logger.info(f"   Escalation rate: {metrics['escalation_rate']:.1%}")
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Based on {len(conversations)} conversations"] if len(conversations) < 100 else [],
                sources=[f"{agent_name} conversations", "Operational metrics", "LLM analysis"],
                execution_time=execution_time,
                token_count=0  # Will be updated after LLM call
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"AgentPerformanceAgent error: {e}")
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _calculate_performance_metrics(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate operational performance metrics"""
        
        # FCR (First Contact Resolution)
        closed_convs = [c for c in conversations if c.get('state') == 'closed']
        fcr_convs = [c for c in closed_convs if c.get('count_reopens', 0) == 0]
        fcr_rate = len(fcr_convs) / len(closed_convs) if closed_convs else 0
        
        # Resolution time
        resolution_times = []
        for conv in closed_convs:
            created = conv.get('created_at')
            updated = conv.get('updated_at')
            if created and updated:
                if isinstance(created, (int, float)):
                    created_dt = datetime.fromtimestamp(created)
                    updated_dt = datetime.fromtimestamp(updated)
                else:
                    created_dt = created
                    updated_dt = updated
                hours = (updated_dt - created_dt).total_seconds() / 3600
                resolution_times.append(hours)
        
        # Escalations (to senior staff)
        escalated = [
            c for c in conversations
            if any(name in str(c.get('full_text', '')).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary'])
        ]
        escalation_rate = len(escalated) / len(conversations) if conversations else 0
        
        # Response time
        response_times = [
            c.get('time_to_admin_reply', 0) / 3600 for c in conversations
            if c.get('time_to_admin_reply')
        ]
        
        # Complexity
        avg_parts = np.mean([c.get('count_conversation_parts', 0) for c in conversations]) if conversations else 0
        
        return {
            'fcr_rate': fcr_rate,
            'fcr_count': len(fcr_convs),
            'total_closed': len(closed_convs),
            'median_resolution_hours': np.median(resolution_times) if resolution_times else 0,
            'p90_resolution_hours': np.percentile(resolution_times, 90) if resolution_times else 0,
            'escalation_rate': escalation_rate,
            'escalated_count': len(escalated),
            'median_response_hours': np.median(response_times) if response_times else 0,
            'avg_conversation_complexity': avg_parts,
            'resolution_time_distribution': {
                'under_4h': sum(1 for t in resolution_times if t < 4) / len(resolution_times) * 100 if resolution_times else 0,
                'under_24h': sum(1 for t in resolution_times if t < 24) / len(resolution_times) * 100 if resolution_times else 0,
                'over_48h': sum(1 for t in resolution_times if t > 48) / len(resolution_times) * 100 if resolution_times else 0
            }
        }
    
    def _analyze_category_performance(self, conversations: List[Dict]) -> Dict[str, Dict]:
        """Analyze performance by category (Tech, API, Bug, etc.)"""
        from collections import defaultdict
        
        category_metrics = defaultdict(lambda: {
            'total': 0,
            'fcr_count': 0,
            'escalated_count': 0,
            'resolution_times': []
        })
        
        for conv in conversations:
            # Get category from tags or custom attributes
            tags = [t.get('name', t) if isinstance(t, dict) else t 
                   for t in conv.get('tags', {}).get('tags', [])]
            
            # Determine category
            category = 'Other'
            for tag in tags:
                tag_lower = str(tag).lower()
                if 'bug' in tag_lower or 'technical' in tag_lower:
                    category = 'Technical Troubleshooting'
                    break
                elif 'api' in tag_lower:
                    category = 'API Issues'
                    break
                elif 'billing' in tag_lower:
                    category = 'Billing'
                    break
            
            # Calculate metrics for this category
            category_metrics[category]['total'] += 1
            
            if conv.get('state') == 'closed' and conv.get('count_reopens', 0) == 0:
                category_metrics[category]['fcr_count'] += 1
            
            if any(name in str(conv.get('full_text', '')).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary']):
                category_metrics[category]['escalated_count'] += 1
            
            # Resolution time
            if conv.get('state') == 'closed':
                created = conv.get('created_at')
                updated = conv.get('updated_at')
                if created and updated:
                    if isinstance(created, (int, float)):
                        hours = (updated - created) / 3600
                    else:
                        hours = (updated - created).total_seconds() / 3600
                    category_metrics[category]['resolution_times'].append(hours)
        
        # Calculate rates
        performance_by_category = {}
        for category, stats in category_metrics.items():
            if stats['total'] >= 5:  # Only include categories with meaningful sample
                fcr_rate = stats['fcr_count'] / stats['total'] if stats['total'] > 0 else 0
                escalation_rate = stats['escalated_count'] / stats['total'] if stats['total'] > 0 else 0
                median_resolution = np.median(stats['resolution_times']) if stats['resolution_times'] else 0
                
                performance_by_category[category] = {
                    'volume': stats['total'],
                    'fcr_rate': fcr_rate,
                    'escalation_rate': escalation_rate,
                    'median_resolution_hours': median_resolution
                }
        
        return performance_by_category
    
    def _extract_performance_examples(self, conversations: List[Dict], metrics: Dict, category_perf: Dict) -> Dict[str, List[Dict]]:
        """Extract example conversations showing strengths and development areas"""
        from src.config.settings import settings
        
        examples = {
            'high_fcr_examples': [],
            'escalation_examples': [],
            'long_resolution_examples': []
        }
        
        # Find examples of successful FCR
        fcr_convs = [
            c for c in conversations 
            if c.get('state') == 'closed' and c.get('count_reopens', 0) == 0
        ]
        if fcr_convs:
            examples['high_fcr_examples'] = [
                {
                    'id': c.get('id'),
                    'category': self._get_category(c),
                    'resolution_hours': self._get_resolution_hours(c),
                    'intercom_url': self._build_intercom_url(c.get('id'))
                }
                for c in fcr_convs[:3]
            ]
        
        # Find examples of escalations
        escalated = [
            c for c in conversations
            if any(name in str(c.get('full_text', '')).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary'])
        ]
        if escalated:
            examples['escalation_examples'] = [
                {
                    'id': c.get('id'),
                    'category': self._get_category(c),
                    'why_escalated': 'Complex issue requiring senior expertise',
                    'intercom_url': self._build_intercom_url(c.get('id'))
                }
                for c in escalated[:3]
            ]
        
        return examples
    
    def _build_intercom_url(self, conversation_id: str) -> str:
        """Build Intercom conversation URL with workspace ID"""
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"
    
    def _get_category(self, conv: Dict) -> str:
        """Get category for a conversation"""
        tags = [t.get('name', t) if isinstance(t, dict) else t 
               for t in conv.get('tags', {}).get('tags', [])]
        
        for tag in tags:
            tag_lower = str(tag).lower()
            if 'bug' in tag_lower or 'technical' in tag_lower:
                return 'Technical Troubleshooting'
            elif 'api' in tag_lower:
                return 'API Issues'
            elif 'billing' in tag_lower:
                return 'Billing'
        
        return 'Other'
    
    def _get_resolution_hours(self, conv: Dict) -> float:
        """Calculate resolution time in hours"""
        created = conv.get('created_at')
        updated = conv.get('updated_at')
        
        if not (created and updated):
            return 0
        
        if isinstance(created, (int, float)):
            return (updated - created) / 3600
        else:
            return (updated - created).total_seconds() / 3600
    
    async def _generate_performance_insights(
        self, 
        agent_name: str, 
        metrics: Dict, 
        category_performance: Dict,
        examples: Dict
    ) -> str:
        """Generate LLM insights about agent performance"""
        
        # Format category performance for prompt
        cat_perf_text = "\n".join([
            f"- {cat}: {stats['volume']} tickets, {stats['fcr_rate']:.1%} FCR, {stats['escalation_rate']:.1%} escalation rate, {stats['median_resolution_hours']:.1f}h median resolution"
            for cat, stats in sorted(category_performance.items(), key=lambda x: x[1]['volume'], reverse=True)
        ])
        
        prompt = f"""
Analyze {agent_name}'s support performance and provide actionable feedback.

Overall Metrics:
- First Contact Resolution: {metrics['fcr_rate']:.1%}
- Median resolution time: {metrics['median_resolution_hours']:.1f} hours
- Escalation rate: {metrics['escalation_rate']:.1%}
- Total conversations: {metrics.get('total_closed', 0)}

Performance by Category:
{cat_perf_text}

Instructions:
1. Identify 2-3 specific strengths (what {agent_name} does well)
2. Identify 2-3 development opportunities (where improvement is needed)
3. Suggest 3 specific, actionable process improvements or training needs
4. Keep it professional, data-driven, and constructive
5. Focus on patterns, not individual performance criticism
6. Executive tone suitable for performance review

Structure as:
**Strengths:**
- [Specific strength with metric]

**Development Opportunities:**
- [Specific area with metric]

**Recommended Actions:**
1. [Specific process improvement]
2. [Specific training need]
3. [Specific documentation update]

Analysis:"""
        
        try:
            insights = await self.ai_client.generate_analysis(prompt)
            return insights.strip()
        except Exception as e:
            self.logger.warning(f"LLM insights generation failed: {e}")
            return f"{agent_name} FCR: {metrics['fcr_rate']:.1%}, Escalation rate: {metrics['escalation_rate']:.1%}"

