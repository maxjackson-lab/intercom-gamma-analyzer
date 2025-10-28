"""
Admin Profile Cache Service

Caches Intercom admin profiles to avoid repeated API calls and extract
nested/work emails from admin objects.
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from functools import wraps

from src.models.agent_performance_models import AdminProfile
from src.services.duckdb_storage import DuckDBStorage

logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries=3, base_delay=1.0):
    """Decorator for retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.logger.warning(f"All {max_retries} retry attempts failed for {func.__name__}: {e}")
                        raise
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
            return None
        return wrapper
    return decorator


class AdminProfileCache:
    """Cache Intercom admin profiles with session and persistent storage"""
    
    def __init__(self, intercom_service, duckdb_storage: Optional[DuckDBStorage] = None):
        """
        Initialize admin profile cache.
        
        Args:
            intercom_service: IntercomService instance for API calls
            duckdb_storage: Optional DuckDB storage for persistent caching
        """
        self.intercom_service = intercom_service
        self.storage = duckdb_storage
        self.session_cache: Dict[str, AdminProfile] = {}  # In-memory cache for current session
        self.cache_ttl_days = 7  # Refresh profiles older than 7 days
        self.logger = logging.getLogger(__name__)
        
        # Ensure DuckDB schema is created if storage is provided
        if self.storage:
            try:
                self.storage.ensure_schema()
            except Exception as e:
                self.logger.warning(f"Failed to ensure DuckDB schema: {e}")
        
    async def get_admin_profile(
        self, 
        admin_id: str, 
        client = None,  # client parameter kept for backward compatibility but not used
        public_email: Optional[str] = None
    ) -> AdminProfile:
        """
        Get admin profile with caching.
        
        Args:
            admin_id: Intercom admin ID
            client: Deprecated, kept for backward compatibility
            public_email: Optional public/display email from conversation
            
        Returns:
            AdminProfile with work email and vendor information
        """
        # Check session cache first
        if admin_id in self.session_cache:
            self.logger.debug(f"Admin {admin_id} found in session cache")
            return self.session_cache[admin_id]
        
        # Check DuckDB cache
        if self.storage:
            cached = self._get_from_db(admin_id)
            if cached and self._is_cache_valid(cached):
                self.logger.debug(f"Admin {admin_id} found in DB cache")
                self.session_cache[admin_id] = cached
                return cached
        
        # Fetch from Intercom API
        profile = await self._fetch_from_api(admin_id, client, public_email)
        
        # Cache it
        self.session_cache[admin_id] = profile
        if self.storage:
            self._store_in_db(profile)
        
        return profile
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def _fetch_from_api(
        self,
        admin_id: str,
        client,  # No longer needs to be httpx.AsyncClient
        public_email: Optional[str] = None
    ) -> AdminProfile:
        """Fetch admin profile from Intercom API with retry/backoff using SDK"""
        try:
            self.logger.info(f"Fetching admin profile from API: {admin_id}")
            
            # Use SDK to fetch admin details
            admin = await self.intercom_service.client.admins.find(admin_id)
            
            # Convert SDK model to dict
            data = self.intercom_service._model_to_dict(admin)
            
            # Log full API response for debugging
            self.logger.debug(f"Admin API response for {admin_id}: {data}")
            
            # Enhanced email extraction with fallback and validation
            work_email = data.get('email', '').strip() if data.get('email') else ''
            
            # CRITICAL: Log if work_email is empty
            if not work_email:
                self.logger.warning(
                    f"Admin API returned NO WORK EMAIL for {admin_id} "
                    f"(name: {data.get('name')}, public_email: {public_email})"
                )
                # Try to infer vendor from public_email if available
                if public_email:
                    self.logger.info(f"Attempting vendor detection from public_email: {public_email}")
                    inferred_vendor = self._identify_vendor(public_email)
                    if inferred_vendor != 'unknown':
                        self.logger.info(f"Inferred vendor from public_email: {inferred_vendor}")
            
            # If no work email from API, use public_email but log warning
            if not work_email and public_email:
                work_email = public_email.strip()
                self.logger.warning(
                    f"Using public_email as work_email for admin {admin_id} "
                    f"(API returned no work email - vendor detection may fail!)"
                )
            
            # Validate email with basic regex
            if work_email and not self._validate_email(work_email):
                self.logger.warning(f"Invalid email format for admin {admin_id}: {work_email}")
                work_email = ''
            
            name = data.get('name', 'Unknown')
            
            # Determine vendor from work_email (or public_email as last resort)
            vendor = self._identify_vendor(work_email)
            
            # If vendor is unknown but we have public_email, try that too
            if vendor == 'unknown' and public_email and public_email != work_email:
                vendor_from_public = self._identify_vendor(public_email)
                if vendor_from_public != 'unknown':
                    vendor = vendor_from_public
                    self.logger.info(f"Vendor identified from public_email: {vendor}")
            
            profile = AdminProfile(
                id=admin_id,
                name=name,
                email=work_email,
                public_email=public_email or work_email,
                vendor=vendor,
                active=data.get('away_mode_enabled', False) is False,
                cached_at=datetime.now()
            )
            
            self.logger.info(
                f"Fetched admin {name} ({admin_id}): "
                f"work_email={work_email}, public_email={public_email}, vendor={profile.vendor}"
            )
            
            return profile
            
        except Exception as e:
            # SDK ApiError will be caught here
            from intercom.core.api_error import ApiError
            if isinstance(e, ApiError):
                self.logger.warning(f"API error fetching admin {admin_id}: {e.status_code}")
                if e.body:
                    self.logger.warning(f"Response body: {str(e.body)[:500]}")
            else:
                self.logger.warning(f"Failed to fetch admin {admin_id}: {e}")
            return self._create_fallback_profile(admin_id, None, public_email)
    
    def _extract_vendor_from_email(self, email: str) -> Optional[str]:
        """
        Extract vendor name from email domain.
        
        Known vendor domains:
        - @horatio.ai, @hirehoratio.co → 'horatio'
        - @boldr.co, @boldr.com, @boldrimpact.com → 'boldr'
        - @escalated.* → 'escalated'
        
        Returns None for public domains (gmail, yahoo, etc.)
        
        Args:
            email: Email address to extract vendor from
            
        Returns:
            Vendor name or None for public domains or invalid emails
        """
        if not email or '@' not in email:
            return None
        
        domain = email.split('@')[1].lower()
        
        # Public domains - not vendor-specific
        public_domains = {'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com'}
        if domain in public_domains:
            return None
        
        # Known vendor patterns
        if 'horatio' in domain:
            return 'horatio'
        if 'boldr' in domain:
            return 'boldr'
        if 'escalated' in domain:
            return 'escalated'
        if 'gamma' in domain:
            return 'gamma'
        
        # Unknown vendor domain - return first part of domain
        return domain.split('.')[0]
    
    def _identify_vendor(self, email: str) -> str:
        """
        Identify vendor from email domain using exact domain matching.
        
        Args:
            email: Email address to classify
            
        Returns:
            Vendor name: 'horatio', 'boldr', 'gamma', 'escalated', or 'unknown'
        """
        if not email or not isinstance(email, str):
            return "unknown"
        
        email_lower = email.lower().strip()
        
        # Extract domain from email
        if '@' not in email_lower:
            return "unknown"
        
        try:
            domain = email_lower.split('@')[-1].strip()
        except Exception as e:
            self.logger.warning(f"Failed to parse domain from email {email}: {e}")
            return "unknown"
        
        # Known vendor domains (exact match only)
        vendor_domains = {
            'hirehoratio.co': 'horatio',
            'horatio.com': 'horatio',
            'horatio.ai': 'horatio',
            'boldrimpact.com': 'boldr',
            'boldr.com': 'boldr',
            'boldr.co': 'boldr',
            'gamma.app': 'gamma',
            'escalated.com': 'escalated',
            'escalated.io': 'escalated',
        }
        
        return vendor_domains.get(domain, 'unknown')
    
    def _validate_email(self, email: str) -> bool:
        """
        Validate email format with basic regex.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        import re
        # Basic email regex - checks for user@domain.tld pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))
    
    def _create_fallback_profile(
        self,
        admin_id: str,
        conversation_parts: Optional[List[Dict]] = None,
        public_email: Optional[str] = None
    ) -> AdminProfile:
        """
        Create fallback profile when API fetch fails.
        
        Attempts to derive vendor from:
        1. Email domain in conversation_parts (if provided)
        2. public_email parameter
        3. Default to 'unknown'
        
        Args:
            admin_id: Admin ID
            conversation_parts: Optional list of conversation parts to extract email from
            public_email: Optional fallback email
            
        Returns:
            AdminProfile with derived vendor information
        """
        vendor = None
        email = None
        
        # Try to extract vendor from conversation parts
        if conversation_parts:
            for part in conversation_parts:
                author = part.get('author', {})
                if author.get('type') == 'admin' and str(author.get('id')) == str(admin_id):
                    email = author.get('email')
                    if email:
                        vendor = self._extract_vendor_from_email(email)
                        if vendor:
                            self.logger.info(
                                f"Derived vendor '{vendor}' from conversation_parts email for admin {admin_id}"
                            )
                        break
        
        # Fallback to public_email if no vendor found yet
        if not vendor and public_email:
            email = email or public_email
            vendor = self._extract_vendor_from_email(public_email)
            if vendor:
                self.logger.info(
                    f"Derived vendor '{vendor}' from public_email for admin {admin_id}"
                )
        
        # Validate email
        if email and not self._validate_email(email):
            self.logger.warning(f"Invalid email format for admin {admin_id}: {email}")
            email = public_email or f'admin{admin_id}@unknown.com'
        elif not email:
            email = public_email or f'admin{admin_id}@unknown.com'
        
        # Log vendor attribution result
        if vendor:
            self.logger.info(f"Successfully attributed vendor '{vendor}' for admin {admin_id}")
        else:
            self.logger.warning(
                f"Vendor attribution gap for admin {admin_id} - using 'unknown'. "
                f"Email: {email}"
            )
            vendor = 'unknown'
        
        return AdminProfile(
            id=admin_id,
            name=f'Admin {admin_id}',
            email=email,
            public_email=public_email or email,
            vendor=vendor,
            active=True,
            cached_at=datetime.now()
        )
    
    def _get_from_db(self, admin_id: str) -> Optional[AdminProfile]:
        """Retrieve admin profile from DuckDB cache"""
        if not self.storage or not self.storage.conn:
            return None
        
        try:
            # Ensure schema exists before reading
            self.storage.ensure_schema()
            
            result = self.storage.conn.execute(
                """
                SELECT admin_id, name, email, public_email, vendor, active, last_updated
                FROM admin_profiles
                WHERE admin_id = ?
                """,
                [admin_id]
            ).fetchone()
            
            if result:
                return AdminProfile(
                    id=result[0],
                    name=result[1],
                    email=result[2],
                    public_email=result[3],
                    vendor=result[4],
                    active=result[5],
                    cached_at=result[6]
                )
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error retrieving admin {admin_id} from DB: {e}")
            return None
    
    def _store_in_db(self, profile: AdminProfile):
        """Store admin profile in DuckDB cache"""
        if not self.storage or not self.storage.conn:
            return
        
        try:
            # Ensure schema exists before writing
            self.storage.ensure_schema()
            
            now = datetime.now()
            
            # Use INSERT OR REPLACE pattern
            self.storage.conn.execute(
                """
                INSERT OR REPLACE INTO admin_profiles 
                (admin_id, name, email, public_email, vendor, active, first_seen, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    profile.id,
                    profile.name,
                    profile.email,
                    profile.public_email,
                    profile.vendor,
                    profile.active,
                    now,  # first_seen (will be overwritten if exists)
                    now   # last_updated
                ]
            )
            
            self.logger.debug(f"Stored admin {profile.id} in DB cache")
            
        except Exception as e:
            self.logger.warning(f"Error storing admin {profile.id} in DB: {e}")
    
    def _is_cache_valid(self, profile: AdminProfile) -> bool:
        """Check if cached profile is still valid"""
        if not profile.cached_at:
            return False
        
        age = datetime.now() - profile.cached_at
        return age.days < self.cache_ttl_days
    
    def clear_session_cache(self):
        """Clear the in-memory session cache"""
        self.session_cache.clear()
        self.logger.info("Session cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'session_cache_size': len(self.session_cache),
            'cache_ttl_days': self.cache_ttl_days
        }

