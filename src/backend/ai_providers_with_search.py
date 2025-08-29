"""
Extended AI Providers with integrated web search capabilities
"""
import asyncio
import re
from typing import Dict, Any, Optional, Generator, List
from .ai_providers import AIProvider, OpenAIProvider, OllamaProvider, get_ai_provider
from .search_router import SearchRouter
from .search_models import SearchResult
from .search_resource_manager import managed_search_operation


class WebSearchEnabledAIProvider(AIProvider):
    """AI Provider wrapper that adds web search capabilities"""
    
    def __init__(self, base_provider: AIProvider, search_router: SearchRouter, config: Dict[str, Any]):
        self.base_provider = base_provider
        self.search_router = search_router
        self.config = config
        self.search_config = config.get('ai_web_search_integration', {})
        self.enabled = self.search_config.get('enabled', True)
        # Web search is enabled for all questions without any filtering
        self.auto_search_triggers = self.search_config.get('auto_search_triggers', [])
        self.max_search_results_in_context = self.search_config.get('max_search_results_in_context', 5)
        self.search_result_format = self.search_config.get('search_result_format', 'markdown')
        
    def _should_perform_search(self, messages: list) -> bool:
        """Determine if web search should be performed based on the conversation"""
        print(f"\n🔍 [WEB SEARCH DEBUG] Checking if search should be performed...")
        print(f"🔍 [WEB SEARCH DEBUG] Search enabled: {self.enabled}")
        print(f"🔍 [WEB SEARCH DEBUG] Search enabled for ALL questions - no filtering logic")
        
        if not self.enabled:
            print(f"🔍 [WEB SEARCH DEBUG] ❌ Search disabled in config")
            return False
            
        # Validate we have messages
        if not messages:
            print(f"🔍 [WEB SEARCH DEBUG] ❌ No messages provided")
            return False
        
        # Check if we have user messages
        has_user_message = any(msg.get('role') == 'user' for msg in messages)
        if has_user_message:
            print(f"🔍 [WEB SEARCH DEBUG] ✅ Search will execute for this question")
            return True
        else:
            print(f"🔍 [WEB SEARCH DEBUG] ❌ No user messages found")
            return False
        
    def _extract_search_query(self, messages: list) -> str:
        """Extract the search query from the conversation"""
        print(f"🔍 [WEB SEARCH DEBUG] Extracting search query from messages...")
        
        # Get the last user message
        for message in reversed(messages):
            if message['role'] == 'user':
                user_query = message['content']
                print(f"🔍 [WEB SEARCH DEBUG] Using user query as search query: '{user_query}'")
                return user_query.strip()
                
        print(f"🔍 [WEB SEARCH DEBUG] No user message found for query extraction")
        return ""
        
    def _format_search_results(self, results: List[SearchResult]) -> str:
        """Format search results for inclusion in AI context"""
        print(f"🔍 [WEB SEARCH DEBUG] Formatting {len(results)} search results")
        
        if not results:
            print(f"🔍 [WEB SEARCH DEBUG] No results to format")
            return ""
            
        if self.search_result_format == 'markdown':
            formatted = "## Web Search Results\n\n"
            for i, result in enumerate(results[:self.max_search_results_in_context], 1):
                formatted += f"### {i}. {result.title}\n"
                formatted += f"**Source:** {result.source} ({result.metadata.get('provider', 'unknown')})\n"
                formatted += f"**URL:** {result.url}\n"
                formatted += f"**Content:** {result.content}\n"
                if result.timestamp:
                    formatted += f"**Date:** {result.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                formatted += "\n---\n\n"
            
            print(f"🔍 [WEB SEARCH DEBUG] Formatted {self.max_search_results_in_context} results in markdown format")
            return formatted
        else:
            # Plain text format
            formatted = "Web Search Results:\n\n"
            for i, result in enumerate(results[:self.max_search_results_in_context], 1):
                formatted += f"{i}. {result.title}\n"
                formatted += f"   Source: {result.source}\n"
                formatted += f"   {result.content}\n\n"
            
            print(f"🔍 [WEB SEARCH DEBUG] Formatted {self.max_search_results_in_context} results in plain text format")
            return formatted
            
    def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """
        Send a chat completion request with optional web search
        """
        print(f"\n🔍 [WEB SEARCH DEBUG] chat_completion called")
        
        # Check if we should perform a search
        if self._should_perform_search(messages):
            print(f"🔍 [WEB SEARCH DEBUG] ✅ Search decision: YES, performing web search")
            search_query = self._extract_search_query(messages)
            
            print(f"🔍 [WEB SEARCH DEBUG] Extracted search query: '{search_query}'")
            
            if search_query:
                # Perform search
                try:
                    print(f"🔍 [WEB SEARCH DEBUG] Starting web search...")
                    # Use resource-managed search operation
                    import concurrent.futures
                    
                    def run_managed_search():
                        # Create new event loop in this thread with proper resource management
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            async def search_operation():
                                web_search_config = self.config.get('web_search', {})
                                async with managed_search_operation(web_search_config) as resource_manager:
                                    from .search_models import SearchQuery
                                    query_obj = SearchQuery(text=search_query)
                                    return await self.search_router.search(query_obj)
                            
                            return loop.run_until_complete(search_operation())
                        finally:
                            # Properly close the loop
                            loop.close()
                    
                    # Run search in separate thread with resource management
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_managed_search)
                        search_response = future.result(timeout=30)  # 30 second timeout
                    
                    print(f"🔍 [WEB SEARCH DEBUG] Search completed. Found {len(search_response.results)} results")
                except Exception as e:
                    print(f"🔍 [WEB SEARCH DEBUG] ❌ Search error: {e}")
                    return self.base_provider.chat_completion(messages, **kwargs)
                
                if search_response.results:
                    print(f"🔍 [WEB SEARCH DEBUG] ✅ Adding {len(search_response.results)} search results to context")
                    # Add search results to the context
                    search_context = self._format_search_results(search_response.results)
                    
                    print(f"🔍 [WEB SEARCH DEBUG] Search context preview: {search_context[:200]}...")
                    
                    # Create a new message with search results
                    enhanced_messages = messages.copy()
                    
                    # Find the last user message and add search context after it
                    for i in range(len(enhanced_messages) - 1, -1, -1):
                        if enhanced_messages[i]['role'] == 'user':
                            # Insert search results as a system message after the user message
                            enhanced_messages.insert(i + 1, {
                                'role': 'system',
                                'content': f"Use the following search results to form your response:\n\n{search_context}"
                            })
                            break
                    
                    print(f"🔍 [WEB SEARCH DEBUG] ✅ Enhanced messages with search context, proceeding to AI")
                    # Use enhanced messages for the completion
                    return self.base_provider.chat_completion(enhanced_messages, **kwargs)
                else:
                    print(f"🔍 [WEB SEARCH DEBUG] ❌ No search results found")
            else:
                print(f"🔍 [WEB SEARCH DEBUG] ❌ Empty search query extracted")
        else:
            print(f"🔍 [WEB SEARCH DEBUG] ❌ Search decision: NO, proceeding without search")
                    
        # No search needed or no results, proceed normally
        print(f"🔍 [WEB SEARCH DEBUG] Proceeding with normal chat completion")
        return self.base_provider.chat_completion(messages, **kwargs)
        
    def stream_chat_completion(self, messages: list, **kwargs) -> Generator[str, None, None]:
        """
        Stream a chat completion request with optional web search
        """
        # Check if we should perform a search
        if self._should_perform_search(messages):
            search_query = self._extract_search_query(messages)
            
            if search_query:
                # Perform search
                try:
                    # Use resource-managed search operation
                    import concurrent.futures
                    
                    def run_managed_search():
                        # Create new event loop in this thread with proper resource management
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            async def search_operation():
                                web_search_config = self.config.get('web_search', {})
                                async with managed_search_operation(web_search_config) as resource_manager:
                                    from .search_models import SearchQuery
                                    query_obj = SearchQuery(text=search_query)
                                    return await self.search_router.search(query_obj)
                            
                            return loop.run_until_complete(search_operation())
                        finally:
                            # Properly close the loop
                            loop.close()
                    
                    # Run search in separate thread with resource management
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_managed_search)
                        search_response = future.result(timeout=30)  # 30 second timeout
                        
                except Exception as e:
                    print(f"Search error in streaming: {e}")
                    yield from self.base_provider.stream_chat_completion(messages, **kwargs)
                    return
                
                if search_response.results:
                    # Add search results to the context
                    search_context = self._format_search_results(search_response.results)
                    
                    # Create a new message with search results
                    enhanced_messages = messages.copy()
                    
                    # Find the last user message and add search context after it
                    for i in range(len(enhanced_messages) - 1, -1, -1):
                        if enhanced_messages[i]['role'] == 'user':
                            # Insert search results as a system message after the user message
                            enhanced_messages.insert(i + 1, {
                                'role': 'system',
                                'content': f"Use the following search results to form your response:\n\n{search_context}"
                            })
                            break
                            
                    # Use enhanced messages for the streaming completion
                    yield from self.base_provider.stream_chat_completion(enhanced_messages, **kwargs)
                    return
                    
        # No search needed or no results, proceed normally
        yield from self.base_provider.stream_chat_completion(messages, **kwargs)
        
    async def cleanup(self):
        """
        Clean up resources used by the provider
        """
        # Clean up the base provider if it has a cleanup method
        if hasattr(self.base_provider, 'cleanup') and callable(self.base_provider.cleanup):
            await self.base_provider.cleanup()
            
        # Clean up the search router
        if self.search_router:
            await self.search_router.cleanup()


def get_ai_provider_with_search(config: Dict[str, Any]) -> AIProvider:
    """
    Factory function to get an AI provider with optional web search capabilities
    
    Args:
        config: Configuration dictionary from app.config.toml
        
    Returns:
        An instance of the appropriate AI provider, potentially wrapped with web search
    """
    # Get the base AI provider
    base_provider = get_ai_provider(config)
    
    # Check if web search is enabled
    backend_config = config.get('Backend', {})
    web_search_config = backend_config.get('web_search', {})
    
    if web_search_config.get('enabled', False):
        # Initialize search router
        search_router = SearchRouter(web_search_config)
        
        # Wrap the provider with web search capabilities
        return WebSearchEnabledAIProvider(base_provider, search_router, backend_config)
    else:
        # Return the base provider without web search
        return base_provider


# Utility functions for manual search integration
async def search_web(query: str, config: Dict[str, Any]) -> List[SearchResult]:
    """
    Perform a web search manually
    
    Args:
        query: Search query
        config: Configuration dictionary
        
    Returns:
        List of search results
    """
    backend_config = config.get('Backend', {})
    web_search_config = backend_config.get('web_search', {})
    
    if not web_search_config.get('enabled', False):
        return []
    
    # Create a search router and ensure it's properly cleaned up
    search_router = None
    try:
        search_router = SearchRouter(web_search_config)
        from .search_models import SearchQuery
        query_obj = SearchQuery(text=query)
        response = await search_router.search(query_obj)
        return response.results
    except Exception as e:
        print(f"🔍 ❌ Manual search error: {e}")
        return []
    finally:
        # Clean up resources
        if search_router:
            try:
                await search_router.cleanup()
            except Exception as cleanup_error:
                print(f"🔍 ⚠️ Cleanup error: {cleanup_error}")


def format_search_results_for_prompt(results: List[SearchResult], max_results: int = 5) -> str:
    """
    Format search results for inclusion in an AI prompt
    
    Args:
        results: List of search results
        max_results: Maximum number of results to include
        
    Returns:
        Formatted string with search results
    """
    if not results:
        return "No search results found."
        
    formatted = "Web Search Results:\n\n"
    for i, result in enumerate(results[:max_results], 1):
        formatted += f"{i}. {result.title}\n"
        formatted += f"   Source: {result.source} ({result.url})\n"
        formatted += f"   Content: {result.content}\n"
        if result.timestamp:
            formatted += f"   Date: {result.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
        formatted += "\n"
        
    return formatted