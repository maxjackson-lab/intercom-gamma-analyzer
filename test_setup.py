"""
Test script to validate the Intercom Analysis Tool setup.
Run this after setup to ensure everything is working correctly.
"""

import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from intercom_client import IntercomClient, IntercomAPIError
        from text_analyzer import TextAnalyzer
        from trend_analyzer import TrendAnalyzer
        from report_generator import ReportGenerator
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_environment():
    """Test environment variables."""
    print("Testing environment...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
    if not access_token:
        print("❌ INTERCOM_ACCESS_TOKEN not found in .env file")
        print("   Please add your token to the .env file")
        return False
    
    if access_token == 'your_token_here':
        print("❌ Please replace 'your_token_here' with your actual Intercom access token")
        return False
    
    print("✅ Environment variables configured")
    return True

def test_intercom_connection():
    """Test connection to Intercom API."""
    print("Testing Intercom API connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from intercom_client import IntercomClient
        access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
        
        client = IntercomClient(access_token=access_token)
        print("✅ Intercom API connection successful")
        return True
    except Exception as e:
        print(f"❌ Intercom API connection failed: {e}")
        print("   Please check your access token and internet connection")
        return False

def test_text_analyzer():
    """Test text analyzer functionality."""
    print("Testing text analyzer...")
    
    try:
        from text_analyzer import TextAnalyzer
        
        analyzer = TextAnalyzer()
        test_text = "This is a test conversation about browser cache issues and slow loading times."
        
        keywords = analyzer.extract_keywords(test_text)
        if keywords:
            print(f"✅ Text analyzer working - extracted {len(keywords)} keywords")
            print(f"   Sample keywords: {[kw[0] for kw in keywords[:3]]}")
            return True
        else:
            print("❌ Text analyzer failed to extract keywords")
            return False
    except Exception as e:
        print(f"❌ Text analyzer test failed: {e}")
        return False

def test_trend_analyzer():
    """Test trend analyzer functionality."""
    print("Testing trend analyzer...")
    
    try:
        from trend_analyzer import TrendAnalyzer
        
        # Create mock conversation data
        mock_conversations = [
            {
                'id': 'test1',
                'created_at': int(datetime.now().timestamp()),
                'state': 'closed',
                'source': {'type': 'email', 'body': 'Test message about cache issues'},
                'conversation_parts': {'conversation_parts': []}
            },
            {
                'id': 'test2',
                'created_at': int((datetime.now() - timedelta(days=1)).timestamp()),
                'state': 'open',
                'source': {'type': 'chat', 'body': 'Another test about browser problems'},
                'conversation_parts': {'conversation_parts': []}
            }
        ]
        
        # Test pattern analysis
        patterns = ['cache', 'browser']
        pattern_counts = TrendAnalyzer.pattern_analysis(mock_conversations, patterns)
        
        # Test state analysis
        state_breakdown = TrendAnalyzer.conversations_by_state(mock_conversations)
        
        print("✅ Trend analyzer working")
        print(f"   Pattern counts: {pattern_counts}")
        print(f"   State breakdown: {state_breakdown}")
        return True
    except Exception as e:
        print(f"❌ Trend analyzer test failed: {e}")
        return False

def test_report_generator():
    """Test report generator functionality."""
    print("Testing report generator...")
    
    try:
        from report_generator import ReportGenerator
        
        # Create mock analysis results
        mock_results = {
            'total_conversations': 2,
            'unique_keywords': 5,
            'top_keywords': [('test', 2), ('cache', 1), ('browser', 1)],
            'pattern_counts': {'cache': 1, 'browser': 1},
            'state_breakdown': {'closed': 1, 'open': 1}
        }
        
        # Test text report generation
        report_text = ReportGenerator.generate_text_report(mock_results)
        
        if "INTERCOM CONVERSATION TREND ANALYSIS" in report_text:
            print("✅ Report generator working")
            return True
        else:
            print("❌ Report generator failed to create proper report")
            return False
    except Exception as e:
        print(f"❌ Report generator test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Intercom Analysis Tool - Setup Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_environment,
        test_text_analyzer,
        test_trend_analyzer,
        test_report_generator,
        test_intercom_connection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nYou can now run:")
        print("  python main.py --days 7 --max-pages 2  (for testing)")
        print("  python main.py  (for full analysis)")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nCommon solutions:")
        print("1. Run: pip install -r requirements.txt")
        print("2. Check your .env file has a valid INTERCOM_ACCESS_TOKEN")
        print("3. Ensure you have internet connection for API tests")

if __name__ == "__main__":
    main()


