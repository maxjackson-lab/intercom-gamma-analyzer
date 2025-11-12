"""
Test suite for compare-snapshots CLI command.

Tests cover:
- Command execution with valid snapshot IDs
- Error handling for missing snapshots
- Rich table and panel display
- Show-details flag functionality
- Integration with HistoricalSnapshotService
- End-to-end CLI invocation
"""

import pytest
import tempfile
from pathlib import Path
from datetime import date
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.cli.commands import compare_snapshots
from src.services.historical_snapshot_service import HistoricalSnapshotService
from src.services.duckdb_storage import DuckDBStorage


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_duckdb_with_snapshots():
    """Create temp DuckDB database with 2 sample snapshots"""
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
        db_path = tmp.name
    
    storage = DuckDBStorage(db_path)
    service = HistoricalSnapshotService(storage)
    
    # Create two sample snapshots
    snap1_data = {
        'snapshot_id': 'weekly_20251031',
        'analysis_type': 'weekly',
        'period_start': date(2025, 10, 25),
        'period_end': date(2025, 10, 31),
        'total_conversations': 120,
        'topic_volumes': {'Billing': 45, 'API': 18, 'Sites': 22},
        'topic_sentiments': {'Billing': {'positive': 0.6, 'negative': 0.3}},
        'resolution_metrics': {'fcr_rate': 0.80}
    }
    
    snap2_data = {
        'snapshot_id': 'weekly_20251107',
        'analysis_type': 'weekly',
        'period_start': date(2025, 11, 1),
        'period_end': date(2025, 11, 7),
        'total_conversations': 150,
        'topic_volumes': {'Billing': 52, 'API': 52, 'Sites': 25, 'NewTopic': 10},
        'topic_sentiments': {'Billing': {'positive': 0.7, 'negative': 0.2}},
        'resolution_metrics': {'fcr_rate': 0.85}
    }
    
    storage.store_analysis_snapshot(snap1_data)
    storage.store_analysis_snapshot(snap2_data)
    
    yield db_path
    
    # Cleanup
    storage.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_console():
    """Mock Rich console to capture output"""
    with patch('src.cli.commands.console') as mock:
        yield mock


# =============================================================================
# Basic Command Tests
# =============================================================================

@pytest.mark.asyncio
async def test_compare_snapshots_command_success(temp_duckdb_with_snapshots, mock_console):
    """Test successful snapshot comparison"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage:
        # Setup mock to use temp DB
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Verify result structure
        assert 'comparison' in result
        assert 'current_snapshot' in result
        assert 'prior_snapshot' in result
        assert 'error' not in result
        
        # Verify comparison data
        comparison = result['comparison']
        assert 'volume_changes' in comparison
        assert 'significant_changes' in comparison
        
        # Verify console.print was called for tables
        assert mock_console.print.called


@pytest.mark.asyncio
async def test_compare_snapshots_command_current_not_found(temp_duckdb_with_snapshots, mock_console):
    """Test error handling when current snapshot doesn't exist"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage:
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        result = await compare_snapshots('nonexistent_id', 'weekly_20251031', False)
        
        # Verify error response
        assert 'error' in result
        assert 'not found' in result['error']
        
        # Verify error message displayed
        mock_console.print.assert_called()
        error_call = [call for call in mock_console.print.call_args_list if 'Error' in str(call)]
        assert len(error_call) > 0


@pytest.mark.asyncio
async def test_compare_snapshots_command_prior_not_found(temp_duckdb_with_snapshots, mock_console):
    """Test error handling when prior snapshot doesn't exist"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage:
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        result = await compare_snapshots('weekly_20251107', 'nonexistent_id', False)
        
        # Verify error response
        assert 'error' in result
        assert 'not found' in result['error']


# =============================================================================
# Display Tests
# =============================================================================

@pytest.mark.asyncio
async def test_compare_snapshots_command_displays_tables(temp_duckdb_with_snapshots):
    """Test that comparison displays Rich tables"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage, \
         patch('src.cli.commands.console') as mock_console, \
         patch('src.cli.commands.Table') as MockTable:
        
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Verify Tables were created
        assert MockTable.called
        # At least 2 tables: summary and volume changes
        assert MockTable.call_count >= 2


@pytest.mark.asyncio
async def test_compare_snapshots_command_displays_panels(temp_duckdb_with_snapshots):
    """Test that significant changes display as panels"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage, \
         patch('src.cli.commands.console') as mock_console, \
         patch('src.cli.commands.Panel') as MockPanel:
        
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Verify Panels were created (for significant changes, emerging, declining)
        assert MockPanel.called


@pytest.mark.asyncio
async def test_compare_snapshots_command_show_details_flag(temp_duckdb_with_snapshots):
    """Test show_details flag displays additional information"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage, \
         patch('src.cli.commands.console') as mock_console, \
         patch('src.cli.commands.Table') as MockTable:
        
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        # Call with show_details=True
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', True)
        
        # Should create more tables (sentiment and resolution metrics)
        # Basic mode: ~2 tables, Detailed mode: ~4+ tables
        assert MockTable.call_count >= 3


# =============================================================================
# Service Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_compare_snapshots_command_calls_service_calculate_comparison(temp_duckdb_with_snapshots):
    """Test command calls HistoricalSnapshotService.calculate_comparison"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage, \
         patch('src.cli.commands.HistoricalSnapshotService') as MockService:
        
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        mock_service_instance = MagicMock()
        mock_service_instance.calculate_comparison.return_value = {
            'comparison_id': 'test',
            'volume_changes': {},
            'sentiment_changes': {},
            'resolution_changes': {},
            'significant_changes': [],
            'emerging_patterns': [],
            'declining_patterns': []
        }
        MockService.return_value = mock_service_instance
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Verify calculate_comparison was called
        mock_service_instance.calculate_comparison.assert_called_once()


@pytest.mark.asyncio
async def test_compare_snapshots_command_handles_service_error(temp_duckdb_with_snapshots, mock_console):
    """Test command handles service errors gracefully"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage, \
         patch('src.cli.commands.HistoricalSnapshotService') as MockService:
        
        MockStorage.return_value = DuckDBStorage(temp_duckdb_with_snapshots)
        
        # Mock service to raise exception
        mock_service_instance = MagicMock()
        mock_service_instance.calculate_comparison.side_effect = Exception("Service error")
        MockService.return_value = mock_service_instance
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Should return error
        assert 'error' in result


# =============================================================================
# Data Validation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_compare_snapshots_validates_snapshot_data(temp_duckdb_with_snapshots):
    """Test command validates snapshot data before comparison"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage:
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Verify snapshots were retrieved
        assert result['current_snapshot'] is not None
        assert result['prior_snapshot'] is not None
        assert result['current_snapshot']['snapshot_id'] == 'weekly_20251107'
        assert result['prior_snapshot']['snapshot_id'] == 'weekly_20251031'


@pytest.mark.asyncio
async def test_compare_snapshots_returns_counts(temp_duckdb_with_snapshots):
    """Test command returns pattern counts"""
    with patch('src.cli.commands.DuckDBStorage') as MockStorage:
        mock_storage = DuckDBStorage(temp_duckdb_with_snapshots)
        MockStorage.return_value = mock_storage
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Verify count fields
        assert 'significant_changes_count' in result
        assert 'emerging_patterns_count' in result
        assert 'declining_patterns_count' in result
        assert isinstance(result['significant_changes_count'], int)


# =============================================================================
# CLI Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_compare_snapshots_cli_help_text():
    """Test CLI help text is properly defined"""
    from src.main import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(cli, ['compare-snapshots', '--help'])
    
    # Verify help text
    assert result.exit_code == 0
    assert 'Compare two analysis snapshots' in result.output
    assert '--current' in result.output
    assert '--prior' in result.output
    assert '--show-details' in result.output


@pytest.mark.asyncio
async def test_compare_snapshots_cli_missing_required_args():
    """Test CLI fails when required args are missing"""
    from src.main import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    
    # Missing --prior
    result = runner.invoke(cli, ['compare-snapshots', '--current', 'weekly_20251107'])
    assert result.exit_code != 0
    assert 'Missing option' in result.output or 'required' in result.output.lower()
    
    # Missing --current
    result = runner.invoke(cli, ['compare-snapshots', '--prior', 'weekly_20251031'])
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_compare_snapshots_end_to_end(temp_duckdb_with_snapshots):
    """Full end-to-end test with real DuckDB and service"""
    # This test uses real implementations (no mocks)
    storage = DuckDBStorage(temp_duckdb_with_snapshots)
    service = HistoricalSnapshotService(storage)
    
    # Retrieve snapshots
    current = storage.get_analysis_snapshot('weekly_20251107')
    prior = storage.get_analysis_snapshot('weekly_20251031')
    
    # Calculate comparison
    comparison = service.calculate_comparison(current, prior)
    
    # Verify comparison is comprehensive
    assert 'volume_changes' in comparison
    assert 'sentiment_changes' in comparison
    assert 'resolution_changes' in comparison
    assert 'significant_changes' in comparison
    assert 'emerging_patterns' in comparison
    assert 'declining_patterns' in comparison
    
    # Verify specific changes detected
    assert 'API' in comparison['volume_changes']
    assert 'NewTopic' in [p['topic'] for p in comparison['emerging_patterns']]
    
    # Verify significant change for API (18 -> 52 = +189%)
    sig_topics = [c['topic'] for c in comparison['significant_changes']]
    assert 'API' in sig_topics
    
    storage.close()


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_compare_snapshots_same_id():
    """Test comparing a snapshot with itself"""
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
        db_path = tmp.name
    
    storage = DuckDBStorage(db_path)
    snap_data = {
        'snapshot_id': 'weekly_20251107',
        'analysis_type': 'weekly',
        'period_start': date(2025, 11, 1),
        'period_end': date(2025, 11, 7),
        'total_conversations': 100,
        'topic_volumes': {'Billing': 50}
    }
    storage.store_analysis_snapshot(snap_data)
    
    with patch('src.cli.commands.DuckDBStorage') as MockStorage:
        MockStorage.return_value = storage
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251107', False)
        
        # Should succeed but show no changes
        assert 'comparison' in result
        volume_changes = result['comparison']['volume_changes']
        # All changes should be 0
        for topic, changes in volume_changes.items():
            assert changes['change'] == 0
            assert changes['pct'] == 0
    
    storage.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_compare_snapshots_empty_topics():
    """Test comparison when one snapshot has no topics"""
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
        db_path = tmp.name
    
    storage = DuckDBStorage(db_path)
    
    snap1_data = {
        'snapshot_id': 'weekly_20251031',
        'analysis_type': 'weekly',
        'period_start': date(2025, 10, 25),
        'period_end': date(2025, 10, 31),
        'total_conversations': 0,
        'topic_volumes': {}  # No topics
    }
    
    snap2_data = {
        'snapshot_id': 'weekly_20251107',
        'analysis_type': 'weekly',
        'period_start': date(2025, 11, 1),
        'period_end': date(2025, 11, 7),
        'total_conversations': 100,
        'topic_volumes': {'Billing': 50, 'API': 30}
    }
    
    storage.store_analysis_snapshot(snap1_data)
    storage.store_analysis_snapshot(snap2_data)
    
    with patch('src.cli.commands.DuckDBStorage') as MockStorage:
        MockStorage.return_value = storage
        
        result = await compare_snapshots('weekly_20251107', 'weekly_20251031', False)
        
        # Should succeed and detect all topics as emerging
        assert 'comparison' in result
        emerging = result['comparison']['emerging_patterns']
        assert len(emerging) == 2
        emerging_topics = [p['topic'] for p in emerging]
        assert 'Billing' in emerging_topics
        assert 'API' in emerging_topics
    
    storage.close()
    Path(db_path).unlink(missing_ok=True)















