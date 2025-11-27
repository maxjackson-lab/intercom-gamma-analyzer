import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from src.agents.topic_detection_agent import TopicDetectionAgent, TopicCategory
from src.agents.topic_sentiment_agent import TopicSentimentAgent
from src.agents.base_agent import AgentContext, AgentResult, ConfidenceLevel
from src.config.taxonomy import TaxonomyManager
from pathlib import Path
from typing import Dict, Any, Optional
from src.services.presentation_builder import PresentationBuilder
from src.agents.output_formatter_agent import OutputFormatterAgent
from src.agents.insight_agent import InsightAgent
from src.agents.sentiment_agent import SentimentAgent


def build_topic_context(
    topic_distribution: Dict[str, Dict[str, float]],
    sentiment_overrides: Dict[str, Dict[str, Any]] = None
) -> AgentContext:
    """Create a reusable AgentContext for topic-based workflow tests."""
    topic_names = list(topic_distribution.keys())
    sentiments = sentiment_overrides or {
        name: {
            'success': True,
            'data': {
                'sentiment': 'neutral',
                'sentiment_insight': f"{name} sentiment insight"
            }
        }
        for name in topic_names
    }
    topic_examples = {
        name: {
            'data': {
                'examples': [{
                    'conversation_id': f"{name}-1",
                    'preview': f"Example from {name}",
                    'intercom_url': f"https://example.com/{name}"
                }]
            }
        }
        for name in topic_names
    }
    previous_results = {
        'TopicDetectionAgent': {
            'data': {
                'topic_distribution': topic_distribution,
                'topics_by_conversation': {},
                'fallback_metrics': {}
            }
        },
        'TopicSentiments': sentiments,
        'TopicExamples': topic_examples,
        'SegmentationAgent': {
            'data': {
                'segmentation_summary': {
                    'paid_count': 100,
                    'paid_percentage': 70.0,
                    'free_count': 30,
                    'free_percentage': 30.0,
                    'language_distribution': {'English': 120},
                    'total_languages': 1
                }
            }
        },
        'SubTopicDetectionAgent': {'data': {'subtopics_by_tier1_topic': {}}},
        'TrendAgent': {'data': {}},
        'FinPerformanceAgent': {'data': {}},
        'AnalyticalInsights': {}
    }
    metadata = {
        'period_label': 'Weekly',
        'period_type': 'week',
        'week_id': '2024-W01',
        'digest_mode': False
    }
    return AgentContext(
        analysis_id="test-analysis",
        analysis_type="topic_based",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 7),
        conversations=[],
        previous_results=previous_results,
        metadata=metadata
    )

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


class SentimentAgentWrapper(SentimentAgent):
    """Test wrapper exposing private helpers on SentimentAgent."""
    def get_global_examples_public(self) -> str:
        return self._get_global_sentiment_examples()
    
    def looks_like_refusal_public(self, text: str) -> bool:
        return self._looks_like_refusal(text)
    
    def fallback_sentence_public(self, context: Optional[AgentContext] = None) -> str:
        return self._fallback_sentence(context)

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
            return [{'topic': 'Product Question', 'method': 'llm_smart', 'confidence': 0.9}]
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

    async def test_detection_method_in_topic_distribution(self):
        """Ensure topic distribution includes detection metadata"""
        agent = TopicDetectionAgentWrapper()
        conversations = [
            {
                "id": "billing_conv",
                "conversation_parts": {
                    "conversation_parts": [{"body": "I need a refund for my invoice subscription"}]
                }
            },
            {
                "id": "bug_conv",
                "conversation_parts": {
                    "conversation_parts": [{"body": "There is a bug in export"}]
                }
            }
        ]
        context = AgentContext(
            analysis_id="test_detection_method_distribution",
            analysis_type="topic_detection",
            conversations=conversations,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )
        result = await agent.execute(context)
        topic_dist = result.data.get('topic_distribution', {})
        assert topic_dist, "Topic distribution should not be empty"
        billing_stats = topic_dist.get('Billing')
        assert billing_stats is not None
        assert billing_stats['detection_method'] in {'keyword', 'hybrid', 'llm_smart', 'llm_only'}
        assert 'llm_smart_count' in billing_stats
        assert 'keyword_count' in billing_stats

    async def test_fallback_metrics_include_method_counts(self):
        """Verify fallback metrics include key counters"""
        agent = TopicDetectionAgentWrapper()
        conversations = [
            {
                "id": "strong_keywords",
                "conversation_parts": {
                    "conversation_parts": [{"body": "Need refund for invoice charge"}]
                }
            },
            {
                "id": "llm_needed",
                "conversation_parts": {
                    "conversation_parts": [{"body": "Hi there, something weird happens"}]
                }
            }
        ]
        context = AgentContext(
            analysis_id="test_fallback_metrics",
            analysis_type="topic_detection",
            conversations=conversations,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )

        async def mock_llm_classify(*args, **kwargs):
            return [{
                'topic': 'Product Question',
                'method': 'llm_smart',
                'confidence': 0.9
            }]

        original_llm = agent._classify_with_llm_smart
        agent._classify_with_llm_smart = mock_llm_classify
        try:
            result = await agent.execute(context)
        finally:
            agent._classify_with_llm_smart = original_llm

        fallback_metrics = result.data.get('fallback_metrics', {})
        assert 'high_confidence_skip_count' in fallback_metrics
        assert 'llm_calls' in fallback_metrics
        assert 'llm_success_count' in fallback_metrics


class TestOutputFormatterDetectionMethodLabeling:

    def test_detection_method_label_mapping(self):
        agent = OutputFormatterAgent(use_llm_formatting=False)
        assert "Verified by AI Analysis" in agent._get_detection_method_label('llm_smart')
        assert "Verified by AI Analysis" in agent._get_detection_method_label('llm_only')
        assert "Hybrid Detection" in agent._get_detection_method_label('hybrid')
        assert "keyword patterns" in agent._get_detection_method_label('keyword')
        assert "Intercom attributes" in agent._get_detection_method_label('sdk_only')
        assert "Fallback classification" in agent._get_detection_method_label('fallback')
        assert "Intercom attributes" in agent._get_detection_method_label('attribute')
        assert "not specified" in agent._get_detection_method_label('unknown_method')

    def test_topic_card_includes_detection_method(self):
        agent = OutputFormatterAgent(use_llm_formatting=False)
        stats = {
            'volume': 120,
            'percentage': 24.0,
            'detection_method': 'llm_smart',
            'confidence': 0.92,
            'llm_smart_count': 80,
            'llm_only_count': 10,
            'keyword_count': 30,
            'hybrid_count': 0,
            'sdk_only_count': 0,
            'fallback_count': 0
        }
        card = agent._format_topic_card(
            "Billing",
            stats,
            "Customers are frustrated with invoicing",
            [],
            "",
            "",
            "Weekly"
        )
        assert "Verified by AI Analysis" in card
        assert "Confidence: 0.92" in card

    def test_detection_method_breakdown_display(self):
        agent = OutputFormatterAgent(use_llm_formatting=False)
        stats = {
            'volume': 100,
            'percentage': 50.0,
            'detection_method': 'hybrid',
            'confidence': 0.8,
            'llm_smart_count': 20,
            'llm_only_count': 5,
            'hybrid_count': 45,
            'keyword_count': 20,
            'sdk_only_count': 5,
            'fallback_count': 5
        }
        card = agent._format_topic_card(
            "Automation",
            stats,
            "Automation tickets hold steady",
            [],
            "",
            "",
            "Weekly"
        )
        assert "**Detection Mix**" in card
        assert "AI-verified" in card
        assert "Hybrid" in card
        assert "Keyword" in card

    def test_detection_method_validation(self, caplog):
        agent = OutputFormatterAgent(use_llm_formatting=False)
        valid = {
            'formatted_output': 'ok',
            'structured_data': {
                'topics': {
                    'Billing': {'detection_method': 'llm_smart'}
                }
            }
        }
        assert agent.validate_output(valid)
        invalid = {
            'formatted_output': 'ok',
            'structured_data': {
                'topics': {
                    'Billing': {}
                }
            }
        }
        with caplog.at_level('WARNING'):
            agent.validate_output(invalid)
        assert "missing detection_method" in caplog.text


class TestInsightAgentTopicBasedWorkflow:

    @staticmethod
    def _sample_distribution():
        return {
            'Billing': {
                'volume': 50,
                'percentage': 50.0,
                'detection_method': 'llm_smart',
                'confidence': 0.9,
                'llm_smart_count': 40,
                'llm_only_count': 10,
                'hybrid_count': 0,
                'keyword_count': 0,
                'sdk_only_count': 0,
                'fallback_count': 0
            },
            'Automation': {
                'volume': 30,
                'percentage': 30.0,
                'detection_method': 'hybrid',
                'confidence': 0.8,
                'llm_smart_count': 5,
                'llm_only_count': 0,
                'hybrid_count': 20,
                'keyword_count': 5,
                'sdk_only_count': 0,
                'fallback_count': 0
            },
            'Macros': {
                'volume': 20,
                'percentage': 20.0,
                'detection_method': 'keyword',
                'confidence': 0.6,
                'llm_smart_count': 0,
                'llm_only_count': 0,
                'hybrid_count': 0,
                'keyword_count': 15,
                'sdk_only_count': 0,
                'fallback_count': 5
            }
        }

    def test_validate_input_topic_based_workflow(self):
        agent = InsightAgent()
        context = build_topic_context(json.loads(json.dumps(self._sample_distribution())))
        assert agent.validate_input(context)
        assert agent.workflow_type == 'topic_based'

    def test_validate_input_standard_workflow(self):
        agent = InsightAgent()
        context = AgentContext(
            analysis_id="standard",
            analysis_type="standard",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            conversations=[],
            previous_results={
                'CategoryAgent': {'data': {'category_distribution': {}}},
                'SentimentAgent': {'data': {'sentiment_distribution': {}}}
            }
        )
        assert agent.validate_input(context)
        assert agent.workflow_type == 'standard'

    def test_validate_input_missing_agents(self):
        agent = InsightAgent()
        context = AgentContext(
            analysis_id="missing",
            analysis_type="topic_based",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            conversations=[],
            previous_results={
                'TopicDetectionAgent': {
                    'data': {
                        'topic_distribution': self._sample_distribution()
                    }
                }
            }
        )
        with pytest.raises(ValueError):
            agent.validate_input(context)

    def test_format_topic_based_context_data(self):
        agent = InsightAgent()
        context = build_topic_context(json.loads(json.dumps(self._sample_distribution())))
        agent.validate_input(context)
        formatted = agent._format_topic_based_context_data(context)
        assert "TOPIC DETECTION RESULTS" in formatted
        assert "Billing" in formatted
        assert "Detection Method" in formatted
        assert "Detection Mix" in formatted
        assert "Tag insights with detection provenance" in formatted

    def test_extract_detection_method_confidence(self):
        agent = InsightAgent()
        avg_conf, distribution = agent._extract_detection_method_confidence(self._sample_distribution())
        assert pytest.approx(avg_conf, 0.001) == 0.81
        assert pytest.approx(distribution.get('llm_smart', 0), 0.1) == 45.0
        assert pytest.approx(distribution.get('hybrid', 0), 0.1) == 20.0
        assert pytest.approx(distribution.get('keyword', 0), 0.1) == 20.0
        assert pytest.approx(distribution.get('fallback', 0), 0.1) == 5.0

    @pytest.mark.asyncio
    async def test_confidence_propagation_topic_based(self):
        agent = InsightAgent()
        context = build_topic_context(json.loads(json.dumps(self._sample_distribution())))
        response_text = (
            "1. Billing escalations rising (Verified by AI Analysis)\n"
            "2. Automation workflows stable (Hybrid detection: AI + Keywords)\n"
            "3. Macros complaints growing (Trend detected via keyword patterns)\n"
            "Recommendations:\n"
            "1. Fix billing flows (Verified by AI Analysis)\n"
            "2. Improve macro tooling (Trend detected via keyword patterns)\n"
            "3. Reinforce automation wins\n"
        )
        with patch.object(agent.ai_client, 'generate_analysis', new_callable=AsyncMock, return_value=response_text):
            result = await agent.execute(context)
        assert pytest.approx(result.data['detection_method_confidence'], 0.001) == 0.81
        assert pytest.approx(result.confidence, 0.01) == 0.924
        distribution = result.data['detection_method_distribution']
        assert pytest.approx(distribution.get('hybrid', 0), 0.1) == 20.0
        assert pytest.approx(distribution.get('keyword', 0), 0.1) == 20.0
        assert "(Verified by AI Analysis)" in " ".join(result.data['detection_method_tags'])

    def test_detection_method_tag_extraction(self):
        agent = InsightAgent()
        agent.workflow_type = 'topic_based'
        text = "Billing insight (Verified by AI Analysis). Keyword spike (Trend detected via keyword patterns)."
        parsed = agent._parse_insights_response(text)
        assert "(Verified by AI Analysis)" in parsed['detection_method_tags']
        assert "(Trend detected via keyword patterns)" in parsed['detection_method_tags']

    def test_detection_method_tag_missing_warning(self, caplog):
        agent = InsightAgent()
        agent.workflow_type = 'topic_based'
        with caplog.at_level('WARNING'):
            parsed = agent._parse_insights_response("Generic summary without tags.")
        assert parsed['detection_method_tags'] == []
        assert "missing detection method tags" in caplog.text

    def test_output_validation_topic_based(self, caplog):
        agent = InsightAgent()
        agent.workflow_type = 'topic_based'
        good_result = {
            'executive_summary': 'Summary',
            'major_themes': ['1. Theme', '2. Theme', '3. Theme'],
            'recommendations': ['1. Do A', '2. Do B', '3. Do C'],
            'synthesis_quality': 1.0,
            'detection_method_confidence': 0.9,
            'detection_method_distribution': {
                'llm_smart': 40.0,
                'llm_only': 10.0,
                'hybrid': 30.0,
                'keyword': 15.0,
                'sdk_only': 5.0,
                'fallback': 0.0
            },
            'detection_method_tags': ['(Verified by AI Analysis)']
        }
        with caplog.at_level('WARNING'):
            agent.validate_output(good_result)
        assert not caplog.records

        bad_result = {
            'executive_summary': 'Summary',
            'major_themes': ['1. Theme'],
            'recommendations': ['1. Do A'],
            'synthesis_quality': 0.5,
            'detection_method_confidence': 0.3,
            'detection_method_distribution': {},
            'detection_method_tags': []
        }
        with caplog.at_level('WARNING'):
            agent.validate_output(bad_result)
        assert "Detection method confidence is low" in caplog.text
        assert "missing detection_method_distribution" in caplog.text
        assert "did not include detection method tags" in caplog.text


class TestDetectionMethodMixedScenarios:

    @staticmethod
    def _mixed_distribution():
        return {
            'Billing': {
                'volume': 50,
                'percentage': 50.0,
                'detection_method': 'hybrid',
                'confidence': 0.85,
                'llm_smart_count': 0,
                'llm_only_count': 0,
                'hybrid_count': 50,
                'keyword_count': 0,
                'sdk_only_count': 0,
                'fallback_count': 0
            },
            'Automation': {
                'volume': 30,
                'percentage': 30.0,
                'detection_method': 'keyword',
                'confidence': 0.75,
                'llm_smart_count': 0,
                'llm_only_count': 0,
                'hybrid_count': 0,
                'keyword_count': 30,
                'sdk_only_count': 0,
                'fallback_count': 0
            },
            'AI Ops': {
                'volume': 20,
                'percentage': 20.0,
                'detection_method': 'llm_smart',
                'confidence': 0.95,
                'llm_smart_count': 20,
                'llm_only_count': 0,
                'hybrid_count': 0,
                'keyword_count': 0,
                'sdk_only_count': 0,
                'fallback_count': 0
            }
        }

    @staticmethod
    def _fallback_distribution():
        return {
            'Unknown/unresponsive': {
                'volume': 20,
                'percentage': 100.0,
                'detection_method': 'fallback',
                'confidence': 0.1,
                'llm_smart_count': 0,
                'llm_only_count': 0,
                'hybrid_count': 0,
                'keyword_count': 0,
                'sdk_only_count': 0,
                'fallback_count': 20
            }
        }

    @pytest.mark.asyncio
    async def test_mixed_detection_methods_hybrid_keyword_llm(self):
        insight_agent = InsightAgent()
        formatter_agent = OutputFormatterAgent(use_llm_formatting=False)
        context = build_topic_context(json.loads(json.dumps(self._mixed_distribution())))
        response_text = (
            "1. Hybrid-tagged Billing trend (Hybrid detection: AI + Keywords)\n"
            "2. Keyword Automation trend (Trend detected via keyword patterns)\n"
            "3. AI Ops improvements (Verified by AI Analysis)\n"
            "Recommendations:\n"
            "1. Fix billing (Hybrid detection: AI + Keywords)\n"
            "2. Improve automation macros (Trend detected via keyword patterns)\n"
            "3. Accelerate AI Ops (Verified by AI Analysis)\n"
        )
        with patch.object(insight_agent.ai_client, 'generate_analysis', new_callable=AsyncMock, return_value=response_text):
            insight_result = await insight_agent.execute(context)
        formatter_result = await formatter_agent.execute(context)
        formatted = formatter_result.data['formatted_output']
        assert "Hybrid Detection" in formatted
        assert "Trend detected via keyword patterns" in formatted
        assert "Verified by AI Analysis" in formatted
        distribution = insight_result.data['detection_method_distribution']
        assert pytest.approx(distribution.get('hybrid', 0), 0.1) == 50.0
        assert pytest.approx(distribution.get('keyword', 0), 0.1) == 30.0
        assert pytest.approx(distribution.get('llm_smart', 0), 0.1) == 20.0
        assert pytest.approx(insight_result.confidence, 0.01) == 0.936

    @pytest.mark.asyncio
    async def test_low_confidence_fallback_detection(self, caplog):
        insight_agent = InsightAgent()
        formatter_agent = OutputFormatterAgent(use_llm_formatting=False)
        context = build_topic_context(json.loads(json.dumps(self._fallback_distribution())))
        response_text = (
            "1. Sparse signals (Fallback classification (low confidence))\n"
            "Recommendations:\n"
            "1. Gather more data\n"
        )
        with patch.object(insight_agent.ai_client, 'generate_analysis', new_callable=AsyncMock, return_value=response_text):
            with caplog.at_level('WARNING'):
                insight_result = await insight_agent.execute(context)
        formatter_result = await formatter_agent.execute(context)
        formatted = formatter_result.data['formatted_output']
        assert "Fallback classification (low confidence)" in formatted
        assert pytest.approx(insight_result.data['detection_method_confidence'], 0.001) == 0.1
        assert pytest.approx(insight_result.confidence, 0.01) == 0.64
        assert "Detection method confidence is low" in caplog.text

    @pytest.mark.asyncio
    async def test_backward_compatibility_standard_workflow(self):
        agent = InsightAgent()
        context = AgentContext(
            analysis_id="standard",
            analysis_type="insight",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            conversations=[{'id': '1'}],
            previous_results={
                'CategoryAgent': {'data': {'category_distribution': {'Billing': 10}}},
                'SentimentAgent': {'data': {'sentiment_distribution': {'negative': 5}}}
            }
        )
        response_text = (
            "1. Billing issue\n"
            "2. Support improvement\n"
            "3. Macros fix\n"
            "Recommendations:\n"
            "1. Fix billing\n"
            "2. Improve support\n"
            "3. Enhance macros\n"
        )
        with patch.object(agent.ai_client, 'generate_analysis', new_callable=AsyncMock, return_value=response_text):
            result = await agent.execute(context)
        assert 'detection_method_confidence' not in result.data
        assert 'detection_method_distribution' not in result.data
        assert result.confidence_level in [ConfidenceLevel.HIGH.value, ConfidenceLevel.HIGH]

@pytest.mark.asyncio
class TestSentimentAgentUpgrade:
    
    async def test_agent_instructions_forbid_generic_labels(self):
        agent = SentimentAgentWrapper()
        instructions = agent.get_agent_specific_instructions().lower()
        assert "hilary" in instructions
        assert "positive sentiment" in instructions
        assert "mixed sentiment" in instructions
        assert "per-conversation" in instructions
    
    async def test_global_examples_include_nuance(self):
        agent = SentimentAgentWrapper()
        examples = agent.get_global_examples_public()
        assert "✓" in examples
        assert " but " in examples.lower()
        assert examples.count("✓") >= 3
    
    async def test_refusal_detection_and_fallback(self):
        agent = SentimentAgentWrapper()
        context = AgentContext(
            analysis_id="sentiment_refusal",
            analysis_type="sentiment",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            conversations=[{'id': '1', 'conversation_parts': {'conversation_parts': [{'body': 'billing rage'}]}}],
            metadata={}
        )
        agent.ai_client.generate_analysis = AsyncMock(side_effect=["I cannot do that", "Still insufficient data"])
        result = await agent.execute(context)
        assert result.success
        assert result.data['method'] == 'fallback_template'
        assert result.data['sentiment_metrics']['refusal_count'] == 2
        assert result.data['sentiment_metrics']['fallback_used'] is True
        assert "but" in result.data['sentiment_insight'].lower()
    
    async def test_validate_output_quality_metadata(self):
        agent = SentimentAgentWrapper()
        good_result = {
            'sentiment_insight': "Customers love AI Builder but need billing clarity before scaling.",
            'sentiment_distribution': [{'label': 'builder-love', 'percentage': 70, 'nuance': 'love builder but hate billing'}],
            'supporting_evidence': [{'quote': "Love the builder speed but billing is wild."}]
        }
        agent.validate_output(good_result)
        assert good_result['quality_score'] >= 0.7
        assert good_result['contains_nuance'] is True
        assert not good_result['validation_warnings']
        
        bad_result = {
            'sentiment_insight': "Negative sentiment detected about billing.",
            'sentiment_distribution': [],
            'supporting_evidence': []
        }
        agent.validate_output(bad_result)
        assert bad_result['quality_score'] < 0.5
        assert any("Generic pattern detected" in warning for warning in bad_result['validation_warnings'])
    
    async def test_execute_uses_llm_output_structure(self):
        agent = SentimentAgentWrapper()
        context = AgentContext(
            analysis_id="sentiment_structured",
            analysis_type="sentiment",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            conversations=[
                {'id': 'a', 'conversation_parts': {'conversation_parts': [{'body': 'love builder'}]}},
                {'id': 'b', 'conversation_parts': {'conversation_parts': [{'body': 'hate billing'}]}}
            ],
            metadata={}
        )
        payload = {
            "sentiment_insight": "Customers love AI Builder but are livid about billing opacity.",
            "sentiment_distribution": [
                {"label": "builder-love", "percentage": 65, "nuance": "Love the speed but want billing clarity"},
                {"label": "billing-friction", "percentage": 55, "nuance": "Praising support yet raging about invoices"}
            ],
            "supporting_evidence": [
                {"quote": "Love builder but billing feels like roulette.", "conversation_id": "a", "tone": "mixed"}
            ]
        }
        agent.ai_client.generate_analysis = AsyncMock(return_value=json.dumps(payload))
        result = await agent.execute(context)
        assert result.success
        assert result.data['method'] == 'llm'
        assert len(result.data['sentiment_distribution']) == 2
        assert result.data['supporting_evidence'][0]['quote'].startswith("Love builder")
        assert result.data['sentiment_metrics']['retry_count'] == 0
        assert result.data['sentiment_metrics']['fallback_used'] is False
    
    async def test_looks_like_refusal_helper(self):
        agent = SentimentAgentWrapper()
        assert agent.looks_like_refusal_public("I cannot determine that with the given info.")
        assert not agent.looks_like_refusal_public("Users love the product but hate the fees.")
    
    async def test_fallback_sentence_public(self):
        agent = SentimentAgentWrapper()
        fallback = agent.fallback_sentence_public()
        assert "but" in fallback.lower()
        context = AgentContext(
            analysis_id="fallback",
            analysis_type="sentiment",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),
            conversations=[{'id': '1'}],
            metadata={}
        )
        contextual = agent.fallback_sentence_public(context)
        assert "but" in contextual.lower()


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

@pytest.mark.asyncio
class TestPresentationBuilderInsights:
    
    def test_presentation_builder_preserves_sentiment_insights(self):
        """Verify that PresentationBuilder uses verbatim sentiment insights."""
        builder = PresentationBuilder()
        
        # Mock category results with verbatim insights
        results = {
            'Billing': {
                'volume': 100,
                'sentiment_breakdown': {
                    'sentiment_insight': 'Users love the speed but hate the fees.',
                    'sentiment': 'mixed',
                    'confidence': 0.9
                }
            }
        }
        
        output = builder._format_sentiment_breakdown(results)
        
        # Assert intent: Verbatim insight is preserved
        assert 'Users love the speed but hate the fees' in output
        assert 'Billing' in output
        assert 'mixed' not in output  # Generic label should not be used if insight exists
        
    def test_methodology_slide_includes_fallback_metrics(self):
        """Verify methodology slide includes optimization metrics."""
        builder = PresentationBuilder()
        
        results = {'Billing': {'volume': 100}}
        metadata = {
            'start_date': '2023-01-01', 
            'end_date': '2023-01-07',
            'fallback_metrics': {
                'llm_calls': 50,
                'high_confidence_skip_count': 50,
                'total_conversations': 100
            }
        }
        
        output = builder._build_methodology_appendix(results, metadata, 100)
        
        assert 'Optimization Efficiency' in output
        assert '50.0%' in output
        assert 'High-Confidence Skips' in output

    def test_subtopic_breakdown_with_percentages(self):
        """Verify subtopic breakdown is formatted correctly."""
        builder = PresentationBuilder()
        
        results = {'Billing': {'volume': 100}}
        metadata = {
            'subtopics_by_tier1_topic': {
                'Billing': {
                    'tier2': {
                        'Refunds': {'count': 30},
                        'Invoices': {'count': 70}
                    }
                }
            }
        }
        
        output = builder._build_subtopic_breakdown_section(results, metadata)
        
        assert 'Billing Breakdown' in output
        assert 'Refunds' in output
        assert '30' in output
        assert '30.0%' in output
        assert 'Invoices' in output
        assert '70.0%' in output

    def test_voc_detailed_narrative_includes_sentiment_insights(self):
        """Detailed VoC narrative should surface verbatim sentiment insights."""
        builder = PresentationBuilder()
        results = {
            'Billing': {
                'volume': 42,
                'sentiment_breakdown': {
                    'sentiment_insight': 'Users love the speed but hate the fees.',
                    'sentiment': 'mixed',
                    'confidence': 0.91
                }
            }
        }
        metadata = {
            'total_conversations': 42,
            'ai_model': 'gpt-4o',
            'start_date': '2024-10-01',
            'end_date': '2024-10-07'
        }

        narrative = builder._build_voc_detailed_narrative(
            results=results,
            insights=[],
            agent_feedback={},
            metadata=metadata,
            historical_trends=None,
            period_type='weekly'
        )

        assert '**Sentiment Insight Narrative**' in narrative
        assert 'Users love the speed but hate the fees.' in narrative
        assert '| Category | Sentiment | Confidence | Volume |' in narrative
