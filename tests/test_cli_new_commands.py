from click.testing import CliRunner

from src.main import cli


def test_voc_v2_cli_invokes_runner(monkeypatch):
    """Ensure voc-v2 command wires into topic orchestrator."""

    async def fake_run(*args, **kwargs):
        fake_run.called = True

    fake_run.called = False
    monkeypatch.setattr('src.main.run_topic_based_analysis_custom', fake_run)

    runner = CliRunner()
    env = {
        'INTERCOM_ACCESS_TOKEN': 'dummy',
        'OPENAI_API_KEY': 'dummy'
    }
    result = runner.invoke(
        cli,
        ['--skip-validation', 'voc-v2', '--time-period', 'week', '--test-mode', '--test-data-count', 'micro'],
        env=env
    )

    assert result.exit_code == 0
    assert fake_run.called is True


def test_agent_eval_cli_invokes_agent_performance(monkeypatch):
    """Ensure agent-eval command triggers agent performance analysis."""

    async def fake_run(*args, **kwargs):
        fake_run.called = True

    fake_run.called = False
    monkeypatch.setattr('src.main.run_agent_performance_analysis', fake_run)

    runner = CliRunner()
    env = {
        'INTERCOM_ACCESS_TOKEN': 'dummy',
        'OPENAI_API_KEY': 'dummy'
    }
    result = runner.invoke(
        cli,
        [
            '--skip-validation',
            'agent-eval',
            '--vendor', 'horatio',
            '--time-period', 'week',
            '--test-mode',
            '--test-data-count', 'micro'
        ],
        env=env
    )

    assert result.exit_code == 0
    assert fake_run.called is True

