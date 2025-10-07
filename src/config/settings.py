"""
Pydantic settings configuration for the Intercom Gamma Analyzer.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator
from pydantic_settings import BaseSettings as PydanticBaseSettings
import os


class Settings(PydanticBaseSettings):
    """Application settings with environment variable support."""
    
    # API Keys
    intercom_access_token: str = Field(..., env="INTERCOM_ACCESS_TOKEN")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    gamma_api_key: Optional[str] = Field(None, env="GAMMA_API_KEY")
    
    # Intercom API Settings
    intercom_base_url: str = Field("https://api.intercom.io", env="INTERCOM_BASE_URL")
    intercom_api_version: str = Field("2.14", env="INTERCOM_API_VERSION")
    intercom_rate_limit_buffer: int = Field(10, env="INTERCOM_RATE_LIMIT_BUFFER")
    intercom_timeout: int = Field(30, env="INTERCOM_TIMEOUT")
    intercom_max_retries: int = Field(3, env="INTERCOM_MAX_RETRIES")
    
    # OpenAI Settings
    openai_model: str = Field("gpt-4o", env="OPENAI_MODEL")
    openai_temperature: float = Field(0.1, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(4000, env="OPENAI_MAX_TOKENS")
    
    # Analysis Settings
    default_analysis_days: int = Field(30, env="DEFAULT_ANALYSIS_DAYS")
    max_conversations_per_request: int = Field(150, env="MAX_CONVERSATIONS_PER_REQUEST")
    min_conversations_for_analysis: int = Field(10, env="MIN_CONVERSATIONS_FOR_ANALYSIS")
    
    # Voice of Customer Settings
    default_tier1_countries: List[str] = Field(
        default=[
            "United States", "Brazil", "Canada", "Mexico", "France", 
            "United Kingdom", "Germany", "Spain", "South Korea", 
            "Japan", "Australia"
        ],
        env="DEFAULT_TIER1_COUNTRIES"
    )
    
    # Text Analysis Settings
    yake_language: str = Field("en", env="YAKE_LANGUAGE")
    yake_max_ngram_size: int = Field(3, env="YAKE_MAX_NGRAM_SIZE")
    yake_deduplication_threshold: float = Field(0.9, env="YAKE_DEDUPLICATION_THRESHOLD")
    yake_num_keywords: int = Field(20, env="YAKE_NUM_KEYWORDS")
    yake_min_keyword_length: int = Field(3, env="YAKE_MIN_KEYWORD_LENGTH")
    
    # Output Settings
    output_directory: str = Field("outputs", env="OUTPUT_DIRECTORY")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("intercom_analysis.log", env="LOG_FILE")
    
    # Gamma Settings
    gamma_base_url: str = Field("https://gamma.app/api", env="GAMMA_BASE_URL")
    gamma_default_template: str = Field("presentation", env="GAMMA_DEFAULT_TEMPLATE")
    
    @validator('default_tier1_countries', pre=True)
    def parse_tier1_countries(cls, v):
        if isinstance(v, str):
            return [country.strip() for country in v.split(',')]
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

