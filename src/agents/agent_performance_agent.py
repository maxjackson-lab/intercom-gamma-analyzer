"""
AgentPerformanceAgent: Analyzes performance of specific agents or BPO teams.

Purpose:
- Track FCR, resolution time, escalation rate by agent
- Identify strengths and development opportunities
- Generate actionable feedback and process recommendations
- Support any time period for trend analysis
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext, ConfidenceLevel
from src.agents.tools import ToolRegistry, AdminProfileLookupTool, QueryConversationsTool, CalculateFCRTool, CalculateCSATTool
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
        # Setup tools before calling parent constructor
        tool_registry = self._setup_tools()

        super().__init__(
            name=f"AgentPerformanceAgent_{agent_filter}",
            model="gpt-4o",
            temperature=0.3,
            tool_registry=tool_registry
        )
        self.agent_filter = agent_filter.lower()
        self.ai_client = get_ai_client()

        # Log tool setup after initialization
        if self.tool_registry:
            self.logger.info(f"Registered {len(self.tool_registry.tools)} tools for {self.name}")
        else:
            self.logger.warning(f"No tools registered for {self.name}")

    def _setup_tools(self) -> ToolRegistry:
        """Initialize and register all tools needed for agent performance analysis"""
        try:
            registry = ToolRegistry(enable_caching=True)

            # Register all available tools
            registry.register(AdminProfileLookupTool())
            registry.register(QueryConversationsTool())
            registry.register(CalculateFCRTool())
            registry.register(CalculateCSATTool())

            return registry
        except Exception as e:
            logger.warning(f"Failed to setup tools: {e}")
            return None

    def get_agent_specific_instructions(self) -> str:
        """Agent performance analysis instructions"""
        agent_name = self.AGENT_PATTERNS.get(self.agent_filter, {}).get('name', self.agent_filter)
        
        return f"""
AGENT PERFORMANCE ANALYSIS - {agent_name.upper()}

1. Analyze performance objectively with data-driven insights:
   - First Contact Resolution (FCR) rate
   - Customer Satisfaction (CSAT) scores and trends
   - Resolution time (median, P90)
   - Escalation patterns
   - Category-specific performance

2. Identify specific strengths and development areas:
   - What topics does this agent handle well?
   - Are low CSAT scores tied to specific categories or behaviors?
   - What topics require escalation most often?
   - Where are the knowledge gaps?
   - Is there a correlation between FCR and CSAT?

3. Generate actionable recommendations:
   - Process improvements
   - Training opportunities (especially for low-CSAT categories)
   - Documentation needs
   - Workload optimization

4. Professional executive tone:
   - Data-driven, not judgmental
   - Specific examples with Intercom links
   - Comparative benchmarks where applicable
   - Balance CSAT scores with operational context
"""
    
    def get_task_description(self, context: AgentContext) -> str:
        """Describe performance analysis task"""
        agent_name = self.AGENT_PATTERNS.get(self.agent_filter, {}).get('name', self.agent_filter)
        return f"""
Analyze performance of {agent_name} agents across {len(context.conversations)} conversations.

Focus areas:
1. Customer Satisfaction (CSAT scores, negative ratings, trends)
2. Resolution efficiency (FCR, time to resolution)
3. Escalation patterns (what gets escalated and why)
4. Category performance (which topics handled well vs struggle)
5. CSAT correlation (are low CSAT scores tied to specific categories?)
6. Time period trends (if historical data available)
7. Actionable improvement recommendations
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
    
    async def execute(self, context: AgentContext, individual_breakdown: bool = False,
                      analyze_troubleshooting: bool = False, use_ai_tools: bool = False) -> AgentResult:
        """
        Execute agent performance analysis with optional individual breakdown.

        Args:
            context: AgentContext with conversations and metadata
            individual_breakdown: If True, analyze each agent individually
            analyze_troubleshooting: If True, enable AI-powered troubleshooting analysis
            use_ai_tools: If True, use AI-driven tool execution instead of direct API calls

        Returns:
            AgentResult with team-level or individual-level analysis
        """
        if use_ai_tools and self.tool_registry:
            # Use AI-driven tool execution
            return await self.execute_with_tools(context)
        elif not individual_breakdown:
            # Use existing team-level analysis
            return await self._execute_team_analysis(context)
        else:
            # Individual agent analysis with taxonomy breakdown
            return await self._execute_individual_analysis(context, analyze_troubleshooting)
    
    async def _execute_team_analysis(self, context: AgentContext) -> AgentResult:
        """Execute team-level performance analysis (original behavior)"""
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
            
            # Calculate QA metrics
            from src.utils.qa_analyzer import calculate_qa_metrics
            qa_metrics_data = calculate_qa_metrics(
                conversations, 
                metrics['fcr_rate'], 
                metrics.get('reopen_rate', 0)
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
            
            # Add QA metrics if available
            if qa_metrics_data:
                result_data['avg_qa_overall'] = qa_metrics_data.get('overall_qa_score')
                result_data['avg_qa_connection'] = qa_metrics_data.get('customer_connection_score')
                result_data['avg_qa_communication'] = qa_metrics_data.get('communication_quality_score')
                result_data['qa_metrics_summary'] = qa_metrics_data
            
            self.validate_output(result_data)
            
            confidence = min(1.0, len(conversations) / 100)
            confidence_level = (ConfidenceLevel.HIGH if len(conversations) >= 100
                               else ConfidenceLevel.MEDIUM if len(conversations) >= 30
                               else ConfidenceLevel.LOW)

            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(f"AgentPerformanceAgent: Completed in {execution_time:.2f}s")
            self.logger.info(f"   {agent_name} FCR: {metrics['fcr_rate']:.1%}")
            self.logger.info(f"   Escalation rate: {metrics['escalation_rate']:.1%}")

            # Add tool call summary to result data if tools were used
            if self.tool_registry and self.tool_calls_made:
                result_data['tool_calls_summary'] = self.get_tool_call_summary()

            # Update sources to include tool executions if used
            sources = [f"{agent_name} conversations", "Operational metrics", "LLM analysis"]
            if self.tool_registry and self.tool_calls_made:
                sources.append(f"Tool executions ({len(self.tool_calls_made)} calls)")

            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                limitations=[f"Based on {len(conversations)} conversations"] if len(conversations) < 100 else [],
                sources=sources,
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
    
    async def _execute_individual_analysis(self, context: AgentContext, 
                                           analyze_troubleshooting: bool = False) -> AgentResult:
        """Execute individual agent performance analysis with taxonomy breakdown"""
        start_time = datetime.now()
        
        try:
            import httpx
            from src.services.admin_profile_cache import AdminProfileCache
            from src.services.individual_agent_analyzer import IndividualAgentAnalyzer
            from src.services.duckdb_storage import DuckDBStorage
            from src.services.historical_data_manager import HistoricalDataManager
            from src.models.agent_performance_models import VendorPerformanceReport
            from src.services.intercom_service_v2 import IntercomServiceV2
            
            self.validate_input(context)
            
            conversations = context.conversations
            agent_name = self.AGENT_PATTERNS.get(self.agent_filter, {}).get('name', self.agent_filter)
            
            self.logger.info(
                f"AgentPerformanceAgent: Individual breakdown for {agent_name} "
                f"({len(conversations)} conversations)"
            )
            
            # Initialize services (no longer need admin_cache since using tools)
            duckdb_storage = DuckDBStorage()
            
            # Extract admin details for all conversations
            self.logger.info("Extracting admin profiles from conversations...")
            admin_details_map = {}
            all_admins_seen = {}  # Track ALL admins for debugging

            # Collect unique admin IDs and their public emails
            unique_admins = {}
            for conv in conversations:
                admin_ids = self._extract_admin_ids(conv)
                for admin_id in admin_ids:
                    if admin_id not in unique_admins:
                        public_email = self._get_public_email_for_admin(conv, admin_id)
                        unique_admins[admin_id] = public_email

            # Use tool-based lookups for admin profiles
            import asyncio
            tasks = []
            for admin_id, public_email in unique_admins.items():
                tasks.append(self.tool_registry.execute_tool(
                    'lookup_admin_profile',
                    admin_id=admin_id,
                    public_email=public_email
                ))

            # Execute all lookups in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for (admin_id, public_email), result in zip(unique_admins.items(), results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Tool lookup failed for admin {admin_id}: {result}")
                    continue

                if not result.success:
                    self.logger.warning(f"Tool lookup unsuccessful for admin {admin_id}: {result.error_message}")
                    continue

                # Extract data from tool result
                data = result.data
                admin_id_canonical = data['admin_id']  # Use admin_id field (id is deprecated)
                email = data.get('email')
                vendor = data.get('vendor')
                name = data.get('name')

                # Track all admins for debugging
                all_admins_seen[admin_id] = {
                    'email': email,
                    'vendor': vendor,
                    'name': name
                }

                # Only include if vendor matches
                if vendor == self.agent_filter:
                    admin_details_map[admin_id_canonical] = {
                        'id': admin_id_canonical,  # Keep both for compatibility
                        'admin_id': admin_id_canonical,
                        'name': name,
                        'email': email,
                        'vendor': vendor
                    }

                    # Attach to conversations for grouping (find conversations with this admin)
                    for conv in conversations:
                        if admin_id in self._extract_admin_ids(conv):
                            if '_admin_details' not in conv:
                                conv['_admin_details'] = []
                            conv['_admin_details'].append(admin_details_map[admin_id_canonical])
            
            # Enhanced logging for debugging
            self.logger.info(f"Found {len(admin_details_map)} {agent_name} agents")
            self.logger.info(f"Total unique admins seen: {len(all_admins_seen)}")
            
            # Log vendor distribution for debugging
            vendor_counts = {}
            for admin_info in all_admins_seen.values():
                vendor = admin_info['vendor']
                vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
            
            self.logger.info(f"Admin vendor distribution: {vendor_counts}")
            
            # If no matches, log sample admins for debugging
            if not admin_details_map:
                self.logger.warning(f"No {agent_name} agents found! Sampl admins seen:")
                for admin_id, info in list(all_admins_seen.items())[:5]:
                    self.logger.warning(
                        f"  Admin {admin_id}: {info['name']} - "
                        f"email={info['email']}, vendor={info['vendor']}"
                    )
            
            if not admin_details_map:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    data={},
                    confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                    error_message=f"No {agent_name} agents found in conversations",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Analyze individual agents
            analyzer = IndividualAgentAnalyzer(
                self.agent_filter,
                None,  # No longer need admin_cache since using tools
                duckdb_storage,
                enable_troubleshooting_analysis=analyze_troubleshooting
            )
            agent_metrics = await analyzer.analyze_agents(conversations, admin_details_map)
            
            # Generate vendor-level report
            report = self._build_vendor_report(
                agent_metrics, 
                context, 
                agent_name
            )
            
            # Store in DuckDB for historical tracking and get WoW trends
            from src.services.historical_performance_manager import HistoricalPerformanceManager
            historical_manager = HistoricalPerformanceManager(duckdb_storage)
            
            # Store this week's snapshot
            await historical_manager.store_weekly_snapshot(
                vendor=self.agent_filter,
                week_start=context.start_date,
                week_end=context.end_date,
                agent_metrics=agent_metrics
            )
            
            # Get week-over-week comparison if available
            wow_changes = await historical_manager.get_week_over_week_comparison(
                self.agent_filter,
                context.start_date
            )
            report.week_over_week_changes = wow_changes if wow_changes else None
            
            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(f"Individual analysis completed in {execution_time:.2f}s")
            self.logger.info(f"   Analyzed {len(agent_metrics)} agents")
            self.logger.info(f"   {len(report.agents_needing_coaching)} need coaching")
            self.logger.info(f"   {len(report.agents_for_praise)} deserve praise")

            # Add tool call summary to result data
            result_data = report.dict()
            if self.tool_registry and self.tool_calls_made:
                tool_summary = self.get_tool_call_summary()
                result_data['tool_calls_summary'] = tool_summary

            # Update sources to include tool executions if used
            sources = [f"{agent_name} agents", "Taxonomy analysis", "Historical data"]
            if self.tool_registry and self.tool_calls_made:
                sources.append(f"Tool executions ({len(self.tool_calls_made)} calls)")

            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=1.0,
                confidence_level=ConfidenceLevel.HIGH,
                limitations=[],
                sources=sources,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Individual analysis error: {e}", exc_info=True)
            
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _extract_admin_ids(self, conv: Dict) -> List[str]:
        """Extract all admin IDs from a conversation"""
        admin_ids = set()
        
        # From conversation_parts
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            author = part.get('author', {})
            if author.get('type') == 'admin' and author.get('id'):
                admin_ids.add(str(author['id']))
        
        # From assignee
        if conv.get('admin_assignee_id'):
            admin_ids.add(str(conv['admin_assignee_id']))
        
        return list(admin_ids)
    
    def _get_public_email_for_admin(self, conv: Dict, admin_id: str) -> Optional[str]:
        """
        Get email for an admin from conversation.
        
        NOTE: This extracts the email directly from conversation_parts, which may be
        the work email (@hirehoratio.co) rather than public email depending on
        Intercom's configuration.
        """
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            author = part.get('author', {})
            if author.get('type') == 'admin' and str(author.get('id')) == admin_id:
                email = author.get('email')
                if email:
                    self.logger.debug(f"Found email for admin {admin_id} in conversation: {email}")
                    return email
        
        # Also check source author
        source = conv.get('source', {})
        if source:
            author = source.get('author', {})
            if author.get('type') == 'admin' and str(author.get('id')) == admin_id:
                email = author.get('email')
                if email:
                    self.logger.debug(f"Found email for admin {admin_id} in source: {email}")
                    return email
        
        return None
    
    def _build_vendor_report(
        self, 
        agent_metrics: List[Any], 
        context: AgentContext,
        vendor_name: str
    ) -> Any:
        """Build VendorPerformanceReport from agent metrics"""
        from src.models.agent_performance_models import VendorPerformanceReport, TeamTrainingNeed
        
        # Calculate team metrics
        total_convs = sum(a.total_conversations for a in agent_metrics)
        team_fcr = sum(a.fcr_rate * a.total_conversations for a in agent_metrics) / total_convs if total_convs else 0
        team_esc = sum(a.escalation_rate * a.total_conversations for a in agent_metrics) / total_convs if total_convs else 0
        
        # Calculate team QA metrics (average across agents with QA data)
        agents_with_qa = [a for a in agent_metrics if a.qa_metrics is not None]
        if agents_with_qa:
            team_qa_overall = sum(a.qa_metrics.overall_qa_score for a in agents_with_qa) / len(agents_with_qa)
            team_qa_connection = sum(a.qa_metrics.customer_connection_score for a in agents_with_qa) / len(agents_with_qa)
            team_qa_communication = sum(a.qa_metrics.communication_quality_score for a in agents_with_qa) / len(agents_with_qa)
            team_qa_content = sum(a.qa_metrics.content_quality_score for a in agents_with_qa) / len(agents_with_qa)
        else:
            team_qa_overall = team_qa_connection = team_qa_communication = team_qa_content = None
        
        team_metrics = {
            'total_conversations': total_convs,
            'team_fcr_rate': team_fcr,
            'team_escalation_rate': team_esc,
            'total_agents': len(agent_metrics),
            'team_qa_overall': team_qa_overall,
            'team_qa_connection': team_qa_connection,
            'team_qa_communication': team_qa_communication,
            'team_qa_content': team_qa_content,
            'agents_with_qa_metrics': len(agents_with_qa)
        }
        
        # Identify agents needing coaching (bottom 25% or coaching_priority = high)
        agents_needing_coaching = [
            a for a in agent_metrics 
            if a.coaching_priority == "high" or a.fcr_rank > len(agent_metrics) * 0.75
        ]
        
        # Identify agents for praise (top 25% or excellent performance)
        agents_for_praise = [
            a for a in agent_metrics 
            if a.fcr_rank <= max(1, len(agent_metrics) * 0.25) or a.fcr_rate >= 0.9
        ]
        
        # Identify team strengths and weaknesses from common patterns
        team_strengths, team_weaknesses = self._identify_team_patterns(agent_metrics)
        
        # Identify team training needs
        team_training_needs = self._identify_team_training_needs(agent_metrics)
        
        # Generate highlights and lowlights
        highlights = self._generate_highlights(agent_metrics, team_metrics)
        lowlights = self._generate_lowlights(agent_metrics, team_metrics)
        
        # Add WoW trend summary to highlights/lowlights (will be filled after WoW calculation)
        # This is a placeholder that will be updated with actual trends
        
        return VendorPerformanceReport(
            vendor_name=vendor_name,
            analysis_period={
                'start': context.start_date.isoformat(),
                'end': context.end_date.isoformat()
            },
            team_metrics=team_metrics,
            agents=agent_metrics,
            agents_needing_coaching=agents_needing_coaching,
            agents_for_praise=agents_for_praise,
            team_strengths=team_strengths,
            team_weaknesses=team_weaknesses,
            team_training_needs=team_training_needs,
            highlights=highlights,
            lowlights=lowlights
        )
    
    def _identify_team_patterns(self, agent_metrics: List[Any]) -> tuple[List[str], List[str]]:
        """Identify team-wide strengths and weaknesses"""
        from collections import Counter
        
        # Collect all categories mentioned
        all_strong = []
        all_weak = []
        
        for agent in agent_metrics:
            all_strong.extend(agent.strong_categories)
            all_weak.extend(agent.weak_categories)
        
        # Find common patterns (mentioned by >30% of agents)
        threshold = max(1, len(agent_metrics) * 0.3)
        
        strong_counts = Counter(all_strong)
        weak_counts = Counter(all_weak)
        
        team_strengths = [cat for cat, count in strong_counts.items() if count >= threshold]
        team_weaknesses = [cat for cat, count in weak_counts.items() if count >= threshold]
        
        return team_strengths, team_weaknesses
    
    def _identify_team_training_needs(self, agent_metrics: List[Any]) -> List[Any]:
        """Identify team-wide training needs"""
        from collections import defaultdict
        from src.models.agent_performance_models import TeamTrainingNeed
        
        # Group agents by weak subcategories
        weak_by_subcat = defaultdict(list)
        
        for agent in agent_metrics:
            for subcat in agent.weak_subcategories:
                weak_by_subcat[subcat].append(agent.agent_name)
        
        # Create training needs for subcategories affecting multiple agents
        training_needs = []
        for subcat, agent_names in weak_by_subcat.items():
            if len(agent_names) >= 2:  # At least 2 agents struggle
                priority = "high" if len(agent_names) >= len(agent_metrics) * 0.5 else "medium"
                
                training_needs.append(TeamTrainingNeed(
                    topic=subcat,
                    reason=f"{len(agent_names)} agents showing poor performance in this area",
                    affected_agents=agent_names,
                    priority=priority,
                    example_conversations=[]
                ))
        
        return training_needs
    
    def _generate_highlights(self, agent_metrics: List[Any], team_metrics: Dict) -> List[str]:
        """Generate highlights from analysis"""
        highlights = []
        
        # Team FCR
        if team_metrics['team_fcr_rate'] >= 0.85:
            highlights.append(f"Excellent team FCR: {team_metrics['team_fcr_rate']:.1%}")
        
        # Top CSAT performers
        agents_with_csat = [a for a in agent_metrics if a.csat_survey_count >= 5]
        if agents_with_csat:
            top_csat_agent = max(agents_with_csat, key=lambda a: a.csat_score)
            if top_csat_agent.csat_score >= 4.5:
                highlights.append(
                    f"{top_csat_agent.agent_name}: {top_csat_agent.csat_score:.2f} CSAT "
                    f"({top_csat_agent.csat_survey_count} surveys)"
                )
        
        # Top FCR performers
        top_agents = sorted(agent_metrics, key=lambda a: a.fcr_rate, reverse=True)[:2]
        for agent in top_agents:
            if agent.fcr_rate >= 0.9:
                highlights.append(f"{agent.agent_name}: {agent.fcr_rate:.1%} FCR")
        
        # Achievements
        for agent in agent_metrics:
            if agent.praise_worthy_achievements:
                highlights.append(f"{agent.agent_name}: {agent.praise_worthy_achievements[0]}")
                break
        
        return highlights[:5]  # Top 5
    
    def _generate_lowlights(self, agent_metrics: List[Any], team_metrics: Dict) -> List[str]:
        """Generate lowlights from analysis"""
        lowlights = []
        
        # Low CSAT performers
        agents_with_csat = [a for a in agent_metrics if a.csat_survey_count >= 5]
        if agents_with_csat:
            low_csat_agents = [a for a in agents_with_csat if a.csat_score < 3.5]
            if low_csat_agents:
                worst_csat = min(low_csat_agents, key=lambda a: a.csat_score)
                lowlights.append(
                    f"{worst_csat.agent_name}: Low CSAT {worst_csat.csat_score:.2f} "
                    f"({worst_csat.negative_csat_count} negative ratings)"
                )
        
        # High escalation rate
        if team_metrics['team_escalation_rate'] > 0.15:
            lowlights.append(f"Team escalation rate elevated: {team_metrics['team_escalation_rate']:.1%}")
        
        # Agents needing coaching
        struggling_agents = [a for a in agent_metrics if a.coaching_priority == "high"]
        if struggling_agents:
            lowlights.append(f"{len(struggling_agents)} agents need immediate coaching")
        
        # Common weak areas
        from collections import Counter
        all_weak = []
        for agent in agent_metrics:
            all_weak.extend(agent.weak_categories)
        
        if all_weak:
            most_common_weak = Counter(all_weak).most_common(1)[0]
            lowlights.append(f"Team struggles with {most_common_weak[0]} ({most_common_weak[1]} agents)")
        
        return lowlights[:5]  # Top 5
    
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

