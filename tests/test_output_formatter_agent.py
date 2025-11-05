"""
Unit tests for OutputFormatterAgent: Validate enhanced output formatting with sub-topic support.

This test suite validates:
1. Topic card formatting with 3-tier sub-topic hierarchies
2. Finn card formatting with sub-topic performance metrics
3. Backward compatibility when sub-topic data is unavailable
4. Helper method formatting (sub-topic metrics line)
5. End-to-end execution with complete agent results
6. Input/output validation
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List

from src.agents.output_formatter_agent import OutputFormatterAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def agent():
    """Create OutputFormatterAgent instance for testing."""
    return OutputFormatterAgent()


@pytest.fixture
def mock_segmentation_result() -> Dict[str, Any]:
    """Create mock SegmentationAgent output."""
    return {
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


@pytest.fixture
def mock_topic_detection_result() -> Dict[str, Any]:
    """Create mock TopicDetectionAgent output."""
    return {
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


@pytest.fixture
def mock_subtopic_detection_result() -> Dict[str, Any]:
    """Create mock SubTopicDetectionAgent output with 3-tier hierarchy."""
    return {
        'subtopics_by_tier1_topic': {
            'Billing Issues': {
                'tier2': {
                    'Refund': {'volume': 30, 'percentage': 30.0, 'source': 'tags'},
                    'Invoice': {'volume': 25, 'percentage': 25.0, 'source': 'tags'},
                    'annual': {'volume': 20, 'percentage': 20.0, 'source': 'custom_attributes'},
                    'monthly': {'volume': 15, 'percentage': 15.0, 'source': 'custom_attributes'},
                    'Payment': {'volume': 10, 'percentage': 10.0, 'source': 'topics'}
                },
                'tier3': {
                    'Refund Processing Delays': {'volume': 20, 'percentage': 20.0, 'keywords': ['refund', 'delay'], 'method': 'llm_semantic'},
                    'Invoice Discrepancies': {'volume': 15, 'percentage': 15.0, 'keywords': ['invoice', 'error'], 'method': 'llm_semantic'},
                    'Payment Method Issues': {'volume': 10, 'percentage': 10.0, 'keywords': ['payment', 'method'], 'method': 'llm_semantic'}
                }
            },
            'Account Issues': {
                'tier2': {
                    'Login': {'volume': 40, 'percentage': 50.0, 'source': 'tags'},
                    'Password': {'volume': 20, 'percentage': 25.0, 'source': 'tags'},
                    'premium': {'volume': 10, 'percentage': 12.5, 'source': 'custom_attributes'},
                    'free': {'volume': 10, 'percentage': 12.5, 'source': 'custom_attributes'}
                },
                'tier3': {
                    'Login Failures': {'volume': 25, 'percentage': 31.2, 'keywords': ['login', 'fail'], 'method': 'llm_semantic'},
                    'Password Reset Issues': {'volume': 15, 'percentage': 18.7, 'keywords': ['password', 'reset'], 'method': 'llm_semantic'}
                }
            },
            'Product Questions': {
                'tier2': {
                    'Feature': {'volume': 30, 'percentage': 42.8, 'source': 'tags'},
                    'Integration': {'volume': 20, 'percentage': 28.6, 'source': 'tags'},
                    'v2': {'volume': 10, 'percentage': 14.3, 'source': 'custom_attributes'},
                    'v1': {'volume': 10, 'percentage': 14.3, 'source': 'custom_attributes'}
                },
                'tier3': {
                    'Feature Requests': {'volume': 20, 'percentage': 28.6, 'keywords': ['feature', 'request'], 'method': 'llm_semantic'},
                    'Usage Questions': {'volume': 15, 'percentage': 21.4, 'keywords': ['how', 'use'], 'method': 'llm_semantic'}
                }
            }
        }
    }


@pytest.fixture
def mock_topic_sentiments() -> Dict[str, Any]:
    """Create mock topic sentiments."""
    return {
        'Billing Issues': {
            'data': {
                'sentiment_insight': 'Customers are frustrated with billing delays and unclear charges.'
            }
        },
        'Account Issues': {
            'data': {
                'sentiment_insight': 'Users struggle with login problems, causing significant frustration.'
            }
        },
        'Product Questions': {
            'data': {
                'sentiment_insight': 'Generally positive inquiries about new features and integrations.'
            }
        }
    }


@pytest.fixture
def mock_topic_examples() -> Dict[str, Any]:
    """Create mock topic examples."""
    return {
        'Billing Issues': {
            'data': {
                'examples': [
                    {
                        'preview': 'I was charged twice for my subscription this month',
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/123',
                        'language': 'English',
                        'translation': None
                    },
                    {
                        'preview': 'Can you explain this invoice?',
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/124',
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
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/125',
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
                        'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/126',
                        'language': 'English',
                        'translation': None
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_fin_performance_with_subtopics() -> Dict[str, Any]:
    """Create mock FinPerformanceAgent output with sub-topic performance data."""
    return {
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
                    'preview': 'The information was incorrect about refunds',
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
            'struggling_topics': [('Billing Issues', {'resolution_rate': 0.6, 'total': 5})],
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


@pytest.fixture
def mock_fin_performance_without_subtopics() -> Dict[str, Any]:
    """Create mock FinPerformanceAgent output without sub-topic performance (backward compatibility)."""
    return {
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
            'performance_by_subtopic': None
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
            'struggling_topics': [('Billing Issues', {'resolution_rate': 0.6, 'total': 5})],
            'performance_by_subtopic': None
        }
    }


@pytest.fixture
def mock_context_with_all_results(
    mock_segmentation_result,
    mock_topic_detection_result,
    mock_subtopic_detection_result,
    mock_topic_sentiments,
    mock_topic_examples,
    mock_fin_performance_with_subtopics
) -> AgentContext:
    """Create AgentContext with all previous_results populated including sub-topics."""
    return AgentContext(
        analysis_id="test-all-results",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={
            'week_id': '2024-W18',
            'period_type': 'weekly',
            'period_label': 'Weekly'
        },
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            'SubTopicDetectionAgent': {'data': mock_subtopic_detection_result},
            'TopicSentiments': mock_topic_sentiments,
            'TopicExamples': mock_topic_examples,
            'FinPerformanceAgent': {'data': mock_fin_performance_with_subtopics},
            'TrendAgent': {
                'data': {
                    'trends': {
                        'Billing Issues': {'direction': '↑', 'alert': '🔥'},
                        'Account Issues': {'direction': '→', 'alert': ''}
                    },
                    'trend_insights': {
                        'Billing Issues': 'Significant increase in billing complaints this week.',
                        'Account Issues': 'Stable volume of account-related issues.'
                    }
                }
            }
        }
    )


@pytest.fixture
def mock_context_without_subtopics(
    mock_segmentation_result,
    mock_topic_detection_result,
    mock_topic_sentiments,
    mock_topic_examples,
    mock_fin_performance_without_subtopics
) -> AgentContext:
    """Create AgentContext without SubTopicDetectionAgent results (backward compatibility)."""
    return AgentContext(
        analysis_id="test-no-subtopics",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={
            'week_id': '2024-W18',
            'period_type': 'weekly',
            'period_label': 'Weekly'
        },
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            'TopicSentiments': mock_topic_sentiments,
            'TopicExamples': mock_topic_examples,
            'FinPerformanceAgent': {'data': mock_fin_performance_without_subtopics},
            'TrendAgent': {
                'data': {
                    'trends': {},
                    'trend_insights': {}
                }
            }
        }
    )


# ============================================================================
# TEST CASES
# ============================================================================

def test_validate_input_success(agent, mock_context_with_all_results):
    """Verify validation passes with required agents present."""
    assert agent.validate_input(mock_context_with_all_results) is True


def test_validate_input_missing_required_agent(agent):
    """Verify validation fails when required agent is missing."""
    context = AgentContext(
        analysis_id="test-missing",
        analysis_type="weekly",
        conversations=[],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        previous_results={'SegmentationAgent': {'data': {}}}  # Missing TopicDetectionAgent
    )
    
    with pytest.raises(ValueError, match="Missing required agent outputs"):
        agent.validate_input(context)


def test_validate_output_success(agent):
    """Verify validation passes when result contains formatted_output."""
    result = {'formatted_output': 'Test output'}
    assert agent.validate_output(result) is True


def test_validate_output_failure(agent):
    """Verify validation fails when formatted_output is missing."""
    result = {'some_other_key': 'value'}
    assert agent.validate_output(result) is False


def test_format_topic_card_without_subtopics(agent):
    """Test _format_topic_card() with subtopics=None (backward compatibility)."""
    stats = {'volume': 100, 'percentage': 40.0, 'detection_method': 'attribute'}
    sentiment = 'Frustrated customers with billing issues'
    examples = [
        {
            'preview': 'I was charged twice',
            'intercom_url': 'https://app.intercom.com/a/apps/test/inbox/inbox/123',
            'language': 'English',
            'translation': None
        }
    ]
    trend = ' ↑ 🔥'
    trend_explanation = 'Significant increase this week'
    
    card = agent._format_topic_card(
        'Billing Issues',
        stats,
        sentiment,
        examples,
        trend,
        trend_explanation,
        'Weekly',
        subtopics=None
    )
    
    # Verify basic structure
    assert '### Billing Issues ↑ 🔥' in card
    assert '100 tickets / 40.0% of weekly volume' in card
    assert 'Frustrated customers with billing issues' in card
    assert 'Significant increase this week' in card
    assert '**Examples**:' in card
    assert 'I was charged twice' in card
    
    # Verify NO sub-topic section
    assert 'Sub-Topic Breakdown' not in card
    assert 'Tier 2: From Intercom Data' not in card
    assert 'Tier 3: AI-Discovered Themes' not in card


def test_format_topic_card_with_tier2_subtopics(agent, mock_subtopic_detection_result):
    """Test _format_topic_card() with Tier 2 sub-topics."""
    stats = {'volume': 100, 'percentage': 40.0, 'detection_method': 'attribute'}
    sentiment = 'Frustrated customers'
    examples = []
    subtopics = mock_subtopic_detection_result['subtopics_by_tier1_topic']['Billing Issues']
    
    card = agent._format_topic_card(
        'Billing Issues',
        stats,
        sentiment,
        examples,
        '',
        '',
        'Weekly',
        subtopics=subtopics
    )
    
    # Verify sub-topic section exists
    assert '**Sub-Topic Breakdown**:' in card
    assert '_Tier 2: From Intercom Data_' in card
    
    # Verify Tier 2 sub-topics are present
    assert 'Refund: 30 conversations (30.0%) [Source: tags]' in card
    assert 'Invoice: 25 conversations (25.0%) [Source: tags]' in card
    assert 'annual: 20 conversations (20.0%) [Source: custom_attributes]' in card
    
    # Verify sorted by volume (descending)
    refund_idx = card.index('Refund:')
    invoice_idx = card.index('Invoice:')
    annual_idx = card.index('annual:')
    assert refund_idx < invoice_idx < annual_idx


def test_format_topic_card_with_tier3_subtopics(agent, mock_subtopic_detection_result):
    """Test _format_topic_card() with Tier 3 themes."""
    stats = {'volume': 100, 'percentage': 40.0, 'detection_method': 'attribute'}
    sentiment = 'Frustrated customers'
    examples = []
    subtopics = mock_subtopic_detection_result['subtopics_by_tier1_topic']['Billing Issues']
    
    card = agent._format_topic_card(
        'Billing Issues',
        stats,
        sentiment,
        examples,
        '',
        '',
        'Weekly',
        subtopics=subtopics
    )
    
    # Verify Tier 3 section exists
    assert '_Tier 3: AI-Discovered Themes_' in card
    
    # Verify Tier 3 themes are present
    assert 'Refund Processing Delays: 20 conversations (20.0%)' in card
    assert 'Invoice Discrepancies: 15 conversations (15.0%)' in card
    
    # Verify sorted by volume (descending)
    refund_delay_idx = card.index('Refund Processing Delays:')
    invoice_disc_idx = card.index('Invoice Discrepancies:')
    assert refund_delay_idx < invoice_disc_idx


def test_format_topic_card_with_both_tiers(agent, mock_subtopic_detection_result):
    """Test _format_topic_card() with both Tier 2 and Tier 3."""
    stats = {'volume': 80, 'percentage': 32.0, 'detection_method': 'keyword'}
    sentiment = 'Users struggle with login'
    examples = []
    subtopics = mock_subtopic_detection_result['subtopics_by_tier1_topic']['Account Issues']
    
    card = agent._format_topic_card(
        'Account Issues',
        stats,
        sentiment,
        examples,
        '',
        '',
        'Weekly',
        subtopics=subtopics
    )
    
    # Verify both sections exist
    assert '**Sub-Topic Breakdown**:' in card
    assert '_Tier 2: From Intercom Data_' in card
    assert '_Tier 3: AI-Discovered Themes_' in card
    
    # Verify Tier 2 before Tier 3
    tier2_idx = card.index('_Tier 2: From Intercom Data_')
    tier3_idx = card.index('_Tier 3: AI-Discovered Themes_')
    assert tier2_idx < tier3_idx


def test_format_subtopic_metrics_line(agent):
    """Test _format_subtopic_metrics_line() helper with all metrics present."""
    metrics = {
        'total': 10,
        'resolution_rate': 0.8,
        'knowledge_gap_rate': 0.1,
        'escalation_rate': 0.1,
        'avg_rating': 4.5,
        'rated_count': 8
    }
    
    line = agent._format_subtopic_metrics_line('Refund', metrics)
    
    assert 'Refund:' in line
    assert '80.0% resolution' in line
    assert '10.0% gaps' in line
    assert '10.0% escalation' in line
    assert '⭐ 4.5/5 (8 rated)' in line
    assert '(10 convs)' in line


def test_format_subtopic_metrics_line_without_rating(agent):
    """Test _format_subtopic_metrics_line() when avg_rating is None."""
    metrics = {
        'total': 5,
        'resolution_rate': 0.6,
        'knowledge_gap_rate': 0.2,
        'escalation_rate': 0.2,
        'avg_rating': None,
        'rated_count': 0
    }
    
    line = agent._format_subtopic_metrics_line('Login', metrics)
    
    assert 'Login:' in line
    assert '60.0% resolution' in line
    assert '20.0% gaps' in line
    assert '20.0% escalation' in line
    assert '⭐' not in line  # No rating shown
    assert '(5 convs)' in line


def test_format_free_tier_fin_card_without_subtopics(agent, mock_fin_performance_without_subtopics):
    """Test free tier card without sub-topic performance (backward compatibility)."""
    card = agent._format_free_tier_fin_card(mock_fin_performance_without_subtopics)
    
    # Verify basic structure exists
    assert '### Free Tier: Fin AI Performance (AI-Only Support)' in card
    assert '30 conversations from Free tier customers' in card
    assert 'Resolution rate: 70.0%' in card
    assert 'Knowledge gaps: 5 conversations' in card
    
    # Verify NO sub-topic section
    assert 'Performance by Sub-Topic' not in card


def test_format_free_tier_fin_card_with_subtopics(agent, mock_fin_performance_with_subtopics):
    """Test free tier card with sub-topic performance data."""
    card = agent._format_free_tier_fin_card(mock_fin_performance_with_subtopics)
    
    # Verify sub-topic section exists
    assert '**Performance by Sub-Topic**:' in card
    
    # Verify Tier 1 topic headers
    assert '_Billing Issues_' in card
    assert '_Account Issues_' in card
    
    # Verify Tier 2 metrics are shown
    assert 'Refund: 80.0% resolution | 10.0% gaps | 10.0% escalation | ⭐ 4.5/5 (8 rated) (10 convs)' in card
    assert 'Invoice: 75.0% resolution | 12.5% gaps | 12.5% escalation | ⭐ 4.0/5 (6 rated) (8 convs)' in card
    
    # Verify Tier 3 metrics are shown (without rating)
    assert 'Refund Processing Delays: 60.0% resolution | 20.0% gaps | 20.0% escalation (5 convs)' in card


def test_format_paid_tier_fin_card_without_subtopics(agent, mock_fin_performance_without_subtopics):
    """Test paid tier card without sub-topic performance (backward compatibility)."""
    card = agent._format_paid_tier_fin_card(mock_fin_performance_without_subtopics)
    
    # Verify basic structure exists
    assert '### Paid Tier: Fin-Resolved Conversations' in card
    assert '20 paid customers resolved their issues with Fin AI' in card
    assert 'Resolution rate: 75.0%' in card
    
    # Verify NO sub-topic section
    assert 'Performance by Sub-Topic' not in card


def test_format_paid_tier_fin_card_with_subtopics(agent, mock_fin_performance_with_subtopics):
    """Test paid tier card with sub-topic performance data."""
    card = agent._format_paid_tier_fin_card(mock_fin_performance_with_subtopics)
    
    # Verify sub-topic section exists
    assert '**Performance by Sub-Topic**:' in card
    
    # Verify Tier 1 topic header
    assert '_Product Questions_' in card
    
    # Verify Tier 2 metrics are shown
    assert 'Feature: 83.3% resolution | 0.0% gaps | 16.7% escalation | ⭐ 4.8/5 (5 rated) (6 convs)' in card
    
    # Verify Tier 3 metrics are shown
    assert 'Feature Requests: 75.0% resolution | 0.0% gaps | 25.0% escalation | ⭐ 4.5/5 (3 rated) (4 convs)' in card


@pytest.mark.asyncio
async def test_execute_end_to_end_with_subtopics(agent, mock_context_with_all_results):
    """Test full execution with all data including sub-topics."""
    result = await agent.execute(mock_context_with_all_results)
    
    # Verify success
    assert result.success is True
    assert result.agent_name == 'OutputFormatterAgent'
    assert 'formatted_output' in result.data
    
    output = result.data['formatted_output']
    
    # Verify header
    assert 'Voice of Customer Analysis' in output
    assert 'May 01 - May 31, 2024' in output
    
    # Verify executive summary
    assert 'Executive Summary' in output
    assert '250 conversations analyzed' in output
    
    # Verify topic cards with sub-topics
    assert '### Billing Issues' in output
    assert '**Sub-Topic Breakdown**:' in output
    assert '_Tier 2: From Intercom Data_' in output
    assert '_Tier 3: AI-Discovered Themes_' in output
    assert 'Refund: 30 conversations (30.0%) [Source: tags]' in output
    
    # Verify Finn cards with sub-topic performance
    assert '### Free Tier: Fin AI Performance (AI-Only Support)' in output
    assert '**Performance by Sub-Topic**:' in output
    assert '_Billing Issues_' in output
    assert 'Refund: 80.0% resolution | 10.0% gaps | 10.0% escalation' in output
    
    # Verify metadata
    assert result.data['total_topics'] == 3
    assert result.data['has_trend_data'] is True


@pytest.mark.asyncio
async def test_execute_end_to_end_without_subtopics(agent, mock_context_without_subtopics):
    """Test full execution without SubTopicDetectionAgent results (backward compatibility)."""
    result = await agent.execute(mock_context_without_subtopics)
    
    # Verify success
    assert result.success is True
    assert 'formatted_output' in result.data
    
    output = result.data['formatted_output']
    
    # Verify topic cards exist but WITHOUT sub-topic sections
    assert '### Billing Issues' in output
    assert '**Sub-Topic Breakdown**:' not in output
    assert '_Tier 2: From Intercom Data_' not in output
    assert '_Tier 3: AI-Discovered Themes_' not in output
    
    # Verify Finn cards exist but WITHOUT sub-topic performance
    assert '### Free Tier: Fin AI Performance (AI-Only Support)' in output
    assert '**Performance by Sub-Topic**:' not in output


def test_subtopic_section_ordering(agent, mock_subtopic_detection_result):
    """Verify Tier 2 appears before Tier 3 in output."""
    stats = {'volume': 100, 'percentage': 40.0, 'detection_method': 'attribute'}
    sentiment = 'Test'
    subtopics = mock_subtopic_detection_result['subtopics_by_tier1_topic']['Billing Issues']
    
    card = agent._format_topic_card(
        'Billing Issues',
        stats,
        sentiment,
        [],
        '',
        '',
        'Weekly',
        subtopics=subtopics
    )
    
    tier2_idx = card.index('_Tier 2: From Intercom Data_')
    tier3_idx = card.index('_Tier 3: AI-Discovered Themes_')
    
    assert tier2_idx < tier3_idx


def test_subtopic_limiting(agent):
    """Verify top 10 Tier 2 and top 5 Tier 3 limits are enforced."""
    # Create 15 Tier 2 sub-topics and 10 Tier 3 themes
    subtopics = {
        'tier2': {f'Subtopic_{i}': {'volume': 100-i, 'percentage': 10.0, 'source': 'tags'} for i in range(15)},
        'tier3': {f'Theme_{i}': {'volume': 50-i, 'percentage': 5.0} for i in range(10)}
    }
    
    stats = {'volume': 100, 'percentage': 40.0, 'detection_method': 'attribute'}
    
    card = agent._format_topic_card(
        'Test Topic',
        stats,
        'Test sentiment',
        [],
        '',
        '',
        'Weekly',
        subtopics=subtopics
    )
    
    # Count tier2 entries
    tier2_section_start = card.index('_Tier 2: From Intercom Data_')
    tier3_section_start = card.index('_Tier 3: AI-Discovered Themes_')
    tier2_section = card[tier2_section_start:tier3_section_start]
    
    tier2_count = sum(1 for line in tier2_section.split('\n') if 'Subtopic_' in line)
    assert tier2_count == 10  # Top 10 only
    
    # Count tier3 entries
    tier3_section = card[tier3_section_start:]
    tier3_count = sum(1 for line in tier3_section.split('\n') if 'Theme_' in line)
    assert tier3_count == 5  # Top 5 only


def test_empty_subtopic_tiers(agent):
    """Test when tier2 or tier3 is empty dict."""
    # Empty tier2, has tier3
    subtopics_no_tier2 = {
        'tier2': {},
        'tier3': {'Theme A': {'volume': 10, 'percentage': 10.0}}
    }
    
    stats = {'volume': 100, 'percentage': 40.0, 'detection_method': 'attribute'}
    
    card = agent._format_topic_card(
        'Test Topic',
        stats,
        'Test',
        [],
        '',
        '',
        'Weekly',
        subtopics=subtopics_no_tier2
    )
    
    # Should show sub-topic section with only tier3
    assert '**Sub-Topic Breakdown**:' in card
    assert '_Tier 2: From Intercom Data_' not in card
    assert '_Tier 3: AI-Discovered Themes_' in card
    
    # Empty tier3, has tier2
    subtopics_no_tier3 = {
        'tier2': {'SubA': {'volume': 10, 'percentage': 10.0, 'source': 'tags'}},
        'tier3': {}
    }
    
    card2 = agent._format_topic_card(
        'Test Topic',
        stats,
        'Test',
        [],
        '',
        '',
        'Weekly',
        subtopics=subtopics_no_tier3
    )
    
    # Should show sub-topic section with only tier2
    assert '**Sub-Topic Breakdown**:' in card2
    assert '_Tier 2: From Intercom Data_' in card2
    assert '_Tier 3: AI-Discovered Themes_' not in card2


def test_subtopic_metrics_sorting_by_resolution_rate(agent, mock_fin_performance_with_subtopics):
    """Verify sub-topic metrics are sorted by resolution rate descending."""
    card = agent._format_free_tier_fin_card(mock_fin_performance_with_subtopics)
    
    # Within Billing Issues tier2, Refund (80%) should appear before Invoice (75%)
    refund_idx = card.index('Refund: 80.0%')
    invoice_idx = card.index('Invoice: 75.0%')
    
    assert refund_idx < invoice_idx


# ============================================================================
# GRACEFUL DEGRADATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_missing_segmentation_agent(agent):
    """Test formatter handles missing SegmentationAgent output"""
    context = AgentContext(
        analysis_id="test-001",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(100)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'TopicDetectionAgent': {
                'data': {'topic_distribution': {'Billing': {'volume': 10, 'percentage': 10.0}}}
            },
            # 'SegmentationAgent': missing
        }
    )
    
    # Should return error result (SegmentationAgent is required)
    result = await agent.execute(context)
    assert result.success is False
    assert "Missing required agent" in result.error_message


@pytest.mark.asyncio
async def test_missing_topic_detection_agent(agent):
    """Test formatter fails when TopicDetectionAgent output missing"""
    context = AgentContext(
        analysis_id="test-002",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(100)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {
                'data': {'segmentation_summary': {'paid_count': 50, 'free_count': 50}}
            },
            # 'TopicDetectionAgent': missing (required)
        }
    )
    
    # Should return error result (topics are required)
    result = await agent.execute(context)
    assert result.success is False
    assert "Missing required agent" in result.error_message


@pytest.mark.asyncio
async def test_missing_trend_agent(agent, mock_segmentation_result, mock_topic_detection_result):
    """Test formatter handles missing TrendAgent output"""
    context = AgentContext(
        analysis_id="test-003",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            'TopicSentiments': {
                'Billing Issues': {'data': {'sentiment_insight': 'Frustrated'}}
            },
            'TopicExamples': {
                'Billing Issues': {'data': {'examples': []}}
            },
            # 'TrendAgent': missing (optional)
        }
    )
    
    result = await agent.execute(context)
    
    assert result.success is True
    output = result.data.get('formatted_output', '')
    # Should not crash and should not show trend indicators
    assert 'Billing Issues' in output
    assert result.data['has_trend_data'] is False


@pytest.mark.asyncio
async def test_missing_fin_agent(agent, mock_segmentation_result, mock_topic_detection_result):
    """Test formatter handles missing FinPerformanceAgent output"""
    context = AgentContext(
        analysis_id="test-004",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            'TopicSentiments': {
                'Billing Issues': {'data': {'sentiment_insight': 'Frustrated'}}
            },
            'TopicExamples': {
                'Billing Issues': {'data': {'examples': []}}
            },
            # 'FinPerformanceAgent': missing (optional)
        }
    )
    
    result = await agent.execute(context)
    
    assert result.success is True
    output = result.data.get('formatted_output', '')
    # Should include placeholder message
    assert 'Fin AI Performance Analysis' in output
    assert 'Section Unavailable' in output
    assert 'FinPerformanceAgent' in output
    assert '⚠️' in output


@pytest.mark.asyncio
async def test_missing_subtopic_agent(agent, mock_segmentation_result, mock_topic_detection_result):
    """Test formatter handles missing SubTopicDetectionAgent output"""
    context = AgentContext(
        analysis_id="test-005",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            'TopicSentiments': {
                'Billing Issues': {'data': {'sentiment_insight': 'Frustrated'}}
            },
            'TopicExamples': {
                'Billing Issues': {'data': {'examples': []}}
            },
            # 'SubTopicDetectionAgent': missing (optional)
        }
    )
    
    result = await agent.execute(context)
    
    assert result.success is True
    output = result.data.get('formatted_output', '')
    # Should not crash, should not show sub-topic sections
    assert 'Billing Issues' in output
    assert 'Sub-Topic Breakdown' not in output


@pytest.mark.asyncio
async def test_all_sections_present(agent, mock_context_with_all_results):
    """Test formatter works normally when all sections present"""
    result = await agent.execute(mock_context_with_all_results)
    
    assert result.success is True
    output = result.data.get('formatted_output', '')
    # Should not include placeholder messages
    assert 'Section Unavailable' not in output
    assert '⚠️' not in output or '⭐' in output  # ⭐ is for ratings, ⚠️ should only be in placeholders


@pytest.mark.asyncio
async def test_placeholder_message_format(agent):
    """Test placeholder messages are properly formatted"""
    placeholder = agent._generate_missing_section_placeholder(
        "Test Section",
        "TestAgent"
    )
    
    # Should be markdown formatted
    assert '##' in placeholder  # Heading
    assert '⚠️' in placeholder  # Warning icon
    assert 'Section Unavailable' in placeholder
    assert 'TestAgent' in placeholder
    assert '---' in placeholder  # Separator
    assert 'did not complete successfully or was not run' in placeholder
    assert 'ensure the TestAgent runs successfully' in placeholder


@pytest.mark.asyncio
async def test_warnings_logged_for_missing(agent, mock_segmentation_result, mock_topic_detection_result, caplog):
    """Test warnings are logged for missing optional sections"""
    import logging
    caplog.set_level(logging.WARNING)
    
    context = AgentContext(
        analysis_id="test-007",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            # Missing: TrendAgent, FinPerformanceAgent, SubTopicDetectionAgent, TopicSentiments, TopicExamples
        }
    )
    
    result = await agent.execute(context)
    
    # Should log warning
    assert any('Missing optional' in record.message for record in caplog.records)
    # Should still succeed
    assert result.success is True


@pytest.mark.asyncio
async def test_missing_multiple_optional_agents(agent, mock_segmentation_result, mock_topic_detection_result):
    """Test formatter handles multiple missing optional sections"""
    context = AgentContext(
        analysis_id="test-008",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            # Missing: All optional agents
        }
    )
    
    result = await agent.execute(context)
    
    assert result.success is True
    output = result.data.get('formatted_output', '')
    # Should include FIN placeholder
    assert 'Section Unavailable' in output
    assert 'FinPerformanceAgent' in output


@pytest.mark.asyncio
async def test_empty_fin_performance_data(agent, mock_segmentation_result, mock_topic_detection_result):
    """Test formatter handles empty FinPerformanceAgent data"""
    context = AgentContext(
        analysis_id="test-009",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
            'TopicSentiments': {},
            'TopicExamples': {},
            'FinPerformanceAgent': {'data': {}},  # Empty data
        }
    )
    
    result = await agent.execute(context)
    
    assert result.success is True
    output = result.data.get('formatted_output', '')
    # Should show placeholder for empty FIN data
    assert 'Section Unavailable' in output or 'Fin AI Performance Analysis' in output


@pytest.mark.asyncio
async def test_validate_input_info_logging(agent, mock_segmentation_result, mock_topic_detection_result, caplog):
    """Test validate_input logs info about present and missing sections"""
    import logging
    caplog.set_level(logging.INFO)
    
    context = AgentContext(
        analysis_id="test-010",
        analysis_type="weekly",
        conversations=[{'id': f'conv_{i}'} for i in range(250)],
        start_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 5, 31, tzinfo=timezone.utc),
        metadata={'week_id': '2024-W18'},
        previous_results={
            'SegmentationAgent': {'data': mock_segmentation_result},
            'TopicDetectionAgent': {'data': mock_topic_detection_result},
        }
    )
    
    agent.validate_input(context)
    
    # Should log validation complete message with counts
    assert any('Input validation complete' in record.message for record in caplog.records)
    assert any('Present:' in record.message and 'Missing optional:' in record.message for record in caplog.records)


def test_expected_agents_configuration(agent):
    """Test EXPECTED_AGENTS configuration is properly defined"""
    expected_agents = agent.EXPECTED_AGENTS
    
    # Verify structure
    assert isinstance(expected_agents, dict)
    assert len(expected_agents) > 0
    
    # Verify required agents
    assert expected_agents['SegmentationAgent']['required'] is True
    assert expected_agents['TopicDetectionAgent']['required'] is True
    
    # Verify optional agents
    assert expected_agents['SubTopicDetectionAgent']['required'] is False
    assert expected_agents['TrendAgent']['required'] is False
    assert expected_agents['FinPerformanceAgent']['required'] is False
    
    # Verify all have keys
    for agent_name, config in expected_agents.items():
        assert 'required' in config
        assert 'key' in config
        assert isinstance(config['required'], bool)
        assert isinstance(config['key'], str)


# ============================================================================
# TEST CASES FOR PHASE 3: Week-over-Week Comparison Section
# ============================================================================

@pytest.fixture
def sample_comparison_data() -> Dict[str, Any]:
    """Create sample comparison data with all fields"""
    return {
        'comparison_id': 'comp_weekly_20251114_weekly_20251107',
        'volume_changes': {
            'Billing': {'change': 7, 'pct': 0.156, 'current': 52, 'prior': 45},
            'API': {'change': 34, 'pct': 1.889, 'current': 52, 'prior': 18},
            'Sites': {'change': 3, 'pct': 0.136, 'current': 25, 'prior': 22}
        },
        'sentiment_changes': {
            'Billing': {'positive_delta': 0.15, 'negative_delta': -0.10, 'shift': 'more positive'},
            'API': {'positive_delta': -0.12, 'negative_delta': 0.12, 'shift': 'more negative'}
        },
        'resolution_changes': {
            'fcr_rate_delta': 0.03,
            'resolution_time_delta': -0.5,
            'interpretation': 'improving'
        },
        'significant_changes': [
            {'topic': 'API', 'change': 34, 'pct': 1.889, 'direction': 'increasing', 'alert': '⚠️', 'current': 52, 'prior': 18}
        ],
        'emerging_patterns': [
            {'topic': 'NewFeature', 'volume': 12, 'context': 'New topic appeared this period'}
        ],
        'declining_patterns': [
            {'topic': 'OldIssue', 'prior_volume': 8, 'context': 'Topic disappeared this period'}
        ]
    }


def test_format_comparison_section_includes_all_subsections(agent, sample_comparison_data):
    """Test comparison section includes all subsections"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    # Verify all subsection headers present
    assert '## Week-over-Week Changes 📊' in result
    assert '### Volume Changes' in result
    assert '### Significant Changes' in result
    assert '### Emerging Patterns (New Topics)' in result
    assert '### Declining Patterns (Disappeared Topics)' in result
    assert '### Sentiment Shifts' in result
    assert '### Resolution Quality Changes' in result


def test_format_comparison_section_handles_missing_data(agent):
    """Test comparison section handles incomplete data gracefully"""
    incomplete_data = {
        'volume_changes': {'Billing': {'change': 5, 'pct': 0.1, 'current': 55, 'prior': 50}},
        # Missing: sentiment_changes, resolution_changes, etc.
    }
    
    result = agent._format_comparison_section(incomplete_data)
    
    # Should not crash
    assert '## Week-over-Week Changes 📊' in result
    assert '### Volume Changes' in result
    # Should not include missing subsections
    assert '### Sentiment Shifts' not in result


def test_format_comparison_section_formats_volume_changes_correctly(agent, sample_comparison_data):
    """Test volume changes are formatted correctly"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    # Verify formatting
    assert '**Billing**: 52 conversations (+7, +15.6%)' in result
    assert '**API**: 52 conversations (+34, +188.9%)' in result
    assert '**Sites**: 25 conversations (+3, +13.6%)' in result


def test_format_comparison_section_highlights_significant_changes(agent, sample_comparison_data):
    """Test significant changes are highlighted"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    assert '### Significant Changes' in result
    assert '⚠️ **API**: +34 conversations (+188.9%)' in result
    assert '_Interpretation: increasing trend detected_' in result


def test_format_comparison_section_shows_emerging_patterns(agent, sample_comparison_data):
    """Test emerging patterns are shown"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    assert '### Emerging Patterns (New Topics) 🆕' in result
    assert '**NewFeature**: 12 conversations (new this period)' in result
    assert '_These topics appeared for the first time this period_' in result


def test_format_comparison_section_shows_declining_patterns(agent, sample_comparison_data):
    """Test declining patterns are shown"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    assert '### Declining Patterns (Disappeared Topics) 📉' in result
    assert '**OldIssue**: 8 conversations last period (disappeared)' in result
    assert '_These topics were present last period but not this period_' in result


def test_format_comparison_section_shows_sentiment_shifts(agent, sample_comparison_data):
    """Test sentiment shifts are shown for notable changes"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    assert '### Sentiment Shifts' in result
    assert '**Billing**: more positive (+15.0% positive sentiment)' in result
    assert '**API**: more negative (-12.0% positive sentiment)' in result


def test_format_comparison_section_shows_resolution_changes(agent, sample_comparison_data):
    """Test resolution quality changes are shown"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    assert '### Resolution Quality Changes' in result
    assert '**First Contact Resolution**: +3.0% (improving)' in result
    assert '**Median Resolution Time**: -0.5 hours (improving)' in result
    assert '_Overall: Resolution quality is **improving**_' in result


@pytest.mark.asyncio
async def test_execute_includes_comparison_section_when_available(agent, mock_context_with_all_results, sample_comparison_data):
    """Test execute() includes comparison section when data is available"""
    # Add comparison data to context metadata
    mock_context_with_all_results.metadata['comparison_data'] = sample_comparison_data
    
    result = await agent.execute(mock_context_with_all_results)
    
    assert result.success is True
    formatted_output = result.data['formatted_output']
    
    # Verify comparison section is present
    assert 'Week-over-Week Changes 📊' in formatted_output
    assert '### Volume Changes' in formatted_output


@pytest.mark.asyncio
async def test_execute_skips_comparison_section_when_not_available(agent, mock_context_with_all_results, caplog):
    """Test execute() skips comparison section when not available"""
    import logging
    caplog.set_level(logging.INFO)
    
    # No comparison_data in metadata
    result = await agent.execute(mock_context_with_all_results)
    
    assert result.success is True
    formatted_output = result.data['formatted_output']
    
    # Verify comparison section is NOT present
    assert 'Week-over-Week Changes' not in formatted_output
    
    # Verify info log message
    assert any('No prior snapshot available' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_execute_handles_comparison_formatting_error_gracefully(agent, mock_context_with_all_results):
    """Test execute() handles malformed comparison data gracefully"""
    # Add malformed comparison data
    mock_context_with_all_results.metadata['comparison_data'] = {'invalid': 'data'}
    
    result = await agent.execute(mock_context_with_all_results)
    
    # Should still succeed (doesn't fail entire analysis)
    assert result.success is True
    
    # Rest of report should still be generated
    formatted_output = result.data['formatted_output']
    assert 'Executive Summary' in formatted_output
    assert 'Customer Topics' in formatted_output


def test_comparison_section_markdown_validity(agent, sample_comparison_data):
    """Test comparison section generates valid markdown"""
    result = agent._format_comparison_section(sample_comparison_data)
    
    # Verify basic markdown structure
    assert result.startswith('##')  # Level 2 heading
    assert '###' in result  # Level 3 headings
    assert '**' in result  # Bold text
    assert '_' in result  # Italic text
    
    # Verify no syntax errors (no unmatched brackets/parentheses)
    assert result.count('[') == result.count(']')
    assert result.count('(') == result.count(')')


def test_format_comparison_section_empty_subsections(agent):
    """Test comparison section when all lists are empty"""
    empty_data = {
        'volume_changes': {},
        'sentiment_changes': {},
        'resolution_changes': {},
        'significant_changes': [],
        'emerging_patterns': [],
        'declining_patterns': []
    }
    
    result = agent._format_comparison_section(empty_data)
    
    # Should still have header
    assert '## Week-over-Week Changes 📊' in result
    # Should not have any subsections
    assert '###' not in result


def test_format_comparison_section_volume_sorting(agent):
    """Test volume changes are sorted by absolute change descending"""
    data = {
        'volume_changes': {
            'TopicA': {'change': 5, 'pct': 0.1, 'current': 55, 'prior': 50},
            'TopicB': {'change': -15, 'pct': -0.3, 'current': 35, 'prior': 50},
            'TopicC': {'change': 25, 'pct': 0.5, 'current': 75, 'prior': 50}
        }
    }
    
    result = agent._format_comparison_section(data)
    
    # TopicC should appear first (abs(25) largest), then TopicB (abs(15)), then TopicA (abs(5))
    topic_c_idx = result.index('TopicC')
    topic_b_idx = result.index('TopicB')
    topic_a_idx = result.index('TopicA')
    
    assert topic_c_idx < topic_b_idx < topic_a_idx


def test_format_comparison_section_volume_limit(agent):
    """Test volume changes are limited to top 10"""
    # Create 15 volume changes
    volume_changes = {
        f'Topic{i}': {'change': 100-i, 'pct': 0.1, 'current': 200, 'prior': 100}
        for i in range(15)
    }
    
    data = {'volume_changes': volume_changes}
    result = agent._format_comparison_section(data)
    
    # Count topic entries in volume changes section
    volume_section = result.split('###')[1]  # Get Volume Changes section
    topic_count = sum(1 for line in volume_section.split('\n') if 'Topic' in line and '**' in line)
    
    assert topic_count == 10  # Limited to top 10


def test_format_comparison_section_sentiment_limit(agent):
    """Test sentiment shifts are limited to top 5"""
    # Create 10 sentiment changes (all notable)
    sentiment_changes = {
        f'Topic{i}': {'positive_delta': 0.15-i*0.01, 'negative_delta': 0.0, 'shift': 'more positive'}
        for i in range(10)
    }
    
    data = {'sentiment_changes': sentiment_changes}
    result = agent._format_comparison_section(data)
    
    # Count sentiment entries
    if '### Sentiment Shifts' in result:
        sentiment_section = result.split('### Sentiment Shifts')[1].split('###')[0]
        topic_count = sum(1 for line in sentiment_section.split('\n') if 'Topic' in line and '**' in line)
        assert topic_count <= 5  # Limited to top 5

