#!/usr/bin/env python3
"""
Test DuckDuckGo provider without deprecation warnings
"""
import sys
import os
import asyncio
import warnings
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Capture all warnings
warnings.simplefilter('always')


async def test_duckduckgo_search():
    """Test DuckDuckGo provider"""
    print("\n🧪 Testing DuckDuckGo Provider")
    print("="*60)
    
    from src.backend.duckduckgo_provider import DuckDuckGoProvider
    from src.backend.search_models import SearchQuery
    
    config = {
        "enabled": True,
        "region": "us-en",
        "safe_search": "moderate",
        "max_results": 3
    }
    
    provider = DuckDuckGoProvider(config)
    
    # Check availability
    is_available = await provider.is_available()
    print(f"✅ Provider available: {is_available}")
    
    if is_available:
        # Test search
        query = SearchQuery(
            text="Python programming best practices",
            max_results=2,
            language="en"
        )
        
        print(f"\n🔍 Searching for: '{query.text}'")
        
        try:
            results = await provider.search(query)
            print(f"✅ Search completed, found {len(results)} results")
            
            if results:
                print("\n📄 Sample result:")
                first_result = results[0]
                print(f"   Title: {first_result.title}")
                print(f"   URL: {first_result.url}")
                print(f"   Content: {first_result.content[:150]}...")
                print(f"   Source: {first_result.source}")
                
        except Exception as e:
            print(f"❌ Search failed: {e}")
    else:
        print("⚠️ Provider not available")


def main():
    """Run tests and check for warnings"""
    print("\n🚀 Starting DuckDuckGo Provider Test")
    
    # Capture warnings during execution
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # Run the async test
        asyncio.run(test_duckduckgo_search())
        
        # Check for RuntimeWarnings
        print("\n" + "="*60)
        print("📊 Warning Analysis:")
        
        runtime_warnings = [
            warning for warning in w 
            if issubclass(warning.category, RuntimeWarning)
        ]
        
        ddg_warnings = [
            warning for warning in runtime_warnings
            if 'duckduckgo' in str(warning.message).lower() or 'ddgs' in str(warning.message).lower()
        ]
        
        if ddg_warnings:
            print(f"   ❌ Found {len(ddg_warnings)} DuckDuckGo-related warnings:")
            for warning in ddg_warnings:
                print(f"      - {warning.message}")
        else:
            print("   ✅ No DuckDuckGo deprecation warnings!")
            
        if runtime_warnings and not ddg_warnings:
            print(f"   ℹ️ Found {len(runtime_warnings)} other RuntimeWarnings (not DuckDuckGo related)")
    
    print("\n🏁 Test Complete!")


if __name__ == "__main__":
    main()