#!/usr/bin/env python3
"""
Web search system testing
"""
import asyncio
import json
import os
import sys
from typing import Dict, Any

# Add root directory to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.backend.search_router import SearchRouter
from src.backend.query_classifier import QueryClassifier
from src.backend.ai_providers_with_search import get_ai_provider_with_search, search_web


def load_config() -> Dict[str, Any]:
    """Load configuration"""
    config_path = os.path.join(PROJECT_ROOT, 'public', 'app.config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def test_query_classifier():
    """Test query classifier"""
    print("=== Testing QueryClassifier ===")
    
    config = load_config()
    classifier = QueryClassifier(config.get('Backend', {}).get('web_search', {}).get('classification', {}))
    
    test_queries = [
        "What are neural networks?",  # factual
        "Latest news in the world of technology",  # current
        "Find information about Python",  # general
        "What events happened today?",  # current
        "Definition of machine learning",  # factual
    ]
    
    for query_text in test_queries:
        from src.backend.search_models import SearchQuery
        query = SearchQuery(text=query_text)
        classification = classifier.classify(query)
        
        print(f"Query: '{query_text}'")
        print(f"  Type: {classification['primary_type']}")
        print(f"  Confidence: {classification['confidence']:.2f}")
        print(f"  Suggested providers: {classification['suggested_providers']}")
        print(f"  Reasoning: {classification['reasoning']}")
        print()


async def test_search_providers():
    """Test search providers"""
    print("=== Testing search providers ===")
    
    config = load_config()
    web_search_config = config.get('Backend', {}).get('web_search', {})
    
    if not web_search_config.get('enabled', False):
        print("⚠️  Web search disabled in configuration")
        return
    
    search_router = SearchRouter(web_search_config)
    
    # Check provider status
    print("Provider status:")
    provider_status = await search_router.get_provider_status()
    for name, status in provider_status.items():
        available = "✅" if status['available'] else "❌"
        print(f"  {name}: {available}")
    
    # Test search
    test_queries = [
        "Python programming",  # for DuckDuckGo
        "artificial intelligence",  # for Wikipedia
        "technology",  # for RSS
    ]
    
    for query_text in test_queries:
        print(f"\nSearch: '{query_text}'")
        try:
            from src.backend.search_models import SearchQuery
            query = SearchQuery(text=query_text, max_results=3)
            response = await search_router.search(query)
            print(f"  Results found: {len(response.results)}")
            print(f"  Search time: {response.search_time:.2f}s")
            print(f"  Sources used: {response.sources_used}")
            print(f"  Cache: {'hit' if response.cache_hit else 'miss'}")
            
            for i, result in enumerate(response.results[:2], 1):
                print(f"    {i}. {result.title[:50]}...")
                print(f"       Source: {result.source} (score: {result.score:.2f})")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()


async def test_ai_integration():
    """Test AI provider integration"""
    print("=== Testing AI integration ===")
    
    config = load_config()
    backend_config = config.get('Backend', {})
    
    try:
        # Get AI provider with web search support
        ai_provider = get_ai_provider_with_search(config)
        
        # Determine model from configuration
        ai_provider_type = backend_config.get("ai_provider", "openai")
        if ai_provider_type == "ollama":
            provider_config = backend_config.get("ollama", {})
            model = provider_config.get("model")
            if not model:
                print("  ⚠️ Ollama model not specified in configuration, test skipped")
                return
        else:
            provider_config = backend_config.get("openai", {})
            model = provider_config.get("model")
            if not model:
                model = provider_config.get("simple_evaluate_model")
            if not model:
                print("  ⚠️ OpenAI model not specified in configuration, test skipped")
                return
                
        print(f"  ℹ️ Using model: {model}")
        
        test_messages = [
            # Query that should trigger search
            [
                {"role": "user", "content": "Find the latest news about AI development"}
            ],
            # Factual query
            [
                {"role": "user", "content": "What are large language models?"}
            ],
            # Regular query without search
            [
                {"role": "user", "content": "Hello, how are you?"}
            ]
        ]
        
        for i, messages in enumerate(test_messages, 1):
            print(f"Test {i}: {messages[0]['content']}")
            try:
                # Test regular completion with explicit model specification
                response = ai_provider.chat_completion(
                    messages=messages,
                    model=model,
                    max_tokens=150,
                    temperature=0.3
                )
                print(f"  ✅ Response received (length: {len(response['content'])} characters)")
                
                # Show first 100 characters of response
                preview = response['content'][:100] + "..." if len(response['content']) > 100 else response['content']
                print(f"  Preview: {preview}")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            print()
            
    except Exception as e:
        print(f"❌ AI provider initialization error: {e}")


async def test_web_search_utility():
    """Test web search utility function"""
    print("=== Testing web search utility function ===")
    
    config = load_config()
    
    try:
        # Create new event loop for this test
        results = await search_web("machine learning", config)
        print(f"Results found: {len(results)}")
        
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result.title}")
            print(f"     Source: {result.source}")
            print(f"     URL: {result.url}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_health_check():
    """System health check"""
    print("=== System health check ===")
    
    config = load_config()
    web_search_config = config.get('Backend', {}).get('web_search', {})
    
    if not web_search_config.get('enabled', False):
        print("⚠️  Web search disabled in configuration")
        return
    
    search_router = SearchRouter(web_search_config)
    
    try:
        health = await search_router.health_check()
        print(f"System status: {health['status']}")
        print(f"Strategy: {health['strategy']}")
        print(f"Enabled: {health['enabled']}")
        
        print("\nProviders:")
        for name, info in health['providers'].items():
            status = "✅" if info['available'] else "❌"
            print(f"  {name}: {status}")
            
        print(f"\nClassifier:")
        classifier_info = health['classifier']
        print(f"  Confidence threshold: {classifier_info['confidence_threshold']}")
        print(f"  Supported types: {classifier_info['supported_types']}")
        
        cache_info = health['cache']
        if cache_info.get('enabled'):
            print(f"\nCache:")
            if 'stats' in cache_info:
                stats = cache_info['stats']
                print(f"  Total entries: {stats.get('total_entries', 0)}")
                print(f"  Active entries: {stats.get('active_entries', 0)}")
        
    except Exception as e:
        print(f"❌ Check error: {e}")


async def main():
    """Main testing function"""
    print("🔍 Web search system testing\n")
    
    # Check configuration
    try:
        config = load_config()
        print("✅ Configuration loaded")
    except Exception as e:
        print(f"❌ Configuration loading error: {e}")
        return
    
    # Run tests
    tests = [
        ("Query Classifier", test_query_classifier),
        ("Search Providers", test_search_providers),
        ("AI Integration", test_ai_integration),
        ("Utility Function", test_web_search_utility),
        ("Health Check", test_health_check),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print('='*60)
        
        try:
            await test_func()
        except Exception as e:
            print(f"❌ Critical error in test '{test_name}': {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("✅ Testing completed!")
    
    # Close all resources
    for test_name, test_func in tests:
        if test_name == "Search Providers" and 'search_router' in locals():
            try:
                await search_router.cleanup()
                print("✅ SearchRouter resources cleaned")
            except Exception as e:
                print(f"❌ Error cleaning SearchRouter resources: {e}")
        
        if test_name == "AI Integration" and 'ai_provider' in locals():
            if hasattr(ai_provider, 'cleanup') and callable(ai_provider.cleanup):
                try:
                    await ai_provider.cleanup()
                    print("✅ AI provider resources cleaned")
                except Exception as e:
                    print(f"❌ Error cleaning AI provider resources: {e}")


if __name__ == "__main__":
    # Run tests
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
        print("Cleaning up resources...")
        # Cannot call cleanup directly here as we're outside async context
        # But can print message about restart requirement for proper cleanup
        print("To properly clean resources, restart the script and let it complete normally")