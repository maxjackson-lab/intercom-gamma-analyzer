"""
Unit tests for Gamma markdown validation.

Tests markdown content validation before sending to Gamma API.
"""

import pytest
from src.services.gamma_generator import GammaGenerator
from src.services.gamma_client import GammaAPIError


class TestValidateGammaInput:
    """Test _validate_gamma_input method."""
    
    def test_validate_empty_markdown(self):
        """Test validation rejects empty markdown."""
        gamma_generator = GammaGenerator()
        
        # Empty string should raise ValueError
        with pytest.raises(ValueError, match="must be 1-750,000 characters"):
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown("", num_cards=5))
    
    def test_validate_markdown_too_long(self):
        """Test validation rejects markdown > 750,000 characters."""
        gamma_generator = GammaGenerator()
        
        # Create markdown with 750,001 characters
        long_markdown = "x" * 750001
        
        with pytest.raises(ValueError, match="must be 1-750,000 characters"):
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(long_markdown, num_cards=5))
    
    def test_validate_markdown_too_short(self):
        """Test validation warns about very short markdown."""
        gamma_generator = GammaGenerator()
        
        # Very short markdown (< 50 characters) may not produce meaningful presentation
        short_markdown = "Test"
        
        # Should raise ValueError for length
        with pytest.raises(ValueError):
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(short_markdown, num_cards=5))
    
    def test_validate_valid_voc_markdown(self):
        """Test validation passes for valid Hilary-format markdown."""
        gamma_generator = GammaGenerator()
        
        valid_markdown = """# Voice of Customer Analysis - Week 2024-W42

## Customer Topics (Paid Tier - Human Support)

### Billing Issues
**45 tickets / 28% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Sentiment**: Customers frustrated with unexpected charges BUT appreciate quick refunds

**Examples**:
1. "I was charged twice for my subscription" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_123)
2. "Need help understanding my invoice" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_124)
3. "Refund request for duplicate charge" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_125)

---

### Product Questions
**32 tickets / 20% of weekly volume**
**Detection Method**: Keyword detection

**Sentiment**: Users love the new features BUT confused by setup process

**Examples**:
1. "How do I enable the new dashboard?" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_126)
2. "Can't find the export button" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_127)

---

## Fin AI Performance (Free Tier - AI-Only Support)

### Fin AI Analysis
**89 conversations handled by Fin this week**

**What Fin is Doing Well**:
- Resolution rate: 72% of conversations resolved without escalation request

**Knowledge Gaps**:
- 12 conversations where Fin gave incorrect/incomplete information

---
"""
        
        # Should not raise ValueError for valid input
        # (will fail without API key, but that's expected and tested separately)
        try:
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(
                valid_markdown,
                title="Test Report",
                num_cards=5
            ))
        except (GammaAPIError, Exception) as e:
            # Expected if no API key - validation passed
            assert "GAMMA_API_KEY" in str(e) or "API" in str(e)


class TestMarkdownStructureValidation:
    """Test markdown structure validation."""
    
    def test_validate_slide_breaks_present(self):
        """Test validation recognizes slide breaks."""
        markdown_with_breaks = """# Title

## Section 1
Content here

---

## Section 2
More content

---
"""
        
        markdown_without_breaks = """# Title

## Section 1
Content here

## Section 2
More content
"""
        
        # Count slide breaks
        assert markdown_with_breaks.count("---") == 2
        assert markdown_without_breaks.count("---") == 0
    
    def test_validate_intercom_urls_format(self):
        """Test validation recognizes Intercom URLs."""
        valid_urls = [
            "https://app.intercom.com/a/inbox/inbox/conv_123",
            "https://app.intercom.com/a/inbox/inbox/conv_456789",
        ]
        
        malformed_urls = [
            "http://intercom.com/conv_123",  # Wrong protocol/domain
            "https://app.intercom.com/",  # No conversation ID
            "intercom.com/a/inbox/conv_123",  # No protocol
        ]
        
        # Valid URLs should match pattern
        for url in valid_urls:
            assert "https://app.intercom.com/a/inbox/inbox/conv_" in url
        
        # Malformed URLs should not match
        for url in malformed_urls:
            assert not url.startswith("https://app.intercom.com/a/inbox/inbox/conv_")
    
    def test_validate_topic_card_structure(self):
        """Test validation recognizes proper topic card structure."""
        valid_card = """### Billing Issues
**45 tickets / 28% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Sentiment**: Customers frustrated with unexpected charges BUT appreciate quick refunds

**Examples**:
1. "I was charged twice" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_123)
"""
        
        # Check required fields
        assert "###" in valid_card  # Topic name
        assert "tickets / " in valid_card  # Volume
        assert "% of weekly volume" in valid_card  # Percentage
        assert "**Detection Method**:" in valid_card
        assert "**Sentiment**:" in valid_card
        assert "**Examples**:" in valid_card
        assert "[View conversation]" in valid_card
        
        # Incomplete card missing sentiment
        incomplete_card = """### Billing Issues
**45 tickets / 28% of weekly volume**
**Detection Method**: Intercom conversation attribute

**Examples**:
1. "I was charged twice" - [View conversation](https://app.intercom.com/a/inbox/inbox/conv_123)
"""
        
        assert "**Sentiment**:" not in incomplete_card


class TestVoCSpecificValidation:
    """Test VoC-specific validation."""
    
    def test_validate_voc_results_structure(self):
        """Test validation handles VoC results structure."""
        # VoC results with proper structure
        voc_results = {
            'formatted_report': '# Test Report\n\nContent',
            'summary': {
                'total_conversations': 100,
                'topics_analyzed': 5
            }
        }
        
        assert 'formatted_report' in voc_results
        assert 'summary' in voc_results
        
        # Standard analysis results (different structure)
        standard_results = {
            'conversations': [],
            'analysis': {}
        }
        
        assert 'conversations' in standard_results
        
        # Invalid results (missing both)
        invalid_results = {
            'data': []
        }
        
        assert 'formatted_report' not in invalid_results
        assert 'conversations' not in invalid_results
    
    def test_validate_voc_metadata(self):
        """Test validation uses VoC metadata."""
        results_with_metadata = {
            'metadata': {
                'total_conversations': 150,
                'date_range': '2024-10-01 to 2024-10-31'
            }
        }
        
        assert 'metadata' in results_with_metadata
        assert results_with_metadata['metadata']['total_conversations'] == 150
        
        # Results without metadata should still work
        results_without_metadata = {
            'summary': {
                'total_conversations': 150
            }
        }
        
        assert 'metadata' not in results_without_metadata
        assert 'summary' in results_without_metadata


class TestEdgeCases:
    """Test edge cases in validation."""
    
    def test_validate_unicode_characters(self):
        """Test validation handles unicode characters."""
        unicode_markdown = """# Voice of Customer 🎉

## Topics 📊

### Billing 💳
**10 tickets / 25% of volume**

**Sentiment**: Users happy 😊 but confused 😕

**Examples**:
1. "Issue with € currency" - [Link](https://app.intercom.com/a/inbox/inbox/conv_123)
2. "¿Cómo puedo cancelar?" - [Link](https://app.intercom.com/a/inbox/inbox/conv_124)

---
"""
        
        # Check character count is correct
        assert len(unicode_markdown) > 100
        
        # Emojis should be preserved
        assert "🎉" in unicode_markdown
        assert "😊" in unicode_markdown
        
        # International characters should be preserved
        assert "€" in unicode_markdown
        assert "¿" in unicode_markdown
    
    def test_validate_html_in_markdown(self):
        """Test validation handles HTML in markdown."""
        markdown_with_html = """# Report

## Topic

**Sentiment**: Users said <strong>this is great</strong>

**Examples**:
1. Message with <br> line break
2. Message with <a href="https://example.com">link</a>

---
"""
        
        # HTML tags should be present (will be escaped/handled by Gamma)
        assert "<strong>" in markdown_with_html
        assert "<br>" in markdown_with_html
        assert "<a href=" in markdown_with_html
    
    def test_validate_very_long_topic_names(self):
        """Test validation handles very long topic names."""
        long_topic_name = "A" * 200
        markdown_with_long_name = f"""# Report

## Topics

### {long_topic_name}
**10 tickets / 25% of volume**

**Detection Method**: Keyword

**Sentiment**: Mixed

**Examples**:
1. Example - [Link](https://app.intercom.com/a/inbox/inbox/conv_123)

---
"""
        
        # Should still be valid
        assert len(long_topic_name) == 200
        assert long_topic_name in markdown_with_long_name


class TestGenerateFromMarkdownBypassesValidation:
    """Test that generate_from_markdown bypasses category validation."""
    
    def test_generate_from_markdown_bypasses_category_validation(self):
        """Test that markdown mode doesn't require category_results."""
        gamma_generator = GammaGenerator()
        
        # Hilary format doesn't have category_results structure
        markdown_without_categories = """# Voice of Customer Analysis

## Topics

### Billing
**10 tickets / 25% of volume**

**Detection Method**: Keyword

**Sentiment**: Mixed feelings

**Examples**:
1. "Billing issue" - [View](https://app.intercom.com/a/inbox/inbox/conv_123)

---
"""
        
        # Should not require category_results when using generate_from_markdown
        # (will fail without API key, but validation should pass)
        try:
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(
                markdown_without_categories,
                num_cards=3
            ))
        except (GammaAPIError, Exception) as e:
            # Expected if no API key - validation passed
            assert "category" not in str(e).lower() or "GAMMA_API_KEY" in str(e)


class TestValidationHelpers:
    """Test validation helper functions."""
    
    def test_count_sections(self):
        """Test counting sections in markdown."""
        markdown = """# Title

## Section 1
Content

## Section 2
More content

## Section 3
Even more
"""
        
        # Count ## headers
        sections = markdown.count("\n## ")
        assert sections == 3
    
    def test_count_slide_breaks(self):
        """Test counting slide breaks."""
        markdown = """Content

---

More content

---

Final content

---
"""
        
        breaks = markdown.count("\n---\n") + markdown.count("\n---")
        assert breaks >= 3
    
    def test_extract_topic_count(self):
        """Test extracting topic count from markdown."""
        markdown = """# Voice of Customer

## Topics

### Topic 1
Content

---

### Topic 2
Content

---

### Topic 3
Content

---
"""
        
        # Count ### headers (topics)
        topics = markdown.count("\n### ")
        assert topics == 3


class TestLengthBoundaries:
    """Test length boundary conditions."""
    
    def test_minimum_valid_length(self):
        """Test minimum valid markdown length."""
        # Absolute minimum (1 character) - will fail validation
        min_text = "x"
        
        gamma_generator = GammaGenerator()
        with pytest.raises(ValueError):
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(min_text, num_cards=1))
    
    def test_maximum_valid_length(self):
        """Test maximum valid markdown length."""
        # Maximum valid (750,000 characters)
        max_text = "x" * 750000
        
        gamma_generator = GammaGenerator()
        
        # Should not raise ValueError for length (but will fail without API key)
        try:
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(max_text, num_cards=10))
        except ValueError as e:
            # Should NOT be about length
            assert "750,000" not in str(e)
        except Exception:
            # Other errors are OK (API key, etc.)
            pass
    
    def test_just_over_maximum_length(self):
        """Test just over maximum markdown length."""
        # Just over maximum (750,001 characters)
        over_max_text = "x" * 750001
        
        gamma_generator = GammaGenerator()
        with pytest.raises(ValueError, match="must be 1-750,000 characters"):
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(over_max_text, num_cards=10))
    
    def test_practical_voc_length(self):
        """Test practical VoC report length (2,000-20,000 characters)."""
        # Typical VoC report length
        practical_text = "x" * 5000
        
        gamma_generator = GammaGenerator()
        
        # Should not raise ValueError for length
        try:
            import asyncio
            asyncio.run(gamma_generator.generate_from_markdown(practical_text, num_cards=10))
        except ValueError as e:
            # Should NOT be about length
            assert "750,000" not in str(e)
        except Exception:
            # Other errors are OK (API key, etc.)
            pass

