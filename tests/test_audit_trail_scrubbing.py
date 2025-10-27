"""
Tests for PII scrubbing in audit trail
"""

import os
import pytest
from src.services.audit_trail import AuditTrail


def test_email_redaction():
    """Test emails are redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'user_email': 'john.doe@example.com',
        'admin_email': 'support@company.com',
        'message': 'Contact me at jane@test.org'
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    assert 'john.doe@example.com' not in str(scrubbed)
    assert 'support@company.com' not in str(scrubbed)
    assert 'jane@test.org' not in str(scrubbed)
    assert '[EMAIL_REDACTED]' in str(scrubbed)


def test_bearer_token_redaction():
    """Test bearer tokens are redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'auth_header': 'Bearer abc123def456ghi789',
        'token': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    assert 'abc123def456ghi789' not in str(scrubbed)
    assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' not in str(scrubbed)
    assert '[TOKEN_REDACTED]' in str(scrubbed)


def test_conversation_id_redaction():
    """Test conversation IDs are redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'conversation_id': 123456789,
        'text': 'conversation_id: 987654321'
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    # The integer itself won't be redacted, but the string pattern will be
    assert '987654321' not in str(scrubbed['text'])
    assert '[ID_REDACTED]' in str(scrubbed)


def test_api_key_redaction():
    """Test API keys are redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'api_key': 'fake_key_abcdefghijklmnopqrstuvwxyz123456',
        'access_token': '1234567890abcdefghijklmnopqrstuvwxyz'
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    assert 'fake_key_abcdefghijklmnopqrstuvwxyz123456' not in str(scrubbed)
    assert '1234567890abcdefghijklmnopqrstuvwxyz' not in str(scrubbed)
    assert '[API_KEY_REDACTED]' in str(scrubbed)


def test_scrubbing_disabled():
    """Test scrubbing can be disabled"""
    audit = AuditTrail(scrub_pii=False)
    
    data = {
        'email': 'test@example.com',
        'token': 'Bearer secret123'
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    # Should NOT be scrubbed when disabled
    assert scrubbed['email'] == 'test@example.com'
    assert scrubbed['token'] == 'Bearer secret123'


def test_structure_preservation():
    """Test scrubbing preserves data structure"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'users': [
            {'name': 'John', 'email': 'john@test.com'},
            {'name': 'Jane', 'email': 'jane@test.com'}
        ],
        'metadata': {
            'admin_email': 'admin@test.com',
            'count': 2
        }
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    # Structure should be preserved
    assert isinstance(scrubbed, dict)
    assert isinstance(scrubbed['users'], list)
    assert len(scrubbed['users']) == 2
    assert scrubbed['users'][0]['name'] == 'John'
    assert scrubbed['metadata']['count'] == 2
    
    # But emails should be redacted
    assert '[EMAIL_REDACTED]' in str(scrubbed)


def test_tool_call_scrubbing():
    """Test tool calls are scrubbed before storage"""
    audit = AuditTrail(scrub_pii=True)
    
    # Simulate tool call with sensitive data
    audit.tool_call(
        tool_name='lookup_admin',
        arguments={'admin_email': 'agent@horatio.ai', 'admin_id': 12345},
        result={'profile': {'email': 'agent@horatio.ai', 'vendor': 'horatio'}},
        success=True,
        execution_time_ms=150.5
    )
    
    # Check stored data is scrubbed
    stored_call = audit.tool_calls[0]
    assert 'agent@horatio.ai' not in str(stored_call['arguments'])
    assert 'agent@horatio.ai' not in str(stored_call['result'])
    assert '[EMAIL_REDACTED]' in str(stored_call)
    assert stored_call['_scrubbed'] is True


def test_selective_redaction():
    """Test that useful data is preserved while sensitive data is redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'admin_name': 'John Smith',  # Should be preserved
        'admin_email': 'john@company.com',  # Should be redacted
        'vendor': 'horatio',  # Should be preserved
        'conversation_count': 150,  # Should be preserved
        'api_key': 'fake_key_abc123def456ghi789jkl012'  # Should be redacted
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    # Useful data preserved
    assert scrubbed['admin_name'] == 'John Smith'
    assert scrubbed['vendor'] == 'horatio'
    assert scrubbed['conversation_count'] == 150
    
    # Sensitive data redacted
    assert 'john@company.com' not in str(scrubbed)
    assert 'fake_key_abc123def456ghi789jkl012' not in str(scrubbed)


def test_config_toggle_via_environment():
    """Test scrubbing can be controlled via environment variable"""
    
    # Enable via env
    os.environ['SCRUB_AUDIT_DATA'] = 'true'
    audit_on = AuditTrail()
    assert audit_on.scrub_pii is True
    
    # Disable via env
    os.environ['SCRUB_AUDIT_DATA'] = 'false'
    audit_off = AuditTrail()
    assert audit_off.scrub_pii is False
    
    # Cleanup
    del os.environ['SCRUB_AUDIT_DATA']


def test_nested_structure_scrubbing():
    """Test scrubbing works on deeply nested structures"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'level1': {
            'level2': {
                'level3': {
                    'email': 'deep@example.com',
                    'safe_data': 'preserve this'
                }
            }
        }
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    # Structure preserved
    assert 'level1' in scrubbed
    assert 'level2' in scrubbed['level1']
    assert 'level3' in scrubbed['level1']['level2']
    
    # Safe data preserved
    assert scrubbed['level1']['level2']['level3']['safe_data'] == 'preserve this'
    
    # Email redacted
    assert 'deep@example.com' not in str(scrubbed)


def test_admin_id_redaction():
    """Test admin IDs are redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'text': 'admin_id: 54321',
        'message': 'admin_id 12345'
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    assert '54321' not in str(scrubbed['text'])
    assert '[ID_REDACTED]' in str(scrubbed)


def test_environment_variable_secrets():
    """Test environment variable secrets are redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'config': 'API_KEY=abc123def456',
        'settings': 'TOKEN: xyz789',
        'creds': 'PASSWORD=secret123'
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    assert 'abc123def456' not in str(scrubbed)
    assert 'xyz789' not in str(scrubbed)
    assert 'secret123' not in str(scrubbed)
    assert '[REDACTED]' in str(scrubbed)


def test_hex_token_redaction():
    """Test hex tokens are redacted"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'token': 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4',  # 32 char hex
        'secret': 'abc123def456abc123def456abc123def456abc123'  # 40 char hex
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    # Verify sensitive data is redacted (may be caught by API_KEY or HEX_TOKEN pattern)
    assert 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4' not in str(scrubbed)
    assert 'abc123def456abc123def456abc123def456abc123' not in str(scrubbed)
    # Accept either redaction label since hex tokens may be caught by API_KEY pattern first
    assert '[HEX_TOKEN_REDACTED]' in str(scrubbed) or '[API_KEY_REDACTED]' in str(scrubbed)


def test_scrubbing_methods():
    """Test set_scrubbing_enabled and is_scrubbing_enabled methods"""
    audit = AuditTrail(scrub_pii=True)
    
    # Initially enabled
    assert audit.is_scrubbing_enabled() is True
    
    # Disable
    audit.set_scrubbing_enabled(False)
    assert audit.is_scrubbing_enabled() is False
    
    # Re-enable
    audit.set_scrubbing_enabled(True)
    assert audit.is_scrubbing_enabled() is True


def test_list_of_strings_scrubbing():
    """Test scrubbing works on lists of strings"""
    audit = AuditTrail(scrub_pii=True)
    
    data = [
        'email: john@test.com',
        'Bearer abc123token',
        'normal text',
        'conversation_id: 12345'
    ]
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    assert isinstance(scrubbed, list)
    assert len(scrubbed) == 4
    assert 'john@test.com' not in str(scrubbed)
    assert 'abc123token' not in str(scrubbed)
    assert 'normal text' in scrubbed[2]
    assert '[EMAIL_REDACTED]' in str(scrubbed)
    assert '[TOKEN_REDACTED]' in str(scrubbed)


def test_mixed_types_scrubbing():
    """Test scrubbing handles mixed data types correctly"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'string': 'email: test@example.com',
        'integer': 12345,
        'float': 123.45,
        'boolean': True,
        'none': None,
        'list': ['a', 'b', 'c'],
        'nested': {
            'email': 'nested@test.com'
        }
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    # Primitives preserved
    assert scrubbed['integer'] == 12345
    assert scrubbed['float'] == 123.45
    assert scrubbed['boolean'] is True
    assert scrubbed['none'] is None
    assert scrubbed['list'] == ['a', 'b', 'c']
    
    # Emails redacted
    assert 'test@example.com' not in str(scrubbed['string'])
    assert 'nested@test.com' not in str(scrubbed['nested'])


def test_generate_report_scrubbing_note():
    """Test generate_report includes scrubbing note when enabled"""
    audit = AuditTrail(scrub_pii=True)
    
    # Add a tool call
    audit.tool_call(
        tool_name='test_tool',
        arguments={'email': 'test@example.com'},
        result={'status': 'ok'},
        success=True,
        execution_time_ms=100.0
    )
    
    report = audit.generate_report()
    
    # Should include scrubbing note
    assert 'Sensitive data has been redacted for security' in report


def test_no_scrubbing_note_when_disabled():
    """Test generate_report does not include scrubbing note when disabled"""
    audit = AuditTrail(scrub_pii=False)
    
    # Add a tool call
    audit.tool_call(
        tool_name='test_tool',
        arguments={'email': 'test@example.com'},
        result={'status': 'ok'},
        success=True,
        execution_time_ms=100.0
    )
    
    report = audit.generate_report()
    
    # Should NOT include scrubbing note
    assert 'Sensitive data has been redacted for security' not in report


def test_error_message_scrubbing():
    """Test error messages are scrubbed"""
    audit = AuditTrail(scrub_pii=True)
    
    # Simulate tool call with error containing sensitive data
    audit.tool_call(
        tool_name='failed_tool',
        arguments={'key': 'value'},
        result=None,
        success=False,
        execution_time_ms=50.0,
        error_message='Failed to authenticate with Bearer abc123token for user@example.com'
    )
    
    stored_call = audit.tool_calls[0]
    
    # Error message should be scrubbed
    assert 'abc123token' not in str(stored_call['error_message'])
    assert 'user@example.com' not in str(stored_call['error_message'])
    assert '[TOKEN_REDACTED]' in str(stored_call['error_message'])
    assert '[EMAIL_REDACTED]' in str(stored_call['error_message'])


def test_scrubbing_flag_in_tool_call():
    """Test _scrubbed flag is set in tool call data"""
    audit_on = AuditTrail(scrub_pii=True)
    audit_off = AuditTrail(scrub_pii=False)
    
    # With scrubbing
    audit_on.tool_call(
        tool_name='test',
        arguments={},
        result={},
        success=True,
        execution_time_ms=100.0
    )
    assert audit_on.tool_calls[0]['_scrubbed'] is True
    
    # Without scrubbing
    audit_off.tool_call(
        tool_name='test',
        arguments={},
        result={},
        success=True,
        execution_time_ms=100.0
    )
    assert audit_off.tool_calls[0]['_scrubbed'] is False


def test_empty_and_none_handling():
    """Test scrubbing handles empty and None values correctly"""
    audit = AuditTrail(scrub_pii=True)
    
    data = {
        'empty_string': '',
        'empty_list': [],
        'empty_dict': {},
        'none_value': None
    }
    
    scrubbed = audit._scrub_sensitive_data(data)
    
    assert scrubbed['empty_string'] == ''
    assert scrubbed['empty_list'] == []
    assert scrubbed['empty_dict'] == {}
    assert scrubbed['none_value'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])