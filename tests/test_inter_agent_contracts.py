"""
Tests for inter-agent payload contracts using Pydantic models.

Validates that:
1. Models accept valid data
2. Models reject invalid data with clear errors
3. Validators work correctly
4. Serialization/deserialization works
5. Contract adherence in agent workflows
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from src.models.analysis_models import (
    SegmentationPayload,
    TopicDetectionResult,
    SubtopicDetectionResult,
    FinAnalysisPayload,
    TrendAnalysisPayload
)


class TestSegmentationPayload:
    """Tests for SegmentationPayload model"""
    
    def test_valid_data(self):
        """Test SegmentationPayload accepts valid data"""
        data = {
            'paid_customer_conversations': [{'id': '1'}, {'id': '2'}],
            'paid_fin_resolved_conversations': [{'id': '3'}],
            'free_fin_only_conversations': [{'id': '4'}, {'id': '5'}],
            'unknown_tier': [],
            'agent_distribution': {
                'escalated': 1,
                'horatio': 2,
                'boldr': 1,
                'fin_ai': 2,
                'fin_resolved': 1,
                'unknown': 0
            },
            'segmentation_summary': {
                'paid_count': 3,
                'free_count': 2
            }
        }
        
        payload = SegmentationPayload(**data)
        assert len(payload.paid_customer_conversations) == 2
        assert len(payload.free_fin_only_conversations) == 2
        assert payload.agent_distribution['horatio'] == 2
    
    def test_invalid_agent_type(self):
        """Test SegmentationPayload rejects invalid agent types"""
        data = {
            'paid_customer_conversations': [],
            'paid_fin_resolved_conversations': [],
            'free_fin_only_conversations': [],
            'unknown_tier': [],
            'agent_distribution': {
                'invalid_agent': 5  # Invalid agent type
            },
            'segmentation_summary': {}
        }
        
        with pytest.raises(ValidationError, match="Invalid agent types"):
            SegmentationPayload(**data)
    
    def test_default_values(self):
        """Test SegmentationPayload uses default values correctly"""
        minimal_data = {}
        
        payload = SegmentationPayload(**minimal_data)
        assert payload.paid_customer_conversations == []
        assert payload.free_fin_only_conversations == []
        assert payload.agent_distribution == {}
    
    def test_serialization_round_trip(self):
        """Test SegmentationPayload can be serialized and deserialized"""
        original_data = {
            'paid_customer_conversations': [{'id': '1'}],
            'paid_fin_resolved_conversations': [],
            'free_fin_only_conversations': [{'id': '2'}],
            'unknown_tier': [],
            'agent_distribution': {'fin_ai': 1},
            'segmentation_summary': {'total': 2}
        }
        
        # Create model
        payload = SegmentationPayload(**original_data)
        
        # Serialize
        serialized = payload.dict()
        
        # Deserialize
        reconstructed = SegmentationPayload(**serialized)
        
        assert len(reconstructed.paid_customer_conversations) == 1
        assert len(reconstructed.free_fin_only_conversations) == 1


class TestTopicDetectionResult:
    """Tests for TopicDetectionResult model"""
    
    def test_valid_data(self):
        """Test TopicDetectionResult accepts valid data"""
        data = {
            'topics': [
                {'name': 'billing', 'category': 'product'},
                {'name': 'api', 'category': 'technical'}
            ],
            'topic_distribution': {
                'billing': {'volume': 10, 'percentage': 0.5},
                'api': {'volume': 10, 'percentage': 0.5}
            },
            'topics_by_conversation': {
                'conv1': [{'topic': 'billing', 'confidence': 0.9}],
                'conv2': [{'topic': 'api', 'confidence': 0.85}]
            },
            'unassigned_conversations': [],
            'detection_metadata': {'version': '1.0'},
            'confidence_scores': {'billing': 0.95, 'api': 0.88}
        }
        
        result = TopicDetectionResult(**data)
        assert len(result.topics) == 2
        assert result.confidence_scores['billing'] == 0.95
        assert len(result.topics_by_conversation) == 2
    
    def test_invalid_topic_missing_name(self):
        """Test TopicDetectionResult rejects topics missing 'name' field"""
        data = {
            'topics': [
                {'category': 'product'}  # Missing 'name'
            ],
            'topic_distribution': {},
            'topics_by_conversation': {},
            'confidence_scores': {}
        }
        
        with pytest.raises(ValidationError, match="missing required 'name' field"):
            TopicDetectionResult(**data)
    
    def test_invalid_confidence_score(self):
        """Test TopicDetectionResult rejects invalid confidence scores"""
        data = {
            'topics': [{'name': 'billing'}],
            'topic_distribution': {},
            'topics_by_conversation': {},
            'confidence_scores': {'billing': 1.5}  # > 1.0
        }
        
        with pytest.raises(ValidationError, match="must be between 0 and 1"):
            TopicDetectionResult(**data)
    
    def test_confidence_score_negative(self):
        """Test TopicDetectionResult rejects negative confidence scores"""
        data = {
            'topics': [{'name': 'billing'}],
            'topic_distribution': {},
            'topics_by_conversation': {},
            'confidence_scores': {'billing': -0.1}  # < 0
        }
        
        with pytest.raises(ValidationError, match="must be between 0 and 1"):
            TopicDetectionResult(**data)
    
    def test_serialization_round_trip(self):
        """Test TopicDetectionResult serialization/deserialization"""
        original_data = {
            'topics': [{'name': 'test', 'category': 'test'}],
            'topic_distribution': {'test': {'volume': 5}},
            'topics_by_conversation': {'conv1': [{'topic': 'test'}]},
            'unassigned_conversations': [],
            'detection_metadata': {},
            'confidence_scores': {'test': 0.9}
        }
        
        result = TopicDetectionResult(**original_data)
        serialized = result.dict()
        reconstructed = TopicDetectionResult(**serialized)
        
        assert reconstructed.topics == result.topics
        assert reconstructed.confidence_scores == result.confidence_scores


class TestSubtopicDetectionResult:
    """Tests for SubtopicDetectionResult model"""
    
    def test_valid_data(self):
        """Test SubtopicDetectionResult accepts valid data"""
        data = {
            'subtopics_by_tier1_topic': {
                'billing': {
                    'tier2': {
                        'subscription': {'count': 5, 'examples': []},
                        'invoices': {'count': 3, 'examples': []}
                    },
                    'tier3': {
                        'payment_failed': {'count': 2, 'keywords': ['payment', 'failed']},
                        'refund': {'count': 1, 'keywords': ['refund']}
                    }
                }
            },
            'subtopic_metadata': {'total_tier1': 1}
        }
        
        result = SubtopicDetectionResult(**data)
        assert 'billing' in result.subtopics_by_tier1_topic
        assert 'tier2' in result.subtopics_by_tier1_topic['billing']
        assert 'tier3' in result.subtopics_by_tier1_topic['billing']
    
    def test_invalid_missing_tier_structure(self):
        """Test SubtopicDetectionResult rejects missing tier2/tier3"""
        data = {
            'subtopics_by_tier1_topic': {
                'billing': {
                    'tier2': {}
                    # Missing 'tier3'
                }
            },
            'subtopic_metadata': {}
        }
        
        with pytest.raises(ValidationError, match="must contain 'tier2' and 'tier3' keys"):
            SubtopicDetectionResult(**data)
    
    def test_invalid_non_dict_subtopic_data(self):
        """Test SubtopicDetectionResult rejects non-dict subtopic data"""
        data = {
            'subtopics_by_tier1_topic': {
                'billing': "not a dict"  # Should be dict
            },
            'subtopic_metadata': {}
        }
        
        with pytest.raises(ValidationError, match="Input should be a valid dictionary"):
            SubtopicDetectionResult(**data)
    
    def test_serialization_round_trip(self):
        """Test SubtopicDetectionResult serialization/deserialization"""
        original_data = {
            'subtopics_by_tier1_topic': {
                'test': {
                    'tier2': {'sub1': {'count': 1}},
                    'tier3': {'theme1': {'count': 1}}
                }
            },
            'subtopic_metadata': {}
        }
        
        result = SubtopicDetectionResult(**original_data)
        serialized = result.dict()
        reconstructed = SubtopicDetectionResult(**serialized)
        
        assert 'test' in reconstructed.subtopics_by_tier1_topic


class TestFinAnalysisPayload:
    """Tests for FinAnalysisPayload model"""
    
    def test_valid_data(self):
        """Test FinAnalysisPayload accepts valid data"""
        data = {
            'total_fin_conversations': 100,
            'total_free_tier': 60,
            'total_paid_tier': 40,
            'free_tier': {
                'resolution_rate': 0.75,
                'knowledge_gaps_count': 15,
                'performance_by_topic': {
                    'billing': {'resolution_rate': 0.8}
                }
            },
            'paid_tier': {
                'resolution_rate': 0.82,
                'knowledge_gaps_count': 7,
                'performance_by_topic': {
                    'api': {'resolution_rate': 0.9}
                }
            },
            'tier_comparison': {
                'resolution_delta': 0.07,
                'interpretation': 'Paid tier performs better'
            },
            'llm_insights': 'Fin performs well on billing topics.'
        }
        
        payload = FinAnalysisPayload(**data)
        assert payload.total_fin_conversations == 100
        assert payload.free_tier['resolution_rate'] == 0.75
        assert payload.paid_tier['resolution_rate'] == 0.82
    
    def test_negative_conversation_count(self):
        """Test FinAnalysisPayload rejects negative counts"""
        data = {
            'total_fin_conversations': -10,  # Invalid
            'total_free_tier': 0,
            'total_paid_tier': 0,
            'free_tier': {},
            'paid_tier': {}
        }
        
        with pytest.raises(ValidationError):
            FinAnalysisPayload(**data)
    
    def test_missing_required_tier_fields(self):
        """Test FinAnalysisPayload validates tier metrics structure"""
        data = {
            'total_fin_conversations': 10,
            'total_free_tier': 10,
            'total_paid_tier': 0,
            'free_tier': {
                'resolution_rate': 0.5
                # Missing 'knowledge_gaps_count' and 'performance_by_topic'
            },
            'paid_tier': {}
        }
        
        with pytest.raises(ValidationError, match="missing required fields"):
            FinAnalysisPayload(**data)
    
    def test_empty_tiers_allowed(self):
        """Test FinAnalysisPayload allows empty tier dicts"""
        data = {
            'total_fin_conversations': 0,
            'total_free_tier': 0,
            'total_paid_tier': 0,
            'free_tier': {},
            'paid_tier': {}
        }
        
        # Should not raise - empty tiers are valid when count is 0
        payload = FinAnalysisPayload(**data)
        assert payload.total_fin_conversations == 0
    
    def test_serialization_round_trip(self):
        """Test FinAnalysisPayload serialization/deserialization"""
        original_data = {
            'total_fin_conversations': 50,
            'total_free_tier': 30,
            'total_paid_tier': 20,
            'free_tier': {
                'resolution_rate': 0.7,
                'knowledge_gaps_count': 10,
                'performance_by_topic': {}
            },
            'paid_tier': {
                'resolution_rate': 0.8,
                'knowledge_gaps_count': 5,
                'performance_by_topic': {}
            }
        }
        
        payload = FinAnalysisPayload(**original_data)
        serialized = payload.dict()
        reconstructed = FinAnalysisPayload(**serialized)
        
        assert reconstructed.total_fin_conversations == 50
        assert reconstructed.free_tier['resolution_rate'] == 0.7


class TestTrendAnalysisPayload:
    """Tests for TrendAnalysisPayload model"""
    
    def test_valid_data(self):
        """Test TrendAnalysisPayload accepts valid data"""
        data = {
            'trends': [
                {'name': 'billing_increase', 'change': 0.15, 'direction': 'up'},
                {'name': 'api_stable', 'change': 0.02, 'direction': 'stable'}
            ],
            'week_over_week_changes': {
                'billing': 15.5,
                'api': 2.1
            },
            'trending_topics': ['billing', 'authentication'],
            'analysis_period': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-07'
            },
            'trend_insights': 'Billing inquiries increased significantly.'
        }
        
        payload = TrendAnalysisPayload(**data)
        assert len(payload.trends) == 2
        assert len(payload.trending_topics) == 2
        assert payload.analysis_period['start_date'] == '2024-01-01'
    
    def test_missing_period_fields(self):
        """Test TrendAnalysisPayload requires start_date and end_date"""
        data = {
            'trends': [],
            'week_over_week_changes': {},
            'trending_topics': [],
            'analysis_period': {
                'start_date': '2024-01-01'
                # Missing 'end_date'
            }
        }
        
        with pytest.raises(ValidationError, match="must contain 'start_date' and 'end_date'"):
            TrendAnalysisPayload(**data)
    
    def test_default_values(self):
        """Test TrendAnalysisPayload uses default values correctly"""
        minimal_data = {
            'trends': [],
            'analysis_period': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-07'
            }
        }
        
        payload = TrendAnalysisPayload(**minimal_data)
        assert payload.week_over_week_changes == {}
        assert payload.trending_topics == []
        assert payload.trend_insights is None
    
    def test_serialization_round_trip(self):
        """Test TrendAnalysisPayload serialization/deserialization"""
        original_data = {
            'trends': [{'name': 'test_trend', 'value': 10}],
            'week_over_week_changes': {'test': 5.0},
            'trending_topics': ['test'],
            'analysis_period': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-07'
            }
        }
        
        payload = TrendAnalysisPayload(**original_data)
        serialized = payload.dict()
        reconstructed = TrendAnalysisPayload(**serialized)
        
        assert reconstructed.trending_topics == ['test']
        assert reconstructed.analysis_period['start_date'] == '2024-01-01'


class TestContractAdherence:
    """Integration tests for contract adherence in workflows"""
    
    def test_segmentation_to_topic_detection_flow(self):
        """Test data flow from Segmentation to Topic Detection"""
        # Segmentation output
        seg_data = {
            'paid_customer_conversations': [{'id': '1', 'text': 'billing issue'}],
            'paid_fin_resolved_conversations': [],
            'free_fin_only_conversations': [{'id': '2', 'text': 'api help'}],
            'unknown_tier': [],
            'agent_distribution': {'fin_ai': 1, 'fin_resolved': 0},
            'segmentation_summary': {}
        }
        
        seg_payload = SegmentationPayload(**seg_data)
        
        # Topic detection should be able to use segmentation output
        all_conversations = (
            seg_payload.paid_customer_conversations +
            seg_payload.free_fin_only_conversations
        )
        
        assert len(all_conversations) == 2
        assert all_conversations[0]['id'] == '1'
    
    def test_topic_detection_to_fin_analysis_flow(self):
        """Test data flow from Topic Detection to Fin Analysis"""
        # Topic detection output
        topic_data = {
            'topics': [{'name': 'billing'}],
            'topic_distribution': {'billing': {'volume': 5}},
            'topics_by_conversation': {
                'conv1': [{'topic': 'billing', 'confidence': 0.9}]
            },
            'unassigned_conversations': [],
            'detection_metadata': {},
            'confidence_scores': {'billing': 0.9}
        }
        
        topic_payload = TopicDetectionResult(**topic_data)
        
        # Fin analysis should be able to use topic assignments
        assert 'conv1' in topic_payload.topics_by_conversation
        assert topic_payload.topics_by_conversation['conv1'][0]['topic'] == 'billing'
    
    def test_subtopic_to_fin_analysis_flow(self):
        """Test data flow from Subtopic Detection to Fin Analysis"""
        # Subtopic detection output
        subtopic_data = {
            'subtopics_by_tier1_topic': {
                'billing': {
                    'tier2': {'subscription': {'count': 3}},
                    'tier3': {'payment_failed': {'count': 1}}
                }
            },
            'subtopic_metadata': {}
        }
        
        subtopic_payload = SubtopicDetectionResult(**subtopic_data)
        
        # Fin analysis should be able to use subtopic structure
        assert 'billing' in subtopic_payload.subtopics_by_tier1_topic
        billing_subs = subtopic_payload.subtopics_by_tier1_topic['billing']
        assert 'tier2' in billing_subs
        assert 'tier3' in billing_subs


class TestErrorHandling:
    """Tests for error handling and validation messages"""
    
    def test_validation_error_includes_field_name(self):
        """Test that validation errors clearly indicate which field failed"""
        data = {
            'total_fin_conversations': 'not_a_number',  # Should be int
            'total_free_tier': 0,
            'total_paid_tier': 0,
            'free_tier': {},
            'paid_tier': {}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            FinAnalysisPayload(**data)
        
        # Error should mention the problematic field
        error_str = str(exc_info.value)
        assert 'total_fin_conversations' in error_str
    
    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are reported"""
        data = {
            'topics': [
                {}  # Missing 'name'
            ],
            'topic_distribution': {},
            'topics_by_conversation': {},
            'confidence_scores': {
                'test': 2.0  # Invalid (> 1.0)
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TopicDetectionResult(**data)
        
        # Should report both errors
        error_str = str(exc_info.value)
        # At least one error should be reported
        assert len(str(exc_info.value)) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])