"""
Helper utility to get AI client based on configuration.
Makes it easy for agents to use the configured AI model.
"""

import logging
import asyncio
from typing import Union
from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.openai_client import OpenAIClient
from src.services.claude_client import ClaudeClient
from src.config.modes import get_analysis_mode_config
from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_ai_client() -> Union[OpenAIClient, ClaudeClient]:
    """
    Get the configured AI client (OpenAI or Claude).
    
    Reads from:
    1. AI_MODEL environment variable
    2. config/analysis_modes.yaml ai_model.default_model
    3. Defaults to OpenAI
    
    Returns:
        Configured AI client instance
    """
    config = get_analysis_mode_config()
    model_name = config.get_default_ai_model()
    
    factory = AIModelFactory()
    
    if model_name == 'claude':
        model_type = AIModel.ANTHROPIC_CLAUDE
    else:
        model_type = AIModel.OPENAI_GPT4
    
    logger.info(f"Getting AI client: {model_name}")
    return factory.get_client(model_type)


def get_ai_factory() -> AIModelFactory:
    """
    Get the AI model factory for advanced use cases (fallback, etc).
    
    Returns:
        AIModelFactory instance
    """
    return AIModelFactory()


def get_recommended_semaphore(client: Union[OpenAIClient, ClaudeClient]) -> asyncio.Semaphore:
    """
    Get recommended semaphore size based on the AI client type.
    
    Provider-specific limits:
    - OpenAI: Default 10 concurrent (configurable via OPENAI_CONCURRENCY)
    - Anthropic: Default 2 concurrent (configurable via ANTHROPIC_CONCURRENCY)
      Tier 1 limit: 50 RPM → ~0.8 req/s → 2 concurrent max
    
    Args:
        client: The AI client instance (OpenAIClient or ClaudeClient)
    
    Returns:
        asyncio.Semaphore with provider-appropriate size
    """
    from src.services.claude_client import ClaudeClient
    
    if isinstance(client, ClaudeClient):
        concurrency = settings.anthropic_concurrency
    else:
        concurrency = settings.openai_concurrency
    
    logger.debug(f"Recommended semaphore size for {type(client).__name__}: {concurrency}")
    return asyncio.Semaphore(concurrency)

