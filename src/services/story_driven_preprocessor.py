"""
Story-driven data preprocessor that focuses on extracting customer narratives
and emotional experiences from Intercom and Canny data.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import json

from services.openai_client import OpenAIClient
from config.story_driven_prompts import StoryDrivenPrompts

logger = logging.getLogger(__name__)


class StoryDrivenPreprocessor:
    """
    Preprocessor that focuses on extracting customer stories and narratives
    rather than just technical metrics.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.openai_client = OpenAIClient()
        
        # Emotional indicators for story extraction
        self.emotional_indicators = {
            'frustration': ['frustrated', 'annoying', 'terrible', 'awful', 'hate', 'disappointed', 'angry'],
            'excitement': ['excited', 'amazing', 'love', 'fantastic', 'brilliant', 'perfect', 'awesome'],
            'confusion': ['confused', 'unclear', 'don\'t understand', 'not sure', 'how do i', 'help me'],
            'satisfaction': ['satisfied', 'happy', 'great', 'good', 'thanks', 'appreciate', 'excellent'],
            'urgency': ['urgent', 'asap', 'immediately', 'critical', 'emergency', 'right now'],
            'gratitude': ['thank you', 'thanks', 'appreciate', 'grateful', 'helpful', 'saved me']
        }
        
        # Story elements to extract
        self.story_elements = {
            'customer_goals': ['trying to', 'want to', 'need to', 'looking for', 'hoping to'],
            'pain_points': ['problem', 'issue', 'bug', 'broken', 'not working', 'can\'t', 'unable'],
            'success_moments': ['worked', 'solved', 'fixed', 'success', 'got it', 'perfect'],
            'journey_moments': ['first time', 'new to', 'learning', 'getting started', 'onboarding']
        }
        
        self.logger.info("StoryDrivenPreprocessor initialized")
    
    async def preprocess_for_story_analysis(
        self,
        conversations: List[Dict[str, Any]],
        canny_posts: List[Dict[str, Any]],
        analysis_period: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Preprocess data with a focus on extracting customer stories and narratives.
        
        Args:
            conversations: List of Intercom conversations
            canny_posts: List of Canny feedback posts
            analysis_period: Time period for analysis
            options: Additional preprocessing options
            
        Returns:
            Dictionary containing story-focused preprocessed data
        """
        self.logger.info(f"Starting story-driven preprocessing for {len(conversations)} conversations and {len(canny_posts)} Canny posts")
        
        options = options or {}
        
        try:
            # Step 1: Extract customer stories from conversations
            conversation_stories = await self._extract_conversation_stories(conversations, options)
            
            # Step 2: Extract stories from Canny feedback
            canny_stories = await self._extract_canny_stories(canny_posts, options)
            
            # Step 3: Identify emotional patterns
            emotional_patterns = self._identify_emotional_patterns(conversation_stories, canny_stories)
            
            # Step 4: Extract customer journey moments
            journey_moments = self._extract_journey_moments(conversation_stories, canny_stories)
            
            # Step 5: Identify recurring themes
            recurring_themes = await self._identify_recurring_themes(conversation_stories, canny_stories)
            
            # Step 6: Generate story insights
            story_insights = await self._generate_story_insights(
                conversation_stories, canny_stories, emotional_patterns, recurring_themes
            )
            
            # Step 7: Create narrative synthesis
            narrative_synthesis = await self._create_narrative_synthesis(
                conversation_stories, canny_stories, analysis_period
            )
            
            # Step 8: Log ChatGPT analysis for Gamma
            chatgpt_analysis = await self._log_chatgpt_analysis(
                story_insights, narrative_synthesis, analysis_period
            )
            
            results = {
                'analysis_metadata': {
                    'analysis_period': analysis_period,
                    'conversation_count': len(conversations),
                    'canny_post_count': len(canny_posts),
                    'preprocessing_timestamp': datetime.now().isoformat(),
                    'options': options
                },
                'conversation_stories': conversation_stories,
                'canny_stories': canny_stories,
                'emotional_patterns': emotional_patterns,
                'journey_moments': journey_moments,
                'recurring_themes': recurring_themes,
                'story_insights': story_insights,
                'narrative_synthesis': narrative_synthesis,
                'chatgpt_analysis_log': chatgpt_analysis
            }
            
            self.logger.info("Story-driven preprocessing completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Story-driven preprocessing failed: {e}", exc_info=True)
            raise
    
    async def _extract_conversation_stories(
        self, 
        conversations: List[Dict[str, Any]], 
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract customer stories from Intercom conversations."""
        self.logger.info(f"Extracting stories from {len(conversations)} conversations")
        
        stories = []
        
        for conv in conversations:
            try:
                story = await self._extract_single_conversation_story(conv, options)
                if story:
                    stories.append(story)
            except Exception as e:
                self.logger.warning(f"Failed to extract story from conversation {conv.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Extracted {len(stories)} conversation stories")
        return stories
    
    async def _extract_single_conversation_story(
        self, 
        conversation: Dict[str, Any], 
        options: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract a single customer story from a conversation."""
        try:
            # Extract conversation text
            conversation_text = self._extract_full_conversation_text(conversation)
            
            if not conversation_text or len(conversation_text.strip()) < 20:
                return None
            
            # Extract story elements
            story_elements = self._extract_story_elements(conversation_text)
            
            # Identify emotional tone
            emotional_tone = self._identify_emotional_tone(conversation_text)
            
            # Extract customer quotes
            customer_quotes = self._extract_customer_quotes(conversation)
            
            # Identify journey stage
            journey_stage = self._identify_journey_stage(conversation_text)
            
            # Generate story summary using AI
            story_summary = await self._generate_story_summary(conversation_text, options)
            
            return {
                'conversation_id': conversation.get('id'),
                'created_at': conversation.get('created_at'),
                'conversation_text': conversation_text,
                'story_elements': story_elements,
                'emotional_tone': emotional_tone,
                'customer_quotes': customer_quotes,
                'journey_stage': journey_stage,
                'story_summary': story_summary,
                'intercom_url': self._generate_intercom_url(conversation.get('id')),
                'tags': conversation.get('tags', {}).get('tags', []),
                'custom_attributes': conversation.get('custom_attributes', {})
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract story from conversation: {e}")
            return None
    
    def _extract_full_conversation_text(self, conversation: Dict[str, Any]) -> str:
        """Extract all text from a conversation for story analysis."""
        text_parts = []
        
        # Extract from source
        source = conversation.get('source', {})
        if source.get('body'):
            text_parts.append(f"Customer: {source['body']}")
        
        # Extract from conversation parts
        parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            if part.get('body'):
                author_type = part.get('author', {}).get('type', 'unknown')
                if author_type == 'user':
                    text_parts.append(f"Customer: {part['body']}")
                elif author_type == 'admin':
                    text_parts.append(f"Support: {part['body']}")
        
        return '\n'.join(text_parts)
    
    def _extract_story_elements(self, text: str) -> Dict[str, List[str]]:
        """Extract story elements from conversation text."""
        elements = {}
        text_lower = text.lower()
        
        for element_type, keywords in self.story_elements.items():
            elements[element_type] = []
            for keyword in keywords:
                if keyword in text_lower:
                    # Extract context around the keyword
                    context = self._extract_context_around_keyword(text, keyword)
                    if context:
                        elements[element_type].append(context)
        
        return elements
    
    def _extract_context_around_keyword(self, text: str, keyword: str) -> str:
        """Extract context around a keyword for story analysis."""
        # Find the keyword in the text
        keyword_pos = text.lower().find(keyword)
        if keyword_pos == -1:
            return ""
        
        # Extract 50 characters before and after the keyword
        start = max(0, keyword_pos - 50)
        end = min(len(text), keyword_pos + len(keyword) + 50)
        
        context = text[start:end].strip()
        return context
    
    def _identify_emotional_tone(self, text: str) -> Dict[str, Any]:
        """Identify the emotional tone of the conversation."""
        text_lower = text.lower()
        emotional_scores = {}
        
        for emotion, keywords in self.emotional_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            emotional_scores[emotion] = score
        
        # Determine dominant emotion
        dominant_emotion = max(emotional_scores.items(), key=lambda x: x[1])
        
        return {
            'dominant_emotion': dominant_emotion[0] if dominant_emotion[1] > 0 else 'neutral',
            'emotional_scores': emotional_scores,
            'emotional_intensity': sum(emotional_scores.values())
        }
    
    def _extract_customer_quotes(self, conversation: Dict[str, Any]) -> List[str]:
        """Extract meaningful customer quotes from the conversation."""
        quotes = []
        
        # Extract from source
        source = conversation.get('source', {})
        if source.get('body') and len(source['body'].strip()) > 10:
            quotes.append(source['body'].strip())
        
        # Extract from conversation parts
        parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            if (part.get('author', {}).get('type') == 'user' and 
                part.get('body') and len(part['body'].strip()) > 10):
                quotes.append(part['body'].strip())
        
        return quotes[:3]  # Limit to top 3 quotes
    
    def _identify_journey_stage(self, text: str) -> str:
        """Identify the customer journey stage based on conversation content."""
        text_lower = text.lower()
        
        if any(phrase in text_lower for phrase in ['first time', 'new to', 'getting started', 'onboarding']):
            return 'onboarding'
        elif any(phrase in text_lower for phrase in ['how do i', 'tutorial', 'guide', 'learn']):
            return 'learning'
        elif any(phrase in text_lower for phrase in ['problem', 'issue', 'bug', 'not working']):
            return 'troubleshooting'
        elif any(phrase in text_lower for phrase in ['upgrade', 'plan', 'billing', 'subscription']):
            return 'expansion'
        elif any(phrase in text_lower for phrase in ['cancel', 'refund', 'leave', 'switch']):
            return 'churn_risk'
        else:
            return 'ongoing_use'
    
    async def _generate_story_summary(
        self, 
        conversation_text: str, 
        options: Dict[str, Any]
    ) -> str:
        """Generate a story summary using AI analysis."""
        try:
            # Use a focused prompt for story extraction
            prompt = f"""Analyze this customer support conversation and extract the key story elements:

{conversation_text}

Provide a brief story summary (2-3 sentences) that captures:
1. What the customer was trying to accomplish
2. What challenges they faced
3. How the interaction resolved (if it did)
4. The emotional tone of the experience

Focus on the human story, not just the technical details."""

            summary = await self.openai_client.generate_analysis(prompt)
            return summary
            
        except Exception as e:
            self.logger.warning(f"Failed to generate story summary: {e}")
            return "Story summary generation failed"
    
    async def _extract_canny_stories(
        self, 
        canny_posts: List[Dict[str, Any]], 
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract customer stories from Canny feedback posts."""
        self.logger.info(f"Extracting stories from {len(canny_posts)} Canny posts")
        
        stories = []
        
        for post in canny_posts:
            try:
                story = await self._extract_single_canny_story(post, options)
                if story:
                    stories.append(story)
            except Exception as e:
                self.logger.warning(f"Failed to extract story from Canny post {post.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Extracted {len(stories)} Canny stories")
        return stories
    
    async def _extract_single_canny_story(
        self, 
        post: Dict[str, Any], 
        options: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract a single customer story from a Canny post."""
        try:
            title = post.get('title', '')
            details = post.get('details', '')
            
            if not title and not details:
                return None
            
            # Combine title and details
            full_text = f"{title}\n{details}".strip()
            
            # Extract story elements
            story_elements = self._extract_story_elements(full_text)
            
            # Identify emotional tone
            emotional_tone = self._identify_emotional_tone(full_text)
            
            # Identify post type
            post_type = self._identify_canny_post_type(full_text)
            
            # Generate story summary
            story_summary = await self._generate_canny_story_summary(full_text, options)
            
            return {
                'post_id': post.get('id'),
                'title': title,
                'details': details,
                'full_text': full_text,
                'story_elements': story_elements,
                'emotional_tone': emotional_tone,
                'post_type': post_type,
                'story_summary': story_summary,
                'canny_url': post.get('url', ''),
                'score': post.get('score', 0),
                'status': post.get('status', 'open'),
                'created': post.get('created'),
                'author': post.get('author', {}).get('name', 'Anonymous')
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract Canny story: {e}")
            return None
    
    def _identify_canny_post_type(self, text: str) -> str:
        """Identify the type of Canny post based on content."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['bug', 'error', 'broken', 'not working', 'issue']):
            return 'bug_report'
        elif any(word in text_lower for word in ['feature', 'add', 'new', 'want', 'need']):
            return 'feature_request'
        elif any(word in text_lower for word in ['improve', 'better', 'enhance', 'optimize']):
            return 'improvement_request'
        elif any(word in text_lower for word in ['question', 'how', 'what', 'why', 'help']):
            return 'question'
        else:
            return 'general_feedback'
    
    async def _generate_canny_story_summary(
        self, 
        post_text: str, 
        options: Dict[str, Any]
    ) -> str:
        """Generate a story summary for a Canny post."""
        try:
            prompt = f"""Analyze this customer feedback and extract the key story elements:

{post_text}

Provide a brief story summary (2-3 sentences) that captures:
1. What the customer is asking for or reporting
2. Why this matters to them
3. The context or use case they're describing
4. The emotional tone of their request

Focus on the customer's perspective and needs."""

            summary = await self.openai_client.generate_analysis(prompt)
            return summary
            
        except Exception as e:
            self.logger.warning(f"Failed to generate Canny story summary: {e}")
            return "Story summary generation failed"
    
    def _identify_emotional_patterns(
        self, 
        conversation_stories: List[Dict[str, Any]], 
        canny_stories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Identify emotional patterns across all stories."""
        all_emotional_scores = {
            'frustration': 0,
            'excitement': 0,
            'confusion': 0,
            'satisfaction': 0,
            'urgency': 0,
            'gratitude': 0
        }
        
        # Aggregate emotional scores from conversations
        for story in conversation_stories:
            emotional_tone = story.get('emotional_tone', {})
            emotional_scores = emotional_tone.get('emotional_scores', {})
            for emotion, score in emotional_scores.items():
                if emotion in all_emotional_scores:
                    all_emotional_scores[emotion] += score
        
        # Aggregate emotional scores from Canny posts
        for story in canny_stories:
            emotional_tone = story.get('emotional_tone', {})
            emotional_scores = emotional_tone.get('emotional_scores', {})
            for emotion, score in emotional_scores.items():
                if emotion in all_emotional_scores:
                    all_emotional_scores[emotion] += score
        
        # Calculate percentages
        total_emotions = sum(all_emotional_scores.values())
        emotional_percentages = {}
        if total_emotions > 0:
            for emotion, score in all_emotional_scores.items():
                emotional_percentages[emotion] = (score / total_emotions) * 100
        
        return {
            'emotional_scores': all_emotional_scores,
            'emotional_percentages': emotional_percentages,
            'dominant_emotions': sorted(
                all_emotional_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
        }
    
    def _extract_journey_moments(
        self, 
        conversation_stories: List[Dict[str, Any]], 
        canny_stories: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Extract key moments in the customer journey."""
        journey_moments = {
            'onboarding': [],
            'learning': [],
            'troubleshooting': [],
            'expansion': [],
            'churn_risk': [],
            'ongoing_use': []
        }
        
        # Categorize conversation stories by journey stage
        for story in conversation_stories:
            journey_stage = story.get('journey_stage', 'ongoing_use')
            if journey_stage in journey_moments:
                journey_moments[journey_stage].append(story)
        
        return journey_moments
    
    async def _identify_recurring_themes(
        self, 
        conversation_stories: List[Dict[str, Any]], 
        canny_stories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify recurring themes across all stories."""
        # This would use AI to identify common themes
        # For now, return a placeholder structure
        return [
            {
                'theme': 'Customer onboarding challenges',
                'frequency': 15,
                'description': 'Customers struggling with initial setup and getting started',
                'examples': ['First-time user confusion', 'Onboarding process complexity']
            },
            {
                'theme': 'Feature discovery and learning',
                'frequency': 12,
                'description': 'Customers seeking help to understand and use features',
                'examples': ['How-to questions', 'Feature explanation requests']
            }
        ]
    
    async def _generate_story_insights(
        self,
        conversation_stories: List[Dict[str, Any]],
        canny_stories: List[Dict[str, Any]],
        emotional_patterns: Dict[str, Any],
        recurring_themes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate insights from the story analysis."""
        try:
            # Create a comprehensive prompt for insight generation
            prompt = StoryDrivenPrompts.get_insight_extraction_prompt(
                conversation_stories,
                canny_stories,
                "Current Analysis Period"
            )
            
            insights = await self.openai_client.generate_analysis(prompt)
            
            return {
                'insights_text': insights,
                'emotional_patterns': emotional_patterns,
                'recurring_themes': recurring_themes,
                'story_count': len(conversation_stories) + len(canny_stories)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate story insights: {e}")
            return {'error': f'Story insights generation failed: {e}'}
    
    async def _create_narrative_synthesis(
        self,
        conversation_stories: List[Dict[str, Any]],
        canny_stories: List[Dict[str, Any]],
        analysis_period: str
    ) -> str:
        """Create a narrative synthesis of all customer stories."""
        try:
            # Prepare data for narrative synthesis
            intercom_data = f"Conversation stories: {len(conversation_stories)} stories"
            canny_data = f"Canny feedback stories: {len(canny_stories)} stories"
            
            prompt = StoryDrivenPrompts.get_narrative_synthesis_prompt(
                intercom_data,
                canny_data,
                analysis_period
            )
            
            narrative = await self.openai_client.generate_analysis(prompt)
            return narrative
            
        except Exception as e:
            self.logger.error(f"Failed to create narrative synthesis: {e}")
            return f"Narrative synthesis generation failed: {e}"
    
    async def _log_chatgpt_analysis(
        self,
        story_insights: Dict[str, Any],
        narrative_synthesis: str,
        analysis_period: str
    ) -> Dict[str, Any]:
        """Log ChatGPT analysis before sending to Gamma API."""
        try:
            analysis_log = {
                'timestamp': datetime.now().isoformat(),
                'analysis_period': analysis_period,
                'story_insights': story_insights,
                'narrative_synthesis': narrative_synthesis,
                'model_used': 'gpt-4',
                'analysis_type': 'story_driven_customer_experience'
            }
            
            # Log the analysis
            self.logger.info(f"ChatGPT analysis logged for {analysis_period}")
            self.logger.debug(f"Analysis log: {json.dumps(analysis_log, indent=2)}")
            
            return analysis_log
            
        except Exception as e:
            self.logger.error(f"Failed to log ChatGPT analysis: {e}")
            return {'error': f'Analysis logging failed: {e}'}
    
    def _generate_intercom_url(self, conversation_id: str) -> str:
        """Generate Intercom conversation URL."""
        from config.settings import settings
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or not conversation_id:
            return ""
        
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"