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
from src.agents.performance_analysis.metrics_calculator import PerformanceMetricsCalculator
from src.agents.performance_analysis.data_extractor import ConversationDataExtractor
from src.agents.performance_analysis.report_builder import VendorReportBuilder
from src.agents.performance_analysis.category_analyzer import CategoryPerformanceAnalyzer
from src.agents.performance_analysis.example_extractor import ExampleConversationExtractor
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

        # Initialize modular components
        self.data_extractor = ConversationDataExtractor(self.tool_registry) if self.tool_registry else None
        self.metrics_calculator = PerformanceMetricsCalculator()
        self.category_analyzer = CategoryPerformanceAnalyzer()
        self.report_builder = VendorReportBuilder()
        self.example_extractor = ExampleConversationExtractor()

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
            
            # Calculate operational metrics using modular component
            metrics = self.metrics_calculator.calculate_performance_metrics(conversations)
            
            # Analyze by category using modular component
            category_performance = self.category_analyzer.analyze_category_performance(conversations)
            
            # Extract example conversations using modular component
            examples = self.example_extractor.extract_performance_examples(conversations, metrics, category_performance)
            
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
            from src.services.individual_agent_analyzer import IndividualAgentAnalyzer
            from src.services.duckdb_storage import DuckDBStorage
            from src.services.historical_performance_manager import HistoricalPerformanceManager
            from src.models.agent_performance_models import VendorPerformanceReport
            
            self.validate_input(context)
            
            conversations = context.conversations
            agent_name = self.AGENT_PATTERNS.get(self.agent_filter, {}).get('name', self.agent_filter)
            
            self.logger.info(
                f"AgentPerformanceAgent: Individual breakdown for {agent_name} "
                f"({len(conversations)} conversations)"
            )
            
            # Initialize services (no longer need admin_cache since using tools)
            duckdb_storage = DuckDBStorage()
            
            # Extract admin details using modular component
            if self.data_extractor:
                admin_details_map, all_admins_seen = await self.data_extractor.extract_admin_profiles(
                    conversations, self.agent_filter
                )
            else:
                # Fallback if no tools available
                admin_details_map = {}
                all_admins_seen = {}
            
            # If no matches, return error
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
            
            # Generate vendor-level report using modular component
            report = self.report_builder.build_vendor_report(
                agent_metrics, 
                context, 
                agent_name
            )
            
            # Store in DuckDB for historical tracking and get WoW trends
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