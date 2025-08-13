"""
Extended AI Providers with integrated web search capabilities
"""
import asyncio
import re
from typing import Dict, Any, Optional, Generator, List
from .ai_providers import AIProvider, OpenAIProvider, OllamaProvider, get_ai_provider
from .search_router import SearchRouter
from .search_models import SearchResult


class WebSearchEnabledAIProvider(AIProvider):
    """AI Provider wrapper that adds web search capabilities"""
    
    def __init__(self, base_provider: AIProvider, search_router: SearchRouter, config: Dict[str, Any]):
        self.base_provider = base_provider
        self.search_router = search_router
        self.config = config
        self.search_config = config.get('ai_web_search_integration', {})
        self.enabled = self.search_config.get('enabled', True)
        self.auto_search_triggers = self.search_config.get('auto_search_triggers', [])
        self.max_search_results_in_context = self.search_config.get('max_search_results_in_context', 5)
        self.search_result_format = self.search_config.get('search_result_format', 'markdown')
        
    def _should_perform_search(self, messages: list) -> bool:
        """Determine if web search should be performed based on the conversation"""
        if not self.enabled:
            return False
            
        # Check the last user message
        if not messages:
            return False
            
        last_user_message = None
        for message in reversed(messages):
            if message['role'] == 'user':
                last_user_message = message['content']
                break
                
        if not last_user_message:
            return False
            
        # Check for explicit search triggers
        message_lower = last_user_message.lower()
        for trigger in self.auto_search_triggers:
            if trigger.lower() in message_lower:
                return True
                
        # Check for questions about current events, news, or recent information
        current_event_patterns = [
            r'\b(сегодня|вчера|на этой неделе|в этом месяце|недавно|последн[ие]е|актуальн|новост|событи[яе])\b',
            r'\b(today|yesterday|this week|this month|recently|latest|current|news|events?)\b',
            r'\b20\d{2}\b',  # Years like 2024, 2025
            r'\b(что происходит|что случилось|какие новости)\b',
            r'\b(what\'s happening|what happened|what\'s new)\b'
        ]
        
        for pattern in current_event_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
                
        # Check for factual questions that might need current information
        factual_patterns = [
            r'\b(кто|что|где|когда|почему|как|сколько)\b.*\?',
            r'\b(who|what|where|when|why|how|how much|how many)\b.*\?',
            r'\b(цена|стоимость|курс|погода|температура)\b',
            r'\b(price|cost|rate|weather|temperature)\b'
        ]
        
        for pattern in factual_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                # For factual questions, we might want to search if it seems to be about current data
                if any(word in message_lower for word in ['сейчас', 'now', 'текущ', 'current', 'сегодня', 'today']):
                    return True
                    
        return False
        
    def _extract_search_query(self, messages: list) -> str:
        """Extract the search query from the conversation"""
        # Get the last user message
        for message in reversed(messages):
            if message['role'] == 'user':
                user_query = message['content']
                
                # Remove trigger phrases to clean up the query
                cleaned_query = user_query
                for trigger in self.auto_search_triggers:
                    cleaned_query = re.sub(rf'\b{re.escape(trigger)}\b', '', cleaned_query, flags=re.IGNORECASE)
                    
                return cleaned_query.strip()
                
        return ""
        
    def _format_search_results(self, results: List[SearchResult]) -> str:
        """Format search results for inclusion in AI context"""
        if not results:
            return ""
            
        if self.search_result_format == 'markdown':
            formatted = "## Результаты веб-поиска\n\n"
            for i, result in enumerate(results[:self.max_search_results_in_context], 1):
                formatted += f"### {i}. {result.title}\n"
                formatted += f"**Источник:** {result.source} ({result.metadata.get('provider', 'unknown')})\n"
                formatted += f"**URL:** {result.url}\n"
                formatted += f"**Содержание:** {result.content}\n"
                if result.timestamp:
                    formatted += f"**Дата:** {result.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                formatted += "\n---\n\n"
            return formatted
        else:
            # Plain text format
            formatted = "Результаты веб-поиска:\n\n"
            for i, result in enumerate(results[:self.max_search_results_in_context], 1):
                formatted += f"{i}. {result.title}\n"
                formatted += f"   Источник: {result.source}\n"
                formatted += f"   {result.content}\n\n"
            return formatted
            
    def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """
        Send a chat completion request with optional web search
        """
        # Check if we should perform a search
        if self._should_perform_search(messages):
            search_query = self._extract_search_query(messages)
            
            if search_query:
                # Perform search
                try:
                    # Always use a new event loop to avoid nested loop issues
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        from .search_models import SearchQuery
                        query_obj = SearchQuery(text=search_query)
                        search_response = loop.run_until_complete(
                            self.search_router.search(query_obj)
                        )
                    finally:
                        loop.close()
                except Exception as e:
                    print(f"Search error: {e}")
                    return self.base_provider.chat_completion(messages, **kwargs)
                
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
                                'content': f"Используй следующие результаты поиска для формирования ответа:\n\n{search_context}"
                            })
                            break
                            
                    # Use enhanced messages for the completion
                    return self.base_provider.chat_completion(enhanced_messages, **kwargs)
                    
        # No search needed or no results, proceed normally
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
                    # Always use a new event loop to avoid nested loop issues
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        from .search_models import SearchQuery
                        query_obj = SearchQuery(text=search_query)
                        search_response = loop.run_until_complete(
                            self.search_router.search(query_obj)
                        )
                    finally:
                        loop.close()
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
                                'content': f"Используй следующие результаты поиска для формирования ответа:\n\n{search_context}"
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
        config: Configuration dictionary from app.config.json
        
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
    finally:
        # Clean up resources
        if search_router:
            await search_router.cleanup()


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