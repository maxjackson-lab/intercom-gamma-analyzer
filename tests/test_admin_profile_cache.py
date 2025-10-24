"""
Tests for AdminProfileCache service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
import httpx

from src.services.admin_profile_cache import AdminProfileCache
from src.models.agent_performance_models import AdminProfile


@pytest.fixture
def mock_intercom_service():
    """Mock Intercom service"""
    service = Mock()
    service.base_url = "https://api.intercom.io"
    service.headers = {
        'Authorization': 'Bearer test_token',
        'Accept': 'application/json'
    }
    return service


@pytest.fixture
def mock_duckdb_storage():
    """Mock DuckDB storage"""
    storage = Mock()
    storage.conn = Mock()
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
        """Test fetching admin profile from API"""
        cache = AdminProfileCache(mock_intercom_service, mock_duckdb_storage)
        
        # Mock the HTTP client
        mock_response = Mock()
        mock_response.json = Mock(return_value=sample_admin_api_response)
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        # Get profile
        profile = await cache.get_admin_profile('12345', mock_client)
        
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
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Should not be called"))
        
        # Get profile - should use cache
        profile = await cache.get_admin_profile('12345', mock_client)
        
        assert profile == cached_profile
        assert mock_client.get.call_count == 0
    
    @pytest.mark.asyncio
    async def test_api_failure_fallback(self, mock_intercom_service):
        """Test fallback when API call fails"""
        cache = AdminProfileCache(mock_intercom_service, None)
        
        # Mock client with error
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("API error"))
        
        # Get profile - should return fallback
        profile = await cache.get_admin_profile('12345', mock_client, public_email='agent@test.com')
        
        assert isinstance(profile, AdminProfile)
        assert profile.id == '12345'
        assert profile.name == 'Unknown'
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

