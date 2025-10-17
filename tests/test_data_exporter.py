"""
Unit tests for data exporter service.
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from services.data_exporter import DataExporter


class TestDataExporter:
    """Test cases for data exporter service."""
    
    def test_initialization(self, temp_dir):
        """Test data exporter initialization."""
        exporter = DataExporter(str(temp_dir))
        
        assert exporter.output_dir == temp_dir
        assert temp_dir.exists()
    
    def test_export_conversations_to_csv(self, temp_dir, sample_conversations):
        """Test CSV export of conversations."""
        exporter = DataExporter(str(temp_dir))
        
        filepath = exporter.export_conversations_to_csv(sample_conversations, "test_export")
        
        assert Path(filepath).exists()
        assert filepath.endswith('.csv')
        
        # Verify CSV content
        df = pd.read_csv(filepath)
        assert len(df) == len(sample_conversations)
        assert 'conversation_id' in df.columns
        assert 'created_at' in df.columns
        assert 'state' in df.columns
    
    def test_export_conversations_to_excel(self, temp_dir, sample_conversations):
        """Test Excel export of conversations."""
        exporter = DataExporter(str(temp_dir))
        
        filepath = exporter.export_conversations_to_excel(sample_conversations, "test_export")
        
        assert Path(filepath).exists()
        assert filepath.endswith('.xlsx')
        
        # Verify Excel content
        df = pd.read_excel(filepath)
        assert len(df) == len(sample_conversations)
        assert 'conversation_id' in df.columns
    
    def test_export_raw_data_to_json(self, temp_dir, sample_conversations):
        """Test JSON export of raw data."""
        exporter = DataExporter(str(temp_dir))
        
        filepath = exporter.export_raw_data_to_json(sample_conversations, "test_export")
        
        assert Path(filepath).exists()
        assert filepath.endswith('.json')
        
        # Verify JSON content
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert len(data) == len(sample_conversations)
        assert data[0]['id'] == sample_conversations[0]['id']
    
    def test_export_to_parquet(self, temp_dir, sample_conversations):
        """Test Parquet export."""
        exporter = DataExporter(str(temp_dir))
        
        filepath = exporter.export_to_parquet(sample_conversations, "test_export")
        
        assert Path(filepath).exists()
        assert filepath.endswith('.parquet')
        
        # Verify Parquet content
        df = pd.read_parquet(filepath)
        assert len(df) == len(sample_conversations)
    
    def test_export_technical_troubleshooting_analysis(self, temp_dir, technical_troubleshooting_conversations):
        """Test technical troubleshooting analysis export."""
        exporter = DataExporter(str(temp_dir))
        
        filepath = exporter.export_technical_troubleshooting_analysis(
            technical_troubleshooting_conversations, "test_tech_analysis"
        )
        
        assert Path(filepath).exists()
        assert filepath.endswith('.csv')
        
        # Verify CSV content
        df = pd.read_csv(filepath)
        assert len(df) == len(technical_troubleshooting_conversations)
        
        # Check for technical analysis columns
        expected_columns = [
            'conversation_id', 'conversation_url', 'created_at', 'state',
            'cache_clear_mentioned', 'browser_switch_mentioned', 'connection_issue_mentioned',
            'escalation_mentioned', 'primary_issue_category'
        ]
        
        for col in expected_columns:
            assert col in df.columns
    
    def test_detect_technical_patterns(self, temp_dir):
        """Test technical pattern detection."""
        exporter = DataExporter(str(temp_dir))
        
        # Test cache clearing pattern
        text_with_cache = "Please try clearing your browser cache and cookies"
        patterns = exporter._detect_technical_patterns(text_with_cache)
        
        assert patterns['cache_clear'] is True
        assert 'clear cache' in patterns['keywords']
        
        # Test browser switching pattern
        text_with_browser = "Try using a different browser like Chrome"
        patterns = exporter._detect_technical_patterns(text_with_browser)
        
        assert patterns['browser_switch'] is True
        assert 'different browser' in patterns['keywords']
        
        # Test connection issue pattern
        text_with_connection = "Check your internet connection and wifi"
        patterns = exporter._detect_technical_patterns(text_with_connection)
        
        assert patterns['connection_issue'] is True
        assert 'internet connection' in patterns['keywords']
        
        # Test escalation pattern
        text_with_escalation = "Let me escalate this to @Hilary for review"
        patterns = exporter._detect_technical_patterns(text_with_escalation)
        
        assert patterns['escalation'] is True
        assert 'escalate' in patterns['keywords']
    
    def test_detect_escalations(self, temp_dir):
        """Test escalation detection."""
        exporter = DataExporter(str(temp_dir))
        
        # Test escalation to Hilary
        text_with_hilary = "Forwarding this to @Hilary for assistance"
        escalations = exporter._detect_escalations(text_with_hilary)
        
        assert 'Hilary' in escalations['escalated_to']
        
        # Test escalation to Dae-Ho
        text_with_daeho = "Let me get @Dae-Ho to look at this"
        escalations = exporter._detect_escalations(text_with_daeho)
        
        assert 'Dae-Ho' in escalations['escalated_to']
        
        # Test escalation to Max
        text_with_max = "I'll escalate this to @Max Jackson"
        escalations = exporter._detect_escalations(text_with_max)
        
        assert 'Max Jackson' in escalations['escalated_to']
    
    def test_extract_agent_actions(self, temp_dir, sample_conversation):
        """Test agent action extraction."""
        exporter = DataExporter(str(temp_dir))
        
        actions = exporter._extract_agent_actions(sample_conversation)
        
        assert 'actions' in actions
        assert 'resolution_notes' in actions
        assert 'customer_response' in actions
        assert isinstance(actions['actions'], list)
    
    def test_extract_conversation_text(self, temp_dir, sample_conversation):
        """Test conversation text extraction."""
        exporter = DataExporter(str(temp_dir))
        
        text = exporter._extract_conversation_text(sample_conversation)
        
        assert isinstance(text, str)
        assert len(text) > 0
        # Should contain text from source and conversation parts
        assert "refund" in text.lower()
    
    def test_format_timestamp(self, temp_dir):
        """Test timestamp formatting."""
        exporter = DataExporter(str(temp_dir))
        
        # Test Unix timestamp
        unix_ts = 1699123456
        formatted = exporter._format_timestamp(unix_ts)
        assert isinstance(formatted, str)
        
        # Test None
        formatted = exporter._format_timestamp(None)
        assert formatted == ""
        
        # Test string timestamp
        string_ts = "2023-11-04T10:30:56Z"
        formatted = exporter._format_timestamp(string_ts)
        assert isinstance(formatted, str)
    
    def test_prepare_conversations_dataframe(self, temp_dir, sample_conversations):
        """Test conversation dataframe preparation."""
        exporter = DataExporter(str(temp_dir))
        
        df = exporter._prepare_conversations_dataframe(sample_conversations)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_conversations)
        
        # Check for expected columns
        expected_columns = [
            'conversation_id', 'created_at', 'state', 'priority',
            'admin_assignee_id', 'language', 'conversation_rating',
            'ai_agent_participated', 'tags', 'topics'
        ]
        
        for col in expected_columns:
            assert col in df.columns
    
    def test_prepare_technical_dataframe(self, temp_dir, technical_troubleshooting_conversations):
        """Test technical dataframe preparation."""
        exporter = DataExporter(str(temp_dir))
        
        df = exporter._prepare_technical_dataframe(technical_troubleshooting_conversations)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(technical_troubleshooting_conversations)
        
        # Check for technical analysis columns
        expected_columns = [
            'conversation_id', 'cache_clear_mentioned', 'browser_switch_mentioned',
            'connection_issue_mentioned', 'escalation_mentioned', 'primary_issue_category'
        ]
        
        for col in expected_columns:
            assert col in df.columns
    
    def test_export_with_empty_data(self, temp_dir):
        """Test export with empty data."""
        exporter = DataExporter(str(temp_dir))
        
        # Test CSV export with empty list
        filepath = exporter.export_conversations_to_csv([], "empty_test")
        assert Path(filepath).exists()
        
        df = pd.read_csv(filepath)
        assert len(df) == 0
    
    def test_export_with_missing_fields(self, temp_dir):
        """Test export with conversations missing some fields."""
        exporter = DataExporter(str(temp_dir))
        
        # Create conversation with missing fields
        incomplete_conversation = {
            "id": "incomplete_123",
            "created_at": 1699123456,
            "state": "closed"
            # Missing many fields
        }
        
        filepath = exporter.export_conversations_to_csv([incomplete_conversation], "incomplete_test")
        assert Path(filepath).exists()
        
        df = pd.read_csv(filepath)
        assert len(df) == 1
        assert df.iloc[0]['conversation_id'] == "incomplete_123"
    
    def test_technical_pattern_detection_edge_cases(self, temp_dir):
        """Test technical pattern detection with edge cases."""
        exporter = DataExporter(str(temp_dir))
        
        # Test empty text
        patterns = exporter._detect_technical_patterns("")
        assert patterns['cache_clear'] is False
        assert patterns['browser_switch'] is False
        assert patterns['connection_issue'] is False
        assert patterns['escalation'] is False
        assert len(patterns['keywords']) == 0
        
        # Test text with no patterns
        patterns = exporter._detect_technical_patterns("This is just regular text")
        assert patterns['cache_clear'] is False
        assert patterns['browser_switch'] is False
        assert patterns['connection_issue'] is False
        assert patterns['escalation'] is False
        
        # Test text with multiple patterns
        text_with_multiple = "Clear your cache and try a different browser with better internet connection"
        patterns = exporter._detect_technical_patterns(text_with_multiple)
        assert patterns['cache_clear'] is True
        assert patterns['browser_switch'] is True
        assert patterns['connection_issue'] is True
    
    def test_escalation_detection_edge_cases(self, temp_dir):
        """Test escalation detection with edge cases."""
        exporter = DataExporter(str(temp_dir))
        
        # Test empty text
        escalations = exporter._detect_escalations("")
        assert len(escalations['escalated_to']) == 0
        assert escalations['notes'] == ""
        
        # Test text with no escalations
        escalations = exporter._detect_escalations("This is just regular text")
        assert len(escalations['escalated_to']) == 0
        
        # Test text with multiple escalations
        text_with_multiple = "Let me get @Hilary and @Dae-Ho to look at this"
        escalations = exporter._detect_escalations(text_with_multiple)
        assert len(escalations['escalated_to']) == 2
        assert 'Hilary' in escalations['escalated_to']
        assert 'Dae-Ho' in escalations['escalated_to']
    
    def test_file_naming(self, temp_dir, sample_conversations):
        """Test that exported files have correct naming."""
        exporter = DataExporter(str(temp_dir))
        
        # Test CSV naming
        csv_path = exporter.export_conversations_to_csv(sample_conversations, "test_name")
        assert "test_name" in csv_path
        assert csv_path.endswith('.csv')
        
        # Test Excel naming
        excel_path = exporter.export_conversations_to_excel(sample_conversations, "test_name")
        assert "test_name" in excel_path
        assert excel_path.endswith('.xlsx')
        
        # Test JSON naming
        json_path = exporter.export_raw_data_to_json(sample_conversations, "test_name")
        assert "test_name" in json_path
        assert json_path.endswith('.json')
        
        # Test Parquet naming
        parquet_path = exporter.export_to_parquet(sample_conversations, "test_name")
        assert "test_name" in parquet_path
        assert parquet_path.endswith('.parquet')
    
    def test_output_directory_creation(self, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        non_existent_dir = temp_dir / "new_output_dir"
        
        # Directory shouldn't exist yet
        assert not non_existent_dir.exists()
        
        # Create exporter - should create directory
        exporter = DataExporter(str(non_existent_dir))
        
        # Directory should now exist
        assert non_existent_dir.exists()






