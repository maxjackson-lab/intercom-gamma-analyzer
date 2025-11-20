"""
Test Data Generator Service

Generates realistic test conversations for testing the analysis pipeline
without hitting the Intercom API.

Uses the same test fixtures from tests/conftest.py but scaled up for
realistic volume testing.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class TestDataGenerator:
    """Generate realistic test conversation data for pipeline testing."""
    
    # Realistic topic distribution based on actual data (Updated Nov 2025)
    TOPIC_DISTRIBUTION = {
        'Billing': 0.32,  # 32% billing issues (matches real data)
        'Product Question': 0.16,  # 16% product questions
        'Bug': 0.12,  # 12% bugs
        'Account': 0.11,  # 11% account issues
        'Workspace': 0.06,  # 6% workspace/team
        'Feedback': 0.02,  # 2% feedback
        'Privacy': 0.01,  # 1% privacy
        'Abuse': 0.01,  # 1% abuse
        'Credits': 0.01,  # 1% credits
        'Promotions': 0.01,  # 1% promotions
        'Agent/Buddy': 0.01,  # 1% AI agent questions (should be low!)
        'Other': 0.16  # 16% other/edge cases (realistic for keyword-based detection)
    }
    
    # Tier distribution
    TIER_DISTRIBUTION = {
        'Free': 0.47,  # 47% free tier
        'Pro': 0.28,  # 28% pro
        'Plus': 0.24,  # 24% plus
        'Ultra': 0.01  # 1% ultra
    }
    
    # Language distribution (top languages)
    LANGUAGE_DISTRIBUTION = {
        'English': 0.46,
        'Spanish': 0.11,
        'Brazilian Portuguese': 0.10,
        'Russian': 0.05,
        'French': 0.04,
        'Korean': 0.04,
        'Japanese': 0.03,
        'German': 0.03,
        'Other': 0.14
    }
    
    # Sample messages by topic (includes edge cases for keyword testing)
    MESSAGE_TEMPLATES = {
        'Billing': [
            "I just signed up for gamma pro monthly plan but it charged me for the whole year",
            "I got confused and paid for the annual pro, the reality is that I can't afford it",
            "I accidentally subscribed for a year, I want to get a refund",
            "Can I get a refund? I selected the wrong plan",
            "Why was I charged for annual when I selected monthly?",
            "I need help with my subscription billing",
            "The invoice amount is incorrect",
            "Can you provide a refund for the annual subscription?",
            "Need invoice for my payment",  # ✅ Tests 'invoice' keyword
            "Unexpected charge on my credit card"  # ✅ Tests 'charge' keyword
        ],
        'Product Question': [
            "How do I connect my custom domain?",
            "Where can I find domain settings or SSL settings?",
            "Can I export to PowerPoint?",
            "How do I publish my presentation?",
            "Can I use my own domain with Gamma?",
            "Is there a way to white label the site?",
            "How do I add password protection?",
            "Can I connect multiple domains to one site?"
        ],
        'Bug': [
            "When I export my slides to Google Slides, the icons are not exported",
            "I upgraded to Pro but only received 2000 credits instead of 4000",
            "PDF export shows incorrect page numbers",
            "The site won't publish to my custom domain",
            "Credits are missing after upgrade",
            "My presentation isn't loading",
            "Images aren't appearing in the export",
            "The API is returning errors even though I have credits"
        ],
        'Account': [
            "How do I change my account email address?",
            "I can't reset my password",
            "I need to transfer my subscription to another account",
            "How do I sign in from a different device?",
            "I lost access to my Google account",
            "Can I merge two accounts?",
            "How do I update my billing information?",
            "I'm locked out of my account"
        ],
        'Credits': [
            "I just spent 96 dollars and started working on a deck - out of credits?",
            "How do credits work?",
            "Why are my credits depleting so fast?",
            "Can I recharge my credits?",
            "I'm missing credits after my subscription",
            "The watermark appeared even though I paid",
            "API shows zero credits even though I have a subscription",
            "We lost 4,500 credits from Thursday to Friday"
        ],
        'Agent/Buddy': [
            "How does the gamma ai work?",  # ✅ Should match "gamma ai"
            "Tell me about your ai assistant features",  # ✅ Should match "ai assistant"
            "What is buddy in gamma?",  # ✅ Should match "buddy"
            "Can the chatbot help me with presentations?"  # ✅ Should match "chatbot"
        ],
        'Other': [
            "How does Gamma work?",
            "What features are included in Pro?",
            "Can I collaborate with my team?",
            "Is there a mobile app?",
            "This is my final decision on the plan",  # ❌ Should NOT match "fin"
            "I use email daily for work communication",  # ❌ Should NOT match "ai"
            "Can I speak to an agent about my issue?",  # ❌ Should NOT match Agent/Buddy
            "What's the difference between Plus and Pro?",
            "Do you offer educational discounts?",
            "Can I use Gamma for commercial purposes?",
            "I need to finish this project by Friday",  # ❌ Should NOT match "fin"
            "Is there a waiting list available?"  # ❌ Should NOT match "ai"
        ]
    }
    
    # Agent email patterns
    AGENT_EMAILS = {
        'horatio': [
            'agent1@hirehoratio.co',
            'agent2@hirehoratio.co',
            'agent3@hirehoratio.co',
            'support@hirehoratio.co'
        ],
        'boldr': [
            'agent1@boldrimpact.com',
            'agent2@boldrimpact.com',
            'support@boldrimpact.com'
        ],
        'escalated': [
            'max.jackson@gamma.app',
            'dae-ho.kim@gamma.app',
            'hilary@gamma.app'
        ]
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_conversations(
        self,
        count: int = 100,
        start_date: datetime = None,
        end_date: datetime = None,
        include_free_tier: bool = True,
        include_paid_tier: bool = True,
        agent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic test conversations.
        
        Args:
            count: Number of conversations to generate
            start_date: Start of date range
            end_date: End of date range
            include_free_tier: Include free tier Fin conversations
            include_paid_tier: Include paid tier human-supported conversations
            
        Returns:
            List of conversation dicts matching Intercom structure
        """
        if start_date is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now()
        
        self.logger.info(f"🧪 Generating {count} test conversations")
        self.logger.info(f"   Date range: {start_date.date()} to {end_date.date()}")
        if agent_filter:
            self.logger.info(f"   Agent filter: {agent_filter}")
        
        conversations = []
        date_range_seconds = int((end_date - start_date).total_seconds())
        normalized_filter = agent_filter.lower() if agent_filter else None
        max_attempts = count * 5 if normalized_filter else count
        attempts = 0
        
        while len(conversations) < count and attempts < max_attempts:
            attempts += 1
            i = attempts  # Use attempt count for deterministic IDs
            # Determine tier
            tier = self._select_random_tier()
            
            # Free tier → Fin AI only
            # Paid tier → mix of human agents and Fin-resolved
            if tier == 'Free':
                if not include_free_tier:
                    continue
                conv = self._create_fin_conversation(
                    conv_id=f'test_free_{i}',
                    tier='Free',
                    start_date=start_date,
                    date_range_seconds=date_range_seconds,
                    index=i
                )
            else:
                if not include_paid_tier:
                    continue
                # REALITY: ALL paid conversations start with Fin/Support Sal
                # ~75% Fin resolves successfully (no human escalation)
                # ~25% escalate to human (Horatio, Boldr, Senior Staff)
                if random.random() < 0.25:
                    # 25% escalate to human
                    conv = self._create_human_conversation(
                        conv_id=f'test_paid_{i}',
                        tier=tier,
                        start_date=start_date,
                        date_range_seconds=date_range_seconds,
                        index=i
                    )
                else:
                    # 75% Fin resolves successfully
                    conv = self._create_fin_conversation(
                        conv_id=f'test_paid_fin_{i}',
                        tier=tier,
                        start_date=start_date,
                        date_range_seconds=date_range_seconds,
                        index=i
                    )
            
            # Apply optional agent/vendor filter
            if normalized_filter and not self._matches_agent_filter(conv, normalized_filter):
                continue
            
            conversations.append(conv)
        
        if normalized_filter and len(conversations) < count:
            self.logger.warning(
                f"Requested {count} conversations for agent '{agent_filter}' "
                f"but only generated {len(conversations)} after {attempts} attempts. "
                "Consider relaxing filters or increasing include_paid_tier/include_free_tier options."
            )
        
        self.logger.info(f"   ✅ Generated {len(conversations)} conversations")
        self._log_distribution(conversations)
        
        return conversations
    
    def _select_random_tier(self) -> str:
        """Select tier based on realistic distribution."""
        rand = random.random()
        cumulative = 0
        for tier, prob in self.TIER_DISTRIBUTION.items():
            cumulative += prob
            if rand <= cumulative:
                return tier
        return 'Free'
    
    def _select_random_topic(self) -> str:
        """Select topic based on realistic distribution."""
        rand = random.random()
        cumulative = 0
        for topic, prob in self.TOPIC_DISTRIBUTION.items():
            cumulative += prob
            if rand <= cumulative:
                return topic
        return 'Other'
    
    def _select_random_language(self) -> str:
        """Select language based on realistic distribution."""
        rand = random.random()
        cumulative = 0
        for lang, prob in self.LANGUAGE_DISTRIBUTION.items():
            cumulative += prob
            if rand <= cumulative:
                return lang
        return 'English'
    
    def _create_fin_conversation(
        self,
        conv_id: str,
        tier: str,
        start_date: datetime,
        date_range_seconds: int,
        index: int
    ) -> Dict[str, Any]:
        """Create a Fin AI conversation (no human agent)."""
        topic = self._select_random_topic()
        language = self._select_random_language()
        
        # Random timestamp within range
        offset = random.randint(0, date_range_seconds)
        created_at = int((start_date + timedelta(seconds=offset)).timestamp())
        updated_at = created_at + random.randint(300, 3600)
        
        # Select message template
        messages = self.MESSAGE_TEMPLATES.get(topic, self.MESSAGE_TEMPLATES['Other'])
        message = random.choice(messages)
        
        # Build conversation tags and attributes based on topic
        # REALISTIC: 60% of conversations have NO custom_attributes (messy data)
        # 40% have clean metadata (well-tagged)
        has_metadata = random.random() < 0.40
        
        tags = []
        custom_attrs = {
            'Language': language,
            'Fin AI Agent: Preview': True,
            'Copilot used': False
        }
        conversation_topics = []
        
        if has_metadata:
            # Clean metadata (40% of conversations)
            if topic == 'Billing':
                tags.append('Refund - Requests')
                custom_attrs['Category'] = 'Billing'  # ✅ Use 'Category' key
                custom_attrs['Reason for contact'] = 'Billing'  # ✅ Standard Intercom field
                conversation_topics.append('refund')
                conversation_topics.append('subscription')
            elif topic == 'Product Question':
                custom_attrs['Category'] = 'Product Question'
                custom_attrs['Reason for contact'] = 'Product Question'
                conversation_topics.append('domain')
                conversation_topics.append('publish')
            elif topic == 'Bug':
                custom_attrs['Category'] = 'Bug'
                custom_attrs['Reason for contact'] = 'Bug'
                tags.append('Bug')
                conversation_topics.append('export')
                conversation_topics.append('credits')
            elif topic == 'Account':
                custom_attrs['Category'] = 'Account'
                custom_attrs['Reason for contact'] = 'Account'
                conversation_topics.append('reset password')
                conversation_topics.append('google account')
            elif topic == 'Credits':
                tags.append('Gamma 3.0')
                custom_attrs['Category'] = 'Account'
                custom_attrs['Subcategory'] = 'Credits'
                conversation_topics.append('credits')
                conversation_topics.append('api')
        # else: 60% have NO topic metadata (rely on keyword detection)
        
        return {
            'id': conv_id,
            'created_at': created_at,
            'updated_at': updated_at,
            'state': 'closed',
            'priority': 'normal',
            'admin_assignee_id': None,  # No human agent for Fin
            'conversation_rating': random.choice([None, None, None, 4, 5]),  # Mostly unrated
            'ai_agent_participated': True,
            'custom_attributes': custom_attrs,
            'statistics': {
                'time_to_admin_reply': None,
                'handling_time': updated_at - created_at,
                'count_conversation_parts': random.randint(2, 8),
                'count_reopens': 0
            },
            'tags': {
                'tags': [{'name': tag} for tag in tags]
            },
            'topics': {
                'topics': [{'name': t} for t in conversation_topics]
            },
            'conversation_topics': [{'name': t} for t in conversation_topics],
            # NOTE: full_text and customer_messages are NOT injected here
            # They should be derived by code under test via extract_conversation_text() and extract_customer_messages()
            'source': {
                'body': f"<p>{message}</p>",
                'author': {
                    'type': 'user',
                    'id': f'user_{index}'
                }
            },
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'id': f'part_1_{conv_id}',
                        'type': 'comment',
                        'body': f'<p>{message}</p>',
                        'author': {'type': 'user', 'id': f'user_{index}'},
                        'created_at': created_at
                    },
                    {
                        'id': f'part_2_{conv_id}',
                        'type': 'comment',
                        'body': '<p>I can help with that! [Support Sal response]</p>',
                        'author': {
                            'type': 'admin',  # ✅ Sal appears as admin in real data
                            'id': 'sal_12345',
                            'name': 'Support Sal',  # ✅ Critical for Sal detection
                            'email': 'sal@gamma.app'
                        },
                        'created_at': created_at + 120
                    }
                ]
            },
            # Add tier info for segmentation (top-level field expected by SegmentationAgent)
            'tier': tier,
            '_test_agent_type': 'fin_ai'
        }
    
    def _create_human_conversation(
        self,
        conv_id: str,
        tier: str,
        start_date: datetime,
        date_range_seconds: int,
        index: int
    ) -> Dict[str, Any]:
        """Create a human-supported conversation."""
        topic = self._select_random_topic()
        language = self._select_random_language()
        
        # Random timestamp
        offset = random.randint(0, date_range_seconds)
        created_at = int((start_date + timedelta(seconds=offset)).timestamp())
        updated_at = created_at + random.randint(1800, 7200)
        
        # Select agent type (70% Horatio, 20% Boldr, 10% Escalated)
        agent_type_rand = random.random()
        if agent_type_rand < 0.70:
            agent_type = 'horatio'
            admin_email = random.choice(self.AGENT_EMAILS['horatio'])
            admin_id = f'horatio_admin_{random.randint(1, 20)}'
        elif agent_type_rand < 0.90:
            agent_type = 'boldr'
            admin_email = random.choice(self.AGENT_EMAILS['boldr'])
            admin_id = f'boldr_admin_{random.randint(1, 10)}'
        else:
            agent_type = 'escalated'
            admin_email = random.choice(self.AGENT_EMAILS['escalated'])
            admin_id = f'escalated_admin_{random.randint(1, 3)}'
        
        # Select message
        messages = self.MESSAGE_TEMPLATES.get(topic, self.MESSAGE_TEMPLATES['Other'])
        message = random.choice(messages)
        
        # Build tags and attributes
        tags = []
        custom_attrs = {
            'Language': language,
            'Fin AI Agent: Preview': False,
            'Copilot used': False
        }
        conversation_topics = []
        
        if topic == 'Billing':
            tags.append('Refund - Requests')
            custom_attrs['Billing'] = 'Refund'
            conversation_topics.append('refund')
            conversation_topics.append('subscription')
        elif topic == 'Product Question':
            custom_attrs['Product Question'] = 'Sites'
            conversation_topics.append('domain')
            conversation_topics.append('publish')
        elif topic == 'Bug':
            custom_attrs['Bug'] = 'Export'
            conversation_topics.append('export pdf')
            conversation_topics.append('credits')
        elif topic == 'Account':
            custom_attrs['Account'] = 'Password Reset'
            conversation_topics.append('reset password')
        elif topic == 'Credits':
            tags.append('Gamma 3.0')
            custom_attrs['Credits'] = 'How credits work'
            conversation_topics.append('credits')
        
        # Rating (30% of conversations rated)
        rating = None
        if random.random() < 0.30:
            rating = random.choice([3, 4, 4, 5, 5])  # Mostly positive
        
        return {
            'id': conv_id,
            'created_at': created_at,
            'updated_at': updated_at,
            'state': 'closed',
            'priority': 'normal',
            'admin_assignee_id': admin_id,
            'conversation_rating': rating,
            'ai_agent_participated': True,  # ALL paid conversations start with Fin, then escalate to human
            'custom_attributes': custom_attrs,
            'statistics': {
                'time_to_admin_reply': random.randint(300, 3600),
                'handling_time': updated_at - created_at,
                'count_conversation_parts': random.randint(3, 12),
                'count_reopens': random.choice([0, 0, 0, 1])  # Rarely reopened
            },
            'tags': {
                'tags': [{'name': tag} for tag in tags]
            },
            'topics': {
                'topics': [{'name': t} for t in conversation_topics]
            },
            'conversation_topics': [{'name': t} for t in conversation_topics],
            # NOTE: full_text and customer_messages are NOT injected here
            # They should be derived by code under test via extract_conversation_text() and extract_customer_messages()
            'source': {
                'body': f"<p>{message}</p>",
                'author': {
                    'type': 'user',
                    'id': f'user_{index}',
                    'email': f'customer_{index}@example.com'
                }
            },
            'conversation_parts': {
                'conversation_parts': [
                    {
                        'id': f'part_1_{conv_id}',
                        'type': 'comment',
                        'body': f'<p>{message}</p>',
                        'author': {'type': 'user', 'id': f'user_{index}'},
                        'created_at': created_at
                    },
                    {
                        'id': f'part_2_{conv_id}',
                        'type': 'comment',
                        'body': '<p>Thanks for reaching out! Let me help with that.</p>',
                        'author': {
                            'type': 'admin',
                            'id': admin_id,
                            'email': admin_email
                        },
                        'created_at': created_at + 600
                    }
                ]
            },
            'tier': tier,
            '_test_agent_type': agent_type
        }
    
    def _matches_agent_filter(self, conversation: Dict[str, Any], agent_filter: str) -> bool:
        """Check if generated conversation matches requested agent filter."""
        agent_type = conversation.get('_test_agent_type')
        
        if agent_filter in ('horatio', 'boldr', 'escalated'):
            return agent_type == agent_filter
        if agent_filter in ('fin', 'fin_ai', 'ai', 'support_sal'):
            return agent_type == 'fin_ai'
        if agent_filter in ('all', 'any', 'team'):
            return True
        
        # Unknown filters default to including the conversation
        return True
    
    def _log_distribution(self, conversations: List[Dict]) -> None:
        """Log the distribution of generated conversations."""
        tier_counts = defaultdict(int)
        topic_counts = defaultdict(int)
        agent_counts = defaultdict(int)
        
        for conv in conversations:
            tier = conv.get('tier', 'Unknown')
            tier_counts[tier] += 1
            
            if conv.get('ai_agent_participated'):
                agent_counts['fin_ai'] += 1
            elif '_test_agent_type' in conv:
                agent_counts[conv['_test_agent_type']] += 1
            else:
                agent_counts['unknown'] += 1
            
            # Extract topic from custom_attributes
            attrs = conv.get('custom_attributes', {})
            for key in ['Billing', 'Product Question', 'Bug', 'Account', 'Credits']:
                if key in attrs:
                    topic_counts[key] += 1
                    break
            else:
                topic_counts['Other'] += 1
        
        self.logger.info(f"   Tier distribution: {dict(tier_counts)}")
        self.logger.info(f"   Topic distribution: {dict(topic_counts)}")
        self.logger.info(f"   Agent distribution: {dict(agent_counts)}")


def generate_test_data_for_mode(
    analysis_mode: str,
    count: int = 100,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to generate test data for a specific analysis mode.
    
    Args:
        analysis_mode: Type of analysis (voice-of-customer, agent-performance, etc.)
        count: Number of conversations
        start_date: Start date
        end_date: End date
        
    Returns:
        List of test conversations
    """
    generator = TestDataGenerator()
    
    # Adjust parameters based on analysis mode
    if 'agent-performance' in analysis_mode:
        # Agent performance needs human-supported conversations
        return generator.generate_conversations(
            count=count,
            start_date=start_date,
            end_date=end_date,
            include_free_tier=False,  # Only paid tier for agent analysis
            include_paid_tier=True
        )
    elif 'voice-of-customer' in analysis_mode or 'voc' in analysis_mode:
        # VoC needs both tiers
        return generator.generate_conversations(
            count=count,
            start_date=start_date,
            end_date=end_date,
            include_free_tier=True,
            include_paid_tier=True
        )
    else:
        # Default: generate both tiers
        return generator.generate_conversations(
            count=count,
            start_date=start_date,
            end_date=end_date
        )

