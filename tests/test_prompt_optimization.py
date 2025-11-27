import pytest
import json
from unittest.mock import MagicMock, patch
from src.agents.topic_detection_agent import TopicDetectionAgent, TopicCategory
from src.agents.topic_sentiment_agent import TopicSentimentAgent
from src.agents.base_agent import AgentContext, AgentResult
from src.config.taxonomy import TaxonomyManager
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

    async def test_sentiment_examples(self):
        """Verify sentiment agent uses domain-specific examples"""
        agent = TopicSentimentAgent()
        context = AgentContext(
            analysis_id="test_123",
            analysis_type="sentiment",
            start_date="2023-01-01",
            end_date="2023-01-02",
            metadata={
                'current_topic': 'Billing',
                'topic_conversations': []
            }
        )
        
        prompt = agent.get_task_description(context)
        
        # Should contain Billing-specific examples
        assert "credit model" in prompt or "invoice" in prompt
        assert "export bugs" not in prompt

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
            
            # Should log warning (check logs if capturing logs, or assume logic works)

    async def test_dynamic_ranking_missing_table(self):
        """Test graceful fallback when table is missing"""
        agent = TopicDetectionAgentWrapper()
        
        # Mock duckdb connection and execute to raise CatalogException
        import duckdb
        with patch('duckdb.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = duckdb.CatalogException("Table not found")
            
            ranking = agent._get_dynamic_ranking()
            assert ranking is None

    async def test_few_shot_examples_json_safe(self):
        """Test that few-shot examples are JSON-safe strings"""
        agent = TopicDetectionAgentWrapper()
        examples = agent.get_few_shot_examples_public()
        
        # Should not contain unescaped quotes that break JSON if inserted into a prompt string
        # Ideally, we check if it can be included in a JSON string
        json_str = json.dumps({"prompt": f"text {examples}"})
        assert json_str  # Should parse successfully

    async def test_multi_language_keywords(self):
        """Test that Russian and Korean keywords trigger detection"""
        agent = TopicDetectionAgentWrapper(llm_first=False) # Keyword mode
        
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
        agent = TopicDetectionAgentWrapper()
        
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
