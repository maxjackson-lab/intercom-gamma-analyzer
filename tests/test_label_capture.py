"""
Test for label capture and aggregation.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.topic_detection_agent import TopicDetectionAgent
from src.agents.base_agent import AgentContext

@pytest.mark.asyncio
async def test_label_capture_and_structure():
    """Test that the agent captures both topic and label from LLM."""
    agent = TopicDetectionAgent()
    agent.ai_client = AsyncMock()
    
    # Mock LLM response with JSON including label
    mock_json = '{"topic": "Billing", "label": "Double Charge Refund", "confidence": 0.9}'
    agent.ai_client.client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=mock_json))
    ]
    agent.ai_client.client.chat.completions.create.return_value.usage.total_tokens = 100
    
    # Test the method directly
    result = await agent._classify_with_llm_smart("test text", sdk_hint="Billing")
    
    assert result is not None
    assert result['topic'] == 'Billing'
    assert result['subtopic'] == 'Double Charge Refund'
    assert result['method'] == 'llm_smart'

@pytest.mark.asyncio
async def test_normalization_preserves_label():
    """Test that label is preserved even when topic is normalized."""
    agent = TopicDetectionAgent()
    agent.ai_client = AsyncMock()
    
    # Mock LLM return with slightly messy topic but clear label
    mock_json = '{"topic": "billing", "label": "Invoice PDF Download", "confidence": 0.8}'
    agent.ai_client.client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=mock_json))
    ]
    agent.ai_client.client.chat.completions.create.return_value.usage.total_tokens = 100
    
    result = await agent._classify_with_llm_smart("test text")
    
    assert result['topic'] == 'Billing'  # Normalized
    assert result['subtopic'] == 'Invoice PDF Download'  # Preserved

if __name__ == "__main__":
    pass

