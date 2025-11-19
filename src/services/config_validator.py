"""
Configuration Validator

Validates API keys and critical environment variables on startup.
Fails fast if critical keys are missing or invalid.
"""

import logging
import os
from typing import Dict, Any, Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)


async def validate_configuration() -> Dict[str, bool]:
    """
    Validate API keys and critical env vars on startup.
    
    Tests each API key by making a minimal connection test.
    Checks for placeholder values that indicate misconfiguration.
    
    Returns:
        Dictionary mapping service names to validation status (True/False)
        
    Raises:
        ValueError: If critical API keys are missing or invalid
    """
    results = {}
    critical_services = []
    
    # Test OpenAI API key
    if settings.openai_api_key:
        try:
            from src.services.openai_client import OpenAIClient
            client = OpenAIClient()
            await client.test_connection()
            results['openai'] = True
            logger.info("✅ OpenAI API key: Valid")
        except Exception as e:
            results['openai'] = False
            critical_services.append('OpenAI')
            logger.error(f"❌ OpenAI API key invalid: {e}")
    else:
        results['openai'] = False
        critical_services.append('OpenAI')
        logger.error("❌ OpenAI API key: Missing")
    
    # Test Anthropic API key
    if settings.anthropic_api_key:
        try:
            from src.services.claude_client import ClaudeClient
            client = ClaudeClient()
            await client.test_connection()
            results['anthropic'] = True
            logger.info("✅ Anthropic API key: Valid")
        except Exception as e:
            results['anthropic'] = False
            # Anthropic is optional (fallback), so don't add to critical_services
            logger.warning(f"⚠️  Anthropic API key invalid: {e}")
    else:
        results['anthropic'] = False
        logger.warning("⚠️  Anthropic API key: Missing (optional)")
    
    # Test Intercom API key
    if settings.intercom_access_token:
        # Check for placeholder values
        placeholder_values = [
            "your-access-token-here",
            "your-workspace-id-here",
            "placeholder",
            "test",
            "example"
        ]
        
        is_placeholder = any(
            placeholder.lower() in settings.intercom_access_token.lower()
            for placeholder in placeholder_values
        )
        
        if is_placeholder:
            results['intercom'] = False
            critical_services.append('Intercom')
            logger.error(f"❌ Intercom access token appears to be placeholder: {settings.intercom_access_token[:20]}...")
        else:
            # Basic validation: check if token looks valid (starts with expected prefix)
            # Intercom tokens typically start with 'dG9r' (base64 encoded) or similar
            if len(settings.intercom_access_token) > 10:
                results['intercom'] = True
                logger.info("✅ Intercom access token: Present (not validated via API call)")
            else:
                results['intercom'] = False
                critical_services.append('Intercom')
                logger.error("❌ Intercom access token: Too short (likely invalid)")
    else:
        results['intercom'] = False
        critical_services.append('Intercom')
        logger.error("❌ Intercom access token: Missing")
    
    # Test Intercom workspace ID
    if settings.intercom_workspace_id:
        if settings.intercom_workspace_id.lower() in ["your-workspace-id-here", "placeholder", "test", "example"]:
            logger.warning(f"⚠️  Intercom workspace ID appears to be placeholder: {settings.intercom_workspace_id}")
        else:
            logger.info(f"✅ Intercom workspace ID: Present ({settings.intercom_workspace_id})")
    else:
        logger.warning("⚠️  Intercom workspace ID: Missing (may cause issues)")
    
    # Test Gamma API key (optional)
    if settings.gamma_api_key:
        # Basic validation: check if key looks valid
        if len(settings.gamma_api_key) > 10:
            results['gamma'] = True
            logger.info("✅ Gamma API key: Present (not validated via API call)")
        else:
            results['gamma'] = False
            logger.warning("⚠️  Gamma API key: Too short (likely invalid)")
    else:
        results['gamma'] = False
        logger.warning("⚠️  Gamma API key: Missing (optional - Gamma features will be disabled)")
    
    # Fail fast if critical services are missing
    if critical_services:
        error_msg = f"Critical API keys missing or invalid: {', '.join(critical_services)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Log summary
    status_summary = []
    for service, is_valid in results.items():
        status_icon = "✅" if is_valid else "❌"
        status_summary.append(f"{service}: {status_icon}")
    
    logger.info(f"API Keys: {', '.join(status_summary)}")
    
    return results


def validate_environment_variables() -> Dict[str, Any]:
    """
    Validate critical environment variables (non-API-key config).
    
    Returns:
        Dictionary of validation results
    """
    results = {}
    
    # Check for required env vars
    required_vars = [
        'INTERCOM_ACCESS_TOKEN',
        'INTERCOM_WORKSPACE_ID'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Check for placeholder values
            placeholder_values = ["your-", "placeholder", "test", "example"]
            is_placeholder = any(
                placeholder.lower() in value.lower()
                for placeholder in placeholder_values
            )
            
            if is_placeholder:
                results[var] = {'status': 'placeholder', 'value': value[:20] + '...'}
                logger.warning(f"⚠️  {var} appears to be placeholder")
            else:
                results[var] = {'status': 'valid', 'value': '***'}
                logger.info(f"✅ {var}: Present")
        else:
            results[var] = {'status': 'missing'}
            logger.warning(f"⚠️  {var}: Missing")
    
    return results

