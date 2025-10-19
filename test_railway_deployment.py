#!/usr/bin/env python3
"""
Test script to verify Railway deployment configuration.
"""

import os
import sys
from pathlib import Path

def test_pythonpath():
    """Test PYTHONPATH configuration."""
    print("🔧 Testing PYTHONPATH configuration...")
    pythonpath = os.environ.get('PYTHONPATH', 'Not set')
    print(f"   PYTHONPATH: {pythonpath}")
    
    # Check if src module can be imported
    try:
        import src
        print("   ✅ src module imported successfully")
        return True
    except ImportError as e:
        print(f"   ❌ Failed to import src module: {e}")
        return False

def test_dependencies():
    """Test critical dependencies."""
    print("\n🔧 Testing critical dependencies...")
    
    dependencies = [
        'fastapi',
        'uvicorn',
        'pandas',
        'numpy',
        'openai',
        'requests'
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep}")
            missing.append(dep)
    
    if missing:
        print(f"   Missing dependencies: {missing}")
        return False
    return True

def test_chat_dependencies():
    """Test chat interface dependencies."""
    print("\n🔧 Testing chat interface dependencies...")
    
    chat_deps = [
        'sentence_transformers',
        'faiss'
    ]
    
    missing = []
    for dep in chat_deps:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep}")
            missing.append(dep)
    
    if missing:
        print(f"   Missing chat dependencies: {missing}")
        print("   ⚠️  Chat interface will have limited functionality")
        return False
    return True

def test_environment():
    """Test environment variables."""
    print("\n🔧 Testing environment variables...")
    
    required_vars = [
        'INTERCOM_ACCESS_TOKEN',
        'OPENAI_API_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f"   ✅ {var}")
        else:
            print(f"   ❌ {var}")
            missing.append(var)
    
    if missing:
        print(f"   Missing environment variables: {missing}")
        print("   ⚠️  Some features may not work without these variables")
        return False
    return True

def test_file_structure():
    """Test file structure."""
    print("\n🔧 Testing file structure...")
    
    required_files = [
        'src/main.py',
        'src/config/settings.py',
        'deploy/railway_web.py',
        'requirements-railway.txt',
        'Dockerfile'
    ]
    
    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
            missing.append(file_path)
    
    if missing:
        print(f"   Missing files: {missing}")
        return False
    return True

def main():
    """Run all tests."""
    print("🚀 Testing Railway deployment configuration...\n")
    
    tests = [
        test_pythonpath,
        test_dependencies,
        test_chat_dependencies,
        test_environment,
        test_file_structure
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Test failed with error: {e}")
            results.append(False)
    
    print(f"\n📊 Test Results:")
    print(f"   Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("   ✅ All tests passed! Railway deployment should work.")
        return 0
    else:
        print("   ❌ Some tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())