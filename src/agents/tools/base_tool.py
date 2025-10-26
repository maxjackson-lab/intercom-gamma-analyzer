from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
import logging
import time


class ToolParameter(BaseModel):
    """Define individual tool parameters following JSON Schema conventions."""
    name: str
    type: Literal["string", "number", "integer", "boolean", "array", "object"]
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """Describe tool capabilities in a format compatible with OpenAI/Anthropic function calling."""
    name: str
    description: str
    parameters: List[ToolParameter]

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        }


class ToolResult(BaseModel):
    """Standardized wrapper for tool execution results."""
    success: bool
    data: Any
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    
    class Config:
        arbitrary_types_allowed = True


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Provides common functionality for tool execution, error handling, and logging.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"tools.{name}")
    
    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """
        Return the tool's definition with parameters.
        
        Returns:
            ToolDefinition: The tool's schema definition
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool's logic with arbitrary keyword arguments.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: The execution result
        """
        pass
    
    async def safe_execute(self, **kwargs) -> ToolResult:
        """
        Wrapper that catches exceptions, measures execution time, logs errors,
        and returns ToolResult with error details if execution fails.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: The execution result, including error handling
        """
        start_time = time.time()
        try:
            result = await self.execute(**kwargs)
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.exception(f"Tool execution failed: {str(e)}")
            return ToolResult(
                success=False,
                data=None,
                error_message=str(e),
                execution_time_ms=execution_time
            )