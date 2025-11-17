"""
Test LLM topic normalization (fuzzy matching).

Verifies that the LLM can return topics in different formats
and we correctly normalize them to our taxonomy.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.topic_detection_agent import TopicDetectionAgent


def test_llm_topic_normalization():
    """Test that LLM responses are correctly normalized to valid topics."""
    
    agent = TopicDetectionAgent()
    
    # TEST CASES FROM PRODUCTION LOGS (Nov 17, 2025)
    test_cases = [
        # Case sensitivity
        ("billing", "Billing"),
        ("account", "Account"),
        ("bug", "Bug"),
        ("workspace", "Workspace"),
        
        # Specific subcategories → Parent category
        ("Refund Request", "Billing"),
        ("Account Management", "Account"),
        ("Download Issues", "Product Question"),
        ("Template Upload and Customization", "Product Question"),
        ("Login Method Change", "Account"),
        ("Technical Issue", "Bug"),
        ("Discount Request", "Promotions"),
        ("Image Editing and Uploading", "Product Question"),
        ("App Usage and Access Issues", "Account"),
        ("Website Text Size Adjustment", "Product Question"),
        
        # Exact matches (should pass through)
        ("Billing", "Billing"),
        ("Account", "Account"),
        ("Product Question", "Product Question"),
        
        # Unknown
        ("Unknown", "Unknown"),
        ("Unknown/unresponsive", None),  # Might not be in topics
        
        # Invalid (should return None)
        ("Completely Invalid Topic Name", None),
        ("RandomGarbage", None),
    ]
    
    for llm_response, expected_topic in test_cases:
        result = agent._normalize_llm_topic(llm_response)
        
        if expected_topic is None:
            # For invalid topics or Unknown/unresponsive
            if llm_response == "Unknown/unresponsive":
                # This is a special case - might be valid
                assert result in [None, "Unknown"], f"Expected None or Unknown for '{llm_response}', got '{result}'"
            else:
                assert result is None, f"Expected None for invalid topic '{llm_response}', got '{result}'"
        else:
            assert result == expected_topic, f"Failed: '{llm_response}' → expected '{expected_topic}', got '{result}'"
    
    print("\n✅ ALL NORMALIZATION TESTS PASSED!")
    print("\nTest cases validated:")
    print("  ✅ Case-insensitive matching (billing → Billing)")
    print("  ✅ Fuzzy matching (Refund Request → Billing)")
    print("  ✅ Semantic mapping (Download Issues → Product Question)")
    print("  ✅ Invalid topic rejection (RandomGarbage → None)")


if __name__ == "__main__":
    test_llm_topic_normalization()

