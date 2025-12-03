"""
Centralized model profile definitions to keep OpenAI/Anthropic usage consistent.

OpenAI production guidance (https://platform.openai.com/docs/guides/production-best-practices)
emphasizes predictable configuration, so we map every run to a single provider-specific
profile and expose helpers for agents to select the appropriate model per scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from src.config.modes import get_analysis_mode_config


ALLOWED_SCOPES = {"quick", "intensive"}
DEFAULT_SCOPE = "intensive"


@dataclass(frozen=True)
class ModelProfile:
    """Represents the model names that should be used for a provider."""

    provider: str  # "openai" or "claude"
    scopes: Dict[str, str]


MODEL_PROFILES: Dict[str, ModelProfile] = {
    "openai": ModelProfile(
        provider="openai",
        scopes={
            "quick": "gpt-4o-mini",  # fast/cheap per OpenAI production guidance
            "intensive": "gpt-4o",  # high-accuracy writer for executive outputs
        },
    ),
    "claude": ModelProfile(
        provider="claude",
        scopes={
            "quick": "claude-haiku-4-5-20251001",  # Anthropic Haiku 4.5
            "intensive": "claude-sonnet-4-5-20250929",  # Anthropic Sonnet 4.5
        },
    ),
}


def _normalize_provider(provider: Optional[str]) -> str:
    key = (provider or "").strip().lower()
    if key in MODEL_PROFILES:
        return key
    return "openai"


def _normalize_scope(scope: Optional[str]) -> str:
    normalized = (scope or DEFAULT_SCOPE).strip().lower()
    if normalized not in ALLOWED_SCOPES:
        raise ValueError(
            f"Unsupported model scope '{scope}'. Allowed scopes: {sorted(ALLOWED_SCOPES)}"
        )
    return normalized


def get_model_profile(provider: Optional[str] = None) -> ModelProfile:
    """
    Return the active model profile for the requested provider (or global default).

    Providers are constrained to 'openai' or 'claude' so we never mix vendors
    within a single analysis run.
    """
    provider_key = _normalize_provider(provider or get_analysis_mode_config().get_default_ai_model())
    return MODEL_PROFILES[provider_key]


def select_model_for_scope(scope: Optional[str] = None, provider: Optional[str] = None) -> str:
    """
    Select the model name for a given scope ('quick' or 'intensive') from the active profile.
    """
    normalized_scope = _normalize_scope(scope)
    profile = get_model_profile(provider)
    try:
        return profile.scopes[normalized_scope]
    except KeyError as exc:
        raise ValueError(
            f"Scope '{normalized_scope}' missing in profile '{profile.provider}'"
        ) from exc

