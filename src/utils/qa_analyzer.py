"""
QA Analysis Utilities - Automated quality scoring for agent performance.

Implements Gamma QA Rubric metrics:
- Customer Connection (greeting quality, name usage)
- Communication Quality (grammar, formatting)
- Content Quality (derived from FCR/reopen rates)
"""

import re
from typing import Dict, List, Any, Optional
from collections import Counter


# Greeting patterns for detection
GREETING_PATTERNS = [
    r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
    r'\bhowdy\b',
    r'\bwelcome\b',
    r'\bthanks? for (reaching out|contacting|writing)\b'
]

# Common grammar/spelling errors to detect
COMMON_ERRORS = {
    r'\byour\s+welcome\b': "you're welcome",
    r'\bits\s+okay\b': "it's okay", 
    r'\bcant\b': "can't",
    r'\bdont\b': "don't",
    r'\bwont\b': "won't",
    r'\bim\b': "I'm",
    r'\bId\b': "I'd",
    r'\bteh\b': "the",
    r'\brecieve\b': "receive",
    r'\boccured\b': "occurred"
}


def analyze_greeting_quality(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the quality of agent's greeting in first message.
    
    Args:
        conversation: Intercom conversation with conversation_parts
        
    Returns:
        Dict with greeting_present, customer_name_used, greeting_quality_score
    """
    # Get first agent message
    first_agent_message = get_first_agent_message(conversation)
    if not first_agent_message:
        return {
            'greeting_present': False,
            'customer_name_used': False,
            'greeting_quality_score': 0.0
        }
    
    message_text = first_agent_message.lower()
    
    # Check for greeting
    has_greeting = any(
        re.search(pattern, message_text, re.IGNORECASE) 
        for pattern in GREETING_PATTERNS
    )
    
    # Check for customer name usage
    customer_name = get_customer_name(conversation)
    used_name = False
    if customer_name:
        # Check if name appears in first message (case insensitive)
        name_parts = customer_name.lower().split()
        used_name = any(part in message_text for part in name_parts if len(part) > 2)
    
    # Calculate score (0.5 for greeting, 0.5 for name)
    score = 0.0
    if has_greeting:
        score += 0.5
    if used_name:
        score += 0.5
    
    return {
        'greeting_present': has_greeting,
        'customer_name_used': used_name,
        'greeting_quality_score': score
    }


def analyze_grammar_quality(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze grammar and spelling in agent messages.
    
    Args:
        conversation: Intercom conversation with conversation_parts
        
    Returns:
        Dict with avg_errors_per_message, total_errors, messages_analyzed
    """
    agent_messages = get_agent_messages(conversation)
    
    if not agent_messages:
        return {
            'avg_grammar_errors_per_message': 0.0,
            'total_errors': 0,
            'messages_analyzed': 0
        }
    
    total_errors = 0
    
    for message in agent_messages:
        # Strip HTML tags for analysis
        clean_text = strip_html(message)
        
        # Check for common errors
        for pattern, correction in COMMON_ERRORS.items():
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            total_errors += len(matches)
        
        # Check for multiple spaces (formatting issue)
        if re.search(r'\s{3,}', clean_text):
            total_errors += 1
        
        # Check for missing punctuation at end of sentences
        sentences = re.split(r'[.!?]', clean_text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 50 and not re.search(r'[.!?]$', sentence):
                total_errors += 0.5  # Half penalty for potential run-on
    
    avg_errors = total_errors / len(agent_messages)
    
    return {
        'avg_grammar_errors_per_message': round(avg_errors, 2),
        'total_errors': int(total_errors),
        'messages_analyzed': len(agent_messages)
    }


def analyze_formatting_quality(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze message formatting (paragraphs, line breaks, structure).
    
    Args:
        conversation: Intercom conversation with conversation_parts
        
    Returns:
        Dict with proper_formatting_rate, avg_message_length_words
    """
    agent_messages = get_agent_messages(conversation)
    
    if not agent_messages:
        return {
            'proper_formatting_rate': 0.0,
            'avg_message_length_words': 0,
            'messages_with_formatting': 0
        }
    
    messages_with_proper_formatting = 0
    total_words = 0
    
    for message in agent_messages:
        clean_text = strip_html(message)
        words = len(clean_text.split())
        total_words += words
        
        # Good formatting indicators:
        # 1. Has line breaks for long messages (>150 chars)
        # 2. Not a wall of text
        # 3. Appropriate use of paragraphs
        
        has_proper_formatting = False  # Default to False, must prove good formatting
        
        # Short messages (<150 chars) get a pass
        if len(clean_text) < 150:
            has_proper_formatting = True
        else:
            # Long messages need paragraph breaks
            # Check for paragraph indicators
            has_paragraph_breaks = ('\n\n' in message or 
                                  message.count('<p>') > 1 or 
                                  message.count('\n') >= 2)
            
            if has_paragraph_breaks:
                # Check for excessive line breaks (poor formatting)
                if message.count('\n\n\n') > 0:
                    has_proper_formatting = False
                else:
                    has_proper_formatting = True
            else:
                # No breaks in long message = wall of text
                has_proper_formatting = False
        
        if has_proper_formatting:
            messages_with_proper_formatting += 1
    
    formatting_rate = messages_with_proper_formatting / len(agent_messages)
    avg_words = total_words / len(agent_messages)
    
    return {
        'proper_formatting_rate': round(formatting_rate, 2),
        'avg_message_length_words': int(avg_words),
        'messages_with_formatting': messages_with_proper_formatting
    }


def calculate_qa_metrics(
    conversations: List[Dict[str, Any]],
    fcr_rate: float,
    reopen_rate: float
) -> Optional[Dict[str, Any]]:
    """
    Calculate comprehensive QA metrics for a set of conversations.
    
    Args:
        conversations: List of Intercom conversations
        fcr_rate: First Contact Resolution rate (0-1)
        reopen_rate: Reopen rate (0-1)
        
    Returns:
        Dict with all QA metrics or None if no data
    """
    if not conversations:
        return None
    
    # Aggregate greeting quality across all conversations
    greeting_results = [analyze_greeting_quality(conv) for conv in conversations]
    greeting_present_count = sum(1 for r in greeting_results if r['greeting_present'])
    name_used_count = sum(1 for r in greeting_results if r['customer_name_used'])
    avg_greeting_score = sum(r['greeting_quality_score'] for r in greeting_results) / len(greeting_results)
    
    # Aggregate grammar quality
    grammar_results = [analyze_grammar_quality(conv) for conv in conversations]
    total_errors = sum(r['total_errors'] for r in grammar_results)
    total_messages = sum(r['messages_analyzed'] for r in grammar_results)
    avg_errors_per_message = total_errors / total_messages if total_messages > 0 else 0
    
    # Aggregate formatting quality
    formatting_results = [analyze_formatting_quality(conv) for conv in conversations]
    avg_formatting_rate = sum(r['proper_formatting_rate'] for r in formatting_results) / len(formatting_results)
    avg_message_length = sum(r['avg_message_length_words'] for r in formatting_results) / len(formatting_results)
    
    # Calculate composite scores
    
    # Customer Connection Score (greeting quality)
    customer_connection_score = avg_greeting_score
    
    # Communication Quality Score (grammar + formatting)
    # Lower errors = higher score
    grammar_score = max(0.0, 1.0 - (avg_errors_per_message * 0.2))  # Each error reduces score
    communication_quality_score = (grammar_score * 0.5) + (avg_formatting_rate * 0.5)
    
    # Content Quality Score (from existing metrics)
    # High FCR and low reopen = good content
    content_quality_score = (fcr_rate * 0.7) + ((1.0 - reopen_rate) * 0.3)
    
    # Overall QA Score (weighted average)
    overall_qa_score = (
        (customer_connection_score * 0.30) +
        (communication_quality_score * 0.35) +
        (content_quality_score * 0.35)
    )
    
    return {
        'greeting_present': greeting_present_count > len(conversations) * 0.8,  # 80%+ have greetings
        'customer_name_used': name_used_count > len(conversations) * 0.5,  # 50%+ use names
        'greeting_quality_score': round(avg_greeting_score, 2),
        'avg_grammar_errors_per_message': round(avg_errors_per_message, 2),
        'avg_message_length_words': int(avg_message_length),
        'proper_formatting_rate': round(avg_formatting_rate, 2),
        'customer_connection_score': round(customer_connection_score, 2),
        'communication_quality_score': round(communication_quality_score, 2),
        'content_quality_score': round(content_quality_score, 2),
        'overall_qa_score': round(overall_qa_score, 2),
        'messages_analyzed': total_messages,
        'conversations_sampled': len(conversations)
    }


# Helper functions

def get_first_agent_message(conversation: Dict[str, Any]) -> Optional[str]:
    """Extract first agent message from conversation"""
    parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
    
    for part in parts:
        if part.get('author', {}).get('type') == 'admin':
            return part.get('body', '')
    
    return None


def get_agent_messages(conversation: Dict[str, Any]) -> List[str]:
    """Extract all agent messages from conversation"""
    parts = conversation.get('conversation_parts', {}).get('conversation_parts', [])
    
    messages = []
    for part in parts:
        if part.get('author', {}).get('type') == 'admin':
            body = part.get('body', '')
            if body:
                messages.append(body)
    
    return messages


def get_customer_name(conversation: Dict[str, Any]) -> Optional[str]:
    """Extract customer name from conversation"""
    # Try source (initial message metadata)
    source = conversation.get('source', {})
    if source.get('author', {}).get('type') == 'user':
        name = source.get('author', {}).get('name')
        if name:
            return name
    
    # Try contacts
    contacts = conversation.get('contacts', {}).get('contacts', [])
    if contacts:
        name = contacts[0].get('name')
        if name:
            return name
    
    return None


def strip_html(text: str) -> str:
    """Remove HTML tags from text"""
    # Simple HTML tag removal
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

