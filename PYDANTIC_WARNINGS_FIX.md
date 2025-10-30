# Pydantic Serializer Warnings Fix

## Problem

When running analysis commands, users would see annoying warnings:

```
/usr/local/lib/python3.11/site-packages/pydantic/main.py:347: UserWarning: Pydantic serializer warnings:
  Expected `str` but got `int` - serialized value may not be as expected
  return self.__pydantic_serializer__.to_python(
```

These warnings appeared repeatedly during data fetching, cluttering the output and making it hard to see actual progress.

## Root Cause

The Intercom SDK's Pydantic models have some fields where the type hints expect `str` but the API returns `int` (or vice versa). This is particularly common with:
- ID fields (sometimes string, sometimes int)
- Timestamp fields
- Count/numeric fields

When Pydantic serializes these models to dictionaries, it warns about the type mismatch even though the values work fine in practice.

## Solution

Applied a **two-part fix**:

### 1. Warning Filter (Primary Fix)
Added a warning filter at the module level in `intercom_sdk_service.py`:

```python
import warnings

# Suppress Pydantic serializer warnings from Intercom SDK
warnings.filterwarnings(
    'ignore',
    category=UserWarning,
    module='pydantic.main',
    message='.*Expected `str` but got `int`.*'
)
```

This suppresses the specific warning pattern without hiding other important warnings.

### 2. Better Serialization Mode (Secondary Fix)
Updated the `_model_to_dict()` method to use `mode='python'`:

```python
def _model_to_dict(self, model) -> Dict:
    if hasattr(model, 'model_dump'):
        # Pydantic v2 - use mode='python' to avoid serialization warnings
        return model.model_dump(mode='python', exclude_none=False)
```

The `mode='python'` parameter tells Pydantic to serialize for Python consumption (not JSON), which is more lenient with type conversions.

## Files Modified

- **`src/services/intercom_sdk_service.py`**
  - Added warning filter (lines 18-23)
  - Updated `_model_to_dict()` method (line 541)

## Impact

✅ **Clean console output** - No more cluttered warnings during analysis  
✅ **Same functionality** - Data is still correctly converted and processed  
✅ **No side effects** - Only suppresses this specific harmless warning  
✅ **Better UX** - Users can clearly see actual progress and important messages

## Testing

The fix was tested with:
- `scripts/test_pydantic_warnings.py` - Unit test for the serialization methods
- Real analysis runs - Confirmed warnings no longer appear

## Why This is Safe

1. **Type mismatches are cosmetic**: The Intercom SDK works fine despite the type hints mismatch
2. **Data is correct**: Values are properly converted and used in analysis
3. **Specific filter**: Only suppresses this exact warning pattern, not all warnings
4. **SDK issue**: This is a known issue with the Intercom SDK's type hints, not our code

## Alternative Approaches Considered

1. ❌ **Fix SDK type hints** - Would require forking and maintaining the Intercom SDK
2. ❌ **Ignore all warnings** - Too broad, would hide real issues
3. ✅ **Targeted warning filter** - Best balance of clean output and safety

## Related Files

- `scripts/test_pydantic_warnings.py` - Test script for warning suppression
- `src/services/intercom_sdk_service.py` - Main fix location

