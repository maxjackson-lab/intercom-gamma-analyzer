"""
Analysis Mode Configuration Helper

Provides centralized configuration for analysis modes and feature flags.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisMode(Enum):
    """Available analysis modes."""
    STANDARD = 'standard'
    MULTI_AGENT = 'multi-agent'
    AUTO = 'auto'


class AnalysisModeConfig:
    """
    Centralized configuration for analysis modes.
    
    Reads from config/analysis_modes.yaml and allows environment variable overrides.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize analysis mode configuration.
        
        Args:
            config_path: Path to analysis_modes.yaml (optional)
        """
        self.logger = logging.getLogger(__name__)
        
        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "analysis_modes.yaml"
        
        self.config_path = config_path
        self.config = self._load_config()
        
        self.logger.info(f"Loaded analysis mode config from {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config or {}
            else:
                self.logger.warning(f"Config file not found: {self.config_path}, using defaults")
                return self._get_default_config()
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'default_mode': 'standard',
            'auto_thresholds': {
                'multi_agent_min_conversations': 100,
                'force_multi_agent_for_types': ['topic-based', 'synthesis']
            },
            'features': {
                'enable_topic_based': True,
                'enable_synthesis': True,
                'enable_trends': True,
                'enable_gamma': True,
                'enable_canny': True,
                'enable_historical': True
            },
            'multi_agent': {
                'max_parallel_topics': 10,
                'enable_llm_topic_discovery': True,
                'enable_topic_metrics': True
            }
        }
    
    def get_analysis_mode(
        self,
        force_mode: Optional[str] = None,
        analysis_type: Optional[str] = None,
        conversation_count: Optional[int] = None
    ) -> AnalysisMode:
        """
        Determine which analysis mode to use.
        
        Priority order:
        1. CLI flags (--force-multi-agent, --force-standard)
        2. Environment variable (ANALYSIS_MODE)
        3. Auto-selection based on thresholds
        4. Default from config
        
        Args:
            force_mode: Forced mode from CLI ('multi-agent', 'standard', None)
            analysis_type: Type of analysis being performed
            conversation_count: Number of conversations to analyze
        
        Returns:
            AnalysisMode enum value
        """
        # Priority 1: CLI force flags
        if force_mode:
            if force_mode in ['multi-agent', 'multi_agent']:
                self.logger.info("Using multi-agent mode (forced via CLI)")
                return AnalysisMode.MULTI_AGENT
            elif force_mode == 'standard':
                self.logger.info("Using standard mode (forced via CLI)")
                return AnalysisMode.STANDARD
        
        # Priority 2: Environment variable
        env_mode = os.getenv('ANALYSIS_MODE')
        if env_mode:
            if env_mode.lower() in ['multi-agent', 'multi_agent']:
                self.logger.info("Using multi-agent mode (from ANALYSIS_MODE env var)")
                return AnalysisMode.MULTI_AGENT
            elif env_mode.lower() == 'standard':
                self.logger.info("Using standard mode (from ANALYSIS_MODE env var)")
                return AnalysisMode.STANDARD
        
        # Priority 3: Auto-selection based on config
        default_mode = self.config.get('default_mode', 'standard')
        
        if default_mode == 'auto':
            # Check if analysis type forces multi-agent
            force_types = self.config.get('auto_thresholds', {}).get('force_multi_agent_for_types', [])
            if analysis_type and analysis_type in force_types:
                self.logger.info(f"Using multi-agent mode (analysis type '{analysis_type}' requires it)")
                return AnalysisMode.MULTI_AGENT
            
            # Check conversation count threshold
            min_conversations = self.config.get('auto_thresholds', {}).get('multi_agent_min_conversations', 100)
            if conversation_count and conversation_count >= min_conversations:
                self.logger.info(f"Using multi-agent mode (conversation count {conversation_count} >= threshold {min_conversations})")
                return AnalysisMode.MULTI_AGENT
            else:
                self.logger.info(f"Using standard mode (conversation count {conversation_count} < threshold {min_conversations})")
                return AnalysisMode.STANDARD
        
        # Priority 4: Default from config
        if default_mode in ['multi-agent', 'multi_agent']:
            self.logger.info("Using multi-agent mode (default from config)")
            return AnalysisMode.MULTI_AGENT
        else:
            self.logger.info("Using standard mode (default from config)")
            return AnalysisMode.STANDARD
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled.
        
        Args:
            feature_name: Name of the feature (e.g., 'enable_gamma')
        
        Returns:
            True if feature is enabled
        """
        features = self.config.get('features', {})
        return features.get(feature_name, True)
    
    def get_multi_agent_setting(self, setting_name: str) -> Any:
        """
        Get a multi-agent workflow setting.
        
        Args:
            setting_name: Name of the setting (e.g., 'max_parallel_topics')
        
        Returns:
            Setting value
        """
        multi_agent_config = self.config.get('multi_agent', {})
        return multi_agent_config.get(setting_name)


# Global singleton instance
_config_instance: Optional[AnalysisModeConfig] = None


def get_analysis_mode_config() -> AnalysisModeConfig:
    """
    Get the global analysis mode configuration instance.
    
    Returns:
        AnalysisModeConfig singleton
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = AnalysisModeConfig()
    return _config_instance


def get_analysis_mode(
    force_mode: Optional[str] = None,
    analysis_type: Optional[str] = None,
    conversation_count: Optional[int] = None
) -> AnalysisMode:
    """
    Convenience function to get analysis mode.
    
    Args:
        force_mode: Forced mode from CLI ('multi-agent', 'standard', None)
        analysis_type: Type of analysis being performed
        conversation_count: Number of conversations to analyze
    
    Returns:
        AnalysisMode enum value
    """
    config = get_analysis_mode_config()
    return config.get_analysis_mode(force_mode, analysis_type, conversation_count)

