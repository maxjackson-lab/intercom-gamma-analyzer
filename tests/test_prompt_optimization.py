import pytest
from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.topic_sentiment_agent import TopicSentimentAgent
from src.agents.base_agent import AgentContext, AgentResult
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
