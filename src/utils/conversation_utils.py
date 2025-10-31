"""
Utility functions for extracting data from Intercom conversations.

This module provides standard functions for extracting text content, metadata,
and other information from Intercom conversation objects.
"""

import re
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def extract_conversation_text(conversation: Dict[str, Any], clean_html: bool = True) -> str:
    """
    Extract all text content from an Intercom conversation.
    
    This function extracts text from:
    - conversation.source.body (initial message)
    - conversation.conversation_parts[].body (all replies)
    - conversation.notes[].body (internal notes, optional)
    
    Args:
        conversation: Intercom conversation dictionary
        clean_html: Whether to strip HTML tags from text
        
    Returns:
        Combined text content from all parts of the conversation
    """
    text_parts = []
    
    try:
        # Extract from source (initial message)
        source = conversation.get('source', {})
        if isinstance(source, dict):
            body = source.get('body', '')
            if body:
                if clean_html:
                    body = _clean_html(body)
                text_parts.append(body)
        
        # Extract from conversation parts (replies)
        conversation_parts = conversation.get('conversation_parts', {})
        if isinstance(conversation_parts, dict):
            parts = conversation_parts.get('conversation_parts', [])
        elif isinstance(conversation_parts, list):
            parts = conversation_parts
        else:
            parts = []
        
        for part in parts:
            if isinstance(part, dict):
                body = part.get('body', '')
                if body:
                    if clean_html:
                        body = _clean_html(body)
                    text_parts.append(body)
        
        # Optionally extract from notes
        notes = conversation.get('notes', {})
        if isinstance(notes, dict):
            note_list = notes.get('notes', [])
            for note in note_list:
                if isinstance(note, dict):
                    body = note.get('body', '')
                    if body:
                        if clean_html:
                            body = _clean_html(body)
                        text_parts.append(body)
    
    except Exception as e:
        logger.error(f"Error extracting conversation text: {e}")
    
    return ' '.join(text_parts).strip()


def extract_customer_messages(conversation: Dict[str, Any], clean_html: bool = True) -> List[str]:
    """
    Extract only customer (user) messages from a conversation.
    
    This filters out admin/bot messages and returns only customer-authored content.
    
    Args:
        conversation: Intercom conversation dictionary
        clean_html: Whether to strip HTML tags from text
        
    Returns:
        List of customer message texts in chronological order
    """
    customer_msgs = []
    
    try:
        # Extract from source (initial message) if from customer
        source = conversation.get('source', {})
        if isinstance(source, dict):
            author = source.get('author', {})
            if author.get('type') == 'user':  # Customer/user message
                body = source.get('body', '').strip()
                if body:
                    if clean_html:
                        body = _clean_html(body)
                    customer_msgs.append(body)
        
        # Extract from conversation parts
        conversation_parts = conversation.get('conversation_parts', {})
        if isinstance(conversation_parts, dict):
            parts = conversation_parts.get('conversation_parts', [])
        elif isinstance(conversation_parts, list):
            parts = conversation_parts
        else:
            parts = []
        
        for part in parts:
            if isinstance(part, dict):
                author = part.get('author', {})
                if author.get('type') == 'user':  # Customer/user message
                    body = part.get('body', '').strip()
                    if body:
                        if clean_html:
                            body = _clean_html(body)
                        customer_msgs.append(body)
    
    except Exception as e:
        logger.error(f"Error extracting customer messages: {e}")
    
    return customer_msgs


def _clean_html(text: str) -> str:
    """
    Remove HTML tags and clean up text content.
    
    Args:
        text: Text potentially containing HTML
        
    Returns:
        Cleaned text with HTML removed
    """
    if not text:
        return ''
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_conversation_metadata(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key metadata from a conversation.
    
    Args:
        conversation: Intercom conversation dictionary
        
    Returns:
        Dictionary containing conversation metadata
    """
    return {
        'id': conversation.get('id'),
        'created_at': conversation.get('created_at'),
        'updated_at': conversation.get('updated_at'),
        'state': conversation.get('state'),
        'tags': [tag.get('name', tag) if isinstance(tag, dict) else tag 
                for tag in conversation.get('tags', {}).get('tags', [])],
        'custom_attributes': conversation.get('custom_attributes', {}),
        'assignee': conversation.get('admin_assignee', {}).get('name'),
        'contact_id': (conversation.get('contacts', {}).get('contacts', [{}])[0].get('id') 
                      if conversation.get('contacts', {}).get('contacts') else None),
    }

