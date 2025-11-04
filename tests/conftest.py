"""
Pytest configuration and shared fixtures for Intercom Analysis Tool tests.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import json

# Proper package imports - tests should be run with pytest from project root
# If running from within tests/ directory, run: python -m pytest from root instead
from src.config.settings import Settings
from src.services.duckdb_storage import DuckDBStorage
from src.services.elt_pipeline import ELTPipeline
from src.config.taxonomy import TaxonomyManager, Category, Subcategory


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_settings():
    """Create test settings with mock values."""
    return Settings(
        intercom_access_token="test_token",
        openai_api_key="test_openai_key",
        gamma_api_key="test_gamma_key",
        output_directory="test_outputs",
        log_level="DEBUG"
    )


@pytest.fixture
def sample_conversation():
    """Sample conversation data for testing."""
    return {
        "id": "test_conv_123",
        "created_at": 1699123456,
        "updated_at": 1699123456,
        "state": "closed",
        "priority": "normal",
        "admin_assignee_id": "admin_123",
        "conversation_rating": 5,
        "ai_agent_participated": True,
        "custom_attributes": {
            "Language": "en",
            "Fin AI Agent: Preview": True,
            "Copilot used": False
        },
        "statistics": {
            "time_to_admin_reply": 300,
            "handling_time": 1800,
            "count_conversation_parts": 5,
            "count_reopens": 0
        },
        "tags": {
            "tags": [
                {"name": "billing"},
                {"name": "refund"}
            ]
        },
        "topics": {
            "topics": [
                {"name": "Billing"},
                {"name": "Refund"}
            ]
        },
        "source": {
            "body": "<p>I need a refund for my subscription</p>"
        },
        "conversation_parts": {
            "conversation_parts": [
                {
                    "id": "part_1",
                    "type": "comment",
                    "body": "<p>I can help you with that refund request.</p>",
                    "author": {
                        "type": "admin",
                        "id": "admin_123"
                    },
                    "created_at": 1699123500
                },
                {
                    "id": "part_2", 
                    "type": "comment",
                    "body": "<p>Thank you for your help!</p>",
                    "author": {
                        "type": "user",
                        "id": "user_456"
                    },
                    "created_at": 1699123600
                }
            ]
        }
    }


@pytest.fixture
def sample_conversations(sample_conversation):
    """Multiple sample conversations for testing."""
    conversations = []
    
    # Create variations
    for i in range(5):
        conv = sample_conversation.copy()
        conv["id"] = f"test_conv_{i}"
        conv["created_at"] = 1699123456 + (i * 3600)  # 1 hour apart
        
        if i % 2 == 0:
            conv["tags"]["tags"] = [{"name": "bug"}, {"name": "export"}]
            conv["topics"]["topics"] = [{"name": "Bug"}, {"name": "Export"}]
            conv["source"]["body"] = "<p>I'm having trouble exporting my presentation</p>"
        else:
            conv["tags"]["tags"] = [{"name": "billing"}, {"name": "refund"}]
            conv["topics"]["topics"] = [{"name": "Billing"}, {"name": "Refund"}]
            conv["source"]["body"] = "<p>I need a refund for my subscription</p>"
        
        conversations.append(conv)
    
    return conversations


@pytest.fixture
def sample_conversation_with_int_timestamp():
    """Sample conversation with integer Unix timestamp for testing timestamp conversion."""
    return {
        'id': 'test_conv_int_123',
        'created_at': 1699123456,  # Integer Unix timestamp (2023-11-04)
        'updated_at': 1699125456,
        'state': 'closed',
        'admin_assignee_id': 'admin_123',
        'ai_agent_participated': False,
        # NOTE: customer_messages and full_text should be derived via extract_customer_messages() and extract_conversation_text()
        'conversation_rating': 4,
        'tags': {'tags': [{'name': 'billing'}]},
        'topics': {'topics': [{'name': 'Billing'}]}
    }


@pytest.fixture
def sample_conversation_with_datetime_timestamp():
    """Sample conversation with datetime timestamp for testing timestamp conversion."""
    from datetime import timezone
    return {
        'id': 'test_conv_datetime_456',
        'created_at': datetime(2023, 11, 4, 12, 0, 0, tzinfo=timezone.utc),
        'updated_at': datetime(2023, 11, 4, 13, 0, 0, tzinfo=timezone.utc),
        'state': 'closed',
        'admin_assignee_id': 'admin_456',
        'ai_agent_participated': False,
        # NOTE: customer_messages and full_text should be derived via extract_customer_messages() and extract_conversation_text()
        'conversation_rating': 3,
        'tags': {'tags': [{'name': 'export'}, {'name': 'bug'}]},
        'topics': {'topics': [{'name': 'Export'}, {'name': 'Bug'}]}
    }


@pytest.fixture
def sample_conversation_with_float_timestamp():
    """Sample conversation with float Unix timestamp for testing timestamp conversion."""
    return {
        'id': 'test_conv_float_789',
        'created_at': 1699123456.789,  # Float with fractional seconds
        'updated_at': 1699125456.123,
        'state': 'closed',
        'admin_assignee_id': 'admin_789',
        'ai_agent_participated': True,
        # NOTE: customer_messages and full_text should be derived via extract_customer_messages() and extract_conversation_text()
        'conversation_rating': 5,
        'tags': {'tags': [{'name': 'feedback'}, {'name': 'dashboard'}]},
        'topics': {'topics': [{'name': 'Dashboard'}, {'name': 'Feedback'}]}
    }


@pytest.fixture
def sample_conversations_for_example_extraction():
    """List of conversations with varied characteristics for example extraction testing."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    conversations = []
    
    # 10 conversations with integer timestamps (most common)
    for i in range(10):
        conversations.append({
            'id': f'conv_int_{i}',
            'created_at': int((now - timedelta(days=i)).timestamp()),
            'updated_at': int((now - timedelta(days=i) + timedelta(hours=1)).timestamp()),
            'state': 'closed',
            # NOTE: customer_messages and full_text should be derived via utilities
            'conversation_rating': 4 if i % 2 == 0 else None,
            'tags': {'tags': [{'name': 'bug'}, {'name': 'crash'}]},
            'topics': {'topics': [{'name': 'Bug'}, {'name': 'Crash'}]}
        })
    
    # 5 conversations with datetime timestamps
    for i in range(10, 15):
        conversations.append({
            'id': f'conv_datetime_{i}',
            'created_at': now - timedelta(days=i % 7),
            'updated_at': now - timedelta(days=i % 7) + timedelta(hours=2),
            'state': 'closed',
            # NOTE: customer_messages and full_text should be derived via utilities
            'conversation_rating': 5,
            'tags': {'tags': [{'name': 'feedback'}, {'name': 'ui'}]},
            'topics': {'topics': [{'name': 'Feedback'}, {'name': 'UI'}]}
        })
    
    # 3 conversations with float timestamps
    for i in range(15, 18):
        conversations.append({
            'id': f'conv_float_{i}',
            'created_at': (now - timedelta(days=i % 10)).timestamp(),
            'updated_at': (now - timedelta(days=i % 10) + timedelta(hours=1)).timestamp(),
            'state': 'closed',
            # NOTE: customer_messages and full_text should be derived via utilities
            'conversation_rating': 5,
            'tags': {'tags': [{'name': 'support'}, {'name': 'positive'}]},
            'topics': {'topics': [{'name': 'Support'}, {'name': 'Positive'}]}
        })
    
    # 2 conversations with None timestamps (edge case)
    for i in range(18, 20):
        conversations.append({
            'id': f'conv_none_{i}',
            'created_at': None,
            'updated_at': None,
            'state': 'open',
            # NOTE: customer_messages and full_text should be derived via utilities
            'conversation_rating': None,
            'tags': {'tags': [{'name': 'billing'}, {'name': 'issue'}]},
            'topics': {'topics': [{'name': 'Billing'}, {'name': 'Issue'}]}
        })
    
    return conversations


@pytest.fixture
def mock_openai_client_for_examples():
    """Mock OpenAI client for example extraction testing."""
    
    class MockOpenAIClientForExamples:
        def __init__(self):
            self.call_count = 0
            self.last_prompt = None
        
        async def generate_analysis(self, prompt: str, **kwargs) -> str:
            """Return mock example selection indices."""
            self.call_count += 1
            self.last_prompt = prompt
            # Return JSON array of example indices (1-indexed)
            return '[1, 3, 5, 7]'
    
    return MockOpenAIClientForExamples()


@pytest.fixture
def duckdb_storage(temp_dir):
    """Create a DuckDB storage instance for testing."""
    db_path = temp_dir / "test_conversations.duckdb"
    storage = DuckDBStorage(str(db_path))
    yield storage
    storage.close()


@pytest.fixture
def sample_analysis_snapshot():
    """Sample analysis snapshot data for testing."""
    return {
        'snapshot_id': 'weekly_20251107',
        'analysis_type': 'weekly',
        'period_start': date(2025, 11, 1),
        'period_end': date(2025, 11, 7),
        'total_conversations': 100,
        'date_range_label': 'Nov 1-7, 2025',
        'insights_summary': 'Test insights for the week',
        'topic_volumes': {
            'Billing': 45,
            'API': 18,
            'Account': 12,
            'Feature Requests': 15,
            'Bug Reports': 10
        },
        'topic_sentiments': {
            'Billing': {
                'positive': 0.6,
                'negative': 0.3,
                'neutral': 0.1
            },
            'API': {
                'positive': 0.4,
                'negative': 0.5,
                'neutral': 0.1
            }
        },
        'tier_distribution': {
            'paid': 80,
            'free': 20
        },
        'agent_attribution': {
            'horatio': 60,
            'boldr': 30,
            'internal': 10
        },
        'resolution_metrics': {
            'fcr': 0.85,
            'reopen_rate': 0.05,
            'avg_resolution_time': 24.5
        },
        'fin_performance': {
            'total_conversations': 30,
            'resolution_rate': 0.75,
            'knowledge_gap_rate': 0.15
        },
        'key_patterns': {
            'cache_clear': 15,
            'escalations': 5
        },
        'reviewed': False,
        'reviewed_by': None,
        'reviewed_at': None,
        'notes': None
    }


@pytest.fixture
def sample_comparative_analysis():
    """Sample comparative analysis data for testing."""
    return {
        'comparison_id': 'comp_20251107_20251031',
        'comparison_type': 'week_over_week',
        'current_snapshot_id': 'weekly_20251107',
        'prior_snapshot_id': 'weekly_20251031',
        'volume_changes': {
            'Billing': {
                'change': 7,
                'pct': 0.16,
                'previous': 38,
                'current': 45
            },
            'API': {
                'change': -3,
                'pct': -0.14,
                'previous': 21,
                'current': 18
            }
        },
        'sentiment_changes': {
            'Billing': {
                'positive_delta': 0.05,
                'negative_delta': -0.02
            }
        },
        'resolution_changes': {
            'fcr_delta': 0.03,
            'resolution_time_delta': -2.5
        },
        'significant_changes': [
            {
                'topic': 'Billing',
                'change_type': 'volume_increase',
                'magnitude': 'moderate'
            }
        ],
        'emerging_patterns': [
            {
                'pattern': 'refund_requests',
                'volume': 12,
                'trend': 'increasing'
            }
        ],
        'declining_patterns': [
            {
                'pattern': 'account_login_issues',
                'volume': 3,
                'trend': 'decreasing'
            }
        ]
    }


@pytest.fixture
def sample_metrics_timeseries():
    """Sample metrics timeseries data for testing."""
    return [
        {
            'metric_id': 'ts_1',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'billing_volume',
            'metric_value': 45.0,
            'metric_unit': 'count',
            'category': 'volume'
        },
        {
            'metric_id': 'ts_2',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'api_volume',
            'metric_value': 18.0,
            'metric_unit': 'count',
            'category': 'volume'
        },
        {
            'metric_id': 'ts_3',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'fcr_rate',
            'metric_value': 0.85,
            'metric_unit': 'percentage',
            'category': 'resolution'
        },
        {
            'metric_id': 'ts_4',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'reopen_rate',
            'metric_value': 0.05,
            'metric_unit': 'percentage',
            'category': 'resolution'
        },
        {
            'metric_id': 'ts_5',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'avg_sentiment',
            'metric_value': 0.75,
            'metric_unit': 'score',
            'category': 'sentiment'
        },
        {
            'metric_id': 'ts_6',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'fin_resolution_rate',
            'metric_value': 0.75,
            'metric_unit': 'percentage',
            'category': 'fin_performance'
        },
        {
            'metric_id': 'ts_7',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'escalation_count',
            'metric_value': 5.0,
            'metric_unit': 'count',
            'category': 'patterns'
        },
        {
            'metric_id': 'ts_8',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'avg_resolution_time',
            'metric_value': 24.5,
            'metric_unit': 'hours',
            'category': 'resolution'
        },
        {
            'metric_id': 'ts_9',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'paid_tier_pct',
            'metric_value': 0.80,
            'metric_unit': 'percentage',
            'category': 'segmentation'
        },
        {
            'metric_id': 'ts_10',
            'snapshot_id': 'weekly_20251107',
            'metric_name': 'free_tier_pct',
            'metric_value': 0.20,
            'metric_unit': 'percentage',
            'category': 'segmentation'
        }
    ]


@pytest.fixture
def elt_pipeline(temp_dir):
    """Create an ELT pipeline instance for testing."""
    output_dir = temp_dir / "test_outputs"
    pipeline = ELTPipeline(str(output_dir))
    yield pipeline
    pipeline.close()


@pytest.fixture
def taxonomy_manager():
    """Create a taxonomy manager for testing."""
    return TaxonomyManager()


@pytest.fixture
def mock_intercom_response():
    """Mock Intercom API response."""
    return {
        "conversations": [
            {
                "id": "conv_1",
                "created_at": 1699123456,
                "state": "closed",
                "admin_assignee_id": "admin_123"
            },
            {
                "id": "conv_2", 
                "created_at": 1699123457,
                "state": "open",
                "admin_assignee_id": "admin_456"
            }
        ],
        "pages": {
            "next": {
                "starting_after": "conv_2"
            }
        }
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": "This is a test analysis report with insights about the conversation data."
                }
            }
        ]
    }


@pytest.fixture
def test_date_range():
    """Test date range for analysis."""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    return start_date, end_date


@pytest.fixture
def test_datetime_range():
    """Test datetime range for analysis."""
    end_datetime = datetime.now()
    start_datetime = end_datetime - timedelta(days=30)
    return start_datetime, end_datetime


class MockIntercomSDKService:
    """Mock Intercom service for testing."""
    
    def __init__(self, conversations: List[Dict] = None):
        self.conversations = conversations or []
        self.call_count = 0
    
    async def test_connection(self) -> bool:
        return True
    
    async def fetch_conversations_by_date_range(self, start_date, end_date, max_conversations: Optional[int] = None, **kwargs):
        self.call_count += 1
        if max_conversations:
            return self.conversations[:max_conversations]
        return self.conversations
    
    async def fetch_conversations_by_query(self, query_type, suggestion=None, custom_query=None, max_pages=None):
        self.call_count += 1
        return self.conversations


class MockOpenAIClient:
    """Mock OpenAI client for testing."""
    
    def __init__(self, response: str = "Test analysis report"):
        self.response = response
        self.call_count = 0
    
    async def generate_analysis(self, prompt: str) -> str:
        self.call_count += 1
        return self.response


class MockDataExporter:
    """Mock data exporter for testing."""
    
    def __init__(self):
        self.export_count = 0
        self.exported_files = []
    
    def export_conversations_to_csv(self, conversations, filename):
        self.export_count += 1
        filepath = f"test_outputs/{filename}.csv"
        self.exported_files.append(filepath)
        return filepath
    
    def export_conversations_to_excel(self, conversations, filename):
        self.export_count += 1
        filepath = f"test_outputs/{filename}.xlsx"
        self.exported_files.append(filepath)
        return filepath
    
    def export_raw_data_to_json(self, data, filename):
        self.export_count += 1
        filepath = f"test_outputs/{filename}.json"
        self.exported_files.append(filepath)
        return filepath


@pytest.fixture
def mock_intercom_service(sample_conversations):
    """Mock Intercom service fixture."""
    return MockIntercomSDKService(sample_conversations)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client fixture."""
    return MockOpenAIClient()


@pytest.fixture
def mock_data_exporter():
    """Mock data exporter fixture."""
    return MockDataExporter()


# Test data for specific scenarios
@pytest.fixture
def technical_troubleshooting_conversations():
    """Conversations with technical troubleshooting patterns."""
    return [
        {
            "id": "tech_1",
            "created_at": 1699123456,
            "state": "closed",
            "source": {
                "body": "<p>I can't export my presentation. Can you help?</p>"
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>Try clearing your browser cache and cookies. Press Ctrl+Shift+Delete.</p>",
                        "author": {"type": "admin"}
                    },
                    {
                        "body": "<p>That worked! Thank you.</p>",
                        "author": {"type": "user"}
                    }
                ]
            }
        },
        {
            "id": "tech_2",
            "created_at": 1699123457,
            "state": "closed",
            "source": {
                "body": "<p>My presentation won't load properly</p>"
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>Try using a different browser like Chrome or Firefox.</p>",
                        "author": {"type": "admin"}
                    },
                    {
                        "body": "<p>I'll try Chrome. Thanks!</p>",
                        "author": {"type": "user"}
                    }
                ]
            }
        }
    ]


@pytest.fixture
def escalation_conversations():
    """Conversations with escalation patterns."""
    return [
        {
            "id": "escalation_1",
            "created_at": 1699123456,
            "state": "closed",
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>This is a complex billing issue. Let me escalate this to @Hilary for review.</p>",
                        "author": {"type": "admin"}
                    }
                ]
            }
        },
        {
            "id": "escalation_2",
            "created_at": 1699123457,
            "state": "open",
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>This technical issue needs @Dae-Ho's expertise. Forwarding to him.</p>",
                        "author": {"type": "admin"}
                    }
                ]
            }
        }
    ]


@pytest.fixture
def fin_conversations():
    """Conversations involving Fin AI agent."""
    return [
        {
            "id": "fin_1",
            "created_at": 1699123456,
            "state": "closed",
            "ai_agent_participated": True,
            "custom_attributes": {
                "Fin AI Agent: Preview": True
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>I can help you with that billing question.</p>",
                        "author": {"type": "admin"}
                    }
                ]
            }
        },
        {
            "id": "fin_2",
            "created_at": 1699123457,
            "state": "open",
            "ai_agent_participated": False,
            "custom_attributes": {
                "Fin AI Agent: Preview": False
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "<p>This requires human assistance. Let me help you directly.</p>",
                        "author": {"type": "admin"}
                    }
                ]
            }
        }
    ]


@pytest.fixture
def sample_fin_conversations_with_ratings():
    """List of 20+ Finn conversations with varied ratings, escalation/knowledge gap phrases, and Tier 2 indicators."""
    conversations = []
    ratings = [1, 2, 3, 4, 5, None]  # Cycle through ratings
    topics = ['Billing Issues', 'Account Issues', 'Product Questions']
    
    for i in range(20):
        rating = ratings[i % len(ratings)]
        topic = topics[i % len(topics)]
        
        # Base conversation
        conv = {
            'id': f'fin_conv_{i}',
            'created_at': 1699123456 + (i * 3600),
            'updated_at': 1699123456 + (i * 3600) + 1800,
            'state': 'closed',
            'admin_assignee_id': 'admin_fin',
            'ai_agent_participated': True,
            'conversation_rating': rating,
            'custom_attributes': {
                'Fin AI Agent: Preview': True,
                'Language': 'en'
            },
            'tags': {'tags': []},
            'conversation_topics': [],
            'detected_topics': [topic],
            # NOTE: full_text and customer_messages should be derived via utilities
        }
        
        # Add Tier 2 indicators based on topic
        if topic == 'Billing Issues':
            if i % 2 == 0:
                conv['tags']['tags'].append({'name': 'Refund'})
                conv['conversation_topics'].append({'name': 'Refund'})
            else:
                conv['tags']['tags'].append({'name': 'Invoice'})
                conv['conversation_topics'].append({'name': 'Invoice'})
            conv['custom_attributes']['billing_type'] = 'annual' if i % 4 == 0 else 'monthly'
        elif topic == 'Account Issues':
            conv['tags']['tags'].append({'name': 'Login'})
            conv['conversation_topics'].append({'name': 'Login'})
            conv['custom_attributes']['account_type'] = 'premium' if i % 3 == 0 else 'free'
        else:  # Product Questions
            conv['tags']['tags'].append({'name': 'Feature'})
            conv['conversation_topics'].append({'name': 'Feature'})
            conv['custom_attributes']['product_version'] = 'v2' if i % 5 == 0 else 'v1'
        
        # NOTE: Removed full_text modifications - text should be in source/conversation_parts
        # Add escalation/knowledge gap phrases to conversation_parts instead if needed
        
        conversations.append(conv)
    
    return conversations


@pytest.fixture
def mock_subtopic_data_for_fin():
    """Mock SubTopicDetectionAgent output structure for Finn conversations."""
    return {
        'subtopics_by_tier1_topic': {
            'Billing Issues': {
                'tier2': {
                    'Refund': {'volume': 5, 'percentage': 50.0, 'source': 'tags'},
                    'Invoice': {'volume': 3, 'percentage': 30.0, 'source': 'tags'},
                    'annual': {'volume': 1, 'percentage': 10.0, 'source': 'custom_attributes'},
                    'monthly': {'volume': 1, 'percentage': 10.0, 'source': 'custom_attributes'}
                },
                'tier3': {
                    'Refund Processing Delays': {'keywords': ['refund', 'delay'], 'method': 'llm_semantic'},
                    'Invoice Discrepancies': {'keywords': ['invoice', 'error'], 'method': 'llm_semantic'}
                }
            },
            'Account Issues': {
                'tier2': {
                    'Login': {'volume': 4, 'percentage': 66.7, 'source': 'tags'},
                    'premium': {'volume': 1, 'percentage': 16.7, 'source': 'custom_attributes'},
                    'free': {'volume': 1, 'percentage': 16.7, 'source': 'custom_attributes'}
                },
                'tier3': {
                    'Login Failures': {'keywords': ['login', 'fail'], 'method': 'llm_semantic'},
                    'Password Reset Issues': {'keywords': ['password', 'reset'], 'method': 'llm_semantic'}
                }
            },
            'Product Questions': {
                'tier2': {
                    'Feature': {'volume': 3, 'percentage': 60.0, 'source': 'tags'},
                    'v1': {'volume': 1, 'percentage': 20.0, 'source': 'custom_attributes'},
                    'v2': {'volume': 1, 'percentage': 20.0, 'source': 'custom_attributes'}
                },
                'tier3': {
                    'Feature Requests': {'keywords': ['feature', 'request'], 'method': 'llm_semantic'},
                    'Usage Questions': {'keywords': ['how', 'use'], 'method': 'llm_semantic'}
                }
            }
        }
    }


@pytest.fixture
def mock_output_formatter_context_with_subtopics(mock_subtopic_data_for_fin):
    """
    Create complete AgentContext for OutputFormatterAgent testing with all required previous_results.
    
    Includes sub-topic data and Finn performance with sub-topic metrics.
    """
    from src.agents.base_agent import AgentContext
    
    # Segmentation result
    segmentation_result = {
        'segmentation_summary': {
            'paid_count': 150,
            'free_count': 100,
            'paid_percentage': 60.0,
            'free_percentage': 40.0,
            'language_distribution': {
                'en': 180,
                'es': 40,
                'fr': 20,
                'de': 10
            },
            'total_languages': 4
        }
    }
    
    # Topic detection result
    topic_detection_result = {
        'topic_distribution': {
            'Billing Issues': {
                'volume': 100,
                'percentage': 40.0,
                'detection_method': 'attribute'
            },
            'Account Issues': {
                'volume': 80,
                'percentage': 32.0,
                'detection_method': 'keyword'
            },
            'Product Questions': {
                'volume': 70,
                'percentage': 28.0,
                'detection_method': 'attribute'
            }
        }
    }
    
    # Topic sentiments
    topic_sentiments = {
        'Billing Issues': {
            'data': {
                'sentiment_insight': 'Customers frustrated with billing delays and unclear charges.'
            }
        },
        'Account Issues': {
            'data': {
                'sentiment_insight': 'Users struggle with login issues causing significant frustration.'
            }
        },
        'Product Questions': {
            'data': {
                'sentiment_insight': 'Generally positive inquiries about new features.'
            }
        }
    }
    
    # Topic examples
    topic_examples = {
        'Billing Issues': {
            'data': {
                'examples': [
                    {
                        'preview': 'I was charged twice for my subscription',
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/100',
                        'language': 'English',
                        'translation': None
                    },
                    {
                        'preview': 'Can you explain this invoice?',
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/101',
                        'language': 'English',
                        'translation': None
                    }
                ]
            }
        },
        'Account Issues': {
            'data': {
                'examples': [
                    {
                        'preview': 'I cannot login to my account',
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/102',
                        'language': 'English',
                        'translation': None
                    }
                ]
            }
        },
        'Product Questions': {
            'data': {
                'examples': [
                    {
                        'preview': 'How do I integrate with Salesforce?',
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/103',
                        'language': 'English',
                        'translation': None
                    }
                ]
            }
        }
    }
    
    # Finn performance with sub-topic metrics
    fin_performance_result = {
        'total_fin_conversations': 50,
        'total_free_tier': 30,
        'total_paid_tier': 20,
        'free_tier': {
            'total_conversations': 30,
            'resolution_rate': 0.7,
            'resolved_count': 21,
            'knowledge_gaps_count': 5,
            'knowledge_gap_rate': 0.167,
            'knowledge_gap_examples': [
                {
                    'id': 'fin_gap_1',
                    'preview': 'The information was incorrect',
                    'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/200'
                }
            ],
            'performance_by_topic': {},
            'top_performing_topics': [('Billing Issues', {'resolution_rate': 0.8, 'total': 15})],
            'struggling_topics': [('Account Issues', {'resolution_rate': 0.5, 'total': 10})],
            'performance_by_subtopic': {
                'Billing Issues': {
                    'tier2': {
                        'Refund': {
                            'total': 10,
                            'resolution_rate': 0.8,
                            'knowledge_gap_rate': 0.1,
                            'escalation_rate': 0.1,
                            'avg_rating': 4.5,
                            'rated_count': 8,
                            'resolved_count': 8,
                            'knowledge_gap_count': 1,
                            'escalation_count': 1
                        },
                        'Invoice': {
                            'total': 8,
                            'resolution_rate': 0.75,
                            'knowledge_gap_rate': 0.125,
                            'escalation_rate': 0.125,
                            'avg_rating': 4.0,
                            'rated_count': 6,
                            'resolved_count': 6,
                            'knowledge_gap_count': 1,
                            'escalation_count': 1
                        }
                    },
                    'tier3': {
                        'Refund Processing Delays': {
                            'total': 5,
                            'resolution_rate': 0.6,
                            'knowledge_gap_rate': 0.2,
                            'escalation_rate': 0.2,
                            'avg_rating': None,
                            'rated_count': 0,
                            'resolved_count': 3,
                            'knowledge_gap_count': 1,
                            'escalation_count': 1
                        }
                    }
                },
                'Account Issues': {
                    'tier2': {
                        'Login': {
                            'total': 7,
                            'resolution_rate': 0.57,
                            'knowledge_gap_rate': 0.286,
                            'escalation_rate': 0.143,
                            'avg_rating': 3.5,
                            'rated_count': 4,
                            'resolved_count': 4,
                            'knowledge_gap_count': 2,
                            'escalation_count': 1
                        }
                    },
                    'tier3': {
                        'Login Failures': {
                            'total': 4,
                            'resolution_rate': 0.5,
                            'knowledge_gap_rate': 0.25,
                            'escalation_rate': 0.25,
                            'avg_rating': 3.0,
                            'rated_count': 2,
                            'resolved_count': 2,
                            'knowledge_gap_count': 1,
                            'escalation_count': 1
                        }
                    }
                }
            }
        },
        'paid_tier': {
            'total_conversations': 20,
            'resolution_rate': 0.75,
            'resolved_count': 15,
            'knowledge_gaps_count': 3,
            'knowledge_gap_rate': 0.15,
            'knowledge_gap_examples': [],
            'performance_by_topic': {},
            'top_performing_topics': [('Product Questions', {'resolution_rate': 0.9, 'total': 10})],
            'struggling_topics': [],
            'performance_by_subtopic': {
                'Product Questions': {
                    'tier2': {
                        'Feature': {
                            'total': 6,
                            'resolution_rate': 0.833,
                            'knowledge_gap_rate': 0.0,
                            'escalation_rate': 0.167,
                            'avg_rating': 4.8,
                            'rated_count': 5,
                            'resolved_count': 5,
                            'knowledge_gap_count': 0,
                            'escalation_count': 1
                        }
                    },
                    'tier3': {
                        'Feature Requests': {
                            'total': 4,
                            'resolution_rate': 0.75,
                            'knowledge_gap_rate': 0.0,
                            'escalation_rate': 0.25,
                            'avg_rating': 4.5,
                            'rated_count': 3,
                            'resolved_count': 3,
                            'knowledge_gap_count': 0,
                            'escalation_count': 1
                        }
                    }
                }
            }
        },
        'tier_comparison': {
            'resolution_rate_delta': 0.05,
            'resolution_rate_interpretation': 'Paid tier performs better',
            'knowledge_gap_delta': -0.017,
            'knowledge_gap_interpretation': 'Free tier has more knowledge gaps',
            'free_tier_resolution': 0.7,
            'paid_tier_resolution': 0.75,
            'free_tier_knowledge_gaps': 0.167,
            'paid_tier_knowledge_gaps': 0.15
        }
    }
    
    # Trend result
    trend_result = {
        'trends': {
            'Billing Issues': {'direction': '↑', 'alert': '🔥'},
            'Account Issues': {'direction': '→', 'alert': ''}
        },
        'trend_insights': {
            'Billing Issues': 'Significant increase in billing complaints this week.',
            'Account Issues': 'Stable volume of account issues.'
        }
    }
    
    # Sample conversations
    conversations = [{'id': f'conv_{i}', 'created_at': 1699123456 + i * 1000} for i in range(250)]
    
    return AgentContext(
        conversations=conversations,
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={
            'week_id': '2024-W18',
            'period_type': 'weekly',
            'period_label': 'Weekly'
        },
        previous_results={
            'SegmentationAgent': {'data': segmentation_result},
            'TopicDetectionAgent': {'data': topic_detection_result},
            'SubTopicDetectionAgent': {'data': mock_subtopic_data_for_fin},
            'TopicSentiments': topic_sentiments,
            'TopicExamples': topic_examples,
            'FinPerformanceAgent': {'data': fin_performance_result},
            'TrendAgent': {'data': trend_result}
        }
    )


@pytest.fixture
def sample_orchestrator_conversations():
    """
    Comprehensive list of 70+ conversations for full orchestrator testing.
    
    Includes:
    - 50 paid conversations (mix of human and Finn) with varied topics and sub-topic indicators
    - 20 free conversations (Finn-only) with ai_agent_participated=True
    - All required fields for each agent in the pipeline
    - Realistic Intercom data structure
    """
    from datetime import timezone
    conversations = []
    
    # 50 paid conversations with sub-topic indicators
    topics = ['Billing Issues', 'Account Issues', 'Product Questions']
    for i in range(50):
        topic = topics[i % len(topics)]
        is_finn = i % 4 == 0
        
        conv = {
            'id': f'paid_orch_{i}',
            'created_at': 1699123456 + (i * 3600),
            'updated_at': 1699123456 + (i * 3600) + 1800,
            'state': 'closed',
            'admin_assignee_id': f'admin_{i}',
            'ai_agent_participated': is_finn,
            'conversation_rating': (i % 5) + 1 if i % 3 == 0 else None,
            'detected_topics': [topic],
            # NOTE: full_text and customer_messages should be derived via utilities
            'tags': {'tags': []},
            'conversation_topics': [],
            'custom_attributes': {'Language': 'en'}
        }
        
        # Add sub-topic indicators
        if topic == 'Billing Issues':
            if i % 2 == 0:
                conv['tags']['tags'].append({'name': 'Refund'})
                conv['conversation_topics'].append({'name': 'Refund'})
                # NOTE: Text should be in source/conversation_parts, not full_text
            else:
                conv['tags']['tags'].append({'name': 'Invoice'})
                conv['conversation_topics'].append({'name': 'Invoice'})
                # NOTE: Text should be in source/conversation_parts, not full_text
            conv['custom_attributes']['billing_type'] = 'annual' if i % 4 == 0 else 'monthly'
        elif topic == 'Account Issues':
            conv['tags']['tags'].append({'name': 'Login'})
            conv['conversation_topics'].append({'name': 'Login'})
            conv['custom_attributes']['account_type'] = 'premium' if i % 3 == 0 else 'standard'
            # NOTE: Text should be in source/conversation_parts, not full_text
        else:  # Product Questions
            conv['tags']['tags'].append({'name': 'Feature'})
            conv['conversation_topics'].append({'name': 'Feature'})
            conv['custom_attributes']['product_version'] = 'v2' if i % 5 == 0 else 'v1'
            # NOTE: Text should be in source/conversation_parts, not full_text
        
        conversations.append(conv)
    
    # 20 free conversations (Finn-only)
    for i in range(20):
        conv = {
            'id': f'free_orch_{i}',
            'created_at': 1699123456 + ((i + 50) * 3600),
            'updated_at': 1699123456 + ((i + 50) * 3600) + 900,
            'state': 'closed',
            'admin_assignee_id': 'admin_finn',
            'ai_agent_participated': True,
            'conversation_rating': None,
            'detected_topics': ['Support'],
            # NOTE: full_text and customer_messages should be derived via utilities
            'tags': {'tags': [{'name': 'support'}]},
            'conversation_topics': [],
            'custom_attributes': {'Language': 'en', 'tier': 'free'}
        }
        conversations.append(conv)
    
    return conversations


@pytest.fixture
def mock_orchestrator_week_params():
    """Week parameters for orchestrator testing."""
    from datetime import timezone
    return {
        'week_id': '2024-W42',
        'start_date': datetime(2024, 10, 14, tzinfo=timezone.utc),
        'end_date': datetime(2024, 10, 20, tzinfo=timezone.utc),
        'period_type': 'week',
        'period_label': 'Week of Oct 14-20, 2024'
    }


@pytest.fixture
def sample_admin_profile():
    """Sample admin profile for testing."""
    from src.models.agent_performance_models import AdminProfile
    
    return AdminProfile(
        id="admin_123",
        name="Test Agent",
        email="test.agent@hirehoratio.co",
        public_email="test.agent@hirehoratio.co",
        vendor="horatio",
        active=True,
        cached_at=datetime.now()
    )


@pytest.fixture
def sample_admin_profiles():
    """Multiple admin profiles for testing with various vendors."""
    from src.models.agent_performance_models import AdminProfile
    
    return [
        AdminProfile(
            id="admin_horatio_1",
            name="Horatio Agent 1",
            email="agent1@hirehoratio.co",
            public_email="agent1@hirehoratio.co",
            vendor="horatio",
            active=True,
            cached_at=datetime.now()
        ),
        AdminProfile(
            id="admin_horatio_2",
            name="Horatio Agent 2",
            email="agent2@horatio.com",
            public_email="agent2@horatio.com",
            vendor="horatio",
            active=True,
            cached_at=datetime.now()
        ),
        AdminProfile(
            id="admin_boldr_1",
            name="Boldr Agent 1",
            email="agent1@boldrimpact.com",
            public_email="agent1@boldrimpact.com",
            vendor="boldr",
            active=True,
            cached_at=datetime.now()
        ),
        AdminProfile(
            id="admin_boldr_2",
            name="Boldr Agent 2",
            email="agent2@boldr.com",
            public_email="agent2@boldr.com",
            vendor="boldr",
            active=True,
            cached_at=datetime.now()
        ),
        AdminProfile(
            id="admin_unknown",
            name="Unknown Agent",
            email="agent@example.com",
            public_email="agent@example.com",
            vendor="unknown",
            active=True,
            cached_at=datetime.now()
        ),
    ]


def create_test_conversation(
    conv_id: str,
    state: str = "closed",
    admin_id: str = "admin_123",
    created_at: int = None,
    updated_at: int = None,
    count_reopens: int = 0,
    tags: List[str] = None,
    topics: List[str] = None,
    ai_agent: bool = False,
    rating: int = None,
    escalated_to: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Factory function to create test conversations with consistent structure.
    
    Args:
        conv_id: Conversation ID
        state: Conversation state
        admin_id: Admin assignee ID
        created_at: Creation timestamp (Unix, defaults to now)
        updated_at: Update timestamp (Unix, defaults to created_at + 1 hour)
        count_reopens: Number of reopens
        tags: List of tag names
        topics: List of topic names
        ai_agent: Whether AI agent participated
        rating: Conversation rating (1-5 or None)
        escalated_to: Name of person escalated to (adds to conversation_parts)
        **kwargs: Additional fields to override
        
    Returns:
        Conversation dict matching Intercom structure
    """
    now_ts = int(datetime.now().timestamp())
    created_ts = created_at if created_at is not None else now_ts
    updated_ts = updated_at if updated_at is not None else created_ts + 3600
    
    tags = tags or []
    topics = topics or []
    
    # Build conversation body text
    body_text = f"Customer message for conversation {conv_id}."
    if escalated_to:
        body_text += f" Escalated to {escalated_to}."
    
    conv = {
        'id': conv_id,
        'created_at': created_ts,
        'updated_at': updated_ts,
        'state': state,
        'priority': 'normal',
        'admin_assignee_id': admin_id,
        'conversation_rating': rating,
        'ai_agent_participated': ai_agent,
        'custom_attributes': {
            'Language': 'en',
            'Fin AI Agent: Preview': ai_agent,
            'Copilot used': False
        },
        'statistics': {
            'time_to_admin_reply': 300,
            'handling_time': updated_ts - created_ts,
            'count_conversation_parts': 5,
            'count_reopens': count_reopens
        },
        'tags': {
            'tags': [{'name': tag} for tag in tags]
        },
        'topics': {
            'topics': [{'name': topic} for topic in topics]
        },
        # NOTE: full_text and customer_messages should be derived via utilities, not pre-injected
        'source': {
            'body': f"<p>{body_text}</p>",
            'author': {
                'type': 'user',
                'id': f'user_{conv_id}'
            }
        },
        'conversation_parts': {
            'conversation_parts': [
                {
                    'id': f'part_1_{conv_id}',
                    'type': 'comment',
                    'body': '<p>Admin response</p>',
                    'author': {
                        'type': 'admin',
                        'id': admin_id
                    },
                    'created_at': created_ts + 300
                }
            ]
        }
    }
    
    # Override with any additional kwargs
    conv.update(kwargs)
    
    return conv


def create_test_admin_details(
    admin_id: str,
    name: str = None,
    email: str = None,
    vendor: str = "horatio"
) -> Dict[str, Any]:
    """
    Factory function to create admin detail dictionaries.
    
    Args:
        admin_id: Admin ID
        name: Admin name (defaults to "Agent {id}")
        email: Admin email (defaults to {id}@vendor.com)
        vendor: Vendor name
        
    Returns:
        Admin details dict
    """
    if name is None:
        name = f"Agent {admin_id}"
    
    if email is None:
        vendor_domains = {
            'horatio': 'hirehoratio.co',
            'boldr': 'boldrimpact.com',
            'gamma': 'gamma.app',
            'unknown': 'example.com'
        }
        domain = vendor_domains.get(vendor, 'example.com')
        email = f"{admin_id}@{domain}"
    
    return {
        'id': admin_id,
        'name': name,
        'email': email,
        'vendor': vendor,
        'active': True
    }


@pytest.fixture
def mock_output_formatter_context_without_subtopics():
    """
    Create AgentContext for OutputFormatterAgent testing without sub-topic data (backward compatibility).
    
    This fixture tests that the formatter gracefully handles missing SubTopicDetectionAgent results.
    """
    from src.agents.base_agent import AgentContext
    
    # Segmentation result
    segmentation_result = {
        'segmentation_summary': {
            'paid_count': 150,
            'free_count': 100,
            'paid_percentage': 60.0,
            'free_percentage': 40.0,
            'language_distribution': {
                'en': 180,
                'es': 40,
                'fr': 20
            },
            'total_languages': 3
        }
    }
    
    # Topic detection result
    topic_detection_result = {
        'topic_distribution': {
            'Billing Issues': {
                'volume': 100,
                'percentage': 40.0,
                'detection_method': 'attribute'
            },
            'Account Issues': {
                'volume': 80,
                'percentage': 32.0,
                'detection_method': 'keyword'
            },
            'Product Questions': {
                'volume': 70,
                'percentage': 28.0,
                'detection_method': 'attribute'
            }
        }
    }
    
    # Topic sentiments
    topic_sentiments = {
        'Billing Issues': {
            'data': {
                'sentiment_insight': 'Customers frustrated with billing issues.'
            }
        },
        'Account Issues': {
            'data': {
                'sentiment_insight': 'Users struggle with account issues.'
            }
        },
        'Product Questions': {
            'data': {
                'sentiment_insight': 'Generally positive inquiries.'
            }
        }
    }
    
    # Topic examples
    topic_examples = {
        'Billing Issues': {
            'data': {
                'examples': [
                    {
                        'preview': 'I was charged twice',
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/100',
                        'language': 'English',
                        'translation': None
                    }
                ]
            }
        },
        'Account Issues': {
            'data': {
                'examples': []
            }
        },
        'Product Questions': {
            'data': {
                'examples': []
            }
        }
    }
    
    # Finn performance WITHOUT sub-topic data
    fin_performance_result = {
        'total_fin_conversations': 50,
        'total_free_tier': 30,
        'total_paid_tier': 20,
        'free_tier': {
            'total_conversations': 30,
            'resolution_rate': 0.7,
            'resolved_count': 21,
            'knowledge_gaps_count': 5,
            'knowledge_gap_rate': 0.167,
            'knowledge_gap_examples': [],
            'performance_by_topic': {},
            'top_performing_topics': [('Billing Issues', {'resolution_rate': 0.8, 'total': 15})],
            'struggling_topics': [('Account Issues', {'resolution_rate': 0.5, 'total': 10})],
            'performance_by_subtopic': None  # No sub-topic data
        },
        'paid_tier': {
            'total_conversations': 20,
            'resolution_rate': 0.75,
            'resolved_count': 15,
            'knowledge_gaps_count': 3,
            'knowledge_gap_rate': 0.15,
            'knowledge_gap_examples': [],
            'performance_by_topic': {},
            'top_performing_topics': [('Product Questions', {'resolution_rate': 0.9, 'total': 10})],
            'struggling_topics': [],
            'performance_by_subtopic': None  # No sub-topic data
        }
    }
    
    # Trend result (minimal)
    trend_result = {
        'trends': {},
        'trend_insights': {}
    }
    
    # Sample conversations
    conversations = [{'id': f'conv_{i}', 'created_at': 1699123456 + i * 1000} for i in range(250)]
    
    return AgentContext(
        conversations=conversations,
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={
            'week_id': '2024-W18',
            'period_type': 'weekly',
            'period_label': 'Weekly'
        },
        previous_results={
            'SegmentationAgent': {'data': segmentation_result},
            'TopicDetectionAgent': {'data': topic_detection_result},
            # SubTopicDetectionAgent is MISSING (backward compatibility test)
            'TopicSentiments': topic_sentiments,
            'TopicExamples': topic_examples,
            'FinPerformanceAgent': {'data': fin_performance_result},
            'TrendAgent': {'data': trend_result}
        }
    )






