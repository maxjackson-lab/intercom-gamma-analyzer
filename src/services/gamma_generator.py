"""
Gamma Generator Service for Intercom Analysis Tool.
Generates professional Gamma presentations from analysis results using real Gamma API.
"""

import time
import structlog
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import json

from src.services.gamma_client import GammaClient, GammaAPIError
from src.services.presentation_builder import PresentationBuilder
from src.config.gamma_prompts import GammaPrompts
from src.utils.time_utils import detect_period_type
from src.utils.agent_output_display import get_display
from src.config.modes import get_analysis_mode_config

logger = structlog.get_logger()


class GammaGenerator:
    """
    Service for generating professional Gamma presentations from analysis results.
    
    Features:
    - Real Gamma API integration with v1.0 endpoints
    - Multiple presentation styles (executive, detailed, training)
    - Customer quote integration with Intercom links
    - Automated polling and error handling
    - Export options (PDF, PPTX)
    - Automatic theme name→ID resolution
    """
    
    def __init__(self, gamma_client: Optional[GammaClient] = None, presentation_builder: Optional[PresentationBuilder] = None):
        """
        Initialize Gamma generator.
        
        Args:
            gamma_client: Gamma API client (optional)
            presentation_builder: Presentation content builder (optional)
        """
        self.client = gamma_client or GammaClient()
        self.builder = presentation_builder or PresentationBuilder()
        self.prompts = GammaPrompts()
        self.logger = structlog.get_logger()
        
        self.logger.info(
            "gamma_generator_initialized",
            has_client=bool(self.client),
            has_builder=bool(self.builder)
        )
    
    async def generate_from_analysis(
        self,
        analysis_results: Dict,
        style: str = "executive",
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate a Gamma presentation from analysis results.
        
        Args:
            analysis_results: Analysis results dictionary
            style: Presentation style ("executive", "detailed", "training")
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results
            
        Returns:
            Dictionary with gamma_url, generation_id, and metadata
            
        Raises:
            GammaAPIError: If generation fails
        """
        self.logger.info(
            "gamma_generation_start",
            style=style,
            export_format=export_format,
            has_conversations=bool(analysis_results.get('conversations'))
        )
        
        start_time = time.time()
        
        try:
            # Detect period type from date range
            start_date = analysis_results.get('start_date')
            end_date = analysis_results.get('end_date')
            period_type, period_label = detect_period_type(start_date, end_date) if start_date and end_date else ('custom', 'Custom')
            
            # Build narrative content
            input_text = self.builder.build_narrative_content(analysis_results, style, period_type)
            
            # Validate input before sending to Gamma
            validation_errors = self._validate_gamma_input(input_text, analysis_results)
            if validation_errors:
                self.logger.error(f"Gamma input validation failed: {validation_errors}")
                raise ValueError(f"Gamma input validation failed: {'; '.join(validation_errors)}")
            
            # Get style-specific parameters
            num_cards = self.prompts.get_slide_count_for_style(style)
            additional_instructions = self.prompts.get_additional_instructions_for_style(style)
            
            # Display Gamma API call preview if enabled (with error handling)
            config = get_analysis_mode_config()
            enable_display = config.get_visibility_setting('enable_agent_output_display', True)
            show_full_text = config.get_visibility_setting('show_full_gamma_input', False)
            
            if enable_display:
                try:
                    display = get_display()
                    display.display_gamma_api_call(
                        input_text=input_text,
                        parameters={
                            'format': 'presentation',
                            'num_cards': num_cards,
                            'text_mode': 'generate',
                            'card_split': 'auto',
                            'theme_name': 'stockholm',
                            'export_format': export_format,
                            'additional_instructions': additional_instructions[:100] + '...' if additional_instructions and len(additional_instructions) > 100 else additional_instructions
                        },
                        show_full_text=show_full_text
                    )
                except Exception as e:
                    logger.warning(f"Failed to display Gamma API call preview: {e}")
            
            # Generate presentation
            generation_id = await self.client.generate_presentation(
                input_text=input_text,
                format="presentation",
                num_cards=num_cards,
                text_mode="generate",
                export_as=export_format,
                additional_instructions=additional_instructions
            )
            
            # Poll for completion
            result = await self.client.poll_generation(generation_id)
            
            elapsed = time.time() - start_time
            
            # Prepare response
            response = {
                'gamma_url': result.get('gammaUrl'),
                'generation_id': generation_id,
                'export_url': result.get('exportUrl'),
                'credits_used': result.get('credits', {}).get('deducted', 0),
                'generation_time_seconds': elapsed,
                'style': style,
                'export_format': export_format,
                'slide_count': num_cards,
                'period_type': period_type,
                'period_label': period_label
            }
            
            # Generate markdown summary (non-blocking)
            try:
                from src.services.google_docs_exporter import GoogleDocsExporter
                from pathlib import Path
                
                # Check if we should display markdown preview
                try:
                    config = get_analysis_mode_config()
                    show_markdown_preview = config.get_visibility_setting('show_markdown_preview', True)
                    markdown_max_lines = config.get_visibility_setting('markdown_preview_max_lines', 50)
                except Exception as e:
                    logger.warning(f"Failed to read markdown preview config: {e}")
                    show_markdown_preview = True
                    markdown_max_lines = 50
                
                docs_exporter = GoogleDocsExporter()
                markdown_output_dir = output_dir if output_dir else Path("outputs")
                markdown_output_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                markdown_filename = f"analysis_{period_type}_{style}_{timestamp}.md"
                markdown_path = markdown_output_dir / markdown_filename
                
                docs_exporter.export_to_markdown(
                    analysis_results=analysis_results,
                    output_path=markdown_path,
                    style=style
                )
                
                # Read preview
                with open(markdown_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                    markdown_preview = markdown_content[:500] if len(markdown_content) > 500 else markdown_content
                
                # Display preview if enabled
                if show_markdown_preview:
                    try:
                        display = get_display()
                        display.display_markdown_preview(
                            markdown_content,
                            title=f"Markdown Summary - {style.title()}",
                            max_lines=markdown_max_lines
                        )
                    except Exception as e:
                        logger.warning(f"Failed to display markdown preview: {e}")
                
                # Add to response
                response['markdown_summary_path'] = str(markdown_path)
                response['markdown_preview'] = markdown_preview
                response['markdown_size_bytes'] = len(markdown_content)
                
                self.logger.info(
                    "markdown_summary_generated",
                    markdown_path=str(markdown_path),
                    size_bytes=len(markdown_content)
                )
                
            except Exception as e:
                self.logger.warning(
                    "markdown_summary_generation_failed",
                    error=str(e),
                    exc_info=True
                )
                # Don't fail the entire Gamma generation for markdown issues
                response['markdown_summary_path'] = None
            
            # Save metadata if output directory provided
            if output_dir:
                await self._save_generation_metadata(response, analysis_results, output_dir)
            
            self.logger.info(
                "gamma_generation_complete",
                generation_id=generation_id,
                gamma_url=result.get('gammaUrl'),
                credits_used=result.get('credits', {}).get('deducted', 0),
                total_time_seconds=elapsed
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "gamma_generation_failed",
                style=style,
                error=str(e),
                elapsed_seconds=time.time() - start_time,
                exc_info=True
            )
            raise
    
    async def generate_from_markdown(
        self,
        input_text: str,
        title: Optional[str] = None,
        num_cards: int = 10,
        theme_name: Optional[str] = None,
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate a Gamma presentation from markdown text, preserving formatting.

        This method bypasses category_results validation and uses:
        - textMode="preserve" to keep markdown formatting
        - cardSplit="inputTextBreaks" to respect --- breaks

        Ideal for topic-based Hilary format output.

        Args:
            input_text: Markdown text (1-400,000 characters, v1.0 token limit: ~100k tokens)
            title: Optional presentation title
            num_cards: Number of slides (default 10)
            theme_name: Gamma theme name (e.g., "Night Sky") - automatically resolved to themeId
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results

        Returns:
            Dictionary with gamma_url, generation_id, and metadata

        Raises:
            GammaAPIError: If generation fails
        """
        self.logger.info(
            "gamma_markdown_generation_start",
            input_length=len(input_text),
            num_cards=num_cards,
            theme=theme_name,
            export_format=export_format
        )

        start_time = time.time()

        try:
            # Validate input text length (v1.0: ~100k tokens ≈ 400k chars)
            if len(input_text) < 1 or len(input_text) > 400000:
                raise ValueError(
                    f"Input text must be 1-400,000 characters (v1.0 token limit: ~100k tokens), "
                    f"got {len(input_text)}"
                )

            # Validate Hilary markdown format
            hilary_validation_errors = self._validate_hilary_markdown(input_text)
            if hilary_validation_errors:
                self.logger.error(f"Hilary markdown validation failed: {hilary_validation_errors}")
                raise ValueError(f"Hilary markdown validation failed: {'; '.join(hilary_validation_errors)}")
            
            # Add title if provided
            if title and not input_text.startswith(f"# {title}"):
                input_text = f"# {title}\n\n{input_text}"
            
            # Generate presentation with markdown preservation
            generation_id = await self.client.generate_presentation(
                input_text=input_text,
                format="presentation",
                num_cards=num_cards,
                text_mode="preserve",  # Preserve markdown formatting
                card_split="inputTextBreaks",  # Use --- for slide breaks
                theme_name=theme_name,
                export_as=export_format
            )
            
            # Poll for completion
            result = await self.client.poll_generation(generation_id)
            
            elapsed = time.time() - start_time
            
            # Prepare response
            response = {
                'gamma_url': result.get('gammaUrl'),
                'generation_id': generation_id,
                'export_url': result.get('exportUrl'),
                'credits_used': result.get('credits', {}).get('deducted', 0),
                'generation_time_seconds': elapsed,
                'theme': theme_name,
                'export_format': export_format,
                'slide_count': num_cards
            }
            
            # Save metadata if output directory provided
            if output_dir:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                metadata_file = output_dir / f"gamma_markdown_{timestamp}.json"
                with open(metadata_file, 'w') as f:
                    json.dump(response, f, indent=2)
                self.logger.info(f"Saved metadata to {metadata_file}")
            
            self.logger.info(
                "gamma_markdown_generation_complete",
                generation_id=generation_id,
                gamma_url=result.get('gammaUrl'),
                credits_used=result.get('credits', {}).get('deducted', 0),
                total_time_seconds=elapsed
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "gamma_markdown_generation_failed",
                error=str(e),
                elapsed_seconds=time.time() - start_time,
                exc_info=True
            )
            raise
    
    async def generate_executive_presentation(
        self,
        analysis_results: Dict,
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate executive-style presentation.
        
        Args:
            analysis_results: Analysis results dictionary
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results
            
        Returns:
            Dictionary with presentation details
        """
        return await self.generate_from_analysis(
            analysis_results=analysis_results,
            style="executive",
            export_format=export_format,
            output_dir=output_dir
        )
    
    async def generate_detailed_presentation(
        self,
        analysis_results: Dict,
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate detailed analysis presentation.
        
        Args:
            analysis_results: Analysis results dictionary
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results
            
        Returns:
            Dictionary with presentation details
        """
        return await self.generate_from_analysis(
            analysis_results=analysis_results,
            style="detailed",
            export_format=export_format,
            output_dir=output_dir
        )
    
    async def generate_training_presentation(
        self,
        analysis_results: Dict,
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate training-focused presentation.
        
        Args:
            analysis_results: Analysis results dictionary
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results
            
        Returns:
            Dictionary with presentation details
        """
        return await self.generate_from_analysis(
            analysis_results=analysis_results,
            style="training",
            export_format=export_format,
            output_dir=output_dir
        )
    
    async def generate_all_styles(
        self,
        analysis_results: Dict,
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate all presentation styles.
        
        Args:
            analysis_results: Analysis results dictionary
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results
            
        Returns:
            Dictionary with all presentation results
        """
        self.logger.info("generating_all_presentation_styles")
        
        results = {}
        styles = ["executive", "detailed", "training"]
        
        for style in styles:
            try:
                self.logger.info(f"generating_{style}_presentation")
                results[style] = await self.generate_from_analysis(
                    analysis_results=analysis_results,
                    style=style,
                    export_format=export_format,
                    output_dir=output_dir
                )
            except Exception as e:
                self.logger.error(
                    f"failed_to_generate_{style}_presentation",
                    error=str(e),
                    exc_info=True
                )
                results[style] = {
                    'error': str(e),
                    'style': style,
                    'generation_successful': False
                }
        
        self.logger.info(
            "all_presentation_styles_complete",
            successful_generations=len([r for r in results.values() if r.get('generation_successful', True)])
        )
        
        return results
    
    async def generate_from_voc_analysis(
        self,
        voc_results: Dict,
        style: str = "executive",
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate Gamma presentation from VoC analysis results.
        
        Wrapper that converts VoC structure to standard analysis format.
        
        Args:
            voc_results: VoC analysis results with structure:
                - results: Dict[category, {volume, sentiment_breakdown, examples, agent_breakdown}]
                - agent_feedback_summary: Dict[agent_type, summary]
                - insights: List[str]
                - historical_trends: Optional[Dict]
                - metadata: Dict with analysis info
            style: Presentation style ("executive", "detailed", "training")
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results
            
        Returns:
            Dictionary with presentation details
        """
        self.logger.info("generating_gamma_from_voc", style=style)
        
        try:
            # Detect period type from metadata
            metadata = voc_results.get('metadata', {})
            start_date = metadata.get('start_date')
            end_date = metadata.get('end_date')
            period_type, period_label = detect_period_type(start_date, end_date) if start_date and end_date else ('custom', 'Custom')
            
            # Use VoC-specific narrative builder
            input_text = self.builder.build_voc_narrative_content(voc_results, style, period_type)
            
            # Validate input before sending to Gamma
            validation_errors = self._validate_gamma_input(input_text, voc_results, mode='voc')
            if validation_errors:
                self.logger.error(f"Gamma input validation failed: {validation_errors}")
                raise ValueError(f"Gamma input validation failed: {'; '.join(validation_errors)}")
            
            # Get style-specific parameters
            num_cards = self.prompts.get_slide_count_for_style(style)
            additional_instructions = self.prompts.get_additional_instructions_for_style(style)
            
            # Generate presentation
            generation_id = await self.client.generate_presentation(
                input_text=input_text,
                format="presentation",
                num_cards=num_cards,
                text_mode="generate",
                export_as=export_format,
                additional_instructions=additional_instructions
            )
            
            # Poll for completion
            result = await self.client.poll_generation(generation_id)

            elapsed = time.time() - start_time

            # Prepare response
            response = {
                'gamma_url': result.get('gammaUrl'),
                'generation_id': generation_id,
                'export_url': result.get('exportUrl'),
                'credits_used': result.get('credits', {}).get('deducted', 0),
                'generation_time_seconds': elapsed,
                'style': style,
                'export_format': export_format,
                'slide_count': num_cards,
                'voc_analysis': True,  # Flag to indicate this came from VoC
                'period_type': period_type,
                'period_label': period_label
            }
            
            # Generate markdown summary
            try:
                from src.services.google_docs_exporter import GoogleDocsExporter
                from pathlib import Path
                
                docs_exporter = GoogleDocsExporter()
                markdown_output_dir = output_dir if output_dir else Path("outputs")
                markdown_output_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                markdown_filename = f"voc_analysis_{period_type}_{style}_{timestamp}.md"
                markdown_path = markdown_output_dir / markdown_filename
                
                docs_exporter.export_to_markdown(
                    analysis_results=voc_results,
                    output_path=markdown_path,
                    style=style
                )
                
                # Read preview
                with open(markdown_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                    markdown_preview = markdown_content[:500] if len(markdown_content) > 500 else markdown_content
                
                # Add to response
                response['markdown_summary_path'] = str(markdown_path)
                response['markdown_preview'] = markdown_preview
                response['markdown_size_bytes'] = len(markdown_content)
                
                self.logger.info(
                    "voc_markdown_summary_generated",
                    markdown_path=str(markdown_path),
                    size_bytes=len(markdown_content)
                )
                
            except Exception as e:
                self.logger.warning(
                    "voc_markdown_summary_generation_failed",
                    error=str(e),
                    exc_info=True
                )
                response['markdown_summary_path'] = None
            
            # Save metadata if output directory provided
            if output_dir:
                await self._save_generation_metadata(response, voc_results, output_dir)
            
            self.logger.info(
                "voc_gamma_presentation_generated",
                style=style,
                gamma_url=response.get('gamma_url'),
                credits_used=response.get('credits_used')
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "voc_gamma_generation_failed",
                style=style,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def generate_from_canny_analysis(
        self,
        canny_results: Dict,
        style: str = "executive",
        export_format: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate Gamma presentation from Canny analysis results.
        
        Args:
            canny_results: Canny analysis results with structure:
                - posts_analyzed: int
                - sentiment_summary: Dict with overall sentiment and breakdowns
                - top_requests: List of top voted requests
                - status_breakdown: Dict of posts by status
                - category_breakdown: Dict of posts by category
                - vote_analysis: Dict with voting patterns
                - engagement_metrics: Dict with engagement statistics
                - trending_posts: List of trending posts
                - insights: List of actionable insights
                - metadata: Dict with analysis info
            style: Presentation style ("executive", "detailed", "training")
            export_format: Export format ("pdf" or "pptx")
            output_dir: Output directory for saving results
            
        Returns:
            Dictionary with presentation details
        """
        self.logger.info("generating_gamma_from_canny", style=style)
        
        try:
            # Detect period type from metadata
            metadata = canny_results.get('metadata', {})
            start_date = metadata.get('start_date')
            end_date = metadata.get('end_date')
            period_type, period_label = detect_period_type(start_date, end_date) if start_date and end_date else ('custom', 'Custom')
            
            # Use Canny-specific narrative builder
            input_text = self.builder.build_canny_narrative_content(canny_results, style, period_type)
            
            # Validate input before sending to Gamma
            validation_errors = self._validate_gamma_input(input_text, canny_results, mode='canny')
            if validation_errors:
                self.logger.error(f"Gamma input validation failed: {validation_errors}")
                raise ValueError(f"Gamma input validation failed: {'; '.join(validation_errors)}")
            
            # Get style-specific parameters
            num_cards = self.prompts.get_slide_count_for_style(style)
            additional_instructions = self.prompts.get_additional_instructions_for_style(style)
            
            # Generate presentation
            generation_id = await self.client.generate_presentation(
                input_text=input_text,
                format="presentation",
                num_cards=num_cards,
                text_mode="generate",
                export_as=export_format,
                additional_instructions=additional_instructions
            )
            
            # Poll for completion
            result = await self.client.poll_generation(generation_id)

            elapsed = time.time() - start_time

            # Prepare response
            response = {
                'gamma_url': result.get('gammaUrl'),
                'generation_id': generation_id,
                'export_url': result.get('exportUrl'),
                'credits_used': result.get('credits', {}).get('deducted', 0),
                'generation_time_seconds': elapsed,
                'style': style,
                'export_format': export_format,
                'slide_count': num_cards,
                'canny_analysis': True,  # Flag to indicate this came from Canny
                'period_type': period_type,
                'period_label': period_label
            }
            
            # Generate markdown summary
            try:
                from src.services.google_docs_exporter import GoogleDocsExporter
                from pathlib import Path
                
                docs_exporter = GoogleDocsExporter()
                markdown_output_dir = output_dir if output_dir else Path("outputs")
                markdown_output_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                markdown_filename = f"canny_analysis_{period_type}_{style}_{timestamp}.md"
                markdown_path = markdown_output_dir / markdown_filename
                
                docs_exporter.export_to_markdown(
                    analysis_results=canny_results,
                    output_path=markdown_path,
                    style=style
                )
                
                # Read preview
                with open(markdown_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                    markdown_preview = markdown_content[:500] if len(markdown_content) > 500 else markdown_content
                
                # Add to response
                response['markdown_summary_path'] = str(markdown_path)
                response['markdown_preview'] = markdown_preview
                response['markdown_size_bytes'] = len(markdown_content)
                
                self.logger.info(
                    "canny_markdown_summary_generated",
                    markdown_path=str(markdown_path),
                    size_bytes=len(markdown_content)
                )
                
            except Exception as e:
                self.logger.warning(
                    "canny_markdown_summary_generation_failed",
                    error=str(e),
                    exc_info=True
                )
                response['markdown_summary_path'] = None
            
            # Save metadata if output directory provided
            if output_dir:
                await self._save_generation_metadata(response, canny_results, output_dir)
            
            self.logger.info(
                "canny_gamma_presentation_generated",
                style=style,
                gamma_url=response.get('gamma_url'),
                credits_used=response.get('credits_used')
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "canny_gamma_generation_failed",
                style=style,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _save_generation_metadata(
        self,
        generation_result: Dict[str, Any],
        analysis_results: Dict,
        output_dir: Path
    ) -> None:
        """
        Save generation metadata to file.
        
        Args:
            generation_result: Generation result dictionary
            analysis_results: Original analysis results
            output_dir: Output directory
        """
        try:
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            style = generation_result.get('style', 'unknown')
            
            metadata = {
                'generation_metadata': generation_result,
                'analysis_summary': {
                    'conversation_count': len(analysis_results.get('conversations', [])),
                    'start_date': analysis_results.get('start_date'),
                    'end_date': analysis_results.get('end_date'),
                    'categories_analyzed': len(analysis_results.get('category_results', {})),
                    'period_type': generation_result.get('period_type', 'custom')
                },
                'generated_at': datetime.now().isoformat(),
                'style': style
            }
            
            filename = f"gamma_generation_{style}_{timestamp}.json"
            filepath = output_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            self.logger.info(
                "gamma_metadata_saved",
                filepath=str(filepath),
                style=style
            )
            
        except Exception as e:
            self.logger.error(
                "failed_to_save_gamma_metadata",
                error=str(e),
                exc_info=True
            )
    
    def get_available_styles(self) -> List[str]:
        """Get list of available presentation styles."""
        return ["executive", "detailed", "training"]
    
    def get_style_description(self, style: str) -> str:
        """Get description of a presentation style."""
        descriptions = {
            "executive": "High-level presentation for C-level executives focusing on business impact and strategic recommendations (8-12 slides)",
            "detailed": "Comprehensive analysis for operations teams with detailed data and implementation plans (15-20 slides)",
            "training": "Educational presentation for support teams with scenarios and best practices (10-15 slides)"
        }
        return descriptions.get(style, "Unknown presentation style")
    
    async def test_gamma_connection(self) -> bool:
        """
        Test connection to Gamma API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            return await self.client.test_connection()
        except Exception as e:
            self.logger.error(
                "gamma_connection_test_failed",
                error=str(e),
                exc_info=True
            )
            return False
    
    def get_generation_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about generation results.
        
        Args:
            results: Generation results dictionary
            
        Returns:
            Statistics dictionary
        """
        if isinstance(results, dict) and 'style' in results:
            # Single generation result
            return {
                'total_generations': 1,
                'successful_generations': 1 if results.get('gamma_url') else 0,
                'total_credits_used': results.get('credits_used', 0),
                'total_time_seconds': results.get('generation_time_seconds', 0),
                'styles_generated': [results.get('style', 'unknown')]
            }
        else:
            # Multiple generation results
            successful = [r for r in results.values() if isinstance(r, dict) and r.get('gamma_url')]
            failed = [r for r in results.values() if isinstance(r, dict) and not r.get('gamma_url')]
            
            return {
                'total_generations': len(results),
                'successful_generations': len(successful),
                'failed_generations': len(failed),
                'total_credits_used': sum(r.get('credits_used', 0) for r in successful),
                'total_time_seconds': sum(r.get('generation_time_seconds', 0) for r in successful),
                'styles_generated': [r.get('style', 'unknown') for r in successful],
                'failed_styles': [r.get('style', 'unknown') for r in failed]
            }

    def _validate_gamma_input(self, input_text: str, analysis_results: Dict, mode: str = 'hilary') -> List[str]:
        """
        Validate input before sending to Gamma API.

        Args:
            input_text: The generated markdown text
            analysis_results: Original analysis results
            mode: Validation mode - 'hilary' (topic orchestrator), 'voc', or 'canny'

        Returns:
            List of validation error strings (empty if valid)
        """
        validation_errors = []

        # Critical Check 1: Character limit (strict)
        if len(input_text) < 1:
            validation_errors.append("Input text is empty")
        elif len(input_text) > 400000:
            validation_errors.append(
                f"Input text too long: {len(input_text)} chars "
                f"(max 400,000 for v1.0, token limit: ~100k tokens)"
            )

        # Critical Check 2: Minimum content quality (strict)
        if len(input_text) < 200:
            validation_errors.append("Input text too short for meaningful presentation (minimum 200 characters)")

        # Mode-specific validation
        if mode == 'hilary':
            return self._validate_hilary_input(input_text, analysis_results, validation_errors)
        elif mode == 'voc':
            return self._validate_voc_input(input_text, analysis_results, validation_errors)
        elif mode == 'canny':
            return self._validate_canny_input(input_text, analysis_results, validation_errors)
        else:
            validation_errors.append(f"Unknown validation mode: {mode}")
            return validation_errors

    def _validate_hilary_input(self, input_text: str, analysis_results: Dict, validation_errors: List[str]) -> List[str]:
        """Validate Hilary markdown (topic orchestrator) input."""
        # Detect if this is topic-based orchestrator output
        is_topic_based = (
            'formatted_report' in analysis_results or
            'agent_results' in analysis_results or
            ('summary' in analysis_results and 'topics_analyzed' in analysis_results.get('summary', {}))
        )

        # Check required sections
        required_sections = ["Executive Summary"]
        optional_sections = ["Analysis", "Recommendations", "Immediate Actions", "Next Steps", "Critical Insights"]

        for section in required_sections:
            if section not in input_text:
                validation_errors.append(f"Missing required section: {section}")

        # Check if at least one optional section is present (warning only)
        has_optional_section = any(section in input_text for section in optional_sections)
        if not has_optional_section:
            self.logger.warning(f"No optional sections found: {', '.join(optional_sections)}")

        # Check data presence
        if is_topic_based:
            summary = analysis_results.get('summary', {})
            total_conversations = summary.get('total_conversations', 0)
            if total_conversations == 0:
                validation_errors.append("No conversations found in topic-based summary")
        elif 'conversations' in analysis_results:
            conversation_count = len(analysis_results.get('conversations', []))
            if conversation_count == 0:
                validation_errors.append("No conversations provided for analysis")

        # Check Intercom URL format (warning only)
        if 'intercom.com' in input_text:
            import re
            urls = re.findall(r'https://app\.intercom\.com/\S+', input_text)
            if not urls:
                self.logger.warning("Intercom URLs may be malformed")

        # Check category data presence (skip for topic-based)
        if not is_topic_based:
            category_results = analysis_results.get('category_results', {})
            if not category_results:
                self.logger.warning("No category analysis results available")

        return validation_errors

    def _validate_voc_input(self, input_text: str, analysis_results: Dict, validation_errors: List[str]) -> List[str]:
        """Validate VoC analysis input."""
        # Critical: Check for results structure
        if 'results' not in analysis_results:
            validation_errors.append("VoC results missing 'results' dictionary")
            return validation_errors

        # Critical: Check total volume
        total_volume = sum(
            category_data.get('volume', 0)
            for category_data in analysis_results['results'].values()
            if isinstance(category_data, dict)
        )
        if total_volume == 0:
            validation_errors.append("No conversations in VoC results (zero volume across all categories)")

        # Critical: Check metadata
        metadata = analysis_results.get('metadata', {})
        total_conversations = metadata.get('total_conversations', 0)
        if total_conversations == 0:
            validation_errors.append("VoC metadata shows zero conversations")

        # Optional: Check for required sections (warning only)
        required_sections = ["Executive Summary", "Analysis"]
        for section in required_sections:
            if section not in input_text:
                self.logger.warning(f"VoC input missing optional section: {section}")

        return validation_errors

    def _validate_canny_input(self, input_text: str, analysis_results: Dict, validation_errors: List[str]) -> List[str]:
        """Validate Canny analysis input."""
        # Critical: Check posts_analyzed
        posts_analyzed = analysis_results.get('posts_analyzed', 0)
        if posts_analyzed == 0:
            validation_errors.append("Canny analysis has zero posts analyzed")

        # Critical: Check sentiment_summary exists
        if 'sentiment_summary' not in analysis_results:
            validation_errors.append("Canny results missing 'sentiment_summary'")

        # Critical: Check status_breakdown present
        if 'status_breakdown' not in analysis_results:
            validation_errors.append("Canny results missing 'status_breakdown'")

        # Critical: Check top_requests non-empty when posts > 0
        if posts_analyzed > 0:
            top_requests = analysis_results.get('top_requests', [])
            if not top_requests:
                validation_errors.append("Canny analysis has posts but no top_requests")

        # Optional: Check for required sections (warning only)
        required_sections = ["Executive Summary", "Analysis"]
        for section in required_sections:
            if section not in input_text:
                self.logger.warning(f"Canny input missing optional section: {section}")

        return validation_errors

    def _validate_hilary_markdown(self, markdown: str) -> List[str]:
        """
        Validate Hilary markdown formatting contract.

        Checks:
        - Slide break presence (---)
        - Card headers (###)
        - Well-formed Intercom URLs for examples
        - Expected structure for topic cards

        Args:
            markdown: The formatted markdown text

        Returns:
            List of validation errors (empty if valid)
        """
        import re

        errors = []

        # Check for slide breaks
        slide_breaks = markdown.count('\n---\n')
        if slide_breaks == 0:
            errors.append("No slide breaks (---) found in markdown")

        # Check for card headers (### for topics)
        card_headers = len(re.findall(r'\n###\s+\w', markdown))
        if card_headers == 0:
            errors.append("No card headers (###) found in markdown")

        # Check Intercom URL format when examples are present
        if '**Examples**:' in markdown or 'View conversation' in markdown:
            # Look for Intercom URLs
            intercom_urls = re.findall(r'https://app\.intercom\.com/a/[^\s\)]+', markdown)

            # Check format of found URLs
            for url in intercom_urls:
                if '/inbox/inbox/conv_' not in url:
                    errors.append(f"Malformed Intercom URL found: {url[:50]}...")

            # Warn if examples mentioned but no URLs found
            if '**Examples**:' in markdown and len(intercom_urls) == 0:
                self.logger.warning("Examples section found but no Intercom URLs present")

        # Check for minimum expected structure in topic cards
        if '###' in markdown:
            # Should have volume indicators
            if 'tickets' not in markdown.lower() and 'conversations' not in markdown.lower():
                self.logger.warning("Topic cards may be missing volume indicators")

            # Should have sentiment indicators
            if '**Sentiment**:' not in markdown:
                self.logger.warning("Topic cards may be missing sentiment sections")

        return errors