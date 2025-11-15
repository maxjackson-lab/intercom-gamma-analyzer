"""
Unit tests for topic detection bug fix

Tests the critical fix for attribute-based detection that was checking
dict keys instead of values, causing 47% Unknown rate.
"""

import pytest
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.base_agent import AgentContext


class TestTopicDetectionFix:
    """Test suite for topic detection attribute bug fix"""
    
    @pytest.fixture
    def agent(self):
        """Create topic detection agent"""
        return TopicDetectionAgent()
    
    def test_attribute_in_values_billing(self, agent):
        """
        Test that 'Billing' in custom_attributes VALUES is detected correctly
        
        This was the bug: checking 'Billing' in dict keys instead of values
        """
        conv = {
            'id': 'test_billing_attr',
            'custom_attributes': {
                'Category': 'Billing',  # Billing is a VALUE, not a key!
                'Language': 'English'
            },
            'tags': {'tags': []},
            'source': {'body': 'Some text about payment'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should detect Billing via attribute
        assert len(result) > 0, "Should detect at least one topic"
        billing_detected = any(t['topic'] == 'Billing' for t in result)
        assert billing_detected, "Should detect Billing from custom_attributes value"
        
        # Should use attribute method (not keyword)
        billing_topic = next(t for t in result if t['topic'] == 'Billing')
        assert billing_topic['method'] == 'attribute', "Should detect via attribute method"
        assert billing_topic['confidence'] == 1.0, "Attribute detection should have 1.0 confidence"
    
    def test_attribute_in_values_bug(self, agent):
        """Test Bug detection from custom_attributes values"""
        conv = {
            'id': 'test_bug_attr',
            'custom_attributes': {
                'Type': 'Bug',
                'Priority': 'high'
            },
            'tags': {'tags': []},
            'source': {'body': 'Something is broken'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        bug_detected = any(t['topic'] == 'Bug' for t in result)
        assert bug_detected, "Should detect Bug from custom_attributes value"
    
    def test_attribute_in_tags(self, agent):
        """Test topic detection from tags list"""
        conv = {
            'id': 'test_tags',
            'custom_attributes': {},
            'tags': {'tags': [{'name': 'Account'}, {'name': 'urgent'}]},
            'source': {'body': 'Login problem'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        account_detected = any(t['topic'] == 'Account' for t in result)
        assert account_detected, "Should detect Account from tags"
        
        account_topic = next(t for t in result if t['topic'] == 'Account')
        assert account_topic['method'] == 'attribute', "Should detect via attribute method from tags"
    
    def test_keyword_detection_still_works(self, agent):
        """Test that keyword-based detection still works"""
        conv = {
            'id': 'test_keyword',
            'custom_attributes': {},
            'tags': {'tags': []},
            'source': {'body': 'I need help with my invoice and payment issues'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should detect Billing via keywords
        billing_detected = any(t['topic'] == 'Billing' for t in result)
        assert billing_detected, "Should detect Billing from keywords"
        
        billing_topic = next(t for t in result if t['topic'] == 'Billing')
        assert billing_topic['method'] == 'keyword', "Should detect via keyword method"
        assert 0.5 <= billing_topic['confidence'] <= 0.9, "Keyword confidence should be 0.5-0.9"
    
    def test_unknown_fallback(self, agent):
        """Test that Unknown fallback works when no topics match"""
        conv = {
            'id': 'test_unknown',
            'custom_attributes': {},
            'tags': {'tags': []},
            'source': {'body': 'xyz random gibberish abc'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should fall back to Unknown/unresponsive
        assert len(result) == 1, "Should have exactly 1 topic (fallback)"
        assert result[0]['topic'] == 'Unknown/unresponsive', "Should fallback to Unknown"
        assert result[0]['method'] == 'fallback', "Should use fallback method"
        assert result[0]['confidence'] == 0.3, "Fallback should have low confidence"
    
    def test_multiple_topics_detection(self, agent):
        """Test that multiple topics can be detected in one conversation"""
        conv = {
            'id': 'test_multi',
            'custom_attributes': {},
            'tags': {'tags': []},
            'source': {'body': 'I have a billing question about the invoice and also found a bug in the export feature'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should detect both Billing and Bug
        topics = [t['topic'] for t in result]
        assert 'Billing' in topics, "Should detect Billing"
        assert 'Bug' in topics, "Should detect Bug"
        assert len(result) >= 2, "Should detect multiple topics"
    
    def test_attribute_priority_over_keyword(self, agent):
        """Test that attribute detection takes priority over keyword detection"""
        conv = {
            'id': 'test_priority',
            'custom_attributes': {'Category': 'Billing'},
            'tags': {'tags': []},
            'source': {'body': 'I have a billing question with invoice'},  # Keywords present
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should detect Billing via attribute (not keyword)
        billing_topics = [t for t in result if t['topic'] == 'Billing']
        assert len(billing_topics) == 1, "Should detect Billing only once (attribute takes priority)"
        assert billing_topics[0]['method'] == 'attribute', "Should use attribute method, not keyword"
    
    def test_expanded_keywords_bug(self, agent):
        """Test that expanded Bug keywords work"""
        conv = {
            'id': 'test_expanded_bug',
            'custom_attributes': {},
            'tags': {'tags': []},
            'source': {'body': "This doesn't work correctly and failed when I tried it"},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should detect Bug via expanded keywords ("doesn't work", "failed")
        bug_detected = any(t['topic'] == 'Bug' for t in result)
        assert bug_detected, "Should detect Bug from expanded keywords"
    
    def test_expanded_keywords_product(self, agent):
        """Test that expanded Product Question keywords work"""
        conv = {
            'id': 'test_expanded_product',
            'custom_attributes': {},
            'tags': {'tags': []},
            'source': {'body': 'I need help understanding how this feature works'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should detect Product Question via expanded keywords
        product_detected = any(t['topic'] == 'Product Question' for t in result)
        assert product_detected, "Should detect Product Question from expanded keywords"
    
    def test_empty_text_fallback(self, agent):
        """Test that conversations with empty text fall back to Unknown"""
        conv = {
            'id': 'test_empty',
            'custom_attributes': {},
            'tags': {'tags': []},
            'source': {},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        assert len(result) == 1, "Should have exactly 1 topic (fallback)"
        assert result[0]['topic'] == 'Unknown/unresponsive', "Should fallback to Unknown for empty text"
        assert result[0]['method'] == 'fallback', "Should indicate fallback method"


class TestTopicDistributionNormalization:
    """Test suite for mathematical normalization of topic distributions"""
    
    @pytest.fixture
    def agent(self):
        """Create topic detection agent"""
        return TopicDetectionAgent()
    
    def test_normal_distribution_normalization(self, agent):
        """
        Test normal case: percentages that don't sum to 100 are normalized proportionally.
        
        Example: If we have 30% and 20% (total 50%), they should become 60% and 40%.
        """
        input_dist = {'Billing': 30.0, 'Bug': 20.0}
        result = agent._normalize_topic_distribution(input_dist)
        
        # Should scale proportionally to 100%
        assert abs(result['Billing'] - 60.0) < 0.1, "Billing should be scaled to 60%"
        assert abs(result['Bug'] - 40.0) < 0.1, "Bug should be scaled to 40%"
        
        # Total must be exactly 100%
        total = sum(result.values())
        assert abs(total - 100.0) < 0.1, f"Total should be 100%, got {total}%"
    
    def test_single_topic_normalization(self, agent):
        """Test single-topic case: should always be 100%"""
        input_dist = {'Billing': 42.0}
        result = agent._normalize_topic_distribution(input_dist)
        
        assert result['Billing'] == 100.0, "Single topic should be normalized to 100%"
    
    def test_zero_total_normalization(self, agent):
        """Test zero-total case: all zeros should remain zeros"""
        input_dist = {'Billing': 0.0, 'Bug': 0.0, 'Account': 0.0}
        result = agent._normalize_topic_distribution(input_dist)
        
        # All should remain 0 (cannot normalize a zero distribution)
        assert all(v == 0.0 for v in result.values()), "Zero-total should return all zeros"
    
    def test_empty_distribution_normalization(self, agent):
        """Test empty input: should return empty dict"""
        input_dist = {}
        result = agent._normalize_topic_distribution(input_dist)
        
        assert result == {}, "Empty input should return empty dict"
    
    def test_rounding_behavior(self, agent):
        """Test that rounding is deterministic and sums to exactly 100"""
        # Use values that will cause rounding issues (e.g., 33.333... each)
        input_dist = {'A': 10, 'B': 10, 'C': 10}
        result = agent._normalize_topic_distribution(input_dist)
        
        # All should be ~33.3%
        for topic in ['A', 'B', 'C']:
            assert abs(result[topic] - 33.3) < 0.5, f"{topic} should be ~33.3%"
        
        # Total must be EXACTLY 100.0 (with rounding correction applied)
        total = sum(result.values())
        assert abs(total - 100.0) < 0.1, f"Total must be exactly 100%, got {total}%"
    
    def test_large_distribution_normalization(self, agent):
        """Test with many topics to ensure scaling works correctly"""
        input_dist = {
            'Billing': 15, 'Bug': 12, 'Account': 10,
            'Feedback': 8, 'Product Question': 7,
            'Unknown': 3
        }
        result = agent._normalize_topic_distribution(input_dist)
        
        # Total input: 55, so everything should scale by 100/55 ≈ 1.818
        total = sum(result.values())
        assert abs(total - 100.0) < 0.1, f"Total should be 100%, got {total}%"
        
        # Check that proportions are maintained (largest stays largest)
        assert result['Billing'] > result['Bug'], "Billing should remain largest"
        assert result['Bug'] > result['Account'], "Bug should remain second"
    
    def test_already_normalized_distribution(self, agent):
        """Test that already-normalized distribution (100%) passes through correctly"""
        input_dist = {'Billing': 60.0, 'Bug': 40.0}
        result = agent._normalize_topic_distribution(input_dist)
        
        # Should remain the same (already sums to 100)
        assert abs(result['Billing'] - 60.0) < 0.1
        assert abs(result['Bug'] - 40.0) < 0.1
        
        total = sum(result.values())
        assert abs(total - 100.0) < 0.1
    
    def test_normalization_idempotent(self, agent):
        """Test that normalizing twice gives same result (idempotent)"""
        input_dist = {'Billing': 30.0, 'Bug': 20.0}
        
        result1 = agent._normalize_topic_distribution(input_dist)
        result2 = agent._normalize_topic_distribution(result1)
        
        # Should be identical (normalizing a normalized distribution)
        for topic in result1:
            assert abs(result1[topic] - result2[topic]) < 0.01, \
                f"Normalization should be idempotent for {topic}"


class TestAttributeDetectionEdgeCases:
    """Test edge cases for attribute detection"""
    
    @pytest.fixture
    def agent(self):
        return TopicDetectionAgent()
    
    def test_none_attributes(self, agent):
        """Test handling of None custom_attributes"""
        conv = {
            'id': 'test_none_attrs',
            'custom_attributes': None,  # Can SDK return None?
            'tags': {'tags': []},
            'source': {'body': 'billing issue'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should still detect via keywords
        billing_detected = any(t['topic'] == 'Billing' for t in result)
        assert billing_detected, "Should detect Billing via keywords when attributes is None"
    
    def test_list_attributes(self, agent):
        """Test handling of non-dict custom_attributes"""
        conv = {
            'id': 'test_list_attrs',
            'custom_attributes': ['Billing', 'urgent'],  # What if it's a list?
            'tags': {'tags': []},
            'source': {'body': 'payment problem'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should not crash, should fall back to keywords
        assert len(result) > 0, "Should handle list attributes gracefully"
    
    def test_nested_tags(self, agent):
        """Test proper tags extraction from nested structure"""
        conv = {
            'id': 'test_nested_tags',
            'custom_attributes': {},
            'tags': {
                'tags': [
                    {'name': 'Bug', 'id': 'tag_123'},
                    {'name': 'urgent', 'id': 'tag_456'}
                ]
            },
            'source': {'body': 'something wrong'},
            'conversation_parts': {'conversation_parts': []}
        }
        
        result = agent._detect_topics_for_conversation(conv)
        
        # Should extract 'Bug' from nested tag structure
        bug_detected = any(t['topic'] == 'Bug' for t in result)
        assert bug_detected, "Should detect Bug from nested tags structure"


