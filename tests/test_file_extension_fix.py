#!/usr/bin/env python3
"""
Test to verify the file extension fix for question loading.
Tests that the extension removal logic works correctly for both .json and .toml files.
"""

import re

def test_extension_removal():
    """Test the JavaScript regex logic in Python equivalent"""
    
    # JavaScript regex: rawQId.replace(/\.(json|toml)$/, '')
    def remove_extension(filename):
        return re.sub(r'\.(json|toml)$', '', filename)
    
    # Test cases
    test_cases = [
        ("q4.toml", "q4"),      # Original problem case
        ("q4.json", "q4"),      # Legacy case
        ("q4", "q4"),           # No extension case
        ("q4.txt", "q4.txt"),   # Other extension (should not be removed)
        ("q4.toml.backup", "q4.toml.backup"),  # Complex extension
        ("test.q4.toml", "test.q4"),  # Dot in name
    ]
    
    results = []
    for input_name, expected in test_cases:
        actual = remove_extension(input_name)
        success = actual == expected
        results.append({
            'input': input_name,
            'expected': expected,
            'actual': actual,
            'success': success
        })
        print(f"{'✅' if success else '❌'} {input_name} → {actual} (expected: {expected})")
    
    # Summary
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"\nTest Results: {passed}/{total} passed")
    
    # Verify the specific fix
    problem_case = "q4.toml"
    fixed_result = remove_extension(problem_case)
    print(f"\n🔧 Fix Verification:")
    print(f"Input from config: {problem_case}")
    print(f"After processing: {fixed_result}")
    print(f"Final URL would be: /questions/{fixed_result}.toml")
    print(f"Expected URL: /questions/q4.toml")
    
    return passed == total

if __name__ == "__main__":
    success = test_extension_removal()
    exit(0 if success else 1)