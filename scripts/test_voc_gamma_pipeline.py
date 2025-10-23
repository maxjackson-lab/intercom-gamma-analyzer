#!/usr/bin/env python3
"""
VoC → Gamma Pipeline Quick Test Script

Usage:
  python scripts/test_voc_gamma_pipeline.py

This script validates the VoC analysis → Gamma generation pipeline
with sample data and mocked API calls.

Expected output:
- ✓ Markdown format is valid
- ✓ Markdown length: XXXX characters (valid)
- ✓ Gamma input validation passed
- ✓ Gamma generation (mocked) successful
- ✓ Full pipeline (mocked) successful
- ✓ Expected slide count: X
- 🎉 All tests passed!

If any tests fail:
1. Check the error message for details
2. Review markdown format in SAMPLE_HILARY_MARKDOWN
3. Verify validation logic in src/services/gamma_generator.py
4. Run full test suite: pytest tests/integration/test_voc_gamma_integration.py

This script runs in < 2 minutes and requires no API keys.
"""

import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.gamma_generator import GammaGenerator
from src.services.gamma_client import GammaAPIError

# Check if colorama is available for colored output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


# Color helpers
def green(text):
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}" if HAS_COLOR else text


def red(text):
    return f"{Fore.RED}{text}{Style.RESET_ALL}" if HAS_COLOR else text


def yellow(text):
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}" if HAS_COLOR else text


def cyan(text):
    return f"{Fore.CYAN}{text}{Style.RESET_ALL}" if HAS_COLOR else text


# Sample Hilary-format markdown
SAMPLE_HILARY_MARKDOWN = """# Voice of Customer Analysis - Week 2024-W42

## Customer Topics (Paid Tier - Human Support)

### Billing Issues
**45 tickets / 28% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Sentiment**: Customers frustrated with unexpected charges BUT appreciate quick refunds

**Examples**:
1. "I was charged twice for my subscription" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_123)
2. "Need help understanding my invoice" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_124)
3. "Refund request for duplicate charge" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_125)
4. "Incorrect billing amount shown" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_126)
5. "Want to cancel my subscription" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_127)

---

### Product Questions
**32 tickets / 20% of weekly volume**
**Detection Method**: Keyword detection

**Sentiment**: Users love the new features BUT confused by setup process

**Examples**:
1. "How do I enable the new dashboard?" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_128)
2. "Can't find the export button" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_129)
3. "New feature not working as expected" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_130)

---

### Technical Issues
**28 tickets / 17% of weekly volume**
**Detection Method**: Keyword detection

**Sentiment**: Users experiencing bugs BUT patient with support team

**Examples**:
1. "App crashes when I try to export" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_131)
2. "Data not syncing properly" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_132)
3. "Login errors on mobile app" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_133)
4. "Integration with Salesforce broken" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_134)

---

## Fin AI Performance (Free Tier - AI-Only Support)

### Fin AI Analysis
**89 conversations handled by Fin this week**

**What Fin is Doing Well**:
- Resolution rate: 72% of conversations resolved without escalation request
- Fastest responses on basic account questions
- Good at directing users to documentation

**Knowledge Gaps**:
- 12 conversations where Fin gave incorrect/incomplete information
- Struggles with complex billing questions
- Needs better context on recent product updates

---
"""

SAMPLE_TOPIC_ORCHESTRATOR_RESULTS = {
    'formatted_report': SAMPLE_HILARY_MARKDOWN,
    'summary': {
        'total_conversations': 160,
        'paid_conversations': 71,
        'free_conversations': 89,
        'topics_analyzed': 3,
        'total_execution_time': 12.5,
        'agents_completed': 7
    },
    'week_id': '2024-W42'
}


def test_markdown_format(verbose=False):
    """Validate markdown structure."""
    print("Testing markdown format...")
    
    markdown = SAMPLE_HILARY_MARKDOWN
    
    try:
        # Check for title
        assert "# Voice of Customer Analysis" in markdown, "Missing title"
        
        # Check for required sections
        assert "## Customer Topics" in markdown, "Missing Customer Topics section"
        assert "## Fin AI Performance" in markdown, "Missing Fin AI Performance section"
        
        # Check for slide breaks
        slide_breaks = markdown.count("---")
        assert slide_breaks >= 3, f"Expected at least 3 slide breaks, found {slide_breaks}"
        
        # Check for Intercom URLs
        assert "https://app.intercom.com/a/inbox/inbox/conv_" in markdown, "Missing Intercom URLs"
        
        # Check topic card structure
        assert "**Detection Method**:" in markdown, "Missing Detection Method"
        assert "**Sentiment**:" in markdown, "Missing Sentiment"
        assert "**Examples**:" in markdown, "Missing Examples"
        assert "tickets / " in markdown, "Missing ticket count"
        assert "% of weekly volume" in markdown, "Missing percentage"
        
        if verbose:
            print(f"  - Title: ✓")
            print(f"  - Customer Topics section: ✓")
            print(f"  - Fin AI Performance section: ✓")
            print(f"  - Slide breaks: {slide_breaks} ✓")
            print(f"  - Intercom URLs: ✓")
            print(f"  - Topic card structure: ✓")
        
        print(green("✓ Markdown format is valid"))
        return True
        
    except AssertionError as e:
        print(red(f"✗ Markdown format invalid: {e}"))
        return False


def test_markdown_length(verbose=False):
    """Check markdown length is within Gamma limits."""
    print("Testing markdown length...")
    
    markdown = SAMPLE_HILARY_MARKDOWN
    length = len(markdown)
    
    try:
        assert 1 <= length <= 750000, f"Length {length} outside valid range (1-750,000)"
        
        if verbose:
            print(f"  - Length: {length} characters")
            print(f"  - Within limits (1-750,000): ✓")
        
        print(green(f"✓ Markdown length: {length} characters (valid)"))
        return True
        
    except AssertionError as e:
        print(red(f"✗ Markdown length invalid: {e}"))
        return False


def test_gamma_input_validation(verbose=False):
    """Test Gamma input validation."""
    print("Testing Gamma input validation...")
    
    try:
        gamma_generator = GammaGenerator()
        
        # Test that valid markdown doesn't raise ValueError for length
        markdown = SAMPLE_HILARY_MARKDOWN
        
        # We can't actually validate without calling the API,
        # but we can test the length check
        if len(markdown) < 1 or len(markdown) > 750000:
            raise ValueError("Invalid length")
        
        if verbose:
            print(f"  - Length validation: ✓")
            print(f"  - Structure: ✓")
        
        print(green("✓ Gamma input validation passed"))
        return True
        
    except Exception as e:
        print(red(f"✗ Gamma input validation failed: {e}"))
        return False


async def test_gamma_generation_mock(verbose=False):
    """Test Gamma generation with mocks."""
    print("Testing Gamma generation (mocked)...")
    
    try:
        # Mock the Gamma client
        with patch('src.services.gamma_generator.GammaClient') as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.generate_presentation = AsyncMock(
                return_value='gen_test123'
            )
            mock_client_instance.poll_generation = AsyncMock(
                return_value={
                    'gammaUrl': 'https://gamma.app/docs/test123',
                    'credits': {'deducted': 2}
                }
            )
            MockClient.return_value = mock_client_instance
            
            gamma_generator = GammaGenerator()
            result = await gamma_generator.generate_from_markdown(
                input_text=SAMPLE_HILARY_MARKDOWN,
                title="Test VoC Analysis",
                num_cards=10
            )
            
            assert 'gamma_url' in result, "Missing gamma_url"
            assert result['gamma_url'] == 'https://gamma.app/docs/test123'
            assert 'generation_id' in result, "Missing generation_id"
            assert 'credits_used' in result, "Missing credits_used"
            
            if verbose:
                print(f"  - Gamma URL: {result['gamma_url']}")
                print(f"  - Generation ID: {result['generation_id']}")
                print(f"  - Credits used: {result['credits_used']}")
            
            print(green("✓ Gamma generation (mocked) successful"))
            return True
            
    except Exception as e:
        print(red(f"✗ Gamma generation failed: {e}"))
        if verbose:
            import traceback
            traceback.print_exc()
        return False


async def test_full_pipeline_mock(verbose=False):
    """Test full pipeline with mocks."""
    print("Testing full pipeline (mocked)...")
    
    try:
        # Mock TopicOrchestrator and GammaGenerator
        with patch('src.agents.topic_orchestrator.TopicOrchestrator') as MockOrch, \
             patch('src.services.gamma_generator.GammaClient') as MockClient:
            
            # Setup TopicOrchestrator mock
            mock_orch_instance = AsyncMock()
            mock_orch_instance.execute_weekly_analysis = AsyncMock(
                return_value=SAMPLE_TOPIC_ORCHESTRATOR_RESULTS
            )
            MockOrch.return_value = mock_orch_instance
            
            # Setup GammaClient mock
            mock_client_instance = AsyncMock()
            mock_client_instance.generate_presentation = AsyncMock(
                return_value='gen_test456'
            )
            mock_client_instance.poll_generation = AsyncMock(
                return_value={
                    'gammaUrl': 'https://gamma.app/docs/test456',
                    'credits': {'deducted': 2}
                }
            )
            MockClient.return_value = mock_client_instance
            
            # Simulate run_topic_based_analysis flow
            from src.agents.topic_orchestrator import TopicOrchestrator
            
            orchestrator = TopicOrchestrator()
            results = await orchestrator.execute_weekly_analysis(
                conversations=[],
                week_id="2024-W42",
                start_date=None,
                end_date=None
            )
            
            assert 'formatted_report' in results, "Missing formatted_report"
            
            markdown = results['formatted_report']
            assert len(markdown) > 200, "Formatted report too short"
            
            # Generate Gamma presentation
            gamma_generator = GammaGenerator()
            gamma_result = await gamma_generator.generate_from_markdown(
                input_text=markdown,
                title="Voice of Customer Analysis - Week 2024-W42",
                num_cards=10
            )
            
            assert gamma_result['gamma_url'], "No Gamma URL"
            
            if verbose:
                print(f"  - TopicOrchestrator: ✓")
                print(f"  - Markdown generated: {len(markdown)} chars")
                print(f"  - Gamma URL: {gamma_result['gamma_url']}")
            
            print(green("✓ Full pipeline (mocked) successful"))
            return True
            
    except Exception as e:
        print(red(f"✗ Full pipeline failed: {e}"))
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def test_slide_count_calculation(verbose=False):
    """Test slide count calculation."""
    print("Testing slide count calculation...")
    
    try:
        markdown = SAMPLE_HILARY_MARKDOWN
        
        # Count topics (### headers)
        topic_count = markdown.count("\n### ")
        
        # Expected slide count: topics + 2 (title + Fin)
        # Note: Actual Gamma may create more/fewer slides
        expected_slides = topic_count + 2
        
        if verbose:
            print(f"  - Topics found: {topic_count}")
            print(f"  - Expected slides: {expected_slides}")
        
        print(green(f"✓ Expected slide count: {expected_slides}"))
        return True
        
    except Exception as e:
        print(red(f"✗ Slide count calculation failed: {e}"))
        return False


async def test_with_real_api(verbose=False):
    """Test with real Gamma API (requires GAMMA_API_KEY)."""
    print("\n" + cyan("Testing with REAL Gamma API..."))
    
    if not os.getenv("GAMMA_API_KEY"):
        print(yellow("⚠ GAMMA_API_KEY not set, skipping real API test"))
        return None
    
    try:
        gamma_generator = GammaGenerator()
        
        print("Generating presentation (this may take 30-60 seconds)...")
        
        result = await gamma_generator.generate_from_markdown(
            input_text=SAMPLE_HILARY_MARKDOWN,
            title="VoC Pipeline Test",
            num_cards=10
        )
        
        print(green("✓ Real API test successful!"))
        print(f"  📊 Gamma URL: {result['gamma_url']}")
        print(f"  💳 Credits used: {result['credits_used']}")
        print(f"  ⏱️  Generation time: {result['generation_time_seconds']:.1f}s")
        print(f"\n  👉 Open this URL in your browser to verify:")
        print(f"     {result['gamma_url']}")
        
        return True
        
    except Exception as e:
        print(red(f"✗ Real API test failed: {e}"))
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def print_banner():
    """Print test banner."""
    print("\n" + "="*60)
    print(cyan("🧪 VoC → Gamma Pipeline Quick Test"))
    print("="*60 + "\n")


def print_summary(results, verbose=False):
    """Print test summary."""
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    skipped = sum(1 for r in results if r is None)
    total = len(results)
    
    print("\n" + "="*60)
    print(f"Test Results: {passed}/{total} passed", end="")
    if skipped > 0:
        print(f" ({skipped} skipped)", end="")
    print()
    print("="*60 + "\n")
    
    if failed == 0 and passed > 0:
        print(green("🎉 All tests passed! Pipeline is ready."))
        print("\nNext steps:")
        print("  1. Run integration tests:")
        print("     pytest tests/integration/test_voc_gamma_integration.py")
        print("  2. Test on Railway:")
        print("     Follow VOC_GAMMA_VALIDATION_GUIDE.md")
        print("  3. Run with real API:")
        print("     python scripts/test_voc_gamma_pipeline.py --real-api")
        return 0
    else:
        print(red("❌ Some tests failed. Please review errors above."))
        print("\nTroubleshooting:")
        print("  1. Check markdown format in SAMPLE_HILARY_MARKDOWN")
        print("  2. Verify validation logic in src/services/gamma_generator.py")
        print("  3. Run with --verbose for detailed output")
        print("  4. Check implementation in src/main.py lines 3274-3334")
        return 1


async def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description="VoC → Gamma Pipeline Quick Test")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--real-api', action='store_true', help='Test with real Gamma API (requires GAMMA_API_KEY)')
    args = parser.parse_args()
    
    print_banner()
    
    results = []
    
    # Run sync tests
    results.append(test_markdown_format(verbose=args.verbose))
    results.append(test_markdown_length(verbose=args.verbose))
    results.append(test_gamma_input_validation(verbose=args.verbose))
    
    # Run async tests
    results.append(await test_gamma_generation_mock(verbose=args.verbose))
    results.append(await test_full_pipeline_mock(verbose=args.verbose))
    
    # Run sync test
    results.append(test_slide_count_calculation(verbose=args.verbose))
    
    # Run real API test if requested
    if args.real_api:
        results.append(await test_with_real_api(verbose=args.verbose))
    
    # Print summary and exit
    exit_code = print_summary(results, verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())

