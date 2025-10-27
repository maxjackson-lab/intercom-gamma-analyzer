"""
Data Extractor Module - Handles conversation data extraction and admin profile lookups
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ConversationDataExtractor:
    """Handles extraction of data from conversations and admin profiles"""
    
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
    
    async def extract_admin_profiles(self, conversations: List[Dict], agent_filter: str) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
        """
        Extract admin profiles from conversations using tool-based lookups
        
        Returns:
            Tuple of (admin_details_map, all_admins_seen)
        """
        logger.info("Extracting admin profiles from conversations...")
        admin_details_map = {}
        all_admins_seen = {}  # Track ALL admins for debugging

        # Collect unique admin IDs and their public emails
        unique_admins = {}
        for conv in conversations:
            admin_ids = self._extract_admin_ids(conv)
            for admin_id in admin_ids:
                if admin_id not in unique_admins:
                    public_email = self._get_public_email_for_admin(conv, admin_id)
                    unique_admins[admin_id] = public_email

        # Use tool-based lookups for admin profiles
        tasks = []
        for admin_id, public_email in unique_admins.items():
            tasks.append(self.tool_registry.execute_tool(
                'lookup_admin_profile',
                admin_id=admin_id,
                public_email=public_email
            ))

        # Execute all lookups in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for (admin_id, public_email), result in zip(unique_admins.items(), results):
            if isinstance(result, Exception):
                logger.warning(f"Tool lookup failed for admin {admin_id}: {result}")
                continue

            if not result.success:
                logger.warning(f"Tool lookup unsuccessful for admin {admin_id}: {result.error_message}")
                continue

            # Extract data from tool result
            data = result.data
            admin_id_canonical = data['admin_id']  # Use admin_id field (id is deprecated)
            email = data.get('email')
            vendor = data.get('vendor')
            name = data.get('name')

            # Track all admins for debugging
            all_admins_seen[admin_id] = {
                'email': email,
                'vendor': vendor,
                'name': name
            }

            # Only include if vendor matches
            if vendor == agent_filter:
                admin_details_map[admin_id_canonical] = {
                    'id': admin_id_canonical,  # Keep both for compatibility
                    'admin_id': admin_id_canonical,
                    'name': name,
                    'email': email,
                    'vendor': vendor
                }

                # Attach to conversations for grouping (find conversations with this admin)
                for conv in conversations:
                    if admin_id in self._extract_admin_ids(conv):
                        if '_admin_details' not in conv:
                            conv['_admin_details'] = []
                        conv['_admin_details'].append(admin_details_map[admin_id_canonical])

        # Enhanced logging for debugging
        logger.info(f"Found {len(admin_details_map)} {agent_filter} agents")
        logger.info(f"Total unique admins seen: {len(all_admins_seen)}")

        # Log vendor distribution for debugging
        vendor_counts = {}
        for admin_info in all_admins_seen.values():
            vendor = admin_info['vendor']
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1

        logger.info(f"Admin vendor distribution: {vendor_counts}")

        # If no matches, log sample admins for debugging
        if not admin_details_map:
            logger.warning(f"No {agent_filter} agents found! Sample admins seen:")
            for admin_id, info in list(all_admins_seen.items())[:5]:
                logger.warning(
                    f"  Admin {admin_id}: {info['name']} - "
                    f"email={info['email']}, vendor={info['vendor']}"
                )

        return admin_details_map, all_admins_seen
    
    def _extract_admin_ids(self, conv: Dict) -> List[str]:
        """Extract all admin IDs from a conversation"""
        admin_ids = set()
        
        # From conversation_parts
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            author = part.get('author', {})
            if author.get('type') == 'admin' and author.get('id'):
                admin_ids.add(str(author['id']))
        
        # From assignee
        if conv.get('admin_assignee_id'):
            admin_ids.add(str(conv['admin_assignee_id']))
        
        return list(admin_ids)
    
    def _get_public_email_for_admin(self, conv: Dict, admin_id: str) -> Optional[str]:
        """
        Get email for an admin from conversation.
        
        NOTE: This extracts the email directly from conversation_parts, which may be
        the work email (@hirehoratio.co) rather than public email depending on
        Intercom's configuration.
        """
        parts = conv.get('conversation_parts', {}).get('conversation_parts', [])
        for part in parts:
            author = part.get('author', {})
            if author.get('type') == 'admin' and str(author.get('id')) == admin_id:
                email = author.get('email')
                if email:
                    logger.debug(f"Found email for admin {admin_id} in conversation: {email}")
                    return email
        
        # Also check source author
        source = conv.get('source', {})
        if source:
            author = source.get('author', {})
            if author.get('type') == 'admin' and str(author.get('id')) == admin_id:
                email = author.get('email')
                if email:
                    logger.debug(f"Found email for admin {admin_id} in source: {email}")
                    return email
        
        return None