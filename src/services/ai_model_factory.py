"""
AI Model Factory for managing OpenAI and Claude clients.
"""

from enum import Enum
from typing import Union, Dict, Any
import logging

from src.services.openai_client import OpenAIClient
from src.services.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class AIModel(Enum):
    """Available AI models for analysis."""
    OPENAI_GPT4 = "openai"
    ANTHROPIC_CLAUDE = "claude"


class AIModelFactory:
    """Factory for creating AI clients."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._openai_client = None
        self._claude_client = None
        
        self.logger.info("AIModelFactory initialized")
    
    def get_client(self, model: AIModel) -> Union[OpenAIClient, ClaudeClient]:
        """
        Get AI client for specified model.
        
        Args:
            model: Which AI model to use
        
        Returns:
            Appropriate AI client (OpenAI or Claude)
        
        Raises:
            ValueError: If model is not supported
        """
        self.logger.info(f"Getting AI client for model: {model.value}")
        
        if model == AIModel.OPENAI_GPT4:
            if not self._openai_client:
                self._openai_client = OpenAIClient()
            return self._openai_client
        
        elif model == AIModel.ANTHROPIC_CLAUDE:
            if not self._claude_client:
                self._claude_client = ClaudeClient()
            return self._claude_client
        
        else:
            raise ValueError(f"Unsupported AI model: {model}")
    
    async def analyze_sentiment(
        self, 
        text: str, 
        language: str = None,
        model: AIModel = AIModel.OPENAI_GPT4,
        fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze sentiment with specified model.
        
        Args:
            text: Text to analyze
            language: Language hint (optional)
            model: Which AI model to use
            fallback: If True, try other model if primary fails
        
        Returns:
            Sentiment analysis with model attribution
        
        Raises:
            Exception: If both primary and fallback models fail
        """
        self.logger.info(f"Analyzing sentiment with {model.value}")
        
        try:
            client = self.get_client(model)
            result = await client.analyze_sentiment_multilingual(text, language)
            result['model_used'] = model.value
            return result
            
        except Exception as e:
            self.logger.error(f"Primary model ({model.value}) failed: {e}")
            
            if fallback:
                # Try the other model
                fallback_model = (AIModel.ANTHROPIC_CLAUDE if model == AIModel.OPENAI_GPT4 
                                 else AIModel.OPENAI_GPT4)
                
                self.logger.warning(f"Falling back to {fallback_model.value}")
                
                try:
                    client = self.get_client(fallback_model)
                    result = await client.analyze_sentiment_multilingual(text, language)
                    result['model_used'] = fallback_model.value
                    result['fallback'] = True
                    return result
                except Exception as fallback_error:
                    self.logger.error(f"Fallback model also failed: {fallback_error}")
                    raise
            raise
    
    async def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to all available AI models.
        
        Returns:
            Dictionary with model names and connection status
        """
        self.logger.info("Testing connections to all AI models")
        
        results = {}
        
        # Test OpenAI
        try:
            openai_client = self.get_client(AIModel.OPENAI_GPT4)
            results['openai'] = await openai_client.test_connection()
        except Exception as e:
            self.logger.error(f"OpenAI connection test failed: {e}")
            results['openai'] = False
        
        # Test Claude
        try:
            claude_client = self.get_client(AIModel.ANTHROPIC_CLAUDE)
            results['claude'] = await claude_client.test_connection()
        except Exception as e:
            self.logger.error(f"Claude connection test failed: {e}")
            results['claude'] = False
        
        self.logger.info(f"Connection test results: {results}")
        return results
    
    async def analyze_with_fallback(
        self,
        task: str,
        inputs: Dict[str, Any],
        model: AIModel = AIModel.OPENAI_GPT4,
        method_name: str = "generate_analysis"
    ) -> Dict[str, Any]:
        """
        Execute any analysis task with automatic fallback to alternative model.
        
        This is a general-purpose fallback wrapper that can be used by agents
        to get resilience without changing their business logic.
        
        Args:
            task: Description of the analysis task (for logging)
            inputs: Dictionary of inputs to pass to the client method
            model: Primary AI model to use
            method_name: Name of the client method to call (default: generate_analysis)
        
        Returns:
            Analysis result with model attribution and fallback flag
        
        Raises:
            Exception: If both primary and fallback models fail
        
        Example:
            result = await ai_factory.analyze_with_fallback(
                task="sentiment analysis",
                inputs={"prompt": "Analyze this: ..."},
                model=AIModel.OPENAI_GPT4
            )
        """
        self.logger.info(f"Executing task '{task}' with {model.value} (fallback enabled)")
        
        try:
            # Try primary model
            client = self.get_client(model)
            method = getattr(client, method_name)
            
            # Handle both dict and direct prompt inputs
            if isinstance(inputs, dict) and 'prompt' in inputs:
                result = await method(inputs['prompt'])
            elif isinstance(inputs, str):
                result = await method(inputs)
            else:
                result = await method(**inputs)
            
            # Ensure result is a dict
            if isinstance(result, str):
                result = {'response': result}
            
            result['model_used'] = model.value
            result['fallback_used'] = False
            
            return result
            
        except Exception as e:
            self.logger.error(f"Primary model ({model.value}) failed for task '{task}': {e}")
            
            # Try fallback model
            fallback_model = (AIModel.ANTHROPIC_CLAUDE if model == AIModel.OPENAI_GPT4 
                             else AIModel.OPENAI_GPT4)
            
            self.logger.warning(f"Falling back to {fallback_model.value} for task '{task}'")
            
            try:
                client = self.get_client(fallback_model)
                method = getattr(client, method_name)
                
                # Handle both dict and direct prompt inputs
                if isinstance(inputs, dict) and 'prompt' in inputs:
                    result = await method(inputs['prompt'])
                elif isinstance(inputs, str):
                    result = await method(inputs)
                else:
                    result = await method(**inputs)
                
                # Ensure result is a dict
                if isinstance(result, str):
                    result = {'response': result}
                
                result['model_used'] = fallback_model.value
                result['fallback_used'] = True
                result['primary_model_error'] = str(e)
                
                self.logger.info(f"Fallback successful for task '{task}' using {fallback_model.value}")
                
                return result
                
            except Exception as fallback_error:
                self.logger.error(f"Fallback model ({fallback_model.value}) also failed for task '{task}': {fallback_error}")
                raise Exception(
                    f"Both {model.value} and {fallback_model.value} failed. "
                    f"Primary error: {e}. Fallback error: {fallback_error}"
                )