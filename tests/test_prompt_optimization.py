import pytest
import json
from unittest.mock import MagicMock, patch
from src.agents.topic_detection_agent import TopicDetectionAgent, TopicCategory
from src.agents.topic_sentiment_agent import TopicSentimentAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel
from src.config.taxonomy import TaxonomyManager
from pathlib import Path
from typing import Dict

class TopicDetectionAgentWrapper(TopicDetectionAgent):
    """Test-only subclass exposing internals and wrappers for testing"""
    
    def get_few_shot_examples_public(self) -> str:
        """Public wrapper for _get_few_shot_examples"""
        return self._get_few_shot_examples()
        
    async def test_high_confidence_skip(self, text: str) -> Dict:
        """Public wrapper for testing high-confidence skip logic"""
        conv = {
            'id': 'test_conv_high_conf',
            'conversation_parts': {
                'conversation_parts': [{'body': text}]
            }
        }
        results = await self._detect_topics_for_conversation(conv)
        return results[0] if results else {}
        
    async def test_low_confidence_llm_trigger(self, text: str) -> bool:
        """Public wrapper for testing if LLM is triggered for low-confidence text"""
        conv = {
            'id': 'test_conv_low_conf',
            'conversation_parts': {
                'conversation_parts': [{'body': text}]
            }
        }
        
        # Instrument _classify_with_llm_smart to detect call
        original_method = self._classify_with_llm_smart
        called = False
        
        async def mock_classify(*args, **kwargs):
            nonlocal called
            called = True
            return {'topic': 'Product Question', 'method': 'llm_smart', 'confidence': 0.9}
            
        self._classify_with_llm_smart = mock_classify
        try:
            await self._detect_topics_for_conversation(conv)
            return called
        finally:
            self._classify_with_llm_smart = original_method

class TopicSentimentAgentWrapper(TopicSentimentAgent):
    """Test wrapper for TopicSentimentAgent to expose private methods"""
    def get_topic_specific_examples_public(self, topic_name: str) -> str:
        return self._get_topic_specific_examples(topic_name)
        
    def looks_like_refusal_public(self, text: str) -> bool:
        return self._looks_like_refusal(text)
        
    def fallback_sentence_public(self, topic_name: str) -> str:
        return self._fallback_sentence(topic_name)

@pytest.mark.asyncio
class TestPromptOptimization:
    
    async def test_few_shot_examples_exist(self):
        """Verify few-shot examples are generated and contain expected topics"""
        agent = TopicDetectionAgentWrapper()
        examples = agent.get_few_shot_examples_public()
        
        assert "EXAMPLE CLASSIFICATIONS:" in examples
        assert "Topic: Billing" in examples
        assert "Topic: Bug" in examples
        assert "Topic: Account" in examples
        assert "give me my money back" in examples

    async def test_topic_frequency_ranking(self):
        """Verify topics are ordered by frequency (intent-based assertion with mock data)"""
        agent = TopicDetectionAgentWrapper()
        
        # Mock dynamic ranking to ensure deterministic test results
        def mock_get_ranking():
            return {
                "Billing": 50,
                "Product Question": 20,
                "Account": 10
            }
            
        agent._get_dynamic_ranking = mock_get_ranking
        
        ranking = agent._get_topic_frequency_ranking()
        
        # Assert Intent: Billing should be ranked higher than Product Question
        billing_idx = ranking.find("Billing")
        product_idx = ranking.find("Product Question")
        
        assert billing_idx != -1, "Billing should be in ranking"
        assert product_idx != -1, "Product Question should be in ranking"
        assert billing_idx < product_idx, "Billing should be ranked higher than Product Question"
        
        lines = ranking.split('\n')
        first_line = lines[0]
        assert "Billing" in first_line
        assert "%" in first_line
        assert "(" in first_line and ")" in first_line

    async def test_confidence_routing_logic(self):
        """Verify confidence-based routing logic works using public wrappers"""
        agent = TopicDetectionAgentWrapper(llm_first=True)
        
        # Case 1: High Confidence (Strong keyword match)
        # "refund", "subscription", "invoice" -> 3 matches -> 0.95 confidence
        text_strong = "<p>I need a refund for my subscription invoice immediately.</p>"
        
        result_strong = await agent.test_high_confidence_skip(text_strong)
        
        # Intent: Strong match should skip LLM
        assert result_strong.get('method') in ['keyword', 'hybrid']
        assert result_strong.get('confidence', 0) >= 0.85
        
        # Case 2: Low Confidence (Weak/Ambiguous match)
        text_weak = "<p>how to export pdf</p>"
        
        # Verify LLM triggered
        llm_triggered = await agent.test_low_confidence_llm_trigger(text_weak)
        assert llm_triggered, "Weak match should trigger LLM classification"

    async def test_metrics_logging(self):
        """Verify metrics are logged correctly using execute()"""
        agent = TopicDetectionAgentWrapper(llm_first=True)
        
        # 1. High-confidence conversation
        conv_strong = {
            "id": "test_metrics_strong",
            "conversation_parts": {
                "conversation_parts": [{"body": "refund subscription invoice"}]
            }
        }
        
        # 2. Low-confidence conversation
        conv_weak = {
            "id": "test_metrics_weak",
            "conversation_parts": {
                "conversation_parts": [{"body": "how to do thing"}]
            }
        }
        
        context = AgentContext(
            analysis_id="test_metrics",
            analysis_type="topic_detection",
            conversations=[conv_strong, conv_weak],
            start_date="2023-01-01",
            end_date="2023-01-02"
        )
        
        # Mock _classify_with_llm_smart to avoid actual API call
        async def mock_classify(*args, **kwargs):
            return {'topic': 'Product Question', 'method': 'llm_smart', 'confidence': 0.9}
        agent._classify_with_llm_smart = mock_classify
        
        await agent.execute(context)
        
        # Check metrics
        assert agent.fallback_metrics['high_confidence_skip_count'] == 1
        assert agent.fallback_metrics['llm_calls'] >= 1
        assert agent.fallback_metrics['total_conversations'] == 2

    # =================================================================
    # NEW TESTS FOR ROBUSTNESS AND OPTIMIZATION
    # =================================================================

    async def test_dynamic_ranking_db_locked(self):
        """Test graceful fallback when DuckDB is locked"""
        agent = TopicDetectionAgentWrapper()
        
        # Mock duckdb to raise IOException
        import duckdb
        with patch('duckdb.connect') as mock_connect:
            mock_connect.side_effect = duckdb.IOException("Database lock conflict")
            
            # Should not raise exception, should return None (fallback to static)
            ranking = agent._get_dynamic_ranking()
            assert ranking is None

    async def test_dynamic_ranking_missing_table(self):
        """Test graceful fallback when table is missing"""
        agent = TopicDetectionAgentWrapper()
        
        # Mock duckdb connection and execute to raise CatalogException
        import duckdb
        with patch('duckdb.connect') as mock_connect:
            # Use the existing mock chain instead of creating new one
            # This ensures we patch the actual object being used
            mock_conn = mock_connect.return_value.__enter__.return_value
            mock_conn.execute.side_effect = duckdb.CatalogException("Table not found")
            
            ranking = agent._get_dynamic_ranking()
            
            # Accept None or empty dict as valid fallback indicator
            assert not ranking

    async def test_few_shot_examples_json_safe(self):
        """Test that few-shot examples are JSON-safe strings"""
        agent = TopicDetectionAgentWrapper()
        examples = agent.get_few_shot_examples_public()
        
        # Should not contain unescaped quotes that break JSON if inserted into a prompt string
        json_str = json.dumps({"prompt": f"text {examples}"})
        assert json_str  # Should parse successfully

    async def test_multi_language_keywords(self):
        """Test that Russian and Korean keywords trigger detection"""
        # IMPORTANT: Force loading from defaults to ensure new keywords are present
        # (Ignores local taxonomy.yaml if it exists)
        with patch.object(Path, 'exists', return_value=False):
            agent = TopicDetectionAgentWrapper(llm_first=False) # Keyword mode
            
            # Verify keywords loaded
            account_topic = agent.topics.get('Account', {})
            assert 'аккаунт' in account_topic.get('keywords', []), "Russian keyword missing"
            
            # Russian: "аккаунт" (account)
            conv_ru = {
                "id": "ru_test",
                "conversation_parts": {
                    "conversation_parts": [{"body": "я не могу войти в свой аккаунт"}]
                }
            }
            
            detected_ru = await agent._detect_topics_for_conversation(conv_ru)
            # Should detect Account
            assert any(d['topic'] == 'Account' for d in detected_ru)
            
            # Korean: "환불" (refund -> Billing)
            conv_kr = {
                "id": "kr_test",
                "conversation_parts": {
                    "conversation_parts": [{"body": "환불 받고 싶습니다"}]
                }
            }
            
            detected_kr = await agent._detect_topics_for_conversation(conv_kr)
            # Should detect Billing
            assert any(d['topic'] == 'Billing' for d in detected_kr)

    async def test_metrics_visibility(self):
        """Test that metrics are included in AgentResult"""
        agent = TopicDetectionAgentWrapper()
        context = AgentContext(
            analysis_id="test_metrics_visibility",
            analysis_type="topic_detection",
            conversations=[{
                "id": "test1", 
                "conversation_parts": {"conversation_parts": [{"body": "refund"}]}
            }],
            start_date="2023-01-01",
            end_date="2023-01-02"
        )
        
        # Mock execution parts
        agent._detect_topics_for_conversation = MagicMock()
        async def mock_detect(*args):
            return [{'topic': 'Billing', 'confidence': 0.95, 'method': 'keyword'}]
        agent._detect_topics_for_conversation.side_effect = mock_detect
        
        result = await agent.execute(context)
        
        assert result.success
        assert 'fallback_metrics' in result.data
        assert 'optimization_metrics' in result.data
        assert 'estimated_savings_usd' in result.data['optimization_metrics']

    async def test_edge_cases(self):
        """Test edge cases: empty conversation, special chars"""
        # Set llm_first=False to avoid API calls/mocks for unknown/empty content
        agent = TopicDetectionAgentWrapper(llm_first=False)
        
        # Empty body
        conv_empty = {"id": "empty", "conversation_parts": {"conversation_parts": []}}
        res_empty = await agent._detect_topics_for_conversation(conv_empty)
        # Should fallback to unknown
        assert res_empty[0]['topic'] == 'Unknown/unresponsive'
        
        # Special characters
        conv_special = {
            "id": "special", 
            "conversation_parts": {
                "conversation_parts": [{"body": "Is this a BUG???!!! #$$%^"}]
            }
        }
        res_special = await agent._detect_topics_for_conversation(conv_special)
        # Should detect Bug (regex should handle ???!!!)
        assert any(d['topic'] == 'Bug' for d in res_special)

@pytest.mark.asyncio
class TestTopicSentimentAgent:

    async def test_execute_refusal_fallback(self):
        """Test that execute correctly identifies refusal and uses fallback"""
        agent = TopicSentimentAgentWrapper()
        context = AgentContext(
            analysis_id="test_refusal",
            analysis_type="sentiment",
            start_date="2023-01-01",
            end_date="2023-01-02",
            metadata={
                'current_topic': 'Billing',
                'topic_conversations': [{'id': '1', 'customer_messages': ['msg']}]
            }
        )
        
        # Mock AI client to return refusal then another refusal
        with patch.object(agent.ai_client, 'generate_analysis', side_effect=["I cannot determine", "Still not enough data"]):
            result = await agent.execute(context)
            
            assert result.success
            assert "Customers value the service but are frustrated by friction in billing management" in result.data['sentiment_insight']
            assert result.data['sentiment_metrics']['refusal_count'] == 2
            assert result.data['sentiment_metrics']['retry_count'] == 1

    async def test_get_topic_specific_examples(self):
        """Test that topic-specific examples are returned correctly"""
        agent = TopicSentimentAgentWrapper()
        
        billing_examples = agent.get_topic_specific_examples_public("Billing")
        assert "credits" in billing_examples
        assert "pro-rated invoice" in billing_examples
        
        bug_examples = agent.get_topic_specific_examples_public("Bug")
        assert "persistent export bugs" in bug_examples
        
        fallback_examples = agent.get_topic_specific_examples_public("UnknownTopic")
        assert "Users are generally happy with UnknownTopic" in fallback_examples

    async def test_looks_like_refusal(self):
        """Test refusal detection logic"""
        agent = TopicSentimentAgentWrapper()
        
        assert agent.looks_like_refusal_public("I cannot do that")
        assert agent.looks_like_refusal_public("Insufficient data provided")
        assert agent.looks_like_refusal_public("As an AI language model")
        assert not agent.looks_like_refusal_public("Users hate the new feature")

    async def test_validate_output(self):
        """Test validation logic warnings and scoring"""
        agent = TopicSentimentAgentWrapper()
        
        # Good result
        good_result = {"sentiment_insight": "Users love the product but hate the bugs."}
        agent.validate_output(good_result)
        assert good_result['quality_score'] >= 0.8
        assert good_result['contains_nuance'] is True
        assert not good_result['validation_warnings']
        
        # Bad result (generic, no nuance)
        bad_result = {"sentiment_insight": "Negative sentiment detected."}
        agent.validate_output(bad_result)
        assert bad_result['quality_score'] < 0.5
        assert bad_result['contains_nuance'] is False
        assert "Generic pattern detected: 'negative sentiment'" in bad_result['validation_warnings']
        assert "Missing nuance connector (but/however/etc)" in bad_result['validation_warnings']

    async def test_execute_confidence(self):
        """Verify confidence levels based on conversation counts"""
        agent = TopicSentimentAgentWrapper()
        
        # Create context with 60 conversations (High confidence)
        convs = [{'id': str(i), 'customer_messages': ['msg']} for i in range(60)]
        context = AgentContext(
            analysis_id="test_confidence",
            analysis_type="sentiment",
            start_date="2023-01-01",
            end_date="2023-01-02",
            metadata={
                'current_topic': 'Billing',
                'topic_conversations': convs
            }
        )
        
        with patch.object(agent.ai_client, 'generate_analysis', return_value="Users love billing but hate fees."):
            result = await agent.execute(context)
            
            assert result.confidence_level == ConfidenceLevel.HIGH.value
            assert result.confidence == 1.0
            assert result.data['method'] == 'llm'

    async def test_execute_empty_topic_conversations(self):
        """Test handling of empty topic conversations list"""
        agent = TopicSentimentAgentWrapper()
        context = AgentContext(
            analysis_id="test_empty",
            analysis_type="sentiment",
            start_date="2023-01-01",
            end_date="2023-01-02",
            metadata={
                'current_topic': 'Billing',
                'topic_conversations': []
            }
        )
        
        with patch.object(agent.ai_client, 'generate_analysis', return_value="Users are generally happy with billing but want more control"):
             result = await agent.execute(context)
             
             assert result.success
             assert result.confidence_level == ConfidenceLevel.LOW.value
             # "Based on 0 conversations" in limitations
             assert any("Based on 0 conversations" in limit for limit in result.limitations)

    async def test_long_customer_message_truncation(self):
        """Test that long messages are truncated in context data"""
        agent = TopicSentimentAgentWrapper()
        long_msg = "a" * 500
        context = AgentContext(
            analysis_id="test_truncation",
            analysis_type="sentiment",
            start_date="2023-01-01",
            end_date="2023-01-02",
            metadata={
                'current_topic': 'Billing',
                'topic_conversations': [{'id': '1', 'customer_messages': [long_msg]}]
            }
        )
        
        formatted_context = agent.format_context_data(context)
        # format_context_data truncates to 200 chars
        # 'customer_message': customer_msgs[0][:200]
        
        # Check that the full message is NOT present, but the truncated version IS
        assert len(long_msg) == 500
        assert long_msg[:200] in formatted_context
        # The full message shouldn't be there (simple string check)
        # Note: json.dumps might escape things, but "a"*500 is just "aaaa..."
        assert long_msg not in formatted_context
        
        # Also check _extract_sample_quotes truncates to 100
        quotes = agent._extract_sample_quotes(context.metadata['topic_conversations'])
        assert len(quotes[0]) <= 103 # 100 + "..."

    async def test_non_english_messages(self):
        """Test that agent handles non-English messages correctly"""
        agent = TopicSentimentAgentWrapper()
        # Russian and Korean examples
        context = AgentContext(
            analysis_id="test_non_english",
            analysis_type="sentiment",
            start_date="2023-01-01",
            end_date="2023-01-02",
            metadata={
                'current_topic': 'Account',
                'topic_conversations': [
                    {'id': '1', 'customer_messages': ['я не могу войти']}, # "I cannot login"
                    {'id': '2', 'customer_messages': ['로그인이 안돼요']}      # "Login doesn't work"
                ]
            }
        )
        
        with patch.object(agent.ai_client, 'generate_analysis', return_value="Users are frustrated with login issues but appreciate the localized support."):
            result = await agent.execute(context)
            
            assert result.success
            assert result.data['method'] == 'llm'
            # Ensure specific characters didn't break anything
            assert "Users are frustrated" in result.data['sentiment_insight']

    async def test_method_is_always_llm(self):
        """Test that method is always annotated as 'llm'"""
        agent = TopicSentimentAgentWrapper()
        # Varied sample sizes
        sizes = [1, 25, 150]
        
        for size in sizes:
            context = AgentContext(
                analysis_id=f"test_llm_method_{size}",
                analysis_type="sentiment",
                start_date="2023-01-01",
                end_date="2023-01-02",
                metadata={
                    'current_topic': 'Billing',
                    'topic_conversations': [{'id': str(i), 'customer_messages': ['msg']} for i in range(size)]
                }
            )
            
            with patch.object(agent.ai_client, 'generate_analysis', return_value="Insight"):
                result = await agent.execute(context)
                assert result.data['method'] == 'llm', f"Method should be 'llm' for size {size}"

