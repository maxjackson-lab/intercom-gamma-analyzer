"""
Data Preprocessor Service for Intercom Analysis Tool.
Handles data validation, normalization, and missing data with confidence levels.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple, Set
from pathlib import Path
import json

from src.config.settings import settings
from src.models.analysis_models import ConversationSchema
from src.utils.conversation_utils import extract_conversation_text, extract_customer_messages

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Comprehensive data preprocessor with confidence-based missing data handling.
    
    Features:
    - Data validation and normalization
    - Missing data inference with confidence levels
    - Deduplication and outlier detection
    - Text cleaning and standardization
    - Statistical sampling for large datasets
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize data preprocessor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Confidence thresholds
        self.high_confidence_threshold = 0.8
        self.medium_confidence_threshold = 0.6
        self.low_confidence_threshold = 0.4
        
        # Text cleaning patterns
        self.html_pattern = re.compile(r'<[^>]+>')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Common technical terms for inference
        self.technical_keywords = {
            'cache': ['cache', 'cached', 'clearing cache', 'clear cache'],
            'browser': ['browser', 'chrome', 'firefox', 'safari', 'edge'],
            'connection': ['connection', 'internet', 'network', 'connectivity'],
            'export': ['export', 'exporting', 'download', 'csv', 'excel'],
            'api': ['api', 'endpoint', 'request', 'response', 'authentication'],
            'billing': ['billing', 'invoice', 'payment', 'subscription', 'refund'],
            'account': ['account', 'login', 'password', 'sign in', 'authentication']
        }
        
        self.logger.info("Initialized DataPreprocessor with confidence-based inference")
    
    def preprocess_conversations(
        self, 
        conversations: List[Dict[str, Any]], 
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Preprocess a list of conversations with comprehensive validation and inference.
        
        Args:
            conversations: Raw conversation data
            options: Preprocessing options
            
        Returns:
            Tuple of (processed_conversations, preprocessing_stats)
        """
        self.logger.info(f"Starting preprocessing of {len(conversations)} conversations")
        
        options = options or {}
        stats = {
            "original_count": len(conversations),
            "processed_count": 0,
            "deduplicated_count": 0,
            "inferred_data": {},
            "validation_errors": [],
            "confidence_levels": {"high": 0, "medium": 0, "low": 0, "none": 0}
        }
        
        try:
            # Step 1: Validate and normalize
            validated_conversations = self._validate_conversations(conversations, stats)
            self.logger.info(f"Validation completed: {len(validated_conversations)} valid conversations")
            
            # Step 2: Deduplicate
            if options.get('deduplicate', True):
                deduplicated_conversations = self._deduplicate_conversations(validated_conversations, stats)
                self.logger.info(f"Deduplication completed: {len(deduplicated_conversations)} unique conversations")
            else:
                deduplicated_conversations = validated_conversations
            
            # Step 3: Infer missing data
            if options.get('infer_missing', True):
                processed_conversations = self._infer_missing_data(deduplicated_conversations, stats)
                self.logger.info(f"Missing data inference completed")
            else:
                processed_conversations = deduplicated_conversations
            
            # Step 4: Clean and standardize text
            if options.get('clean_text', True):
                processed_conversations = self._clean_conversation_text(processed_conversations, stats)
                self.logger.info(f"Text cleaning completed")
            
            # Step 5: Detect outliers
            if options.get('detect_outliers', True):
                processed_conversations = self._detect_outliers(processed_conversations, stats)
                self.logger.info(f"Outlier detection completed")
            
            # Step 6: Statistical sampling (if needed)
            if options.get('max_conversations') and len(processed_conversations) > options['max_conversations']:
                processed_conversations = self._statistical_sampling(
                    processed_conversations, 
                    options['max_conversations'], 
                    stats
                )
                self.logger.info(f"Statistical sampling completed: {len(processed_conversations)} conversations")
            
            stats["processed_count"] = len(processed_conversations)
            
            self.logger.info(f"Preprocessing completed: {stats['processed_count']} conversations processed")
            return processed_conversations, stats
            
        except Exception as e:
            self.logger.error(f"Preprocessing failed: {e}", exc_info=True)
            raise PreprocessingError(f"Failed to preprocess conversations: {e}") from e
    
    def _validate_conversations(
        self, 
        conversations: List[Dict[str, Any]], 
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Validate conversation data and normalize fields.
        
        Uses ConversationSchema for validation and adds customer_messages field.
        Drops conversations without valid ID or usable text.
        """
        validated = []
        
        for i, conv in enumerate(conversations):
            try:
                # Basic validation
                if not isinstance(conv, dict):
                    stats["validation_errors"].append(f"Conversation {i}: Not a dictionary")
                    continue
                
                if not conv.get('id'):
                    stats["validation_errors"].append(f"Conversation {i}: Missing ID")
                    continue
                
                # Extract customer messages before schema validation
                # Use centralized utility from conversation_utils
                customer_messages = extract_customer_messages(conv, clean_html=True)
                conv['customer_messages'] = customer_messages
                
                # Validate with ConversationSchema
                try:
                    validated_conv = ConversationSchema(**conv)
                    
                    # Check for usable text content
                    if not validated_conv.has_usable_text():
                        stats["validation_errors"].append(
                            f"Conversation {conv.get('id')}: No usable text content (no customer messages)"
                        )
                        continue
                    
                    # Convert back to dict for downstream processing
                    conv_dict = validated_conv.dict()
                    # Preserve extra fields that were in original conv
                    for key, value in conv.items():
                        if key not in conv_dict:
                            conv_dict[key] = value
                    
                    validated.append(conv_dict)
                    
                except Exception as schema_error:
                    stats["validation_errors"].append(
                        f"Conversation {conv.get('id')}: Schema validation failed - {schema_error}"
                    )
                    continue
                    
            except Exception as e:
                self.logger.warning(f"Validation error for conversation {i}: {e}")
                stats["validation_errors"].append(f"Conversation {i}: Validation error - {e}")
                continue
        
        return validated
    
    # NOTE: _extract_customer_messages() removed - now using centralized extract_customer_messages() from conversation_utils
    
    def _normalize_timestamps(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize timestamp fields to timezone-aware UTC datetime objects (idempotent).

        This method is idempotent - if a field is already a datetime, it ensures
        it's timezone-aware UTC but doesn't re-parse it.
        """
        timestamp_fields = ['created_at', 'updated_at', 'closed_at', 'last_contact_at']

        for field in timestamp_fields:
            if field in conv and conv[field]:
                try:
                    if isinstance(conv[field], datetime):
                        # Already datetime - ensure it's timezone-aware UTC
                        if conv[field].tzinfo is None:
                            conv[field] = conv[field].replace(tzinfo=timezone.utc)
                        else:
                            conv[field] = conv[field].astimezone(timezone.utc)
                    elif isinstance(conv[field], (int, float)):
                        # Unix timestamp
                        conv[field] = datetime.fromtimestamp(conv[field], tz=timezone.utc)
                    elif isinstance(conv[field], str):
                        # ISO string
                        conv[field] = datetime.fromisoformat(conv[field].replace('Z', '+00:00'))
                except Exception as e:
                    self.logger.warning(f"Failed to normalize timestamp {field}: {e}")
                    conv[field] = None

        return conv
    
    def _normalize_custom_attributes(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize custom attributes structure."""
        if 'custom_attributes' not in conv:
            conv['custom_attributes'] = {}
        
        # Ensure custom_attributes is a dictionary
        if not isinstance(conv['custom_attributes'], dict):
            conv['custom_attributes'] = {}
        
        return conv
    
    def _validate_required_fields(self, conv: Dict[str, Any]) -> bool:
        """Validate that required fields are present."""
        required_fields = ['id', 'created_at']
        
        for field in required_fields:
            if not conv.get(field):
                return False
        
        return True
    
    def _deduplicate_conversations(
        self, 
        conversations: List[Dict[str, Any]], 
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate conversations based on ID."""
        seen_ids = set()
        deduplicated = []
        
        for conv in conversations:
            conv_id = conv.get('id')
            if conv_id and conv_id not in seen_ids:
                seen_ids.add(conv_id)
                deduplicated.append(conv)
        
        stats["deduplicated_count"] = len(conversations) - len(deduplicated)
        return deduplicated
    
    def _infer_missing_data(
        self, 
        conversations: List[Dict[str, Any]], 
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Infer missing data with confidence levels."""
        inferred_stats = {
            "categories_inferred": 0,
            "topics_inferred": 0,
            "languages_inferred": 0,
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0, "none": 0}
        }
        
        for conv in conversations:
            # Infer category from text content
            category, confidence = self._infer_category(conv)
            if category and confidence > self.low_confidence_threshold:
                conv['inferred_category'] = category
                conv['category_confidence'] = confidence
                inferred_stats["categories_inferred"] += 1
                inferred_stats["confidence_distribution"][self._get_confidence_level(confidence)] += 1
            
            # Infer topics from text content
            topics, confidence = self._infer_topics(conv)
            if topics and confidence > self.low_confidence_threshold:
                conv['inferred_topics'] = topics
                conv['topics_confidence'] = confidence
                inferred_stats["topics_inferred"] += 1
            
            # Infer language from text content
            language, confidence = self._infer_language(conv)
            if language and confidence > self.low_confidence_threshold:
                conv['inferred_language'] = language
                conv['language_confidence'] = confidence
                inferred_stats["languages_inferred"] += 1
        
        stats["inferred_data"] = inferred_stats
        return conversations
    
    def _infer_category(self, conv: Dict[str, Any]) -> Tuple[Optional[str], float]:
        """Infer conversation category from text content."""
        # Use centralized utility from conversation_utils
        text = extract_conversation_text(conv, clean_html=True).lower()
        
        # Check for technical keywords
        for category, keywords in self.technical_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > 0:
                confidence = min(0.9, 0.5 + (matches * 0.1))
                return category, confidence
        
        # Check for billing keywords
        billing_keywords = ['refund', 'invoice', 'payment', 'subscription', 'billing', 'charge']
        if any(keyword in text for keyword in billing_keywords):
            return 'billing', 0.7
        
        # Check for account keywords
        account_keywords = ['login', 'password', 'account', 'sign in', 'authentication']
        if any(keyword in text for keyword in account_keywords):
            return 'account', 0.6
        
        return None, 0.0
    
    def _infer_topics(self, conv: Dict[str, Any]) -> Tuple[List[str], float]:
        """Infer conversation topics from text content."""
        # Use centralized utility from conversation_utils
        text = extract_conversation_text(conv, clean_html=True).lower()
        topics = []
        confidence = 0.0
        
        # Simple keyword-based topic inference
        topic_keywords = {
            'export': ['export', 'download', 'csv', 'excel', 'data export'],
            'api': ['api', 'endpoint', 'request', 'response', 'authentication'],
            'browser': ['browser', 'chrome', 'firefox', 'safari', 'edge'],
            'cache': ['cache', 'cached', 'clearing cache', 'clear cache'],
            'connection': ['connection', 'internet', 'network', 'connectivity'],
            'refund': ['refund', 'money back', 'cancel subscription'],
            'invoice': ['invoice', 'billing', 'payment', 'charge']
        }
        
        for topic, keywords in topic_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > 0:
                topics.append(topic)
                confidence = max(confidence, min(0.8, 0.4 + (matches * 0.1)))
        
        return topics, confidence
    
    def _infer_language(self, conv: Dict[str, Any]) -> Tuple[Optional[str], float]:
        """Infer conversation language from text content."""
        # Use centralized utility from conversation_utils
        text = extract_conversation_text(conv, clean_html=True)
        
        # Simple language detection based on common words
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        spanish_words = ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le']
        french_words = ['le', 'la', 'de', 'et', 'à', 'un', 'il', 'que', 'ne', 'se', 'ce', 'pas', 'tout']
        
        text_lower = text.lower()
        
        english_count = sum(1 for word in english_words if word in text_lower)
        spanish_count = sum(1 for word in spanish_words if word in text_lower)
        french_count = sum(1 for word in french_words if word in text_lower)
        
        total_words = len(text.split())
        if total_words < 5:  # Too short to determine language
            return None, 0.0
        
        if english_count > spanish_count and english_count > french_count:
            confidence = min(0.9, english_count / total_words * 10)
            return 'en', confidence
        elif spanish_count > english_count and spanish_count > french_count:
            confidence = min(0.9, spanish_count / total_words * 10)
            return 'es', confidence
        elif french_count > english_count and french_count > spanish_count:
            confidence = min(0.9, french_count / total_words * 10)
            return 'fr', confidence
        
        return None, 0.0
    
    # NOTE: _extract_conversation_text() removed - now using centralized extract_conversation_text() from conversation_utils
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level string from numeric confidence."""
        if confidence >= self.high_confidence_threshold:
            return "high"
        elif confidence >= self.medium_confidence_threshold:
            return "medium"
        elif confidence >= self.low_confidence_threshold:
            return "low"
        else:
            return "none"
    
    def _normalize_conversation_parts(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize conversation_parts to ensure consistent dict structure.
        
        SDK may return conversation_parts as:
        - dict: {'conversation_parts': [...]}
        - list: [...]
        
        This normalizes to always use dict wrapper: {'conversation_parts': [...]}
        """
        if 'conversation_parts' not in conv:
            return conv
        
        parts = conv['conversation_parts']
        
        # If it's a list, wrap it in dict
        if isinstance(parts, list):
            conv['conversation_parts'] = {'conversation_parts': parts}
        # If it's already a dict, keep it
        elif isinstance(parts, dict):
            # Ensure it has the 'conversation_parts' key
            if 'conversation_parts' not in parts:
                # Malformed dict - try to salvage it
                self.logger.warning(
                    f"Conversation {conv.get('id')}: conversation_parts dict missing 'conversation_parts' key"
                )
                conv['conversation_parts'] = {'conversation_parts': []}
        else:
            # Unknown type - default to empty
            self.logger.warning(
                f"Conversation {conv.get('id')}: unexpected conversation_parts type {type(parts)}"
            )
            conv['conversation_parts'] = {'conversation_parts': []}
        
        return conv
    
    def _clean_conversation_text(
        self,
        conversations: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Clean and standardize text content in conversations (idempotent).

        Skips cleaning if body_cleaned flag is already present.
        """
        cleaned_count = 0

        for conv in conversations:
            # NORMALIZE conversation_parts structure first
            conv = self._normalize_conversation_parts(conv)
            
            # Clean conversation parts
            parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
            for part in parts:
                if part.get('body') and not part.get('body_cleaned'):
                    original_body = part['body']
                    cleaned_body = self._clean_text(original_body)
                    if cleaned_body != original_body:
                        part['body'] = cleaned_body
                        part['body_cleaned'] = True
                        cleaned_count += 1

            # Clean source body
            source = conv.get('source', {})
            if source.get('body') and not source.get('body_cleaned'):
                original_body = source['body']
                cleaned_body = self._clean_text(original_body)
                if cleaned_body != original_body:
                    source['body'] = cleaned_body
                    source['body_cleaned'] = True
                    cleaned_count += 1

        stats["text_cleaned_count"] = cleaned_count
        return conversations
    
    def _clean_text(self, text: str) -> str:
        """Clean and standardize text content."""
        if not text:
            return text
        
        # Remove HTML tags
        text = self.html_pattern.sub('', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Normalize line breaks
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        return text.strip()
    
    def _detect_outliers(
        self, 
        conversations: List[Dict[str, Any]], 
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect and flag outlier conversations."""
        if len(conversations) < 10:  # Need minimum data for outlier detection
            return conversations
        
        # Calculate text length statistics
        text_lengths = []
        for conv in conversations:
            # Use centralized utility from conversation_utils
            text = extract_conversation_text(conv, clean_html=True)
            text_lengths.append(len(text))
        
        if not text_lengths:
            return conversations
        
        # Simple outlier detection using IQR
        text_lengths.sort()
        q1 = text_lengths[len(text_lengths) // 4]
        q3 = text_lengths[3 * len(text_lengths) // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers_detected = 0
        for conv in conversations:
            # Use centralized utility from conversation_utils
            text = extract_conversation_text(conv, clean_html=True)
            text_length = len(text)
            
            if text_length < lower_bound or text_length > upper_bound:
                conv['is_outlier'] = True
                conv['outlier_reason'] = 'text_length'
                outliers_detected += 1
            else:
                conv['is_outlier'] = False
        
        stats["outliers_detected"] = outliers_detected
        return conversations
    
    def _statistical_sampling(
        self, 
        conversations: List[Dict[str, Any]], 
        max_count: int, 
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Perform statistical sampling to reduce dataset size."""
        if len(conversations) <= max_count:
            return conversations
        
        # Stratified sampling by category if available
        categories = {}
        for conv in conversations:
            category = conv.get('inferred_category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(conv)
        
        sampled = []
        samples_per_category = max_count // len(categories)
        
        for category, convs in categories.items():
            if len(convs) <= samples_per_category:
                sampled.extend(convs)
            else:
                # Random sampling within category
                import random
                sampled.extend(random.sample(convs, samples_per_category))
        
        # Fill remaining slots randomly
        remaining = max_count - len(sampled)
        if remaining > 0:
            remaining_convs = [conv for conv in conversations if conv not in sampled]
            if remaining_convs:
                import random
                sampled.extend(random.sample(remaining_convs, min(remaining, len(remaining_convs))))
        
        stats["sampling_applied"] = True
        stats["original_count"] = len(conversations)
        stats["sampled_count"] = len(sampled)
        
        return sampled
    
    def get_preprocessing_report(self, stats: Dict[str, Any]) -> str:
        """Generate a human-readable preprocessing report."""
        report = []
        report.append("=== Data Preprocessing Report ===")
        report.append(f"Original conversations: {stats['original_count']}")
        report.append(f"Processed conversations: {stats['processed_count']}")
        report.append(f"Deduplicated: {stats['deduplicated_count']}")
        
        if stats.get('inferred_data'):
            inferred = stats['inferred_data']
            report.append(f"Categories inferred: {inferred['categories_inferred']}")
            report.append(f"Topics inferred: {inferred['topics_inferred']}")
            report.append(f"Languages inferred: {inferred['languages_inferred']}")
            
            confidence_dist = inferred.get('confidence_distribution', {})
            report.append("Confidence distribution:")
            for level, count in confidence_dist.items():
                report.append(f"  {level}: {count}")
        
        if stats.get('validation_errors'):
            report.append(f"Validation errors: {len(stats['validation_errors'])}")
        
        if stats.get('outliers_detected'):
            report.append(f"Outliers detected: {stats['outliers_detected']}")
        
        if stats.get('sampling_applied'):
            report.append(f"Statistical sampling: {stats['sampled_count']} from {stats['original_count']}")
        
        return "\n".join(report)


# Custom Exceptions
class PreprocessingError(Exception):
    """Exception raised when preprocessing fails."""
    pass






