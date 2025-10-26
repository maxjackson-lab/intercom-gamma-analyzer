"""
Tool infrastructure for agent function calling.

This module provides the base classes and registry for tools that agents can use during analysis.
"""

from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.agents.tools.registry import ToolRegistry

__all__ = [
    'BaseTool',
    'ToolDefinition',
    'ToolParameter',
    'ToolResult',
    'ToolRegistry'
]