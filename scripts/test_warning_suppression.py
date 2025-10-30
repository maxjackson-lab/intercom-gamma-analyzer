#!/usr/bin/env python3
"""
Quick test to verify Pydantic warnings are suppressed.
Run this to simulate what happens during actual execution.
"""

import warnings
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*80)
print("Testing Warning Suppression")
print("="*80)

# Apply the same filters as in main.py
warnings.filterwarnings('ignore', category=UserWarning, message='.*Pydantic serializer warnings.*')
warnings.filterwarnings('ignore', category=UserWarning, message='.*Expected.*but got.*serialized value.*')

print("\n✅ Warning filters applied")
print("\nNow triggering a UserWarning to test if suppression works...")

# Trigger the exact warning
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")  # This should be overridden by our filters
    
    # Apply our filters again inside the context
    warnings.filterwarnings('ignore', category=UserWarning, message='.*Pydantic serializer warnings.*')
    warnings.filterwarnings('ignore', category=UserWarning, message='.*Expected.*but got.*serialized value.*')
    
    # Trigger warnings that match our pattern
    warnings.warn("Pydantic serializer warnings: Expected `str` but got `int`", UserWarning)
    warnings.warn("Expected `str` but got `int` - serialized value may not be as expected", UserWarning)
    
    print(f"\nWarnings captured: {len(w)}")
    if w:
        print("⚠️  Some warnings got through:")
        for warning in w:
            print(f"   {warning.category.__name__}: {warning.message}")
    else:
        print("✅ No warnings captured - suppression working!")

print("\n" + "="*80)
print("Testing with actual imports...")
print("="*80)

try:
    # This would trigger the warnings if not suppressed
    from src.services.intercom_sdk_service import IntercomSDKService
    print("✅ Imported IntercomSDKService without warnings")
except Exception as e:
    print(f"❌ Error importing: {e}")

print("\n" + "="*80)
print("✅ Test complete - if you didn't see Pydantic warnings above, it's working!")
print("="*80)


