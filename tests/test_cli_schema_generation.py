import sys

import pytest

from src.cli import schema as schema_module
from src.services.web_command_executor import WebCommandExecutor


def test_generate_executor_schema_detects_conflicting_flag_definitions(monkeypatch):
    conflicting_mappings = {
        'cmd_a': {
            'command': 'python',
            'args': ['src/main.py', 'cmd-a'],
            'allowed_flags': {
                '--shared-flag': {
                    'type': 'integer',
                    'min': 1,
                    'max': 5
                }
            }
        },
        'cmd_b': {
            'command': 'python',
            'args': ['src/main.py', 'cmd-b'],
            'allowed_flags': {
                '--shared-flag': {
                    'type': 'integer',
                    'min': 2,
                    'max': 10
                }
            }
        }
    }
    monkeypatch.setattr(
        schema_module,
        'CANONICAL_COMMAND_MAPPINGS',
        conflicting_mappings,
        raising=False
    )

    with pytest.raises(ValueError) as excinfo:
        schema_module.generate_executor_schema()

    assert "conflicting schema" in str(excinfo.value)
    assert "cmd_a" in str(excinfo.value)
    assert "cmd_b" in str(excinfo.value)


def test_optional_value_flags_allow_missing_value(monkeypatch):
    optional_mapping = {
        'cmd_optional': {
            'command': 'python',
            'args': ['src/main.py', 'cmd-optional'],
            'allowed_flags': {
                '--optional-int': {
                    'type': 'integer',
                    'min': 1,
                    'max': 10,
                    'requires_value': False
                },
                '--optional-enum': {
                    'type': 'enum',
                    'values': ['fast', 'slow'],
                    'requires_value': False
                }
            }
        }
    }
    monkeypatch.setattr(
        schema_module,
        'CANONICAL_COMMAND_MAPPINGS',
        optional_mapping,
        raising=False
    )

    schema = schema_module.generate_executor_schema()
    flag_schemas = schema['python']['flag_schemas']

    assert flag_schemas['--optional-int']['requires_value'] is False
    assert flag_schemas['--optional-enum']['requires_value'] is False

    # Avoid depending on host PATH during tests
    monkeypatch.setattr(
        'src.services.web_command_executor.shutil.which',
        lambda cmd: sys.executable if cmd.startswith('python') else None
    )

    executor = WebCommandExecutor()
    executor.COMMAND_SCHEMAS = {
        'python': {
            'allowed_modules': set(schema_module.DEFAULT_ALLOWED_MODULES),
            'allowed_flags': set(optional_mapping['cmd_optional']['allowed_flags'].keys()),
            'flag_schemas': flag_schemas
        }
    }

    _, validated_args = executor._validate_command_and_args(
        'python',
        ['src/main.py', 'cmd-optional', '--optional-int', '--optional-enum']
    )

    assert '--optional-int' in validated_args
    assert '--optional-enum' in validated_args

