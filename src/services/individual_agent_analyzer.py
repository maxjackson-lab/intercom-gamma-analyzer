"""
Individual Agent Performance Analyzer

Analyzes performance of individual agents within a vendor team,
with taxonomy-based category/subcategory breakdown.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import numpy as np

from src.models.agent_performance_models import (
    IndividualAgentMetrics,
    CategoryPerformance,
    TeamTrainingNeed,
    QAPerformanceMetrics
)
from src.services.admin_profile_cache import AdminProfileCache
from src.services.duckdb_storage import DuckDBStorage
from src.config.taxonomy import taxonomy_manager
from src.utils.qa_analyzer import calculate_qa_metrics

logger = logging.getLogger(__name__)


class IndividualAgentAnalyzer:
    """Analyze performance of individual agents within a vendor"""
    
    # Performance thresholds
    EXCELLENT_FCR = 0.85
    GOOD_FCR = 0.75
    FAIR_FCR = 0.70
    
    EXCELLENT_ESCALATION = 0.10
    GOOD_ESCALATION = 0.15
    FAIR_ESCALATION = 0.20
    
    def __init__(
        self, 
        vendor: str, 
        admin_cache: AdminProfileCache, 
        duckdb_storage: Optional[DuckDBStorage] = None,
        enable_troubleshooting_analysis: bool = False
    ):
        """
        Initialize individual agent analyzer.
        
        Args:
            vendor: Vendor name ('horatio', 'boldr', etc.)
            admin_cache: AdminProfileCache instance
            duckdb_storage: Optional DuckDB storage
            enable_troubleshooting_analysis: Enable AI-powered troubleshooting analysis (slower)
        """
        self.vendor = vendor
        self.admin_cache = admin_cache
        self.storage = duckdb_storage
        self.enable_troubleshooting_analysis = enable_troubleshooting_analysis
        self.logger = logging.getLogger(__name__)
        self.taxonomy = taxonomy_manager
        
        # Initialize troubleshooting analyzer if enabled
        if enable_troubleshooting_analysis:
            from src.services.troubleshooting_analyzer import TroubleshootingAnalyzer
            self.troubleshooting_analyzer = TroubleshootingAnalyzer()
        else:
            self.troubleshooting_analyzer = None
    
    async def analyze_agents(
        self, 
        conversations: List[Dict], 
        admin_details_map: Dict[str, Dict]
    ) -> List[IndividualAgentMetrics]:
        """
        Analyze each agent's performance.
        
        Args:
            conversations: List of conversations with _admin_details attached
            admin_details_map: Map of agent_id -> admin details
            
        Returns:
            List of IndividualAgentMetrics for each agent
        """
        self.logger.info(
            f"Analyzing {len(admin_details_map)} agents from {len(conversations)} conversations"
        )
        
        # Group conversations by agent
        conversations_by_agent = self._group_by_agent(conversations, admin_details_map)
        
        # Calculate metrics for each agent
        agent_metrics = []
        for agent_id, agent_convs in conversations_by_agent.items():
            if agent_id not in admin_details_map:
                continue
            
            metrics = await self._calculate_individual_metrics(
                agent_id, 
                agent_convs, 
                admin_details_map[agent_id]
            )
            agent_metrics.append(metrics)
        
        # Rank agents
        agent_metrics = self._rank_agents(agent_metrics)
        
        # Identify coaching needs and achievements
        for agent in agent_metrics:
            agent.coaching_priority = self._assess_coaching_priority(agent)
            agent.coaching_focus_areas = self._identify_coaching_areas(agent)
            agent.praise_worthy_achievements = self._identify_achievements(agent)
        
        self.logger.info(f"Analyzed {len(agent_metrics)} agents")
        
        return agent_metrics
    
    def _group_by_agent(
        self, 
        conversations: List[Dict], 
        admin_details_map: Dict[str, Dict]
    ) -> Dict[str, List[Dict]]:
        """Group conversations by agent ID"""
        conversations_by_agent = defaultdict(list)
        
        for conv in conversations:
            admin_details = conv.get('_admin_details', [])
            
            # Find the primary agent for this conversation
            for admin in admin_details:
                agent_id = admin.get('id')
                if agent_id and agent_id in admin_details_map:
                    conversations_by_agent[agent_id].append(conv)
                    break  # Only assign to one agent
        
        return dict(conversations_by_agent)
    
    async def _calculate_individual_metrics(
        self, 
        agent_id: str, 
        convs: List[Dict], 
        agent_info: Dict
    ) -> IndividualAgentMetrics:
        """Calculate comprehensive metrics for one agent"""
        
        # Basic metrics
        closed_convs = [c for c in convs if c.get('state') == 'closed']
        fcr_convs = [c for c in closed_convs if c.get('count_reopens', 0) == 0]
        reopened_convs = [c for c in closed_convs if c.get('count_reopens', 0) > 0]
        
        fcr_rate = len(fcr_convs) / len(closed_convs) if len(closed_convs) > 0 else 0.0
        reopen_rate = len(reopened_convs) / len(closed_convs) if len(closed_convs) > 0 else 0.0
        
        # Escalations
        escalated = [
            c for c in convs
            if any(name in str(c.get('full_text', '')).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary'])
        ]
        escalation_rate = len(escalated) / len(convs) if len(convs) > 0 else 0.0
        
        # Resolution times
        resolution_times = []
        for conv in closed_convs:
            created = conv.get('created_at')
            updated = conv.get('updated_at')
            if created and updated:
                if isinstance(created, (int, float)):
                    hours = (updated - created) / 3600
                else:
                    hours = (updated - created).total_seconds() / 3600
                resolution_times.append(hours)
        
        median_resolution = float(np.median(resolution_times)) if len(resolution_times) > 0 else 0.0
        over_48h = len([t for t in resolution_times if t > 48])
        
        # Response times
        response_times = [
            (c.get('time_to_admin_reply', 0) or 0) / 3600 
            for c in convs 
            if c.get('time_to_admin_reply')
        ]
        median_response = float(np.median(response_times)) if len(response_times) > 0 else 0.0
        
        # Complexity
        avg_complexity = float(np.mean([
            c.get('count_conversation_parts', 0) for c in convs
        ])) if len(convs) > 0 else 0.0
        
        # CSAT metrics (customer satisfaction)
        rated_convs = [c for c in convs if c.get('conversation_rating') is not None]
        ratings = [c.get('conversation_rating') for c in rated_convs]
        
        csat_score = float(np.mean(ratings)) if ratings else 0.0
        csat_survey_count = len(rated_convs)
        negative_csat_count = len([r for r in ratings if r <= 2])  # 1★ or 2★
        
        # Rating distribution
        rating_distribution = {
            '5_star': len([r for r in ratings if r == 5]),
            '4_star': len([r for r in ratings if r == 4]),
            '3_star': len([r for r in ratings if r == 3]),
            '2_star': len([r for r in ratings if r == 2]),
            '1_star': len([r for r in ratings if r == 1])
        }
        
        # Taxonomy-based performance breakdown
        perf_by_category = self._analyze_category_performance(convs)
        perf_by_subcategory = self._analyze_subcategory_performance(convs)
        
        # Identify strengths and weaknesses
        strong_cats, weak_cats = self._identify_category_strengths_weaknesses(perf_by_category)
        strong_subcats, weak_subcats = self._identify_subcategory_strengths_weaknesses(perf_by_subcategory)
        
        # Find example conversations
        best_example = self._find_best_example(fcr_convs)
        coaching_example = self._find_coaching_example(escalated, reopened_convs)
        
        # Find worst CSAT examples for coaching (egregious cases)
        worst_csat_examples = self._find_worst_csat_examples(rated_convs, ratings)
        
        # Troubleshooting analysis (if enabled)
        troubleshooting_metrics = {}
        if self.troubleshooting_analyzer:
            troubleshooting_pattern = await self.troubleshooting_analyzer.analyze_agent_troubleshooting_pattern(
                convs,
                agent_info.get('name', 'Unknown')
            )
            troubleshooting_metrics = {
                'avg_troubleshooting_score': troubleshooting_pattern['avg_troubleshooting_score'],
                'avg_diagnostic_questions': troubleshooting_pattern['avg_diagnostic_questions'],
                'premature_escalation_rate': troubleshooting_pattern['premature_escalation_rate'],
                'troubleshooting_consistency': troubleshooting_pattern['consistency_score']
            }
        else:
            troubleshooting_metrics = {
                'avg_troubleshooting_score': 0.0,
                'avg_diagnostic_questions': 0.0,
                'premature_escalation_rate': 0.0,
                'troubleshooting_consistency': 0.0
            }
        
        # QA Metrics (automated quality analysis)
        qa_metrics_data = calculate_qa_metrics(convs, fcr_rate, reopen_rate)
        qa_metrics = QAPerformanceMetrics(**qa_metrics_data) if qa_metrics_data else None
        
        return IndividualAgentMetrics(
            agent_id=agent_id,
            agent_name=agent_info.get('name', 'Unknown'),
            agent_email=agent_info.get('email', ''),
            vendor=agent_info.get('vendor', self.vendor),
            total_conversations=len(convs),
            fcr_rate=fcr_rate,
            reopen_rate=reopen_rate,
            escalation_rate=escalation_rate,
            median_resolution_hours=float(median_resolution),
            median_response_hours=float(median_response),
            over_48h_count=over_48h,
            avg_conversation_complexity=float(avg_complexity),
            # CSAT metrics
            csat_score=csat_score,
            csat_survey_count=csat_survey_count,
            negative_csat_count=negative_csat_count,
            rating_distribution=rating_distribution,
            # QA metrics (automated quality analysis)
            qa_metrics=qa_metrics,
            # Troubleshooting metrics
            avg_troubleshooting_score=troubleshooting_metrics['avg_troubleshooting_score'],
            avg_diagnostic_questions=troubleshooting_metrics['avg_diagnostic_questions'],
            premature_escalation_rate=troubleshooting_metrics['premature_escalation_rate'],
            troubleshooting_consistency=troubleshooting_metrics['troubleshooting_consistency'],
            # Taxonomy performance
            performance_by_category=perf_by_category,
            performance_by_subcategory=perf_by_subcategory,
            strong_categories=strong_cats,
            weak_categories=weak_cats,
            strong_subcategories=strong_subcats,
            weak_subcategories=weak_subcats,
            fcr_rank=0,  # Will be set in _rank_agents
            response_time_rank=0,  # Will be set in _rank_agents
            coaching_priority="medium",  # Will be assessed later
            coaching_focus_areas=[],  # Will be identified later
            praise_worthy_achievements=[],  # Will be identified later
            best_example_url=best_example,
            needs_coaching_example_url=coaching_example,
            worst_csat_examples=worst_csat_examples
        )
    
    def _analyze_category_performance(self, convs: List[Dict]) -> Dict[str, CategoryPerformance]:
        """Analyze performance by primary taxonomy category"""
        category_stats = defaultdict(lambda: {
            'total': 0,
            'fcr_count': 0,
            'escalated_count': 0,
            'resolution_times': []
        })
        
        for conv in convs:
            # Get category from tags/topics using taxonomy
            categories = self._extract_categories(conv)
            
            for category in categories:
                primary = category.get('primary', 'Unknown')
                category_stats[primary]['total'] += 1
                
                if conv.get('state') == 'closed' and conv.get('count_reopens', 0) == 0:
                    category_stats[primary]['fcr_count'] += 1
                
                if any(name in str(conv.get('full_text', '')).lower() 
                      for name in ['dae-ho', 'max jackson', 'hilary']):
                    category_stats[primary]['escalated_count'] += 1
                
                # Resolution time
                if conv.get('state') == 'closed':
                    created = conv.get('created_at')
                    updated = conv.get('updated_at')
                    if created and updated:
                        if isinstance(created, (int, float)):
                            hours = (updated - created) / 3600
                        else:
                            hours = (updated - created).total_seconds() / 3600
                        category_stats[primary]['resolution_times'].append(hours)
        
        # Convert to CategoryPerformance objects
        result = {}
        for category, stats in category_stats.items():
            if stats['total'] >= 3:  # Minimum sample size
                fcr_rate = stats['fcr_count'] / stats['total'] if stats['total'] > 0 else 0.0
                escalation_rate = stats['escalated_count'] / stats['total'] if stats['total'] > 0 else 0.0
                median_res = float(np.median(stats['resolution_times'])) if len(stats['resolution_times']) > 0 else 0.0
                
                result[category] = CategoryPerformance(
                    primary_category=category,
                    subcategory=None,
                    volume=stats['total'],
                    fcr_rate=fcr_rate,
                    escalation_rate=escalation_rate,
                    median_resolution_hours=float(median_res),
                    performance_level=self._assess_performance_level(fcr_rate, escalation_rate)
                )
        
        return result
    
    def _analyze_subcategory_performance(self, convs: List[Dict]) -> Dict[str, CategoryPerformance]:
        """Analyze performance by subcategory"""
        subcategory_stats = defaultdict(lambda: {
            'primary': '',
            'total': 0,
            'fcr_count': 0,
            'escalated_count': 0,
            'resolution_times': []
        })
        
        for conv in convs:
            categories = self._extract_categories(conv)
            
            for category in categories:
                primary = category.get('primary', 'Unknown')
                subcategory = category.get('subcategory')
                
                if subcategory:
                    key = f"{primary}>{subcategory}"
                    subcategory_stats[key]['primary'] = primary
                    subcategory_stats[key]['total'] += 1
                    
                    if conv.get('state') == 'closed' and conv.get('count_reopens', 0) == 0:
                        subcategory_stats[key]['fcr_count'] += 1
                    
                    if any(name in str(conv.get('full_text', '')).lower() 
                          for name in ['dae-ho', 'max jackson', 'hilary']):
                        subcategory_stats[key]['escalated_count'] += 1
                    
                    # Resolution time
                    if conv.get('state') == 'closed':
                        created = conv.get('created_at')
                        updated = conv.get('updated_at')
                        if created and updated:
                            if isinstance(created, (int, float)):
                                hours = (updated - created) / 3600
                            else:
                                hours = (updated - created).total_seconds() / 3600
                            subcategory_stats[key]['resolution_times'].append(hours)
        
        # Convert to CategoryPerformance objects
        result = {}
        for key, stats in subcategory_stats.items():
            if stats['total'] >= 2:  # Lower threshold for subcategories
                fcr_rate = stats['fcr_count'] / stats['total'] if stats['total'] > 0 else 0.0
                escalation_rate = stats['escalated_count'] / stats['total'] if stats['total'] > 0 else 0.0
                median_res = float(np.median(stats['resolution_times'])) if len(stats['resolution_times']) > 0 else 0.0
                
                primary, subcat = key.split('>', 1)
                
                result[key] = CategoryPerformance(
                    primary_category=primary,
                    subcategory=subcat,
                    volume=stats['total'],
                    fcr_rate=fcr_rate,
                    escalation_rate=escalation_rate,
                    median_resolution_hours=float(median_res),
                    performance_level=self._assess_performance_level(fcr_rate, escalation_rate)
                )
        
        return result
    
    def _extract_categories(self, conv: Dict) -> List[Dict]:
        """Extract categories from conversation using taxonomy"""
        # Use taxonomy manager to classify (with fallback)
        try:
            classifications = self.taxonomy.classify_conversation(conv) if self.taxonomy and hasattr(self.taxonomy, 'classify_conversation') else []
        except Exception as e:
            self.logger.warning(f"Taxonomy classification failed: {e}")
            classifications = []
        
        # Also check tags (with defensive extraction)
        tags_data = conv.get('tags', {})
        if isinstance(tags_data, dict):
            tags_list = tags_data.get('tags', [])
        elif isinstance(tags_data, list):
            tags_list = tags_data
        else:
            tags_list = []
            
        tags = [
            t.get('name', t) if isinstance(t, dict) else t 
            for t in tags_list
        ]
        
        # Simple mapping for common tags
        categories = []
        for tag in tags:
            tag_lower = str(tag).lower()
            if 'billing' in tag_lower or 'refund' in tag_lower:
                categories.append({'primary': 'Billing', 'subcategory': 'Refund' if 'refund' in tag_lower else None})
            elif 'bug' in tag_lower:
                categories.append({'primary': 'Bug', 'subcategory': None})
            elif 'account' in tag_lower:
                categories.append({'primary': 'Account', 'subcategory': None})
            elif 'api' in tag_lower:
                categories.append({'primary': 'Product Question', 'subcategory': 'Integration'})
        
        # Add classifications from taxonomy
        for classification in classifications:
            categories.append({
                'primary': classification.get('category', 'Unknown'),
                'subcategory': classification.get('subcategory')
            })
        
        return categories if categories else [{'primary': 'Unknown', 'subcategory': None}]
    
    def _assess_performance_level(self, fcr_rate: float, escalation_rate: float) -> str:
        """Assess performance level based on FCR and escalation"""
        if fcr_rate >= self.EXCELLENT_FCR and escalation_rate <= self.EXCELLENT_ESCALATION:
            return "excellent"
        elif fcr_rate >= self.GOOD_FCR and escalation_rate <= self.GOOD_ESCALATION:
            return "good"
        elif fcr_rate >= self.FAIR_FCR and escalation_rate <= self.FAIR_ESCALATION:
            return "fair"
        else:
            return "poor"
    
    def _identify_category_strengths_weaknesses(
        self, 
        perf_by_category: Dict[str, CategoryPerformance]
    ) -> tuple[List[str], List[str]]:
        """Identify strong and weak categories"""
        strong = []
        weak = []
        
        for category, perf in perf_by_category.items():
            if perf.performance_level in ["excellent", "good"]:
                strong.append(category)
            elif perf.performance_level == "poor":
                weak.append(category)
        
        return strong, weak
    
    def _identify_subcategory_strengths_weaknesses(
        self, 
        perf_by_subcategory: Dict[str, CategoryPerformance]
    ) -> tuple[List[str], List[str]]:
        """Identify strong and weak subcategories"""
        strong = []
        weak = []
        
        for subcat, perf in perf_by_subcategory.items():
            if perf.performance_level in ["excellent", "good"]:
                strong.append(subcat)
            elif perf.performance_level == "poor":
                weak.append(subcat)
        
        return strong, weak
    
    def _rank_agents(self, agent_metrics: List[IndividualAgentMetrics]) -> List[IndividualAgentMetrics]:
        """Rank agents by performance"""
        # Sort by FCR (descending)
        sorted_by_fcr = sorted(agent_metrics, key=lambda a: a.fcr_rate, reverse=True)
        for i, agent in enumerate(sorted_by_fcr):
            agent.fcr_rank = i + 1
        
        # Sort by response time (ascending)
        sorted_by_response = sorted(agent_metrics, key=lambda a: a.median_response_hours)
        for i, agent in enumerate(sorted_by_response):
            agent.response_time_rank = i + 1
        
        return agent_metrics
    
    def _assess_coaching_priority(self, agent: IndividualAgentMetrics) -> str:
        """Assess coaching priority for an agent"""
        # High priority if poor performance on key metrics OR low CSAT
        if agent.fcr_rate < self.FAIR_FCR or agent.escalation_rate > self.FAIR_ESCALATION:
            return "high"
        
        # High priority if low CSAT with sufficient surveys (egregious cases)
        if agent.csat_survey_count >= 5 and agent.csat_score < 3.5:
            return "high"
        
        # High priority if multiple negative CSAT ratings
        if agent.negative_csat_count >= 3:
            return "high"
        
        # HIGH PRIORITY: Poor troubleshooting methodology
        if agent.premature_escalation_rate > 0.4:  # >40% premature escalations
            return "high"
        
        if agent.avg_troubleshooting_score < 0.4:  # Low effort score
            return "high"
        
        # Medium priority if multiple weak categories
        if len(agent.weak_categories) >= 2 or len(agent.weak_subcategories) >= 3:
            return "medium"
        
        # Medium priority if moderate CSAT issues
        if agent.csat_survey_count >= 5 and agent.csat_score < 4.0:
            return "medium"
        
        # Medium priority if moderate troubleshooting issues
        if agent.premature_escalation_rate > 0.25 or agent.avg_troubleshooting_score < 0.6:
            return "medium"
        
        # Low priority otherwise
        return "low"
    
    def _identify_coaching_areas(self, agent: IndividualAgentMetrics) -> List[str]:
        """Identify specific areas for coaching"""
        areas = []
        
        # HIGHEST PRIORITY: Troubleshooting methodology (your main focus!)
        if agent.premature_escalation_rate > 0.4:
            areas.append(
                f"CRITICAL: Premature Escalations ({agent.premature_escalation_rate:.0%}) - "
                f"Establish troubleshooting checklist before escalating"
            )
        elif agent.premature_escalation_rate > 0.25:
            areas.append(f"Premature Escalations ({agent.premature_escalation_rate:.0%})")
        
        if agent.avg_diagnostic_questions < 2.0 and agent.avg_troubleshooting_score > 0:
            areas.append(
                f"Insufficient Diagnostic Questions (avg {agent.avg_diagnostic_questions:.1f}) - "
                f"Require minimum 3 questions before escalating"
            )
        
        if agent.troubleshooting_consistency < 0.6 and agent.avg_troubleshooting_score > 0:
            areas.append("Inconsistent Troubleshooting Approach - Apply process consistently")
        
        # PRIORITY: Low CSAT issues
        if agent.csat_score < 3.5 and agent.csat_survey_count >= 3:
            areas.append(f"URGENT: Low CSAT ({agent.csat_score:.2f}) - Review worst tickets immediately")
        elif agent.negative_csat_count >= 2:
            areas.append(f"Customer Satisfaction ({agent.negative_csat_count} negative ratings)")
        
        # Add weak subcategories as coaching focus
        for subcat in agent.weak_subcategories[:5]:  # Top 5
            areas.append(subcat)
        
        # If no subcategories, use weak categories
        if not areas:
            for cat in agent.weak_categories[:3]:
                areas.append(cat)
        
        return areas
    
    def _identify_achievements(self, agent: IndividualAgentMetrics) -> List[str]:
        """Identify praise-worthy achievements"""
        achievements = []
        
        # High FCR
        if agent.fcr_rate >= self.EXCELLENT_FCR:
            achievements.append(f"Excellent FCR rate: {agent.fcr_rate:.1%}")
        
        # Low escalation
        if agent.escalation_rate <= self.EXCELLENT_ESCALATION:
            achievements.append(f"Minimal escalations: {agent.escalation_rate:.1%}")
        
        # Top rank
        if agent.fcr_rank == 1:
            achievements.append("Top FCR performer on team")
        
        # Strong categories
        if len(agent.strong_categories) >= 3:
            achievements.append(f"Excellence across {len(agent.strong_categories)} categories")
        
        return achievements
    
    def _find_best_example(self, fcr_convs: List[Dict]) -> Optional[str]:
        """Find URL of best resolved conversation"""
        if not fcr_convs:
            return None
        
        # Find fastest resolution
        best = min(fcr_convs, key=lambda c: self._get_resolution_hours(c), default=None)
        if best:
            return self._build_intercom_url(best.get('id'))
        
        return None
    
    def _find_coaching_example(
        self, 
        escalated: List[Dict], 
        reopened: List[Dict]
    ) -> Optional[str]:
        """Find URL of conversation needing coaching"""
        # Prefer reopened (indicates incomplete resolution)
        if reopened:
            return self._build_intercom_url(reopened[0].get('id'))
        
        # Otherwise use escalated
        if escalated:
            return self._build_intercom_url(escalated[0].get('id'))
        
        return None
    
    def _find_worst_csat_examples(
        self, 
        rated_convs: List[Dict],
        ratings: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Find worst CSAT conversations for coaching.
        
        Returns top 3-5 most egregious low-CSAT tickets with:
        - Conversation URL
        - CSAT rating
        - Brief customer complaint/issue
        - Category (if available)
        
        Prioritizes 1★ over 2★ ratings.
        """
        if not rated_convs:
            return []
        
        # Find conversations with low ratings (1-2 stars)
        low_csat_convs = []
        for conv in rated_convs:
            rating = conv.get('conversation_rating')
            if rating and rating <= 2:
                low_csat_convs.append(conv)
        
        if not low_csat_convs:
            return []
        
        # Sort by rating (worst first)
        low_csat_convs.sort(key=lambda c: c.get('conversation_rating', 5))
        
        # Build detailed examples for top 5 worst
        examples = []
        for conv in low_csat_convs[:5]:
            rating = conv.get('conversation_rating')
            conv_id = conv.get('id')
            
            # Extract customer complaint/issue
            full_text = conv.get('full_text', '')
            customer_messages = conv.get('customer_messages', [])
            
            # Try to get the main customer complaint (first message or first 200 chars)
            complaint = ""
            if customer_messages:
                complaint = customer_messages[0][:200] + "..." if len(customer_messages[0]) > 200 else customer_messages[0]
            elif full_text:
                complaint = full_text[:200] + "..." if len(full_text) > 200 else full_text
            
            # Get category if available
            category = conv.get('primary_category', 'Unknown')
            subcategory = conv.get('subcategory')
            category_label = f"{category}>{subcategory}" if subcategory else category
            
            # Get whether it was reopened or escalated (red flags)
            reopened = conv.get('count_reopens', 0) > 0
            escalated = any(name in full_text.lower() for name in ['dae-ho', 'max jackson', 'hilary'])
            
            red_flags = []
            if reopened:
                red_flags.append("Reopened")
            if escalated:
                red_flags.append("Escalated")
            
            examples.append({
                'url': self._build_intercom_url(conv_id),
                'rating': int(rating),
                'category': category_label,
                'complaint': complaint,
                'red_flags': red_flags,
                'conversation_id': conv_id
            })
        
        return examples
    
    def _get_resolution_hours(self, conv: Dict) -> float:
        """Get resolution time in hours"""
        created = conv.get('created_at')
        updated = conv.get('updated_at')
        
        if not (created and updated):
            return float('inf')
        
        try:
            if isinstance(created, (int, float)) and isinstance(updated, (int, float)):
                return float((updated - created) / 3600) if created > 0 else float('inf')
            else:
                delta = (updated - created).total_seconds()
                return float(delta / 3600) if delta > 0 else float('inf')
        except Exception as e:
            self.logger.warning(f"Error calculating resolution hours: {e}")
            return float('inf')
    
    def _build_intercom_url(self, conversation_id: Optional[str]) -> Optional[str]:
        """Build Intercom conversation URL"""
        if not conversation_id:
            return None
        
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"

