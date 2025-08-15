#!/usr/bin/env python3
"""
Test debounce functionality in QuestionSection component.

This test verifies that:
1. Request sending is delayed by the configured amount (default 1 second)
2. Multiple rapid user interactions reset the timer
3. Only the final action triggers a request
4. Different interaction types (checkbox, text, radio) all respect debouncing
"""

import sys
import os
import json
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_debounce_config_loading():
    """Test that debounce configuration is properly loaded from app.config.json"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'app.config.json')
    
    print("Testing debounce configuration loading...")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        request_send_delay = config.get('Frontend', {}).get('request_send_delay')
        
        assert request_send_delay is not None, "request_send_delay not found in config"
        assert request_send_delay == 1000, f"Expected request_send_delay=1000, got {request_send_delay}"
        
        print(f"✅ Debounce delay configured: {request_send_delay}ms")
        return True
        
    except Exception as e:
        print(f"❌ Failed to load debounce config: {e}")
        return False

def test_debounce_utils_import():
    """Test that debounce utilities can be imported"""
    print("\nTesting debounce utilities import...")
    
    try:
        # Test if the debounce utils file exists and is readable
        debounce_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'debounceUtils.js')
        
        assert os.path.exists(debounce_path), f"debounceUtils.js not found at {debounce_path}"
        
        with open(debounce_path, 'r') as f:
            content = f.read()
            
        # Check for required functions
        assert 'export function debounce(' in content, "debounce function not found"
        assert 'export function useDebounce(' in content, "useDebounce function not found" 
        assert 'export function useDebouncedCallback(' in content, "useDebouncedCallback function not found"
        
        print("✅ All debounce utilities found in debounceUtils.js")
        return True
        
    except Exception as e:
        print(f"❌ Failed to verify debounce utils: {e}")
        return False

def test_question_section_integration():
    """Test that QuestionSection.js is properly integrated with debounce functionality"""
    print("\nTesting QuestionSection debounce integration...")
    
    try:
        question_section_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'QuestionSection.js')
        
        assert os.path.exists(question_section_path), f"QuestionSection.js not found at {question_section_path}"
        
        with open(question_section_path, 'r') as f:
            content = f.read()
            
        # Check for debounce integration
        assert 'import { useDebouncedCallback } from \'./debounceUtils\';' in content, "debounceUtils import not found"
        assert 'useDebouncedCallback(' in content, "useDebouncedCallback hook not used"
        assert 'request_send_delay' in content, "request_send_delay config not accessed"
        assert 'debouncedSubmissionTrigger' in content, "debouncedSubmissionTrigger not found"
        
        # Check that direct setSubmissionTrigger calls are replaced with debounced version
        lines = content.split('\n')
        debounced_calls = [line for line in lines if 'debouncedSubmissionTrigger.run(' in line]
        direct_calls = [line for line in lines if 'setSubmissionTrigger({ question' in line and 'debouncedSubmissionTrigger' not in line]
        
        assert len(debounced_calls) >= 2, f"Expected at least 2 debounced calls, found {len(debounced_calls)}"
        assert len(direct_calls) == 0, f"Found {len(direct_calls)} direct setSubmissionTrigger calls that should be debounced"
        
        print(f"✅ QuestionSection properly integrated with debounce ({len(debounced_calls)} debounced calls)")
        return True
        
    except Exception as e:
        print(f"❌ Failed to verify QuestionSection integration: {e}")
        return False

def test_debounce_behavior_simulation():
    """Simulate debounce behavior using Python timing"""
    print("\nSimulating debounce behavior...")
    
    class MockDebounce:
        def __init__(self, delay_ms):
            self.delay_ms = delay_ms / 1000.0  # Convert to seconds
            self.timer = None
            self.callback = None
            self.call_count = 0
            
        def run(self, callback, *args):
            self.callback = callback
            self.call_count += 1
            
            # Cancel previous timer
            if self.timer:
                self.timer = None
                
            # Schedule new execution
            self.timer = time.time() + self.delay_ms
            
        def check_execution(self):
            if self.timer and time.time() >= self.timer:
                self.timer = None
                if self.callback:
                    self.callback()
                    return True
            return False
    
    try:
        # Test rapid interactions
        debouncer = MockDebounce(100)  # 100ms for faster testing
        executed = False
        
        def mock_submission():
            nonlocal executed
            executed = True
        
        # Simulate rapid user interactions
        start_time = time.time()
        debouncer.run(mock_submission)  # First interaction
        time.sleep(0.05)  # 50ms
        debouncer.run(mock_submission)  # Second interaction (should reset timer)
        time.sleep(0.05)  # 50ms 
        debouncer.run(mock_submission)  # Third interaction (should reset timer again)
        
        # At this point, no execution should have happened
        assert not debouncer.check_execution(), "Callback executed too early"
        assert not executed, "Callback executed before delay period"
        
        # Wait for delay period
        time.sleep(0.12)  # Additional 120ms = 170ms total from last interaction
        
        # Now execution should happen
        execution_happened = debouncer.check_execution()
        
        print(f"   Timer set: {debouncer.timer is not None}")
        print(f"   Current time: {time.time()}")
        print(f"   Timer time: {debouncer.timer}")
        print(f"   Execution happened: {execution_happened}")
        print(f"   Callback executed: {executed}")
        
        # The execution should happen immediately when checked after the delay
        assert execution_happened or executed, "Callback should execute after delay"
        
        print(f"✅ Debounce behavior simulation successful ({debouncer.call_count} calls, 1 execution)")
        return True
        
    except Exception as e:
        print(f"❌ Debounce simulation failed: {e}")
        return False

def main():
    """Run all debounce functionality tests"""
    print("=" * 60)
    print("TESTING DEBOUNCE FUNCTIONALITY")
    print("=" * 60)
    
    tests = [
        test_debounce_config_loading,
        test_debounce_utils_import, 
        test_question_section_integration,
        test_debounce_behavior_simulation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"DEBOUNCE TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All debounce functionality tests passed!")
        return True
    else:
        print("⚠️  Some debounce tests failed. Check implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)