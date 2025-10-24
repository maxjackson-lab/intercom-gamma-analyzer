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
    TeamTrainingNeed
)
from src.services.admin_profile_cache import AdminProfileCache
from src.services.duckdb_storage import DuckDBStorage
from src.config.taxonomy import taxonomy_manager

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
        duckdb_storage: Optional[DuckDBStorage] = None
    ):
        """
        Initialize individual agent analyzer.
        
        Args:
            vendor: Vendor name ('horatio', 'boldr', etc.)
            admin_cache: AdminProfileCache instance
            duckdb_storage: Optional DuckDB storage
        """
        self.vendor = vendor
        self.admin_cache = admin_cache
        self.storage = duckdb_storage
        self.logger = logging.getLogger(__name__)
        self.taxonomy = taxonomy_manager
    
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
        
        fcr_rate = len(fcr_convs) / len(closed_convs) if closed_convs else 0
        reopen_rate = len(reopened_convs) / len(closed_convs) if closed_convs else 0
        
        # Escalations
        escalated = [
            c for c in convs
            if any(name in str(c.get('full_text', '')).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary'])
        ]
        escalation_rate = len(escalated) / len(convs) if convs else 0
        
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
        
        median_resolution = np.median(resolution_times) if resolution_times else 0
        over_48h = len([t for t in resolution_times if t > 48])
        
        # Response times
        response_times = [
            c.get('time_to_admin_reply', 0) / 3600 
            for c in convs 
            if c.get('time_to_admin_reply')
        ]
        median_response = np.median(response_times) if response_times else 0
        
        # Complexity
        avg_complexity = np.mean([
            c.get('count_conversation_parts', 0) for c in convs
        ]) if convs else 0
        
        # Taxonomy-based performance breakdown
        perf_by_category = self._analyze_category_performance(convs)
        perf_by_subcategory = self._analyze_subcategory_performance(convs)
        
        # Identify strengths and weaknesses
        strong_cats, weak_cats = self._identify_category_strengths_weaknesses(perf_by_category)
        strong_subcats, weak_subcats = self._identify_subcategory_strengths_weaknesses(perf_by_subcategory)
        
        # Find example conversations
        best_example = self._find_best_example(fcr_convs)
        coaching_example = self._find_coaching_example(escalated, reopened_convs)
        
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
            needs_coaching_example_url=coaching_example
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
                fcr_rate = stats['fcr_count'] / stats['total']
                escalation_rate = stats['escalated_count'] / stats['total']
                median_res = np.median(stats['resolution_times']) if stats['resolution_times'] else 0
                
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
                fcr_rate = stats['fcr_count'] / stats['total']
                escalation_rate = stats['escalated_count'] / stats['total']
                median_res = np.median(stats['resolution_times']) if stats['resolution_times'] else 0
                
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
        # Use taxonomy manager to classify
        classifications = self.taxonomy.classify_conversation(conv)
        
        # Also check tags
        tags = [
            t.get('name', t) if isinstance(t, dict) else t 
            for t in conv.get('tags', {}).get('tags', [])
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
        # High priority if poor performance on key metrics
        if agent.fcr_rate < self.FAIR_FCR or agent.escalation_rate > self.FAIR_ESCALATION:
            return "high"
        
        # Medium priority if multiple weak categories
        if len(agent.weak_categories) >= 2 or len(agent.weak_subcategories) >= 3:
            return "medium"
        
        # Low priority otherwise
        return "low"
    
    def _identify_coaching_areas(self, agent: IndividualAgentMetrics) -> List[str]:
        """Identify specific areas for coaching"""
        areas = []
        
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
    
    def _get_resolution_hours(self, conv: Dict) -> float:
        """Get resolution time in hours"""
        created = conv.get('created_at')
        updated = conv.get('updated_at')
        
        if not (created and updated):
            return float('inf')
        
        if isinstance(created, (int, float)):
            return (updated - created) / 3600
        else:
            return (updated - created).total_seconds() / 3600
    
    def _build_intercom_url(self, conversation_id: Optional[str]) -> Optional[str]:
        """Build Intercom conversation URL"""
        if not conversation_id:
            return None
        
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"

