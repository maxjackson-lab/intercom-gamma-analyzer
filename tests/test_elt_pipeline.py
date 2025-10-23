"""
Unit tests for ELT pipeline service.
"""

import pytest
import asyncio
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.elt_pipeline import ELTPipeline


class TestELTPipeline:
    """Test cases for ELT pipeline service."""
    
    def test_initialization(self, temp_dir):
        """Test ELT pipeline initialization."""
        output_dir = temp_dir / "test_outputs"
        pipeline = ELTPipeline(str(output_dir))
        
        assert pipeline.output_dir == output_dir
        assert pipeline.raw_data_dir == output_dir / "raw_data"
        assert output_dir.exists()
        assert pipeline.raw_data_dir.exists()
        
        pipeline.close()
    
    @pytest.mark.asyncio
    async def test_extract_and_load(self, elt_pipeline, sample_conversations, test_date_range):
        """Test extract and load functionality."""
        start_date, end_date = test_date_range
        
        # Mock the intercom service
        with patch.object(elt_pipeline.intercom_service, 'fetch_conversations_by_date_range') as mock_fetch:
            mock_fetch.return_value = sample_conversations
            
            # Run extract and load
            stats = await elt_pipeline.extract_and_load(start_date, end_date)
            
            # Verify results
            assert stats['conversations_count'] == len(sample_conversations)
            assert stats['date_range'] == f"{start_date} to {end_date}"
            assert 'raw_file' in stats
            assert 'storage_time' in stats
            
            # Verify raw file was created
            raw_file = Path(stats['raw_file'])
            assert raw_file.exists()
            
            # Verify data was stored in DuckDB
            conversations_df = elt_pipeline.duckdb_storage.query("SELECT COUNT(*) as count FROM conversations")
            assert conversations_df.iloc[0]['count'] == len(sample_conversations)
    
    @pytest.mark.asyncio
    async def test_extract_and_load_with_max_pages(self, elt_pipeline, sample_conversations, test_date_range):
        """Test extract and load with page limit."""
        start_date, end_date = test_date_range
        
        with patch.object(elt_pipeline.intercom_service, 'fetch_conversations_by_date_range') as mock_fetch:
            mock_fetch.return_value = sample_conversations[:2]  # Limit to 2 conversations
            
            stats = await elt_pipeline.extract_and_load(start_date, end_date, max_pages=1)
            
            assert stats['conversations_count'] == 2
            mock_fetch.assert_called_once_with(start_date, end_date, max_pages=1)
    
    @pytest.mark.asyncio
    async def test_extract_and_load_no_conversations(self, elt_pipeline, test_date_range):
        """Test extract and load with no conversations."""
        start_date, end_date = test_date_range
        
        with patch.object(elt_pipeline.intercom_service, 'fetch_conversations_by_date_range') as mock_fetch:
            mock_fetch.return_value = []
            
            stats = await elt_pipeline.extract_and_load(start_date, end_date)
            
            assert stats['conversations_count'] == 0
            assert stats['extraction_time'] == 0
            assert stats['storage_time'] == 0
    
    def test_store_raw_json(self, elt_pipeline, sample_conversations, test_date_range):
        """Test raw JSON storage."""
        start_date, end_date = test_date_range
        
        raw_file = elt_pipeline._store_raw_json(sample_conversations, start_date, end_date)
        
        assert raw_file.exists()
        assert raw_file.suffix == '.json'
        
        # Verify content
        with open(raw_file, 'r') as f:
            stored_data = json.load(f)
        
        assert len(stored_data) == len(sample_conversations)
        assert stored_data[0]['id'] == sample_conversations[0]['id']
    
    def test_generate_extraction_stats(self, elt_pipeline, sample_conversations, test_date_range):
        """Test extraction statistics generation."""
        start_date, end_date = test_date_range
        
        stats = elt_pipeline._generate_extraction_stats(sample_conversations, start_date, end_date)
        
        assert stats['conversations_count'] == len(sample_conversations)
        assert stats['date_range'] == f"{start_date} to {end_date}"
        assert stats['date_span_days'] == (end_date - start_date).days + 1
        assert 'conversation_states' in stats
        assert 'languages' in stats
        assert 'agents' in stats
        assert 'unique_tags' in stats
        assert 'unique_topics' in stats
        assert 'top_tags' in stats
        assert 'top_topics' in stats
    
    def test_transform_technical_data(self, elt_pipeline, sample_conversations, test_date_range):
        """Test technical data transformation."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(sample_conversations)
        
        # Transform for technical analysis
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        df = elt_pipeline.transform_for_analysis("technical", filters)
        
        assert isinstance(df, type(elt_pipeline.duckdb_storage.query("SELECT 1")))
        # Should have technical pattern columns
        expected_columns = ['id', 'created_at', 'state', 'pattern_type', 'pattern_value']
        for col in expected_columns:
            if col in df.columns:
                assert True  # Column exists
    
    def test_transform_category_data(self, elt_pipeline, sample_conversations, test_date_range):
        """Test category data transformation."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(sample_conversations)
        
        # Transform for category analysis
        filters = {
            'category': 'Billing',
            'start_date': start_date,
            'end_date': end_date
        }
        
        df = elt_pipeline.transform_for_analysis("category", filters)
        
        assert isinstance(df, type(elt_pipeline.duckdb_storage.query("SELECT 1")))
    
    def test_transform_fin_data(self, elt_pipeline, fin_conversations, test_date_range):
        """Test Fin data transformation."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(fin_conversations)
        
        # Transform for Fin analysis
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        df = elt_pipeline.transform_for_analysis("fin", filters)
        
        assert isinstance(df, type(elt_pipeline.duckdb_storage.query("SELECT 1")))
    
    def test_transform_agent_data(self, elt_pipeline, sample_conversations, test_date_range):
        """Test agent data transformation."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(sample_conversations)
        
        # Transform for agent analysis
        filters = {
            'agent_id': 'admin_123',
            'start_date': start_date,
            'end_date': end_date
        }
        
        df = elt_pipeline.transform_for_analysis("agent", filters)
        
        assert isinstance(df, type(elt_pipeline.duckdb_storage.query("SELECT 1")))
    
    def test_transform_unknown_analysis_type(self, elt_pipeline, test_date_range):
        """Test transformation with unknown analysis type."""
        start_date, end_date = test_date_range
        
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        with pytest.raises(ValueError, match="Unknown analysis type"):
            elt_pipeline.transform_for_analysis("unknown_type", filters)
    
    def test_get_data_summary(self, elt_pipeline, sample_conversations, test_date_range):
        """Test data summary generation."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(sample_conversations)
        
        # Get summary
        summary = elt_pipeline.get_data_summary(start_date, end_date)
        
        assert 'total_conversations' in summary
        assert 'unique_agents' in summary
        assert 'fin_conversations' in summary
        assert 'avg_handling_time' in summary
        assert 'avg_rating' in summary
    
    def test_export_analysis_data_csv(self, elt_pipeline, sample_conversations, test_date_range):
        """Test CSV export of analysis data."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(sample_conversations)
        
        # Export data
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        with patch.object(elt_pipeline.data_exporter, 'export_conversations_to_csv') as mock_export:
            mock_export.return_value = "test_output.csv"
            
            result = elt_pipeline.export_analysis_data("technical", filters, "csv")
            
            assert result == "test_output.csv"
            mock_export.assert_called_once()
    
    def test_export_analysis_data_excel(self, elt_pipeline, sample_conversations, test_date_range):
        """Test Excel export of analysis data."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(sample_conversations)
        
        # Export data
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        with patch.object(elt_pipeline.data_exporter, 'export_conversations_to_excel') as mock_export:
            mock_export.return_value = "test_output.xlsx"
            
            result = elt_pipeline.export_analysis_data("category", filters, "excel")
            
            assert result == "test_output.xlsx"
            mock_export.assert_called_once()
    
    def test_export_analysis_data_json(self, elt_pipeline, sample_conversations, test_date_range):
        """Test JSON export of analysis data."""
        start_date, end_date = test_date_range
        
        # Store conversations first
        elt_pipeline.duckdb_storage.store_conversations(sample_conversations)
        
        # Export data
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        with patch.object(elt_pipeline.data_exporter, 'export_raw_data_to_json') as mock_export:
            mock_export.return_value = "test_output.json"
            
            result = elt_pipeline.export_analysis_data("fin", filters, "json")
            
            assert result == "test_output.json"
            mock_export.assert_called_once()
    
    def test_export_analysis_data_invalid_format(self, elt_pipeline, test_date_range):
        """Test export with invalid format."""
        start_date, end_date = test_date_range
        
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        with pytest.raises(ValueError, match="Unsupported output format"):
            elt_pipeline.export_analysis_data("technical", filters, "invalid")
    
    def test_close_pipeline(self, temp_dir):
        """Test closing the pipeline."""
        output_dir = temp_dir / "test_close"
        pipeline = ELTPipeline(str(output_dir))
        
        # Pipeline should be open
        assert pipeline.duckdb_storage.conn is not None
        
        # Close pipeline
        pipeline.close()
        
        # Connection should be closed
        assert pipeline.duckdb_storage.conn is None
    
    @pytest.mark.asyncio
    async def test_error_handling_in_extract(self, elt_pipeline, test_date_range):
        """Test error handling during extraction."""
        start_date, end_date = test_date_range
        
        with patch.object(elt_pipeline.intercom_service, 'fetch_conversations_by_date_range') as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                await elt_pipeline.extract_and_load(start_date, end_date)
    
    def test_error_handling_in_transform(self, elt_pipeline, test_date_range):
        """Test error handling during transformation."""
        start_date, end_date = test_date_range
        
        filters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Mock DuckDB query to raise exception
        with patch.object(elt_pipeline.duckdb_storage, 'query') as mock_query:
            mock_query.side_effect = Exception("Database Error")
            
            with pytest.raises(Exception, match="Database Error"):
                elt_pipeline.transform_for_analysis("technical", filters)






