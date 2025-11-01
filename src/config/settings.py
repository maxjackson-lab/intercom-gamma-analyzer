"""
Pydantic settings configuration for the Intercom Gamma Analyzer.
"""

from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Keys
    intercom_access_token: str = Field(..., env="INTERCOM_ACCESS_TOKEN")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    gamma_api_key: Optional[str] = Field(None, env="GAMMA_API_KEY")
    intercom_workspace_id: Optional[str] = Field(None, env="INTERCOM_WORKSPACE_ID")
    
    # Feature Flags - Control new features
    use_dual_fin_metrics: bool = Field(False, env="USE_DUAL_FIN_METRICS")  # Set to True to show Intercom-compatible + Quality metrics
    
    # Intercom API Settings
    intercom_base_url: str = Field("https://api.intercom.io", env="INTERCOM_BASE_URL")
    intercom_api_version: str = Field("2.14", env="INTERCOM_API_VERSION")
    intercom_rate_limit_buffer: int = Field(10, env="INTERCOM_RATE_LIMIT_BUFFER")
    intercom_timeout: int = Field(300, env="INTERCOM_TIMEOUT")  # 5 minutes per request (SDK default is 60s)
    intercom_max_retries: int = Field(3, env="INTERCOM_MAX_RETRIES")
    intercom_concurrency: int = Field(5, env="INTERCOM_CONCURRENCY")  # Max concurrent enrichment requests
    intercom_request_delay_ms: int = Field(200, env="INTERCOM_REQUEST_DELAY_MS")  # Delay between API requests
    
    # OpenAI Settings
    openai_model: str = Field("gpt-4o", env="OPENAI_MODEL")
    openai_temperature: float = Field(0.1, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(4000, env="OPENAI_MAX_TOKENS")
    
    # Anthropic/Claude Settings
    anthropic_model: str = Field("claude-3-opus-20240229", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(4000, env="ANTHROPIC_MAX_TOKENS")
    
    # Canny API Settings
    canny_api_key: Optional[str] = Field(None, env="CANNY_API_KEY")
    canny_base_url: str = Field("https://canny.io/api/v1", env="CANNY_BASE_URL")
    canny_timeout: int = Field(30, env="CANNY_TIMEOUT")
    canny_max_retries: int = Field(3, env="CANNY_MAX_RETRIES")
    
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
    voc_default_ai_model: str = Field("openai", env="VOC_DEFAULT_AI_MODEL")  # "openai" or "claude"
    voc_enable_ai_fallback: bool = Field(True, env="VOC_ENABLE_AI_FALLBACK")
    voc_historical_weeks: int = Field(26, env="VOC_HISTORICAL_WEEKS")  # 6 months
    voc_top_categories_count: int = Field(10, env="VOC_TOP_CATEGORIES_COUNT")
    
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
    gamma_timeout: int = Field(60, env="GAMMA_TIMEOUT")

    # Data Export & PII Settings
    redact_sensitive_outputs: bool = Field(True, env="REDACT_SENSITIVE_OUTPUTS")
    export_raw_data: bool = Field(False, env="EXPORT_RAW_DATA")

    # Agent Checkpoint Settings
    max_checkpoints: int = Field(100, env="MAX_CHECKPOINTS")

    @field_validator('default_tier1_countries', mode='before')
    @classmethod
    def parse_tier1_countries(cls, v):
        if isinstance(v, str):
            return [country.strip() for country in v.split(',')]
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()

