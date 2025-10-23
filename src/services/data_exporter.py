"""
Data export service for spreadsheet and other format exports.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import json

from src.config.settings import settings

logger = logging.getLogger(__name__)


class DataExporter:
    """Service for exporting data to various formats."""
    
    def __init__(self):
        self.output_dir = Path(settings.output_directory)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def export_conversations_to_excel(
        self, 
        conversations: List[Dict], 
        filename: str,
        include_metrics: bool = True
    ) -> str:
        """Export conversations to Excel with multiple sheets."""
        self.logger.info(f"Exporting {len(conversations)} conversations to Excel")
        
        output_path = self.output_dir / f"{filename}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Main conversations sheet
            conversations_df = self._prepare_conversations_dataframe(conversations)
            conversations_df.to_excel(writer, sheet_name='Conversations', index=False)
            
            # Metrics summary sheet
            if include_metrics:
                metrics_df = self._prepare_metrics_dataframe(conversations)
                metrics_df.to_excel(writer, sheet_name='Metrics_Summary', index=False)
            
            # Time-based analysis sheet
            time_analysis_df = self._prepare_time_analysis_dataframe(conversations)
            time_analysis_df.to_excel(writer, sheet_name='Time_Analysis', index=False)
            
            # Topic analysis sheet
            topic_analysis_df = self._prepare_topic_analysis_dataframe(conversations)
            topic_analysis_df.to_excel(writer, sheet_name='Topic_Analysis', index=False)
            
            # Agent performance sheet
            agent_performance_df = self._prepare_agent_performance_dataframe(conversations)
            agent_performance_df.to_excel(writer, sheet_name='Agent_Performance', index=False)
            
            # Customer satisfaction sheet
            satisfaction_df = self._prepare_satisfaction_dataframe(conversations)
            satisfaction_df.to_excel(writer, sheet_name='Customer_Satisfaction', index=False)
        
        self.logger.info(f"Excel export completed: {output_path}")
        return str(output_path)
    
    def export_conversations_to_csv(
        self, 
        conversations: List[Dict], 
        filename: str,
        split_by_category: bool = True
    ) -> List[str]:
        """Export conversations to CSV files."""
        self.logger.info(f"Exporting {len(conversations)} conversations to CSV")
        
        output_files = []
        
        if split_by_category:
            # Export different categories to separate CSV files
            categories = {
                'conversations': self._prepare_conversations_dataframe(conversations),
                'metrics': self._prepare_metrics_dataframe(conversations),
                'time_analysis': self._prepare_time_analysis_dataframe(conversations),
                'topic_analysis': self._prepare_topic_analysis_dataframe(conversations),
                'agent_performance': self._prepare_agent_performance_dataframe(conversations),
                'satisfaction': self._prepare_satisfaction_dataframe(conversations)
            }
            
            for category, df in categories.items():
                if not df.empty:
                    output_path = self.output_dir / f"{filename}_{category}.csv"
                    df.to_csv(output_path, index=False)
                    output_files.append(str(output_path))
        else:
            # Single CSV file
            df = self._prepare_conversations_dataframe(conversations)
            output_path = self.output_dir / f"{filename}.csv"
            df.to_csv(output_path, index=False)
            output_files.append(str(output_path))
        
        self.logger.info(f"CSV export completed: {len(output_files)} files")
        return output_files
    
    def export_analysis_results_to_excel(
        self, 
        analysis_results: Any, 
        filename: str
    ) -> str:
        """Export analysis results to Excel with multiple sheets."""
        self.logger.info("Exporting analysis results to Excel")
        
        output_path = self.output_dir / f"{filename}_analysis.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Executive summary sheet
            if hasattr(analysis_results, 'executive_summary'):
                summary_df = self._prepare_executive_summary_dataframe(analysis_results)
                summary_df.to_excel(writer, sheet_name='Executive_Summary', index=False)
            
            # Metrics sheet
            if hasattr(analysis_results, 'volume'):
                metrics_df = self._prepare_analysis_metrics_dataframe(analysis_results)
                metrics_df.to_excel(writer, sheet_name='Metrics', index=False)
            
            # Trends sheet
            if hasattr(analysis_results, 'key_trends'):
                trends_df = self._prepare_trends_dataframe(analysis_results)
                trends_df.to_excel(writer, sheet_name='Trends', index=False)
            
            # Customer quotes sheet
            if hasattr(analysis_results, 'customer_quotes'):
                quotes_df = self._prepare_quotes_dataframe(analysis_results)
                quotes_df.to_excel(writer, sheet_name='Customer_Quotes', index=False)
            
            # Recommendations sheet
            if hasattr(analysis_results, 'recommendations'):
                recommendations_df = self._prepare_recommendations_dataframe(analysis_results)
                recommendations_df.to_excel(writer, sheet_name='Recommendations', index=False)
        
        self.logger.info(f"Analysis results export completed: {output_path}")
        return str(output_path)
    
    def export_raw_data_to_json(
        self, 
        conversations: List[Dict], 
        filename: str
    ) -> str:
        """Export raw conversation data to JSON."""
        self.logger.info(f"Exporting {len(conversations)} conversations to JSON")
        
        output_path = self.output_dir / f"{filename}_raw.json"
        
        # Add metadata
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_conversations": len(conversations),
                "export_type": "raw_conversations"
            },
            "conversations": conversations
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"JSON export completed: {output_path}")
        return str(output_path)
    
    def export_to_parquet(
        self, 
        conversations: List[Dict], 
        filename: str
    ) -> str:
        """Export conversations to Parquet format for efficient storage."""
        self.logger.info(f"Exporting {len(conversations)} conversations to Parquet")
        
        df = self._prepare_conversations_dataframe(conversations)
        output_path = self.output_dir / f"{filename}.parquet"
        
        df.to_parquet(output_path, index=False)
        
        self.logger.info(f"Parquet export completed: {output_path}")
        return str(output_path)
    
    def export_technical_troubleshooting_analysis(
        self, 
        conversations: List[Dict], 
        filename: str
    ) -> str:
        """Export technical troubleshooting analysis to CSV."""
        self.logger.info(f"Exporting technical troubleshooting analysis for {len(conversations)} conversations")
        
        output_path = self.output_dir / f"{filename}_technical_troubleshooting.csv"
        
        # Prepare technical troubleshooting data
        tech_data = []
        
        for conv in conversations:
            # Extract all conversation text
            full_text = self._extract_conversation_text(conv)
            
            # Detect technical troubleshooting patterns
            patterns = self._detect_technical_patterns(full_text)
            
            # Extract agent actions and escalations
            agent_actions = self._extract_agent_actions(conv)
            escalations = self._detect_escalations(full_text)
            
            # Get conversation metadata
            row = {
                'conversation_id': conv.get('id'),
                'conversation_url': f"https://app.intercom.com/a/inbox/{conv.get('id')}",
                'created_at': self._format_timestamp(conv.get('created_at')),
                'state': conv.get('state'),
                'priority': conv.get('priority'),
                'admin_assignee_id': conv.get('admin_assignee_id'),
                'tags': ', '.join([tag.get('name', tag) if isinstance(tag, dict) else tag for tag in conv.get('tags', {}).get('tags', [])]),
                'topics': ', '.join([topic.get('name', topic) if isinstance(topic, dict) else topic for topic in conv.get('topics', {}).get('topics', [])]),
                'language': conv.get('custom_attributes', {}).get('Language', ''),
                'ai_agent_participated': conv.get('ai_agent_participated', False),
                'fin_ai_preview': conv.get('custom_attributes', {}).get('Fin AI Agent: Preview', False),
                'copilot_used': conv.get('custom_attributes', {}).get('Copilot used', False),
                'conversation_rating': conv.get('conversation_rating'),
                'time_to_admin_reply': conv.get('statistics', {}).get('time_to_admin_reply'),
                'handling_time': conv.get('statistics', {}).get('handling_time'),
                'count_conversation_parts': conv.get('statistics', {}).get('count_conversation_parts'),
                'count_reopens': conv.get('statistics', {}).get('count_reopens'),
            }
            
            # Add detected patterns
            row.update({
                'cache_clear_mentioned': patterns.get('cache_clear', False),
                'browser_switch_mentioned': patterns.get('browser_switch', False),
                'connection_issue_mentioned': patterns.get('connection_issue', False),
                'escalation_mentioned': patterns.get('escalation', False),
                'product_issue_mentioned': patterns.get('product_issue', False),
                'detected_keywords': ', '.join(patterns.get('keywords', [])),
                'escalated_to': ', '.join(escalations.get('escalated_to', [])),
                'escalation_notes': escalations.get('notes', ''),
                'agent_actions': ', '.join(agent_actions.get('actions', [])),
                'resolution_notes': agent_actions.get('resolution_notes', ''),
                'customer_response': agent_actions.get('customer_response', ''),
            })
            
            # Determine primary issue category
            if patterns.get('escalation'):
                row['primary_issue_category'] = 'escalation'
            elif patterns.get('cache_clear'):
                row['primary_issue_category'] = 'cache_clear'
            elif patterns.get('browser_switch'):
                row['primary_issue_category'] = 'browser_switch'
            elif patterns.get('connection_issue'):
                row['primary_issue_category'] = 'connection_issue'
            elif patterns.get('product_issue'):
                row['primary_issue_category'] = 'product_issue'
            else:
                row['primary_issue_category'] = 'other'
            
            tech_data.append(row)
        
        # Create DataFrame and export
        df = pd.DataFrame(tech_data)
        df.to_csv(output_path, index=False)
        
        self.logger.info(f"Technical troubleshooting analysis export completed: {output_path}")
        return str(output_path)
    
    # Data preparation methods
    def _prepare_conversations_dataframe(self, conversations: List[Dict]) -> pd.DataFrame:
        """Prepare conversations data for DataFrame."""
        data = []
        
        for conv in conversations:
            # Basic conversation info
            row = {
                'conversation_id': conv.get('id'),
                'conversation_url': f"https://app.intercom.com/a/inbox/{conv.get('id')}",
                'created_at': self._format_timestamp(conv.get('created_at')),
                'updated_at': self._format_timestamp(conv.get('updated_at')),
                'closed_at': self._format_timestamp(conv.get('statistics', {}).get('last_close_at')),
                'state': conv.get('state'),
                'priority': conv.get('priority'),
                'source_type': conv.get('source', {}).get('type'),
                'source_subject': conv.get('source', {}).get('subject'),
                'source_body': conv.get('source', {}).get('body', '')[:500],  # Truncate for readability
                'source_url': conv.get('source', {}).get('url'),
                'conversation_rating': conv.get('conversation_rating'),
                'tags': ', '.join([tag.get('name', tag) if isinstance(tag, dict) else tag for tag in conv.get('tags', {}).get('tags', [])]),
                'topics': ', '.join([topic.get('name', topic) if isinstance(topic, dict) else topic for topic in conv.get('topics', {}).get('topics', [])]),
            }
            
            # Custom attributes (Hilary's metadata)
            custom_attrs = conv.get('custom_attributes', {})
            row.update({
                'has_attachments': custom_attrs.get('Has attachments', False),
                'auto_translated': custom_attrs.get('Auto-translated', False),
                'fin_ai_preview': custom_attrs.get('Fin AI Agent: Preview', False),
                'copilot_used': custom_attrs.get('Copilot used', False),
                'language': custom_attrs.get('Language', ''),
            })
            
            # AI Agent participation
            row['ai_agent_participated'] = conv.get('ai_agent_participated', False)
            row['ai_resolution_state'] = conv.get('ai_agent', {}).get('resolution_state')
            row['ai_source_title'] = conv.get('ai_agent', {}).get('source_title')
            
            # Contact information
            contact = conv.get('contacts', {}).get('contacts', [{}])[0] if conv.get('contacts', {}).get('contacts') else {}
            row.update({
                'contact_id': contact.get('id'),
                'contact_email': contact.get('email'),
                'contact_name': contact.get('name'),
                'contact_country': contact.get('location', {}).get('country'),
                'contact_city': contact.get('location', {}).get('city'),
                'user_tier': contact.get('custom_attributes', {}).get('tier'),
            })
            
            # Assignment and team info
            row.update({
                'admin_assignee_id': conv.get('admin_assignee_id'),
                'team_assignee_id': conv.get('team_assignee_id'),
                'sla_applied': conv.get('sla_applied'),
            })
            
            # Statistics
            stats = conv.get('statistics', {})
            row.update({
                'time_to_assignment': stats.get('time_to_assignment'),
                'time_to_admin_reply': stats.get('time_to_admin_reply'),
                'time_to_first_close': stats.get('time_to_first_close'),
                'median_time_to_reply': stats.get('median_time_to_reply'),
                'handling_time': stats.get('handling_time'),
                'count_reopens': stats.get('count_reopens'),
                'count_assignments': stats.get('count_assignments'),
                'count_conversation_parts': stats.get('count_conversation_parts'),
            })
            
            # Conversation parts
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            row.update({
                'total_messages': len(parts),
                'agent_messages': sum(1 for part in parts if part.get('author', {}).get('type') == 'admin'),
                'customer_messages': sum(1 for part in parts if part.get('author', {}).get('type') == 'user'),
            })
            
            # Response time calculation
            if parts:
                first_agent_response = None
                for part in parts:
                    if part.get('author', {}).get('type') == 'admin':
                        first_agent_response = part.get('created_at')
                        break
                
                if first_agent_response:
                    response_time = first_agent_response - conv.get('created_at', 0)
                    row['first_response_time_seconds'] = response_time
                    row['first_response_time_hours'] = response_time / 3600
            
            # Resolution time
            if conv.get('state') == 'closed' and conv.get('closed_at'):
                resolution_time = conv.get('closed_at') - conv.get('created_at', 0)
                row['resolution_time_seconds'] = resolution_time
                row['resolution_time_hours'] = resolution_time / 3600
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def _prepare_metrics_dataframe(self, conversations: List[Dict]) -> pd.DataFrame:
        """Prepare metrics summary for DataFrame."""
        if not conversations:
            return pd.DataFrame()
        
        # Calculate basic metrics
        total_conversations = len(conversations)
        closed_conversations = sum(1 for conv in conversations if conv.get('state') == 'closed')
        
        # Response times
        response_times = []
        for conv in conversations:
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            for part in parts:
                if part.get('author', {}).get('type') == 'admin':
                    response_time = part.get('created_at') - conv.get('created_at', 0)
                    response_times.append(response_time)
                    break
        
        # Ratings
        ratings = [conv.get('conversation_rating') for conv in conversations if conv.get('conversation_rating')]
        
        # Source types
        source_types = [conv.get('source', {}).get('type') for conv in conversations]
        source_type_counts = pd.Series(source_types).value_counts()
        
        # Countries
        countries = []
        for conv in conversations:
            contact = conv.get('contacts', {}).get('contacts', [{}])[0] if conv.get('contacts', {}).get('contacts') else {}
            country = contact.get('location', {}).get('country')
            if country:
                countries.append(country)
        country_counts = pd.Series(countries).value_counts()
        
        metrics_data = [
            {'metric': 'Total Conversations', 'value': total_conversations, 'type': 'count'},
            {'metric': 'Closed Conversations', 'value': closed_conversations, 'type': 'count'},
            {'metric': 'Resolution Rate', 'value': (closed_conversations / total_conversations * 100) if total_conversations > 0 else 0, 'type': 'percentage'},
            {'metric': 'Average Response Time (hours)', 'value': np.mean(response_times) / 3600 if response_times else 0, 'type': 'time'},
            {'metric': 'Median Response Time (hours)', 'value': np.median(response_times) / 3600 if response_times else 0, 'type': 'time'},
            {'metric': 'Average Rating', 'value': np.mean(ratings) if ratings else 0, 'type': 'rating'},
            {'metric': 'Median Rating', 'value': np.median(ratings) if ratings else 0, 'type': 'rating'},
        ]
        
        # Add source type breakdown
        for source_type, count in source_type_counts.items():
            metrics_data.append({
                'metric': f'Conversations via {source_type.title()}', 
                'value': count, 
                'type': 'count'
            })
        
        # Add top countries
        for country, count in country_counts.head(10).items():
            metrics_data.append({
                'metric': f'Conversations from {country}', 
                'value': count, 
                'type': 'count'
            })
        
        return pd.DataFrame(metrics_data)
    
    def _prepare_time_analysis_dataframe(self, conversations: List[Dict]) -> pd.DataFrame:
        """Prepare time-based analysis for DataFrame."""
        if not conversations:
            return pd.DataFrame()
        
        time_data = []
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                dt = datetime.fromtimestamp(created_at)
                time_data.append({
                    'conversation_id': conv.get('id'),
                    'date': dt.date(),
                    'hour': dt.hour,
                    'day_of_week': dt.strftime('%A'),
                    'week': dt.strftime('%Y-W%U'),
                    'month': dt.strftime('%Y-%m'),
                    'quarter': f"{dt.year}-Q{(dt.month-1)//3+1}",
                    'state': conv.get('state'),
                    'source_type': conv.get('source', {}).get('type'),
                })
        
        return pd.DataFrame(time_data)
    
    def _prepare_topic_analysis_dataframe(self, conversations: List[Dict]) -> pd.DataFrame:
        """Prepare topic analysis for DataFrame."""
        if not conversations:
            return pd.DataFrame()
        
        topic_data = []
        
        for conv in conversations:
            text = self._extract_conversation_text(conv)
            topics = self._categorize_conversation(text)
            
            topic_data.append({
                'conversation_id': conv.get('id'),
                'primary_topic': topics.get('primary', 'other'),
                'secondary_topics': ', '.join(topics.get('secondary', [])),
                'is_billing_related': topics.get('billing', False),
                'is_technical_issue': topics.get('technical', False),
                'is_product_question': topics.get('product', False),
                'is_account_related': topics.get('account', False),
                'text_length': len(text),
                'word_count': len(text.split()),
            })
        
        return pd.DataFrame(topic_data)
    
    def _prepare_agent_performance_dataframe(self, conversations: List[Dict]) -> pd.DataFrame:
        """Prepare agent performance analysis for DataFrame."""
        if not conversations:
            return pd.DataFrame()
        
        agent_data = {}
        
        for conv in conversations:
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            
            for part in parts:
                author = part.get('author', {})
                if author.get('type') == 'admin':
                    agent_email = author.get('email', 'unknown')
                    
                    if agent_email not in agent_data:
                        agent_data[agent_email] = {
                            'agent_email': agent_email,
                            'total_responses': 0,
                            'conversations_handled': set(),
                            'response_times': [],
                            'ratings': []
                        }
                    
                    agent_data[agent_email]['total_responses'] += 1
                    agent_data[agent_email]['conversations_handled'].add(conv.get('id'))
                    
                    # Response time
                    response_time = part.get('created_at') - conv.get('created_at', 0)
                    agent_data[agent_email]['response_times'].append(response_time)
                    
                    # Rating
                    rating = conv.get('conversation_rating')
                    if rating:
                        agent_data[agent_email]['ratings'].append(rating)
        
        # Convert to DataFrame
        performance_data = []
        for agent_email, data in agent_data.items():
            performance_data.append({
                'agent_email': agent_email,
                'total_responses': data['total_responses'],
                'conversations_handled': len(data['conversations_handled']),
                'average_response_time_hours': np.mean(data['response_times']) / 3600 if data['response_times'] else 0,
                'median_response_time_hours': np.median(data['response_times']) / 3600 if data['response_times'] else 0,
                'average_rating': np.mean(data['ratings']) if data['ratings'] else 0,
                'total_ratings': len(data['ratings'])
            })
        
        return pd.DataFrame(performance_data)
    
    def _prepare_satisfaction_dataframe(self, conversations: List[Dict]) -> pd.DataFrame:
        """Prepare customer satisfaction analysis for DataFrame."""
        if not conversations:
            return pd.DataFrame()
        
        satisfaction_data = []
        
        for conv in conversations:
            rating = conv.get('conversation_rating')
            if rating:
                contact = conv.get('contacts', {}).get('contacts', [{}])[0] if conv.get('contacts', {}).get('contacts') else {}
                
                satisfaction_data.append({
                    'conversation_id': conv.get('id'),
                    'rating': rating,
                    'rating_category': self._categorize_rating(rating),
                    'source_type': conv.get('source', {}).get('type'),
                    'country': contact.get('location', {}).get('country'),
                    'user_tier': contact.get('custom_attributes', {}).get('tier'),
                    'created_at': self._format_timestamp(conv.get('created_at')),
                    'state': conv.get('state'),
                })
        
        return pd.DataFrame(satisfaction_data)
    
    def _prepare_executive_summary_dataframe(self, analysis_results: Any) -> pd.DataFrame:
        """Prepare executive summary for DataFrame."""
        summary_data = []
        
        if hasattr(analysis_results, 'executive_summary'):
            summary = analysis_results.executive_summary
            if isinstance(summary, dict):
                for key, value in summary.items():
                    summary_data.append({
                        'metric': key.replace('_', ' ').title(),
                        'value': value,
                        'category': 'executive_summary'
                    })
        
        return pd.DataFrame(summary_data)
    
    def _prepare_analysis_metrics_dataframe(self, analysis_results: Any) -> pd.DataFrame:
        """Prepare analysis metrics for DataFrame."""
        metrics_data = []
        
        # Volume metrics
        if hasattr(analysis_results, 'volume'):
            volume = analysis_results.volume
            metrics_data.extend([
                {'metric': 'Total Conversations', 'value': volume.total_conversations, 'category': 'volume'},
                {'metric': 'AI Resolution Rate', 'value': volume.ai_resolution_rate, 'category': 'volume'},
            ])
        
        # Efficiency metrics
        if hasattr(analysis_results, 'efficiency'):
            efficiency = analysis_results.efficiency
            metrics_data.extend([
                {'metric': 'Median Response Time (hours)', 'value': efficiency.median_first_response_seconds / 3600 if efficiency.median_first_response_seconds else 0, 'category': 'efficiency'},
                {'metric': 'Resolution Rate', 'value': efficiency.resolution_rate, 'category': 'efficiency'},
            ])
        
        # Satisfaction metrics
        if hasattr(analysis_results, 'satisfaction'):
            satisfaction = analysis_results.satisfaction
            metrics_data.extend([
                {'metric': 'Overall CSAT', 'value': satisfaction.overall_csat, 'category': 'satisfaction'},
                {'metric': 'Positive Sentiment', 'value': satisfaction.positive_sentiment_count, 'category': 'satisfaction'},
                {'metric': 'Negative Sentiment', 'value': satisfaction.negative_sentiment_count, 'category': 'satisfaction'},
            ])
        
        return pd.DataFrame(metrics_data)
    
    def _prepare_trends_dataframe(self, analysis_results: Any) -> pd.DataFrame:
        """Prepare trends data for DataFrame."""
        trends_data = []
        
        if hasattr(analysis_results, 'key_trends'):
            for trend in analysis_results.key_trends:
                trends_data.append({
                    'trend_name': trend.get('name', ''),
                    'description': trend.get('description', ''),
                    'type': trend.get('type', ''),
                    'significance': trend.get('significance', ''),
                })
        
        return pd.DataFrame(trends_data)
    
    def _prepare_quotes_dataframe(self, analysis_results: Any) -> pd.DataFrame:
        """Prepare customer quotes for DataFrame."""
        quotes_data = []
        
        if hasattr(analysis_results, 'customer_quotes'):
            for quote in analysis_results.customer_quotes:
                quotes_data.append({
                    'conversation_id': quote.get('conversation_id', ''),
                    'quote': quote.get('quote', ''),
                    'context': quote.get('context', ''),
                    'significance': quote.get('significance', ''),
                })
        
        return pd.DataFrame(quotes_data)
    
    def _prepare_recommendations_dataframe(self, analysis_results: Any) -> pd.DataFrame:
        """Prepare recommendations for DataFrame."""
        recommendations_data = []
        
        if hasattr(analysis_results, 'recommendations'):
            for i, rec in enumerate(analysis_results.recommendations):
                recommendations_data.append({
                    'priority': i + 1,
                    'recommendation': rec,
                    'category': 'general'
                })
        
        return pd.DataFrame(recommendations_data)
    
    # Helper methods
    def _format_timestamp(self, timestamp: Optional[int]) -> str:
        """Format timestamp to readable string."""
        if not timestamp:
            return ''
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    def _extract_conversation_text(self, conversation: Dict) -> str:
        """Extract all text from a conversation."""
        texts = []
        
        # Source body
        source_body = conversation.get('source', {}).get('body', '')
        if source_body:
            texts.append(source_body)
        
        # Conversation parts
        parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            part_body = part.get('body', '')
            if part_body:
                texts.append(part_body)
        
        return ' '.join(texts)
    
    def _categorize_conversation(self, text: str) -> Dict[str, Any]:
        """Categorize conversation based on text content."""
        text_lower = text.lower()
        
        categories = {
            'billing': any(word in text_lower for word in ['billing', 'payment', 'charge', 'invoice', 'subscription']),
            'technical': any(word in text_lower for word in ['bug', 'error', 'issue', 'problem', 'not working']),
            'product': any(word in text_lower for word in ['feature', 'how to', 'tutorial', 'guide']),
            'account': any(word in text_lower for word in ['account', 'login', 'password', 'profile', 'settings'])
        }
        
        # Determine primary category
        primary = 'other'
        for category, is_match in categories.items():
            if is_match:
                primary = category
                break
        
        # Secondary categories
        secondary = [cat for cat, is_match in categories.items() if is_match and cat != primary]
        
        return {
            'primary': primary,
            'secondary': secondary,
            **categories
        }
    
    def _categorize_rating(self, rating: float) -> str:
        """Categorize rating into text categories."""
        if rating >= 4.5:
            return 'Excellent'
        elif rating >= 4.0:
            return 'Good'
        elif rating >= 3.0:
            return 'Average'
        elif rating >= 2.0:
            return 'Poor'
        else:
            return 'Very Poor'
    
    def _detect_technical_patterns(self, text: str) -> Dict[str, Any]:
        """Detect technical troubleshooting patterns in conversation text."""
        import re
        
        text_lower = text.lower()
        patterns = {
            'cache_clear': False,
            'browser_switch': False,
            'connection_issue': False,
            'escalation': False,
            'product_issue': False,
            'keywords': []
        }
        
        # Cache clearing patterns
        cache_patterns = [
            'clear cache', 'clear cookies', 'ctrl+shift+delete', 'ctrl shift delete',
            'hard refresh', 'cache', 'cookies', 'browser cache', 'clear browsing data',
            'incognito', 'private browsing', 'clear history'
        ]
        
        for pattern in cache_patterns:
            if pattern in text_lower:
                patterns['cache_clear'] = True
                patterns['keywords'].append(pattern)
                break
        
        # Browser switching patterns
        browser_patterns = [
            'different browser', 'try chrome', 'try firefox', 'try safari', 'try edge',
            'switch browser', 'another browser', 'incognito mode', 'private window',
            'browser issue', 'browser problem', 'update browser', 'browser version'
        ]
        
        for pattern in browser_patterns:
            if pattern in text_lower:
                patterns['browser_switch'] = True
                patterns['keywords'].append(pattern)
                break
        
        # Connection issues
        connection_patterns = [
            'internet connection', 'wifi', 'network', 'connectivity', 'connection issue',
            'slow connection', 'connection problem', 'offline', 'not loading',
            'timeout', 'connection error', 'network error', 'dns', 'proxy'
        ]
        
        for pattern in connection_patterns:
            if pattern in text_lower:
                patterns['connection_issue'] = True
                patterns['keywords'].append(pattern)
                break
        
        # Escalation patterns
        escalation_patterns = [
            '@dae-ho', '@hilary', '@max', '@max jackson', 'escalate', 'escalation',
            'note to', 'cc:', 'forward to', 'assign to', 'hand off', 'transfer',
            'supervisor', 'manager', 'lead', 'senior'
        ]
        
        for pattern in escalation_patterns:
            if pattern in text_lower:
                patterns['escalation'] = True
                patterns['keywords'].append(pattern)
                break
        
        # Product issues (generic)
        product_patterns = [
            'bug', 'error', 'issue', 'problem', 'not working', 'broken', 'glitch',
            'feature', 'functionality', 'sprite', 'gamma', 'app', 'platform',
            'technical issue', 'system error', 'application error'
        ]
        
        for pattern in product_patterns:
            if pattern in text_lower:
                patterns['product_issue'] = True
                patterns['keywords'].append(pattern)
                break
        
        return patterns
    
    def _detect_escalations(self, text: str) -> Dict[str, Any]:
        """Detect escalation patterns and who was escalated to."""
        import re
        
        text_lower = text.lower()
        escalations = {
            'escalated_to': [],
            'notes': ''
        }
        
        # Look for specific names
        names = ['dae-ho', 'hilary', 'max', 'max jackson']
        for name in names:
            if name in text_lower:
                escalations['escalated_to'].append(name.title())
        
        # Look for escalation notes
        escalation_indicators = ['note to', 'cc:', 'forward to', 'assign to', 'escalate']
        for indicator in escalation_indicators:
            if indicator in text_lower:
                # Try to extract the note content
                pattern = rf'{indicator}[^.!?]*[.!?]'
                matches = re.findall(pattern, text_lower)
                if matches:
                    escalations['notes'] = matches[0]
                break
        
        return escalations
    
    def _extract_agent_actions(self, conversation: Dict) -> Dict[str, Any]:
        """Extract agent actions and responses from conversation."""
        actions = {
            'actions': [],
            'resolution_notes': '',
            'customer_response': ''
        }
        
        parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
        
        for part in parts:
            author = part.get('author', {})
            if author.get('type') == 'admin':
                body = part.get('body', '')
                if body:
                    # Look for common agent actions
                    body_lower = body.lower()
                    
                    if any(word in body_lower for word in ['clear', 'cache', 'cookies']):
                        actions['actions'].append('cache_clear_instruction')
                    if any(word in body_lower for word in ['browser', 'chrome', 'firefox', 'safari']):
                        actions['actions'].append('browser_switch_instruction')
                    if any(word in body_lower for word in ['connection', 'wifi', 'network']):
                        actions['actions'].append('connection_troubleshooting')
                    if any(word in body_lower for word in ['escalate', 'note to', 'assign']):
                        actions['actions'].append('escalation')
                    
                    # Store the last agent message as resolution notes
                    actions['resolution_notes'] = body[:500]  # Truncate for readability
        
        # Look for customer responses after agent actions
        for i, part in enumerate(parts):
            author = part.get('author', {})
            if author.get('type') == 'user' and i > 0:
                # Check if previous part was from admin
                prev_part = parts[i-1]
                if prev_part.get('author', {}).get('type') == 'admin':
                    actions['customer_response'] = part.get('body', '')[:200]
                    break
        
        return actions

