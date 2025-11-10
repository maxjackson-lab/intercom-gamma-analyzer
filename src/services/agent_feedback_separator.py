"""
Agent feedback separator for categorizing conversations by agent type.
"""

import logging
import re
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class AgentFeedbackSeparator:
    """Separates conversations by agent type with case-insensitive matching."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Agent patterns configuration
        self.agent_patterns = {
            'finn_ai': [
                r'finn',
                r'ai\s+agent',
                r'automated\s+response',
                r'bot\s+response',
                r'ai\s+assistant'
            ],
            'boldr_support': [
                r'boldr',
                r'@boldr\.com',
                r'boldr\s+support',
                r'boldr\s+team'
            ],
            'horatio_support': [
                r'horatio',
                r'@horatio\.com',
                r'horatio\s+support',
                r'horatio\s+team'
            ],
            'gamma_cx_staff': [
                r'gamma\s+cx',
                r'gamma\s+customer\s+experience',
                r'gamma\s+support\s+staff',
                r'@gamma\.app'
            ]
        }
        
        self.logger.info("AgentFeedbackSeparator initialized")
    
    def separate_by_agent_type(self, conversations: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Separate conversations by agent type.
        
        Args:
            conversations: List of conversation dictionaries
        
        Returns:
            Dictionary with agent types as keys and conversation lists as values
        """
        self.logger.info(f"Separating {len(conversations)} conversations by agent type")
        
        separated = {
            'finn_ai': [],
            'boldr_support': [],
            'horatio_support': [],
            'gamma_cx_staff': [],
            'mixed_agent': [],
            'customer_only': []
        }
        
        for conv in conversations:
            agent_type = self._identify_agent_type(conv)
            separated[agent_type].append(conv)
            
            self.logger.debug(
                f"Conversation {conv.get('id')} classified as {agent_type}"
            )
        
        # Log distribution
        for agent_type, convs in separated.items():
            if convs:
                percentage = len(convs) / len(conversations) * 100
                self.logger.info(
                    f"{agent_type}: {len(convs)} conversations ({percentage:.1f}%)"
                )
        
        return separated
    
    def _identify_agent_type(self, conversation: Dict) -> str:
        """
        Identify the agent type for a conversation.
        
        Args:
            conversation: Conversation dictionary
        
        Returns:
            Agent type string
        """
        # Extract all text content from the conversation
        text_content = self._extract_conversation_text(conversation)
        
        # Check for each agent type
        agent_scores = defaultdict(int)
        
        for agent_type, patterns in self.agent_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                agent_scores[agent_type] += len(matches)
        
        # Determine agent type based on scores
        if not agent_scores:
            return 'customer_only'
        
        # Get the agent type with highest score
        primary_agent = max(agent_scores.items(), key=lambda x: x[1])
        
        # If multiple agents detected, classify as mixed
        if len([score for score in agent_scores.values() if score > 0]) > 1:
            return 'mixed_agent'
        
        # If primary agent has score > 0, return it
        if primary_agent[1] > 0:
            return primary_agent[0]
        
        return 'customer_only'
    
    def _extract_conversation_text(self, conversation: Dict) -> str:
        """
        Extract all text content from a conversation for agent detection.
        
        Args:
            conversation: Conversation dictionary
        
        Returns:
            Combined text content
        """
        text_parts = []
        
        # Extract from conversation parts
        if 'conversation_parts' in conversation:
            parts = conversation['conversation_parts']
            if isinstance(parts, dict) and 'conversation_parts' in parts:
                parts = parts['conversation_parts']
            
            for part in parts:
                if isinstance(part, dict):
                    # Extract body text
                    if 'body' in part:
                        text_parts.append(part['body'])
                    
                    # Extract author information
                    if 'author' in part:
                        author = part['author']
                        if isinstance(author, dict):
                            if 'name' in author:
                                text_parts.append(author['name'])
                            if 'email' in author:
                                text_parts.append(author['email'])
        
        # Extract from source (safe access)
        source_body = conversation.get('source', {}).get('body')
        if source_body:
            text_parts.append(source_body)
        
        # Extract from custom attributes
        if 'custom_attributes' in conversation:
            custom_attrs = conversation['custom_attributes']
            if isinstance(custom_attrs, dict):
                for value in custom_attrs.values():
                    if isinstance(value, str):
                        text_parts.append(value)
        
        return ' '.join(text_parts)
    
    def get_agent_statistics(self, separated_conversations: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Get statistics about agent distribution.
        
        Args:
            separated_conversations: Output from separate_by_agent_type
        
        Returns:
            Statistics dictionary
        """
        total_conversations = sum(len(convs) for convs in separated_conversations.values())
        
        stats = {
            'total_conversations': total_conversations,
            'agent_distribution': {},
            'agent_percentages': {}
        }
        
        for agent_type, conversations in separated_conversations.items():
            count = len(conversations)
            percentage = (count / total_conversations * 100) if total_conversations > 0 else 0
            
            stats['agent_distribution'][agent_type] = count
            stats['agent_percentages'][agent_type] = round(percentage, 2)
        
        return stats
    
    def filter_by_agent_type(
        self, 
        conversations: List[Dict], 
        agent_types: List[str]
    ) -> List[Dict]:
        """
        Filter conversations by specific agent types.
        
        Args:
            conversations: List of conversations
            agent_types: List of agent types to include
        
        Returns:
            Filtered list of conversations
        """
        self.logger.info(f"Filtering conversations by agent types: {agent_types}")
        
        separated = self.separate_by_agent_type(conversations)
        
        filtered_conversations = []
        for agent_type in agent_types:
            if agent_type in separated:
                filtered_conversations.extend(separated[agent_type])
        
        self.logger.info(f"Filtered to {len(filtered_conversations)} conversations")
        return filtered_conversations
