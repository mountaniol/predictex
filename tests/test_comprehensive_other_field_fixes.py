#!/usr/bin/env python3
"""
Comprehensive test for "Other" text field fixes in QnA Evaluator frontend.

This test validates:
1. No duplicate text fields appear in SG01 question
2. Proper state reset when all options are unchecked
3. Score and explanation clearing when answers become empty
4. Proper re-evaluation when options are selected again

Author: Predictex AI
Date: 2025-01-13
"""

import asyncio
import sys
import os
import json
from playwright.async_api import async_playwright

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

class ComprehensiveOtherFieldTest:
    def __init__(self):
        self.browser = None
        self.page = None
        self.base_url = "http://localhost:3000"
        
    async def setup(self):
        """Initialize browser and navigate to the application"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True, slow_mo=100)
        self.page = await self.browser.new_page()
        
        # Navigate to the application
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state('networkidle')
        print("✓ Application loaded successfully")
        
    async def teardown(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
            print("✓ Browser closed")
            
    async def test_no_duplicate_text_fields(self):
        """Test that SG01 question has no duplicate text fields"""
        print("\n--- Testing No Duplicate Text Fields in SG01 ---")
        
        # Find all sections on the page to debug what we're getting
        all_sections = await self.page.locator('div:has-text("Why are you selling now?")').all()
        print(f"Found {len(all_sections)} sections with 'Why are you selling now?' text")
        
        # Use a more specific selector for the SG01 question
        # Look for the parent container that contains both the text and checkboxes
        sg01_container = self.page.locator('div').filter(has_text="Why are you selling now?").filter(has=self.page.locator('input[type="checkbox"]')).first
        
        try:
            await sg01_container.wait_for(timeout=5000)
            print("✓ Found SG01 question container")
        except:
            print("✗ Could not find SG01 question container")
            return False
        
        # Count text input fields in this specific container
        text_inputs = await sg01_container.locator('input[type="text"]').all()
        print(f"Found {len(text_inputs)} text input fields in SG01 container")
        
        # Debug: Print information about each text input to understand what we found
        for i, input_field in enumerate(text_inputs):
            placeholder = await input_field.get_attribute('placeholder') or "None"
            name = await input_field.get_attribute('name') or "None"
            id_attr = await input_field.get_attribute('id') or "None"
            print(f"  Input {i+1}: id='{id_attr}', placeholder='{placeholder}', name='{name}'")
        
        # Check if we have the expected SG01_OTHER field
        sg01_other_inputs = [input_field for input_field in text_inputs
                            if 'SG01_OTHER' in (await input_field.get_attribute('id') or '')]
        
        if len(sg01_other_inputs) == 1:
            print("✓ Found exactly 1 SG01_OTHER text field as expected")
            return True
        elif len(sg01_other_inputs) == 0:
            print("✗ No SG01_OTHER text field found")
            return False
        else:
            print(f"✗ DUPLICATE SG01_OTHER FIELDS: Found {len(sg01_other_inputs)} SG01_OTHER fields")
            return False
            
    async def test_empty_answer_state_reset(self):
        """Test that state resets properly when all options are unchecked"""
        print("\n--- Testing Empty Answer State Reset ---")
        
        # Find the SG01 question container more precisely
        sg01_section = self.page.locator('div').filter(has_text="Why are you selling now?").filter(has=self.page.locator('input[type="checkbox"]')).first
        await sg01_section.wait_for()
        
        # Step 1: Select an option to trigger evaluation
        print("Step 1: Selecting 'Declining sales' option...")
        declining_sales_checkbox = sg01_section.locator('input[type="checkbox"][value="declining_sales"]').first
        await declining_sales_checkbox.click()
        
        # Wait for evaluation to complete
        print("Waiting for AI evaluation...")
        await self.page.wait_for_timeout(3000)
        
        # Check if score appears
        score_element = sg01_section.locator('div:has-text("Score:")').first
        try:
            await score_element.wait_for(timeout=10000)
            score_text = await score_element.text_content()
            print(f"✓ Score appeared: {score_text}")
        except:
            print("✗ Score did not appear after selecting option")
            return False
            
        # Step 2: Uncheck all options
        print("Step 2: Unchecking all options...")
        await declining_sales_checkbox.click()
        
        # Wait a moment for state changes
        await self.page.wait_for_timeout(1000)
        
        # Step 3: Verify score and explanation are hidden/cleared
        print("Step 3: Verifying score and explanation are cleared...")
        
        # Check if score element is hidden or removed
        score_elements = await sg01_section.locator('div:has-text("Score:")').all()
        if len(score_elements) == 0:
            print("✓ Score element removed completely")
            score_cleared = True
        else:
            # Check if score element is still visible
            is_visible = await score_elements[0].is_visible()
            if not is_visible:
                print("✓ Score element hidden")
                score_cleared = True
            else:
                print("✗ Score element still visible after unchecking all options")
                score_cleared = False
                
        # Check if explanation button is hidden
        explain_buttons = await sg01_section.locator('button:has-text("Explain")').all()
        if len(explain_buttons) == 0:
            print("✓ Explanation button removed completely")
            explanation_cleared = True
        else:
            is_visible = await explain_buttons[0].is_visible()
            if not is_visible:
                print("✓ Explanation button hidden")
                explanation_cleared = True
            else:
                print("✗ Explanation button still visible after unchecking all options")
                explanation_cleared = False
                
        return score_cleared and explanation_cleared
        
    async def test_re_evaluation_after_reselection(self):
        """Test that evaluation works properly after reselecting options"""
        print("\n--- Testing Re-evaluation After Reselection ---")
        
        # Find the SG01 question container more precisely
        sg01_section = self.page.locator('div').filter(has_text="Why are you selling now?").filter(has=self.page.locator('input[type="checkbox"]')).first
        
        # Select an option again
        print("Selecting 'Declining sales' option again...")
        declining_sales_checkbox = sg01_section.locator('input[type="checkbox"][value="declining_sales"]').first
        await declining_sales_checkbox.click()
        
        # Wait for evaluation
        print("Waiting for re-evaluation...")
        await self.page.wait_for_timeout(3000)
        
        # Verify score appears again
        try:
            score_element = sg01_section.locator('div:has-text("Score:")').first
            await score_element.wait_for(timeout=10000)
            score_text = await score_element.text_content()
            print(f"✓ Score reappeared after reselection: {score_text}")
            return True
        except:
            print("✗ Score did not appear after reselecting option")
            return False
            
    async def test_other_text_field_functionality(self):
        """Test that 'Other' text field works properly without duplicates"""
        print("\n--- Testing Other Text Field Functionality ---")
        
        # Find the SG01 question container more precisely
        sg01_section = self.page.locator('div').filter(has_text="Why are you selling now?").filter(has=self.page.locator('input[type="checkbox"]')).first
        
        # Clear any existing selections first
        checkboxes = await sg01_section.locator('input[type="checkbox"]').all()
        for checkbox in checkboxes:
            if await checkbox.is_checked():
                await checkbox.click()
        
        await self.page.wait_for_timeout(500)
        
        # Select "Other" option (note: value is lowercase "other" in config)
        print("Selecting 'Other' option...")
        other_checkbox = sg01_section.locator('input[type="checkbox"][value="other"]').first
        await other_checkbox.click()
        
        # Find and fill the text field (specifically SG01_OTHER)
        print("Finding and filling the 'Other' text field...")
        sg01_other_input = sg01_section.locator('input[type="text"]').filter(lambda el: 'SG01_OTHER' in el.get_attribute('id') if el.get_attribute('id') else False).first
        
        try:
            await sg01_other_input.wait_for(timeout=2000)
            await sg01_other_input.fill("Custom reason for selling")
            await sg01_other_input.blur()  # Trigger onBlur event
            print("✓ Successfully filled SG01_OTHER text field")
        except:
            print("✗ Could not find or fill SG01_OTHER text field")
            return False
        
        print("Waiting for evaluation with 'Other' text...")
        await self.page.wait_for_timeout(3000)
        
        # Verify score appears
        try:
            score_element = sg01_section.locator('div:has-text("Score:")').first
            await score_element.wait_for(timeout=10000)
            score_text = await score_element.text_content()
            print(f"✓ Score appeared with 'Other' text: {score_text}")
            return True
        except:
            print("✗ Score did not appear with 'Other' text input")
            return False
            
    async def run_all_tests(self):
        """Run all tests and report results"""
        print("=== Comprehensive Other Field Fixes Test ===")
        print(f"Testing application at: {self.base_url}")
        
        try:
            await self.setup()
            
            # Run all tests
            test_results = {
                "no_duplicate_text_fields": await self.test_no_duplicate_text_fields(),
                "empty_answer_state_reset": await self.test_empty_answer_state_reset(),
                "re_evaluation_after_reselection": await self.test_re_evaluation_after_reselection(),
                "other_text_field_functionality": await self.test_other_text_field_functionality()
            }
            
            # Report results
            print("\n=== TEST RESULTS ===")
            all_passed = True
            for test_name, passed in test_results.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"{test_name}: {status}")
                if not passed:
                    all_passed = False
                    
            print(f"\nOverall Result: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
            return all_passed
            
        except Exception as e:
            print(f"Test execution failed: {e}")
            return False
        finally:
            await self.teardown()

async def main():
    """Main function to run the comprehensive test"""
    test = ComprehensiveOtherFieldTest()
    success = await test.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())