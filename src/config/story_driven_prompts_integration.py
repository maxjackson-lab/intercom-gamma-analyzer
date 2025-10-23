"""
Integration of story-driven prompts with the main prompt system.
"""

from typing import Dict, List, Optional
from datetime import datetime
from src.config.story_driven_prompts import StoryDrivenPrompts


class StoryDrivenPromptIntegration:
    """Integration class for story-driven prompts with existing prompt system."""
    
    @staticmethod
    def get_enhanced_voice_of_customer_prompt(
        month: int,
        year: int,
        tier1_countries: List[str],
        intercom_data: str,
        canny_data: str = None,
        use_story_driven: bool = True
    ) -> str:
        """
        Get enhanced Voice of Customer prompt with optional story-driven approach.
        
        Args:
            month: Month for analysis
            year: Year for analysis
            tier1_countries: List of tier 1 countries
            intercom_data: Intercom conversation data
            canny_data: Optional Canny feedback data
            use_story_driven: Whether to use story-driven approach
            
        Returns:
            Enhanced prompt string
        """
        if use_story_driven and canny_data:
            # Use story-driven approach with Canny data
            return StoryDrivenPrompts.get_customer_journey_story_prompt(
                conversations=intercom_data,
                canny_posts=canny_data,
                analysis_period=f"{month}/{year}",
                focus_areas=tier1_countries
            )
        elif use_story_driven:
            # Use story-driven approach without Canny data
            return StoryDrivenPrompts.get_customer_journey_story_prompt(
                conversations=intercom_data,
                canny_posts=[],
                analysis_period=f"{month}/{year}",
                focus_areas=tier1_countries
            )
        else:
            # Fall back to traditional approach
            from config.prompts import PromptTemplates
            return PromptTemplates.get_voice_of_customer_prompt(
                month=month,
                year=year,
                tier1_countries=tier1_countries,
                intercom_data=intercom_data
            )
    
    @staticmethod
    def get_enhanced_trend_analysis_prompt(
        start_date: str,
        end_date: str,
        focus_areas: List[str],
        custom_instructions: Optional[str],
        intercom_data: str,
        canny_data: str = None,
        use_story_driven: bool = True
    ) -> str:
        """
        Get enhanced trend analysis prompt with optional story-driven approach.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            focus_areas: Areas to focus on
            custom_instructions: Custom analysis instructions
            intercom_data: Intercom conversation data
            canny_data: Optional Canny feedback data
            use_story_driven: Whether to use story-driven approach
            
        Returns:
            Enhanced prompt string
        """
        if use_story_driven:
            # Use story-driven approach
            return StoryDrivenPrompts.get_insight_extraction_prompt(
                conversations=intercom_data,
                canny_posts=canny_data or [],
                analysis_period=f"{start_date} to {end_date}"
            )
        else:
            # Fall back to traditional approach
            from config.prompts import PromptTemplates
            return PromptTemplates.get_trend_analysis_prompt(
                start_date=start_date,
                end_date=end_date,
                focus_areas=focus_areas,
                custom_instructions=custom_instructions,
                intercom_data=intercom_data
            )
    
    @staticmethod
    def get_enhanced_executive_presentation_prompt(
        start_date: str,
        end_date: str,
        conversation_count: int,
        key_metrics: Dict,
        customer_quotes: List[Dict],
        top_issues: List[Dict],
        recommendations: List[str],
        use_story_driven: bool = True
    ) -> str:
        """
        Get enhanced executive presentation prompt with optional story-driven approach.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            conversation_count: Number of conversations
            key_metrics: Key business metrics
            customer_quotes: Customer quotes
            top_issues: Top issues identified
            recommendations: Business recommendations
            use_story_driven: Whether to use story-driven approach
            
        Returns:
            Enhanced prompt string
        """
        if use_story_driven:
            # Use story-driven approach
            customer_stories = {
                'conversation_count': conversation_count,
                'customer_quotes': customer_quotes,
                'top_issues': top_issues
            }
            
            business_metrics = {
                'key_metrics': key_metrics,
                'recommendations': recommendations
            }
            
            return StoryDrivenPrompts.get_executive_story_prompt(
                customer_stories=customer_stories,
                business_metrics=business_metrics,
                analysis_period=f"{start_date} to {end_date}"
            )
        else:
            # Fall back to traditional approach
            from config.gamma_prompts import GammaPrompts
            return GammaPrompts.build_executive_presentation_prompt(
                start_date=start_date,
                end_date=end_date,
                conversation_count=conversation_count,
                key_metrics=key_metrics,
                customer_quotes=customer_quotes,
                top_issues=top_issues,
                recommendations=recommendations
            )
    
    @staticmethod
    def get_chatgpt_analysis_logging_prompt(
        analysis_type: str,
        analysis_data: Dict,
        analysis_period: str
    ) -> str:
        """
        Get prompt for logging ChatGPT analysis before Gamma API calls.
        
        Args:
            analysis_type: Type of analysis being performed
            analysis_data: Data being analyzed
            analysis_period: Time period for analysis
            
        Returns:
            Logging prompt string
        """
        return f"""# ChatGPT Analysis Logging - {analysis_type}

## Analysis Metadata
- **Analysis Type:** {analysis_type}
- **Analysis Period:** {analysis_period}
- **Timestamp:** {datetime.now().isoformat()}
- **Model Used:** GPT-4

## Analysis Data Summary
- **Data Points:** {len(analysis_data.get('conversations', []))} conversations, {len(analysis_data.get('canny_posts', []))} Canny posts
- **Key Themes:** {len(analysis_data.get('recurring_themes', []))} recurring themes identified
- **Emotional Patterns:** {len(analysis_data.get('emotional_patterns', {}).get('emotional_scores', {}))} emotional patterns detected
- **Journey Stages:** {len(analysis_data.get('journey_moments', {}))} journey stages analyzed

## Analysis Quality Indicators
- **Data Completeness:** {analysis_data.get('data_quality_score', 'N/A')}
- **Story Coherence:** {analysis_data.get('story_coherence_score', 'N/A')}
- **Actionability:** {analysis_data.get('actionability_score', 'N/A')}

## Key Insights Generated
{analysis_data.get('key_insights', 'No insights generated')}

## Narrative Synthesis
{analysis_data.get('narrative_synthesis', 'No narrative synthesis available')}

## Business Implications
{analysis_data.get('business_implications', 'No business implications identified')}

## Next Steps for Gamma Presentation
- Focus on customer stories and emotional journey
- Highlight actionable insights with specific examples
- Connect customer experiences to business impact
- Use real customer quotes to make it tangible
- Balance challenges with opportunities

This analysis is ready for Gamma presentation generation with a focus on storytelling and customer experience narratives."""