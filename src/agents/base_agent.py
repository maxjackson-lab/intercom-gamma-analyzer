"""
Base agent class with integrated hallucination prevention.

Implements the core patterns from Claude's research:
- "I Don't Know" permission
- "According To" grounding
- Confidence scoring
- Chain-of-Verification
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import logging
import json
import time

# Conditional import for ToolRegistry to avoid circular imports
try:
    from src.agents.tools.registry import ToolRegistry
except ImportError:
    ToolRegistry = None

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for agent outputs"""
    HIGH = "high"      # >0.8 confidence
    MEDIUM = "medium"  # 0.6-0.8 confidence
    LOW = "low"        # <0.6 confidence


class AgentContext(BaseModel):
    """Context passed to agents containing necessary data and metadata"""
    analysis_id: str
    analysis_type: str
    start_date: datetime
    end_date: datetime
    conversations: Optional[List[Dict]] = None
    previous_results: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True


class AgentMetrics(BaseModel):
    """Structured metrics for agent execution"""
    execution_time: float = 0.0
    input_count: int = 0
    output_count: int = 0
    llm_calls: int = 0
    token_count: int = 0
    selected_examples_count: int = 0
    error_count: int = 0
    
    class Config:
        arbitrary_types_allowed = True


class AgentResult(BaseModel):
    """Standardized output from agents with quality metadata"""
    agent_name: str
    success: bool
    data: Dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    confidence_level: ConfidenceLevel
    limitations: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    verification_passed: bool = True
    execution_time: float = 0.0
    token_count: int = 0
    error_message: Optional[str] = None
    metrics: Optional[AgentMetrics] = None
    
    class Config:
        use_enum_values = True


class BaseAgent(ABC):
    """
    Abstract base class for all analysis agents.

    Provides common functionality:
    - Hallucination prevention
    - Input/output validation
    - Confidence scoring
    - Error handling
    - Tool calling support (OpenAI function calling)

    Tool Calling:
        Agents can optionally use tools by passing a ToolRegistry to __init__.
        Use execute_with_tools() instead of execute() to enable multi-iteration
        tool calling with automatic tracking and audit trail support.

    Example:
        ```python
        class MyAgent(BaseAgent):
            def __init__(self):
                tool_registry = ToolRegistry()
                tool_registry.register_tool(MyTool())
                super().__init__(
                    name="MyAgent",
                    tool_registry=tool_registry
                )

            async def execute(self, context):
                # Use tool-enabled execution
                return await self.execute_with_tools(context)
        ```
    """
    
    def __init__(self, name: str, model: str = "gpt-4o", temperature: float = 0.3, tool_registry: Optional['ToolRegistry'] = None):
        self.name = name
        self.model = model
        self.temperature = temperature
        self.logger = logging.getLogger(f"agents.{name}")
        self.tool_registry = tool_registry
        self.tool_calls_made: List[Dict[str, Any]] = []
        self.logger.info(f"Agent {name} initialized with tools: {tool_registry is not None}")
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's specialized task.

        Args:
            context: AgentContext with all necessary data

        Returns:
            AgentResult with validated output and metadata
        """
        pass

    async def execute_with_tools(self, context: AgentContext, max_tool_iterations: int = 3) -> AgentResult:
        """
        Execute agent with tool calling enabled (multi-iteration loop).

        This method orchestrates the tool calling flow:
        1. Builds initial prompt and creates message list
        2. Calls AI with tool definitions
        3. If AI wants to call tools:
           - Executes each tool
           - Tracks tool calls for audit trail
           - Feeds results back to AI
           - Continues loop
        4. Returns final AI response with tool call metadata

        Args:
            context: AgentContext with all necessary data
            max_tool_iterations: Maximum number of tool calling iterations (default: 3)

        Returns:
            AgentResult with validated output, confidence, and tool call metadata

        Note:
            - Falls back to regular execute() if no tool_registry is available
            - Tool execution failures are fed back to model for adaptation
            - Tracks all tool calls in self.tool_calls_made for audit trail
        """
        start_time = time.time()

        try:
            # Check if tools are available
            if self.tool_registry is None:
                self.logger.warning("No tool registry available, falling back to regular execution")
                return await self.execute(context)

            # Validate input
            self.validate_input(context)

            # Clear tool calls tracking
            self.tool_calls_made = []

            # Build initial prompt
            initial_prompt = self.build_prompt(context)

            # Create initial messages list
            messages = [
                {"role": "system", "content": initial_prompt}
            ]

            # Tool calling loop
            iteration = 0
            response = None

            while iteration < max_tool_iterations:
                iteration += 1
                self.logger.info(f"Tool calling iteration {iteration}/{max_tool_iterations}")

                # Call AI with tools
                response = await self._call_ai_with_tools(messages, context)
                response_message = response.choices[0].message

                # Check if model wants to call tools
                if response_message.tool_calls:
                    self.logger.info(f"Model requested {len(response_message.tool_calls)} tool call(s)")

                    # Prepare to collect tool call messages
                    tool_call_messages = []

                    # Execute each tool call
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        self.logger.info(f"Agent calling tool: {tool_name} with args: {tool_args}")

                        # Execute tool
                        tool_result = await self.tool_registry.execute_tool(tool_name, **tool_args)

                        # Track tool call
                        self.tool_calls_made.append({
                            'tool_name': tool_name,
                            'arguments': tool_args,
                            'result': tool_result.data if tool_result.success else None,
                            'success': tool_result.success,
                            'error_message': tool_result.error_message,
                            'execution_time_ms': tool_result.execution_time_ms
                        })

                        # Append tool result message
                        tool_call_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result.data) if tool_result.success else json.dumps({"error": tool_result.error_message})
                        })

                    # Append assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": response_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in response_message.tool_calls
                        ]
                    })

                    # Append all tool result messages
                    messages.extend(tool_call_messages)

                    # Continue loop - model can make more tool calls
                    continue
                else:
                    # No tool calls - model is done
                    self.logger.info("Model did not request any tool calls - execution complete")
                    break

            # Extract final content
            final_content = response.choices[0].message.content if response else ""

            execution_time = time.time() - start_time
            self.logger.info(f"Tool-enabled execution complete. Made {len(self.tool_calls_made)} tool calls in {execution_time:.2f}s")

            # Parse final content into result data
            # Base implementation returns generic result - subclasses should override
            result_data = {
                'response': final_content,
                'tool_calls_made': self.tool_calls_made
            }

            # Calculate confidence
            confidence, confidence_level = self.calculate_confidence(result_data, context)

            # Extract token count from response
            token_count = 0
            if response and hasattr(response, 'usage') and response.usage:
                token_count = getattr(response.usage, 'total_tokens', 0)

            # Return AgentResult
            return AgentResult(
                agent_name=self.name,
                success=True,
                data=result_data,
                confidence=confidence,
                confidence_level=confidence_level,
                sources=["AI analysis", "Tool executions"],
                execution_time=execution_time,
                token_count=token_count
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Tool-enabled execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={'tool_calls_made': self.tool_calls_made},
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                error_message=str(e),
                execution_time=execution_time,
                token_count=0
            )

    @abstractmethod
    def validate_input(self, context: AgentContext) -> bool:
        """
        Validate input before processing.
        
        Args:
            context: AgentContext to validate
            
        Returns:
            True if valid, raises ValueError if invalid
        """
        pass
    
    @abstractmethod
    def validate_output(self, result: Dict[str, Any]) -> bool:
        """
        Validate output before returning.
        
        Args:
            result: Raw output to validate
            
        Returns:
            True if valid, raises ValueError if invalid
        """
        pass
    
    def get_hallucination_prevention_prompt(self) -> str:
        """
        Get base hallucination prevention instructions.
        
        From Claude's research - most effective patterns:
        1. Explicit "I Don't Know" permission
        2. Forbidden from inventing data
        3. "According to" grounding required
        """
        return """
CRITICAL HALLUCINATION PREVENTION RULES:

1. You are FORBIDDEN from inventing URLs, citations, conversation IDs, or references.

2. If you are unsure about any information, you MUST state "I cannot verify this information" 
   rather than guessing or fabricating.

3. Only use information from the provided context and data. Do NOT use your general knowledge 
   or training data to fill gaps.

4. For each claim you make, use the format: [Claim] - [Source from provided data]

5. If information is not in the provided data, state: "This information is not available 
   in the provided dataset"

6. NEVER fabricate:
   - Conversation IDs or Intercom URLs
   - Customer names or identifiers
   - Data points or statistics not in the source
   - Categories not in the provided taxonomy
   - Timestamps or date ranges not explicitly given

7. Use confidence levels for all outputs:
   - HIGH confidence: Information directly from provided data
   - MEDIUM confidence: Inferred from patterns in data
   - LOW confidence: Uncertain - explicitly state limitations
"""
    
    def calculate_confidence(self, result: Dict[str, Any], context: AgentContext) -> tuple[float, ConfidenceLevel]:
        """
        Calculate confidence score for agent output.
        
        Args:
            result: Agent's output data
            context: Input context
            
        Returns:
            Tuple of (confidence_score, confidence_level)
        """
        # Base confidence starts at 1.0
        confidence = 1.0
        
        # Deduct for uncertainty indicators
        result_str = str(result)
        if "cannot verify" in result_str.lower():
            confidence -= 0.2
        if "not available" in result_str.lower():
            confidence -= 0.1
        if "uncertain" in result_str.lower():
            confidence -= 0.15
        
        # Deduct for missing expected data
        if not result or len(result) == 0:
            confidence -= 0.5
        
        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))
        
        # Determine confidence level
        if confidence >= 0.8:
            level = ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        return confidence, level
    
    async def verify_output(self, output: Dict[str, Any], context: AgentContext) -> bool:
        """
        Implement Chain-of-Verification pattern.

        From research: Can improve accuracy by 23%.

        Args:
            output: Agent's output to verify
            context: Original context

        Returns:
            True if verification passes
        """
        # Subclasses can override with specific verification logic
        return True

    async def _call_ai_with_tools(self, messages: List[Dict], context: AgentContext) -> Any:
        """
        Call OpenAI API with tool definitions and return response.

        This method integrates with OpenAI's function calling API:
        - Retrieves tool definitions from registry
        - Calls OpenAI with tools parameter
        - Returns raw response (may contain tool_calls)

        Args:
            messages: List of message dictionaries (OpenAI format)
            context: AgentContext (for potential future use)

        Returns:
            OpenAI ChatCompletion response object with choices[0].message potentially containing tool_calls

        Raises:
            Exception: If OpenAI API call fails

        Note:
            - Currently OpenAI-only (Claude support can be added later)
            - Uses tool_choice="auto" to let model decide when to use tools
            - Response structure: response.choices[0].message.tool_calls = [{id, function: {name, arguments}}]
        """
        try:
            from openai import AsyncOpenAI
            from src.config.settings import settings

            # Create OpenAI client
            client = AsyncOpenAI(api_key=settings.openai_api_key)

            # Get tool definitions from registry
            tools = self.tool_registry.get_tool_definitions() if self.tool_registry else None

            # Call OpenAI API with tools
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",  # Let model decide when to use tools
                temperature=self.temperature
            )

            return response

        except Exception as e:
            self.logger.error(f"AI call with tools failed: {e}", exc_info=True)
            raise

    def get_tool_call_summary(self) -> Dict[str, Any]:
        """
        Get summary of tool calls made during execution (for audit trail).

        Returns:
            Dictionary containing:
            - total_tool_calls: Total number of tool calls made
            - successful_calls: Number of successful tool calls
            - failed_calls: Number of failed tool calls
            - tools_used: List of unique tool names used
            - total_execution_time_ms: Sum of all tool execution times
            - calls: Full list of tool call details

        Example:
            {
                "total_tool_calls": 3,
                "successful_calls": 2,
                "failed_calls": 1,
                "tools_used": ["lookup_admin_profile", "calculate_fcr"],
                "total_execution_time_ms": 1234.5,
                "calls": [...]
            }
        """
        successful_calls = sum(1 for call in self.tool_calls_made if call.get('success', False))
        failed_calls = sum(1 for call in self.tool_calls_made if not call.get('success', False))
        tools_used = list(set(call.get('tool_name') for call in self.tool_calls_made))
        total_execution_time_ms = sum(call.get('execution_time_ms', 0) for call in self.tool_calls_made)

        return {
            'total_tool_calls': len(self.tool_calls_made),
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'tools_used': tools_used,
            'total_execution_time_ms': total_execution_time_ms,
            'calls': self.tool_calls_made
        }

    def get_agent_specific_instructions(self) -> str:
        """
        Get agent-specific instructions.
        Override in subclasses for specialized behavior.
        """
        return ""
    
    def build_prompt(self, context: AgentContext) -> str:
        """
        Build complete prompt with hallucination prevention.
        
        Args:
            context: AgentContext with data
            
        Returns:
            Complete prompt string
        """
        base_prevention = self.get_hallucination_prevention_prompt()
        agent_instructions = self.get_agent_specific_instructions()
        
        return f"""
{base_prevention}

{agent_instructions}

Your task: {self.get_task_description(context)}

Provided data:
{self.format_context_data(context)}
"""
    
    @abstractmethod
    def get_task_description(self, context: AgentContext) -> str:
        """Get description of this agent's specific task"""
        pass
    
    @abstractmethod
    def format_context_data(self, context: AgentContext) -> str:
        """Format context data for inclusion in prompt"""
        pass

