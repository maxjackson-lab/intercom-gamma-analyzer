"""
ELT Pipeline Service for Intercom Analysis Tool.
Extract-Load-Transform pipeline for processing conversation data.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import json
import pandas as pd

from src.services.intercom_sdk_service import IntercomSDKService
from src.services.duckdb_storage import DuckDBStorage
from src.services.data_exporter import DataExporter

logger = logging.getLogger(__name__)


class ELTPipeline:
    """Extract-Load-Transform pipeline for conversation data."""
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.intercom_service = IntercomSDKService()
        self.duckdb_storage = DuckDBStorage(self.output_dir / "conversations.duckdb")
        self.data_exporter = DataExporter()

        # Raw data storage
        self.raw_data_dir = self.output_dir / "raw_data"
        self.raw_data_dir.mkdir(exist_ok=True)
    
    async def extract_and_load(self, start_date: Union[date, datetime], end_date: Union[date, datetime], max_pages: Optional[int] = None) -> Dict[str, Any]:
        """
        Extract conversations from Intercom and load into DuckDB.

        Args:
            start_date: Start date for extraction
            end_date: End date for extraction
            max_pages: Maximum pages to fetch (for testing)

        Returns:
            Dictionary with extraction statistics
        """
        logger.info(f"Starting ELT pipeline: {start_date} to {end_date}")

        # Step 1: Extract from Intercom
        extraction_start = datetime.now()
        conversations = await self._extract_conversations(start_date, end_date, max_pages)
        extraction_time = (datetime.now() - extraction_start).total_seconds()

        if not conversations:
            logger.warning("No conversations found for the specified date range")
            return {
                'conversations_count': 0,
                'date_range': f"{start_date} to {end_date}",
                'extraction_time': extraction_time,
                'storage_time': 0
            }

        # Step 2: Store raw JSON (for debugging/backup)
        raw_file = self._store_raw_json(conversations, start_date, end_date)

        # Step 3: Load into DuckDB
        storage_start = datetime.now()
        self.duckdb_storage.store_conversations(conversations)
        storage_time = (datetime.now() - storage_start).total_seconds()

        # Step 4: Generate summary statistics
        stats = self._generate_extraction_stats(conversations, start_date, end_date)
        stats.update({
            'raw_file': str(raw_file),
            'extraction_time': extraction_time,
            'storage_time': storage_time
        })

        logger.info(f"ELT pipeline completed: {len(conversations)} conversations processed")
        return stats
    
    async def _extract_conversations(self, start_date: Union[date, datetime], end_date: Union[date, datetime], max_pages: Optional[int]) -> List[Dict]:
        """Extract conversations from Intercom API."""
        logger.info(f"Extracting conversations from {start_date} to {end_date}")

        # Convert date to datetime if needed
        if isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        if isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.max.time())

        # Use IntercomSDKService with max_conversations parameter
        # Convert max_pages to rough conversation estimate (50 per page)
        max_conversations = (max_pages * 50) if max_pages else None
        conversations = await self.intercom_service.fetch_conversations_by_date_range(
            start_date, end_date, max_conversations=max_conversations
        )

        logger.info(f"Extracted {len(conversations)} conversations")
        return conversations
    
    def _store_raw_json(self, conversations: List[Dict], start_date: date, end_date: date) -> Path:
        """
        Store raw JSON data for backup and debugging with optional PII redaction.

        Only stores if export_raw_data setting is enabled. When enabled, applies
        PII redaction to protect sensitive information.
        """
        from src.config.settings import settings

        if not settings.export_raw_data:
            logger.info("Raw data export disabled (export_raw_data=False)")
            # Return a placeholder path
            return self.raw_data_dir / "export_disabled.json"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_conversations_{start_date}_{end_date}_{timestamp}.json"
        filepath = self.raw_data_dir / filename

        # Apply PII redaction if enabled
        if settings.redact_sensitive_outputs:
            logger.info("Applying PII redaction to raw data export")
            from src.services.data_exporter import DataExporter
            exporter = DataExporter()
            sanitized_conversations = [exporter._sanitize_dict(conv) for conv in conversations]
            export_data = sanitized_conversations
        else:
            export_data = conversations

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Raw data stored: {filepath} (redacted={settings.redact_sensitive_outputs})")
        return filepath
    
    def _generate_extraction_stats(self, conversations: List[Dict], start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate extraction statistics."""
        stats = {
            'conversations_count': len(conversations),
            'date_range': f"{start_date} to {end_date}",
            'date_span_days': (end_date - start_date).days + 1,
            'avg_conversations_per_day': len(conversations) / max(1, (end_date - start_date).days + 1)
        }
        
        # Analyze conversation states
        states = {}
        languages = {}
        agents = {}
        tags = {}
        topics = {}
        
        for conv in conversations:
            # States
            state = conv.get('state', 'unknown')
            states[state] = states.get(state, 0) + 1
            
            # Languages
            lang = conv.get('custom_attributes', {}).get('Language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
            
            # Agents
            agent_id = conv.get('admin_assignee_id')
            if agent_id:
                agents[agent_id] = agents.get(agent_id, 0) + 1
            
            # Tags
            conv_tags = conv.get('tags', {}).get('tags', [])
            for tag in conv_tags:
                tag_name = tag.get('name', str(tag)) if isinstance(tag, dict) else str(tag)
                tags[tag_name] = tags.get(tag_name, 0) + 1
            
            # Topics
            conv_topics = conv.get('topics', {}).get('topics', [])
            for topic in conv_topics:
                topic_name = topic.get('name', str(topic)) if isinstance(topic, dict) else str(topic)
                topics[topic_name] = topics.get(topic_name, 0) + 1
        
        stats.update({
            'conversation_states': states,
            'languages': languages,
            'agents': agents,
            'unique_tags': len(tags),
            'unique_topics': len(topics),
            'top_tags': dict(sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_topics': dict(sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10])
        })
        
        return stats
    
    def transform_for_analysis(self, analysis_type: str, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Transform data for specific analysis type.
        
        Args:
            analysis_type: Type of analysis (technical, category, fin, etc.)
            filters: Filters to apply (date range, categories, etc.)
        
        Returns:
            Transformed DataFrame ready for analysis
        """
        logger.info(f"Transforming data for {analysis_type} analysis")
        
        if analysis_type == "technical":
            return self._transform_technical_data(filters)
        elif analysis_type == "category":
            return self._transform_category_data(filters)
        elif analysis_type == "fin":
            return self._transform_fin_data(filters)
        elif analysis_type == "agent":
            return self._transform_agent_data(filters)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    def _transform_technical_data(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Transform data for technical analysis."""
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        
        # Get technical patterns
        patterns_df = self.duckdb_storage.get_technical_patterns(start_date, end_date)
        
        # Get escalations
        escalations_df = self.duckdb_storage.get_escalations(start_date, end_date)
        
        # Get conversations with technical patterns
        sql = """
        SELECT
            c.*,
            tp.pattern_type,
            tp.pattern_value,
            tp.detected_keywords,
            e.escalated_to,
            e.escalation_notes
        FROM conversations c
        LEFT JOIN technical_patterns tp ON c.id = tp.conversation_id
        LEFT JOIN escalations e ON c.id = e.conversation_id
        WHERE c.created_at >= $start_date AND c.created_at <= $end_date
        AND (tp.pattern_value = true OR e.escalated_to IS NOT NULL)
        ORDER BY c.created_at DESC
        """

        return self.duckdb_storage.query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
    
    def _transform_category_data(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Transform data for category analysis."""
        category = filters.get('category')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        
        return self.duckdb_storage.get_conversations_by_category(category, start_date, end_date)
    
    def _transform_fin_data(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Transform data for Fin analysis."""
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        
        return self.duckdb_storage.get_fin_analysis(start_date, end_date)
    
    def _transform_agent_data(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Transform data for agent analysis."""
        agent_id = filters.get('agent_id')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        
        sql = """
        SELECT c.*, cc.primary_category, cc.subcategory
        FROM conversations c
        LEFT JOIN conversation_categories cc ON c.id = cc.conversation_id
        WHERE c.admin_assignee_id = $agent_id
        AND c.created_at >= $start_date
        AND c.created_at <= $end_date
        ORDER BY c.created_at DESC
        """

        return self.duckdb_storage.query(sql, {
            'agent_id': agent_id,
            'start_date': start_date,
            'end_date': end_date
        })
    
    def get_data_summary(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get summary of available data."""
        sql = """
        SELECT
            COUNT(*) as total_conversations,
            COUNT(DISTINCT admin_assignee_id) as unique_agents,
            COUNT(CASE WHEN ai_agent_participated THEN 1 END) as fin_conversations,
            AVG(handling_time) as avg_handling_time,
            AVG(conversation_rating) as avg_rating
        FROM conversations
        WHERE created_at >= $start_date AND created_at <= $end_date
        """

        summary_df = self.duckdb_storage.query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
        
        if not summary_df.empty:
            return summary_df.iloc[0].to_dict()
        else:
            return {}
    
    def export_analysis_data(self, analysis_type: str, filters: Dict[str, Any], output_format: str = "csv") -> str:
        """Export transformed data for analysis."""
        df = self.transform_for_analysis(analysis_type, filters)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{analysis_type}_analysis_{timestamp}"
        
        if output_format == "csv":
            return self.data_exporter.export_conversations_to_csv(df.to_dict('records'), filename)
        elif output_format == "excel":
            return self.data_exporter.export_conversations_to_excel(df.to_dict('records'), filename)
        elif output_format == "json":
            return self.data_exporter.export_raw_data_to_json(df.to_dict('records'), filename)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def close(self):
        """Close all connections."""
        self.duckdb_storage.close()
        logger.info("ELT pipeline closed")
