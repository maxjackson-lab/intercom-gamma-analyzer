"""
Voice of Customer analyzer for sentiment analysis and trend detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict

from src.services.ai_model_factory import AIModelFactory, AIModel
from src.services.agent_feedback_separator import AgentFeedbackSeparator

logger = logging.getLogger(__name__)


class VoiceOfCustomerAnalyzer:
    """Main Voice of Customer analyzer for sentiment analysis and insights."""
    
    def __init__(
        self, 
        ai_model_factory: AIModelFactory,
        agent_separator: AgentFeedbackSeparator,
        historical_manager: Optional[Any] = None  # Deprecated: HistoricalDataManager removed
    ):
        self.ai_model_factory = ai_model_factory
        self.agent_separator = agent_separator
        self.historical_manager = historical_manager  # Optional - deprecated, will be removed
        self.logger = logging.getLogger(__name__)
        
        if historical_manager is not None:
            self.logger.warning("HistoricalDataManager is deprecated and will be removed. Historical trends disabled.")
        
        self.logger.info("VoiceOfCustomerAnalyzer initialized")
    
    async def analyze_weekly_sentiment(
        self, 
        conversations: List[Dict],
        ai_model: AIModel = AIModel.OPENAI_GPT4,
        enable_fallback: bool = True,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment for top volume categories.
        
        Args:
            conversations: List of conversations to analyze
            ai_model: Which AI model to use (openai or claude)
            enable_fallback: If True, use other model if primary fails
            options: Additional options (include_trends, etc.)
        
        Returns:
            Comprehensive VoC analysis results
        """
        self.logger.info(
            f"Starting VoC analysis with {len(conversations)} conversations "
            f"using {ai_model.value}"
        )
        
        start_time = datetime.now()
        options = options or {}
        
        # Get top categories by volume using taxonomy
        top_categories = await self._get_top_categories_by_volume(conversations, ai_model)
        
        results = {}
        for category, category_conversations in top_categories.items():
            self.logger.info(f"Analyzing {category}: {len(category_conversations)} conversations")
            
            # Extract actual conversations from wrapped dict format
            actual_conversations = [
                item['conversation'] if isinstance(item, dict) and 'conversation' in item else item
                for item in category_conversations
            ]
            
            # Analyze sentiment using selected AI model
            sentiment_analysis = await self._analyze_category_sentiment(
                actual_conversations, 
                ai_model,
                enable_fallback
            )
            
            # Select representative examples with Intercom URLs
            representative_examples = await self._select_representative_examples(
                actual_conversations,
                sentiment_analysis,
                target_count=7
            )
            
            results[category] = {
                'volume': len(actual_conversations),
                'sentiment_breakdown': sentiment_analysis,
                'examples': representative_examples,
                'agent_breakdown': self._get_agent_breakdown(actual_conversations),
                'language_breakdown': self._get_language_breakdown(actual_conversations)
            }
        
        # Include trends if requested
        if options.get('include_trends', False):
            trends = self._get_historical_trends()
            results['_trends'] = trends
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        analysis_results = {
            'results': results,
            'metadata': {
                'ai_model': ai_model.value,
                'execution_time_seconds': execution_time,
                'total_conversations': len(conversations),
                'categories_analyzed': len(results),
                'analysis_date': datetime.now().isoformat()
            }
        }
        
        # Store historical snapshot
        await self._store_historical_snapshot(analysis_results)
        
        self.logger.info(f"VoC analysis completed in {execution_time:.2f}s")
        return analysis_results
    
    async def _analyze_category_sentiment(
        self, 
        conversations: List[Dict],
        ai_model: AIModel,
        enable_fallback: bool
    ) -> Dict[str, Any]:
        """Analyze sentiment for a category."""
        # First, try to extract sentiment from Intercom custom attributes
        sentiment_from_attrs = self._extract_sentiment_from_attributes(conversations)
        
        if sentiment_from_attrs['coverage'] > 0.8:  # 80%+ have attributes
            self.logger.info("Using Intercom custom attributes for sentiment")
            return sentiment_from_attrs
        
        # Fallback to AI analysis
        self.logger.info(f"Using AI analysis ({ai_model.value})")
        combined_text = self._combine_conversation_texts(conversations)
        
        result = await self.ai_model_factory.analyze_sentiment(
            text=combined_text,
            language='auto',
            model=ai_model,
            fallback=enable_fallback
        )
        
        return {
            'sentiment': result['sentiment'],
            'confidence': result['confidence'],
            'analysis': result['analysis'],
            'emotional_indicators': result.get('emotional_indicators', []),
            'source': 'ai_analysis',
            'model_used': result.get('model_used', ai_model.value)
        }
    
    def _extract_sentiment_from_attributes(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Extract sentiment from Intercom custom attributes."""
        sentiments = []
        cx_scores = []
        explanations = []
        
        for conv in conversations:
            custom_attrs = conv.get('custom_attributes', {})
            
            if 'User Sentiment' in custom_attrs:
                sentiments.append(custom_attrs['User Sentiment'])
            
            if 'CX Score rating' in custom_attrs:
                try:
                    cx_scores.append(float(custom_attrs['CX Score rating']))
                except (ValueError, TypeError):
                    pass
            
            if 'CX Score explanation' in custom_attrs:
                explanations.append(custom_attrs['CX Score explanation'])
        
        # Calculate sentiment distribution
        sentiment_counts = Counter(sentiments)
        total_sentiments = len(sentiments)
        
        sentiment_breakdown = {}
        if total_sentiments > 0:
            for sentiment, count in sentiment_counts.items():
                sentiment_breakdown[sentiment] = {
                    'count': count,
                    'percentage': round(count / total_sentiments * 100, 2)
                }
        
        # Calculate average CX score
        avg_cx_score = sum(cx_scores) / len(cx_scores) if cx_scores else None
        
        return {
            'sentiment_breakdown': sentiment_breakdown,
            'average_cx_score': avg_cx_score,
            'cx_explanations': explanations[:5],  # Top 5 explanations
            'coverage': total_sentiments / len(conversations) if conversations else 0,
            'source': 'intercom_attributes'
        }
    
    def _combine_conversation_texts(self, conversations: List[Dict]) -> str:
        """Combine conversation texts for AI analysis."""
        texts = []
        
        for conv in conversations:
            # Extract from conversation parts
            if 'conversation_parts' in conv:
                parts = conv['conversation_parts']
                if isinstance(parts, dict) and 'conversation_parts' in parts:
                    parts = parts['conversation_parts']
                
                for part in parts:
                    if isinstance(part, dict) and 'body' in part:
                        texts.append(part['body'])
            
            # Extract from source
            # Safe nested access
            body = conv.get('source', {}).get('body')
            if body:
                texts.append(body)
        
        return ' '.join(texts[:10])  # Limit to first 10 conversations to avoid token limits
    
    async def _get_top_categories_by_volume(self, conversations: List[Dict], ai_model: AIModel) -> Dict[str, List[Dict]]:
        """Get top categories by conversation volume using taxonomy system."""
        from src.config.taxonomy import taxonomy_manager
        
        category_counts = defaultdict(list)
        unclassified = []
        
        self.logger.info(f"Classifying {len(conversations)} conversations using taxonomy system")
        
        for conv in conversations:
            # Try taxonomy classification first
            classifications = taxonomy_manager.classify_conversation(conv)
            
            if classifications and classifications[0]['confidence'] >= 0.5:
                # Use highest confidence classification
                top_classification = classifications[0]
                category_name = top_classification['category']
                
                category_counts[category_name].append({
                    'conversation': conv,
                    'subcategory': top_classification['subcategory'],
                    'confidence': top_classification['confidence'],
                    'method': top_classification['method']
                })
            else:
                unclassified.append(conv)
        
        # AI classification for unclassified (emerging trends)
        if unclassified and len(unclassified) >= 5:
            self.logger.info(f"Detecting emerging trends in {len(unclassified)} unclassified conversations")
            emerging_categories = await self._detect_emerging_categories(unclassified, ai_model)
            
            for cat_name, cat_convs in emerging_categories.items():
                category_counts[f"Emerging: {cat_name}"].extend(cat_convs)
        elif unclassified:
            # Put remaining unclassified in Unknown category
            for conv in unclassified:
                category_counts['Unknown'].append({
                    'conversation': conv,
                    'subcategory': 'Unclassified',
                    'confidence': 0.0,
                    'method': 'fallback'
                })
        
        # Sort by volume and return top categories
        sorted_categories = sorted(
            category_counts.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )
        
        # Return top 10 categories or all if less than 10
        top_categories = dict(sorted_categories[:10])
        
        self.logger.info(f"Top categories by volume: {[(k, len(v)) for k, v in top_categories.items()]}")
        return top_categories
    
    async def _detect_emerging_categories(
        self, 
        unclassified_conversations: List[Dict],
        ai_model: AIModel
    ) -> Dict[str, List[Dict]]:
        """
        Use AI to detect emerging categories not in taxonomy.
        
        Strategy:
        1. Sample conversations (max 50 for performance)
        2. Use AI to identify common themes
        3. Group conversations by detected themes
        4. Return with confidence scores
        """
        import random
        import json
        
        if len(unclassified_conversations) < 5:
            return {}
        
        # Sample conversations for AI analysis
        sample_size = min(50, len(unclassified_conversations))
        sample = random.sample(unclassified_conversations, sample_size)
        
        # Extract text snippets from sampled conversations
        conversation_texts = []
        for i, conv in enumerate(sample):
            # Safe nested access
            text = conv.get('source', {}).get('body', '')[:200]  # First 200 chars
            conversation_texts.append(f"{i+1}. {text}")
        
        combined_text = "\n".join(conversation_texts)
        
        # Prepare prompt for AI
        prompt = f"""Analyze these {sample_size} customer support conversations that don't fit existing categories.
Identify 2-4 emerging themes or patterns.

Conversations:
{combined_text}

For each theme, provide:
- theme_name: Short name (2-4 words)
- description: Brief description (1 sentence)
- confidence: Float between 0 and 1
- conversation_indices: List of conversation numbers (1-{sample_size}) that match this theme

Return ONLY valid JSON in this exact format:
{{"themes": [{{"theme_name": "Example Theme", "description": "Description here", "confidence": 0.85, "conversation_indices": [1, 3, 5]}}]}}"""
        
        try:
            # Call AI model
            client = self.ai_model_factory.get_client(ai_model)
            
            # Use sentiment analysis method as a proxy for theme detection
            result = await client.analyze_sentiment_multilingual(prompt, language='en')
            
            # Try to parse JSON from the response with robust extraction
            analysis_text = result.get('analysis', '{}')

            # Try to extract JSON from fenced code blocks first
            import re
            json_fence_pattern = r'```json\s*(\{[\s\S]*?\})\s*```'
            fence_match = re.search(json_fence_pattern, analysis_text)

            if fence_match:
                json_str = fence_match.group(1)
            else:
                # Fallback: Find JSON braces
                start_idx = analysis_text.find('{')
                end_idx = analysis_text.rfind('}') + 1

                if start_idx >= 0 and end_idx > start_idx:
                    json_str = analysis_text[start_idx:end_idx]
                else:
                    self.logger.warning("Could not extract JSON from AI response for emerging trends")
                    return {}

            try:
                themes_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON from AI response: {e}. Raw text: {json_str[:200]}")
                return {}
            
            # Group conversations by detected themes
            theme_groups = defaultdict(list)
            
            for theme in themes_data.get('themes', []):
                theme_name = theme.get('theme_name', 'Unknown Theme')
                confidence = theme.get('confidence', 0.5)
                indices = theme.get('conversation_indices', [])
                
                # Map indices back to actual conversations
                for idx in indices:
                    if 0 < idx <= len(sample):
                        conv = sample[idx - 1]
                        theme_groups[theme_name].append({
                            'conversation': conv,
                            'subcategory': 'Emerging',
                            'confidence': confidence,
                            'method': 'ai_emerging_trend'
                        })
            
            self.logger.info(f"Detected {len(theme_groups)} emerging themes")
            return dict(theme_groups)
            
        except Exception as e:
            self.logger.error(f"Failed to detect emerging trends: {e}")
            return {}
    
    async def _select_representative_examples(
        self,
        conversations: List[Dict],
        sentiment_analysis: Dict,
        target_count: int = 7
    ) -> Dict[str, List[Dict]]:
        """
        Select 3-10 most representative conversation examples with Intercom URLs.
        
        Strategy:
        1. Score each conversation for quality (clarity, readability)
        2. Stratify by sentiment type
        3. Generate Intercom URLs
        4. Return diverse, high-quality examples
        """
        if len(conversations) <= target_count:
            return self._format_all_examples_with_urls(conversations)
        
        # Score each conversation
        scored_conversations = []
        for conv in conversations:
            score = self._score_conversation_quality(conv, sentiment_analysis)
            scored_conversations.append((score, conv))
        
        # Sort by score
        scored_conversations.sort(reverse=True, key=lambda x: x[0])
        
        # Select diverse examples (stratified by different aspects)
        selected = scored_conversations[:target_count]
        
        # Format with Intercom URLs
        examples_by_sentiment = defaultdict(list)
        
        for score, conv in selected:
            quote = self._extract_quote(conv)
            if not quote or len(quote) < 10:
                continue
                
            sentiment_type = self._determine_conversation_sentiment(conv)
            
            examples_by_sentiment[sentiment_type].append({
                'text': quote,
                'conversation_id': conv.get('id'),
                'intercom_url': self._generate_intercom_url(conv.get('id')),
                'confidence': score
            })
        
        return dict(examples_by_sentiment)
    
    def _score_conversation_quality(self, conversation: Dict, sentiment_analysis: Dict) -> float:
        """Score conversation quality for selection."""
        score = 0.5  # Base score
        
        # Check if conversation has clear content (safe access)
        body = conversation.get('source', {}).get('body')
        if body:
            
            # Length (not too short, not too long)
            if 50 < len(body) < 500:
                score += 0.2
            
            # Has clear sentiment indicators
            sentiment = sentiment_analysis.get('sentiment', 'neutral')
            positive_words = ['great', 'thank', 'excellent', 'amazing', 'perfect', 'love']
            negative_words = ['frustrat', 'terrible', 'awful', 'disappointed', 'hate', 'broken', 'bug']
            
            body_lower = body.lower()
            
            if sentiment == 'positive' and any(word in body_lower for word in positive_words):
                score += 0.2
            elif sentiment == 'negative' and any(word in body_lower for word in negative_words):
                score += 0.2
            
            # Readable (has sentences)
            if '. ' in body or '! ' in body or '? ' in body:
                score += 0.1
        
        return min(score, 1.0)
    
    def _extract_quote(self, conversation: Dict) -> str:
        """Extract a representative quote from conversation."""
        body = conversation.get('source', {}).get('body')
        if body:
            # Limit to first 200 characters
            if len(body) > 200:
                return body[:197] + "..."
            return body
        return ""
    
    def _determine_conversation_sentiment(self, conversation: Dict) -> str:
        """Determine sentiment type for a conversation."""
        # Check custom attributes first
        custom_attrs = conversation.get('custom_attributes', {})
        if 'User Sentiment' in custom_attrs:
            sentiment = custom_attrs['User Sentiment'].lower()
            if sentiment in ['positive', 'negative', 'neutral']:
                return sentiment
        
        # Simple keyword-based fallback (safe access)
        body = conversation.get('source', {}).get('body', '').lower()
        if body:
            
            positive_words = ['great', 'thank', 'excellent', 'amazing', 'perfect', 'love']
            negative_words = ['frustrat', 'terrible', 'awful', 'disappointed', 'hate', 'broken', 'bug']
            
            positive_count = sum(1 for word in positive_words if word in body)
            negative_count = sum(1 for word in negative_words if word in body)
            
            if positive_count > negative_count:
                return 'positive'
            elif negative_count > positive_count:
                return 'negative'
        
        return 'neutral'
    
    def _generate_intercom_url(self, conversation_id: str) -> str:
        """
        Generate Intercom conversation URL.

        Correct format per Intercom docs is:
        https://app.intercom.com/a/apps/{workspace_id}/inbox/conversation/{conversation_id}
        """
        from src.config.settings import settings
        workspace_id = settings.intercom_workspace_id

        if not workspace_id or not conversation_id:
            return ""

        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/conversation/{conversation_id}"
    
    def _format_all_examples_with_urls(self, conversations: List[Dict]) -> Dict[str, List[Dict]]:
        """Format all conversations when count is small."""
        examples_by_sentiment = defaultdict(list)
        
        for conv in conversations:
            quote = self._extract_quote(conv)
            if not quote or len(quote) < 10:
                continue
                
            sentiment_type = self._determine_conversation_sentiment(conv)
            
            examples_by_sentiment[sentiment_type].append({
                'text': quote,
                'conversation_id': conv.get('id'),
                'intercom_url': self._generate_intercom_url(conv.get('id')),
                'confidence': 0.8
            })
        
        return dict(examples_by_sentiment)
    
    def _get_sentiment_examples(self, conversations: List[Dict]) -> Dict[str, List[str]]:
        """Get example quotes for each sentiment (legacy method)."""
        examples = defaultdict(list)
        
        for conv in conversations:
            # Extract sentiment from custom attributes
            custom_attrs = conv.get('custom_attributes', {})
            sentiment = custom_attrs.get('User Sentiment', 'neutral')
            
            # Extract quote from conversation
            quote = self._extract_quote_from_conversation(conv)
            if quote and len(examples[sentiment]) < 3:  # Max 3 examples per sentiment
                examples[sentiment].append(quote)
        
        return dict(examples)
    
    def _extract_quote_from_conversation(self, conversation: Dict) -> Optional[str]:
        """Extract a representative quote from conversation."""
        # Try to get the most recent customer message
        if 'conversation_parts' in conversation:
            parts = conversation['conversation_parts']
            if isinstance(parts, dict) and 'conversation_parts' in parts:
                parts = parts['conversation_parts']
            
            # Look for customer messages (reverse order to get most recent)
            for part in reversed(parts):
                if isinstance(part, dict):
                    author = part.get('author', {})
                    if isinstance(author, dict) and author.get('type') == 'user':
                        body = part.get('body', '')
                        if body and len(body) > 20:  # Meaningful quote
                            return body[:200] + '...' if len(body) > 200 else body
        
        return None
    
    def _get_agent_breakdown(self, conversations: List[Dict]) -> Dict[str, int]:
        """Get agent breakdown for conversations."""
        separated = self.agent_separator.separate_by_agent_type(conversations)
        return {agent_type: len(convs) for agent_type, convs in separated.items() if convs}
    
    def _get_language_breakdown(self, conversations: List[Dict]) -> Dict[str, int]:
        """Get language breakdown for conversations."""
        languages = []
        
        for conv in conversations:
            custom_attrs = conv.get('custom_attributes', {})
            language = custom_attrs.get('Language', 'unknown')
            languages.append(language)
        
        return dict(Counter(languages))
    
    def _get_historical_trends(self) -> Dict[str, Any]:
        """Get historical trends for comparison."""
        # Deprecated: HistoricalDataManager removed - return empty trends
        self.logger.debug("Historical trends disabled (HistoricalDataManager deprecated)")
        return {
            'trends': {},
            'insights': ['Historical trends unavailable (deprecated HistoricalDataManager removed)'],
            'periods_analyzed': 0
        }
    
    async def _store_historical_snapshot(self, analysis_results: Dict[str, Any]):
        """Store current analysis as historical snapshot."""
        # Deprecated: HistoricalDataManager removed - no-op
        self.logger.debug("Historical snapshot storage disabled (HistoricalDataManager deprecated)")
    
    def generate_insights(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from analysis results."""
        insights = []
        results = analysis_results.get('results', {})
        
        # Volume insights
        total_volume = sum(data.get('volume', 0) for data in results.values())
        if total_volume > 0:
            top_category = max(results.items(), key=lambda x: x[1].get('volume', 0))
            insights.append(f"Top volume category: {top_category[0]} ({top_category[1]['volume']} conversations)")
        
        # Sentiment insights
        for category, data in results.items():
            sentiment_data = data.get('sentiment_breakdown', {})
            if isinstance(sentiment_data, dict) and 'sentiment' in sentiment_data:
                sentiment = sentiment_data['sentiment']
                confidence = sentiment_data.get('confidence', 0)
                
                if sentiment == 'negative' and confidence > 0.7:
                    insights.append(f"High negative sentiment in {category} (confidence: {confidence:.2f})")
                elif sentiment == 'positive' and confidence > 0.8:
                    insights.append(f"Strong positive sentiment in {category} (confidence: {confidence:.2f})")
        
        # Agent insights
        for category, data in results.items():
            agent_breakdown = data.get('agent_breakdown', {})
            if agent_breakdown and 'counts' in agent_breakdown:
                counts = agent_breakdown['counts']
                if counts:
                    top_agent = max(counts.items(), key=lambda x: x[1])
                    insights.append(f"{category} primarily handled by {top_agent[0]} ({top_agent[1]} conversations)")
        
        return insights
