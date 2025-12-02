"""
Multi-agent system for advanced Intercom analysis.

This module provides specialized AI agents for different aspects of conversation analysis,
with built-in hallucination prevention and quality validation.

Note: MultiAgentOrchestrator is deprecated—prefer UnifiedOrchestrator + MultiAgentStrategy.
"""

from src.agents.base_agent import BaseAgent, AgentResult, AgentContext
# Deprecated: Use UnifiedOrchestrator with MultiAgentStrategy instead.
from src.agents.orchestrator import MultiAgentOrchestrator
from src.agents.subtopic_detection_agent import SubTopicDetectionAgent

__all__ = [
    'BaseAgent',
    'AgentResult',
    'AgentContext',
    'MultiAgentOrchestrator',
    'SubTopicDetectionAgent'
]

__deprecated__ = ['MultiAgentOrchestrator']

