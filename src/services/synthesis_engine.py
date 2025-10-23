"""
Synthesis engine for cross-category analysis and insights.

This service combines results from multiple category analyzers to generate
comprehensive insights and identify patterns across different conversation types.
"""

import logging
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict, Counter
from datetime import datetime
import json

from src.services.openai_client import OpenAIClient
from src.config.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class SynthesisEngine:
    """
    Synthesizes results from multiple category analyzers to generate
    comprehensive insights and cross-category patterns.
    
    This service:
    - Combines analysis results from different categories
    - Identifies cross-category patterns and trends
    - Generates executive summaries
    - Provides actionable insights
    - Creates unified reports
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.openai_client = OpenAIClient()
        self.logger.info("SynthesisEngine initialized")

    async def synthesize_category_results(
        self,
        category_results: Dict[str, Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Synthesize results from multiple category analyzers.
        
        Args:
            category_results: Dictionary of category analysis results
            start_date: Start date of analysis period
            end_date: End date of analysis period
            options: Additional options for synthesis
            
        Returns:
            Dictionary containing synthesized insights and recommendations
        """
        self.logger.info(f"Synthesizing results from {len(category_results)} categories")
        
        if not category_results:
            return {
                'message': 'No category results to synthesize',
                'summary': {}
            }
        
        # Extract common metrics across categories
        cross_category_metrics = self._extract_cross_category_metrics(category_results)
        
        # Identify cross-category patterns
        cross_category_patterns = self._identify_cross_category_patterns(category_results)
        
        # Generate trend analysis
        trend_analysis = self._analyze_cross_category_trends(category_results)
        
        # Identify priority areas
        priority_areas = self._identify_priority_areas(category_results)
        
        # Generate actionable insights
        actionable_insights = self._generate_actionable_insights(category_results)
        
        # Create executive summary
        executive_summary = self._create_executive_summary(
            category_results,
            cross_category_metrics,
            cross_category_patterns,
            trend_analysis,
            priority_areas
        )
        
        # Generate AI-powered synthesis
        ai_synthesis = None
        if options and options.get('generate_ai_insights', False):
            ai_synthesis = await self._generate_ai_synthesis(
                category_results,
                cross_category_metrics,
                cross_category_patterns,
                trend_analysis,
                priority_areas,
                start_date,
                end_date
            )
        
        results = {
            'synthesis_metadata': {
                'categories_analyzed': list(category_results.keys()),
                'analysis_period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                },
                'total_conversations': sum(
                    result.get('data_summary', {}).get('total_conversations', 0)
                    for result in category_results.values()
                ),
                'filtered_conversations': sum(
                    result.get('data_summary', {}).get('filtered_conversations', 0)
                    for result in category_results.values()
                )
            },
            'cross_category_metrics': cross_category_metrics,
            'cross_category_patterns': cross_category_patterns,
            'trend_analysis': trend_analysis,
            'priority_areas': priority_areas,
            'actionable_insights': actionable_insights,
            'executive_summary': executive_summary,
            'ai_synthesis': ai_synthesis
        }
        
        self.logger.info("Category results synthesis completed")
        return results

    def _extract_cross_category_metrics(self, category_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Extract common metrics across all categories."""
        metrics = {
            'total_conversations_by_category': {},
            'conversation_volume_distribution': {},
            'sentiment_distribution_by_category': {},
            'topic_overlap': {},
            'tag_overlap': {},
            'escalation_patterns': {},
            'success_rates': {}
        }
        
        # Extract conversation volumes
        for category, results in category_results.items():
            data_summary = results.get('data_summary', {})
            metrics['total_conversations_by_category'][category] = data_summary.get('total_conversations', 0)
            metrics['conversation_volume_distribution'][category] = data_summary.get('filtered_conversations', 0)
        
        # Extract sentiment distributions
        for category, results in category_results.items():
            data_summary = results.get('data_summary', {})
            sentiment = data_summary.get('sentiment_distribution', {})
            if sentiment:
                metrics['sentiment_distribution_by_category'][category] = sentiment
        
        # Extract topic and tag overlaps
        all_topics = defaultdict(int)
        all_tags = defaultdict(int)
        
        for category, results in category_results.items():
            data_summary = results.get('data_summary', {})
            
            # Collect topics
            topics = data_summary.get('top_topics', [])
            for topic in topics:
                all_topics[topic['topic']] += topic['count']
            
            # Collect tags
            tags = data_summary.get('top_tags', [])
            for tag in tags:
                all_tags[tag['tag']] += tag['count']
        
        # Find overlapping topics and tags
        metrics['topic_overlap'] = self._find_overlapping_items(all_topics, category_results, 'topics')
        metrics['tag_overlap'] = self._find_overlapping_items(all_tags, category_results, 'tags')
        
        return metrics

    def _identify_cross_category_patterns(self, category_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns that span multiple categories."""
        patterns = {
            'common_issues': defaultdict(int),
            'escalation_patterns': defaultdict(int),
            'success_patterns': defaultdict(int),
            'temporal_patterns': defaultdict(int),
            'user_behavior_patterns': defaultdict(int)
        }
        
        # Analyze common issues across categories
        for category, results in category_results.items():
            analysis_results = results.get('analysis_results', {})
            
            # Extract common issues from each category
            if 'common_issues' in analysis_results:
                for issue in analysis_results['common_issues']:
                    patterns['common_issues'][issue] += 1
            
            # Extract escalation patterns
            if 'escalation_analysis' in analysis_results:
                escalation_stats = analysis_results['escalation_analysis'].get('statistics', {})
                for trigger, count in escalation_stats.items():
                    patterns['escalation_patterns'][trigger] += count
            
            # Extract success patterns
            if 'success_analysis' in analysis_results:
                success_stats = analysis_results['success_analysis'].get('statistics', {})
                for pattern, count in success_stats.items():
                    patterns['success_patterns'][pattern] += count
        
        # Convert defaultdicts to regular dicts
        for pattern_type in patterns:
            patterns[pattern_type] = dict(patterns[pattern_type])
        
        return patterns

    def _analyze_cross_category_trends(self, category_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends across categories."""
        trends = {
            'volume_trends': {},
            'sentiment_trends': {},
            'escalation_trends': {},
            'success_trends': {},
            'category_correlation': {}
        }
        
        # Analyze volume trends
        category_volumes = {}
        for category, results in category_results.items():
            data_summary = results.get('data_summary', {})
            category_volumes[category] = data_summary.get('filtered_conversations', 0)
        
        trends['volume_trends'] = self._calculate_volume_trends(category_volumes)
        
        # Analyze sentiment trends
        sentiment_trends = {}
        for category, results in category_results.items():
            data_summary = results.get('data_summary', {})
            sentiment = data_summary.get('sentiment_distribution', {})
            if sentiment:
                sentiment_trends[category] = sentiment
        
        trends['sentiment_trends'] = self._calculate_sentiment_trends(sentiment_trends)
        
        # Analyze escalation trends
        escalation_trends = {}
        for category, results in category_results.items():
            analysis_results = results.get('analysis_results', {})
            if 'escalation_analysis' in analysis_results:
                escalation_rate = analysis_results['escalation_analysis'].get('escalation_rate', 0)
                escalation_trends[category] = escalation_rate
        
        trends['escalation_trends'] = self._calculate_escalation_trends(escalation_trends)
        
        # Analyze success trends
        success_trends = {}
        for category, results in category_results.items():
            analysis_results = results.get('analysis_results', {})
            if 'success_analysis' in analysis_results:
                success_rate = analysis_results['success_analysis'].get('success_rate', 0)
                success_trends[category] = success_rate
        
        trends['success_trends'] = self._calculate_success_trends(success_trends)
        
        # Calculate category correlations
        trends['category_correlation'] = self._calculate_category_correlations(category_results)
        
        return trends

    def _identify_priority_areas(self, category_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Identify priority areas based on analysis results."""
        priorities = {
            'high_priority_categories': [],
            'escalation_hotspots': [],
            'success_opportunities': [],
            'improvement_areas': [],
            'resource_allocation': {}
        }
        
        # Identify high-priority categories based on volume and issues
        category_priorities = {}
        for category, results in category_results.items():
            data_summary = results.get('data_summary', {})
            analysis_results = results.get('analysis_results', {})
            
            # Calculate priority score
            volume = data_summary.get('filtered_conversations', 0)
            escalation_rate = analysis_results.get('escalation_analysis', {}).get('escalation_rate', 0)
            failure_rate = analysis_results.get('failure_analysis', {}).get('failure_rate', 0)
            
            priority_score = (volume * 0.4) + (escalation_rate * 0.3) + (failure_rate * 0.3)
            category_priorities[category] = priority_score
        
        # Sort categories by priority
        sorted_priorities = sorted(category_priorities.items(), key=lambda x: x[1], reverse=True)
        priorities['high_priority_categories'] = [cat for cat, score in sorted_priorities[:3]]
        
        # Identify escalation hotspots
        escalation_hotspots = []
        for category, results in category_results.items():
            analysis_results = results.get('analysis_results', {})
            escalation_rate = analysis_results.get('escalation_analysis', {}).get('escalation_rate', 0)
            
            if escalation_rate > 30:  # Threshold for high escalation rate
                escalation_hotspots.append({
                    'category': category,
                    'escalation_rate': escalation_rate,
                    'priority': 'high' if escalation_rate > 50 else 'medium'
                })
        
        priorities['escalation_hotspots'] = sorted(escalation_hotspots, key=lambda x: x['escalation_rate'], reverse=True)
        
        # Identify success opportunities
        success_opportunities = []
        for category, results in category_results.items():
            analysis_results = results.get('analysis_results', {})
            success_rate = analysis_results.get('success_analysis', {}).get('success_rate', 0)
            
            if success_rate < 70:  # Threshold for improvement opportunity
                success_opportunities.append({
                    'category': category,
                    'success_rate': success_rate,
                    'improvement_potential': 100 - success_rate
                })
        
        priorities['success_opportunities'] = sorted(success_opportunities, key=lambda x: x['improvement_potential'], reverse=True)
        
        # Generate resource allocation recommendations
        priorities['resource_allocation'] = self._generate_resource_allocation_recommendations(category_results)
        
        return priorities

    def _generate_actionable_insights(self, category_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate actionable insights from the analysis."""
        insights = []
        
        # Generate insights based on cross-category patterns
        cross_category_patterns = self._identify_cross_category_patterns(category_results)
        
        # Insight 1: Common issues across categories
        common_issues = cross_category_patterns.get('common_issues', {})
        if common_issues:
            top_issue = max(common_issues.items(), key=lambda x: x[1])
            insights.append({
                'type': 'cross_category_issue',
                'title': f"Common Issue: {top_issue[0]}",
                'description': f"This issue appears in {top_issue[1]} categories and affects multiple conversation types.",
                'action': f"Create a unified response strategy for {top_issue[0]} across all categories.",
                'priority': 'high' if top_issue[1] >= 3 else 'medium',
                'impact': 'cross_category'
            })
        
        # Insight 2: Escalation patterns
        escalation_patterns = cross_category_patterns.get('escalation_patterns', {})
        if escalation_patterns:
            top_escalation = max(escalation_patterns.items(), key=lambda x: x[1])
            insights.append({
                'type': 'escalation_pattern',
                'title': f"Escalation Pattern: {top_escalation[0]}",
                'description': f"This escalation trigger appears {top_escalation[1]} times across categories.",
                'action': f"Develop specific training for handling {top_escalation[0]} scenarios.",
                'priority': 'high' if top_escalation[1] >= 10 else 'medium',
                'impact': 'escalation_reduction'
            })
        
        # Insight 3: Success patterns
        success_patterns = cross_category_patterns.get('success_patterns', {})
        if success_patterns:
            top_success = max(success_patterns.items(), key=lambda x: x[1])
            insights.append({
                'type': 'success_pattern',
                'title': f"Success Pattern: {top_success[0]}",
                'description': f"This success pattern appears {top_success[1]} times across categories.",
                'action': f"Standardize and replicate {top_success[0]} approach across all categories.",
                'priority': 'medium',
                'impact': 'success_improvement'
            })
        
        # Insight 4: Category-specific insights
        for category, results in category_results.items():
            analysis_results = results.get('analysis_results', {})
            
            # Check for high escalation rates
            escalation_rate = analysis_results.get('escalation_analysis', {}).get('escalation_rate', 0)
            if escalation_rate > 40:
                insights.append({
                    'type': 'category_escalation',
                    'title': f"High Escalation Rate in {category}",
                    'description': f"{category} category has an escalation rate of {escalation_rate:.1f}%.",
                    'action': f"Investigate and address root causes of escalations in {category} category.",
                    'priority': 'high',
                    'impact': 'category_specific'
                })
            
            # Check for low success rates
            success_rate = analysis_results.get('success_analysis', {}).get('success_rate', 0)
            if success_rate < 60:
                insights.append({
                    'type': 'category_success',
                    'title': f"Low Success Rate in {category}",
                    'description': f"{category} category has a success rate of {success_rate:.1f}%.",
                    'action': f"Improve resolution capabilities and training for {category} category.",
                    'priority': 'high',
                    'impact': 'category_specific'
                })
        
        return insights

    def _create_executive_summary(
        self,
        category_results: Dict[str, Dict[str, Any]],
        cross_category_metrics: Dict[str, Any],
        cross_category_patterns: Dict[str, Any],
        trend_analysis: Dict[str, Any],
        priority_areas: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an executive summary of the synthesis results."""
        summary = {
            'overview': {
                'total_categories_analyzed': len(category_results),
                'total_conversations': cross_category_metrics.get('total_conversations_by_category', {}),
                'analysis_period': 'N/A',  # Will be set by caller
                'key_findings': []
            },
            'key_metrics': {
                'conversation_volume_distribution': cross_category_metrics.get('conversation_volume_distribution', {}),
                'sentiment_distribution': cross_category_metrics.get('sentiment_distribution_by_category', {}),
                'escalation_rates': trend_analysis.get('escalation_trends', {}),
                'success_rates': trend_analysis.get('success_trends', {})
            },
            'priority_areas': {
                'high_priority_categories': priority_areas.get('high_priority_categories', []),
                'escalation_hotspots': priority_areas.get('escalation_hotspots', []),
                'success_opportunities': priority_areas.get('success_opportunities', [])
            },
            'cross_category_insights': {
                'common_issues': cross_category_patterns.get('common_issues', {}),
                'escalation_patterns': cross_category_patterns.get('escalation_patterns', {}),
                'success_patterns': cross_category_patterns.get('success_patterns', {})
            },
            'recommendations': {
                'immediate_actions': [],
                'medium_term_improvements': [],
                'long_term_strategic_changes': []
            }
        }
        
        # Generate key findings
        key_findings = []
        
        # Finding 1: Volume distribution
        volume_dist = cross_category_metrics.get('conversation_volume_distribution', {})
        if volume_dist:
            top_category = max(volume_dist.items(), key=lambda x: x[1])
            key_findings.append(f"{top_category[0]} category has the highest conversation volume ({top_category[1]} conversations)")
        
        # Finding 2: Escalation hotspots
        escalation_hotspots = priority_areas.get('escalation_hotspots', [])
        if escalation_hotspots:
            top_hotspot = escalation_hotspots[0]
            key_findings.append(f"{top_hotspot['category']} category has the highest escalation rate ({top_hotspot['escalation_rate']:.1f}%)")
        
        # Finding 3: Success opportunities
        success_opportunities = priority_areas.get('success_opportunities', [])
        if success_opportunities:
            top_opportunity = success_opportunities[0]
            key_findings.append(f"{top_opportunity['category']} category has the lowest success rate ({top_opportunity['success_rate']:.1f}%)")
        
        summary['overview']['key_findings'] = key_findings
        
        # Generate recommendations
        recommendations = self._generate_recommendations(category_results, cross_category_patterns, priority_areas)
        summary['recommendations'] = recommendations
        
        return summary

    def _generate_recommendations(
        self,
        category_results: Dict[str, Dict[str, Any]],
        cross_category_patterns: Dict[str, Any],
        priority_areas: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate recommendations based on the analysis."""
        recommendations = {
            'immediate_actions': [],
            'medium_term_improvements': [],
            'long_term_strategic_changes': []
        }
        
        # Immediate actions
        escalation_hotspots = priority_areas.get('escalation_hotspots', [])
        for hotspot in escalation_hotspots[:2]:  # Top 2 hotspots
            recommendations['immediate_actions'].append(
                f"Address high escalation rate in {hotspot['category']} category ({hotspot['escalation_rate']:.1f}%)"
            )
        
        # Medium-term improvements
        success_opportunities = priority_areas.get('success_opportunities', [])
        for opportunity in success_opportunities[:2]:  # Top 2 opportunities
            recommendations['medium_term_improvements'].append(
                f"Improve success rate in {opportunity['category']} category (current: {opportunity['success_rate']:.1f}%)"
            )
        
        # Long-term strategic changes
        common_issues = cross_category_patterns.get('common_issues', {})
        if common_issues:
            top_issue = max(common_issues.items(), key=lambda x: x[1])
            recommendations['long_term_strategic_changes'].append(
                f"Develop comprehensive strategy for {top_issue[0]} across all categories"
            )
        
        return recommendations

    def _find_overlapping_items(
        self,
        all_items: Dict[str, int],
        category_results: Dict[str, Dict[str, Any]],
        item_type: str
    ) -> Dict[str, Any]:
        """Find items that appear in multiple categories."""
        overlapping = {}
        
        for item, total_count in all_items.items():
            if total_count > 1:  # Appears in multiple categories
                categories = []
                for category, results in category_results.items():
                    data_summary = results.get('data_summary', {})
                    items = data_summary.get(f'top_{item_type}', [])
                    
                    for item_data in items:
                        if item_data[item_type[:-1]] == item:  # Remove 's' from item_type
                            categories.append(category)
                            break
                
                if len(categories) > 1:
                    overlapping[item] = {
                        'total_count': total_count,
                        'categories': categories,
                        'category_count': len(categories)
                    }
        
        return overlapping

    def _calculate_volume_trends(self, category_volumes: Dict[str, int]) -> Dict[str, Any]:
        """Calculate volume trends across categories."""
        total_volume = sum(category_volumes.values())
        trends = {}
        
        for category, volume in category_volumes.items():
            percentage = (volume / total_volume * 100) if total_volume > 0 else 0
            trends[category] = {
                'volume': volume,
                'percentage': percentage,
                'trend': 'high' if percentage > 20 else 'medium' if percentage > 10 else 'low'
            }
        
        return trends

    def _calculate_sentiment_trends(self, sentiment_trends: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Calculate sentiment trends across categories."""
        trends = {}
        
        for category, sentiment in sentiment_trends.items():
            total = sum(sentiment.values())
            if total > 0:
                positive_pct = (sentiment.get('positive', 0) / total * 100)
                negative_pct = (sentiment.get('negative', 0) / total * 100)
                
                trends[category] = {
                    'positive_percentage': positive_pct,
                    'negative_percentage': negative_pct,
                    'sentiment_score': positive_pct - negative_pct,
                    'overall_sentiment': 'positive' if positive_pct > negative_pct else 'negative'
                }
        
        return trends

    def _calculate_escalation_trends(self, escalation_trends: Dict[str, float]) -> Dict[str, Any]:
        """Calculate escalation trends across categories."""
        trends = {}
        
        for category, rate in escalation_trends.items():
            trends[category] = {
                'escalation_rate': rate,
                'trend': 'high' if rate > 30 else 'medium' if rate > 15 else 'low',
                'priority': 'high' if rate > 40 else 'medium' if rate > 20 else 'low'
            }
        
        return trends

    def _calculate_success_trends(self, success_trends: Dict[str, float]) -> Dict[str, Any]:
        """Calculate success trends across categories."""
        trends = {}
        
        for category, rate in success_trends.items():
            trends[category] = {
                'success_rate': rate,
                'trend': 'high' if rate > 80 else 'medium' if rate > 60 else 'low',
                'improvement_needed': rate < 70
            }
        
        return trends

    def _calculate_category_correlations(self, category_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate correlations between categories."""
        correlations = {}
        
        # This is a simplified correlation calculation
        # In a real implementation, you would use statistical methods
        categories = list(category_results.keys())
        
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                # Calculate correlation based on shared topics/tags
                correlation_score = self._calculate_simple_correlation(
                    category_results[cat1],
                    category_results[cat2]
                )
                
                if correlation_score > 0.3:  # Threshold for significant correlation
                    correlations[f"{cat1}-{cat2}"] = {
                        'correlation_score': correlation_score,
                        'strength': 'strong' if correlation_score > 0.7 else 'medium'
                    }
        
        return correlations

    def _calculate_simple_correlation(self, results1: Dict[str, Any], results2: Dict[str, Any]) -> float:
        """Calculate a simple correlation score between two category results."""
        # This is a simplified correlation calculation
        # In a real implementation, you would use proper statistical methods
        
        data1 = results1.get('data_summary', {})
        data2 = results2.get('data_summary', {})
        
        # Compare topics
        topics1 = set(topic['topic'] for topic in data1.get('top_topics', []))
        topics2 = set(topic['topic'] for topic in data2.get('top_topics', []))
        
        topic_overlap = len(topics1.intersection(topics2))
        topic_union = len(topics1.union(topics2))
        
        topic_correlation = topic_overlap / topic_union if topic_union > 0 else 0
        
        # Compare tags
        tags1 = set(tag['tag'] for tag in data1.get('top_tags', []))
        tags2 = set(tag['tag'] for tag in data2.get('top_tags', []))
        
        tag_overlap = len(tags1.intersection(tags2))
        tag_union = len(tags1.union(tags2))
        
        tag_correlation = tag_overlap / tag_union if tag_union > 0 else 0
        
        # Average the correlations
        return (topic_correlation + tag_correlation) / 2

    def _generate_resource_allocation_recommendations(self, category_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate resource allocation recommendations."""
        recommendations = {
            'high_priority_categories': [],
            'medium_priority_categories': [],
            'low_priority_categories': [],
            'resource_suggestions': {}
        }
        
        # Calculate priority scores for each category
        category_priorities = {}
        for category, results in category_results.items():
            data_summary = results.get('data_summary', {})
            analysis_results = results.get('analysis_results', {})
            
            volume = data_summary.get('filtered_conversations', 0)
            escalation_rate = analysis_results.get('escalation_analysis', {}).get('escalation_rate', 0)
            failure_rate = analysis_results.get('failure_analysis', {}).get('failure_rate', 0)
            
            priority_score = (volume * 0.4) + (escalation_rate * 0.3) + (failure_rate * 0.3)
            category_priorities[category] = priority_score
        
        # Sort categories by priority
        sorted_priorities = sorted(category_priorities.items(), key=lambda x: x[1], reverse=True)
        
        # Categorize by priority level
        total_categories = len(sorted_priorities)
        high_count = max(1, total_categories // 3)
        medium_count = max(1, total_categories // 3)
        
        recommendations['high_priority_categories'] = [cat for cat, score in sorted_priorities[:high_count]]
        recommendations['medium_priority_categories'] = [cat for cat, score in sorted_priorities[high_count:high_count + medium_count]]
        recommendations['low_priority_categories'] = [cat for cat, score in sorted_priorities[high_count + medium_count:]]
        
        # Generate resource suggestions
        for category in recommendations['high_priority_categories']:
            recommendations['resource_suggestions'][category] = {
                'priority': 'high',
                'suggested_resources': ['Additional training', 'Enhanced documentation', 'Dedicated support'],
                'estimated_impact': 'high'
            }
        
        for category in recommendations['medium_priority_categories']:
            recommendations['resource_suggestions'][category] = {
                'priority': 'medium',
                'suggested_resources': ['Standard training', 'Process improvement', 'Monitoring'],
                'estimated_impact': 'medium'
            }
        
        for category in recommendations['low_priority_categories']:
            recommendations['resource_suggestions'][category] = {
                'priority': 'low',
                'suggested_resources': ['Basic monitoring', 'Periodic review'],
                'estimated_impact': 'low'
            }
        
        return recommendations

    async def _generate_ai_synthesis(
        self,
        category_results: Dict[str, Dict[str, Any]],
        cross_category_metrics: Dict[str, Any],
        cross_category_patterns: Dict[str, Any],
        trend_analysis: Dict[str, Any],
        priority_areas: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Generate AI-powered synthesis of the analysis results."""
        try:
            # Create a comprehensive summary for AI analysis
            summary_text = f"""
            Cross-Category Analysis Summary
            Analysis Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
            
            Categories Analyzed: {list(category_results.keys())}
            
            Cross-Category Metrics:
            - Total conversations by category: {cross_category_metrics.get('total_conversations_by_category', {})}
            - Conversation volume distribution: {cross_category_metrics.get('conversation_volume_distribution', {})}
            - Sentiment distribution by category: {cross_category_metrics.get('sentiment_distribution_by_category', {})}
            
            Cross-Category Patterns:
            - Common issues: {cross_category_patterns.get('common_issues', {})}
            - Escalation patterns: {cross_category_patterns.get('escalation_patterns', {})}
            - Success patterns: {cross_category_patterns.get('success_patterns', {})}
            
            Trend Analysis:
            - Volume trends: {trend_analysis.get('volume_trends', {})}
            - Sentiment trends: {trend_analysis.get('sentiment_trends', {})}
            - Escalation trends: {trend_analysis.get('escalation_trends', {})}
            - Success trends: {trend_analysis.get('success_trends', {})}
            
            Priority Areas:
            - High priority categories: {priority_areas.get('high_priority_categories', [])}
            - Escalation hotspots: {priority_areas.get('escalation_hotspots', [])}
            - Success opportunities: {priority_areas.get('success_opportunities', [])}
            
            Please provide a comprehensive synthesis of these results, including:
            1. Key insights and patterns
            2. Strategic recommendations
            3. Priority actions
            4. Long-term implications
            """
            
            # Use the custom analysis prompt
            ai_synthesis = await self.openai_client.generate_analysis(
                PromptTemplates.get_custom_analysis_prompt(
                    custom_prompt=summary_text,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    intercom_data="Cross-category analysis results"
                )
            )
            
            return ai_synthesis
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI synthesis: {e}")
            return f"AI synthesis generation failed: {e}"
