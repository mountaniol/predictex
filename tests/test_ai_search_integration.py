#!/usr/bin/env python3
"""
Integration test for AI-powered search with real backend
"""
import requests
import json
import time

def test_ai_powered_search():
    """Test AI-powered search through the backend API"""
    
    print("\n" + "="*80)
    print("🧪 TESTING AI-POWERED SEARCH INTEGRATION")
    print("="*80)
    
    url = "http://localhost:3001/api/simple-evaluate.mjs"
    
    test_cases = [
        {
            "name": "Declining Sales Analysis",
            "payload": {
                "questionId": "SG01",
                "allAnswers": {
                    "SG01": ["declining_sales", "increased_competition"],
                    "MET.LOC": "San Francisco, CA",
                    "MET.IND": "Technology",
                    "MET.SIZE": "50-100 employees"
                }
            }
        },
        {
            "name": "AI Competitive Advantage",
            "payload": {
                "questionId": "SG02",
                "allAnswers": {
                    "SG02": "We use AI and machine learning for predictive analytics in customer behavior",
                    "MET.LOC": "New York, NY",
                    "MET.IND": "FinTech",
                    "MET.SIZE": "100-500 employees"
                }
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n📝 Test: {test['name']}")
        print(f"   Question ID: {test['payload']['questionId']}")
        
        # Extract answer for display
        answer = test['payload']['allAnswers'].get(test['payload']['questionId'])
        if isinstance(answer, list):
            answer = ", ".join(answer)
        print(f"   Answer: {answer[:80]}{'...' if len(str(answer)) > 80 else ''}")
        print(f"   Context: {test['payload']['allAnswers'].get('MET.LOC')}, {test['payload']['allAnswers'].get('MET.IND')}")
        
        print(f"\n   🚀 Sending request...")
        start_time = time.time()
        
        try:
            response = requests.post(url, json=test['payload'], timeout=60)
            duration = time.time() - start_time
            
            print(f"   ⏱️ Response time: {duration:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success!")
                print(f"   📊 Score: {result.get('score')}")
                
                explanation = result.get('explanation', '')
                print(f"   📝 Explanation length: {len(explanation)} chars")
                
                # Check for AI search indicators
                ai_search_indicators = [
                    'according to', 'based on', 'research shows', 'data indicates',
                    'statistics show', 'industry report', 'market analysis', 
                    'recent trends', 'studies suggest', 'sources indicate'
                ]
                
                found_indicators = [ind for ind in ai_search_indicators 
                                  if ind.lower() in explanation.lower()]
                
                if found_indicators:
                    print(f"   🔍 AI Search indicators found: {', '.join(found_indicators[:3])}")
                    print(f"   ✨ Enhanced with AI-powered search results!")
                else:
                    print(f"   ⚠️ No clear AI search indicators detected")
                
                # Show a snippet of the explanation
                print(f"\n   📄 Explanation snippet:")
                print(f"      {explanation[:200]}...")
                
                # Check if response time indicates complex search (>10s usually means search was performed)
                if duration > 10:
                    print(f"\n   💡 Long response time ({duration:.1f}s) suggests comprehensive search was performed")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Request timeout after 60 seconds")
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Connection error - is the backend server running?")
            print(f"      Start with: python -m src.backend.py_local_api_server")
        except Exception as e:
            print(f"   💥 Unexpected error: {e}")


def test_search_configuration():
    """Test that AI search is properly configured"""
    
    print("\n" + "="*80)
    print("🧪 CHECKING AI SEARCH CONFIGURATION")
    print("="*80)
    
    # Check configuration file
    try:
        with open('public/app.config.json', 'r') as f:
            config = json.load(f)
        
        ai_search_config = config.get('Backend', {}).get('ai_web_search_integration', {})
        
        print("\n📋 Configuration Status:")
        print(f"   AI Search Enabled: {ai_search_config.get('enabled', False)}")
        print(f"   AI-Powered Queries: {ai_search_config.get('ai_powered_queries', False)}")
        print(f"   Search Result Format: {ai_search_config.get('search_result_format', 'text')}")
        print(f"   Max Results in Context: {ai_search_config.get('max_search_results_in_context', 0)}")
        
        web_search_config = config.get('Backend', {}).get('web_search', {})
        print(f"\n   Mock Providers Enabled: {web_search_config.get('enable_mock_providers', False)}")
        
        if ai_search_config.get('ai_powered_queries'):
            print("\n   ✅ AI-powered search is ENABLED!")
        else:
            print("\n   ⚠️ AI-powered search is DISABLED - using simple search")
            
    except Exception as e:
        print(f"\n   ❌ Error reading configuration: {e}")


def test_search_prompt_exists():
    """Check if the search query prompt file exists"""
    
    print("\n" + "="*80)
    print("🧪 CHECKING SEARCH QUERY PROMPT")
    print("="*80)
    
    try:
        with open('public/questions/search-query-prompt.txt', 'r') as f:
            content = f.read()
        
        print(f"\n   ✅ Search query prompt exists!")
        print(f"   📏 Prompt length: {len(content)} characters")
        
        # Check for key sections
        key_sections = [
            "PRIMARY GOAL OF SEARCH",
            "WHY YOU NEED TO SEARCH",
            "AVAILABLE SEARCH SOURCES",
            "OUTPUT FORMAT"
        ]
        
        print(f"\n   📋 Key sections found:")
        for section in key_sections:
            if section in content:
                print(f"      ✅ {section}")
            else:
                print(f"      ❌ {section} (missing)")
                
    except FileNotFoundError:
        print(f"\n   ❌ Search query prompt file not found!")
    except Exception as e:
        print(f"\n   ❌ Error reading prompt: {e}")


def main():
    """Run all integration tests"""
    
    print("\n🚀 Starting AI-Powered Search Integration Tests")
    
    # Test 1: Check configuration
    test_search_configuration()
    
    # Test 2: Check prompt file
    test_search_prompt_exists()
    
    # Test 3: Test with real backend
    test_ai_powered_search()
    
    print("\n" + "="*80)
    print("🏁 Integration Tests Complete!")
    print("="*80)
    print("\nNote: For best results, ensure the backend server is running:")
    print("  python -m src.backend.py_local_api_server")


if __name__ == "__main__":
    main()