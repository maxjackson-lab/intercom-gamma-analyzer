"""
Example Extractor Module - Handles extraction of example conversations
"""

from typing import Dict, Any, List
from src.config.settings import settings


class ExampleConversationExtractor:
    """Handles extraction of example conversations for analysis"""
    
    @staticmethod
    def extract_performance_examples(conversations: List[Dict], metrics: Dict, category_perf: Dict) -> Dict[str, List[Dict]]:
        """Extract example conversations showing strengths and development areas"""
        
        examples = {
            'high_fcr_examples': [],
            'escalation_examples': [],
            'long_resolution_examples': []
        }
        
        # Find examples of successful FCR
        fcr_convs = [
            c for c in conversations 
            if c.get('state') == 'closed' and c.get('count_reopens', 0) == 0
        ]
        if fcr_convs:
            examples['high_fcr_examples'] = [
                {
                    'id': c.get('id'),
                    'category': ExampleConversationExtractor._get_category(c),
                    'resolution_hours': ExampleConversationExtractor._get_resolution_hours(c),
                    'intercom_url': ExampleConversationExtractor._build_intercom_url(c.get('id'))
                }
                for c in fcr_convs[:3]
            ]
        
        # Find examples of escalations
        escalated = [
            c for c in conversations
            if any(name in str(c.get('full_text', '')).lower() 
                  for name in ['dae-ho', 'max jackson', 'hilary'])
        ]
        if escalated:
            examples['escalation_examples'] = [
                {
                    'id': c.get('id'),
                    'category': ExampleConversationExtractor._get_category(c),
                    'why_escalated': 'Complex issue requiring senior expertise',
                    'intercom_url': ExampleConversationExtractor._build_intercom_url(c.get('id'))
                }
                for c in escalated[:3]
            ]
        
        return examples
    
    @staticmethod
    def _build_intercom_url(conversation_id: str) -> str:
        """Build Intercom conversation URL with workspace ID"""
        workspace_id = settings.intercom_workspace_id
        
        if not workspace_id or workspace_id == "your-workspace-id-here":
            return f"https://app.intercom.com/a/apps/[WORKSPACE_ID]/inbox/inbox/{conversation_id}"
        return f"https://app.intercom.com/a/apps/{workspace_id}/inbox/inbox/{conversation_id}"
    
    @staticmethod
    def _get_category(conv: Dict) -> str:
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
    
    @staticmethod
    def _get_resolution_hours(conv: Dict) -> float:
        """Calculate resolution time in hours"""
        created = conv.get('created_at')
        updated = conv.get('updated_at')
        
        if not (created and updated):
            return 0
        
        if isinstance(created, (int, float)):
            return (updated - created) / 3600
        else:
            return (updated - created).total_seconds() / 3600