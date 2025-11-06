# Historical Snapshot Service - Quick Reference

Fast reference guide for using the enhanced HistoricalSnapshotService with best practices.

---

## 🚀 Basic Usage

### Save a Snapshot (Async - Recommended)

```python
from src.services.duckdb_storage import DuckDBStorage
from src.services.historical_snapshot_service import HistoricalSnapshotService

# Initialize
storage = DuckDBStorage()
service = HistoricalSnapshotService(storage)

# In async context (e.g., TopicOrchestrator)
snapshot_id = await service.save_snapshot_async(analysis_output, 'weekly')
print(f"Saved: {snapshot_id}")
```

### Save a Snapshot (Sync - Backward Compatible)

```python
# In sync context
snapshot_id = service.save_snapshot(analysis_output, 'weekly')
```

---

## 📊 List Snapshots

### From CLI

```bash
# List all snapshots
python src/main.py list-snapshots

# Filter by type
python src/main.py list-snapshots --type weekly

# Show only unreviewed
python src/main.py list-snapshots --show-unreviewed

# Limit results
python src/main.py list-snapshots --limit 20
```

### From Code

```python
# Async
snapshots = await service.list_snapshots_async('weekly', limit=10)

# Sync
snapshots = service.list_snapshots('weekly', limit=10)

# Filter reviewed status in code
unreviewed = [s for s in snapshots if not s['reviewed']]
```

---

## 🔍 Retrieve Snapshots

### Get Specific Snapshot

```python
snapshot = storage.get_analysis_snapshot('weekly_20251107')

if snapshot:
    print(f"Conversations: {snapshot['total_conversations']}")
    print(f"Topics: {snapshot['topic_volumes']}")
```

### Get Prior Period

```python
# Get previous week's snapshot
prior = service.get_prior_snapshot('weekly_20251114', 'weekly')

if prior:
    print(f"Prior week: {prior['snapshot_id']}")
```

---

## 📈 Compare Snapshots

```python
# Get current and prior
current = storage.get_analysis_snapshot('weekly_20251114')
prior = service.get_prior_snapshot('weekly_20251114', 'weekly')

if current and prior:
    # Calculate comparison
    comparison = service.calculate_comparison(current, prior)
    
    # Access changes
    volume_changes = comparison['volume_changes']
    for topic, changes in volume_changes.items():
        print(f"{topic}: {changes['change']:+d} ({changes['pct']:+.1%})")
```

---

## ✅ Mark as Reviewed

```python
# Mark snapshot as reviewed
storage.mark_snapshot_reviewed(
    snapshot_id='weekly_20251107',
    reviewed_by='max.jackson',
    notes='Insights look good, shared with team'
)
```

---

## 📋 Check Historical Context

```python
context = service.get_historical_context()

print(f"Weeks available: {context['weeks_available']}")
print(f"Can do trends: {context['can_do_trends']}")  # True if ≥4 weeks
print(f"Can do seasonality: {context['can_do_seasonality']}")  # True if ≥12 weeks

if context['has_baseline']:
    print(f"Baseline since: {context['baseline_date']}")
```

---

## 🔧 Advanced: Using Context Managers

### Safe Transactions

```python
from src.services.historical_snapshot_service import SnapshotData

# Validate with Pydantic
snapshot = SnapshotData.model_validate(raw_data)

# Save with transaction safety
with storage.transaction():
    storage.store_analysis_snapshot(snapshot.model_dump())
    storage.store_metrics_timeseries(metrics)
    # Commits on success, rolls back on error
```

### Safe Connection Access

```python
with storage.get_connection() as conn:
    result = conn.execute("""
        SELECT snapshot_id, total_conversations 
        FROM analysis_snapshots 
        WHERE analysis_type = 'weekly'
        ORDER BY period_start DESC
        LIMIT 10
    """).fetchall()
```

---

## 📄 Export JSON Schema

### From CLI

```bash
# Print to console
python src/main.py export-snapshot-schema

# Export snapshot schema only
python src/main.py export-snapshot-schema --type snapshot

# Save to file
python src/main.py export-snapshot-schema \
    --output docs/api/snapshot_schema.json \
    --type all
```

### From Code

```python
# Get validation schema
validation_schema = service.get_snapshot_json_schema(mode='validation')

# Get serialization schema
serialization_schema = service.get_snapshot_json_schema(mode='serialization')

# Save to file
import json
from pathlib import Path

schema_path = Path('docs/api/snapshot_schema.json')
schema_path.write_text(json.dumps(validation_schema, indent=2))
```

---

## 🧪 Testing with New Fixtures

### Unit Tests (with mocks)

```python
def test_my_feature(mock_duckdb_storage, historical_snapshot_service):
    """Use shared fixtures from conftest.py"""
    # historical_snapshot_service already uses mock_duckdb_storage
    snapshot_id = historical_snapshot_service.save_snapshot(data, 'weekly')
    
    # Verify mock was called
    mock_duckdb_storage.store_analysis_snapshot.assert_called_once()
```

### Integration Tests (with real DB)

```python
def test_end_to_end(temp_duckdb):
    """Use real DuckDB from conftest.py"""
    service = HistoricalSnapshotService(temp_duckdb)
    
    # Save
    snap_id = service.save_snapshot(data, 'weekly')
    
    # Retrieve
    retrieved = temp_duckdb.get_analysis_snapshot(snap_id)
    assert retrieved is not None
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation(temp_duckdb, sample_analysis_output):
    service = HistoricalSnapshotService(temp_duckdb)
    
    # Test async method
    snapshot_id = await service.save_snapshot_async(
        sample_analysis_output, 
        'weekly'
    )
    
    assert snapshot_id.startswith('weekly_')
```

---

## 🐛 Error Handling

### Pydantic Validation Errors

```python
from pydantic import ValidationError

try:
    snapshot = SnapshotData.model_validate(data)
except ValidationError as e:
    # Detailed field-level errors
    for error in e.errors():
        print(f"Field: {error['loc']}")
        print(f"Error: {error['msg']}")
        print(f"Input: {error['input']}")
```

### Graceful Degradation

```python
# Service handles validation failures gracefully
snapshot_id = service.save_snapshot(incomplete_data, 'weekly')
# Returns snapshot_id even if validation fails
# Logs warning but continues
```

---

## 📊 Performance Tips

1. **Use Async Methods in Async Contexts**:
   ```python
   # ✅ Good
   await service.save_snapshot_async(data, 'weekly')
   
   # ❌ Bad (blocks event loop)
   service.save_snapshot(data, 'weekly')
   ```

2. **Reuse TypeAdapters** (already done at module level):
   ```python
   # TypeAdapters created once, reused many times
   # 3-4x faster than json.dumps/loads
   ```

3. **Batch Operations with Transactions**:
   ```python
   with storage.transaction():
       for snapshot in snapshots:
           storage.store_analysis_snapshot(snapshot)
   # Much faster than individual commits
   ```

4. **Use Context for Large Datasets**:
   ```python
   context = service.get_historical_context()
   if context['can_do_seasonality']:
       # Only run expensive seasonality analysis if enough data
       run_seasonality_analysis()
   ```

---

## 🎨 CLI Commands Reference

```bash
# List snapshots
python src/main.py list-snapshots [--type TYPE] [--limit N] [--show-reviewed] [--show-unreviewed]

# Export schema
python src/main.py export-snapshot-schema [--output FILE] [--type snapshot|comparison|all]

# Run analysis (auto-saves snapshot)
python src/main.py voice-of-customer --time-period week
```

---

## 🔐 Type Safety Examples

### Validated Snapshot Creation

```python
from src.services.historical_snapshot_service import SnapshotData
from datetime import date

# Type-safe construction
snapshot = SnapshotData(
    snapshot_id='weekly_20251107',
    analysis_type='weekly',
    period_start=date(2025, 11, 1),
    period_end=date(2025, 11, 7),
    total_conversations=150,
    topic_volumes={'Billing': 45, 'API': 18}
)

# Auto-validates:
# ✅ snapshot_id format
# ✅ analysis_type in allowed values
# ✅ period_end >= period_start
# ✅ total_conversations >= 0
```

### Validated Comparison

```python
from src.services.historical_snapshot_service import ComparisonData

comparison = ComparisonData(
    comparison_id='comp_weekly_20251114_weekly_20251107',
    comparison_type='week_over_week',
    current_snapshot_id='weekly_20251114',
    prior_snapshot_id='weekly_20251107',
    volume_changes={'Billing': {'change': 7, 'pct': 0.16}}
)

# Auto-validates comparison_id format (must start with 'comp_')
```

---

## 🎓 Migration Notes

### Existing Code Compatibility

✅ **All existing code continues to work** - sync methods maintained  
✅ **Validation is opt-in** - falls back to raw data if validation fails  
✅ **No breaking changes** - new async methods are additions

### Recommended Migration Path

1. **Phase 1** (Now): Use shared test fixtures
2. **Phase 2** (Next sprint): Migrate to async methods in TopicOrchestrator
3. **Phase 3** (Future): Use Pydantic models throughout codebase
4. **Phase 4** (Future): Remove deprecated HistoricalDataManager

---

**Last Updated**: November 4, 2025  
**Version**: 2.0 (Best Practices Enhanced)






