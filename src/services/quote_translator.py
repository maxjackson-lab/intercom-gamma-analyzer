"""
Simple quote translation service for multi-language customer quotes.
Uses OpenAI for translation to keep it simple and accurate.
"""

import logging
from typing import Dict, Optional
from src.services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class QuoteTranslator:
    """Translates customer quotes to English for better analysis visibility."""
    
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.logger = logging.getLogger(__name__)
        
        # Cache translations to avoid re-translating same text
        self.translation_cache = {}
    
    async def translate_quote(self, text: str, source_language: Optional[str] = None) -> Dict[str, str]:
        """
        Translate a quote to English if it's in a foreign language.
        
        Args:
            text: The quote text to translate
            source_language: Optional language code (e.g., 'es', 'fr')
            
        Returns:
            Dict with 'original', 'translation', 'language'
        """
        # Check cache first
        cache_key = f"{source_language}:{text[:100]}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]
        
        # Skip if already English or very short
        if source_language and source_language.lower() in ['en', 'english']:
            return {
                'original': text,
                'translation': None,
                'language': 'English',
                'needs_translation': False
            }
        
        if len(text.strip()) < 10:
            return {
                'original': text,
                'translation': None,
                'language': source_language or 'Unknown',
                'needs_translation': False
            }
        
        try:
            # Use GPT to translate
            prompt = f"""Translate this customer quote to English. If it's already in English, just return it unchanged.

Original quote: "{text}"

Provide:
1. The translation in English
2. The detected source language

Format your response as:
TRANSLATION: [English translation here]
LANGUAGE: [Language name]"""
            
            response = await self.openai_client.generate_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse response
            response_text = response['content']
            
            translation = None
            language = source_language or 'Unknown'
            
            # Extract translation
            if 'TRANSLATION:' in response_text:
                translation = response_text.split('TRANSLATION:')[1].split('LANGUAGE:')[0].strip()
            
            # Extract language
            if 'LANGUAGE:' in response_text:
                language = response_text.split('LANGUAGE:')[1].strip()
            
            result = {
                'original': text,
                'translation': translation if translation != text else None,
                'language': language,
                'needs_translation': translation is not None and translation != text
            }
            
            # Cache the result
            self.translation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Translation failed: {e}")
            return {
                'original': text,
                'translation': None,
                'language': source_language or 'Unknown',
                'needs_translation': False,
                'error': str(e)
            }
    
    def get_language_from_conversation(self, conv: Dict) -> str:
        """Extract language from conversation custom attributes."""
        lang = conv.get('custom_attributes', {}).get('Language', 'English')
        return lang if lang else 'English'
    
    def calculate_language_breakdown(self, conversations: list) -> Dict[str, int]:
        """
        Calculate language breakdown for a list of conversations.
        
        Returns:
            Dict mapping language names to conversation counts
        """
        language_counts = {}
        
        for conv in conversations:
            lang = self.get_language_from_conversation(conv)
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Sort by count descending
        sorted_languages = dict(sorted(
            language_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        return sorted_languages

