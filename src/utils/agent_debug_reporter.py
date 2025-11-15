"""
Agent Debug Reporter

Generates human-readable reports showing what EACH agent produced.
Use this to debug multi-agent analysis before it goes to Gamma.
"""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console(record=True)


class AgentDebugReporter:
    """Creates detailed debug reports showing all agent outputs"""
    
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.sections = []
    
    def add_agent_output(self, agent_name: str, agent_result: Dict[str, Any]):
        """Add an agent's output to the report"""
        
        console.print(f"\n{'='*80}")
        console.print(f"[bold cyan]{agent_name}[/bold cyan]")
        console.print(f"{'='*80}\n")
        
        # Status
        success = agent_result.get('success', False)
        confidence = agent_result.get('confidence', 0.0)
        status_icon = "✅" if success else "❌"
        
        console.print(f"{status_icon} [bold]Status:[/bold] {'Success' if success else 'Failed'}")
        console.print(f"🎯 [bold]Confidence:[/bold] {confidence:.2f}")
        
        if agent_result.get('execution_time'):
            console.print(f"⏱️  [bold]Duration:[/bold] {agent_result['execution_time']:.2f}s")
        
        if agent_result.get('token_count'):
            console.print(f"🪙 [bold]Tokens:[/bold] {agent_result['token_count']}")
        
        console.print()
        
        # Data
        data = agent_result.get('data', {})
        
        if agent_name == 'TopicDetectionAgent':
            self._format_topic_detection(data)
        elif agent_name == 'SubTopicDetectionAgent':
            self._format_subtopic_detection(data)
        elif 'sentiment' in agent_name.lower():
            self._format_sentiment(data)
        elif agent_name == 'CorrelationAgent':
            self._format_correlations(data)
        elif agent_name == 'QualityInsightsAgent':
            self._format_quality(data)
        elif agent_name == 'FinPerformanceAgent':
            self._format_fin(data)
        else:
            # Generic formatting
            console.print("[bold]Data:[/bold]")
            for key, value in list(data.items())[:10]:
                console.print(f"  • {key}: {str(value)[:100]}")
    
    def _format_topic_detection(self, data: Dict):
        """Format TopicDetectionAgent output"""
        topic_dist = data.get('topic_distribution', {})
        
        console.print("[bold]Topic Distribution:[/bold]\n")
        
        # Create table
        table = Table(show_header=True)
        table.add_column("Topic", style="cyan")
        table.add_column("Volume", justify="right")
        table.add_column("%", justify="right")
        table.add_column("Method", style="dim")
        
        for topic, stats in sorted(topic_dist.items(), key=lambda x: x[1]['volume'], reverse=True):
            table.add_row(
                topic,
                str(stats['volume']),
                f"{stats['percentage']:.1f}%",
                stats.get('detection_method', 'unknown')
            )
        
        console.print(table)
        console.print()
        
        # Summary
        total_topics = len(topic_dist)
        console.print(f"📊 [bold]{total_topics} topics detected[/bold]")
        
        # Method breakdown
        llm_count = sum(stats.get('llm_smart_count', 0) for stats in topic_dist.values())
        keyword_count = sum(stats.get('keyword_count', 0) for stats in topic_dist.values())
        console.print(f"   LLM classified: {llm_count}")
        console.print(f"   Keyword matched: {keyword_count}")
    
    def _format_subtopic_detection(self, data: Dict):
        """Format SubTopicDetectionAgent output"""
        subtopics = data.get('subtopics_by_tier1_topic', {})
        
        console.print("[bold]Sub-Topic Hierarchy (3-Tier):[/bold]\n")
        
        for tier1_topic, topic_data in subtopics.items():
            console.print(f"[cyan]{tier1_topic}[/cyan]")
            
            # Tier 2
            tier2 = topic_data.get('tier2', {})
            if tier2:
                console.print("  [dim]Tier 2 (from Intercom SDK):[/dim]")
                for subtopic, stats in list(tier2.items())[:5]:
                    console.print(f"    • {subtopic}: {stats.get('volume', 0)} ({stats.get('percentage', 0):.1f}%)")
            
            # Tier 3
            tier3 = topic_data.get('tier3', {})
            if tier3:
                console.print("  [dim]Tier 3 (LLM discovered):[/dim]")
                for theme, stats in list(tier3.items())[:3]:
                    console.print(f"    • {theme}: {stats.get('volume', 0)} ({stats.get('percentage', 0):.1f}%)")
            
            console.print()
    
    def _format_sentiment(self, data: Dict):
        """Format sentiment analysis"""
        insight = data.get('sentiment_insight', 'No insight generated')
        console.print(f"[bold]Sentiment Insight:[/bold]\n{insight}\n")
    
    def _format_correlations(self, data: Dict):
        """Format correlation analysis"""
        correlations = data.get('correlations', [])
        
        console.print(f"[bold]Statistical Correlations Found: {len(correlations)}[/bold]\n")
        
        for corr in correlations[:5]:
            console.print(f"• {corr.get('description', 'Unknown correlation')}")
            console.print(f"  Strength: {corr.get('strength', 0):.2f}")
            console.print(f"  Insight: {corr.get('insight', 'N/A')}")
            console.print()
    
    def _format_quality(self, data: Dict):
        """Format quality insights"""
        insights = data.get('quality_insights', [])
        
        console.print(f"[bold]Quality Insights: {len(insights)}[/bold]\n")
        
        for insight in insights[:5]:
            console.print(f"• {insight.get('description', 'Unknown insight')}")
            console.print()
    
    def _format_fin(self, data: Dict):
        """Format Fin performance"""
        console.print("[bold]Fin AI Performance:[/bold]\n")
        
        free_tier = data.get('free_tier', {})
        paid_tier = data.get('paid_tier', {})
        
        if free_tier:
            console.print(f"[cyan]Free Tier:[/cyan]")
            console.print(f"  Resolution Rate: {free_tier.get('resolution_rate', 0):.1%}")
            console.print(f"  Knowledge Gaps: {free_tier.get('knowledge_gap_rate', 0):.1%}")
            console.print()
        
        if paid_tier:
            console.print(f"[cyan]Paid Tier:[/cyan]")
            console.print(f"  Resolution Rate: {paid_tier.get('resolution_rate', 0):.1%}")
            console.print(f"  Knowledge Gaps: {paid_tier.get('knowledge_gap_rate', 0):.1%}")
    
    def save_report(self):
        """Save the complete debug report"""
        # Export to text
        report_text = console.export_text(clear=False)
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("AGENT DEBUG REPORT - What Each Agent Produced\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("="*80 + "\n\n")
            f.write(report_text)
        
        console.print(f"\n📋 [green]Debug report saved to:[/green] {self.output_path}")
        console.print("[dim]This shows what EACH agent produced before Gamma generation[/dim]")
        
        return self.output_path


def create_agent_debug_report(workflow_results: Dict, output_path: Path) -> Path:
    """
    Create a debug report showing all agent outputs.
    
    Args:
        workflow_results: Dict of agent results from TopicOrchestrator
        output_path: Where to save the report
        
    Returns:
        Path to saved report
    """
    reporter = AgentDebugReporter(output_path)
    
    # Report each agent in execution order
    agent_order = [
        'SegmentationAgent',
        'TopicDetectionAgent',
        'SubTopicDetectionAgent',
        'FinPerformanceAgent',
        'CorrelationAgent',
        'QualityInsightsAgent',
        'OutputFormatterAgent'
    ]
    
    for agent_name in agent_order:
        if agent_name in workflow_results:
            reporter.add_agent_output(agent_name, workflow_results[agent_name])
    
    # Also report per-topic agents
    topic_sentiments = workflow_results.get('TopicSentiments', {})
    if topic_sentiments:
        console.print(f"\n{'='*80}")
        console.print("[bold cyan]Per-Topic Sentiment Analysis[/bold cyan]")
        console.print(f"{'='*80}\n")
        
        for topic, sentiment_result in list(topic_sentiments.items())[:5]:
            console.print(f"[yellow]{topic}:[/yellow]")
            console.print(f"  {sentiment_result.get('data', {}).get('sentiment_insight', 'N/A')}")
            console.print()
    
    return reporter.save_report()

