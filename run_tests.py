#!/usr/bin/env python3
"""
Test runner script for the Intercom Analysis Tool.

This script runs all unit tests and provides comprehensive test coverage reporting.
"""

import sys
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any
import json


def run_command(command: List[str], cwd: str = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(command)}")
        print(f"Return code: {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise


def check_dependencies() -> bool:
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'pytest',
        'pytest-asyncio',
        'pytest-mock',
        'pytest-cov',
        'coverage'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All dependencies are installed")
    return True


def run_unit_tests() -> bool:
    """Run all unit tests."""
    print("\n🧪 Running unit tests...")
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Run pytest with coverage
    command = [
        'python', '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--cov=src',
        '--cov-report=term-missing',
        '--cov-report=html:htmlcov',
        '--cov-report=json:coverage.json',
        '--junitxml=test-results.xml'
    ]
    
    try:
        result = run_command(command, cwd=str(project_root))
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Some tests failed!")
        return False


def run_specific_test_files(test_files: List[str]) -> bool:
    """Run specific test files."""
    print(f"\n🧪 Running specific test files: {', '.join(test_files)}")
    
    project_root = Path(__file__).parent
    
    command = [
        'python', '-m', 'pytest',
        *test_files,
        '-v',
        '--tb=short',
        '--cov=src',
        '--cov-report=term-missing'
    ]
    
    try:
        result = run_command(command, cwd=str(project_root))
        print("✅ All specified tests passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Some specified tests failed!")
        return False


def run_linting() -> bool:
    """Run code linting."""
    print("\n🔍 Running code linting...")
    
    project_root = Path(__file__).parent
    
    # Run black for code formatting
    print("Running black...")
    try:
        run_command(['python', '-m', 'black', '--check', 'src/', 'tests/'], cwd=str(project_root))
        print("✅ Black formatting is correct")
    except subprocess.CalledProcessError:
        print("❌ Black formatting issues found")
        return False
    
    # Run isort for import sorting
    print("Running isort...")
    try:
        run_command(['python', '-m', 'isort', '--check-only', 'src/', 'tests/'], cwd=str(project_root))
        print("✅ Import sorting is correct")
    except subprocess.CalledProcessError:
        print("❌ Import sorting issues found")
        return False
    
    return True


def generate_test_report() -> Dict[str, Any]:
    """Generate a comprehensive test report."""
    print("\n📊 Generating test report...")
    
    project_root = Path(__file__).parent
    coverage_file = project_root / 'coverage.json'
    
    if not coverage_file.exists():
        print("❌ Coverage file not found. Run tests first.")
        return {}
    
    try:
        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)
        
        total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
        
        report = {
            'total_coverage': total_coverage,
            'coverage_data': coverage_data,
            'test_files': list((project_root / 'tests').glob('test_*.py')),
            'source_files': list((project_root / 'src').rglob('*.py'))
        }
        
        print(f"📈 Total test coverage: {total_coverage:.2f}%")
        
        return report
        
    except Exception as e:
        print(f"❌ Error generating test report: {e}")
        return {}


def main():
    """Main test runner function."""
    print("🚀 Intercom Analysis Tool - Test Runner")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('src').exists() or not Path('tests').exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--lint-only':
            if run_linting():
                print("\n✅ All linting checks passed!")
                sys.exit(0)
            else:
                print("\n❌ Linting checks failed!")
                sys.exit(1)
        elif sys.argv[1] == '--test-files':
            if len(sys.argv) < 3:
                print("❌ Please specify test files to run")
                sys.exit(1)
            test_files = sys.argv[2:]
            if run_specific_test_files(test_files):
                print("\n✅ All specified tests passed!")
                sys.exit(0)
            else:
                print("\n❌ Some specified tests failed!")
                sys.exit(1)
        elif sys.argv[1] == '--help':
            print("Usage: python run_tests.py [options]")
            print("Options:")
            print("  --lint-only     Run only linting checks")
            print("  --test-files    Run specific test files")
            print("  --help          Show this help message")
            print("  (no options)    Run all tests and linting")
            sys.exit(0)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Run linting
    if not run_linting():
        print("\n❌ Linting checks failed!")
        sys.exit(1)
    
    # Run unit tests
    if not run_unit_tests():
        print("\n❌ Unit tests failed!")
        sys.exit(1)
    
    # Generate test report
    report = generate_test_report()
    
    print("\n🎉 All tests and checks passed!")
    print("=" * 50)
    
    if report:
        print(f"📊 Test Coverage: {report['total_coverage']:.2f}%")
        print(f"📁 Test Files: {len(report['test_files'])}")
        print(f"📁 Source Files: {len(report['source_files'])}")
    
    print("\n📋 Test Results:")
    print("  - Unit tests: ✅ PASSED")
    print("  - Code linting: ✅ PASSED")
    print("  - Test coverage: ✅ GENERATED")
    
    print("\n📁 Generated Files:")
    print("  - htmlcov/ (HTML coverage report)")
    print("  - coverage.json (JSON coverage data)")
    print("  - test-results.xml (JUnit test results)")
    
    print("\n🔗 View HTML coverage report: open htmlcov/index.html")


if __name__ == '__main__':
    main()