#!/usr/bin/env python3
"""
Simple test to verify web search operations don't leak resources
"""
import warnings
import subprocess
import sys
import tempfile
import os

def capture_resource_warnings():
    """Capture ResourceWarnings from web search operations"""
    
    # Test script that simulates web search usage
    test_script = '''
import warnings
import sys
import os

# Capture all ResourceWarnings
warnings.simplefilter("always", ResourceWarning)

# Simulate the web search operation that was causing leaks
sys.path.append("src/backend")

def simulate_search_operation():
    try:
        # This would previously cause resource leaks
        import asyncio
        
        async def mock_search():
            # Simulate what ai_providers_with_search.py does
            from search_resource_manager import managed_search_operation
            
            config = {
                'web_search': {
                    'enabled': True,
                    'max_sessions': 2,
                    'session_timeout': 5
                }
            }
            
            # Use the new resource-managed approach
            async with managed_search_operation(config) as resource_manager:
                session = await resource_manager.get_session("test_provider")
                stats = await resource_manager.get_stats()
                print(f"Active sessions: {stats['active_sessions']}")
                return "search completed"
        
        # Run the search operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(mock_search())
            print(f"Search result: {result}")
        finally:
            loop.close()
            
        print("✅ Search operation completed without resource warnings")
        return True
        
    except Exception as e:
        print(f"❌ Error in search operation: {e}")
        return False

if __name__ == "__main__":
    # Enable resource warning tracking
    import warnings
    warnings.filterwarnings("error", category=ResourceWarning)
    
    try:
        success = simulate_search_operation()
        sys.exit(0 if success else 1)
    except ResourceWarning as w:
        print(f"❌ ResourceWarning detected: {w}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
'''
    
    # Write test script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        # Run the test script and capture output
        result = subprocess.run([
            sys.executable, temp_script
        ], capture_output=True, text=True, timeout=30)
        
        return result
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_script)
        except OSError:
            pass


def main():
    """Main test function"""
    print("🔍 WebSearch Resource Leak Verification")
    print("=" * 50)
    
    print("Running resource warning detection test...")
    
    try:
        result = capture_resource_warnings()
        
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout}")
        
        if result.stderr:
            print(f"Errors: {result.stderr}")
        
        if result.returncode == 0:
            print("\n🎉 SUCCESS: No resource leaks detected!")
            print("✅ Web search operations properly manage resources")
            print("✅ No unclosed transports or sockets")
            print("✅ SearchResourceManager is working correctly")
        else:
            print("\n❌ FAILURE: Resource leaks or errors detected")
            print("Check the output above for details")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out - possible resource deadlock")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)