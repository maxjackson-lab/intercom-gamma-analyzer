"""
Tests for Railway web deployment and canonical command mapping.

These tests verify that the server-side command schema is properly defined
and that the API endpoint returns the expected structure.
"""

import pytest
import json
from datetime import datetime


# Import the FastAPI app and schema
try:
    from deploy.railway_web import app, CANONICAL_COMMAND_MAPPINGS, validate_command_request
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    CANONICAL_COMMAND_MAPPINGS = None


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    if not HAS_FASTAPI:
        pytest.skip("FastAPI not available")
    
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestCanonicalCommandMappings:
    """Test the CANONICAL_COMMAND_MAPPINGS structure."""
    
    def test_mappings_exist(self):
        """Test that CANONICAL_COMMAND_MAPPINGS is defined."""
        assert CANONICAL_COMMAND_MAPPINGS is not None
        assert isinstance(CANONICAL_COMMAND_MAPPINGS, dict)
        assert len(CANONICAL_COMMAND_MAPPINGS) > 0
    
    def test_all_expected_analysis_types_present(self):
        """Test that all expected analysis types are in the schema."""
        expected_types = [
            'voice_of_customer',
            'agent_performance',
            'agent_coaching',
            'category_billing',
            'category_product',
            'category_api',
            'category_escalations',
            'tech_troubleshooting',
            'all_categories',
            'canny_analysis'
        ]
        
        for analysis_type in expected_types:
            assert analysis_type in CANONICAL_COMMAND_MAPPINGS, f"Missing {analysis_type}"
    
    def test_command_structure(self):
        """Test that each command has the required structure."""
        required_fields = ['command', 'args', 'display_name', 'description', 'allowed_flags']
        
        for command_key, command_config in CANONICAL_COMMAND_MAPPINGS.items():
            for field in required_fields:
                assert field in command_config, f"{command_key} missing {field}"
            
            # Validate types
            assert isinstance(command_config['command'], str)
            assert isinstance(command_config['args'], list)
            assert isinstance(command_config['display_name'], str)
            assert isinstance(command_config['description'], str)
            assert isinstance(command_config['allowed_flags'], dict)
    
    def test_flag_schemas(self):
        """Test that flag schemas have proper structure."""
        for command_key, command_config in CANONICAL_COMMAND_MAPPINGS.items():
            for flag_name, flag_schema in command_config['allowed_flags'].items():
                # All flags must have a type
                assert 'type' in flag_schema, f"{command_key}.{flag_name} missing type"
                
                # Validate type values
                valid_types = ['enum', 'boolean', 'integer', 'date', 'string']
                assert flag_schema['type'] in valid_types, f"{command_key}.{flag_name} has invalid type"
                
                # Enum flags must have values
                if flag_schema['type'] == 'enum':
                    assert 'values' in flag_schema, f"{command_key}.{flag_name} enum missing values"
                    assert len(flag_schema['values']) > 0
                
                # Integer flags should have min/max
                if flag_schema['type'] == 'integer':
                    if 'min' in flag_schema:
                        assert isinstance(flag_schema['min'], int)
                    if 'max' in flag_schema:
                        assert isinstance(flag_schema['max'], int)
    
    def test_voice_of_customer_flags(self):
        """Test voice_of_customer has expected flags."""
        voc = CANONICAL_COMMAND_MAPPINGS['voice_of_customer']
        expected_flags = ['--time-period', '--analysis-type', '--output-format', '--gamma-export', '--test-mode', '--audit-trail']
        
        for flag in expected_flags:
            assert flag in voc['allowed_flags'], f"voice_of_customer missing {flag}"
        
        # Validate specific flag schemas
        assert voc['allowed_flags']['--time-period']['type'] == 'enum'
        assert 'week' in voc['allowed_flags']['--time-period']['values']
        assert 'month' in voc['allowed_flags']['--time-period']['values']
        
        # Validate output format flags (new standard)
        assert voc['allowed_flags']['--output-format']['type'] == 'enum'
        assert 'gamma' in voc['allowed_flags']['--output-format']['values']
        assert 'markdown' in voc['allowed_flags']['--output-format']['values']
        
        assert voc['allowed_flags']['--gamma-export']['type'] == 'enum'
        assert 'pdf' in voc['allowed_flags']['--gamma-export']['values']
        assert 'pptx' in voc['allowed_flags']['--gamma-export']['values']
        
        assert voc['allowed_flags']['--test-mode']['type'] == 'boolean'
    
    def test_agent_performance_flags(self):
        """Test agent_performance has expected flags."""
        agent_perf = CANONICAL_COMMAND_MAPPINGS['agent_performance']
        
        # Should have required --agent flag
        assert '--agent' in agent_perf['allowed_flags']
        assert agent_perf['allowed_flags']['--agent']['required'] is True
        assert agent_perf['allowed_flags']['--agent']['type'] == 'enum'
        assert 'horatio' in agent_perf['allowed_flags']['--agent']['values']
        assert 'boldr' in agent_perf['allowed_flags']['--agent']['values']
        
        # Should have --individual-breakdown flag
        assert '--individual-breakdown' in agent_perf['allowed_flags']
        assert agent_perf['allowed_flags']['--individual-breakdown']['type'] == 'boolean'


class TestAPICommandsEndpoint:
    """Test the /api/commands endpoint."""
    
    def test_endpoint_exists(self, client):
        """Test /api/commands endpoint exists and returns 200."""
        response = client.get('/api/commands')
        assert response.status_code == 200
    
    def test_response_structure(self, client):
        """Test /api/commands returns expected structure."""
        response = client.get('/api/commands')
        data = response.json()
        
        assert 'version' in data
        assert 'commands' in data
        assert 'generated_at' in data
        
        # Validate version
        assert isinstance(data['version'], str)
        
        # Validate generated_at is ISO format timestamp
        datetime.fromisoformat(data['generated_at'])  # Should not raise
        
        # Validate commands
        assert isinstance(data['commands'], dict)
        assert len(data['commands']) > 0
    
    def test_commands_content(self, client):
        """Test /api/commands returns actual command mappings."""
        response = client.get('/api/commands')
        data = response.json()
        commands = data['commands']
        
        # Should have at least the major analysis types
        assert 'voice_of_customer' in commands
        assert 'agent_performance' in commands
        
        # Each command should have required fields
        for command_type, config in commands.items():
            assert 'command' in config
            assert 'args' in config
            assert 'display_name' in config
            assert 'allowed_flags' in config
    
    def test_flag_schemas_in_response(self, client):
        """Test flag schemas are properly included in response."""
        response = client.get('/api/commands')
        data = response.json()
        
        # Check voice_of_customer flags
        voc_flags = data['commands']['voice_of_customer']['allowed_flags']
        
        # time-period should be enum
        assert voc_flags['--time-period']['type'] == 'enum'
        assert 'week' in voc_flags['--time-period']['values']
        assert '6-weeks' in voc_flags['--time-period']['values']
        
        # output-format should be enum including gamma
        assert voc_flags['--output-format']['type'] == 'enum'
        assert 'gamma' in voc_flags['--output-format']['values']
        assert 'markdown' in voc_flags['--output-format']['values']
        
        # gamma-export should be enum with pdf and pptx
        assert voc_flags['--gamma-export']['type'] == 'enum'
        assert 'pdf' in voc_flags['--gamma-export']['values']
        assert 'pptx' in voc_flags['--gamma-export']['values']
    
    def test_caching_headers(self, client):
        """Test that proper caching headers are set."""
        response = client.get('/api/commands')
        
        # Should have cache-control header
        assert 'cache-control' in response.headers
        assert 'public' in response.headers['cache-control']


class TestValidateCommandRequest:
    """Test the validate_command_request function."""
    
    def test_valid_request(self):
        """Test validation of a valid request."""
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {
                '--time-period': 'week',
                '--output-format': 'gamma',
                '--gamma-export': 'pdf',
                '--test-mode': False
            }
        )
        assert is_valid is True
        assert error is None
    
    def test_unknown_analysis_type(self):
        """Test validation rejects unknown analysis type."""
        is_valid, error = validate_command_request(
            'unknown_analysis',
            {}
        )
        assert is_valid is False
        assert 'Unknown analysis type' in error
    
    def test_unknown_flag(self):
        """Test validation rejects unknown flags."""
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--invalid-flag': 'value'}
        )
        assert is_valid is False
        assert 'Unknown flag' in error or 'invalid-flag' in error
    
    def test_invalid_enum_value(self):
        """Test validation rejects invalid enum values."""
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--time-period': 'invalid_period'}
        )
        assert is_valid is False
        assert 'Invalid value' in error or 'Must be one of' in error
    
    def test_missing_required_flag(self):
        """Test validation rejects missing required flags."""
        is_valid, error = validate_command_request(
            'agent_performance',
            {'--time-period': 'week'}  # Missing required --agent flag
        )
        assert is_valid is False
        assert 'Missing required flag' in error or '--agent' in error
    
    def test_invalid_date_format(self):
        """Test validation rejects invalid date formats."""
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--start-date': '2024/10/01'}  # Wrong format
        )
        assert is_valid is False
        assert 'date format' in error.lower() or 'YYYY-MM-DD' in error
    
    def test_valid_date_format(self):
        """Test validation accepts valid date formats."""
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--start-date': '2024-10-01', '--end-date': '2024-10-31'}
        )
        assert is_valid is True
        assert error is None
    
    def test_integer_bounds(self):
        """Test validation enforces integer bounds."""
        # Test with valid integer
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--test-data-count': 100}
        )
        assert is_valid is True
        
        # Test with too small integer (assuming min is 10)
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--test-data-count': 5}
        )
        assert is_valid is False
        assert 'at least' in error.lower()
    
    def test_boolean_type_validation(self):
        """Test validation enforces boolean types."""
        # Valid boolean
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--test-mode': True}
        )
        assert is_valid is True
        
        # Invalid: string instead of boolean
        is_valid, error = validate_command_request(
            'voice_of_customer',
            {'--test-mode': 'true'}
        )
        assert is_valid is False
        assert 'boolean' in error.lower()


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""
    
    def test_voice_of_customer_workflow(self, client):
        """Test complete VoC analysis workflow with schema."""
        # 1. Get schema
        schema_response = client.get('/api/commands')
        assert schema_response.status_code == 200
        schema = schema_response.json()
        
        # 2. Validate we can build a request from schema
        voc_config = schema['commands']['voice_of_customer']
        assert 'allowed_flags' in voc_config
        
        # 3. Build a valid request based on schema
        flags = {
            '--time-period': 'week',
            '--test-mode': True
        }
        
        # 4. Validate the request
        is_valid, error = validate_command_request('voice_of_customer', flags)
        assert is_valid is True
    
    def test_agent_performance_workflow(self, client):
        """Test agent performance workflow with required flags."""
        # Get schema
        schema_response = client.get('/api/commands')
        schema = schema_response.json()
        
        # Agent performance requires --agent flag
        agent_config = schema['commands']['agent_performance']
        assert agent_config['allowed_flags']['--agent']['required'] is True
        
        # Request without required flag should fail
        is_valid, error = validate_command_request('agent_performance', {})
        assert is_valid is False
        
        # Request with required flag should succeed
        is_valid, error = validate_command_request(
            'agent_performance',
            {'--agent': 'horatio'}
        )
        assert is_valid is True
    
    def test_schema_version_tracking(self, client):
        """Test that schema includes version for cache busting."""
        response = client.get('/api/commands')
        data = response.json()
        
        # Should have version
        assert 'version' in data
        assert data['version'] == '1.0'
        
        # Should have timestamp
        assert 'generated_at' in data
        # Timestamp should be recent (within last minute)
        generated_time = datetime.fromisoformat(data['generated_at'])
        now = datetime.now()
        diff = (now - generated_time).total_seconds()
        assert diff < 60, "Schema timestamp is too old"


class TestDebugVersionEndpoint:
    """Test the /debug/version endpoint for dynamic versioning."""
    
    def test_debug_version_endpoint_exists(self, client):
        """Test /debug/version endpoint exists and returns 200."""
        response = client.get('/debug/version')
        assert response.status_code == 200
    
    def test_debug_version_structure(self, client):
        """Test /debug/version returns expected structure."""
        response = client.get('/debug/version')
        data = response.json()
        
        required_fields = [
            'version', 'commit', 'commit_short', 'build_date',
            'uptime_seconds', 'python_version', 'environment',
            'deployment_id', 'timestamp'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_debug_version_non_empty(self, client):
        """Test version and commit are non-empty."""
        response = client.get('/debug/version')
        data = response.json()
        
        assert data['version'], "Version should not be empty"
        assert data['commit'], "Commit should not be empty"
        assert len(data['commit']) > 0, "Commit hash should have length"
    
    def test_debug_version_commit_short(self, client):
        """Test commit_short is first 8 chars of commit."""
        response = client.get('/debug/version')
        data = response.json()
        
        if data['commit'] != 'unknown':
            assert data['commit'].startswith(data['commit_short']), \
                "commit_short should be prefix of commit"
            assert len(data['commit_short']) <= 8, \
                "commit_short should be max 8 chars"
        else:
            # For unknown commits, commit_short should also be 'unknown'
            assert data['commit_short'] == 'unknown', \
                "commit_short should match commit when unknown"
    
    def test_debug_version_build_date_format(self, client):
        """Test build_date is valid ISO format."""
        response = client.get('/debug/version')
        data = response.json()
        
        try:
            # Handle both with and without timezone
            datetime.fromisoformat(data['build_date'].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid build_date format: {data['build_date']}")
    
    def test_debug_version_uptime(self, client):
        """Test uptime is positive number."""
        response = client.get('/debug/version')
        data = response.json()
        
        assert isinstance(data['uptime_seconds'], (int, float)), \
            "uptime_seconds should be numeric"
        assert data['uptime_seconds'] >= 0, \
            "uptime should be positive"
    
    def test_debug_version_python_version(self, client):
        """Test python_version field is present and valid."""
        response = client.get('/debug/version')
        data = response.json()
        
        assert 'python_version' in data
        assert isinstance(data['python_version'], str)
        assert len(data['python_version']) > 0
        # Should contain version number like "3.11" or "3.10"
        assert any(char.isdigit() for char in data['python_version'])
    
    def test_debug_version_environment(self, client):
        """Test environment field defaults correctly."""
        response = client.get('/debug/version')
        data = response.json()
        
        assert 'environment' in data
        assert isinstance(data['environment'], str)
        # Should be either from RAILWAY_ENVIRONMENT or default to 'local'
        assert len(data['environment']) > 0
    
    def test_version_endpoint_public(self, client):
        """Test /debug/version doesn't require authentication."""
        # Should work without auth header
        response = client.get('/debug/version')
        assert response.status_code == 200
        
        # Unlike /execute endpoints which require auth
        execute_response = client.post('/execute/start', json={})
        assert execute_response.status_code in [400, 401], \
            "Execute endpoint should require auth or fail validation"
    
    def test_version_endpoint_performance(self, client):
        """Test /debug/version responds quickly."""
        import time
        start = time.time()
        response = client.get('/debug/version')
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, "Version endpoint should respond in under 1 second"
    
    def test_version_values_match_env_vars(self, client):
        """Test version values come from environment when set."""
        import os
        
        response = client.get('/debug/version')
        data = response.json()
        
        # Check if APP_VERSION env var is being used
        # (In tests, this might be 'dev' as default)
        assert data['version'] in ['dev', os.getenv('APP_VERSION', 'dev')]
        
        # Check if GIT_COMMIT env var is being used
        assert data['commit'] in ['unknown', os.getenv('GIT_COMMIT', 'unknown')]


# Run tests with: pytest tests/test_railway_deployment.py -v