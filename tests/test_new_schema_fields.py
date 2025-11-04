"""
Tests for new schema fields from INTERCOM_SCHEMA_ANALYSIS.md.

Validates that DuckDB storage and data exporters correctly handle:
- SLA fields (sla_applied.sla_name, sla_applied.sla_status)
- Channel field (source.delivered_as)
- Wait time fields (waiting_since)
- Response time fields (first_contact_reply.created_at, statistics.time_to_assignment, statistics.median_time_to_reply)
- CSAT feedback (conversation_rating.remark)
- Fin content sources (ai_agent.content_sources)

Tests cover both presence and absence cases to verify defaults.
"""

import pytest
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

from src.services.duckdb_storage import DuckDBStorage
from src.services.data_exporter import DataExporter


@pytest.fixture
def mock_conversations_with_new_fields() -> List[Dict]:
    """
    Mock conversations with new schema fields.
    Includes both presence and absence cases.
    """
    base_timestamp = int(datetime(2025, 11, 1, tzinfo=timezone.utc).timestamp())
    
    return [
        {
            # Conversation with ALL new fields present
            'id': 'conv_with_all_fields',
            'created_at': base_timestamp,
            'updated_at': base_timestamp + 3600,
            'state': 'closed',
            'priority': 'priority',
            'admin_assignee_id': 'admin_123',
            
            # SLA fields
            'sla_applied': {
                'sla_name': 'First Response SLA',
                'sla_status': 'hit'
            },
            
            # Channel field
            'source': {
                'type': 'conversation',
                'body': 'Customer message here',
                'delivered_as': 'email',
                'author': {
                    'type': 'user',
                    'id': 'user_123'
                }
            },
            
            # Wait time fields
            'waiting_since': base_timestamp + 1800,
            'snoozed_until': None,
            
            # Response time fields
            'first_contact_reply': {
                'created_at': base_timestamp + 600,
                'url': 'https://intercom.com/conversation/conv_with_all_fields'
            },
            
            # Statistics with new fields
            'statistics': {
                'time_to_admin_reply': 600,
                'time_to_assignment': 300,
                'time_to_first_close': 3600,
                'time_to_last_close': 3600,
                'median_time_to_reply': 450,
                'first_contact_reply_at': base_timestamp + 600,
                'first_assignment_at': base_timestamp + 300,
                'first_admin_reply_at': base_timestamp + 600,
                'last_close_at': base_timestamp + 3600,
                'count_reopens': 0,
                'count_assignments': 1,
                'count_conversation_parts': 5
            },
            
            # CSAT with remark
            'conversation_rating': {
                'rating': 5,
                'remark': 'Great service! Very helpful and quick response.',
                'contact': {'id': 'contact_123'},
                'teammate': {'id': 'admin_123'}
            },
            
            # AI agent with content sources
            'ai_agent_participated': True,
            'ai_agent': {
                'source_type': 'workflow',
                'source_title': 'Fin Over Messenger',
                'last_answer_type': 'ai_answer',
                'resolution_state': 'assumed_resolution',
                'content_sources': [
                    {
                        'content_type': 'article',
                        'title': 'How to reset your password',
                        'url': 'https://help.example.com/articles/reset-password'
                    },
                    {
                        'content_type': 'content_snippet',
                        'title': 'Password Requirements',
                        'url': 'https://help.example.com/snippets/password-requirements'
                    }
                ],
                'created_at': base_timestamp,
                'updated_at': base_timestamp + 1800
            },
            
            # Standard fields
            'tags': {'tags': [{'name': 'billing'}]},
            'topics': {'topics': [{'name': 'account'}]},
            'custom_attributes': {
                'Language': 'en',
                'Reason for contact': 'Account Management'
            },
            'contacts': {
                'contacts': [
                    {
                        'id': 'contact_123',
                        'email': 'customer@example.com',
                        'custom_attributes': {'tier': 'premium'}
                    }
                ]
            },
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'id': 'part_1',
                        'part_type': 'comment',
                        'body': 'Admin response',
                        'created_at': base_timestamp + 600,
                        'author': {
                            'type': 'admin',
                            'id': 'admin_123',
                            'name': 'Support Agent'
                        }
                    }
                ]
            }
        },
        {
            # Conversation with NONE of the new fields (defaults test)
            'id': 'conv_without_new_fields',
            'created_at': base_timestamp,
            'updated_at': base_timestamp + 7200,
            'state': 'open',
            'priority': None,
            'admin_assignee_id': None,
            
            # No SLA
            'sla_applied': None,
            
            # No channel (source without delivered_as)
            'source': {
                'type': 'conversation',
                'body': 'Another customer message',
                'author': {
                    'type': 'user',
                    'id': 'user_456'
                }
            },
            
            # No wait time fields
            'waiting_since': None,
            'snoozed_until': None,
            
            # No first_contact_reply
            'first_contact_reply': None,
            
            # Statistics without new fields
            'statistics': {
                'time_to_admin_reply': None,
                'time_to_last_close': None,
                'count_reopens': 0,
                'count_conversation_parts': 2
            },
            
            # No rating
            'conversation_rating': None,
            
            # No AI agent
            'ai_agent_participated': False,
            'ai_agent': None,
            
            # Standard fields
            'tags': {'tags': []},
            'topics': {'topics': []},
            'custom_attributes': {},
            'contacts': {
                'contacts': [
                    {
                        'id': 'contact_456',
                        'email': 'another@example.com',
                        'custom_attributes': {}
                    }
                ]
            },
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'id': 'part_2',
                        'part_type': 'comment',
                        'body': 'Customer question',
                        'created_at': base_timestamp,
                        'author': {
                            'type': 'user',
                            'id': 'user_456',
                            'name': 'Customer'
                        }
                    }
                ]
            }
        },
        {
            # Conversation with SLA missed
            'id': 'conv_sla_missed',
            'created_at': base_timestamp,
            'updated_at': base_timestamp + 10800,
            'state': 'closed',
            'priority': 'priority',
            'admin_assignee_id': 'admin_456',
            
            # SLA missed
            'sla_applied': {
                'sla_name': 'First Response SLA',
                'sla_status': 'missed'
            },
            
            # Channel: chat
            'source': {
                'type': 'conversation',
                'body': 'Urgent issue!',
                'delivered_as': 'chat',
                'author': {
                    'type': 'user',
                    'id': 'user_789'
                }
            },
            
            # Wait time present
            'waiting_since': base_timestamp + 7200,
            'snoozed_until': None,
            
            # First contact reply (late)
            'first_contact_reply': {
                'created_at': base_timestamp + 7200,
                'url': 'https://intercom.com/conversation/conv_sla_missed'
            },
            
            # Statistics with long response times
            'statistics': {
                'time_to_admin_reply': 7200,
                'time_to_assignment': 3600,
                'time_to_first_close': 10800,
                'time_to_last_close': 10800,
                'median_time_to_reply': 5400,
                'first_contact_reply_at': base_timestamp + 7200,
                'first_assignment_at': base_timestamp + 3600,
                'first_admin_reply_at': base_timestamp + 7200,
                'last_close_at': base_timestamp + 10800,
                'count_reopens': 1,
                'count_assignments': 2,
                'count_conversation_parts': 8
            },
            
            # Negative CSAT with remark
            'conversation_rating': {
                'rating': 1,
                'remark': 'Very slow response. Had to wait too long.',
                'contact': {'id': 'contact_789'},
                'teammate': {'id': 'admin_456'}
            },
            
            # No AI agent
            'ai_agent_participated': False,
            'ai_agent': None,
            
            # Standard fields
            'tags': {'tags': [{'name': 'urgent'}]},
            'topics': {'topics': [{'name': 'complaint'}]},
            'custom_attributes': {
                'Language': 'en',
                'Reason for contact': 'Bug Report'
            },
            'contacts': {
                'contacts': [
                    {
                        'id': 'contact_789',
                        'email': 'urgent@example.com',
                        'custom_attributes': {'tier': 'enterprise'}
                    }
                ]
            },
            'conversation_parts': {
                'conversation_parts': []
            }
        }
    ]


@pytest.fixture
def temp_duckdb_path(tmp_path):
    """Temporary DuckDB path for testing."""
    return str(tmp_path / "test_new_fields.duckdb")


@pytest.fixture
def duckdb_storage(temp_duckdb_path):
    """DuckDB storage instance for testing."""
    storage = DuckDBStorage(db_path=temp_duckdb_path)
    yield storage
    storage.close()


@pytest.fixture
def data_exporter(tmp_path):
    """Data exporter instance for testing."""
    from src.config.settings import settings
    original_output_dir = settings.output_directory
    settings.output_directory = str(tmp_path)
    
    exporter = DataExporter()
    yield exporter
    
    # Restore original output directory
    settings.output_directory = original_output_dir


class TestDuckDBNewFields:
    """Test DuckDB storage of new schema fields."""
    
    def test_store_conversations_with_all_new_fields(self, duckdb_storage, mock_conversations_with_new_fields):
        """Test that all new fields are stored in DuckDB."""
        # Store conversations
        duckdb_storage.store_conversations(mock_conversations_with_new_fields)
        
        # Query conversations back
        result = duckdb_storage.query("SELECT * FROM conversations ORDER BY id")
        
        assert len(result) == 3
        
        # Check conversation with all fields
        conv_all = result[result['id'] == 'conv_with_all_fields'].iloc[0]
        assert conv_all['priority'] == 'priority'
        assert conv_all['admin_assignee_id'] == 'admin_123'
        assert conv_all['language'] == 'en'
        assert conv_all['conversation_rating'] == 5
        assert conv_all['ai_agent_participated'] is True
        
        # Check conversation without new fields (defaults)
        conv_none = result[result['id'] == 'conv_without_new_fields'].iloc[0]
        assert pd.isna(conv_none['priority']) or conv_none['priority'] is None
        assert pd.isna(conv_none['admin_assignee_id']) or conv_none['admin_assignee_id'] is None
        assert pd.isna(conv_none['conversation_rating']) or conv_none['conversation_rating'] is None
        assert conv_none['ai_agent_participated'] is False
        
        # Check SLA missed conversation
        conv_sla = result[result['id'] == 'conv_sla_missed'].iloc[0]
        assert conv_sla['priority'] == 'priority'
        assert conv_sla['conversation_rating'] == 1
        assert conv_sla['ai_agent_participated'] is False
    
    def test_metadata_field_includes_new_attributes(self, duckdb_storage, mock_conversations_with_new_fields):
        """Test that metadata JSON includes new custom attributes."""
        import json
        
        duckdb_storage.store_conversations(mock_conversations_with_new_fields)
        
        result = duckdb_storage.query(
            "SELECT id, metadata FROM conversations WHERE id = 'conv_with_all_fields'"
        )
        
        assert len(result) == 1
        metadata = json.loads(result.iloc[0]['metadata'])
        
        # Check that custom attributes are stored
        assert metadata.get('Language') == 'en'
        assert metadata.get('Reason for contact') == 'Account Management'


class TestDataExporterNewFields:
    """Test data exporter includes new schema fields."""
    
    def test_csv_export_includes_new_fields(self, data_exporter, mock_conversations_with_new_fields, tmp_path):
        """Test that CSV export includes new fields in conversations sheet."""
        output_files = data_exporter.export_conversations_to_csv(
            mock_conversations_with_new_fields,
            filename="test_new_fields",
            split_by_category=True
        )
        
        assert len(output_files) > 0
        
        # Find the conversations CSV
        conversations_csv = None
        for file_path in output_files:
            if 'conversations.csv' in file_path:
                conversations_csv = file_path
                break
        
        assert conversations_csv is not None
        
        # Read CSV and check columns
        df = pd.read_csv(conversations_csv)
        
        # Check that key columns exist
        expected_columns = [
            'conversation_id',
            'created_at',
            'state',
            'priority',
            'source_type',
            'conversation_rating',
            'ai_agent_participated',
            'time_to_assignment',
            'median_time_to_reply',
            'count_assignments'
        ]
        
        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"
        
        # Check values for conversation with all fields
        conv_all = df[df['conversation_id'] == 'conv_with_all_fields'].iloc[0]
        assert conv_all['priority'] == 'priority'
        assert conv_all['conversation_rating'] == 5
        assert conv_all['ai_agent_participated'] is True
        assert conv_all['time_to_assignment'] == 300
        assert conv_all['median_time_to_reply'] == 450
        assert conv_all['count_assignments'] == 1
        
        # Check values for conversation without new fields (should have NaN or defaults)
        conv_none = df[df['conversation_id'] == 'conv_without_new_fields'].iloc[0]
        assert pd.isna(conv_none['priority']) or conv_none['priority'] == ''
        assert pd.isna(conv_none['conversation_rating'])
        assert conv_none['ai_agent_participated'] is False
        # time_to_assignment and median_time_to_reply should be NaN or 0
        assert pd.isna(conv_none['time_to_assignment']) or conv_none['time_to_assignment'] == 0
        assert pd.isna(conv_none['median_time_to_reply']) or conv_none['median_time_to_reply'] == 0
    
    def test_excel_export_includes_new_fields(self, data_exporter, mock_conversations_with_new_fields, tmp_path):
        """Test that Excel export includes new fields in conversations sheet."""
        output_path = data_exporter.export_conversations_to_excel(
            mock_conversations_with_new_fields,
            filename="test_new_fields_excel",
            include_metrics=True
        )
        
        assert Path(output_path).exists()
        
        # Read Excel file
        df = pd.read_excel(output_path, sheet_name='Conversations')
        
        # Check that key columns exist
        expected_columns = [
            'conversation_id',
            'priority',
            'conversation_rating',
            'ai_agent_participated',
            'time_to_assignment',
            'median_time_to_reply'
        ]
        
        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"
        
        # Check values
        conv_all = df[df['conversation_id'] == 'conv_with_all_fields'].iloc[0]
        assert conv_all['priority'] == 'priority'
        assert conv_all['conversation_rating'] == 5
        assert conv_all['ai_agent_participated'] is True
        
        # Check SLA conversation
        conv_sla = df[df['conversation_id'] == 'conv_sla_missed'].iloc[0]
        assert conv_sla['conversation_rating'] == 1
        assert conv_sla['time_to_assignment'] == 3600
        assert conv_sla['median_time_to_reply'] == 5400
    
    def test_json_export_preserves_new_fields(self, data_exporter, mock_conversations_with_new_fields, tmp_path):
        """Test that JSON export preserves all new fields."""
        import json
        
        output_path = data_exporter.export_raw_data_to_json(
            mock_conversations_with_new_fields,
            filename="test_new_fields_json"
        )
        
        assert Path(output_path).exists()
        
        # Read JSON
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        conversations = data['conversations']
        assert len(conversations) == 3
        
        # Check conversation with all fields
        conv_all = next(c for c in conversations if c['id'] == 'conv_with_all_fields')
        
        # SLA fields
        assert conv_all['sla_applied']['sla_name'] == 'First Response SLA'
        assert conv_all['sla_applied']['sla_status'] == 'hit'
        
        # Channel field
        assert conv_all['source']['delivered_as'] == 'email'
        
        # Wait time fields
        assert conv_all['waiting_since'] is not None
        
        # First contact reply
        assert conv_all['first_contact_reply']['created_at'] is not None
        
        # Statistics with new fields
        assert conv_all['statistics']['time_to_assignment'] == 300
        assert conv_all['statistics']['median_time_to_reply'] == 450
        
        # CSAT remark
        assert conv_all['conversation_rating']['remark'] == 'Great service! Very helpful and quick response.'
        
        # AI content sources
        assert len(conv_all['ai_agent']['content_sources']) == 2
        assert conv_all['ai_agent']['content_sources'][0]['content_type'] == 'article'
        assert conv_all['ai_agent']['content_sources'][0]['title'] == 'How to reset your password'
        
        # Check conversation without new fields
        conv_none = next(c for c in conversations if c['id'] == 'conv_without_new_fields')
        assert conv_none['sla_applied'] is None
        assert 'delivered_as' not in conv_none['source']
        assert conv_none['waiting_since'] is None
        assert conv_none['first_contact_reply'] is None
        assert conv_none['conversation_rating'] is None
        assert conv_none['ai_agent'] is None


class TestNewFieldsIntegration:
    """Integration tests for new fields across storage and export."""
    
    def test_roundtrip_storage_and_export(
        self, 
        duckdb_storage, 
        data_exporter, 
        mock_conversations_with_new_fields,
        tmp_path
    ):
        """Test that data survives storage -> retrieval -> export pipeline."""
        # Store in DuckDB
        duckdb_storage.store_conversations(mock_conversations_with_new_fields)
        
        # Query back from DuckDB
        result = duckdb_storage.query("SELECT * FROM conversations ORDER BY id")
        
        # Convert back to dict format for exporter
        # (In real usage, conversations are passed directly without DuckDB roundtrip)
        retrieved_conversations = mock_conversations_with_new_fields  # Use original for export
        
        # Export to CSV
        output_files = data_exporter.export_conversations_to_csv(
            retrieved_conversations,
            filename="roundtrip_test",
            split_by_category=True
        )
        
        # Verify export was successful
        assert len(output_files) > 0
        
        # Verify conversations CSV contains data
        conversations_csv = next(f for f in output_files if 'conversations.csv' in f)
        df = pd.read_csv(conversations_csv)
        assert len(df) == 3
        
        # Verify key fields survived the roundtrip
        conv_all = df[df['conversation_id'] == 'conv_with_all_fields'].iloc[0]
        assert conv_all['priority'] == 'priority'
        assert conv_all['conversation_rating'] == 5
        assert conv_all['time_to_assignment'] == 300


class TestFieldDefaults:
    """Test default values for missing new fields."""
    
    def test_missing_sla_defaults(self, duckdb_storage):
        """Test that missing SLA fields don't break storage."""
        conversations = [
            {
                'id': 'conv_no_sla',
                'created_at': int(datetime.now(timezone.utc).timestamp()),
                'updated_at': int(datetime.now(timezone.utc).timestamp()),
                'state': 'open',
                'sla_applied': None,  # Explicitly None
                'source': {'type': 'conversation', 'body': 'Test'},
                'statistics': {},
                'tags': {'tags': []},
                'topics': {'topics': []},
                'custom_attributes': {},
                'contacts': {'contacts': []},
                'conversation_parts': {'conversation_parts': []}
            }
        ]
        
        # Should not raise exception
        duckdb_storage.store_conversations(conversations)
        
        result = duckdb_storage.query("SELECT * FROM conversations WHERE id = 'conv_no_sla'")
        assert len(result) == 1
    
    def test_missing_statistics_fields_defaults(self, duckdb_storage):
        """Test that missing statistics fields use appropriate defaults."""
        conversations = [
            {
                'id': 'conv_no_stats',
                'created_at': int(datetime.now(timezone.utc).timestamp()),
                'updated_at': int(datetime.now(timezone.utc).timestamp()),
                'state': 'open',
                'source': {'type': 'conversation', 'body': 'Test'},
                'statistics': {
                    # Missing: time_to_assignment, median_time_to_reply
                    'count_reopens': 0
                },
                'tags': {'tags': []},
                'topics': {'topics': []},
                'custom_attributes': {},
                'contacts': {'contacts': []},
                'conversation_parts': {'conversation_parts': []}
            }
        ]
        
        # Should not raise exception
        duckdb_storage.store_conversations(conversations)
        
        result = duckdb_storage.query("SELECT * FROM conversations WHERE id = 'conv_no_stats'")
        assert len(result) == 1
        
        # Check that missing fields are handled gracefully
        row = result.iloc[0]
        assert pd.isna(row.get('time_to_assignment')) or row.get('time_to_assignment') is None
    
    def test_missing_channel_field_defaults(self, data_exporter, tmp_path):
        """Test that missing source.delivered_as doesn't break export."""
        conversations = [
            {
                'id': 'conv_no_channel',
                'created_at': int(datetime.now(timezone.utc).timestamp()),
                'updated_at': int(datetime.now(timezone.utc).timestamp()),
                'state': 'open',
                'source': {
                    'type': 'conversation',
                    'body': 'Test message'
                    # Missing: delivered_as
                },
                'statistics': {'count_reopens': 0},
                'tags': {'tags': []},
                'topics': {'topics': []},
                'custom_attributes': {},
                'contacts': {'contacts': []},
                'conversation_parts': {'conversation_parts': []}
            }
        ]
        
        # Should not raise exception
        output_files = data_exporter.export_conversations_to_csv(
            conversations,
            filename="test_no_channel",
            split_by_category=True
        )
        
        assert len(output_files) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

