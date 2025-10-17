"""
Category Filters Service for Intercom Analysis Tool.
Handles taxonomy-based filtering and categorization of conversations.
"""

import logging
import re
from typing import List, Dict, Optional, Any, Set, Tuple
from pathlib import Path
import yaml

from config.taxonomy import taxonomy_manager

logger = logging.getLogger(__name__)


class CategoryFilters:
    """
    Advanced category filtering system based on Intercom taxonomy.
    
    Features:
    - 13 primary categories with 100+ subcategories
    - Text-based pattern matching
    - Confidence scoring
    - Custom tag support
    - Agent-specific filtering
    """
    
    def __init__(self, taxonomy_config: Optional[Dict[str, Any]] = None):
        """
        Initialize category filters.
        
        Args:
            taxonomy_config: Taxonomy configuration (optional)
        """
        self.taxonomy_config = taxonomy_config or self._load_default_taxonomy()
        self.logger = logging.getLogger(__name__)
        
        # Build pattern matching dictionaries
        self.category_patterns = self._build_category_patterns()
        self.subcategory_patterns = self._build_subcategory_patterns()
        
        # Custom tag mappings
        self.custom_tag_mappings = self._build_custom_tag_mappings()
        
        self.logger.info(f"Initialized CategoryFilters with {len(self.category_patterns)} categories")
    
    def _load_default_taxonomy(self) -> Dict[str, Any]:
        """Load default taxonomy configuration."""
        return {
            "primary_categories": {
                "Abuse": {
                    "description": "Spam, harassment, inappropriate content",
                    "subcategories": ["Spam", "Harassment", "Inappropriate Content", "Fake Account"],
                    "keywords": ["spam", "harassment", "inappropriate", "fake", "abuse", "block", "report"]
                },
                "Account": {
                    "description": "Account management, login, profile issues",
                    "subcategories": ["Login Issues", "Password Reset", "Profile Update", "Account Deletion", "Email Change"],
                    "keywords": ["login", "password", "account", "profile", "sign in", "authentication", "email change"]
                },
                "Billing": {
                    "description": "Refunds, invoices, subscriptions, payments",
                    "subcategories": ["Refund", "Invoice", "Subscription", "Payment", "Credit", "Discount"],
                    "keywords": ["refund", "invoice", "billing", "payment", "subscription", "credit", "discount", "charge"]
                },
                "Bug": {
                    "description": "Product bugs, errors, technical issues",
                    "subcategories": ["Account Bug", "Agent Bug", "API Bug", "Export Bug", "Site Bug", "Workspace Bug"],
                    "keywords": ["bug", "error", "broken", "not working", "issue", "problem", "glitch"]
                },
                "Agent/Buddy": {
                    "description": "AI agent interactions and effectiveness",
                    "subcategories": ["Agent Response", "Agent Training", "Agent Escalation"],
                    "keywords": ["agent", "buddy", "ai", "bot", "automated", "fin", "copilot"]
                },
                "Chargeback": {
                    "description": "Payment disputes and chargebacks",
                    "subcategories": ["Dispute", "Chargeback", "Fraud"],
                    "keywords": ["chargeback", "dispute", "fraud", "unauthorized", "charge"]
                },
                "Feedback": {
                    "description": "Feature requests, suggestions, feedback",
                    "subcategories": ["Feature Request", "Suggestion", "Feedback", "Improvement"],
                    "keywords": ["feature", "request", "suggestion", "feedback", "improvement", "enhancement"]
                },
                "Partnerships": {
                    "description": "Partnership inquiries and collaborations",
                    "subcategories": ["Partnership Inquiry", "Collaboration", "Integration"],
                    "keywords": ["partnership", "collaboration", "integration", "partner", "business"]
                },
                "Privacy": {
                    "description": "Privacy concerns, data requests, GDPR",
                    "subcategories": ["Data Request", "Privacy Concern", "GDPR", "Data Deletion"],
                    "keywords": ["privacy", "data", "gdpr", "delete", "personal information", "consent"]
                },
                "Product Question": {
                    "description": "General product questions and how-to",
                    "subcategories": ["How-to", "Feature Question", "Usage Question", "Tutorial"],
                    "keywords": ["how to", "question", "help", "tutorial", "guide", "feature"]
                },
                "Promotions": {
                    "description": "Promotional inquiries and offers",
                    "subcategories": ["Promo Code", "Discount Request", "Special Offer"],
                    "keywords": ["promo", "discount", "offer", "deal", "coupon", "special"]
                },
                "Unknown": {
                    "description": "Unclassified or unclear conversations",
                    "subcategories": ["Unclear", "Unclassified", "General"],
                    "keywords": []
                },
                "Workspace": {
                    "description": "Workspace management and settings",
                    "subcategories": ["Workspace Settings", "Team Management", "Permissions"],
                    "keywords": ["workspace", "team", "settings", "permissions", "member", "admin"]
                },
                "API": {
                    "description": "API integration, endpoints, and technical issues",
                    "subcategories": ["API Integration", "API Bug", "Authentication", "Rate Limiting"],
                    "keywords": ["api", "endpoint", "request", "response", "authentication", "token", "integration", "webhook"]
                }
            },
            "custom_tags": {
                "DC": {
                    "description": "Dae-Ho's custom technical category",
                    "category": "Bug",
                    "subcategory": "Technical Issue",
                    "keywords": ["technical", "complex", "advanced", "escalation"]
                },
                "Priority Support": {
                    "description": "High-priority support requests",
                    "category": "Account",
                    "subcategory": "Priority Issue",
                    "keywords": ["priority", "urgent", "important", "escalate"]
                },
                "Gamma 3.0": {
                    "description": "Gamma 3.0 related inquiries and issues",
                    "category": "Product Question",
                    "subcategory": "Feature Question",
                    "keywords": ["gamma 3.0", "gamma3", "gamma 3", "new gamma", "gamma update", "gamma version"]
                }
            }
        }
    
    def _build_category_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build pattern matching dictionaries for categories."""
        patterns = {}
        
        for category, config in self.taxonomy_config["primary_categories"].items():
            patterns[category] = {
                "keywords": [kw.lower() for kw in config["keywords"]],
                "regex_patterns": self._create_regex_patterns(config["keywords"]),
                "subcategories": config["subcategories"]
            }
        
        return patterns
    
    def _build_subcategory_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build pattern matching dictionaries for subcategories."""
        patterns = {}
        
        for category, config in self.taxonomy_config["primary_categories"].items():
            for subcategory in config["subcategories"]:
                # Create subcategory-specific patterns
                subcategory_keywords = self._get_subcategory_keywords(subcategory)
                patterns[subcategory] = {
                    "parent_category": category,
                    "keywords": [kw.lower() for kw in subcategory_keywords],
                    "regex_patterns": self._create_regex_patterns(subcategory_keywords)
                }
        
        return patterns
    
    def _build_custom_tag_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Build mappings for custom tags."""
        mappings = {}
        
        for tag, config in self.taxonomy_config.get("custom_tags", {}).items():
            mappings[tag] = {
                "category": config.get("category"),
                "subcategory": config.get("subcategory"),
                "keywords": [kw.lower() for kw in config.get("keywords", [])],
                "description": config.get("description")
            }
        
        return mappings
    
    def _create_regex_patterns(self, keywords: List[str]) -> List[re.Pattern]:
        """Create regex patterns for keyword matching."""
        patterns = []
        
        for keyword in keywords:
            # Create word boundary pattern
            pattern = re.compile(r'\b' + re.escape(keyword.lower()) + r'\b', re.IGNORECASE)
            patterns.append(pattern)
        
        return patterns
    
    def _get_subcategory_keywords(self, subcategory: str) -> List[str]:
        """Get keywords for a specific subcategory."""
        # Map subcategories to their specific keywords
        subcategory_keywords = {
            "Refund": ["refund", "money back", "cancel", "return", "reimburse"],
            "Invoice": ["invoice", "bill", "receipt", "payment", "charge"],
            "Subscription": ["subscription", "plan", "upgrade", "downgrade", "renewal"],
            "Export": ["export", "download", "csv", "excel", "data export", "export data"],
            "API": ["api", "endpoint", "request", "response", "authentication", "token"],
            "Login Issues": ["login", "sign in", "authentication", "access", "credentials"],
            "Password Reset": ["password", "reset", "forgot", "change password"],
            "Email Change": ["email", "change email", "update email", "email address"],
            "Feature Request": ["feature", "request", "add", "new feature", "enhancement"],
            "Bug": ["bug", "error", "broken", "not working", "issue", "problem"],
            "Agent Response": ["agent", "bot", "ai", "automated", "fin", "copilot"],
            "Technical Issue": ["technical", "complex", "advanced", "troubleshoot"],
            "Cache": ["cache", "cached", "clearing cache", "clear cache"],
            "Browser": ["browser", "chrome", "firefox", "safari", "edge"],
            "Connection": ["connection", "internet", "network", "connectivity"]
        }
        
        return subcategory_keywords.get(subcategory, [])
    
    def filter_by_category(
        self, 
        conversations: List[Dict[str, Any]], 
        category: str,
        include_subcategories: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Filter conversations by primary category.
        
        Args:
            conversations: List of conversations to filter
            category: Primary category name
            include_subcategories: Whether to include subcategory matches
            
        Returns:
            Filtered list of conversations
        """
        self.logger.info(f"Filtering {len(conversations)} conversations by category: {category}")
        
        if category not in self.category_patterns:
            self.logger.warning(f"Unknown category: {category}")
            return []
        
        filtered = []
        category_config = self.category_patterns[category]
        
        for conv in conversations:
            # Check if conversation already has category
            if self._has_explicit_category(conv, category):
                filtered.append(conv)
                continue
            
            # Check text content for category patterns
            text = self._extract_conversation_text(conv).lower()
            
            # Check primary category keywords
            if self._matches_keywords(text, category_config["keywords"]):
                conv['matched_category'] = category
                conv['category_confidence'] = 0.8
                filtered.append(conv)
                continue
            
            # Check subcategories if requested
            if include_subcategories:
                for subcategory in category_config["subcategories"]:
                    if subcategory in self.subcategory_patterns:
                        subcategory_config = self.subcategory_patterns[subcategory]
                        if self._matches_keywords(text, subcategory_config["keywords"]):
                            conv['matched_category'] = category
                            conv['matched_subcategory'] = subcategory
                            conv['category_confidence'] = 0.7
                            filtered.append(conv)
                            break
        
        self.logger.info(f"Category filter completed: {len(filtered)} conversations match {category}")
        return filtered
    
    def filter_by_subcategory(
        self, 
        conversations: List[Dict[str, Any]], 
        subcategory: str
    ) -> List[Dict[str, Any]]:
        """
        Filter conversations by specific subcategory.
        
        Args:
            conversations: List of conversations to filter
            subcategory: Subcategory name
            
        Returns:
            Filtered list of conversations
        """
        self.logger.info(f"Filtering {len(conversations)} conversations by subcategory: {subcategory}")
        
        if subcategory not in self.subcategory_patterns:
            self.logger.warning(f"Unknown subcategory: {subcategory}")
            return []
        
        filtered = []
        subcategory_config = self.subcategory_patterns[subcategory]
        
        for conv in conversations:
            # Check if conversation already has subcategory
            if self._has_explicit_subcategory(conv, subcategory):
                filtered.append(conv)
                continue
            
            # Check text content for subcategory patterns
            text = self._extract_conversation_text(conv).lower()
            
            if self._matches_keywords(text, subcategory_config["keywords"]):
                conv['matched_category'] = subcategory_config["parent_category"]
                conv['matched_subcategory'] = subcategory
                conv['category_confidence'] = 0.9
                filtered.append(conv)
        
        self.logger.info(f"Subcategory filter completed: {len(filtered)} conversations match {subcategory}")
        return filtered
    
    def filter_by_custom_tag(
        self, 
        conversations: List[Dict[str, Any]], 
        tag: str
    ) -> List[Dict[str, Any]]:
        """
        Filter conversations by custom tag.
        
        Args:
            conversations: List of conversations to filter
            tag: Custom tag name
            
        Returns:
            Filtered list of conversations
        """
        self.logger.info(f"Filtering {len(conversations)} conversations by custom tag: {tag}")
        
        if tag not in self.custom_tag_mappings:
            self.logger.warning(f"Unknown custom tag: {tag}")
            return []
        
        filtered = []
        tag_config = self.custom_tag_mappings[tag]
        
        for conv in conversations:
            # Check if conversation has explicit tag
            if self._has_explicit_tag(conv, tag):
                filtered.append(conv)
                continue
            
            # Check text content for tag patterns
            text = self._extract_conversation_text(conv).lower()
            
            if self._matches_keywords(text, tag_config["keywords"]):
                conv['matched_tag'] = tag
                conv['matched_category'] = tag_config["category"]
                conv['matched_subcategory'] = tag_config["subcategory"]
                conv['tag_confidence'] = 0.8
                filtered.append(conv)
        
        self.logger.info(f"Custom tag filter completed: {len(filtered)} conversations match {tag}")
        return filtered
    
    def filter_by_agent(
        self, 
        conversations: List[Dict[str, Any]], 
        agent_name: str
    ) -> List[Dict[str, Any]]:
        """
        Filter conversations by assigned agent.
        
        Args:
            conversations: List of conversations to filter
            agent_name: Agent name or ID
            
        Returns:
            Filtered list of conversations
        """
        self.logger.info(f"Filtering {len(conversations)} conversations by agent: {agent_name}")
        
        filtered = []
        
        for conv in conversations:
            # Check admin assignee
            assignee = conv.get('admin_assignee', {})
            if assignee:
                assignee_name = assignee.get('name', '').lower()
                assignee_id = assignee.get('id', '')
                
                if (agent_name.lower() in assignee_name or 
                    agent_name == assignee_id):
                    filtered.append(conv)
                    continue
            
            # Check conversation parts for agent mentions
            text = self._extract_conversation_text(conv).lower()
            if agent_name.lower() in text:
                conv['matched_agent'] = agent_name
                filtered.append(conv)
        
        self.logger.info(f"Agent filter completed: {len(filtered)} conversations match {agent_name}")
        return filtered
    
    def filter_by_escalation(
        self, 
        conversations: List[Dict[str, Any]], 
        escalation_target: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter conversations that involve escalations.
        
        Args:
            conversations: List of conversations to filter
            escalation_target: Specific escalation target (optional)
            
        Returns:
            Filtered list of conversations with escalation patterns
        """
        self.logger.info(f"Filtering {len(conversations)} conversations for escalations")
        
        filtered = []
        escalation_keywords = [
            'escalate', 'escalation', 'escalated', 'escalating',
            'transfer', 'transferred', 'handoff', 'hand off',
            'supervisor', 'manager', 'lead', 'senior'
        ]
        
        # Common escalation targets
        escalation_targets = {
            'dae-ho': ['dae-ho', 'daeho', 'dae ho'],
            'hilary': ['hilary', 'hillary'],
            'max jackson': ['max jackson', 'max', 'jackson'],
            'technical': ['technical', 'tech', 'engineering'],
            'billing': ['billing', 'finance', 'payment']
        }
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Check for escalation keywords
            has_escalation = any(keyword in text for keyword in escalation_keywords)
            
            if has_escalation:
                # Check for specific escalation target
                if escalation_target:
                    target_keywords = escalation_targets.get(escalation_target.lower(), [escalation_target.lower()])
                    if any(target in text for target in target_keywords):
                        conv['escalation_detected'] = True
                        conv['escalation_target'] = escalation_target
                        filtered.append(conv)
                else:
                    # Find any escalation target
                    for target, keywords in escalation_targets.items():
                        if any(keyword in text for keyword in keywords):
                            conv['escalation_detected'] = True
                            conv['escalation_target'] = target
                            filtered.append(conv)
                            break
        
        self.logger.info(f"Escalation filter completed: {len(filtered)} conversations have escalations")
        return filtered
    
    def filter_by_technical_patterns(
        self, 
        conversations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter conversations with technical troubleshooting patterns.
        
        Args:
            conversations: List of conversations to filter
            
        Returns:
            Filtered list of conversations with technical patterns
        """
        self.logger.info(f"Filtering {len(conversations)} conversations for technical patterns")
        
        filtered = []
        technical_patterns = {
            'cache_clearing': ['clear cache', 'clearing cache', 'cache', 'cached'],
            'browser_switching': ['browser', 'chrome', 'firefox', 'safari', 'edge', 'different browser'],
            'connection_issues': ['connection', 'internet', 'network', 'connectivity', 'offline'],
            'export_issues': ['export', 'download', 'csv', 'excel', 'export data'],
            'api_issues': ['api', 'endpoint', 'request', 'response', 'authentication'],
            'login_issues': ['login', 'sign in', 'authentication', 'access', 'credentials']
        }
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            detected_patterns = []
            
            for pattern_name, keywords in technical_patterns.items():
                if any(keyword in text for keyword in keywords):
                    detected_patterns.append(pattern_name)
            
            if detected_patterns:
                conv['technical_patterns'] = detected_patterns
                conv['is_technical'] = True
                filtered.append(conv)
        
        self.logger.info(f"Technical pattern filter completed: {len(filtered)} conversations have technical patterns")
        return filtered
    
    def _has_explicit_category(self, conv: Dict[str, Any], category: str) -> bool:
        """Check if conversation has explicit category assignment."""
        # Check tags
        tags = conv.get('tags', {}).get('tags', [])
        for tag in tags:
            if category.lower() in tag.get('name', '').lower():
                return True
        
        # Check topics
        topics = conv.get('topics', {}).get('topics', [])
        for topic in topics:
            if category.lower() in topic.get('name', '').lower():
                return True
        
        # Check custom attributes
        custom_attrs = conv.get('custom_attributes', {})
        for key, value in custom_attrs.items():
            if 'category' in key.lower() and category.lower() in str(value).lower():
                return True
        
        return False
    
    def _has_explicit_subcategory(self, conv: Dict[str, Any], subcategory: str) -> bool:
        """Check if conversation has explicit subcategory assignment."""
        # Check tags
        tags = conv.get('tags', {}).get('tags', [])
        for tag in tags:
            if subcategory.lower() in tag.get('name', '').lower():
                return True
        
        # Check topics
        topics = conv.get('topics', {}).get('topics', [])
        for topic in topics:
            if subcategory.lower() in topic.get('name', '').lower():
                return True
        
        return False
    
    def _has_explicit_tag(self, conv: Dict[str, Any], tag: str) -> bool:
        """Check if conversation has explicit tag assignment."""
        tags = conv.get('tags', {}).get('tags', [])
        for tag_obj in tags:
            if tag.lower() == tag_obj.get('name', '').lower():
                return True
        return False
    
    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text matches any of the keywords."""
        return any(keyword in text for keyword in keywords)
    
    def _extract_conversation_text(self, conv: Dict[str, Any]) -> str:
        """Extract all text content from a conversation."""
        text_parts = []
        
        # Extract from conversation parts
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            if part.get('part_type') == 'comment':
                body = part.get('body', '')
                if body:
                    text_parts.append(body)
        
        # Extract from source
        source = conv.get('source', {})
        if source.get('body'):
            text_parts.append(source['body'])
        
        return ' '.join(text_parts)
    
    def get_available_categories(self) -> List[str]:
        """Get list of available primary categories."""
        return list(self.taxonomy_config["primary_categories"].keys())
    
    def get_available_subcategories(self, category: Optional[str] = None) -> List[str]:
        """Get list of available subcategories."""
        if category:
            return self.taxonomy_config["primary_categories"].get(category, {}).get("subcategories", [])
        else:
            all_subcategories = []
            for cat_config in self.taxonomy_config["primary_categories"].values():
                all_subcategories.extend(cat_config.get("subcategories", []))
            return all_subcategories
    
    def get_available_custom_tags(self) -> List[str]:
        """Get list of available custom tags."""
        return list(self.taxonomy_config.get("custom_tags", {}).keys())
    
    def get_filter_statistics(
        self, 
        conversations: List[Dict[str, Any]], 
        filters_applied: List[str]
    ) -> Dict[str, Any]:
        """Get statistics about applied filters."""
        stats = {
            "total_conversations": len(conversations),
            "filters_applied": filters_applied,
            "category_distribution": {},
            "subcategory_distribution": {},
            "custom_tag_distribution": {},
            "technical_patterns": {},
            "escalation_count": 0
        }
        
        for conv in conversations:
            # Category distribution
            category = conv.get('matched_category', 'unknown')
            stats["category_distribution"][category] = stats["category_distribution"].get(category, 0) + 1
            
            # Subcategory distribution
            subcategory = conv.get('matched_subcategory')
            if subcategory:
                stats["subcategory_distribution"][subcategory] = stats["subcategory_distribution"].get(subcategory, 0) + 1
            
            # Custom tag distribution
            tag = conv.get('matched_tag')
            if tag:
                stats["custom_tag_distribution"][tag] = stats["custom_tag_distribution"].get(tag, 0) + 1
            
            # Technical patterns
            patterns = conv.get('technical_patterns', [])
            for pattern in patterns:
                stats["technical_patterns"][pattern] = stats["technical_patterns"].get(pattern, 0) + 1
            
            # Escalations
            if conv.get('escalation_detected'):
                stats["escalation_count"] += 1
        
        return stats

