#!/usr/bin/env python3
"""
Test for SG01 "Other" text field handling bug fix.

This test verifies that when a user selects "Other" and fills in a text field,
the AI evaluation receives the actual text content instead of just "Other".

Bug Description:
- When user selects "Other" option and fills text field for SG01 question
- AI was receiving only "Other" instead of "Other: [user text content]"
- This led to generic scoring instead of evaluating actual user input

Fix:
- Modified get_readable_answer() function to handle other_text_id fields
- Function now combines "Other" label with associated text field content
"""

import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.backend.py_simple_evaluate import get_readable_answer, find_question_by_id, load_questions_data

def test_other_text_field_handling():
    """
    Test that get_readable_answer() properly handles "Other" option with text field
    """
    print("🧪 Testing 'Other' text field handling...")
    
    # Mock SG01 question structure (simplified)
    sg01_question = {
        'id': 'SG01',
        'text': 'Why are you selling now?',
        'question_type': 'choice-multi',
        'with_other': True,
        'other_text_id': 'SG01_OTHER',
        'options': [
            {'code': 'retirement_move', 'label': 'Retirement or move'},
            {'code': 'declining_sales', 'label': 'Declining sales'},
            {'code': 'other', 'label': 'Other'}
        ]
    }
    
    # Test Case 1: User selects "Other" and fills text field
    print("📝 Test Case 1: 'Other' with text content")
    
    all_answers = {
        'SG01': ['other'],  # User selected "Other" option
        'SG01_OTHER': 'Planning to start a new business venture in different industry'  # User's text input
    }
    
    # Test single selection with "other"
    readable_answer = get_readable_answer(sg01_question, 'other', all_answers)
    expected = "Other: Planning to start a new business venture in different industry"
    
    print(f"   Input: 'other' with text field = '{all_answers['SG01_OTHER']}'")
    print(f"   Output: '{readable_answer}'")
    print(f"   Expected: '{expected}'")
    
    assert readable_answer == expected, f"Expected '{expected}', got '{readable_answer}'"
    print("   ✅ PASS: Single 'Other' option with text field")
    
    # Test Case 2: User selects multiple options including "Other"
    print("\n📝 Test Case 2: Multiple selection including 'Other'")
    
    # Test multi-selection with "other"
    readable_answer = get_readable_answer(sg01_question, ['declining_sales', 'other'], all_answers)
    expected = "Declining sales, Other: Planning to start a new business venture in different industry"
    
    print(f"   Input: ['declining_sales', 'other'] with text field = '{all_answers['SG01_OTHER']}'")
    print(f"   Output: '{readable_answer}'")
    print(f"   Expected: '{expected}'")
    
    assert readable_answer == expected, f"Expected '{expected}', got '{readable_answer}'"
    print("   ✅ PASS: Multi-selection with 'Other' option and text field")
    
    # Test Case 3: User selects "Other" but doesn't fill text field
    print("\n📝 Test Case 3: 'Other' without text content")
    
    all_answers_empty = {
        'SG01': ['other'],
        'SG01_OTHER': ''  # Empty text field
    }
    
    readable_answer = get_readable_answer(sg01_question, 'other', all_answers_empty)
    expected = "Other"  # Should fall back to just "Other"
    
    print(f"   Input: 'other' with empty text field")
    print(f"   Output: '{readable_answer}'")
    print(f"   Expected: '{expected}'")
    
    assert readable_answer == expected, f"Expected '{expected}', got '{readable_answer}'"
    print("   ✅ PASS: 'Other' option with empty text field")
    
    # Test Case 4: Regular option (not "Other")
    print("\n📝 Test Case 4: Regular option selection")
    
    readable_answer = get_readable_answer(sg01_question, 'declining_sales', all_answers)
    expected = "Declining sales"
    
    print(f"   Input: 'declining_sales'")
    print(f"   Output: '{readable_answer}'")
    print(f"   Expected: '{expected}'")
    
    assert readable_answer == expected, f"Expected '{expected}', got '{readable_answer}'"
    print("   ✅ PASS: Regular option selection")
    
    print("\n🎉 All tests passed! 'Other' text field handling is working correctly.")
    return True

def test_ai_evaluation_integration():
    """
    Test that the fix integrates properly with AI evaluation logic
    """
    print("\n🤖 Testing AI evaluation integration...")
    
    # This is a simplified integration test
    # In real scenario, we would test the full evaluation pipeline
    
    print("📋 Simulating evaluation payload construction...")
    
    # Mock scenario: User answers SG01 with "Other" and provides text
    mock_question = {
        'id': 'SG01',
        'text': 'Why are you selling now?',
        'question_type': 'choice-multi',
        'other_text_id': 'SG01_OTHER',
        'options': [
            {'code': 'other', 'label': 'Other'}
        ]
    }
    
    mock_all_answers = {
        'SG01': ['other'],
        'SG01_OTHER': 'Received an unexpected offer that is too good to refuse'
    }
    
    # Test the answer processing
    answer_for_ai = get_readable_answer(mock_question, mock_all_answers.get('SG01'), mock_all_answers)
    
    print(f"   Question: {mock_question['text']}")
    print(f"   User's raw answer: {mock_all_answers['SG01']}")
    print(f"   User's text input: {mock_all_answers['SG01_OTHER']}")
    print(f"   Answer sent to AI: '{answer_for_ai}'")
    
    # Verify AI gets the full context
    assert "Received an unexpected offer that is too good to refuse" in answer_for_ai
    assert answer_for_ai.startswith("Other:")
    
    print("   ✅ PASS: AI evaluation receives full context from 'Other' text field")
    
    print("\n🔗 Integration test completed successfully!")
    return True

if __name__ == "__main__":
    print("🚀 Starting 'Other' text field bug fix validation...\n")
    
    try:
        # Run tests
        test_other_text_field_handling()
        test_ai_evaluation_integration()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("✅ Bug fix verified: 'Other' text fields are now properly handled")
        print("✅ AI evaluations will receive full user input instead of generic 'Other'")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\n" + "="*60)
        print("❌ Bug fix validation failed")
        print("❌ Check the implementation and try again")
        print("="*60)
        sys.exit(1)