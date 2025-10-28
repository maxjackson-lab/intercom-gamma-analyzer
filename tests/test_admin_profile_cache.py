"""
Tests for AdminProfileCache service.
"""

import pytest
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from intercom.core.api_error import ApiError

from src.services.admin_profile_cache import AdminProfileCache
from src.models.agent_performance_models import AdminProfile


@pytest.fixture
def mock_intercom_service():
    """Mock Intercom SDK service"""
    service = Mock()
    service.client = Mock()
    service.client.admins = Mock()
    service._model_to_dict = Mock(side_effect=lambda x: x if isinstance(x, dict) else {'id': getattr(x, 'id', 'test')})
    return service


@pytest.fixture
def mock_duckdb_storage():
    """Mock DuckDB storage"""
    storage = Mock()
    storage.conn = Mock()
    storage.ensure_schema = Mock()
    return storage


@pytest.fixture
def sample_admin_api_response():
    """Sample admin response from Intercom API"""
    return {
        'type': 'admin',
        'id': '12345',
        'name': 'Maria Rodriguez',
        'email': 'maria@hirehoratio.co',
        'away_mode_enabled': False,
        'has_inbox_seat': True,
        'team_ids': []
    }


class TestAdminProfileCache:
    """Test suite for AdminProfileCache"""
    
    @pytest.mark.asyncio
    async def test_get_admin_profile_from_api(
        self, 
        mock_intercom_service, 
        mock_duckdb_storage,
        sample_admin_api_response
    ):
        """Test fetching admin profile from API using SDK"""
        cache = AdminProfileCache(mock_intercom_service, mock_duckdb_storage)
        
        # Mock the SDK client's find method
        mock_intercom_service.client.admins.find = AsyncMock(return_value=sample_admin_api_response)
        mock_intercom_service._model_to_dict.return_value = sample_admin_api_response
        
        # Get profile
        profile = await cache.get_admin_profile('12345')
        
        assert isinstance(profile, AdminProfile)
        assert profile.id == '12345'
        assert profile.name == 'Maria Rodriguez'
        assert profile.email == 'maria@hirehoratio.co'
        assert profile.vendor == 'horatio'
        assert profile.active is True
    
    @pytest.mark.asyncio
    async def test_session_cache_hit(self, mock_intercom_service):
        """Test that session cache prevents redundant API calls"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Add to session cache
        cached_profile = AdminProfile(
            id='12345',
            name='Maria Rodriguez',
            email='maria@hirehoratio.co',
            vendor='horatio',
            active=True,
            cached_at=datetime.now()
        )
        cache.session_cache['12345'] = cached_profile
        
        # Mock client (should not be called)
        mock_intercom_service.client.admins.find = AsyncMock(
            side_effect=Exception("Should not be called")
        )
        
        # Get profile - should use cache
        profile = await cache.get_admin_profile('12345')
        
        assert profile == cached_profile
        assert mock_intercom_service.client.admins.find.call_count == 0
    
    @pytest.mark.asyncio
    async def test_api_failure_fallback(self, mock_intercom_service):
        """Test fallback when API call fails"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Mock client with API error
        mock_intercom_service.client.admins.find = AsyncMock(
            side_effect=ApiError(status_code=500, body={"errors": [{"message": "API error"}]})
        )
        
        # Get profile - should return fallback
        profile = await cache.get_admin_profile('12345', public_email='agent@test.com')
        
        assert isinstance(profile, AdminProfile)
        assert profile.id == '12345'
        assert profile.name == 'Admin 12345'  # Updated expectation per comment
        assert profile.email == 'agent@test.com'
    
    def test_identify_vendor_horatio(self, mock_intercom_service):
        """Test vendor identification for Horatio"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        assert cache._identify_vendor('agent@hirehoratio.co') == 'horatio'
        assert cache._identify_vendor('support@horatio.com') == 'horatio'
    
    def test_identify_vendor_boldr(self, mock_intercom_service):
        """Test vendor identification for Boldr"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        assert cache._identify_vendor('agent@boldrimpact.com') == 'boldr'
        assert cache._identify_vendor('support@boldr.com') == 'boldr'
    
    def test_identify_vendor_gamma(self, mock_intercom_service):
        """Test vendor identification for Gamma"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        assert cache._identify_vendor('max.jackson@gamma.app') == 'gamma'
    
    def test_identify_vendor_unknown(self, mock_intercom_service):
        """Test vendor identification for unknown"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        assert cache._identify_vendor('agent@random.com') == 'unknown'
        assert cache._identify_vendor('') == 'unknown'
        assert cache._identify_vendor(None) == 'unknown'
    
    def test_identify_vendor_edge_cases(self, mock_intercom_service):
        """Test vendor identification edge cases and domain parsing"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Mixed case - should normalize
        assert cache._identify_vendor('Agent@HireHoratio.Co') == 'horatio'
        assert cache._identify_vendor('SUPPORT@BOLDRIMPACT.COM') == 'boldr'
        
        # Whitespace - should trim
        assert cache._identify_vendor('  agent@gamma.app  ') == 'gamma'
        
        # Substring that should NOT match (no more loose @boldr matching)
        assert cache._identify_vendor('agent@myboldr.net') == 'unknown'
        assert cache._identify_vendor('agent@boldrexample.org') == 'unknown'
        
        # Invalid formats
        assert cache._identify_vendor('not-an-email') == 'unknown'
        assert cache._identify_vendor('@horatio.com') == 'unknown'
    
    def test_validate_email(self, mock_intercom_service):
        """Test email validation"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Valid emails
        assert cache._validate_email('test@example.com') is True
        assert cache._validate_email('user.name+tag@domain.co.uk') is True
        assert cache._validate_email('test_123@test-domain.com') is True
        
        # Invalid emails
        assert cache._validate_email('') is False
        assert cache._validate_email('not-an-email') is False
        assert cache._validate_email('@example.com') is False
        assert cache._validate_email('test@') is False
        assert cache._validate_email('test') is False
        assert cache._validate_email(None) is False
        assert cache._validate_email(123) is False
    
    def test_cache_stats(self, mock_intercom_service):
        """Test cache statistics"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Add some items to session cache
        cache.session_cache['1'] = Mock()
        cache.session_cache['2'] = Mock()
        
        stats = cache.get_cache_stats()
        
        assert stats['session_cache_size'] == 2
        assert stats['cache_ttl_days'] == 7
    
    def test_clear_session_cache(self, mock_intercom_service):
        """Test clearing session cache"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Add items
        cache.session_cache['1'] = Mock()
        cache.session_cache['2'] = Mock()
        
        assert len(cache.session_cache) == 2
        
        # Clear
        cache.clear_session_cache()
        
        assert len(cache.session_cache) == 0
    
    def test_is_cache_valid(self, mock_intercom_service):
        """Test cache validity checking"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Valid cache (recent)
        recent_profile = AdminProfile(
            id='123',
            name='Test',
            email='test@test.com',
            vendor='unknown',
            active=True,
            cached_at=datetime.now()
        )
        assert cache._is_cache_valid(recent_profile) is True
        
        # Invalid cache (old)
        old_profile = AdminProfile(
            id='123',
            name='Test',
            email='test@test.com',
            vendor='unknown',
            active=True,
            cached_at=datetime.now() - timedelta(days=10)
        )
        assert cache._is_cache_valid(old_profile) is False
        
        # Invalid cache (no timestamp)
        no_timestamp = AdminProfile(
            id='123',
            name='Test',
            email='test@test.com',
            vendor='unknown',
            active=True,
            cached_at=None
        )
        assert cache._is_cache_valid(no_timestamp) is False
    
    @pytest.mark.asyncio
    async def test_api_failure_with_conversation_parts_fallback(self, mock_intercom_service):
        """Test fallback profile creation with conversation_parts when API fails"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Mock client with API error
        mock_intercom_service.client.admins.find = AsyncMock(
            side_effect=ApiError(status_code=500, body={"errors": [{"message": "API error"}]})
        )
        
        # Simulate conversation parts with agent email
        conversation_parts = [
            {
                'author': {
                    'type': 'admin',
                    'id': '123',
                    'email': 'agent@horatio.ai'
                }
            }
        ]
        
        # Create fallback profile directly
        profile = cache._create_fallback_profile('123', conversation_parts, None)
        
        assert isinstance(profile, AdminProfile)
        assert profile.id == '123'
        # Should derive vendor from email in conversation_parts
        assert profile.vendor == 'horatio'
    
    @pytest.mark.asyncio
    async def test_public_email_no_vendor_mapping(self, mock_intercom_service):
        """Public emails (gmail, yahoo) should not map to vendors"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        conversation_parts = [
            {
                'author': {
                    'type': 'admin',
                    'id': '456',
                    'email': 'agent@gmail.com'
                }
            }
        ]
        
        profile = cache._create_fallback_profile('456', conversation_parts)
        
        # Public domain should not be treated as vendor
        assert profile.vendor == 'unknown'
        assert profile.email == 'agent@gmail.com'
    
    def test_extract_vendor_from_email_known_vendors(self, mock_intercom_service):
        """Test vendor extraction from various known email domains"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        test_cases = [
            ('agent@horatio.ai', 'horatio'),
            ('agent@hirehoratio.co', 'horatio'),
            ('support@boldr.co', 'boldr'),
            ('team@boldrimpact.com', 'boldr'),
            ('admin@escalated.com', 'escalated'),
            ('user@gamma.app', 'gamma'),
        ]
        
        for email, expected_vendor in test_cases:
            vendor = cache._extract_vendor_from_email(email)
            assert vendor == expected_vendor, f"Failed for {email}: got {vendor}, expected {expected_vendor}"
    
    def test_extract_vendor_from_email_public_domains(self, mock_intercom_service):
        """Test that public domains return None"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        public_emails = [
            'user@gmail.com',
            'user@yahoo.com',
            'user@outlook.com',
            'user@hotmail.com',
            'user@icloud.com'
        ]
        
        for email in public_emails:
            vendor = cache._extract_vendor_from_email(email)
            assert vendor is None, f"Public domain {email} should return None, got {vendor}"
    
    def test_extract_vendor_from_email_custom_domains(self, mock_intercom_service):
        """Test that custom/unknown domains extract base domain name"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        test_cases = [
            ('admin@customvendor.com', 'customvendor'),
            ('support@mycompany.io', 'mycompany'),
            ('team@newvendor.co', 'newvendor'),
        ]
        
        for email, expected_vendor in test_cases:
            vendor = cache._extract_vendor_from_email(email)
            assert vendor == expected_vendor, f"Failed for {email}: got {vendor}, expected {expected_vendor}"
    
    def test_extract_vendor_from_email_edge_cases(self, mock_intercom_service):
        """Test edge cases for vendor extraction"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Invalid emails should return None
        assert cache._extract_vendor_from_email('') is None
        assert cache._extract_vendor_from_email('not-an-email') is None
        assert cache._extract_vendor_from_email('@example.com') is None
        assert cache._extract_vendor_from_email(None) is None
    
    @pytest.mark.asyncio
    async def test_retry_on_api_failure(self, mock_intercom_service):
        """Test retry logic with exponential backoff"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Track call count
        call_count = 0
        
        # Mock client that fails twice then succeeds
        async def mock_find(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # First 2 attempts fail
                raise ApiError(status_code=500, body={"errors": [{"message": "Temporary API error"}]})
            
            # Third attempt succeeds
            return {
                'type': 'admin',
                'id': '123',
                'name': 'Test Admin',
                'email': 'test@horatio.ai',
                'away_mode_enabled': False
            }
        
        mock_intercom_service.client.admins.find = mock_find
        mock_intercom_service._model_to_dict = Mock(side_effect=lambda x: x)
        
        # Should retry and eventually succeed
        profile = await cache.get_admin_profile('123')
        
        assert call_count == 3  # Failed twice, succeeded on third try
        assert profile.name == 'Test Admin'
        assert profile.vendor == 'horatio'
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion_fallback(self, mock_intercom_service):
        """Test that after all retries fail, fallback profile is created"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Mock client that always fails
        mock_intercom_service.client.admins.find = AsyncMock(
            side_effect=ApiError(status_code=500, body={"errors": [{"message": "Persistent API error"}]})
        )
        
        # Should exhaust retries and create fallback
        profile = await cache.get_admin_profile('123', public_email='fallback@horatio.ai')
        
        assert isinstance(profile, AdminProfile)
        assert profile.id == '123'
        # Should still derive vendor from public_email
        assert profile.vendor == 'horatio'
    
    def test_fallback_profile_vendor_attribution_logging(self, mock_intercom_service, caplog):
        """Test that vendor attribution gaps are logged"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Create fallback without any email info
        with caplog.at_level(logging.WARNING):
            profile = cache._create_fallback_profile('999', None, None)
        
        assert profile.vendor == 'unknown'
        # Check that warning was logged
        assert any('Vendor attribution gap' in record.message for record in caplog.records)
    
    def test_fallback_profile_successful_attribution_logging(self, mock_intercom_service, caplog):
        """Test that successful vendor attribution is logged"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        conversation_parts = [
            {
                'author': {
                    'type': 'admin',
                    'id': '123',
                    'email': 'agent@boldr.co'
                }
            }
        ]
        
        with caplog.at_level(logging.INFO):
            profile = cache._create_fallback_profile('123', conversation_parts)
        
        assert profile.vendor == 'boldr'
        # Check that success was logged
        assert any('Derived vendor' in record.message and 'boldr' in record.message for record in caplog.records)
