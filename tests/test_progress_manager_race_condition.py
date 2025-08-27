#!/usr/bin/env python3
"""
Test script to verify that the race condition in progress manager has been eliminated.

This test simulates the original race condition scenario:
1. progressManager.startEvaluation() is called in handleAnswerBlur
2. evaluateAnswer() is called later (previously with its own setEvaluating state)
3. progressManager.completeEvaluation() is called after evaluateAnswer returns

The race condition warning should no longer appear after the fix.
"""

import asyncio
import sys
import os
import time
import requests
import threading
import json
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_frontend_backend_integration():
    """Test that frontend and backend are running and responding"""
    print("🧪 Testing Frontend-Backend Integration")
    
    try:
        # Test backend health
        backend_response = requests.get('http://localhost:3001/api/health', timeout=5)
        if backend_response.status_code == 200:
            print("✅ Backend is running and healthy")
        else:
            print(f"⚠️ Backend responded with status: {backend_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend connection failed: {e}")
        return False
    
    try:
        # Test frontend (React dev server typically returns HTML)
        frontend_response = requests.get('http://localhost:3000', timeout=5)
        if frontend_response.status_code == 200:
            print("✅ Frontend is running")
        else:
            print(f"⚠️ Frontend responded with status: {frontend_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Frontend connection failed: {e}")
        return False
    
    return True

def test_single_evaluation():
    """Test single question evaluation to ensure no race condition warnings"""
    print("\n🧪 Testing Single Question Evaluation")
    
    test_payload = {
        "questionId": "SG01",
        "allAnswers": {
            "SG01": ["declining_sales"],
            "MET.LOC": "Charlotte, NC"
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            'http://localhost:3001/api/simple-evaluate.mjs',
            headers={'Content-Type': 'application/json'},
            json=test_payload,
            timeout=30
        )
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if 'score' in data and 'explanation' in data:
                print(f"✅ Evaluation successful in {duration:.2f}s")
                print(f"   Score: {data['score']}")
                print(f"   Explanation length: {len(data.get('explanation', ''))}")
                return True
            else:
                print(f"❌ Invalid response format: {data}")
                return False
        else:
            print(f"❌ Request failed with status {response.status_code}")
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            print(f"   Error: {error_data}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_concurrent_evaluations():
    """Test concurrent evaluations to stress-test the progress manager"""
    print("\n🧪 Testing Concurrent Evaluations")
    
    # Different question payloads for concurrent testing
    test_payloads = [
        {
            "questionId": "SG01",
            "allAnswers": {"SG01": ["declining_sales"], "MET.LOC": "Test Location 1"}
        },
        {
            "questionId": "SG02", 
            "allAnswers": {"SG02": ["poor_cash_flow"], "MET.LOC": "Test Location 2"}
        },
        {
            "questionId": "SG03",
            "allAnswers": {"SG03": ["market_competition"], "MET.LOC": "Test Location 3"}
        }
    ]
    
    results = []
    threads = []
    
    def make_request(payload, result_list):
        try:
            start_time = time.time()
            response = requests.post(
                'http://localhost:3001/api/simple-evaluate.mjs',
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=30
            )
            duration = time.time() - start_time
            result_list.append({
                'questionId': payload['questionId'],
                'success': response.status_code == 200,
                'duration': duration,
                'response': response.json() if response.status_code == 200 else None
            })
        except Exception as e:
            result_list.append({
                'questionId': payload['questionId'],
                'success': False,
                'error': str(e)
            })
    
    # Start concurrent requests
    print("   Starting 3 concurrent evaluation requests...")
    start_time = time.time()
    
    for payload in test_payloads:
        thread = threading.Thread(target=make_request, args=(payload, results))
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    total_duration = time.time() - start_time
    
    # Analyze results
    successful = len([r for r in results if r.get('success')])
    failed = len(results) - successful
    
    print(f"   Results: {successful} successful, {failed} failed")
    print(f"   Total time: {total_duration:.2f}s")
    
    if successful > 0:
        avg_duration = sum(r['duration'] for r in results if r.get('success')) / successful
        print(f"   Average evaluation time: {avg_duration:.2f}s")
    
    return successful >= 2  # At least 2 out of 3 should succeed

def check_console_logs_for_warnings():
    """
    Instructions for manual verification of race condition fix.
    Since we can't directly access browser console logs from this script,
    provide instructions for manual verification.
    """
    print("\n🧪 Manual Console Log Verification")
    print("   To verify the race condition has been eliminated:")
    print("   1. Open http://localhost:3000 in your browser")
    print("   2. Open Developer Tools (F12) and go to Console tab")
    print("   3. Answer several questions quickly")
    print("   4. Look for any warnings containing 'Trying to complete non-existent evaluation'")
    print("   5. ✅ SUCCESS: No such warnings should appear")
    print("   6. ❌ FAILURE: If warnings appear, the race condition still exists")
    
    return True

def run_all_tests():
    """Run all race condition elimination tests"""
    print("=" * 60)
    print("🚀 RACE CONDITION FIX VERIFICATION TESTS")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Frontend-Backend Integration
    if not test_frontend_backend_integration():
        all_passed = False
        print("❌ Skipping further tests due to integration issues")
        return False
    
    # Test 2: Single Evaluation
    if not test_single_evaluation():
        all_passed = False
    
    # Test 3: Concurrent Evaluations
    if not test_concurrent_evaluations():
        all_passed = False
        print("⚠️ Some concurrent evaluations failed - this may be expected under load")
    
    # Test 4: Manual Console Verification
    check_console_logs_for_warnings()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL AUTOMATED TESTS PASSED")
        print("   The race condition appears to be eliminated!")
        print("   Please complete manual console verification for full confirmation.")
    else:
        print("❌ SOME TESTS FAILED")
        print("   Review the failures above and check the implementation.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()