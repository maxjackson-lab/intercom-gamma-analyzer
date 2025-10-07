"""
Text analysis and keyword extraction from Intercom conversations.
"""

import yake
import re
import logging
from collections import Counter
from typing import List, Dict, Tuple, Optional, Any
import html

logger = logging.getLogger(__name__)

class TextAnalyzer:
    """Text analyzer with YAKE keyword extraction and conversation processing."""
    
    def __init__(
        self,
        language: str = "en",
        max_ngram_size: int = 3,
        deduplication_threshold: float = 0.9,
        num_keywords: int = 20,
        min_keyword_length: int = 3
    ):
        """
        Initialize text analyzer with YAKE keyword extractor.
        
        Args:
            language: Language code (en, es, fr, etc.)
            max_ngram_size: Maximum number of words in a keyword
            deduplication_threshold: Similarity threshold for duplicate removal
            num_keywords: Number of keywords to extract per text
            min_keyword_length: Minimum length for keywords
        """
        self.language = language
        self.max_ngram_size = max_ngram_size
        self.deduplication_threshold = deduplication_threshold
        self.num_keywords = num_keywords
        self.min_keyword_length = min_keyword_length
        
        try:
            self.kw_extractor = yake.KeywordExtractor(
                lan=language,
                n=max_ngram_size,
                dedupLim=deduplication_threshold,
                top=num_keywords,
                features=None
            )
            logger.info("YAKE keyword extractor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YAKE extractor: {e}")
            raise
            
    def extract_keywords(self, text: str) -> List[Tuple[str, float]]:
        """
        Extract keywords from text using YAKE.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of (keyword, score) tuples (lower score = more relevant)
        """
        if not text or not text.strip():
            return []
            
        try:
            # Clean and preprocess text
            cleaned_text = self._preprocess_text(text)
            if not cleaned_text:
                return []
                
            keywords = self.kw_extractor.extract_keywords(cleaned_text)
            
            # Filter keywords by minimum length
            filtered_keywords = [
                (kw, score) for kw, score in keywords 
                if len(kw) >= self.min_keyword_length
            ]
            
            logger.debug(f"Extracted {len(filtered_keywords)} keywords from text")
            return filtered_keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
            
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for keyword extraction.
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
            
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
        
        return text.strip()
        
    def extract_conversation_body(self, conversation: Dict) -> str:
        """
        Extract all text content from conversation object.
        
        Args:
            conversation: Intercom conversation object
            
        Returns:
            Combined text from conversation
        """
        texts = []
        
        try:
            # Get source body (initial message)
            source = conversation.get('source', {})
            body = source.get('body', '')
            if body:
                texts.append(self._clean_html(body))
                
            # Get conversation parts (replies)
            parts = conversation.get('conversation_parts', {})
            part_list = parts.get('conversation_parts', [])
            
            for part in part_list:
                part_body = part.get('body', '')
                if part_body:
                    texts.append(self._clean_html(part_body))
                    
            # Get notes if available
            notes = conversation.get('notes', {})
            note_list = notes.get('notes', [])
            
            for note in note_list:
                note_body = note.get('body', '')
                if note_body:
                    texts.append(self._clean_html(note_body))
                    
        except Exception as e:
            logger.error(f"Error extracting conversation body: {e}")
            
        return ' '.join(texts)
        
    def _clean_html(self, text: str) -> str:
        """
        Remove HTML tags and clean text.
        
        Args:
            text: Text with potential HTML
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
            
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    def analyze_conversations(
        self, 
        conversations: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Perform aggregate analysis on conversations.
        
        Args:
            conversations: List of Intercom conversation objects
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with analysis results
        """
        all_keywords = []
        keyword_counter = Counter()
        conversation_keywords = []
        processed_count = 0
        
        logger.info(f"Starting analysis of {len(conversations)} conversations")
        
        for i, conv in enumerate(conversations):
            try:
                text = self.extract_conversation_body(conv)
                if text:
                    keywords = self.extract_keywords(text)
                    
                    # Track keywords with scores
                    conv_keywords = []
                    for kw, score in keywords:
                        all_keywords.append((kw, score))
                        keyword_counter[kw] += 1
                        conv_keywords.append((kw, score))
                        
                    conversation_keywords.append({
                        'conversation_id': conv.get('id'),
                        'keywords': conv_keywords,
                        'text_length': len(text)
                    })
                    
                processed_count += 1
                
                # Progress callback
                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(processed_count, len(conversations))
                    
            except Exception as e:
                logger.error(f"Error analyzing conversation {conv.get('id', 'unknown')}: {e}")
                continue
                
        # Get most common keywords
        top_keywords = keyword_counter.most_common(50)
        
        # Calculate statistics
        total_text_length = sum(conv.get('text_length', 0) for conv in conversation_keywords)
        avg_text_length = total_text_length / len(conversation_keywords) if conversation_keywords else 0
        
        results = {
            "total_conversations": len(conversations),
            "processed_conversations": processed_count,
            "top_keywords": top_keywords,
            "all_keywords_with_scores": all_keywords,
            "unique_keywords": len(keyword_counter),
            "conversation_keywords": conversation_keywords,
            "total_text_length": total_text_length,
            "average_text_length": avg_text_length,
            "analysis_settings": {
                "language": self.language,
                "max_ngram_size": self.max_ngram_size,
                "num_keywords": self.num_keywords,
                "min_keyword_length": self.min_keyword_length
            }
        }
        
        logger.info(f"Analysis complete: {processed_count} conversations processed, "
                   f"{len(keyword_counter)} unique keywords found")
        
        return results
        
    def find_keyword_context(
        self, 
        conversations: List[Dict], 
        keyword: str,
        context_window: int = 50
    ) -> List[Dict]:
        """
        Find conversations containing a specific keyword with context.
        
        Args:
            conversations: List of conversation objects
            keyword: Keyword to search for
            context_window: Number of characters around keyword to include
            
        Returns:
            List of conversations with keyword context
        """
        results = []
        keyword_lower = keyword.lower()
        
        for conv in conversations:
            text = self.extract_conversation_body(conv)
            if keyword_lower in text.lower():
                # Find keyword position and extract context
                text_lower = text.lower()
                pos = text_lower.find(keyword_lower)
                
                if pos != -1:
                    start = max(0, pos - context_window)
                    end = min(len(text), pos + len(keyword) + context_window)
                    context = text[start:end]
                    
                    results.append({
                        'conversation_id': conv.get('id'),
                        'keyword': keyword,
                        'context': context,
                        'position': pos,
                        'full_text_length': len(text)
                    })
                    
        logger.info(f"Found {len(results)} conversations containing keyword '{keyword}'")
        return results
        
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract basic entities from text (emails, URLs, phone numbers).
        
        Args:
            text: Input text
            
        Returns:
            Dict with extracted entities
        """
        entities = {
            'emails': [],
            'urls': [],
            'phone_numbers': []
        }
        
        if not text:
            return entities
            
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['emails'] = re.findall(email_pattern, text)
        
        # Extract URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        entities['urls'] = re.findall(url_pattern, text)
        
        # Extract phone numbers (basic pattern)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        entities['phone_numbers'] = re.findall(phone_pattern, text)
        
        return entities


