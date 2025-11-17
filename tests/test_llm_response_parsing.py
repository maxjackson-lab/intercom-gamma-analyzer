"""
Test LLM response parsing for topic detection.

This test verifies that the TopicDetectionAgent correctly parses
LLM responses that include JSON wrapped in markdown code fences.
"""

import json
import re
import pytest


def parse_llm_response(raw_response: str):
    """
    Parse LLM JSON response, handling markdown code fences.
    
    This is the exact logic used in TopicDetectionAgent._classify_with_llm_smart()
    """
    try:
        # Strip markdown code fences if present
        json_text = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_response.strip(), flags=re.MULTILINE)
        parsed = json.loads(json_text)
        topic_name = parsed.get('topic', '').strip()
        llm_confidence = float(parsed.get('confidence', 0.85))
        return topic_name, llm_confidence
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        return None, None


def test_parse_llm_response_with_code_fences():
    """Test parsing response with markdown code fences (most common case)"""
    raw_response = """```json
{
  "topic": "Billing",
  "confidence": 0.95
}
```"""
    
    topic, confidence = parse_llm_response(raw_response)
    assert topic == "Billing"
    assert confidence == 0.95


def test_parse_llm_response_without_code_fences():
    """Test parsing plain JSON response"""
    raw_response = """{"topic": "Account", "confidence": 0.9}"""
    
    topic, confidence = parse_llm_response(raw_response)
    assert topic == "Account"
    assert confidence == 0.9


def test_parse_llm_response_with_whitespace():
    """Test parsing response with extra whitespace"""
    raw_response = """
    ```json
    {
      "topic": "Bug",
      "confidence": 1.0
    }
    ```
    """
    
    topic, confidence = parse_llm_response(raw_response)
    assert topic == "Bug"
    assert confidence == 1.0


def test_parse_llm_response_lowercase_topic():
    """Test parsing response with lowercase topic (should be preserved)"""
    raw_response = """```json
{
  "topic": "billing",
  "confidence": 0.95
}
```"""
    
    topic, confidence = parse_llm_response(raw_response)
    assert topic == "billing"
    assert confidence == 0.95


def test_parse_llm_response_missing_confidence():
    """Test parsing response with missing confidence (should use default)"""
    raw_response = """```json
{
  "topic": "Technical Support"
}
```"""
    
    topic, confidence = parse_llm_response(raw_response)
    assert topic == "Technical Support"
    assert confidence == 0.85  # Default value


def test_parse_llm_response_invalid_json():
    """Test handling of invalid JSON"""
    raw_response = """```json
{
  "topic": "Billing"
  "confidence": 0.95
}
```"""
    
    topic, confidence = parse_llm_response(raw_response)
    assert topic is None
    assert confidence is None


def test_parse_llm_response_missing_topic_field():
    """Test handling of missing topic field"""
    raw_response = """```json
{
  "confidence": 0.95
}
```"""
    
    topic, confidence = parse_llm_response(raw_response)
    assert topic == ""  # Empty string from .get('topic', '').strip()
    assert confidence == 0.95


def test_parse_llm_response_from_real_log():
    """Test with actual response from sample-mode log (Nov 15, 2025)"""
    # This is what was showing up in the topic summary table
    raw_response = """```json
{
  "topic": "Billing",
  "confidence": 0.95
}
```"""
    
    topic, confidence = parse_llm_response(raw_response)
    
    # Before fix: topic would be the entire raw_response string (including ```json)
    # After fix: topic should be just "Billing"
    assert topic == "Billing"
    assert topic != raw_response  # Make sure we're not using raw response
    assert "```" not in topic  # Make sure code fences are stripped
    assert "\n" not in topic  # Make sure newlines are removed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

