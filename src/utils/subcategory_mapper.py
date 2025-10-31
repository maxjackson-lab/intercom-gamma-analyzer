"""
Subcategory Mapper - Maps SDK data to Hilary's canonical taxonomy

Purpose:
- Map messy SDK subcategories to clean Hilary taxonomy
- Deduplicate: refund, Refund, Refund - Requests → "Refund"
- Filter out off-topic items (domain in Billing, etc.)
- Preserve hierarchical structure from SDK custom_attributes
- Follow Hilary's Google Sheet taxonomy exactly

Example:
    SDK gives: refund (431), Refund (269), Refund - Requests (147)
    Mapper returns: Refund (847) ← Clean, deduplicated, canonical name
"""

import logging
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class SubcategoryMapper:
    """Maps SDK subcategory data to canonical Hilary taxonomy"""
    
    def __init__(self, taxonomy_manager):
        """
        Initialize mapper with TaxonomyManager
        
        Args:
            taxonomy_manager: TaxonomyManager instance with Hilary's taxonomy
        """
        self.taxonomy_manager = taxonomy_manager
        self.categories = taxonomy_manager.categories
        
        # Build normalization maps for fast lookup
        self._build_normalization_maps()
        
        logger.info("SubcategoryMapper initialized with Hilary's taxonomy")
    
    def _build_normalization_maps(self):
        """
        Build lookup maps for normalizing SDK values to canonical names.
        
        Creates:
        - subcategory_lookup: {category: {normalized_name: canonical_name}}
        - Handles case-insensitive matching and common variations
        """
        self.subcategory_lookup = {}
        
        for category_name, category in self.categories.items():
            self.subcategory_lookup[category_name] = {}
            
            for subcat in category.subcategories:
                canonical_name = subcat.name
                
                # Add exact match
                self.subcategory_lookup[category_name][canonical_name.lower()] = canonical_name
                
                # Add common variations
                # "Refund - Requests" → "Refund"
                # "refund" → "Refund"
                # "Refund Request" → "Refund"
                base_name = canonical_name.split(' - ')[0].split(':')[0].strip()
                self.subcategory_lookup[category_name][base_name.lower()] = canonical_name
                
                # Add keyword variations
                for keyword in subcat.keywords:
                    if len(keyword) > 3:  # Skip very short keywords
                        self.subcategory_lookup[category_name][keyword.lower()] = canonical_name
        
        logger.info(f"Built normalization maps for {len(self.subcategory_lookup)} categories")
    
    def normalize_subcategory_name(self, category: str, sdk_value: str) -> Optional[str]:
        """
        Normalize an SDK subcategory value to canonical Hilary taxonomy name.
        
        Args:
            category: Primary category (e.g., "Billing")
            sdk_value: SDK value (e.g., "refund", "Refund - Requests")
            
        Returns:
            Canonical subcategory name (e.g., "Refund") or None if not in taxonomy
        """
        if not sdk_value or category not in self.subcategory_lookup:
            return None
        
        # Normalize SDK value
        normalized = sdk_value.strip().lower()
        
        # Look up canonical name
        canonical = self.subcategory_lookup[category].get(normalized)
        
        if canonical:
            logger.debug(f"Mapped '{sdk_value}' → '{canonical}' (category: {category})")
        
        return canonical
    
    def is_valid_subcategory(self, category: str, subcategory_name: str) -> bool:
        """
        Check if a subcategory belongs to the given category per Hilary's taxonomy.
        
        Args:
            category: Primary category
            subcategory_name: Subcategory to validate
            
        Returns:
            True if subcategory is valid for this category in Hilary's taxonomy
        """
        canonical = self.normalize_subcategory_name(category, subcategory_name)
        return canonical is not None
    
    def map_and_deduplicate_subcategories(
        self,
        category: str,
        raw_subcategories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Map SDK subcategories to Hilary's taxonomy and deduplicate.
        
        Args:
            category: Primary category (e.g., "Billing")
            raw_subcategories: List of raw subcategory dicts from SDK
                              e.g., [{'name': 'refund', 'count': 431, 'source': 'topics'},
                                     {'name': 'Refund', 'count': 269, 'source': 'custom_attributes'}]
        
        Returns:
            Cleaned, deduplicated list with canonical names
            e.g., [{'name': 'Refund', 'count': 847, 'sources': ['topics', 'custom_attributes']}]
        """
        # Group by canonical name
        canonical_groups = defaultdict(lambda: {
            'count': 0,
            'sources': set(),
            'raw_names': set()
        })
        
        for subcat in raw_subcategories:
            sdk_name = subcat.get('name', '')
            count = subcat.get('count', 0)
            source = subcat.get('source', 'unknown')
            
            # Map to canonical name
            canonical = self.normalize_subcategory_name(category, sdk_name)
            
            if canonical:
                # Valid subcategory - add to canonical group
                canonical_groups[canonical]['count'] += count
                canonical_groups[canonical]['sources'].add(source)
                canonical_groups[canonical]['raw_names'].add(sdk_name)
            else:
                # Not in Hilary's taxonomy - filter out
                logger.debug(f"Filtered out '{sdk_name}' - not in {category} taxonomy")
        
        # Convert to clean list
        clean_subcategories = []
        for canonical_name, data in canonical_groups.items():
            clean_subcategories.append({
                'name': canonical_name,
                'count': data['count'],
                'sources': sorted(data['sources']),
                'raw_names': sorted(data['raw_names'])  # For debugging
            })
        
        # Sort by count (highest first)
        clean_subcategories.sort(key=lambda x: x['count'], reverse=True)
        
        logger.info(
            f"{category}: Mapped {len(raw_subcategories)} raw → "
            f"{len(clean_subcategories)} canonical subcategories"
        )
        
        return clean_subcategories
    
    def extract_hierarchical_subcategories(
        self,
        category: str,
        conversations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract clean hierarchical subcategories for a category.
        
        Uses SDK's hierarchical custom_attributes structure:
          "Billing": "Refund" → "Refund": "Given" → "Given Reason": "Did not use"
        
        Maps to Hilary's taxonomy and deduplicates.
        
        Args:
            category: Primary category (e.g., "Billing")
            conversations: Conversations in this category
            
        Returns:
            Hierarchical subcategory structure matching Hilary's taxonomy
        """
        # Collect all subcategory mentions from SDK
        raw_subcategories = []
        subcategory_counts = defaultdict(int)
        
        for conv in conversations:
            conv_id = conv.get('id', 'unknown')
            custom_attrs = conv.get('custom_attributes', {})
            
            # Method 1: Hierarchical structure (custom_attributes[category] = subcategory)
            if isinstance(custom_attrs, dict) and category in custom_attrs:
                subcategory_value = custom_attrs[category]
                if subcategory_value:
                    raw_subcategories.append({
                        'name': subcategory_value,
                        'count': 1,
                        'source': 'custom_attributes',
                        'conv_id': conv_id
                    })
            
            # Method 2: Tags (may have formatted names like "Refund - Requests")
            tags_data = conv.get('tags', {})
            if isinstance(tags_data, dict):
                tags_list = tags_data.get('tags', [])
                for tag in tags_list:
                    tag_name = tag.get('name', tag) if isinstance(tag, dict) else tag
                    if tag_name:
                        raw_subcategories.append({
                            'name': tag_name,
                            'count': 1,
                            'source': 'tags',
                            'conv_id': conv_id
                        })
            
            # Method 3: Topics (Intercom auto-detected, usually lowercase)
            topics_data = conv.get('topics', {})
            if isinstance(topics_data, dict):
                topics_list = topics_data.get('topics', [])
                for topic in topics_list:
                    topic_name = topic.get('name', topic) if isinstance(topic, dict) else topic
                    if topic_name:
                        raw_subcategories.append({
                            'name': topic_name,
                            'count': 1,
                            'source': 'topics',
                            'conv_id': conv_id
                        })
        
        # Map and deduplicate using Hilary's taxonomy
        clean_subcategories = self.map_and_deduplicate_subcategories(category, raw_subcategories)
        
        # Calculate percentages
        total_convs = len(conversations)
        for subcat in clean_subcategories:
            subcat['percentage'] = round(subcat['count'] / total_convs * 100, 1) if total_convs > 0 else 0
        
        return {
            'subcategories': clean_subcategories,
            'total_conversations': total_convs,
            'subcategories_found': len(clean_subcategories)
        }
    
    def get_canonical_name(self, category: str, value: str) -> Optional[str]:
        """
        Get the canonical subcategory name from Hilary's taxonomy.
        
        Args:
            category: Primary category
            value: Any variation of subcategory name
            
        Returns:
            Canonical name from Hilary's taxonomy or None
        """
        return self.normalize_subcategory_name(category, value)

