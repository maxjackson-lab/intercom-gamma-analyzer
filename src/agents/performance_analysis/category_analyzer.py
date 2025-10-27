"""
Category Analyzer Module - Handles performance analysis by category
"""

import numpy as np
from typing import Dict, Any, List
from collections import defaultdict


class CategoryPerformanceAnalyzer:
    """Handles analysis of performance by category and subcategory"""
    
    @staticmethod
    def analyze_category_performance(conversations: List[Dict]) -> Dict[str, Dict]:
        """Analyze performance by category (Tech, API, Bug, etc.)"""
        category_metrics = defaultdict(lambda: {
            'total': 0,
            'fcr_count': 0,
            'escalated_count': 0,
            'resolution_times': []
        })
        
        for conv in conversations:
            # Get category from tags or custom attributes
            tags = [t.get('name', t) if isinstance(t, dict) else t 
                   for t in conv.get('tags', {}).get('tags', [])]
            
            # Determine category
            category = 'Other'
            for tag in tags:
                tag_lower = str(tag).lower()
                if 'bug' in tag_lower or 'technical' in tag_lower:
                    category = 'Technical Troubleshooting'
                    break
                elif 'api' in tag_lower:
                    category = 'API Issues'
                    break
                elif 'billing' in tag_lower:
                    category = 'Billing'
                    break
            
            # Calculate metrics for this category
            category_metrics[category]['total'] += 1
            
            if conv.get('state') == 'closed' and conv.get('count_reopens', 0) == 0:
                category_metrics[category]['fcr_count'] += 1
            
            if any(name in str(conv.get('full_text', '')).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary']):
                category_metrics[category]['escalated_count'] += 1
            
            # Resolution time
            if conv.get('state') == 'closed':
                created = conv.get('created_at')
                updated = conv.get('updated_at')
                if created and updated:
                    if isinstance(created, (int, float)):
                        hours = (updated - created) / 3600
                    else:
                        hours = (updated - created).total_seconds() / 3600
                    category_metrics[category]['resolution_times'].append(hours)
        
        # Calculate rates
        performance_by_category = {}
        for category, stats in category_metrics.items():
            if stats['total'] >= 5:  # Only include categories with meaningful sample
                fcr_rate = stats['fcr_count'] / stats['total'] if stats['total'] > 0 else 0
                escalation_rate = stats['escalated_count'] / stats['total'] if stats['total'] > 0 else 0
                median_resolution = np.median(stats['resolution_times']) if stats['resolution_times'] else 0
                
                performance_by_category[category] = {
                    'volume': stats['total'],
                    'fcr_rate': fcr_rate,
                    'escalation_rate': escalation_rate,
                    'median_resolution_hours': median_resolution
                }
        
        return performance_by_category
    
    @staticmethod
    def get_category_from_conversation(conv: Dict) -> str:
        """Get category for a conversation"""
        tags = [t.get('name', t) if isinstance(t, dict) else t 
               for t in conv.get('tags', {}).get('tags', [])]
        
        for tag in tags:
            tag_lower = str(tag).lower()
            if 'bug' in tag_lower or 'technical' in tag_lower:
                return 'Technical Troubleshooting'
            elif 'api' in tag_lower:
                return 'API Issues'
            elif 'billing' in tag_lower:
                return 'Billing'
        
        return 'Other'