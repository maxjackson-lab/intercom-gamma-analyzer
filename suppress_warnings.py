"""
Global warning suppression module.
Import this FIRST in any entry point to suppress Pydantic warnings.

This ensures warnings are suppressed before any other imports happen.
"""

import warnings
import sys

# Nuclear option: Suppress ALL Pydantic serializer warnings
# This must be imported before any Pydantic models are loaded

# Suppress the specific Pydantic serializer warning patterns
warnings.filterwarnings('ignore', category=UserWarning, message='.*Pydantic serializer warnings.*')
warnings.filterwarnings('ignore', category=UserWarning, message='.*Expected.*but got.*')
warnings.filterwarnings('ignore', category=UserWarning, message='.*serialized value may not be as expected.*')

# Also suppress at the warnings module level
warnings.simplefilter('ignore', UserWarning)

# Print confirmation (can be removed later)
if '--verbose' in sys.argv or '-v' in sys.argv:
    print("✅ Pydantic warning suppression active")


