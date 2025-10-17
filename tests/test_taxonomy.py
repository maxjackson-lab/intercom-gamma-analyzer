"""
Unit tests for taxonomy manager.
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from config.taxonomy import TaxonomyManager, Category, Subcategory


class TestTaxonomyManager:
    """Test cases for taxonomy manager."""
    
    def test_initialization_with_existing_file(self, temp_dir):
        """Test initialization with existing taxonomy file."""
        # Create a test taxonomy file
        taxonomy_file = temp_dir / "test_taxonomy.yaml"
        test_data = {
            'categories': {
                'TestCategory': {
                    'description': 'Test category',
                    'keywords': ['test', 'example'],
                    'confidence_threshold': 0.8,
                    'subcategories': [
                        {
                            'name': 'TestSub',
                            'description': 'Test subcategory',
                            'keywords': ['subtest'],
                            'confidence_threshold': 0.9
                        }
                    ]
                }
            }
        }
        
        with open(taxonomy_file, 'w') as f:
            yaml.dump(test_data, f)
        
        # Initialize manager
        manager = TaxonomyManager(str(taxonomy_file))
        
        assert 'TestCategory' in manager.categories
        assert manager.categories['TestCategory'].description == 'Test category'
        assert len(manager.categories['TestCategory'].subcategories) == 1
    
    def test_initialization_without_file(self, temp_dir):
        """Test initialization without existing file (creates default)."""
        taxonomy_file = temp_dir / "new_taxonomy.yaml"
        
        # Initialize manager (should create default taxonomy)
        manager = TaxonomyManager(str(taxonomy_file))
        
        # Check that file was created
        assert taxonomy_file.exists()
        
        # Check that default categories exist
        expected_categories = [
            'Abuse', 'Account', 'Billing', 'Bug', 'Agent/Buddy',
            'Chargeback', 'Feedback', 'Partnerships', 'Privacy',
            'Product Question', 'Promotions', 'Unknown', 'Workspace'
        ]
        
        for category in expected_categories:
            assert category in manager.categories
    
    def test_get_category(self, taxonomy_manager):
        """Test getting a category by name."""
        billing_category = taxonomy_manager.get_category('Billing')
        
        assert billing_category is not None
        assert billing_category.name == 'Billing'
        assert 'refund' in billing_category.keywords
        assert len(billing_category.subcategories) > 0
    
    def test_get_category_nonexistent(self, taxonomy_manager):
        """Test getting a nonexistent category."""
        category = taxonomy_manager.get_category('Nonexistent')
        assert category is None
    
    def test_get_all_categories(self, taxonomy_manager):
        """Test getting all category names."""
        categories = taxonomy_manager.get_all_categories()
        
        assert len(categories) == 13
        assert 'Billing' in categories
        assert 'Bug' in categories
        assert 'Account' in categories
    
    def test_classify_conversation_by_tags(self, taxonomy_manager, sample_conversation):
        """Test conversation classification by tags."""
        classifications = taxonomy_manager.classify_conversation(sample_conversation)
        
        # Should find billing classification from tags
        billing_classifications = [c for c in classifications if c['category'] == 'Billing']
        assert len(billing_classifications) > 0
        
        # Check confidence and method
        billing_class = billing_classifications[0]
        assert billing_class['confidence'] == 1.0
        assert billing_class['method'] == 'tagged'
    
    def test_classify_conversation_by_topics(self, taxonomy_manager):
        """Test conversation classification by topics."""
        conversation = {
            "tags": {"tags": []},
            "topics": {
                "topics": [
                    {"name": "Bug"},
                    {"name": "Export"}
                ]
            },
            "conversation_parts": {
                "conversation_parts": []
            }
        }
        
        classifications = taxonomy_manager.classify_conversation(conversation)
        
        # Should find bug classification from topics
        bug_classifications = [c for c in classifications if c['category'] == 'Bug']
        assert len(bug_classifications) > 0
    
    def test_classify_conversation_by_text(self, taxonomy_manager):
        """Test conversation classification by text content."""
        conversation = {
            "tags": {"tags": []},
            "topics": {"topics": []},
            "source": {
                "body": "I need help with my account settings and password reset"
            },
            "conversation_parts": {
                "conversation_parts": []
            }
        }
        
        classifications = taxonomy_manager.classify_conversation(conversation)
        
        # Should find account classification from text
        account_classifications = [c for c in classifications if c['category'] == 'Account']
        assert len(account_classifications) > 0
        
        # Check method is text analysis
        account_class = account_classifications[0]
        assert account_class['method'] == 'text_analysis'
        assert account_class['confidence'] < 1.0  # Lower confidence than tagged
    
    def test_classify_conversation_multiple_categories(self, taxonomy_manager):
        """Test conversation classification with multiple categories."""
        conversation = {
            "tags": {
                "tags": [
                    {"name": "billing"},
                    {"name": "bug"}
                ]
            },
            "topics": {
                "topics": [
                    {"name": "Billing"},
                    {"name": "Bug"}
                ]
            },
            "source": {
                "body": "I have a billing issue and a bug report"
            },
            "conversation_parts": {
                "conversation_parts": []
            }
        }
        
        classifications = taxonomy_manager.classify_conversation(conversation)
        
        # Should find both billing and bug classifications
        categories = [c['category'] for c in classifications]
        assert 'Billing' in categories
        assert 'Bug' in categories
    
    def test_extract_conversation_text(self, taxonomy_manager):
        """Test conversation text extraction."""
        conversation = {
            "source": {
                "body": "Initial message"
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "First response"
                    },
                    {
                        "body": "Second response"
                    }
                ]
            }
        }
        
        text = taxonomy_manager._extract_conversation_text(conversation)
        
        assert "Initial message" in text
        assert "First response" in text
        assert "Second response" in text
    
    def test_extract_tags(self, taxonomy_manager):
        """Test tag extraction."""
        conversation = {
            "tags": {
                "tags": [
                    {"name": "billing"},
                    {"name": "refund"},
                    "simple_tag"
                ]
            }
        }
        
        tags = taxonomy_manager._extract_tags(conversation)
        
        assert len(tags) == 3
        assert "billing" in tags
        assert "refund" in tags
        assert "simple_tag" in tags
    
    def test_extract_topics(self, taxonomy_manager):
        """Test topic extraction."""
        conversation = {
            "topics": {
                "topics": [
                    {"name": "Billing"},
                    {"name": "Refund"},
                    "simple_topic"
                ]
            }
        }
        
        topics = taxonomy_manager._extract_topics(conversation)
        
        assert len(topics) == 3
        assert "Billing" in topics
        assert "Refund" in topics
        assert "simple_topic" in topics
    
    def test_classify_by_keyword(self, taxonomy_manager):
        """Test classification by keyword."""
        # Test with billing keyword
        classification = taxonomy_manager._classify_by_keyword("billing", "test_method")
        
        assert classification is not None
        assert classification['category'] == 'Billing'
        assert classification['confidence'] == 1.0
        assert classification['method'] == 'test_method'
    
    def test_classify_by_keyword_nonexistent(self, taxonomy_manager):
        """Test classification with nonexistent keyword."""
        classification = taxonomy_manager._classify_by_keyword("nonexistent_keyword", "test_method")
        assert classification is None
    
    def test_calculate_text_confidence(self, taxonomy_manager):
        """Test text confidence calculation."""
        billing_category = taxonomy_manager.get_category('Billing')
        
        # Text with billing keywords
        text_with_keywords = "I need help with billing and payment issues"
        confidence = taxonomy_manager._calculate_text_confidence(text_with_keywords, billing_category)
        
        assert confidence > 0.0
        assert confidence <= 1.0
        
        # Text without keywords
        text_without_keywords = "This is completely unrelated text"
        confidence = taxonomy_manager._calculate_text_confidence(text_without_keywords, billing_category)
        
        assert confidence == 0.0
    
    def test_find_matching_keywords(self, taxonomy_manager):
        """Test finding matching keywords in text."""
        billing_category = taxonomy_manager.get_category('Billing')
        text = "I have billing issues and need a refund"
        
        matching = taxonomy_manager._find_matching_keywords(text, billing_category.keywords)
        
        assert len(matching) > 0
        assert "billing" in matching
        assert "refund" in matching
    
    def test_save_and_load_taxonomy(self, temp_dir):
        """Test saving and loading taxonomy to/from YAML."""
        taxonomy_file = temp_dir / "test_save_load.yaml"
        
        # Create manager with default taxonomy
        manager1 = TaxonomyManager(str(taxonomy_file))
        
        # Modify a category
        manager1.categories['Billing'].description = "Modified description"
        
        # Save to file
        manager1._save_to_yaml()
        
        # Create new manager from file
        manager2 = TaxonomyManager(str(taxonomy_file))
        
        # Check that modification was saved
        assert manager2.categories['Billing'].description == "Modified description"
    
    def test_billing_category_structure(self, taxonomy_manager):
        """Test Billing category structure."""
        billing = taxonomy_manager.get_category('Billing')
        
        assert billing.name == 'Billing'
        assert 'refund' in billing.keywords
        assert 'billing' in billing.keywords
        assert 'payment' in billing.keywords
        
        # Check subcategories
        subcategory_names = [sub.name for sub in billing.subcategories]
        assert 'Refund' in subcategory_names
        assert 'Subscription' in subcategory_names
        assert 'Invoice' in subcategory_names
    
    def test_bug_category_structure(self, taxonomy_manager):
        """Test Bug category structure."""
        bug = taxonomy_manager.get_category('Bug')
        
        assert bug.name == 'Bug'
        assert 'bug' in bug.keywords
        assert 'error' in bug.keywords
        assert 'broken' in bug.keywords
        
        # Check subcategories
        subcategory_names = [sub.name for sub in bug.subcategories]
        assert 'Export' in subcategory_names
        assert 'Account' in subcategory_names
        assert 'API' in subcategory_names
    
    def test_agent_buddy_category_structure(self, taxonomy_manager):
        """Test Agent/Buddy category structure."""
        agent = taxonomy_manager.get_category('Agent/Buddy')
        
        assert agent.name == 'Agent/Buddy'
        assert 'agent' in agent.keywords
        assert 'buddy' in agent.keywords
        assert 'fin' in agent.keywords
        
        # Check subcategories
        subcategory_names = [sub.name for sub in agent.subcategories]
        assert 'Agent Question' in subcategory_names
        assert 'Agent Feedback' in subcategory_names
    
    def test_classification_deduplication(self, taxonomy_manager):
        """Test that duplicate classifications are removed."""
        conversation = {
            "tags": {
                "tags": [
                    {"name": "billing"},
                    {"name": "Billing"}  # Duplicate with different case
                ]
            },
            "topics": {
                "topics": [
                    {"name": "Billing"}
                ]
            },
            "source": {
                "body": "billing billing billing"  # Multiple text matches
            },
            "conversation_parts": {
                "conversation_parts": []
            }
        }
        
        classifications = taxonomy_manager.classify_conversation(conversation)
        
        # Should have unique classifications only
        unique_keys = set()
        for classification in classifications:
            key = f"{classification['category']}_{classification['subcategory']}"
            assert key not in unique_keys, f"Duplicate classification found: {key}"
            unique_keys.add(key)
    
    def test_classification_confidence_ordering(self, taxonomy_manager):
        """Test that classifications are ordered by confidence."""
        conversation = {
            "tags": {
                "tags": [
                    {"name": "billing"}  # High confidence (tagged)
                ]
            },
            "source": {
                "body": "I have some account issues"  # Lower confidence (text)
            },
            "conversation_parts": {
                "conversation_parts": []
            }
        }
        
        classifications = taxonomy_manager.classify_conversation(conversation)
        
        # Should be ordered by confidence (highest first)
        for i in range(len(classifications) - 1):
            assert classifications[i]['confidence'] >= classifications[i + 1]['confidence']






