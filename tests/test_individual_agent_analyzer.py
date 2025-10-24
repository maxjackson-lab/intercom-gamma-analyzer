"""
Tests for individual agent performance analyzer with taxonomy breakdown.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List

from src.services.individual_agent_analyzer import IndividualAgentAnalyzer
from src.models.agent_performance_models import IndividualAgentMetrics, CategoryPerformance


@pytest.fixture
def mock_admin_cache():
    """Mock AdminProfileCache"""
    cache = Mock()
    cache.session_cache = {}
    return cache


@pytest.fixture
def sample_conversations() -> List[Dict]:
    """Sample conversations with admin details"""
    return [
        {
            'id': 'conv_1',
            'created_at': 1699123456,
            'updated_at': 1699125456,
            'state': 'closed',
            'count_reopens': 0,
            'time_to_admin_reply': 3600,
            'count_conversation_parts': 3,
            'full_text': 'Customer: Billing issue. Agent: Resolved.',
            'tags': {'tags': [{'name': 'Billing'}]},
            '_admin_details': [{'id': 'agent1', 'name': 'Maria', 'email': 'maria@hirehoratio.co', 'vendor': 'horatio'}]
        },
        {
            'id': 'conv_2',
            'created_at': 1699123456,
            'updated_at': 1699135456,  # Longer resolution
            'state': 'closed',
            'count_reopens': 1,  # Reopened
            'time_to_admin_reply': 7200,
            'count_conversation_parts': 8,
            'full_text': 'Customer: API issue. Agent: Let me check. Customer: Still not working. Agent: Escalating to max.jackson.',
            'tags': {'tags': [{'name': 'API'}]},
            '_admin_details': [{'id': 'agent2', 'name': 'John', 'email': 'john@hirehoratio.co', 'vendor': 'horatio'}]
        },
        {
            'id': 'conv_3',
            'created_at': 1699123456,
            'updated_at': 1699124456,
            'state': 'closed',
            'count_reopens': 0,
            'time_to_admin_reply': 1800,
            'count_conversation_parts': 2,
            'full_text': 'Customer: How do I export? Agent: Here is the guide.',
            'tags': {'tags': [{'name': 'Product Question'}]},
            '_admin_details': [{'id': 'agent1', 'name': 'Maria', 'email': 'maria@hirehoratio.co', 'vendor': 'horatio'}]
        }
    ]


@pytest.fixture
def admin_details_map() -> Dict:
    """Admin details map"""
    return {
        'agent1': {
            'id': 'agent1',
            'name': 'Maria Rodriguez',
            'email': 'maria@hirehoratio.co',
            'vendor': 'horatio'
        },
        'agent2': {
            'id': 'agent2',
            'name': 'John Smith',
            'email': 'john@hirehoratio.co',
            'vendor': 'horatio'
        }
    }


class TestIndividualAgentAnalyzer:
    """Test suite for IndividualAgentAnalyzer"""
    
    @pytest.mark.asyncio
    async def test_analyze_agents(self, mock_admin_cache, sample_conversations, admin_details_map):
        """Test analyzing multiple agents"""
        analyzer = IndividualAgentAnalyzer('horatio', mock_admin_cache, None)
        
        agent_metrics = await analyzer.analyze_agents(sample_conversations, admin_details_map)
        
        assert len(agent_metrics) == 2  # Maria and John
        assert all(isinstance(m, IndividualAgentMetrics) for m in agent_metrics)
        
        # Check that Maria (2 convs) and John (1 conv) are analyzed
        maria = next((a for a in agent_metrics if a.agent_name == 'Maria Rodriguez'), None)
        john = next((a for a in agent_metrics if a.agent_name == 'John Smith'), None)
        
        assert maria is not None
        assert john is not None
        
        assert maria.total_conversations == 2
        assert john.total_conversations == 1
    
    def test_group_by_agent(self, mock_admin_cache, sample_conversations, admin_details_map):
        """Test grouping conversations by agent"""
        analyzer = IndividualAgentAnalyzer('horatio', mock_admin_cache, None)
        
        grouped = analyzer._group_by_agent(sample_conversations, admin_details_map)
        
        assert 'agent1' in grouped
        assert 'agent2' in grouped
        assert len(grouped['agent1']) == 2  # Maria: conv_1 and conv_3
        assert len(grouped['agent2']) == 1  # John: conv_2
    
    def test_performance_level_assessment(self, mock_admin_cache):
        """Test performance level assessment logic"""
        analyzer = IndividualAgentAnalyzer('horatio', mock_admin_cache, None)
        
        # Excellent: High FCR, low escalation
        assert analyzer._assess_performance_level(0.90, 0.05) == "excellent"
        
        # Good: Above thresholds
        assert analyzer._assess_performance_level(0.80, 0.12) == "good"
        
        # Fair: Meets minimum thresholds
        assert analyzer._assess_performance_level(0.72, 0.18) == "fair"
        
        # Poor: Below thresholds
        assert analyzer._assess_performance_level(0.65, 0.25) == "poor"
    
    def test_coaching_priority_assessment(self, mock_admin_cache):
        """Test coaching priority assessment"""
        analyzer = IndividualAgentAnalyzer('horatio', mock_admin_cache, None)
        
        # High priority: Poor FCR
        agent_poor_fcr = Mock(
            fcr_rate=0.65,
            escalation_rate=0.15,
            weak_categories=[],
            weak_subcategories=[]
        )
        assert analyzer._assess_coaching_priority(agent_poor_fcr) == "high"
        
        # Medium priority: Multiple weak areas
        agent_weak_areas = Mock(
            fcr_rate=0.75,
            escalation_rate=0.15,
            weak_categories=['Billing', 'API'],
            weak_subcategories=['Billing>Refund', 'Bug>Export', 'Account>Login']
        )
        assert analyzer._assess_coaching_priority(agent_weak_areas) == "medium"
        
        # Low priority: Good performance
        agent_good = Mock(
            fcr_rate=0.88,
            escalation_rate=0.08,
            weak_categories=[],
            weak_subcategories=[]
        )
        assert analyzer._assess_coaching_priority(agent_good) == "low"
    
    def test_identify_achievements(self, mock_admin_cache):
        """Test achievement identification"""
        analyzer = IndividualAgentAnalyzer('horatio', mock_admin_cache, None)
        
        agent = Mock(
            fcr_rate=0.92,
            escalation_rate=0.05,
            fcr_rank=1,
            strong_categories=['Billing', 'Account', 'Bug']
        )
        
        achievements = analyzer._identify_achievements(agent)
        
        assert len(achievements) > 0
        assert any('Excellent FCR' in a for a in achievements)
        assert any('Top FCR performer' in a for a in achievements)
        assert any('Excellence across' in a for a in achievements)
    
    def test_extract_categories(self, mock_admin_cache):
        """Test category extraction from conversations"""
        analyzer = IndividualAgentAnalyzer('horatio', mock_admin_cache, None)
        
        conv = {
            'tags': {'tags': [{'name': 'Billing'}, {'name': 'Refund'}]},
            'custom_attributes': {},
            'full_text': 'Customer wants a refund for billing issue'
        }
        
        categories = analyzer._extract_categories(conv)
        
        assert len(categories) > 0
        assert any(cat['primary'] == 'Billing' for cat in categories)
    
    def test_rank_agents(self, mock_admin_cache):
        """Test agent ranking logic"""
        analyzer = IndividualAgentAnalyzer('horatio', mock_admin_cache, None)
        
        # Create sample agents with different metrics
        agent1 = IndividualAgentMetrics(
            agent_id='1',
            agent_name='Agent 1',
            agent_email='agent1@test.com',
            vendor='horatio',
            total_conversations=100,
            fcr_rate=0.90,
            reopen_rate=0.05,
            escalation_rate=0.08,
            median_resolution_hours=4.0,
            median_response_hours=0.5,
            over_48h_count=2,
            avg_conversation_complexity=3.5,
            fcr_rank=0,
            response_time_rank=0,
            coaching_priority='low'
        )
        
        agent2 = IndividualAgentMetrics(
            agent_id='2',
            agent_name='Agent 2',
            agent_email='agent2@test.com',
            vendor='horatio',
            total_conversations=80,
            fcr_rate=0.75,
            reopen_rate=0.15,
            escalation_rate=0.12,
            median_resolution_hours=6.0,
            median_response_hours=1.2,
            over_48h_count=8,
            avg_conversation_complexity=4.2,
            fcr_rank=0,
            response_time_rank=0,
            coaching_priority='medium'
        )
        
        agents = [agent2, agent1]  # Unsorted order
        ranked = analyzer._rank_agents(agents)
        
        # Agent1 should have better FCR rank
        assert agent1.fcr_rank == 1
        assert agent2.fcr_rank == 2
        
        # Agent1 should have better response time rank
        assert agent1.response_time_rank == 1
        assert agent2.response_time_rank == 2

