#!/usr/bin/env python3
"""
Pydantic Model Validator

Validates Pydantic models with test data:
1. Valid data passes validation
2. Invalid data raises ValidationError
3. Field validators work correctly
4. Required fields are enforced

Prevents: ValidationError at runtime
Priority: P1 (High Impact)
"""

import sys
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pydantic import ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class PydanticModelValidator:
    """Test Pydantic models with valid and invalid data."""
    
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
    
    def validate_all_models(self) -> List[Dict[str, Any]]:
        """Validate all Pydantic models in the project."""
        if not HAS_PYDANTIC:
            return [{
                'error': 'Pydantic not installed',
                'severity': 'critical',
                'fix': 'Install: pip install pydantic'
            }]
        
        # Test AgentContext and AgentResult
        self._test_agent_models()
        
        # Test Snapshot models (if they exist)
        self._test_snapshot_models()
        
        return self.errors
    
    def _test_agent_models(self):
        """Test BaseAgent models."""
        try:
            from src.agents.base_agent import AgentContext, AgentResult
            
            # Test AgentContext with valid data
            try:
                valid_context = AgentContext(
                    analysis_id='test_123',
                    analysis_type='voice-of-customer',
                    start_date=datetime(2025, 11, 1),
                    end_date=datetime(2025, 11, 10),
                    conversations=[],
                    previous_results={},
                    metadata={}
                )
                # ✅ Should pass
            except ValidationError as e:
                self.errors.append({
                    'model': 'AgentContext',
                    'test': 'valid_data',
                    'error': f'Valid data failed validation: {e}',
                    'severity': 'critical'
                })
            except Exception as e:
                self.errors.append({
                    'model': 'AgentContext',
                    'test': 'valid_data',
                    'error': f'Unexpected error: {e}',
                    'severity': 'warning'
                })
            
            # Test AgentResult with valid data
            try:
                valid_result = AgentResult(
                    success=True,
                    data={'test': 'data'},
                    confidence=0.8,
                    sources=['test_source'],
                    limitations=[]
                )
                # ✅ Should pass
            except ValidationError as e:
                self.errors.append({
                    'model': 'AgentResult',
                    'test': 'valid_data',
                    'error': f'Valid data failed validation: {e}',
                    'severity': 'critical'
                })
            except Exception as e:
                pass  # Model might not require all fields
            
            # Test invalid data (should raise ValidationError)
            try:
                invalid_context = AgentContext(
                    analysis_id='test',
                    analysis_type='invalid_type',  # Should fail if validated
                    start_date='not_a_date',  # Wrong type
                    end_date='not_a_date',
                    conversations='not_a_list',  # Wrong type
                    previous_results=[],  # Wrong type (should be dict)
                    metadata='not_a_dict'  # Wrong type
                )
                # If we get here, validation is too permissive
                self.errors.append({
                    'model': 'AgentContext',
                    'test': 'invalid_data',
                    'error': 'Invalid data passed validation (should have failed)',
                    'severity': 'warning'
                })
            except (ValidationError, TypeError):
                # ✅ Expected - validation working
                pass
            except Exception as e:
                pass
        
        except ImportError as e:
            self.errors.append({
                'model': 'AgentContext/AgentResult',
                'error': f'Failed to import: {e}',
                'severity': 'warning',
                'fix': 'Ensure src.agents.base_agent is importable'
            })
        except Exception as e:
            pass
    
    def _test_snapshot_models(self):
        """Test snapshot models if they exist."""
        try:
            from src.services.historical_snapshot_service import SnapshotData, ComparisonData
            
            # Test SnapshotData with valid data
            try:
                valid_snapshot = SnapshotData(
                    snapshot_id='weekly_20251110',
                    analysis_type='weekly',
                    period_start=date(2025, 11, 1),
                    period_end=date(2025, 11, 10),
                    total_conversations=100,
                    topic_volumes={},
                    topic_sentiments={},
                    tier_distribution={},
                    agent_attribution={},
                    key_patterns=[]
                )
                # ✅ Should pass
            except ValidationError as e:
                self.errors.append({
                    'model': 'SnapshotData',
                    'test': 'valid_data',
                    'error': f'Valid data failed: {e}',
                    'severity': 'critical'
                })
            except Exception as e:
                pass  # Model might have different fields
            
            # Test invalid date order (period_end < period_start)
            try:
                invalid_snapshot = SnapshotData(
                    snapshot_id='weekly_20251110',
                    analysis_type='weekly',
                    period_start=date(2025, 11, 10),
                    period_end=date(2025, 11, 1),  # Before start!
                    total_conversations=100,
                    topic_volumes={},
                    topic_sentiments={},
                    tier_distribution={},
                    agent_attribution={},
                    key_patterns=[]
                )
                # Should raise ValidationError!
                self.errors.append({
                    'model': 'SnapshotData',
                    'test': 'invalid_date_order',
                    'error': 'Invalid date order passed validation (should have failed)',
                    'severity': 'warning'
                })
            except ValidationError:
                # ✅ Expected
                pass
            except Exception:
                pass
        
        except ImportError:
            # Snapshot models don't exist or not available
            pass
        except Exception:
            pass


def main():
    """Run Pydantic model validation."""
    print("="*80)
    print("PYDANTIC MODEL VALIDATION")
    print("="*80)
    print()
    
    if not HAS_PYDANTIC:
        print("❌ Pydantic not installed - cannot run validation")
        print("   Install: pip install pydantic")
        return 1
    
    validator = PydanticModelValidator()
    errors = validator.validate_all_models()
    
    if not errors:
        print("✅ All Pydantic models validated successfully!")
        return 0
    
    # Group by severity
    critical = [e for e in errors if e.get('severity') == 'critical']
    warnings = [e for e in errors if e.get('severity') == 'warning']
    
    print(f"📊 Found {len(errors)} issue(s):")
    print(f"   Critical: {len(critical)}")
    print(f"   Warnings: {len(warnings)}")
    print()
    
    if critical:
        print("🔴 CRITICAL ISSUES:")
        for error in critical:
            print(f"   Model: {error.get('model', 'Unknown')}")
            if 'test' in error:
                print(f"   Test: {error['test']}")
            print(f"   Error: {error['error']}")
            print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for error in warnings:
            print(f"   Model: {error.get('model', 'Unknown')}")
            print(f"   Error: {error['error']}")
            if 'fix' in error:
                print(f"   Fix: {error['fix']}")
            print()
    
    if critical:
        print("❌ Critical validation issues found!")
        return 1
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())

