import asyncio
import logging
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.insight_agent import InsightAgent
from src.agents.sentiment_agent import SentimentAgent
from src.config.taxonomy import TaxonomyManager
from src.services.presentation_builder import PresentationBuilder


def create_test_conversation(text: str, conversation_id: str = "conv-1") -> Dict[str, Any]:
    return {
        "id": conversation_id,
        "source": {"author": {"name": "Customer"}},
        "custom_attributes": {},
        "conversation_parts": {"conversation_parts": []},
        "body": text,
    }


def create_russian_conversation(keyword: str, topic: str) -> Dict[str, Any]:
    return create_test_conversation(f"Это сообщение про {keyword} и связано с {topic}")


def create_korean_conversation(keyword: str, topic: str) -> Dict[str, Any]:
    return create_test_conversation(f"이 대화는 {topic} 카테고리에 대한 {keyword} 문제를 다룹니다.")


def assert_hilary_style(text: str) -> None:
    lowered = text.lower()
    connectors = [" but ", " however ", " yet ", " although ", " even though "]
    assert any(connector in lowered for connector in connectors), "Insight missing nuance connector"
    assert len(text.split()) >= 8, "Insight too short for Hilary style"


@pytest.fixture()
def mock_ai_client(monkeypatch):
    import src.agents.topic_detection_agent as topic_detection_module

    mock_client = MagicMock(name="TopicDetectionMockClient")
    mock_client.client = MagicMock()
    mock_client.max_tokens = 1
    mock_client.temperature = 0.1

    monkeypatch.setattr(topic_detection_module, "get_ai_client", lambda: mock_client)
    monkeypatch.setattr(topic_detection_module, "get_recommended_semaphore", lambda _client: asyncio.Semaphore(1))
    return mock_client


@pytest.fixture()
def presentation_builder() -> PresentationBuilder:
    return PresentationBuilder()


@pytest.fixture()
def insight_agent_stub() -> InsightAgent:
    agent = InsightAgent.__new__(InsightAgent)
    agent.logger = logging.getLogger("insight-agent-test")
    agent.workflow_type = "topic_based"
    return agent


@pytest.fixture()
def sentiment_agent_stub() -> SentimentAgent:
    agent = SentimentAgent.__new__(SentimentAgent)
    agent.logger = logging.getLogger("sentiment-agent-test")
    return agent


class TestConfidenceRoutingE2E:
    @pytest.mark.asyncio
    async def test_confidence_routing_balances_llm_usage(self, mock_ai_client, monkeypatch, caplog):
        caplog.set_level(logging.DEBUG)
        agent = TopicDetectionAgent(llm_first=True)

        llm_mock = AsyncMock(return_value={"topic": "Bug", "confidence": 0.72, "method": "llm_smart"})
        monkeypatch.setattr(agent, "_classify_with_llm_smart", llm_mock)

        high_conf_conv = create_test_conversation("Не могу войти в аккаунт, пароль не работает")
        result_high = await agent._detect_topics_for_conversation(high_conf_conv)
        assert result_high[0]["method"] in {"keyword", "hybrid"}
        assert agent.fallback_metrics["high_confidence_skip_count"] >= 1
        llm_mock.assert_not_awaited()
        assert any("High confidence match" in record.message for record in caplog.records)

        low_conf_conv = create_test_conversation("Customers mention unfamiliar workflow with vague wording", "conv-low")
        await agent._detect_topics_for_conversation(low_conf_conv)
        assert agent.fallback_metrics["llm_calls"] >= 1
        assert llm_mock.await_count == 1


class TestSentimentInsightFlowE2E:
    def test_sentiment_insight_flows_to_presentation(self, presentation_builder: PresentationBuilder):
        category_results = {
            "Billing Friction": {
                "volume": 58,
                "sentiment_breakdown": {
                    "sentiment": "negative",
                    "confidence": 0.91,
                    "sentiment_insight": (
                        "Leads appreciate rapid refunds but still threaten churn when invoices "
                        "land without advance notice."
                    ),
                },
            }
        }
        breakdown = presentation_builder._format_sentiment_breakdown(category_results)
        assert "Leads appreciate rapid refunds" in breakdown
        assert_hilary_style(category_results["Billing Friction"]["sentiment_breakdown"]["sentiment_insight"])


class TestMetricsVisibilityE2E:
    def test_methodology_appendix_contains_metrics(self, presentation_builder: PresentationBuilder):
        metadata = {
            "start_date": "2025-11-01",
            "end_date": "2025-11-07",
            "period_type": "weekly",
            "fallback_metrics": {
                "total_conversations": 120,
                "llm_calls": 70,
                "high_confidence_skip_count": 50,
            },
        }
        appendix = presentation_builder._build_methodology_appendix({}, metadata, total_conversations=120)
        assert "| High-Confidence Skips | 50 |" in appendix
        assert "Optimization Rate" in appendix


class TestSubtopicVisualizationE2E:
    def test_subtopic_breakdown_shows_percentages(self, presentation_builder: PresentationBuilder):
        metadata = {
            "subtopics_by_tier1_topic": {
                "Billing": {
                    "tier2": {
                        "Refund Delays": {"count": 30},
                        "Invoice Errors": {"count": 20},
                    }
                }
            }
        }
        section = presentation_builder._build_subtopic_breakdown_section({}, metadata)
        assert "**Refund Delays**" in section
        assert "(60.0%)" in section
        assert "(40.0%)" in section


class TestDetectionMethodTaggingE2E:
    def test_detection_method_tags_enforced(self, insight_agent_stub: InsightAgent):
        text = (
            "Billing reliability (Verified by AI Analysis) highlights refunds. "
            "Trend detected via keyword patterns for attachment bugs."
        )
        tags = insight_agent_stub._extract_detection_method_tags_from_text(text)
        assert "(Verified by AI Analysis)" in tags
        assert "(Trend detected via keyword patterns)" in tags

        payload = {
            "executive_summary": text,
            "major_themes": ["1. Billing improvements (Verified by AI Analysis)"],
            "recommendations": ["1. Harden exports (Trend detected via keyword patterns)"],
            "detection_method_tags": tags,
            "detection_method_confidence": 0.92,
            "detection_method_distribution": {"llm_smart": 60.0, "keyword": 40.0},
        }
        assert insight_agent_stub.validate_output(payload)
        assert payload["detection_method_tags"] == tags


class TestMultiLanguageE2E:
    def test_taxonomy_matches_russian_and_korean_keywords(self):
        taxonomy = TaxonomyManager()
        conversations = [
            ("Account", create_russian_conversation("аккаунт", "Account")),
            ("Billing", create_russian_conversation("оплата", "Billing")),
            ("Bug", create_korean_conversation("오류", "Bug")),
        ]
        for expected, conv in conversations:
            classifications = taxonomy.classify_conversation(conv)
            assert classifications
            assert classifications[0]["category"] == expected
            assert classifications[0]["confidence"] >= 0.5


class TestSentimentAgentUpgradeE2E:
    def test_sentiment_agent_quality_scoring(self, sentiment_agent_stub: SentimentAgent):
        payload = {
            "sentiment_insight": (
                "Customers rave about lightning-fast drafts but still escalate when exports crash mid-demo."
            ),
            "sentiment_distribution": [
                {"label": "Speed praise", "percentage": 65.0, "nuance": "Love the velocity"},
                {"label": "Export crashes", "percentage": 35.0, "nuance": "but demos still fail"},
            ],
            "supporting_evidence": [{"quote": "Deck failed mid-pitch", "conversation_id": "C-1", "tone": "frustrated"}],
        }
        assert sentiment_agent_stub.validate_output(payload)
        assert payload["quality_score"] > 0.5
        assert payload["contains_nuance"] is True
        assert payload["sentiment_metrics"]["generic_pattern_count"] == 0




