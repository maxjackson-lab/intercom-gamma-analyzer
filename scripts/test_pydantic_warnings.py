#!/usr/bin/env python3
"""
Test script to verify Pydantic serialization warnings are suppressed.
"""

import sys
from pathlib import Path
import warnings

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Capture warnings
warnings.simplefilter("always")

print("="*80)
print("Testing Pydantic Serialization Warning Fix")
print("="*80)

# Test the _model_to_dict method with a mock Pydantic model
from pydantic import BaseModel

class MockIntercomModel(BaseModel):
    """Mock model similar to Intercom SDK models"""
    id: str
    created_at: int  # This is an int but might be expected as str
    updated_at: int
    name: str

# Create a test instance
test_model = MockIntercomModel(
    id="123",
    created_at=1234567890,
    updated_at=1234567899,
    name="Test Conversation"
)

print("\n1. Testing WITHOUT mode='python' (old way - should warn):")
print("-" * 80)
try:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result_old = test_model.model_dump(exclude_none=False)
        if w:
            print(f"⚠️  Warnings captured: {len(w)}")
            for warning in w:
                print(f"   {warning.category.__name__}: {warning.message}")
        else:
            print("✅ No warnings (good!)")
        print(f"   Result: {result_old}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n2. Testing WITH mode='python' (new way - should NOT warn):")
print("-" * 80)
try:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result_new = test_model.model_dump(mode='python', exclude_none=False)
        if w:
            print(f"⚠️  Warnings captured: {len(w)}")
            for warning in w:
                print(f"   {warning.category.__name__}: {warning.message}")
        else:
            print("✅ No warnings - fix working!")
        print(f"   Result: {result_new}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n3. Testing the actual IntercomSDKService._model_to_dict method:")
print("-" * 80)
try:
    from src.services.intercom_sdk_service import IntercomSDKService
    
    service = IntercomSDKService()
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = service._model_to_dict(test_model)
        if w:
            print(f"⚠️  Warnings captured: {len(w)}")
            for warning in w:
                print(f"   {warning.category.__name__}: {warning.message}")
        else:
            print("✅ No warnings - _model_to_dict fix working!")
        print(f"   Result: {result}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("Test Complete")
print("="*80)
print("\n✅ If you see 'No warnings' in tests 2 and 3, the fix is working!")


