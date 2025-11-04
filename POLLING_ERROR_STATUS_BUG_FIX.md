# Polling Error Status Bug Fix

## Problem

**Symptom:** Even when generation completes successfully, the status shows as "ERROR" in the UI.

**Root Cause:** `railway_web.py` lines 1283-1287

```python
elif output.get("type") == "error":
    await state_manager.update_execution_status(
        execution_id, ExecutionStatus.FAILED, 
        error_message=output.get("data")
    )
```

This code sets the execution status to `FAILED` on **ANY** error message, even if it's:
- A warning
- An informational error (e.g., "Skipping optional step")
- A recoverable error
- An intermediate error that gets fixed

### The Flow:
1. Command runs successfully
2. During execution, logs show: `{"type": "error", "data": "Optional step skipped"}`
3. Status immediately updated to `FAILED` ❌
4. Command continues and completes successfully
5. Final status never updated because already `FAILED`
6. UI shows "ERROR" even though command succeeded ❌

## The Fix

### Option 1: Only Set FAILED on Critical Errors

```python
elif output.get("type") == "error":
    # Don't immediately fail - log error but let command continue
    # Only fail if this is marked as a critical error
    error_data = output.get("data", "")
    
    # Check if this is a critical error
    critical_markers = [
        "CRITICAL",
        "Fatal",
        "Exception",
        "Traceback",
        "failed to complete"
    ]
    
    is_critical = any(marker in error_data for marker in critical_markers)
    
    if is_critical:
        await state_manager.update_execution_status(
            execution_id, ExecutionStatus.FAILED, 
            error_message=error_data
        )
    else:
        # Just log the error, don't change status
        logger.warning(
            "non_critical_error_logged",
            execution_id=execution_id,
            error=error_data
        )
```

### Option 2: Wait for Final Status

```python
elif output.get("type") == "error":
    # Store error but don't immediately update status
    # Let the command complete and check return code
    if not hasattr(state_manager, '_pending_errors'):
        state_manager._pending_errors = {}
    
    if execution_id not in state_manager._pending_errors:
        state_manager._pending_errors[execution_id] = []
    
    state_manager._pending_errors[execution_id].append(output.get("data"))
    
    # Don't update status yet - wait for completion
```

Then at the end of execution:

```python
# Check final return code
if return_code == 0:
    # Success despite errors
    await state_manager.update_execution_status(
        execution_id, ExecutionStatus.COMPLETED, 
        return_code=0,
        warnings=state_manager._pending_errors.get(execution_id, [])
    )
else:
    # Actually failed
    await state_manager.update_execution_status(
        execution_id, ExecutionStatus.FAILED, 
        return_code=return_code,
        error_message="\n".join(state_manager._pending_errors.get(execution_id, []))
    )
```

### Option 3: Priority-Based Status Updates (Recommended)

```python
# Define status priority (higher = more important)
STATUS_PRIORITY = {
    ExecutionStatus.COMPLETED: 10,   # Highest - if completed, stay completed
    ExecutionStatus.FAILED: 8,       # Critical failure
    ExecutionStatus.ERROR: 6,        # Non-critical error
    ExecutionStatus.RUNNING: 4,      # In progress
    ExecutionStatus.PENDING: 2       # Lowest
}

async def update_execution_status_safe(
    execution_id: str, 
    new_status: ExecutionStatus,
    **kwargs
):
    """
    Update status only if new status has higher priority than current.
    This prevents intermediate errors from overwriting final success.
    """
    current_execution = await state_manager.get_execution(execution_id)
    current_status = current_execution.get('status')
    
    current_priority = STATUS_PRIORITY.get(current_status, 0)
    new_priority = STATUS_PRIORITY.get(new_status, 0)
    
    if new_priority >= current_priority:
        await state_manager.update_execution_status(
            execution_id, new_status, **kwargs
        )
    else:
        logger.debug(
            "status_update_skipped",
            execution_id=execution_id,
            current_status=current_status,
            attempted_new_status=new_status,
            reason="lower_priority"
        )

# Then in the polling loop:
elif output.get("type") == "error":
    # Try to update to ERROR (priority 6)
    # If already COMPLETED (priority 10), this won't overwrite
    await update_execution_status_safe(
        execution_id, ExecutionStatus.ERROR, 
        error_message=output.get("data")
    )
```

## Recommended Implementation

Use **Option 3** (Priority-Based) because:
1. ✅ Prevents intermediate errors from overwriting final success
2. ✅ Still captures critical failures
3. ✅ Allows warnings/errors to be logged without changing final status
4. ✅ Handles edge cases gracefully

## Files to Modify

1. **`railway_web.py`** (lines 1283-1287)
   - Replace immediate `FAILED` update with priority-based logic
   - Add `STATUS_PRIORITY` dict
   - Add `update_execution_status_safe()` helper

2. **`src/services/execution_state_manager.py`** (if exists)
   - Add priority-based update method
   - Track error history without changing status

3. **Frontend (`static/app.js`)**
   - Handle `ERROR` vs `FAILED` differently
   - Show errors as warnings if final status is `COMPLETED`

## Testing

### Test Case 1: Success with Warnings
```bash
# Command that logs errors but completes successfully
python src/main.py --test-mode
```

**Expected:**
- Status: `COMPLETED` ✅
- Warnings shown but not marked as failure

### Test Case 2: Actual Failure
```bash
# Command that actually fails
python src/main.py --invalid-arg
```

**Expected:**
- Status: `FAILED` ❌
- Error message displayed

### Test Case 3: Success then Error
```bash
# Command completes, then logs error
python src/main.py --cleanup-errors
```

**Expected:**
- Status: `COMPLETED` ✅ (doesn't revert to ERROR)
- Cleanup errors logged as warnings

---

## Implementation Code

```python
# Add to railway_web.py after imports

STATUS_PRIORITY = {
    ExecutionStatus.COMPLETED: 10,
    ExecutionStatus.FAILED: 8,
    ExecutionStatus.ERROR: 6,
    ExecutionStatus.RUNNING: 4,
    ExecutionStatus.CANCELLED: 3,
    ExecutionStatus.PENDING: 2
}


async def update_status_with_priority(
    state_manager,
    execution_id: str,
    new_status: ExecutionStatus,
    **kwargs
):
    """Update status only if new status has equal or higher priority."""
    try:
        current = await state_manager.get_execution_status(execution_id)
        current_priority = STATUS_PRIORITY.get(current, 0)
        new_priority = STATUS_PRIORITY.get(new_status, 0)
        
        if new_priority >= current_priority:
            await state_manager.update_execution_status(
                execution_id, new_status, **kwargs
            )
            return True
        return False
    except Exception:
        # If can't get current status, just update
        await state_manager.update_execution_status(
            execution_id, new_status, **kwargs
        )
        return True


# Replace lines 1283-1287 with:
elif output.get("type") == "error":
    # Use priority-based update - won't overwrite COMPLETED
    await update_status_with_priority(
        state_manager,
        execution_id, 
        ExecutionStatus.ERROR,  # Lower priority than COMPLETED
        error_message=output.get("data")
    )
```

---

**This fix ensures successful completions aren't overwritten by intermediate errors.**

