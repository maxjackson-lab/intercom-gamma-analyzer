"""
Tests for system CLI commands.

Focus: connectivity checks, diagnostics helpers, and taxonomy listings.
"""

from unittest.mock import MagicMock

import pytest

from src.cli import system_commands


@pytest.fixture(autouse=True)
def no_sys_exit(monkeypatch):
    """Prevent tests from exiting the interpreter."""

    def fake_exit(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(system_commands.sys, "exit", fake_exit)


@pytest.fixture
def capture_console(monkeypatch):
    """Capture console output."""
    outputs = []

    def fake_print(*args, **kwargs):
        outputs.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(system_commands.console, "print", fake_print)
    return outputs


def test_run_test_command_success(monkeypatch, capture_console):
    """All connectivity checks succeed and summary is printed."""

    class DummyIntercom:
        async def test_connection(self):
            return True

        async def close(self):
            return None

    class DummyOpenAI:
        async def test_connection(self):
            return True

    class DummyGamma:
        async def test_connection(self):
            return True

        async def close(self):
            return None

    monkeypatch.setattr(system_commands, "IntercomSDKService", lambda: DummyIntercom())
    monkeypatch.setattr(system_commands, "OpenAIClient", lambda: DummyOpenAI())
    monkeypatch.setattr(system_commands, "GammaClient", lambda: DummyGamma())
    monkeypatch.setattr(system_commands.settings, "gamma_api_key", "test-key")

    system_commands.run_test_command()

    assert any("All connectivity tests passed" in line for line in capture_console)


def test_run_test_command_failure(monkeypatch, capture_console):
    """A failing connectivity check triggers SystemExit and error messaging."""

    class FailingIntercom:
        async def test_connection(self):
            raise RuntimeError("boom")

        async def close(self):
            return None

    class DummyClient:
        async def test_connection(self):
            return True

        async def close(self):
            return None

    monkeypatch.setattr(system_commands, "IntercomSDKService", lambda: FailingIntercom())
    monkeypatch.setattr(system_commands, "OpenAIClient", lambda: DummyClient())
    monkeypatch.setattr(system_commands, "GammaClient", lambda: DummyClient())
    monkeypatch.setattr(system_commands.settings, "gamma_api_key", "test-key")

    with pytest.raises(SystemExit) as exc:
        system_commands.run_test_command()

    assert exc.value.code == 1
    assert any("connectivity tests failed" in line for line in capture_console)


def test_run_system_info_command(monkeypatch, capture_console):
    """System info helper is invoked."""
    called = []

    def fake_show_info():
        called.append(True)

    monkeypatch.setattr(system_commands, "show_system_info", fake_show_info)

    system_commands.run_system_info_command()

    assert called
    assert any("System Diagnostics" in line for line in capture_console)


def test_run_config_command(monkeypatch, capture_console):
    """Configuration values are printed."""
    monkeypatch.setattr(system_commands.settings, "intercom_api_version", "2.10")
    monkeypatch.setattr(system_commands.settings, "openai_model", "gpt-test")
    monkeypatch.setattr(system_commands.settings, "default_analysis_days", 7)
    monkeypatch.setattr(system_commands.settings, "output_directory", "/tmp/out")
    monkeypatch.setattr(system_commands.settings, "log_level", "DEBUG")
    monkeypatch.setattr(system_commands.settings, "default_tier1_countries", ["US", "CA"])

    system_commands.run_config_command()

    assert any("Output Directory" in line for line in capture_console)


def test_help_commands(monkeypatch):
    """Help system entry points call the correct helpers."""
    help_mock = MagicMock()
    monkeypatch.setattr(system_commands, "help_system", help_mock)

    system_commands.run_help_command()
    system_commands.run_interactive_command()
    system_commands.run_list_commands_command()
    system_commands.run_examples_command()

    help_mock.show_main_help.assert_called()
    help_mock.interactive_mode.assert_called_once()
    help_mock.show_examples.assert_called_once()


def test_run_show_categories_command(monkeypatch, capture_console):
    """Category listing prints taxonomy data."""

    class DummyFilters:
        def __init__(self):
            self.taxonomy_config = {
                "primary_categories": {
                    "Billing": {"subcategories": ["Refunds"], "description": "Money stuff"}
                }
            }

    monkeypatch.setattr(system_commands, "CategoryFilters", lambda: DummyFilters())

    system_commands.run_show_categories_command()

    assert any("Billing" in line for line in capture_console)

