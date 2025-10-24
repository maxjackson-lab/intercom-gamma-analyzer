"""
Unit tests for FinEscalationAnalyzer.detect_escalation_request method.

This test suite validates the new detect_escalation_request method:
- Detection of escalation phrases in conversation text
- Case-insensitive matching
- Extraction from both full_text and conversation_parts
- Negative cases without escalation phrases
"""

import pytest
from typing import Dict, Any

from src.services.fin_escalation_analyzer import FinEscalationAnalyzer


@pytest.fixture
def analyzer():
    """Return FinEscalationAnalyzer instance."""
    return FinEscalationAnalyzer()


@pytest.fixture
def conversation_with_escalation() -> Dict[str, Any]:
    """Conversation dict with escalation phrases in full_text and conversation_parts."""
    return {
        'id': 'test_conv_escalation',
        'full_text': 'I need to speak to a human support agent immediately.',
        'conversation_parts': {
            'conversation_parts': [
                {'body': 'This is not helping. I want to talk to a person.'},
                {'body': 'Please escalate this to a supervisor.'}
            ]
        },
        'source': {'body': 'Transfer me to a manager.'}
    }


@pytest.fixture
def conversation_without_escalation() -> Dict[str, Any]:
    """Conversation dict without escalation phrases."""
    return {
        'id': 'test_conv_no_escalation',
        'full_text': 'Thank you for your help. The issue is resolved.',
        'conversation_parts': {
            'conversation_parts': [
                {'body': 'I appreciate the assistance.'},
                {'body': 'Everything is working now.'}
            ]
        },
        'source': {'body': 'Great service!'}
    }


class TestDetectEscalationRequest:
    """Test suite for detect_escalation_request method."""

    def test_detect_escalation_request_with_speak_to_human(self, analyzer, conversation_with_escalation):
        """Test detection of 'speak to human' phrase."""
        result = analyzer.detect_escalation_request(conversation_with_escalation)
        assert result is True

    def test_detect_escalation_request_with_escalate(self, analyzer, conversation_with_escalation):
        """Test detection of 'escalate' phrase."""
        result = analyzer.detect_escalation_request(conversation_with_escalation)
        assert result is True

    def test_detect_escalation_request_with_supervisor(self, analyzer, conversation_with_escalation):
        """Test detection of 'supervisor' phrase."""
        result = analyzer.detect_escalation_request(conversation_with_escalation)
        assert result is True

    def test_detect_escalation_request_negative(self, analyzer, conversation_without_escalation):
        """Test returns False for conversation without escalation phrases."""
        result = analyzer.detect_escalation_request(conversation_without_escalation)
        assert result is False

    def test_detect_escalation_request_case_insensitive(self, analyzer):
        """Test case-insensitive matching."""
        conversation = {
            'id': 'test_case_insensitive',
            'full_text': 'I NEED TO SPEAK TO A HUMAN SUPPORT AGENT.',
            'conversation_parts': {'conversation_parts': []}
        }
        result = analyzer.detect_escalation_request(conversation)
        assert result is True

    def test_detect_escalation_request_in_conversation_parts(self, analyzer):
        """Test detection in conversation parts, not just source."""
        conversation = {
            'id': 'test_parts_only',
            'full_text': '',
            'conversation_parts': {
                'conversation_parts': [
                    {'body': 'Please transfer me to a real person.'}
                ]
            },
            'source': {'body': 'No escalation here.'}
        }
        result = analyzer.detect_escalation_request(conversation)
        assert result is True