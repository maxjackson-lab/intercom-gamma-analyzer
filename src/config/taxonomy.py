"""
Taxonomy Configuration for Intercom Analysis Tool.
Defines the 13 primary categories and 100+ subcategories for analysis.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml
from pathlib import Path


@dataclass
class Subcategory:
    """Represents a subcategory within a primary category."""
    name: str
    description: str
    keywords: List[str]
    confidence_threshold: float = 0.8


@dataclass
class Category:
    """Represents a primary category in the taxonomy."""
    name: str
    description: str
    subcategories: List[Subcategory]
    keywords: List[str]
    confidence_threshold: float = 0.7


class TaxonomyManager:
    """Manages the taxonomy configuration and mapping."""
    
    def __init__(self, taxonomy_file: Optional[str] = None):
        if taxonomy_file:
            self.taxonomy_file = Path(taxonomy_file)
        else:
            # Use absolute path from module location to work in any working directory
            module_dir = Path(__file__).parent
            self.taxonomy_file = module_dir / "taxonomy.yaml"
        
        self.categories: Dict[str, Category] = {}
        self._load_taxonomy()
    
    def _load_taxonomy(self):
        """Load taxonomy from YAML file or create default."""
        if self.taxonomy_file.exists():
            self._load_from_yaml()
        else:
            import logging
            logging.warning(f"Taxonomy file not found at {self.taxonomy_file}, using default taxonomy")
            self._create_default_taxonomy()
            # Don't save to YAML if file doesn't exist - might be deployment environment
            # self._save_to_yaml()
    
    def _create_default_taxonomy(self):
        """Create the default Gamma taxonomy."""
        self.categories = {
            "Abuse": Category(
                name="Abuse",
                description="Reports of harmful behavior, DMCA, malicious links",
                keywords=["abuse", "spam", "malicious", "dmca", "harassment", "inappropriate"],
                subcategories=[
                    Subcategory("Spam", "Spam messages or content", ["spam", "unsolicited", "promotional"]),
                    Subcategory("Malicious Links", "Suspicious or harmful links", ["malicious", "virus", "phishing", "suspicious link"]),
                    Subcategory("DMCA", "Copyright infringement reports", ["dmca", "copyright", "infringement"]),
                    Subcategory("Harassment", "Harassment or bullying", ["harassment", "bullying", "threat", "intimidation"]),
                    Subcategory("Inappropriate Content", "Inappropriate or offensive content", ["inappropriate", "offensive", "explicit"]),
                    Subcategory("Account Takeover", "Suspected account compromise", ["hacked", "compromised", "unauthorized access"]),
                    Subcategory("Fake Account", "Suspected fake or impersonation", ["fake", "impersonation", "identity theft"]),
                    Subcategory("Report User", "User reporting another user", ["report user", "block user", "user complaint"]),
                    Subcategory("Other Abuse", "Other abuse-related issues", ["abuse", "violation", "policy violation"])
                ]
            ),
            
            "Account": Category(
                name="Account",
                description="Account access, settings, credits, email changes",
                keywords=["account", "login", "password", "email", "settings", "credits"],
                subcategories=[
                    Subcategory("Login Issues", "Problems logging in", ["login", "sign in", "authentication", "password"]),
                    Subcategory("Email Change", "Request to change email address", ["email change", "update email", "new email"]),
                    Subcategory("Password Reset", "Password reset requests", ["password reset", "forgot password", "reset password"]),
                    Subcategory("Account Settings", "Account configuration changes", ["settings", "preferences", "profile", "account settings"]),
                    Subcategory("Credits", "Credit-related questions", ["credits", "balance", "usage", "billing credits"]),
                    Subcategory("Account Deletion", "Request to delete account", ["delete account", "close account", "remove account"]),
                    Subcategory("Two-Factor Auth", "2FA setup or issues", ["2fa", "two factor", "authenticator", "security"]),
                    Subcategory("Account Access", "General account access issues", ["access", "permissions", "locked out"]),
                    Subcategory("Profile Update", "Profile information updates", ["profile", "name change", "update profile"]),
                    Subcategory("Account Verification", "Account verification issues", ["verification", "verify", "unverified"]),
                    Subcategory("Account Merge", "Merging multiple accounts", ["merge", "combine", "duplicate account"]),
                    Subcategory("Other Account", "Other account-related issues", ["account", "user", "member"])
                ]
            ),
            
            "Billing": Category(
                name="Billing",
                description="Refunds, invoices, subscriptions, payment methods",
                keywords=["billing", "payment", "invoice", "refund", "subscription", "credit card"],
                subcategories=[
                    Subcategory("Refund", "Refund requests", ["refund", "money back", "cancel payment"]),
                    Subcategory("Subscription", "Subscription management", ["subscription", "plan", "upgrade", "downgrade"]),
                    Subcategory("Invoice", "Invoice questions", ["invoice", "receipt", "billing statement"]),
                    Subcategory("Payment Method", "Payment method updates", ["payment method", "credit card", "billing info"]),
                    Subcategory("Billing Info", "Billing information changes", ["billing address", "tax info", "billing details"]),
                    Subcategory("Pricing", "Pricing questions", ["price", "cost", "pricing", "how much"]),
                    Subcategory("Discount", "Discount requests", ["discount", "coupon", "promo", "deal"]),
                    Subcategory("Credit", "Account credits", ["credit", "balance", "account credit"]),
                    Subcategory("Failed Payment", "Payment failures", ["failed payment", "declined", "payment error"]),
                    Subcategory("Billing Cycle", "Billing cycle questions", ["billing cycle", "renewal", "auto-renew"]),
                    Subcategory("Tax", "Tax-related questions", ["tax", "vat", "taxes", "tax exempt"]),
                    Subcategory("Currency", "Currency conversion", ["currency", "exchange rate", "usd", "eur"]),
                    Subcategory("Enterprise Billing", "Enterprise billing", ["enterprise", "volume", "custom pricing"]),
                    Subcategory("Trial", "Trial period questions", ["trial", "free trial", "trial period"]),
                    Subcategory("Cancellation", "Subscription cancellation", ["cancel", "cancellation", "stop subscription"]),
                    Subcategory("Reactivation", "Account reactivation", ["reactivate", "restore", "reactivation"]),
                    Subcategory("Proration", "Prorated billing", ["proration", "prorated", "partial refund"]),
                    Subcategory("Billing Dispute", "Billing disputes", ["dispute", "chargeback", "billing error"]),
                    Subcategory("Payment History", "Payment history requests", ["payment history", "transactions", "billing history"]),
                    Subcategory("Billing Contact", "Billing contact changes", ["billing contact", "account manager"]),
                    Subcategory("Invoice Customization", "Custom invoice requests", ["custom invoice", "invoice format"]),
                    Subcategory("Billing Export", "Billing data export", ["export billing", "billing data", "financial report"]),
                    Subcategory("Multi-Currency", "Multi-currency billing", ["multi-currency", "currency conversion"]),
                    Subcategory("Billing Integration", "Billing system integration", ["billing integration", "api billing"]),
                    Subcategory("Billing Automation", "Automated billing", ["automated billing", "auto-billing"]),
                    Subcategory("Billing Analytics", "Billing analytics", ["billing analytics", "usage analytics"]),
                    Subcategory("Billing Compliance", "Billing compliance", ["compliance", "audit", "billing compliance"]),
                    Subcategory("Billing Migration", "Billing system migration", ["migration", "billing migration"]),
                    Subcategory("Other Billing", "Other billing issues", ["billing", "payment", "financial"])
                ]
            ),
            
            "Bug": Category(
                name="Bug",
                description="Product bugs, errors, functionality issues",
                keywords=["bug", "error", "broken", "not working", "issue", "problem"],
                subcategories=[
                    Subcategory("Export", "Export functionality bugs", ["export", "ppt", "pdf", "slides", "download"]),
                    Subcategory("Account", "Account-related bugs", ["account bug", "login bug", "profile bug"]),
                    Subcategory("Agent", "AI agent bugs", ["agent bug", "fin bug", "ai bug", "bot bug"]),
                    Subcategory("API", "API-related bugs", ["api bug", "api error", "integration bug"]),
                    Subcategory("Authentication", "Authentication bugs", ["auth bug", "login bug", "session bug"]),
                    Subcategory("Billing", "Billing system bugs", ["billing bug", "payment bug", "invoice bug"]),
                    Subcategory("Collaboration", "Collaboration features", ["collaboration bug", "sharing bug", "permissions bug"]),
                    Subcategory("Dashboard", "Dashboard bugs", ["dashboard bug", "ui bug", "interface bug"]),
                    Subcategory("Data", "Data-related bugs", ["data bug", "sync bug", "data loss"]),
                    Subcategory("Email", "Email functionality bugs", ["email bug", "notification bug", "email delivery"]),
                    Subcategory("File Upload", "File upload bugs", ["upload bug", "file bug", "attachment bug"]),
                    Subcategory("Font", "Font-related bugs", ["font bug", "text bug", "formatting bug"]),
                    Subcategory("Import", "Import functionality bugs", ["import bug", "upload bug", "file import"]),
                    Subcategory("Integration", "Third-party integration bugs", ["integration bug", "connector bug", "api bug"]),
                    Subcategory("Mobile", "Mobile app bugs", ["mobile bug", "app bug", "ios bug", "android bug"]),
                    Subcategory("Performance", "Performance issues", ["slow", "performance", "loading", "timeout"]),
                    Subcategory("Publishing", "Publishing bugs", ["publish bug", "deploy bug", "publication bug"]),
                    Subcategory("Search", "Search functionality bugs", ["search bug", "find bug", "search not working"]),
                    Subcategory("Security", "Security-related bugs", ["security bug", "vulnerability", "security issue"]),
                    Subcategory("Sync", "Synchronization bugs", ["sync bug", "sync issue", "data sync"]),
                    Subcategory("Template", "Template bugs", ["template bug", "theme bug", "design bug"]),
                    Subcategory("UI/UX", "User interface bugs", ["ui bug", "ux bug", "interface bug", "design bug"]),
                    Subcategory("Video", "Video-related bugs", ["video bug", "media bug", "playback bug"]),
                    Subcategory("Workspace", "Workspace bugs", ["workspace bug", "team bug", "organization bug"]),
                    Subcategory("Other Bug", "Other bug reports", ["bug", "error", "issue", "problem"])
                ]
            ),
            
            "Agent/Buddy": Category(
                name="Agent/Buddy",
                description="AI agent questions and usage (internal name: Buddy)",
                keywords=["agent", "buddy", "fin", "ai", "bot", "assistant"],
                subcategories=[
                    Subcategory("Agent Question", "Questions about AI agent", ["agent", "fin", "ai", "bot", "assistant"]),
                    Subcategory("Agent Feedback", "Feedback on AI agent", ["agent feedback", "fin feedback", "ai feedback"]),
                    Subcategory("Agent Training", "AI agent training requests", ["agent training", "fin training", "ai training"]),
                    Subcategory("Agent Integration", "AI agent integration", ["agent integration", "fin integration", "ai integration"]),
                    Subcategory("Agent Performance", "AI agent performance", ["agent performance", "fin performance", "ai performance"]),
                    Subcategory("Other Agent", "Other AI agent issues", ["agent", "ai", "fin", "buddy"])
                ]
            ),
            
            "Chargeback": Category(
                name="Chargeback",
                description="Disputed or unauthorized charges",
                keywords=["chargeback", "dispute", "unauthorized", "fraudulent"],
                subcategories=[
                    Subcategory("Chargeback", "Chargeback disputes", ["chargeback", "dispute", "unauthorized charge"])
                ]
            ),
            
            "Feedback": Category(
                name="Feedback",
                description="Feature requests and suggestions",
                keywords=["feedback", "suggestion", "feature request", "improvement"],
                subcategories=[
                    Subcategory("Feature Request", "Feature requests", ["feature request", "new feature", "suggestion"]),
                    Subcategory("Improvement", "Product improvements", ["improvement", "enhancement", "better"]),
                    Subcategory("User Experience", "UX feedback", ["ux", "user experience", "usability"]),
                    Subcategory("Other Feedback", "Other feedback", ["feedback", "suggestion", "comment"])
                ]
            ),
            
            "Partnerships": Category(
                name="Partnerships",
                description="Business collaborations, affiliate programs",
                keywords=["partnership", "affiliate", "collaboration", "business"],
                subcategories=[
                    Subcategory("Partnership", "Partnership inquiries", ["partnership", "collaboration", "business"]),
                    Subcategory("Affiliate", "Affiliate program", ["affiliate", "referral", "commission"]),
                    Subcategory("Integration", "Integration partnerships", ["integration", "api partnership", "connector"])
                ]
            ),
            
            "Privacy": Category(
                name="Privacy",
                description="Data protection, security, ToS, privacy policies",
                keywords=["privacy", "security", "data protection", "gdpr", "tos"],
                subcategories=[
                    Subcategory("Privacy Policy", "Privacy policy questions", ["privacy policy", "privacy", "data protection"]),
                    Subcategory("GDPR", "GDPR compliance", ["gdpr", "data protection", "privacy rights"]),
                    Subcategory("Security", "Security concerns", ["security", "data security", "protection"]),
                    Subcategory("Terms of Service", "Terms of service", ["terms", "tos", "terms of service"])
                ]
            ),
            
            "Product Question": Category(
                name="Product Question",
                description="How-to questions about features",
                keywords=["how to", "question", "help", "tutorial", "guide"],
                subcategories=[
                    Subcategory("How to Use", "How-to questions", ["how to", "how do i", "tutorial", "guide"]),
                    Subcategory("Feature Explanation", "Feature explanations", ["what is", "explain", "feature"]),
                    Subcategory("Best Practices", "Best practices", ["best practice", "tips", "recommendations"]),
                    Subcategory("Workflow", "Workflow questions", ["workflow", "process", "steps"]),
                    Subcategory("Integration", "Integration questions", ["integration", "connect", "setup"]),
                    Subcategory("Customization", "Customization questions", ["customize", "personalize", "settings"]),
                    Subcategory("Troubleshooting", "General troubleshooting", ["troubleshoot", "help", "problem"]),
                    Subcategory("Training", "Training requests", ["training", "learn", "education"]),
                    Subcategory("Documentation", "Documentation requests", ["documentation", "docs", "manual"]),
                    Subcategory("Support", "General support", ["support", "help", "assistance"]),
                    Subcategory("Other Product", "Other product questions", ["question", "help", "support"])
                ]
            ),
            
            "Promotions": Category(
                name="Promotions",
                description="Discounts, special offers, coupon codes",
                keywords=["promotion", "discount", "coupon", "offer", "deal"],
                subcategories=[
                    Subcategory("Promotion", "Promotional offers", ["promotion", "offer", "deal", "discount"])
                ]
            ),
            
            # NOTE: "Unknown" removed from detectable categories
            # It should ONLY be used as fallback when no other topics match
            # Otherwise conversations mentioning "unclear" get tagged as Unknown
            # even when they're clearly about Billing, Product, etc.
            
            "Workspace": Category(
                name="Workspace",
                description="Member management, permissions, sharing",
                keywords=["workspace", "team", "member", "permission", "sharing"],
                subcategories=[
                    Subcategory("Member Management", "Member management", ["member", "team", "user management"]),
                    Subcategory("Permissions", "Permission management", ["permission", "access", "role", "admin"])
                ]
            )
        }
    
    def _load_from_yaml(self):
        """Load taxonomy from YAML file."""
        with open(self.taxonomy_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Convert YAML data back to Category objects
        for cat_name, cat_data in data['categories'].items():
            subcategories = []
            for sub_data in cat_data['subcategories']:
                subcategories.append(Subcategory(**sub_data))
            
            self.categories[cat_name] = Category(
                name=cat_name,
                description=cat_data['description'],
                keywords=cat_data['keywords'],
                confidence_threshold=cat_data.get('confidence_threshold', 0.7),
                subcategories=subcategories
            )
    
    def _save_to_yaml(self):
        """Save taxonomy to YAML file."""
        data = {
            'categories': {}
        }
        
        for cat_name, category in self.categories.items():
            data['categories'][cat_name] = {
                'description': category.description,
                'keywords': category.keywords,
                'confidence_threshold': category.confidence_threshold,
                'subcategories': [
                    {
                        'name': sub.name,
                        'description': sub.description,
                        'keywords': sub.keywords,
                        'confidence_threshold': sub.confidence_threshold
                    }
                    for sub in category.subcategories
                ]
            }
        
        with open(self.taxonomy_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)
    
    def get_category(self, name: str) -> Optional[Category]:
        """Get a category by name."""
        return self.categories.get(name)
    
    def get_all_categories(self) -> List[str]:
        """Get all category names."""
        return list(self.categories.keys())
    
    def classify_conversation(self, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Classify a conversation into categories based on tags, topics, and text.
        
        Args:
            conversation: Conversation data from Intercom
        
        Returns:
            List of classification results with confidence scores
        """
        classifications = []
        
        # Extract text for analysis
        full_text = self._extract_conversation_text(conversation)
        text_lower = full_text.lower()
        
        # Get tags and topics
        tags = self._extract_tags(conversation)
        topics = self._extract_topics(conversation)
        
        # Classify based on tags and topics first (high confidence)
        for tag in tags:
            classification = self._classify_by_keyword(tag, "tagged")
            if classification:
                classifications.append(classification)
        
        for topic in topics:
            classification = self._classify_by_keyword(topic, "tagged")
            if classification:
                classifications.append(classification)
        
        # Classify based on text content (lower confidence)
        for category_name, category in self.categories.items():
            confidence = self._calculate_text_confidence(text_lower, category)
            if confidence >= category.confidence_threshold:
                classifications.append({
                    'category': category_name,
                    'subcategory': 'General',
                    'confidence': confidence,
                    'method': 'text_analysis',
                    'keywords_found': self._find_matching_keywords(text_lower, category.keywords)
                })
        
        # Remove duplicates and sort by confidence
        unique_classifications = {}
        for classification in classifications:
            key = f"{classification['category']}_{classification['subcategory']}"
            if key not in unique_classifications or classification['confidence'] > unique_classifications[key]['confidence']:
                unique_classifications[key] = classification
        
        return sorted(unique_classifications.values(), key=lambda x: x['confidence'], reverse=True)
    
    def _extract_conversation_text(self, conversation: Dict[str, Any]) -> str:
        """Extract full text from conversation."""
        from src.utils.conversation_utils import extract_conversation_text
        return extract_conversation_text(conversation, clean_html=True)
    
    def _extract_tags(self, conversation: Dict[str, Any]) -> List[str]:
        """Extract tags from conversation."""
        tags = []
        tags_data = conversation.get('tags', {}).get('tags', [])
        
        for tag in tags_data:
            if isinstance(tag, dict):
                tags.append(tag.get('name', str(tag)))
            else:
                tags.append(str(tag))
        
        return tags
    
    def _extract_topics(self, conversation: Dict[str, Any]) -> List[str]:
        """Extract topics from conversation."""
        topics = []
        topics_data = conversation.get('topics', {}).get('topics', [])
        
        for topic in topics_data:
            if isinstance(topic, dict):
                topics.append(topic.get('name', str(topic)))
            else:
                topics.append(str(topic))
        
        return topics
    
    def _classify_by_keyword(self, keyword: str, method: str) -> Optional[Dict[str, Any]]:
        """Classify based on a single keyword."""
        keyword_lower = keyword.lower()
        
        for category_name, category in self.categories.items():
            # Check category keywords
            if any(cat_keyword.lower() in keyword_lower for cat_keyword in category.keywords):
                return {
                    'category': category_name,
                    'subcategory': 'General',
                    'confidence': 1.0,
                    'method': method,
                    'keywords_found': [keyword]
                }
            
            # Check subcategory keywords
            for subcategory in category.subcategories:
                if any(sub_keyword.lower() in keyword_lower for sub_keyword in subcategory.keywords):
                    return {
                        'category': category_name,
                        'subcategory': subcategory.name,
                        'confidence': 1.0,
                        'method': method,
                        'keywords_found': [keyword]
                    }
        
        return None
    
    def _calculate_text_confidence(self, text: str, category: Category) -> float:
        """Calculate confidence score based on text content."""
        matching_keywords = self._find_matching_keywords(text, category.keywords)
        
        if not matching_keywords:
            return 0.0
        
        # Simple confidence calculation based on keyword matches
        confidence = min(len(matching_keywords) / len(category.keywords), 1.0)
        
        # Boost confidence for exact matches
        exact_matches = sum(1 for keyword in matching_keywords if keyword in text)
        confidence += exact_matches * 0.1
        
        return min(confidence, 1.0)
    
    def _find_matching_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Find keywords that match in the text."""
        matching = []
        for keyword in keywords:
            if keyword.lower() in text:
                matching.append(keyword)
        return matching
    
    def update_taxonomy(self, new_items: Dict[str, Any]):
        """Update taxonomy with new items discovered from data."""
        # This will be implemented to handle dynamic taxonomy updates
        pass


# Global taxonomy manager instance
taxonomy_manager = TaxonomyManager()






