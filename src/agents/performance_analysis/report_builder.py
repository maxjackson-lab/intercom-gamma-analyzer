"""
Report Builder Module - Handles building vendor performance reports
"""

from typing import Dict, Any, List
from collections import Counter, defaultdict
from src.models.agent_performance_models import VendorPerformanceReport, TeamTrainingNeed


class VendorReportBuilder:
    """Handles building comprehensive vendor performance reports"""
    
    @staticmethod
    def build_vendor_report(
        agent_metrics: List[Any], 
        context: Any,
        vendor_name: str
    ) -> VendorPerformanceReport:
        """Build VendorPerformanceReport from agent metrics"""
        
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
        team_strengths, team_weaknesses = VendorReportBuilder._identify_team_patterns(agent_metrics)
        
        # Identify team training needs
        team_training_needs = VendorReportBuilder._identify_team_training_needs(agent_metrics)
        
        # Generate highlights and lowlights
        highlights = VendorReportBuilder._generate_highlights(agent_metrics, team_metrics)
        lowlights = VendorReportBuilder._generate_lowlights(agent_metrics, team_metrics)
        
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
    
    @staticmethod
    def _identify_team_patterns(agent_metrics: List[Any]) -> tuple[List[str], List[str]]:
        """Identify team-wide strengths and weaknesses"""
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
    
    @staticmethod
    def _identify_team_training_needs(agent_metrics: List[Any]) -> List[TeamTrainingNeed]:
        """Identify team-wide training needs"""
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
    
    @staticmethod
    def _generate_highlights(agent_metrics: List[Any], team_metrics: Dict) -> List[str]:
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
    
    @staticmethod
    def _generate_lowlights(agent_metrics: List[Any], team_metrics: Dict) -> List[str]:
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
        all_weak = []
        for agent in agent_metrics:
            all_weak.extend(agent.weak_categories)
        
        if all_weak:
            most_common_weak = Counter(all_weak).most_common(1)[0]
            lowlights.append(f"Team struggles with {most_common_weak[0]} ({most_common_weak[1]} agents)")
        
        return lowlights[:5]  # Top 5