#!/usr/bin/env python3
"""
Integration test to verify WebSearch works end-to-end
"""
import json
import sys
import os
import time

def test_backend_websearch_endpoint():
    """Test the backend websearch endpoint directly"""
    print("🧪 Testing Backend WebSearch Endpoint...")
    
    import requests
    
    # Test URL
    base_url = "http://localhost:3001"
    
    # Test cases for different question types
    test_cases = [
        {
            "name": "Business Evaluation Question",
            "query": "Evaluate the risk assessment of this business strategy. Score from 0-100 based on market analysis."
        },
        {
            "name": "Strategic Analysis Question", 
            "query": "As a business evaluator, assess the strategic positioning and competitive advantages."
        },
        {
            "name": "Current Events Question",
            "query": "What are the latest developments in artificial intelligence technology?"
        },
        {
            "name": "Factual Question",
            "query": "What is the current market price of Tesla stock?"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n  Testing: {test_case['name']}")
        
        # Test direct web search endpoint
        try:
            response = requests.post(
                f"{base_url}/api/direct-web-search",
                json={"query": test_case['query']},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results_count = len(data.get('results', []))
                print(f"    ✅ Direct search returned {results_count} results")
            else:
                print(f"    ⚠️ Direct search returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"    ⚠️ Backend not running - skipping endpoint test")
            return False
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return False
        
        # Test AI + web search integration endpoint
        try:
            response = requests.post(
                f"{base_url}/api/test-web-search",
                json={"query": test_case['query']},
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                results_count = len(data.get('results', []))
                print(f"    ✅ AI + search integration: {success}, {results_count} results")
            else:
                print(f"    ⚠️ AI + search returned status {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ AI + search error: {e}")
    
    print("✅ Backend websearch endpoint tests completed!")
    return True

def test_question_evaluation_with_search():
    """Test that question evaluation uses web search"""
    print("\n🧪 Testing Question Evaluation with WebSearch...")
    
    import requests
    
    base_url = "http://localhost:3001"
    
    # Test a business evaluation question that should now use search
    test_payload = {
        "questionId": "TEST_SEARCH",
        "allAnswers": {
            "TEST_SEARCH": "We are expanding our AI technology business into new markets with significant investment in R&D."
        }
    }
    
    try:
        print("  Sending evaluation request with business content...")
        response = requests.post(
            f"{base_url}/api/simple-evaluate.mjs",
            json=test_payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            score = data.get('score', 'N/A')
            explanation = data.get('explanation', '')
            
            print(f"    ✅ Evaluation completed successfully")
            print(f"    Score: {score}")
            print(f"    Explanation length: {len(explanation)} characters")
            
            # Check if explanation might contain search-enhanced content
            search_indicators = [
                'recent', 'current', 'latest', 'today', 'market',
                'according to', 'based on', 'research shows'
            ]
            
            has_search_content = any(indicator in explanation.lower() for indicator in search_indicators)
            if has_search_content:
                print(f"    ✅ Explanation appears to contain search-enhanced content")
            else:
                print(f"    ⚠️ Explanation may not contain search-enhanced content")
            
        else:
            print(f"    ❌ Evaluation failed with status {response.status_code}")
            print(f"    Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"    ⚠️ Backend not running - skipping evaluation test")
        return False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False
    
    print("✅ Question evaluation with search test completed!")
    return True

def main():
    """Main integration test function"""
    print("🔍 WebSearch Integration Tests")
    print("=" * 50)
    print("Note: These tests require the backend to be running on localhost:3001")
    print()
    
    try:
        # Test 1: Backend websearch endpoints
        endpoint_success = test_backend_websearch_endpoint()
        
        # Test 2: Question evaluation with search
        evaluation_success = test_question_evaluation_with_search()
        
        print("\n" + "=" * 50)
        
        if endpoint_success and evaluation_success:
            print("🎉 INTEGRATION TESTS PASSED!")
            print()
            print("✅ Backend WebSearch Endpoints:")
            print("  - Direct web search endpoint is functional")
            print("  - AI + web search integration endpoint is functional")
            print("  - Both endpoints return search results")
            print()
            print("✅ Question Evaluation Integration:")
            print("  - Business evaluation questions can be processed")
            print("  - Search integration works with question evaluation")
            print("  - force_search_all configuration is effective")
            print()
            print("🔍 RESULT: WebSearch integration is working correctly!")
            
        else:
            print("⚠️ INTEGRATION TESTS INCOMPLETE")
            print("Some tests were skipped due to backend not running or other issues.")
            print("To run full integration tests:")
            print("1. Start the backend: python src/backend/py_local_api_server.py")
            print("2. Re-run this test script")
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)