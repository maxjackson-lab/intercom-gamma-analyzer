from typing import Dict, List, Optional, Any
from src.agents.tools.base_tool import BaseTool, ToolResult, ToolDefinition
import logging
import hashlib
import json


class ToolRegistry:
    """
    Manages tool lifecycle, execution, and caching.
    
    Provides a centralized registry for tools with support for caching,
    performance tracking, and error handling.
    """
    
    def __init__(self, enable_caching: bool = True):
        """
        Initialize the tool registry.
        
        Args:
            enable_caching: Whether to enable caching for tool results
        """
        self.tools: Dict[str, BaseTool] = {}
        self.enable_caching = enable_caching
        self.cache: Dict[str, ToolResult] = {}
        self.execution_count: Dict[str, int] = {}
        self.cache_hit_count: int = 0
        self.logger = logging.getLogger(__name__)
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool instance for use by agents.
        
        Args:
            tool: The tool instance to register
        """
        self.tools[tool.name] = tool
        self.execution_count[tool.name] = 0
        self.logger.info(f"Registered tool: {tool.name}")
    
    def get_tool_definitions(self) -> List[Dict]:
        """
        Get all tool schemas for passing to AI model (function calling).
        
        Returns:
            List of tool definitions in OpenAI format
        """
        definitions = []
        for tool in self.tools.values():
            definition = tool.get_definition()
            openai_format = definition.to_openai_format()
            definitions.append(openai_format)
        return definitions
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name with caching support.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: The execution result
        """
        if tool_name not in self.tools:
            return ToolResult(success=False, data=None, error_message=f"Tool '{tool_name}' not found in registry")
        
        cache_key = self._make_cache_key(tool_name, kwargs)
        if self.enable_caching and cache_key in self.cache:
            self.cache_hit_count += 1
            self.logger.info(f"Cache hit for tool: {tool_name}")
            return self.cache[cache_key].model_copy(deep=True)
        
        tool = self.tools[tool_name]
        result = await tool.safe_execute(**kwargs)
        self.execution_count[tool_name] += 1
        
        if result.success and self.enable_caching:
            self.cache[cache_key] = result.model_copy(deep=True)
        
        self.logger.info(f"Tool executed: {tool_name} - Success: {result.success}, Time: {result.execution_time_ms:.1f}ms")
        return result
    
    def _make_cache_key(self, tool_name: str, kwargs: Dict) -> str:
        """
        Generate deterministic cache key from tool name and parameters.
        
        Args:
            tool_name: Name of the tool
            kwargs: Tool parameters
            
        Returns:
            MD5 hash string as cache key
        """
        sorted_kwargs = json.dumps(kwargs, sort_keys=True, default=str)
        hash_input = f"{tool_name}:{sorted_kwargs}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get tool usage statistics for monitoring and debugging.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_tools": len(self.tools),
            "execution_counts": self.execution_count,
            "cache_hits": self.cache_hit_count,
            "cache_entries": len(self.cache),
            "cache_enabled": self.enable_caching
        }
    
    def clear_cache(self) -> None:
        """
        Allow manual cache invalidation if needed.
        """
        self.cache.clear()
        self.logger.info("Cache cleared")