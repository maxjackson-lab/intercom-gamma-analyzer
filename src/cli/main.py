"""
CLI Main Entrypoint.

This module serves as the primary entry point for the CLI application,
wiring up commands and flags including the audit system.
"""
import asyncio
import click
from typing import Optional

from src.cli.entry import cli
from src.cli.sample_commands import run_sample_mode_command
from src.cli.flags import validate_sample_count

@cli.command(name='sample-mode')
@click.option('--count', type=int, callback=validate_sample_count, default=None,
              help='Number of conversations to sample (defaults per schema mode)')
@click.option('--time-period', type=click.Choice(['yesterday', 'week', 'month', 'quarter', 'year', '6-weeks']),
              default='week', help='Time period window for sampling')
@click.option('--start-date', help='Custom start date (YYYY-MM-DD)')
@click.option('--end-date', help='Custom end date (YYYY-MM-DD)')
@click.option('--save-to-file', is_flag=True, default=False,
              help='Persist sampled conversations and logs to outputs/')
@click.option('--test-llm', is_flag=True, default=False,
              help='Run production LLM sentiment test across sampled topics')
@click.option('--test-all-agents', is_flag=True, default=False,
              help='Exercise all production agents (longer runtime)')
@click.option('--show-agent-thinking', is_flag=True, default=False,
              help='Capture LLM prompts/responses for debugging')
@click.option('--llm-topic-detection', is_flag=True, default=False,
              help='Use LLM-first topic detection (higher accuracy & cost)')
@click.option('--schema-mode', type=click.Choice(['quick', 'standard', 'deep', 'comprehensive']),
              default='quick', help='Sampling preset (controls volume & diagnostics)')
@click.option('--ai-model', type=click.Choice(['openai', 'claude']), default='openai',
              help='AI provider for diagnostic LLM calls')
@click.option('--include-hierarchy/--no-include-hierarchy', default=True,
              help='Include topic hierarchy debugging block')
@click.option('--no-hierarchy', is_flag=True, default=False,
              help='Alias to disable hierarchy block (legacy flag)')
@click.option('--verbose', is_flag=True, default=False,
              help='Enable verbose DEBUG logging for sampling run')
@click.option('--audit-mode', is_flag=True, default=False,
              help='Run validation checks on all agent outputs')
def sample_mode_cli(
    count: Optional[int],
    time_period: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    save_to_file: bool,
    test_llm: bool,
    test_all_agents: bool,
    show_agent_thinking: bool,
    llm_topic_detection: bool,
    schema_mode: str,
    ai_model: str,
    include_hierarchy: bool,
    no_hierarchy: bool,
    verbose: bool,
    audit_mode: bool,
):
    """Pull a real-data sample with ultra-rich logging + diagnostics."""
    asyncio.run(
        run_sample_mode_command(
            count=count,
            start_date=start_date,
            end_date=end_date,
            time_period=time_period or 'week',
            save_to_file=save_to_file,
            test_llm=test_llm,
            test_all_agents=test_all_agents,
            show_agent_thinking=show_agent_thinking,
            llm_topic_detection=llm_topic_detection,
            schema_mode=schema_mode,
            ai_model=ai_model,
            include_hierarchy=include_hierarchy,
            no_hierarchy=no_hierarchy,
            verbose=verbose,
            audit_mode=audit_mode,
        )
    )

if __name__ == "__main__":
    cli()


