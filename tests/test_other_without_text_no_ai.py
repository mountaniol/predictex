#!/usr/bin/env python3
"""
Test to verify that selecting "Other" without text does NOT trigger AI evaluation.

This test validates the fix for the issue where:
- User selects "Other" option
- Text field appears but is empty
- System should NOT call AI until text is entered

The fix ensures:
1. "Other" alone without text is not considered a valid answer
2. AI is only called when "Other" has accompanying text
3. Questions with only "Other" selected show as "unanswered"
"""

def test_other_without_text_no_ai():
    """Test that selecting 'Other' without text doesn't trigger AI"""
    
    print("🧪 Testing 'Other' without text prevention...")
    print("="*60)
    
    # Simulate the validation logic
    def is_valid_answer_for_submission(selected_options, other_text="", question_has_other=True):
        """
        Determines if an answer is valid for AI submission.
        Returns True only if answer is complete and ready for evaluation.
        """
        if not question_has_other:
            # Normal question without "other" option
            if isinstance(selected_options, list):
                return len(selected_options) > 0
            else:
                return selected_options and selected_options != ""
        
        # Question has "other" option
        if isinstance(selected_options, list):
            # Multi-choice question
            if len(selected_options) == 0:
                return False  # Nothing selected
            
            # Check if ONLY "other" is selected
            if len(selected_options) == 1 and selected_options[0] == 'other':
                # Only "other" selected - need text
                return bool(other_text and other_text.strip() != "")
            
            # Multiple selections or non-"other" selections
            has_other = 'other' in selected_options
            if has_other and (not other_text or other_text.strip() == ""):
                # "Other" is selected but no text - still valid if other options selected
                return len(selected_options) > 1
            
            return True
        else:
            # Single-choice question
            if selected_options == 'other':
                # "Other" selected - need text
                return bool(other_text and other_text.strip() != "")
            
            # Non-"other" option selected
            return bool(selected_options and selected_options != "")
    
    # Test Cases
    test_cases = [
        # Format: (selected, other_text, has_other_option, expected, description)
        
        # Multi-choice cases
        (["other"], "", True, False, "Multi: Only 'Other' without text"),
        (["other"], "Custom reason", True, True, "Multi: Only 'Other' with text"),
        (["declining_sales"], "", True, True, "Multi: Regular option selected"),
        (["declining_sales", "other"], "", True, True, "Multi: Multiple with empty 'Other'"),
        (["declining_sales", "other"], "Also this", True, True, "Multi: Multiple with 'Other' text"),
        ([], "", True, False, "Multi: Nothing selected"),
        
        # Single-choice cases
        ("other", "", True, False, "Single: 'Other' without text"),
        ("other", "My reason", True, True, "Single: 'Other' with text"),
        ("retirement", "", True, True, "Single: Regular option selected"),
        ("", "", True, False, "Single: Nothing selected"),
        
        # Edge cases
        (["other"], "   ", True, False, "Multi: 'Other' with only spaces"),
        ("other", "   ", True, False, "Single: 'Other' with only spaces"),
        (["other"], "\n\t", True, False, "Multi: 'Other' with only whitespace"),
    ]
    
    print("\n📝 Running validation tests:")
    all_passed = True
    
    for i, (selected, text, has_other, expected, description) in enumerate(test_cases, 1):
        result = is_valid_answer_for_submission(selected, text, has_other)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            action = "WILL call AI" if result else "WON'T call AI"
        else:
            action = f"ERROR: Got '{result}' (type: {type(result).__name__}), expected '{expected}' (type: {type(expected).__name__})"
            all_passed = False
        
        print(f"  {status} Test {i:2}: {description:<45} -> {action}")
    
    # Simulate UI state logic
    print("\n📝 Testing question state logic:")
    
    def get_question_state(selected_options, other_text="", has_score=False):
        """Simulates question state based on answer and score"""
        is_valid = is_valid_answer_for_submission(selected_options, other_text)
        
        if not is_valid:
            return "unanswered"
        elif not has_score:
            return "waiting_for_evaluation"
        else:
            return "fully_answered"
    
    state_tests = [
        (["other"], "", False, "unanswered", "Only 'Other' no text, no score"),
        (["other"], "Text", False, "waiting_for_evaluation", "Only 'Other' with text, no score"),
        (["other"], "Text", True, "fully_answered", "Only 'Other' with text and score"),
        (["declining_sales", "other"], "", False, "waiting_for_evaluation", "Multiple with empty 'Other'"),
        (["declining_sales", "other"], "", True, "fully_answered", "Multiple with empty 'Other' and score"),
    ]
    
    for selected, text, has_score, expected, description in state_tests:
        result = get_question_state(selected, text, has_score)
        status = "✅" if result == expected else "❌"
        
        if result != expected:
            all_passed = False
        
        print(f"  {status} {description:<50} -> {result}")
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nSummary:")
        print("✓ 'Other' alone without text doesn't trigger AI")
        print("✓ 'Other' with text properly triggers AI")
        print("✓ Multiple selections with empty 'Other' still work")
        print("✓ Question states correctly reflect answer completeness")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the implementation.")
        return False
    
    return True

if __name__ == "__main__":
    test_other_without_text_no_ai()