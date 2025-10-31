"""
Metrics Calculator Module - Handles performance metrics calculations
"""

import numpy as np
from typing import Dict, Any, List
from datetime import datetime
from src.utils.conversation_utils import extract_conversation_text


class PerformanceMetricsCalculator:
    """Handles calculation of performance metrics for agent analysis"""
    
    @staticmethod
    def calculate_performance_metrics(conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate operational performance metrics"""
        
        # FCR (First Contact Resolution)
        closed_convs = [c for c in conversations if c.get('state') == 'closed']
        fcr_convs = [c for c in closed_convs if c.get('count_reopens', 0) == 0]
        fcr_rate = len(fcr_convs) / len(closed_convs) if closed_convs else 0
        
        # Resolution time
        resolution_times = []
        for conv in closed_convs:
            created = conv.get('created_at')
            updated = conv.get('updated_at')
            if created and updated:
                if isinstance(created, (int, float)):
                    created_dt = datetime.fromtimestamp(created)
                    updated_dt = datetime.fromtimestamp(updated)
                else:
                    created_dt = created
                    updated_dt = updated
                hours = (updated_dt - created_dt).total_seconds() / 3600
                resolution_times.append(hours)
        
        # Escalations (to senior staff)
        escalated = [
            c for c in conversations
            if any(name in extract_conversation_text(c, clean_html=True).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary'])
        ]
        escalation_rate = len(escalated) / len(conversations) if conversations else 0
        
        # Response time
        response_times = [
            c.get('time_to_admin_reply', 0) / 3600 for c in conversations
            if c.get('time_to_admin_reply')
        ]
        
        # Complexity
        avg_parts = np.mean([c.get('count_conversation_parts', 0) for c in conversations]) if conversations else 0
        
        return {
            'fcr_rate': fcr_rate,
            'fcr_count': len(fcr_convs),
            'total_closed': len(closed_convs),
            'median_resolution_hours': np.median(resolution_times) if resolution_times else 0,
            'p90_resolution_hours': np.percentile(resolution_times, 90) if resolution_times else 0,
            'escalation_rate': escalation_rate,
            'escalated_count': len(escalated),
            'median_response_hours': np.median(response_times) if response_times else 0,
            'avg_conversation_complexity': avg_parts,
            'resolution_time_distribution': {
                'under_4h': sum(1 for t in resolution_times if t < 4) / len(resolution_times) * 100 if resolution_times else 0,
                'under_24h': sum(1 for t in resolution_times if t < 24) / len(resolution_times) * 100 if resolution_times else 0,
                'over_48h': sum(1 for t in resolution_times if t > 48) / len(resolution_times) * 100 if resolution_times else 0
            }
        }
    
    @staticmethod
    def calculate_resolution_hours(conv: Dict) -> float:
        """Calculate resolution time in hours"""
        created = conv.get('created_at')
        updated = conv.get('updated_at')
        
        if not (created and updated):
            return 0
        
        if isinstance(created, (int, float)):
            return (updated - created) / 3600
        else:
            return (updated - created).total_seconds() / 3600