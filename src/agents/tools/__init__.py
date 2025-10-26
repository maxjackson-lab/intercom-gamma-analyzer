"""
Tool infrastructure for agent function calling.

This module provides the base classes and registry for tools that agents can use during analysis.
"""

from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.agents.tools.registry import ToolRegistry
from src.agents.tools.admin_tools import AdminProfileLookupTool
from src.agents.tools.database_tools import QueryConversationsTool
from src.agents.tools.metric_tools import CalculateFCRTool, CalculateCSATTool

__all__ = [
    'BaseTool',
    'ToolDefinition',
    'ToolParameter',
    'ToolResult',
    'ToolRegistry',
    'AdminProfileLookupTool',
    'QueryConversationsTool',
    'CalculateFCRTool',
    'CalculateCSATTool'
]
