"""
Base agent class with integrated hallucination prevention.

Implements the core patterns from Claude's research:
- "I Don't Know" permission
- "According To" grounding
- Confidence scoring
- Chain-of-Verification
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import logging

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
    """
    
    def __init__(self, name: str, model: str = "gpt-4o", temperature: float = 0.3):
        self.name = name
        self.model = model
        self.temperature = temperature
        self.logger = logging.getLogger(f"agents.{name}")
    
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

