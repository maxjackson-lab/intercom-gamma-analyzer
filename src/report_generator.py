"""
Generate formatted reports from analysis results.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import os

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generator for various report formats from analysis results."""
    
    @staticmethod
    def generate_text_report(
        analysis_results: Dict,
        output_path: Optional[str] = None,
        include_details: bool = True
    ) -> str:
        """
        Generate human-readable text report.
        
        Args:
            analysis_results: Dictionary containing analysis results
            output_path: Optional path to save the report
            include_details: Whether to include detailed breakdowns
            
        Returns:
            Formatted text report
        """
        report = []
        report.append("=" * 80)
        report.append("INTERCOM CONVERSATION TREND ANALYSIS")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY STATISTICS")
        report.append("-" * 80)
        total_conversations = analysis_results.get('total_conversations', 0)
        report.append(f"Total Conversations Analyzed: {total_conversations:,}")
        
        if 'unique_keywords' in analysis_results:
            report.append(f"Unique Keywords Found: {analysis_results['unique_keywords']:,}")
            
        if 'processed_conversations' in analysis_results:
            processed = analysis_results['processed_conversations']
            report.append(f"Successfully Processed: {processed:,}")
            if processed < total_conversations:
                report.append(f"Failed to Process: {total_conversations - processed:,}")
                
        if 'total_text_length' in analysis_results:
            total_text = analysis_results['total_text_length']
            avg_text = analysis_results.get('average_text_length', 0)
            report.append(f"Total Text Length: {total_text:,} characters")
            report.append(f"Average Text Length: {avg_text:.1f} characters")
            
        report.append("")
        
        # Date range information
        if 'date_range' in analysis_results:
            report.append("ANALYSIS PERIOD")
            report.append("-" * 80)
            date_range = analysis_results['date_range']
            report.append(f"Start Date: {date_range.get('start', 'Unknown')}")
            report.append(f"End Date: {date_range.get('end', 'Unknown')}")
            report.append("")
            
        # Top keywords
        if 'top_keywords' in analysis_results:
            report.append("TOP KEYWORDS (by frequency)")
            report.append("-" * 80)
            top_keywords = analysis_results['top_keywords']
            for i, (keyword, count) in enumerate(top_keywords[:20], 1):
                percentage = (count / total_conversations) * 100 if total_conversations > 0 else 0
                report.append(f"{i:2d}. {keyword:40s} {count:4d} ({percentage:5.1f}%)")
            report.append("")
            
        # Pattern analysis
        if 'pattern_counts' in analysis_results:
            report.append("PATTERN ANALYSIS")
            report.append("-" * 80)
            pattern_counts = analysis_results['pattern_counts']
            sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
            
            for pattern, count in sorted_patterns:
                percentage = (count / total_conversations) * 100 if total_conversations > 0 else 0
                report.append(f"{pattern:40s}: {count:4d} ({percentage:5.1f}%)")
            report.append("")
            
        # State breakdown
        if 'state_breakdown' in analysis_results:
            report.append("CONVERSATION STATE BREAKDOWN")
            report.append("-" * 80)
            state_breakdown = analysis_results['state_breakdown']
            for state, count in state_breakdown.items():
                percentage = (count / total_conversations) * 100 if total_conversations > 0 else 0
                report.append(f"{state:20s}: {count:4d} ({percentage:5.1f}%)")
            report.append("")
            
        # Source type breakdown
        if 'source_breakdown' in analysis_results:
            report.append("CONVERSATION SOURCE BREAKDOWN")
            report.append("-" * 80)
            source_breakdown = analysis_results['source_breakdown']
            for source, count in source_breakdown.items():
                percentage = (count / total_conversations) * 100 if total_conversations > 0 else 0
                report.append(f"{source:20s}: {count:4d} ({percentage:5.1f}%)")
            report.append("")
            
        # Agent analysis
        if 'agent_analysis' in analysis_results and include_details:
            report.append("AGENT RESPONSE ANALYSIS")
            report.append("-" * 80)
            agent_df = analysis_results['agent_analysis']
            if not agent_df.empty:
                for _, row in agent_df.head(10).iterrows():
                    agent_email = row['agent_email']
                    response_count = row['response_count']
                    percentage = (response_count / total_conversations) * 100 if total_conversations > 0 else 0
                    report.append(f"{agent_email:40s}: {response_count:4d} ({percentage:5.1f}%)")
            report.append("")
            
        # Conversation length analysis
        if 'conversation_length' in analysis_results and include_details:
            report.append("CONVERSATION LENGTH ANALYSIS")
            report.append("-" * 80)
            length_stats = analysis_results['conversation_length']
            report.append(f"Average Length: {length_stats.get('average_length', 0):.1f} messages")
            report.append(f"Median Length: {length_stats.get('median_length', 0):.1f} messages")
            report.append(f"Max Length: {length_stats.get('max_length', 0)} messages")
            report.append(f"Min Length: {length_stats.get('min_length', 0)} messages")
            report.append("")
            
        # Response time analysis
        if 'response_time' in analysis_results and include_details:
            report.append("RESPONSE TIME ANALYSIS")
            report.append("-" * 80)
            response_stats = analysis_results['response_time']
            report.append(f"Average Response Time: {response_stats.get('average_response_time_hours', 0):.1f} hours")
            report.append(f"Median Response Time: {response_stats.get('median_response_time_hours', 0):.1f} hours")
            report.append(f"Max Response Time: {response_stats.get('max_response_time_hours', 0):.1f} hours")
            report.append("")
            
        # Customer satisfaction
        if 'satisfaction_analysis' in analysis_results and include_details:
            report.append("CUSTOMER SATISFACTION INDICATORS")
            report.append("-" * 80)
            satisfaction = analysis_results['satisfaction_analysis']
            report.append(f"Positive Sentiment: {satisfaction.get('positive_sentiment', 0)} "
                         f"({satisfaction.get('positive_percentage', 0):.1f}%)")
            report.append(f"Negative Sentiment: {satisfaction.get('negative_sentiment', 0)} "
                         f"({satisfaction.get('negative_percentage', 0):.1f}%)")
            report.append(f"Resolution Mentioned: {satisfaction.get('resolution_mentioned', 0)} "
                         f"({satisfaction.get('resolution_percentage', 0):.1f}%)")
            report.append("")
            
        # Analysis settings
        if 'analysis_settings' in analysis_results and include_details:
            report.append("ANALYSIS SETTINGS")
            report.append("-" * 80)
            settings = analysis_results['analysis_settings']
            for key, value in settings.items():
                report.append(f"{key}: {value}")
            report.append("")
            
        report_text = "\n".join(report)
        
        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                logger.info(f"Text report saved to {output_path}")
            except Exception as e:
                logger.error(f"Failed to save text report: {e}")
                
        return report_text
        
    @staticmethod
    def generate_json_report(
        analysis_results: Dict,
        output_path: str
    ):
        """
        Generate JSON report for programmatic access.
        
        Args:
            analysis_results: Dictionary containing analysis results
            output_path: Path to save the JSON file
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Add metadata
            report_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'version': '1.0',
                    'tool': 'Intercom Conversation Trend Analyzer'
                },
                'analysis_results': analysis_results
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)
                
            logger.info(f"JSON report saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save JSON report: {e}")
            raise
            
    @staticmethod
    def generate_csv_exports(
        analysis_results: Dict,
        output_dir: str
    ):
        """
        Generate CSV files for Excel analysis.
        
        Args:
            analysis_results: Dictionary containing analysis results
            output_dir: Directory to save CSV files
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Export top keywords
            if 'top_keywords' in analysis_results:
                df = pd.DataFrame(
                    analysis_results['top_keywords'],
                    columns=['keyword', 'count']
                )
                df['percentage'] = (df['count'] / analysis_results.get('total_conversations', 1)) * 100
                df.to_csv(f"{output_dir}/top_keywords.csv", index=False)
                logger.info("Exported top_keywords.csv")
                
            # Export time series data
            if 'conversations_by_date' in analysis_results:
                df = analysis_results['conversations_by_date']
                df.to_csv(f"{output_dir}/conversations_by_date.csv", index=False)
                logger.info("Exported conversations_by_date.csv")
                
            # Export hourly data
            if 'conversations_by_hour' in analysis_results:
                df = analysis_results['conversations_by_hour']
                df.to_csv(f"{output_dir}/conversations_by_hour.csv", index=False)
                logger.info("Exported conversations_by_hour.csv")
                
            # Export weekly trends
            if 'weekly_trends' in analysis_results:
                df = analysis_results['weekly_trends']
                df.to_csv(f"{output_dir}/weekly_trends.csv", index=False)
                logger.info("Exported weekly_trends.csv")
                
            # Export agent analysis
            if 'agent_analysis' in analysis_results:
                df = analysis_results['agent_analysis']
                if not df.empty:
                    df['percentage'] = (df['response_count'] / analysis_results.get('total_conversations', 1)) * 100
                    df.to_csv(f"{output_dir}/agent_analysis.csv", index=False)
                    logger.info("Exported agent_analysis.csv")
                    
            # Export pattern analysis
            if 'pattern_counts' in analysis_results:
                pattern_data = []
                for pattern, count in analysis_results['pattern_counts'].items():
                    percentage = (count / analysis_results.get('total_conversations', 1)) * 100
                    pattern_data.append({
                        'pattern': pattern,
                        'count': count,
                        'percentage': percentage
                    })
                    
                df = pd.DataFrame(pattern_data)
                df = df.sort_values('count', ascending=False)
                df.to_csv(f"{output_dir}/pattern_analysis.csv", index=False)
                logger.info("Exported pattern_analysis.csv")
                
        except Exception as e:
            logger.error(f"Failed to generate CSV exports: {e}")
            raise
            
    @staticmethod
    def generate_summary_report(
        analysis_results: Dict,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a concise summary report.
        
        Args:
            analysis_results: Dictionary containing analysis results
            output_path: Optional path to save the summary
            
        Returns:
            Formatted summary text
        """
        summary = []
        summary.append("INTERCOM ANALYSIS SUMMARY")
        summary.append("=" * 50)
        summary.append("")
        
        # Key metrics
        total_conversations = analysis_results.get('total_conversations', 0)
        summary.append(f"📊 Total Conversations: {total_conversations:,}")
        
        if 'unique_keywords' in analysis_results:
            summary.append(f"🔑 Unique Keywords: {analysis_results['unique_keywords']:,}")
            
        # Top 5 keywords
        if 'top_keywords' in analysis_results:
            summary.append("\n🏆 Top 5 Keywords:")
            for i, (keyword, count) in enumerate(analysis_results['top_keywords'][:5], 1):
                summary.append(f"  {i}. {keyword} ({count})")
                
        # Top patterns
        if 'pattern_counts' in analysis_results:
            summary.append("\n🎯 Top Patterns:")
            sorted_patterns = sorted(
                analysis_results['pattern_counts'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            for i, (pattern, count) in enumerate(sorted_patterns[:5], 1):
                percentage = (count / total_conversations) * 100 if total_conversations > 0 else 0
                summary.append(f"  {i}. {pattern} ({count}, {percentage:.1f}%)")
                
        # State breakdown
        if 'state_breakdown' in analysis_results:
            summary.append("\n📈 Conversation States:")
            for state, count in analysis_results['state_breakdown'].items():
                percentage = (count / total_conversations) * 100 if total_conversations > 0 else 0
                summary.append(f"  • {state}: {count} ({percentage:.1f}%)")
                
        summary_text = "\n".join(summary)
        
        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(summary_text)
                logger.info(f"Summary report saved to {output_path}")
            except Exception as e:
                logger.error(f"Failed to save summary report: {e}")
                
        return summary_text
        
    @staticmethod
    def generate_all_reports(
        analysis_results: Dict,
        output_dir: str,
        include_details: bool = True
    ):
        """
        Generate all report formats.
        
        Args:
            analysis_results: Dictionary containing analysis results
            output_dir: Directory to save all reports
            include_details: Whether to include detailed breakdowns
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate all report types
            ReportGenerator.generate_text_report(
                analysis_results, 
                f"{output_dir}/trend_report.txt",
                include_details=include_details
            )
            
            ReportGenerator.generate_json_report(
                analysis_results,
                f"{output_dir}/trend_report.json"
            )
            
            ReportGenerator.generate_summary_report(
                analysis_results,
                f"{output_dir}/summary.txt"
            )
            
            ReportGenerator.generate_csv_exports(
                analysis_results,
                output_dir
            )
            
            logger.info(f"All reports generated in {output_dir}")
            
        except Exception as e:
            logger.error(f"Failed to generate all reports: {e}")
            raise


