"""
Async helper functions for Gamma presentation generation.

These helpers allow web routes or orchestrators to await Gamma generation
without invoking ``asyncio.run`` directly inside synchronous contexts.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from src.services.gamma_generator import GammaGenerator


async def generate_gamma_presentation_async(
    *,
    gamma_generator: GammaGenerator,
    analysis_results: Dict[str, Any],
    style: str,
    export_format: Optional[str],
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Generate a single Gamma presentation.

    Args:
        gamma_generator: Shared GammaGenerator instance.
        analysis_results: Parsed analysis JSON payload.
        style: Presentation style key.
        export_format: Optional export format (pdf, pptx, etc.).
        output_dir: Directory where attachments should be saved.
    """
    return await gamma_generator.generate_from_analysis(
        analysis_results=analysis_results,
        style=style,
        export_format=export_format,
        output_dir=output_dir,
    )


async def generate_all_gamma_presentations_async(
    *,
    gamma_generator: GammaGenerator,
    analysis_results: Dict[str, Any],
    export_format: Optional[str],
    output_dir: Path,
) -> Dict[str, Dict[str, Any]]:
    """
    Generate all available Gamma presentation styles.

    Args:
        gamma_generator: Shared GammaGenerator instance.
        analysis_results: Parsed analysis JSON payload.
        export_format: Optional export format (pdf, pptx, etc.).
        output_dir: Directory where attachments should be saved.
    """
    return await gamma_generator.generate_all_styles(
        analysis_results=analysis_results,
        export_format=export_format,
        output_dir=output_dir,
    )


