#!/usr/bin/env python3
"""
Simple test runner for SG01 evaluation bug test.

Usage:
    python tests/run_sg01_test.py

Requirements:
    - Application running on http://192.168.1.50:3000
    - Playwright installed: pip install playwright && playwright install
"""

import sys
from pathlib import Path
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_playwright():
    """Check if Playwright is installed."""
    try:
        import playwright
        print("✅ Playwright is installed")
        return True
    except ImportError:
        print("❌ Playwright not found")
        print("Install with: pip install playwright")
        print("Then run: playwright install")
        return False

def check_server():
    """Check if application server is running."""
    try:
        import requests
        response = requests.get("http://192.168.1.50:3000", timeout=5)
        print("✅ Application server is accessible")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please ensure application is running on http://192.168.1.50:3000")
        return False

def main():
    """Main runner function."""
    print("🧪 SG01 Evaluation Bug Test Runner")
    print("="*50)
    
    # Check prerequisites
    if not check_playwright():
        return 1
        
    if not check_server():
        return 1
    
    print("\n🚀 Starting test...")
    
    # Run the test
    try:
        from test_sg01_evaluation_bug import SG01EvaluationBugTest
        test = SG01EvaluationBugTest()
        success = test.run_test()
        return 0 if success else 1
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())