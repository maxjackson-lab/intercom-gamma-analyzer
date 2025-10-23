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

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

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
        'customer_messages': ['I am having issues with billing charges on my account'],
        'full_text': 'Customer: I am having issues with billing charges on my account. Agent: I can help with that.',
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
        'customer_messages': ['The export feature is not working properly for our team'],
        'full_text': 'Customer: The export feature is not working properly for our team. Agent: Let me investigate.',
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
        'customer_messages': ['I love the new dashboard design but have questions about features'],
        'full_text': 'Customer: I love the new dashboard design but have questions about features.',
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
            'customer_messages': [
                f'I hate this feature because it keeps crashing and losing data. Message {i}.'
            ],
            'full_text': f'Customer message about frustration {i}',
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
            'customer_messages': [
                f'I love the improvements but confused about the new interface. Message {i}.'
            ],
            'full_text': f'Customer feedback message {i}',
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
            'customer_messages': [
                f'I appreciate the quick response time from support. Message {i}.'
            ],
            'full_text': f'Customer appreciation message {i}',
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
            'customer_messages': [
                f'I am frustrated with the billing issues we have been experiencing. Message {i}.'
            ],
            'full_text': f'Customer billing issue message {i}',
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


class MockIntercomService:
    """Mock Intercom service for testing."""
    
    def __init__(self, conversations: List[Dict] = None):
        self.conversations = conversations or []
        self.call_count = 0
    
    async def test_connection(self) -> bool:
        return True
    
    async def fetch_conversations_by_date_range(self, start_date, end_date, max_pages=None):
        self.call_count += 1
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
    return MockIntercomService(sample_conversations)


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






