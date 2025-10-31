"""
Unit tests for DuckDB storage service.
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path

from src.services.duckdb_storage import DuckDBStorage


class TestDuckDBStorage:
    """Test cases for DuckDB storage service."""
    
    def test_initialization(self, temp_dir):
        """Test DuckDB storage initialization."""
        db_path = temp_dir / "test.duckdb"
        storage = DuckDBStorage(str(db_path))
        
        assert storage.db_path == db_path
        assert storage.conn is not None
        assert db_path.exists()
        
        storage.close()
    
    def test_schema_creation(self, duckdb_storage):
        """Test that database schema is created correctly."""
        # Check that tables exist
        tables_query = "SHOW TABLES"
        tables_df = duckdb_storage.query(tables_query)
        
        expected_tables = [
            'conversations', 'conversation_tags', 'conversation_topics',
            'conversation_categories', 'technical_patterns', 'escalations'
        ]
        
        for table in expected_tables:
            assert table in tables_df['name'].values
    
    def test_store_conversations(self, duckdb_storage, sample_conversations):
        """Test storing conversations in DuckDB."""
        # Store conversations
        duckdb_storage.store_conversations(sample_conversations)
        
        # Verify conversations were stored
        conversations_df = duckdb_storage.query("SELECT * FROM conversations")
        assert len(conversations_df) == len(sample_conversations)
        
        # Check specific fields
        assert 'id' in conversations_df.columns
        assert 'created_at' in conversations_df.columns
        assert 'state' in conversations_df.columns
        assert 'full_text' in conversations_df.columns
    
    def test_extract_conversation_data(self, duckdb_storage, sample_conversation):
        """Test conversation data extraction."""
        conv_data = duckdb_storage._extract_conversation_data(sample_conversation)
        
        assert conv_data['id'] == 'test_conv_123'
        assert conv_data['state'] == 'closed'
        assert conv_data['conversation_rating'] == 5
        assert conv_data['ai_agent_participated'] is True
        assert 'refund' in conv_data['full_text'].lower()
    
    def test_extract_tags(self, duckdb_storage, sample_conversation):
        """Test tag extraction."""
        tags = duckdb_storage._extract_tags(sample_conversation)
        
        assert len(tags) == 2
        assert 'billing' in tags
        assert 'refund' in tags
    
    def test_extract_topics(self, duckdb_storage, sample_conversation):
        """Test topic extraction."""
        topics = duckdb_storage._extract_topics(sample_conversation)
        
        assert len(topics) == 2
        assert 'Billing' in topics
        assert 'Refund' in topics
    
    def test_extract_technical_patterns(self, duckdb_storage):
        """Test technical pattern extraction."""
        # Conversation with cache clearing pattern
        conv_with_cache = {
            "id": "test_1",
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "Try clearing your browser cache and cookies"
                    }
                ]
            }
        }
        
        patterns = duckdb_storage._extract_technical_patterns(conv_with_cache)
        
        assert len(patterns) == 1
        assert patterns[0]['type'] == 'cache_clear'
        assert patterns[0]['value'] is True
        assert 'clear cache' in patterns[0]['keywords']
    
    def test_extract_escalations(self, duckdb_storage):
        """Test escalation extraction."""
        # Conversation with escalation
        conv_with_escalation = {
            "id": "test_1",
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "Let me escalate this to @Hilary for review"
                    }
                ]
            }
        }
        
        escalations = duckdb_storage._extract_escalations(conv_with_escalation)
        
        assert len(escalations) == 1
        assert escalations[0]['to'] == 'Hilary'
        assert escalations[0]['type'] == 'mention'
    
    def test_clean_html(self, duckdb_storage):
        """Test HTML cleaning."""
        html_text = "<p>This is <b>bold</b> text with &nbsp; entities</p>"
        clean_text = duckdb_storage._clean_html(html_text)
        
        assert "<p>" not in clean_text
        assert "<b>" not in clean_text
        assert "&nbsp;" not in clean_text
        assert "This is bold text with entities" in clean_text
    
    def test_parse_timestamp(self, duckdb_storage):
        """Test timestamp parsing."""
        # Unix timestamp
        unix_ts = 1699123456
        dt = duckdb_storage._parse_timestamp(unix_ts)
        assert isinstance(dt, datetime)
        
        # ISO string
        iso_string = "2023-11-04T10:30:56Z"
        dt = duckdb_storage._parse_timestamp(iso_string)
        assert isinstance(dt, datetime)
        
        # None
        dt = duckdb_storage._parse_timestamp(None)
        assert dt is None
    
    def test_get_conversations_by_category(self, duckdb_storage, sample_conversations):
        """Test getting conversations by category."""
        # Store conversations
        duckdb_storage.store_conversations(sample_conversations)
        
        # Query by category
        start_date = date.today() - timedelta(days=1)
        end_date = date.today()
        
        df = duckdb_storage.get_conversations_by_category("Billing", start_date, end_date)
        
        # Should return conversations with billing category
        assert len(df) > 0
        assert 'subcategory' in df.columns
        assert 'confidence' in df.columns
    
    def test_get_technical_patterns(self, duckdb_storage, technical_troubleshooting_conversations):
        """Test getting technical patterns."""
        # Store conversations
        duckdb_storage.store_conversations(technical_troubleshooting_conversations)
        
        # Query technical patterns
        start_date = date.today() - timedelta(days=1)
        end_date = date.today()
        
        df = duckdb_storage.get_technical_patterns(start_date, end_date)
        
        # Should return pattern data
        assert len(df) > 0
        assert 'pattern_type' in df.columns
        assert 'occurrence_count' in df.columns
    
    def test_get_escalations(self, duckdb_storage, escalation_conversations):
        """Test getting escalations."""
        # Store conversations
        duckdb_storage.store_conversations(escalation_conversations)
        
        # Query escalations
        start_date = date.today() - timedelta(days=1)
        end_date = date.today()
        
        df = duckdb_storage.get_escalations(start_date, end_date)
        
        # Should return escalation data
        assert len(df) > 0
        assert 'escalated_to' in df.columns
        assert 'escalation_count' in df.columns
    
    def test_get_fin_analysis(self, duckdb_storage, fin_conversations):
        """Test getting Fin analysis."""
        # Store conversations
        duckdb_storage.store_conversations(fin_conversations)
        
        # Query Fin analysis
        start_date = date.today() - timedelta(days=1)
        end_date = date.today()
        
        df = duckdb_storage.get_fin_analysis(start_date, end_date)
        
        # Should return Fin analysis data
        assert len(df) > 0
        assert 'interaction_type' in df.columns
        assert 'conversation_count' in df.columns
    
    def test_query_method(self, duckdb_storage):
        """Test generic query method."""
        # Simple query
        df = duckdb_storage.query("SELECT 1 as test_column")
        
        assert len(df) == 1
        assert df.iloc[0]['test_column'] == 1
    
    def test_batch_processing(self, duckdb_storage):
        """Test batch processing of conversations."""
        # Create many conversations
        conversations = []
        for i in range(1500):  # More than default batch size
            conv = {
                "id": f"batch_conv_{i}",
                "created_at": 1699123456 + i,
                "state": "closed",
                "tags": {"tags": []},
                "topics": {"topics": []},
                "conversation_parts": {"conversation_parts": []}
            }
            conversations.append(conv)
        
        # Store in batches
        duckdb_storage.store_conversations(conversations, batch_size=500)
        
        # Verify all were stored
        df = duckdb_storage.query("SELECT COUNT(*) as count FROM conversations WHERE id LIKE 'batch_conv_%'")
        assert df.iloc[0]['count'] == 1500
    
    def test_error_handling(self, duckdb_storage):
        """Test error handling in queries."""
        # Invalid query should raise exception
        with pytest.raises(Exception):
            duckdb_storage.query("INVALID SQL QUERY")
    
    def test_close_connection(self, temp_dir):
        """Test closing database connection."""
        db_path = temp_dir / "test_close.duckdb"
        storage = DuckDBStorage(str(db_path))
        
        # Connection should be open
        assert storage.conn is not None
        
        # Close connection
        storage.close()
        
        # Connection should be closed (conn will be None)
        assert storage.conn is None
    
    # =============================================================================
    # COMMENT 4: Test cases for full_text/customer_messages derivation from utilities
    # =============================================================================
    
    def test_full_text_derived_from_source_and_parts(self, duckdb_storage):
        """Test that full_text is properly derived from source.body and conversation_parts using utility."""
        conv = {
            "id": "test_full_text_derivation",
            "created_at": 1699123456,
            "source": {
                "body": "<p>Customer initial message</p>"
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>Agent response</p>",
                        "author": {
                            "type": "admin"
                        }
                    },
                    {
                        "body": "<p>Customer follow-up</p>",
                        "author": {
                            "type": "user"
                        }
                    }
                ]
            },
            "tags": {"tags": []},
            "topics": {"topics": []},
            "custom_attributes": {}
        }
        
        # Extract conversation data
        conv_data = duckdb_storage._extract_conversation_data(conv)
        
        # Assert full_text is properly derived (should contain all messages)
        assert conv_data['full_text'] is not None
        assert 'Customer initial message' in conv_data['full_text']
        assert 'Agent response' in conv_data['full_text']
        assert 'Customer follow-up' in conv_data['full_text']
        
        # Assert HTML is cleaned
        assert '<p>' not in conv_data['full_text']
        assert '</p>' not in conv_data['full_text']
    
    def test_customer_messages_derived_from_utility(self, duckdb_storage):
        """Test that customer_messages is properly derived using extract_customer_messages utility."""
        conv = {
            "id": "test_customer_messages_derivation",
            "created_at": 1699123456,
            "source": {
                "body": "<p>Customer initial question</p>",
                "author": {
                    "type": "user"
                }
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>Agent response here</p>",
                        "author": {
                            "type": "admin"
                        }
                    },
                    {
                        "body": "<p>Customer follow-up question</p>",
                        "author": {
                            "type": "user"
                        }
                    },
                    {
                        "body": "<p>Bot response</p>",
                        "author": {
                            "type": "bot"
                        }
                    }
                ]
            },
            "tags": {"tags": []},
            "topics": {"topics": []},
            "custom_attributes": {}
        }
        
        # Extract conversation data
        conv_data = duckdb_storage._extract_conversation_data(conv)
        
        # Assert customer_messages contains only user messages
        assert conv_data['customer_messages'] is not None
        assert 'Customer initial question' in conv_data['customer_messages']
        assert 'Customer follow-up question' in conv_data['customer_messages']
        
        # Assert agent and bot messages are NOT in customer_messages
        assert 'Agent response here' not in conv_data['customer_messages']
        assert 'Bot response' not in conv_data['customer_messages']
        
        # Assert HTML is cleaned
        assert '<p>' not in conv_data['customer_messages']
        assert '</p>' not in conv_data['customer_messages']
    
    def test_conversation_without_source_body(self, duckdb_storage):
        """Test derivation when source.body is missing."""
        conv = {
            "id": "test_no_source_body",
            "created_at": 1699123456,
            "source": {
                # No body field
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>Only conversation part</p>",
                        "author": {
                            "type": "user"
                        }
                    }
                ]
            },
            "tags": {"tags": []},
            "topics": {"topics": []},
            "custom_attributes": {}
        }
        
        # Should not raise error
        conv_data = duckdb_storage._extract_conversation_data(conv)
        
        # Assert full_text contains the conversation part
        assert conv_data['full_text'] is not None
        assert 'Only conversation part' in conv_data['full_text']
        
        # Assert customer_messages contains the conversation part
        assert conv_data['customer_messages'] is not None
        assert 'Only conversation part' in conv_data['customer_messages']
    
    def test_conversation_with_empty_parts(self, duckdb_storage):
        """Test derivation when conversation_parts is empty."""
        conv = {
            "id": "test_empty_parts",
            "created_at": 1699123456,
            "source": {
                "body": "<p>Only source message</p>",
                "author": {
                    "type": "user"
                }
            },
            "conversation_parts": {
                "conversation_parts": []
            },
            "tags": {"tags": []},
            "topics": {"topics": []},
            "custom_attributes": {}
        }
        
        # Should not raise error
        conv_data = duckdb_storage._extract_conversation_data(conv)
        
        # Assert full_text contains only the source message
        assert conv_data['full_text'] is not None
        assert 'Only source message' in conv_data['full_text']
        
        # Assert customer_messages contains only the source message
        assert conv_data['customer_messages'] is not None
        assert 'Only source message' in conv_data['customer_messages']






