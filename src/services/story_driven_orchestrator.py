"""
Story-driven orchestrator that coordinates story-focused analysis
and integrates with the existing analysis pipeline.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from src.services.story_driven_preprocessor import StoryDrivenPreprocessor
from src.services.synthesis_engine import SynthesisEngine
from src.services.gamma_generator import GammaGenerator
from src.services.openai_client import OpenAIClient
from src.config.story_driven_prompts import StoryDrivenPrompts

logger = logging.getLogger(__name__)


class StoryDrivenOrchestrator:
    """
    Orchestrator that focuses on story-driven customer experience analysis.
    This extends the existing analysis pipeline with narrative-focused insights.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize story-driven components
        self.story_preprocessor = StoryDrivenPreprocessor()
        self.synthesis_engine = SynthesisEngine()
        self.gamma_generator = GammaGenerator()
        self.openai_client = OpenAIClient()
        
        self.logger.info("StoryDrivenOrchestrator initialized")
    
    async def run_story_driven_analysis(
        self,
        conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a comprehensive story-driven analysis of customer experience.
        
        Args:
            conversations: List of Intercom conversations
            canny_posts: List of Canny feedback posts
            start_date: Start date for analysis
            end_date: End date for analysis
            options: Analysis options and configuration
            
        Returns:
            Dictionary containing story-driven analysis results
        """
        self.logger.info(f"Starting story-driven analysis from {start_date} to {end_date}")
        
        if options is None:
            options = {}
        
        analysis_period = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        try:
            # Step 1: Preprocess data with story focus
            self.logger.info("Step 1: Preprocessing data for story analysis")
            preprocessed_data = await self.story_preprocessor.preprocess_for_story_analysis(
                conversations, canny_posts, analysis_period, options
            )
            
            # Step 2: Generate customer journey stories
            self.logger.info("Step 2: Generating customer journey stories")
            journey_stories = await self._generate_customer_journey_stories(
                preprocessed_data, analysis_period, options
            )
            
            # Step 3: Extract actionable insights
            self.logger.info("Step 3: Extracting actionable insights")
            actionable_insights = await self._extract_actionable_insights(
                preprocessed_data, journey_stories, analysis_period, options
            )
            
            # Step 4: Create executive narrative
            self.logger.info("Step 4: Creating executive narrative")
            executive_narrative = await self._create_executive_narrative(
                preprocessed_data, journey_stories, actionable_insights, analysis_period, options
            )
            
            # Step 5: Generate Gamma presentation with story focus
            gamma_presentation = None
            if options.get('generate_gamma_presentation', False):
                self.logger.info("Step 5: Generating story-driven Gamma presentation")
                gamma_presentation = await self._generate_story_driven_gamma_presentation(
                    preprocessed_data, journey_stories, actionable_insights, 
                    executive_narrative, start_date, end_date, options
                )
            
            # Step 6: Log all ChatGPT analysis
            self.logger.info("Step 6: Logging ChatGPT analysis")
            chatgpt_analysis_log = await self._log_complete_chatgpt_analysis(
                preprocessed_data, journey_stories, actionable_insights, 
                executive_narrative, analysis_period
            )
            
            results = {
                'analysis_metadata': {
                    'analysis_type': 'story_driven_customer_experience',
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'analysis_period': analysis_period,
                    'conversation_count': len(conversations),
                    'canny_post_count': len(canny_posts),
                    'analysis_timestamp': datetime.now().isoformat(),
                    'options': options
                },
                'preprocessed_data': preprocessed_data,
                'journey_stories': journey_stories,
                'actionable_insights': actionable_insights,
                'executive_narrative': executive_narrative,
                'gamma_presentation': gamma_presentation,
                'chatgpt_analysis_log': chatgpt_analysis_log
            }
            
            self.logger.info("Story-driven analysis completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Story-driven analysis failed: {e}", exc_info=True)
            return {
                'error': f'Story-driven analysis failed: {str(e)}',
                'analysis_metadata': {
                    'analysis_type': 'story_driven_customer_experience',
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'analysis_period': analysis_period,
                    'error_timestamp': datetime.now().isoformat()
                }
            }
    
    async def _generate_customer_journey_stories(
        self,
        preprocessed_data: Dict[str, Any],
        analysis_period: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive customer journey stories."""
        try:
            conversation_stories = preprocessed_data.get('conversation_stories', [])
            canny_stories = preprocessed_data.get('canny_stories', [])
            
            # Use the story-driven prompt for journey analysis
            prompt = StoryDrivenPrompts.get_customer_journey_story_prompt(
                conversation_stories,
                canny_stories,
                analysis_period,
                options.get('focus_areas', [])
            )
            
            journey_analysis = await self.openai_client.generate_analysis(prompt)
            
            return {
                'journey_analysis': journey_analysis,
                'conversation_stories': conversation_stories,
                'canny_stories': canny_stories,
                'emotional_patterns': preprocessed_data.get('emotional_patterns', {}),
                'journey_moments': preprocessed_data.get('journey_moments', {}),
                'recurring_themes': preprocessed_data.get('recurring_themes', [])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate customer journey stories: {e}")
            return {'error': f'Journey story generation failed: {e}'}
    
    async def _extract_actionable_insights(
        self,
        preprocessed_data: Dict[str, Any],
        journey_stories: Dict[str, Any],
        analysis_period: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract actionable insights from the story analysis."""
        try:
            # Get the story insights from preprocessing
            story_insights = preprocessed_data.get('story_insights', {})
            
            # Validate insights using the validation prompt
            insights_to_validate = self._extract_insights_for_validation(story_insights)
            supporting_evidence = self._prepare_supporting_evidence(preprocessed_data)
            
            validation_prompt = StoryDrivenPrompts.get_insight_validation_prompt(
                insights_to_validate,
                supporting_evidence,
                analysis_period
            )
            
            validated_insights = await self.openai_client.generate_analysis(validation_prompt)
            
            return {
                'validated_insights': validated_insights,
                'original_insights': story_insights,
                'supporting_evidence': supporting_evidence,
                'insight_confidence': self._calculate_insight_confidence(story_insights)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract actionable insights: {e}")
            return {'error': f'Insight extraction failed: {e}'}
    
    def _extract_insights_for_validation(self, story_insights: Dict[str, Any]) -> List[str]:
        """Extract insights from story analysis for validation."""
        insights = []
        
        # Extract insights from the story insights text
        insights_text = story_insights.get('insights_text', '')
        if insights_text:
            # Simple extraction - split by common patterns
            lines = insights_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    insights.append(line.lstrip('-•* ').strip())
        
        return insights[:10]  # Limit to top 10 insights
    
    def _prepare_supporting_evidence(self, preprocessed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare supporting evidence for insight validation."""
        evidence = {
            'conversation_stories': preprocessed_data.get('conversation_stories', []),
            'canny_stories': preprocessed_data.get('canny_stories', []),
            'emotional_patterns': preprocessed_data.get('emotional_patterns', {}),
            'recurring_themes': preprocessed_data.get('recurring_themes', []),
            'journey_moments': preprocessed_data.get('journey_moments', {})
        }
        
        return evidence
    
    def _calculate_insight_confidence(self, story_insights: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence levels for insights."""
        # This is a simplified confidence calculation
        # In practice, you'd use more sophisticated methods
        
        confidence = {
            'overall_confidence': 0.8,  # Default confidence
            'data_quality': 0.9,  # Based on data completeness
            'story_coherence': 0.7,  # Based on narrative consistency
            'actionability': 0.8  # Based on insight specificity
        }
        
        return confidence
    
    async def _create_executive_narrative(
        self,
        preprocessed_data: Dict[str, Any],
        journey_stories: Dict[str, Any],
        actionable_insights: Dict[str, Any],
        analysis_period: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an executive-level narrative from the story analysis."""
        try:
            # Prepare customer stories and business metrics
            customer_stories = {
                'conversation_stories': preprocessed_data.get('conversation_stories', []),
                'canny_stories': preprocessed_data.get('canny_stories', []),
                'journey_analysis': journey_stories.get('journey_analysis', ''),
                'emotional_patterns': preprocessed_data.get('emotional_patterns', {})
            }
            
            business_metrics = {
                'total_conversations': len(preprocessed_data.get('conversation_stories', [])),
                'total_canny_posts': len(preprocessed_data.get('canny_stories', [])),
                'emotional_distribution': preprocessed_data.get('emotional_patterns', {}).get('emotional_percentages', {}),
                'journey_distribution': self._calculate_journey_distribution(preprocessed_data.get('journey_moments', {}))
            }
            
            # Use the executive story prompt
            prompt = StoryDrivenPrompts.get_executive_story_prompt(
                customer_stories,
                business_metrics,
                analysis_period
            )
            
            executive_narrative = await self.openai_client.generate_analysis(prompt)
            
            return {
                'narrative_text': executive_narrative,
                'customer_stories': customer_stories,
                'business_metrics': business_metrics,
                'key_themes': preprocessed_data.get('recurring_themes', []),
                'actionable_insights': actionable_insights.get('validated_insights', '')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create executive narrative: {e}")
            return {'error': f'Executive narrative creation failed: {e}'}
    
    def _calculate_journey_distribution(self, journey_moments: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """Calculate distribution of customer journey moments."""
        distribution = {}
        for stage, moments in journey_moments.items():
            distribution[stage] = len(moments)
        return distribution
    
    async def _generate_story_driven_gamma_presentation(
        self,
        preprocessed_data: Dict[str, Any],
        journey_stories: Dict[str, Any],
        actionable_insights: Dict[str, Any],
        executive_narrative: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a Gamma presentation focused on customer stories."""
        try:
            # Prepare analysis results for Gamma
            analysis_results = {
                'conversations': preprocessed_data.get('conversation_stories', []),
                'canny_posts': preprocessed_data.get('canny_stories', []),
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'journey_stories': journey_stories,
                'actionable_insights': actionable_insights,
                'executive_narrative': executive_narrative,
                'emotional_patterns': preprocessed_data.get('emotional_patterns', {}),
                'recurring_themes': preprocessed_data.get('recurring_themes', [])
            }
            
            # Generate Gamma presentation
            gamma_result = await self.gamma_generator.generate_from_analysis(
                analysis_results=analysis_results,
                style=options.get('gamma_style', 'executive'),
                export_format=options.get('gamma_export')
            )
            
            return gamma_result
            
        except Exception as e:
            self.logger.error(f"Failed to generate story-driven Gamma presentation: {e}")
            return {'error': f'Gamma presentation generation failed: {e}'}
    
    async def _log_complete_chatgpt_analysis(
        self,
        preprocessed_data: Dict[str, Any],
        journey_stories: Dict[str, Any],
        actionable_insights: Dict[str, Any],
        executive_narrative: Dict[str, Any],
        analysis_period: str
    ) -> Dict[str, Any]:
        """Log all ChatGPT analysis before sending to Gamma API."""
        try:
            complete_log = {
                'timestamp': datetime.now().isoformat(),
                'analysis_period': analysis_period,
                'analysis_type': 'story_driven_customer_experience',
                'chatgpt_analyses': {
                    'preprocessing_analysis': preprocessed_data.get('chatgpt_analysis_log', {}),
                    'journey_story_analysis': journey_stories.get('journey_analysis', ''),
                    'insight_validation_analysis': actionable_insights.get('validated_insights', ''),
                    'executive_narrative_analysis': executive_narrative.get('narrative_text', '')
                },
                'analysis_metadata': {
                    'conversation_count': len(preprocessed_data.get('conversation_stories', [])),
                    'canny_post_count': len(preprocessed_data.get('canny_stories', [])),
                    'emotional_patterns_identified': len(preprocessed_data.get('emotional_patterns', {}).get('emotional_scores', {})),
                    'recurring_themes_identified': len(preprocessed_data.get('recurring_themes', [])),
                    'journey_stages_analyzed': len(preprocessed_data.get('journey_moments', {}))
                },
                'model_used': 'gpt-4',
                'prompt_templates_used': [
                    'customer_journey_story_prompt',
                    'insight_extraction_prompt',
                    'narrative_synthesis_prompt',
                    'insight_validation_prompt',
                    'executive_story_prompt'
                ]
            }
            
            # Log the complete analysis
            self.logger.info(f"Complete ChatGPT analysis logged for {analysis_period}")
            self.logger.debug(f"Complete analysis log: {json.dumps(complete_log, indent=2)}")
            
            return complete_log
            
        except Exception as e:
            self.logger.error(f"Failed to log complete ChatGPT analysis: {e}")
            return {'error': f'Complete analysis logging failed: {e}'}
    
    async def run_quick_story_analysis(
        self,
        conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        analysis_period: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a quick story analysis for immediate insights.
        This is a lighter version of the full analysis.
        """
        self.logger.info(f"Starting quick story analysis for {analysis_period}")
        
        if options is None:
            options = {}
        
        try:
            # Quick preprocessing
            preprocessed_data = await self.story_preprocessor.preprocess_for_story_analysis(
                conversations, canny_posts, analysis_period, options
            )
            
            # Quick insight generation
            story_insights = preprocessed_data.get('story_insights', {})
            narrative_synthesis = preprocessed_data.get('narrative_synthesis', '')
            
            # Quick executive summary
            executive_summary = await self._generate_quick_executive_summary(
                story_insights, narrative_synthesis, analysis_period
            )
            
            return {
                'analysis_metadata': {
                    'analysis_type': 'quick_story_analysis',
                    'analysis_period': analysis_period,
                    'conversation_count': len(conversations),
                    'canny_post_count': len(canny_posts),
                    'analysis_timestamp': datetime.now().isoformat()
                },
                'story_insights': story_insights,
                'narrative_synthesis': narrative_synthesis,
                'executive_summary': executive_summary,
                'emotional_patterns': preprocessed_data.get('emotional_patterns', {}),
                'recurring_themes': preprocessed_data.get('recurring_themes', [])
            }
            
        except Exception as e:
            self.logger.error(f"Quick story analysis failed: {e}")
            return {'error': f'Quick story analysis failed: {e}'}
    
    async def _generate_quick_executive_summary(
        self,
        story_insights: Dict[str, Any],
        narrative_synthesis: str,
        analysis_period: str
    ) -> str:
        """Generate a quick executive summary from story analysis."""
        try:
            prompt = f"""Create a concise executive summary (3-4 paragraphs) of this customer experience analysis:

Analysis Period: {analysis_period}

Story Insights: {story_insights.get('insights_text', '')}

Narrative Synthesis: {narrative_synthesis}

Focus on:
1. Key customer experience themes
2. Most important insights for business action
3. Immediate opportunities for improvement

Write for an executive audience - clear, actionable, and focused on business impact."""

            summary = await self.openai_client.generate_analysis(prompt)
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate quick executive summary: {e}")
            return "Executive summary generation failed"