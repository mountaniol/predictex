#!/usr/bin/env python3
"""
Test script to verify WebSearch fix - search should execute for all question types
"""
import json
import sys
import os

# Add src path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'backend'))

# Import the specific module directly
import importlib.util
backend_path = os.path.join(os.path.dirname(__file__), 'src', 'backend', 'ai_providers_with_search.py')
spec = importlib.util.spec_from_file_location("ai_providers_with_search", backend_path)
ai_providers_with_search = importlib.util.module_from_spec(spec)

# We'll test the logic directly by inspecting the _should_perform_search method

def test_websearch_configuration():
    """Test that configuration is loaded correctly"""
    print("🧪 Testing WebSearch Configuration...")
    
    # Load config
    with open('public/app.config.json', 'r') as f:
        config = json.load(f)
    
    backend_config = config.get('Backend', {})
    search_integration = backend_config.get('ai_web_search_integration', {})
    
    # Check new configuration options
    force_search_all = search_integration.get('force_search_all', False)
    disable_business_filters = search_integration.get('disable_business_filters', False)
    
    print(f"✅ force_search_all: {force_search_all}")
    print(f"✅ disable_business_filters: {disable_business_filters}")
    
    assert force_search_all == True, "force_search_all should be True"
    assert disable_business_filters == True, "disable_business_filters should be True"
    
    print("✅ Configuration test passed!")
    return backend_config

def test_business_question_search_decision():
    """Test that business evaluation questions now trigger search"""
    print("\n🧪 Testing Business Question Search Decision...")
    
    # Load config
    with open('public/app.config.json', 'r') as f:
        config = json.load(f)
    
    backend_config = config.get('Backend', {})
    
    # Create mock providers (we don't need real AI for this test)
    class MockAIProvider:
        def chat_completion(self, messages, **kwargs):
            return {"choices": [{"message": {"content": "test"}}]}
    
    class MockSearchRouter:
        def __init__(self, config):
            pass
        async def search(self, query):
            return type('MockResponse', (), {'results': []})()
    
    base_provider = MockAIProvider()
    search_router = MockSearchRouter({})
    
    # Create WebSearchEnabledAIProvider
    ws_provider = WebSearchEnabledAIProvider(base_provider, search_router, backend_config)
    
    # Test business evaluation prompts that should NOW trigger search
    business_test_cases = [
        {
            "name": "Risk Assessment Question",
            "messages": [{"role": "user", "content": "Please evaluate the risk assessment of this business model. Score from 0-100."}]
        },
        {
            "name": "Business Evaluator Question", 
            "messages": [{"role": "user", "content": "As a business evaluator, assess the strategic positioning of this company."}]
        },
        {
            "name": "Investment Analysis",
            "messages": [{"role": "user", "content": "Analyze this investment opportunity and return only a single json object with score and explanation."}]
        },
        {
            "name": "Financial Health Assessment",
            "messages": [{"role": "user", "content": "Evaluate the financial health and operational efficiency of the business."}]
        }
    ]
    
    for test_case in business_test_cases:
        print(f"  Testing: {test_case['name']}")
        should_search = ws_provider._should_perform_search(test_case['messages'])
        print(f"    Search decision: {should_search}")
        assert should_search == True, f"Business question '{test_case['name']}' should trigger search when force_search_all=True"
        print(f"    ✅ PASSED")
    
    print("✅ Business question search test passed!")

def test_general_question_search_decision():
    """Test that general questions still trigger search"""
    print("\n🧪 Testing General Question Search Decision...")
    
    # Load config
    with open('public/app.config.json', 'r') as f:
        config = json.load(f)
    
    backend_config = config.get('Backend', {})
    
    # Create mock providers
    class MockAIProvider:
        def chat_completion(self, messages, **kwargs):
            return {"choices": [{"message": {"content": "test"}}]}
    
    class MockSearchRouter:
        def __init__(self, config):
            pass
        async def search(self, query):
            return type('MockResponse', (), {'results': []})()
    
    base_provider = MockAIProvider()
    search_router = MockSearchRouter({})
    
    # Create WebSearchEnabledAIProvider
    ws_provider = WebSearchEnabledAIProvider(base_provider, search_router, backend_config)
    
    # Test general questions
    general_test_cases = [
        {
            "name": "Current Events Question",
            "messages": [{"role": "user", "content": "What are the latest news about artificial intelligence?"}]
        },
        {
            "name": "Factual Question",
            "messages": [{"role": "user", "content": "What is the current price of Bitcoin today?"}]
        },
        {
            "name": "Search Trigger Question",
            "messages": [{"role": "user", "content": "Найди информацию о последних разработках в области машинного обучения"}]
        },
        {
            "name": "Regular Question",
            "messages": [{"role": "user", "content": "Tell me about the weather forecast."}]
        }
    ]
    
    for test_case in general_test_cases:
        print(f"  Testing: {test_case['name']}")
        should_search = ws_provider._should_perform_search(test_case['messages'])
        print(f"    Search decision: {should_search}")
        assert should_search == True, f"Question '{test_case['name']}' should trigger search when force_search_all=True"
        print(f"    ✅ PASSED")
    
    print("✅ General question search test passed!")

def test_force_search_all_disabled():
    """Test behavior when force_search_all is disabled"""
    print("\n🧪 Testing Behavior with force_search_all=False...")
    
    # Create config with force_search_all disabled
    config = {
        'ai_web_search_integration': {
            'enabled': True,
            'force_search_all': False,
            'disable_business_filters': False,
            'auto_search_triggers': ["найди", "поищи"],
            'max_search_results_in_context': 5,
            'search_result_format': 'markdown'
        }
    }
    
    # Create mock providers
    class MockAIProvider:
        def chat_completion(self, messages, **kwargs):
            return {"choices": [{"message": {"content": "test"}}]}
    
    class MockSearchRouter:
        def __init__(self, config):
            pass
        async def search(self, query):
            return type('MockResponse', (), {'results': []})()
    
    base_provider = MockAIProvider()
    search_router = MockSearchRouter({})
    
    # Create WebSearchEnabledAIProvider with force_search_all=False
    ws_provider = WebSearchEnabledAIProvider(base_provider, search_router, config)
    
    # Test that business questions are still blocked when force_search_all=False
    business_messages = [{"role": "user", "content": "Please evaluate the risk assessment. Score from 0-100."}]
    should_search = ws_provider._should_perform_search(business_messages)
    print(f"  Business question with force_search_all=False: {should_search}")
    assert should_search == False, "Business questions should be blocked when force_search_all=False"
    
    # Test that trigger questions still work
    trigger_messages = [{"role": "user", "content": "Найди информацию о компании"}]
    should_search = ws_provider._should_perform_search(trigger_messages)
    print(f"  Trigger question with force_search_all=False: {should_search}")
    assert should_search == True, "Trigger questions should work when force_search_all=False"
    
    print("✅ force_search_all=False test passed!")

def main():
    """Main test function"""
    print("🔍 WebSearch Fix Verification Tests")
    print("=" * 50)
    
    try:
        # Test 1: Configuration
        test_websearch_configuration()
        
        # Test 2: Business questions now trigger search
        test_business_question_search_decision()
        
        # Test 3: General questions still trigger search
        test_general_question_search_decision()
        
        # Test 4: Behavior when force_search_all is disabled
        test_force_search_all_disabled()
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("✅ WebSearch now executes for all question types when force_search_all=True")
        print("✅ Business evaluation filters can be disabled")
        print("✅ Configuration is correctly loaded and applied")
        print("✅ Backwards compatibility maintained when force_search_all=False")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()