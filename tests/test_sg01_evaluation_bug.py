#!/usr/bin/env python3
"""
Automated End-to-End Test for SG01 Question Evaluation Bug

This test reproduces the critical bug where AI evaluation gives incorrect scores
for the "Why are you selling now?" question when "Declining sales" is selected.

Expected behavior: Score 0-19 (Critical Risk)
Actual behavior: Score 50 + explanation about restaurant in Charlotte, NC

Test process:
1. Launch web interface at http://192.168.1.50:3000
2. Fill basic information to progress to SG01
3. Select "Declining sales" option
4. Verify AI response score and explanation
5. Document the bug for debugging purposes
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright")
    print("   Then: playwright install")
    exit(1)


class SG01EvaluationBugTest:
    """Test class for reproducing SG01 evaluation bug."""
    
    def __init__(self, base_url="http://192.168.1.50:3000"):
        self.base_url = base_url
        self.page = None
        self.browser = None
        
    def setup_browser(self):
        """Initialize browser and page."""
        print("🚀 Launching browser...")
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        
        # Set viewport size
        self.page.set_viewport_size({"width": 1280, "height": 720})
        
    def navigate_to_app(self):
        """Navigate to the application."""
        print(f"🌐 Navigating to {self.base_url}...")
        self.page.goto(self.base_url)
        
        # Wait for the application to load
        self.page.wait_for_selector('text=Predictex AI')
        print("✅ Application loaded successfully")
        
    def fill_basic_information(self):
        """Fill in basic information to progress to SG01 question."""
        print("📝 Filling basic information...")
        
        # Fill business location
        location_field = self.page.locator('input[placeholder*="location"]').first
        if location_field.is_visible():
            location_field.fill("New York, NY, USA")
            print("  ✓ Business location filled")
        
        # Fill business activity/industry
        industry_field = self.page.locator('input[placeholder*="business does"], textarea[placeholder*="business does"]').first
        if industry_field.is_visible():
            industry_field.fill("Software consulting services")
            print("  ✓ Business industry filled")
            
        # Wait a moment for any auto-progression
        time.sleep(2)
        
    def wait_for_sg01_question(self):
        """Wait for SG01 question to appear and become visible."""
        print("⏳ Waiting for SG01 question...")
        
        # Look for the question text
        sg01_question = self.page.locator('text=Why are you selling now?')
        sg01_question.wait_for(state='visible', timeout=10000)
        print("✅ SG01 question is visible")
        
    def select_declining_sales(self):
        """Select 'Declining sales' option in SG01 question."""
        print("🎯 Selecting 'Declining sales' option...")
        
        # Use more specific selector for declining sales checkbox
        declining_sales_checkbox = self.page.get_by_role("checkbox", name="Declining sales")
        declining_sales_checkbox.check()
        print("✅ 'Declining sales' option selected")
        
        # Wait for evaluation to complete
        print("⏳ Waiting for AI evaluation...")
        time.sleep(3)
        
    def capture_evaluation_results(self):
        """Capture and analyze the evaluation results."""
        print("📊 Capturing evaluation results...")
        
        results = {}
        
        # Wait for results to load
        self.page.wait_for_selector('text=High Risk, text=Low Risk, text=Critical Risk, text=Moderate Risk', timeout=10000)
        
        # Get the score - look for numeric display
        score_elements = self.page.locator('text=/^\\d+$/').all()
        for element in score_elements:
            score_text = element.text_content().strip()
            if score_text.isdigit():
                results['score'] = int(score_text)
                break
        
        # Get the risk level
        risk_levels = ["Critical Risk", "High Risk", "Moderate Risk", "Low Risk"]
        for level in risk_levels:
            risk_element = self.page.locator(f'text={level}').first
            if risk_element.is_visible():
                results['risk_level'] = level
                break
        
        # Get explanation by clicking Explain button if available
        explain_button = self.page.locator('button:has-text("Explain")').first
        if explain_button.is_visible():
            explain_button.click()
            time.sleep(1)
            
            # Look for explanation in various possible locations
            explanation_selectors = [
                '[class*="explanation"]',
                '[class*="explain"]',
                'div:has(button:text("Explain")) + div',
                'div:has(button:text("Collapse")) div'
            ]
            
            for selector in explanation_selectors:
                explanation_element = self.page.locator(selector).first
                if explanation_element.is_visible():
                    explanation_text = explanation_element.text_content().strip()
                    if explanation_text and len(explanation_text) > 10:  # Valid explanation
                        results['explanation'] = explanation_text
                        break
        
        return results
        
    def analyze_results(self, results):
        """Analyze results and determine if bug is present."""
        print("\n" + "="*60)
        print("📋 EVALUATION RESULTS ANALYSIS")
        print("="*60)
        
        score = results.get('score', 'N/A')
        risk_level = results.get('risk_level', 'N/A')
        explanation = results.get('explanation', 'N/A')
        
        print(f"Score: {score}")
        print(f"Risk Level: {risk_level}")
        print(f"Explanation: {explanation}")
        
        # Expected behavior analysis
        print("\n" + "="*60)
        print("🎯 EXPECTED vs ACTUAL BEHAVIOR")
        print("="*60)
        
        expected_score_range = "0-19 (Critical Risk)"
        actual_score = score
        
        print(f"Expected Score: {expected_score_range}")
        print(f"Actual Score: {actual_score}")
        
        # Check for bugs
        bugs_found = []
        
        if isinstance(score, int) and score >= 20:
            bugs_found.append("❌ SCORE BUG: Score should be 0-19 for declining sales (critical risk)")
            
        if 'restaurant' in explanation.lower() and 'charlotte' in explanation.lower():
            bugs_found.append("❌ EXPLANATION BUG: AI giving unrelated restaurant explanation")
            
        if 'dso' in explanation.lower() or 'days sales outstanding' in explanation.lower():
            bugs_found.append("❌ CONTEXT BUG: AI confusing question context (DSO vs declining sales)")
        
        if bugs_found:
            print(f"\n🚨 {len(bugs_found)} BUG(S) DETECTED:")
            for bug in bugs_found:
                print(f"  {bug}")
                
            print(f"\n💡 DIAGNOSIS:")
            print(f"  - Web interface works correctly (sends proper data)")
            print(f"  - AI evaluation logic has context confusion")
            print(f"  - Possible prompt contamination or memory leak")
            
        else:
            print("\n✅ NO BUGS DETECTED - Evaluation working correctly")
            
        return len(bugs_found) == 0
        
    def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            self.browser.close()
            print("🧹 Browser closed")
    
    def run_test(self):
        """Run the complete test sequence."""
        print("🔬 STARTING SG01 EVALUATION BUG TEST")
        print("="*60)
        
        try:
            self.setup_browser()
            self.navigate_to_app()
            self.fill_basic_information()
            self.wait_for_sg01_question()
            self.select_declining_sales()
            
            results = self.capture_evaluation_results()
            test_passed = self.analyze_results(results)
            
            print("\n" + "="*60)
            if test_passed:
                print("✅ TEST PASSED: No bugs detected")
            else:
                print("❌ TEST FAILED: Bugs detected in AI evaluation")
            print("="*60)
            
            return test_passed
            
        except Exception as e:
            print(f"💥 TEST ERROR: {e}")
            return False
            
        finally:
            self.cleanup()


def main():
    """Main test execution function."""
    print("🧪 SG01 Evaluation Bug Test")
    print("Testing AI evaluation for 'Why are you selling now?' question")
    print()
    
    # Check if server is accessible
    import requests
    try:
        response = requests.get("http://192.168.1.50:3000", timeout=5)
        print("✅ Server is accessible")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please ensure the application is running on http://192.168.1.50:3000")
        return
    
    # Run the test
    test = SG01EvaluationBugTest()
    success = test.run_test()
    
    # Exit with appropriate code
    exit(0 if success else 1)


if __name__ == "__main__":
    main()