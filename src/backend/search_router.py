"""
Central router for web search system
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from .search_models import SearchQuery, SearchResult, SearchResponse
from .search_providers import SearchProvider
from .query_classifier import QueryClassifier
from .cache_manager import CacheManager
from .duckduckgo_provider import DuckDuckGoProvider
from .wikipedia_provider import WikipediaProvider
from .rss_provider import RSSProvider

logger = logging.getLogger(__name__)


class SearchRouter:
    """Central component for routing search queries"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.strategy = config.get("strategy", "smart_routing")
        self.default_language = config.get("default_language", "ru")
        self.max_results = config.get("max_results", 10)
        self.timeout = config.get("timeout", 30)
        
        # Initialize components
        self.classifier = QueryClassifier(config.get("classification", {}))
        self.cache_manager = CacheManager(config.get("cache", {}))
        self.providers = self._initialize_providers()
        
        # Rate limiting
        self.rate_limiting = config.get("rate_limiting", {})
        self._request_times = []
        
    def _initialize_providers(self) -> Dict[str, SearchProvider]:
        """Initialize providers"""
        providers = {}
        
        # DuckDuckGo
        if self.config.get("providers", {}).get("duckduckgo", {}).get("enabled", True):
            providers["duckduckgo"] = DuckDuckGoProvider(
                self.config["providers"]["duckduckgo"]
            )
            logger.info("DuckDuckGo provider initialized")
            
        # Wikipedia
        if self.config.get("providers", {}).get("wikipedia", {}).get("enabled", True):
            providers["wikipedia"] = WikipediaProvider(
                self.config["providers"]["wikipedia"]
            )
            logger.info("Wikipedia provider initialized")
            
        # RSS
        if self.config.get("providers", {}).get("rss", {}).get("enabled", True):
            providers["rss"] = RSSProvider(
                self.config["providers"]["rss"]
            )
            logger.info("RSS provider initialized")
            
        # Initialize mock providers if enabled
        if self.config.get("enable_mock_providers", False):
            from .mock_providers import get_mock_provider
            
            mock_types = ['statistics', 'industry_reports', 'government_data', 'academic', 'local_business']
            for mock_type in mock_types:
                try:
                    providers[mock_type] = get_mock_provider(mock_type, {})
                    logger.info(f"{mock_type} mock provider initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize {mock_type} mock provider: {e}")
            
        if not providers:
            logger.warning("No search providers enabled!")
            
        return providers
        
    async def search(self,
                    query_input,
                    query_type: Optional[str] = None,
                    max_results: Optional[int] = None,
                    language: Optional[str] = None) -> SearchResponse:
        """
        Main search method
        
        Args:
            query_input: Query text or SearchQuery object
            query_type: Query type (optional, will be determined automatically)
            max_results: Maximum number of results
            language: Search language
            
        Returns:
            SearchResponse with search results
        """
        if not self.enabled:
            if isinstance(query_input, SearchQuery):
                query = query_input
            else:
                query = SearchQuery(query_input)
                
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time=0,
                sources_used=[]
            )
            
        # Check rate limiting
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded")
            
        start_time = time.time()
        
        # Create query object if string was passed
        if isinstance(query_input, SearchQuery):
            query = query_input
            # Update parameters if explicitly passed
            if query_type is not None:
                query.query_type = query_type
            if max_results is not None:
                query.max_results = max_results
            if language is not None:
                query.language = language
        else:
            query = SearchQuery(
                text=query_input,
                query_type=query_type,
                max_results=max_results or self.max_results,
                language=language or self.default_language
            )
        
        # Check cache
        cached_result = await self.cache_manager.get(query)
        if cached_result:
            search_time = time.time() - start_time
            return SearchResponse(
                query=query,
                results=cached_result["results"],
                total_results=len(cached_result["results"]),
                search_time=search_time,
                cache_hit=True,
                sources_used=cached_result["sources"]
            )
            
        # Classify query
        classification = self.classifier.classify(query)
        query.query_type = classification["primary_type"]
        
        # Select providers
        selected_providers = await self._select_providers(classification)
        
        if not selected_providers:
            logger.warning("No providers selected for query")
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time=time.time() - start_time,
                cache_hit=False,
                sources_used=[],
                classification=classification
            )
            
        # Execute search
        provider_results = await self._execute_search(query, selected_providers)
        
        # Aggregate and rank results
        final_results = self._aggregate_results(provider_results, query)
        
        # Save to cache
        if final_results:
            await self.cache_manager.store(
                query, 
                final_results,
                list(provider_results.keys())
            )
        
        search_time = time.time() - start_time
        
        return SearchResponse(
            query=query,
            results=final_results,
            total_results=len(final_results),
            search_time=search_time,
            cache_hit=False,
            sources_used=list(provider_results.keys()),
            classification=classification
        )
        
    async def _select_providers(self, classification: Dict[str, Any]) -> List[SearchProvider]:
        """Select providers based on classification"""
        query_type = classification["primary_type"]
        confidence = classification["confidence"]
        suggested_providers = classification["suggested_providers"]
        
        selected = []
        
        # If strategy is to use all providers
        if self.strategy == "all_providers":
            return list(self.providers.values())
            
        # Smart routing strategy
        if confidence > self.config.get("classification", {}).get("confidence_threshold", 0.7):
            # Use recommended providers
            for provider_name in suggested_providers:
                if provider_name in self.providers:
                    provider = self.providers[provider_name]
                    if await provider.is_available():
                        selected.append(provider)
        else:
            # Low confidence - use more providers
            for provider in self.providers.values():
                supported_types = provider.get_supported_query_types()
                if await provider.is_available() and query_type in supported_types:
                    selected.append(provider)
                    
        # If nothing selected, use DuckDuckGo as fallback
        if not selected and "duckduckgo" in self.providers:
            selected.append(self.providers["duckduckgo"])
            
        return selected
        
    async def _execute_search(self, 
                            query: SearchQuery,
                            providers: List[SearchProvider]) -> Dict[str, List[SearchResult]]:
        """Execute search through selected providers"""
        tasks = []
        provider_names = []
        
        for provider in providers:
            tasks.append(provider.safe_search(query))
            provider_names.append(provider.name)
            
        # Execute search in parallel with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Search timeout after {self.timeout} seconds")
            results = []
            
        # Collect results
        provider_results = {}
        for i, result in enumerate(results):
            if i < len(provider_names):
                provider_name = provider_names[i]
                if isinstance(result, Exception):
                    logger.error(f"Provider {provider_name} failed: {result}")
                    provider_results[provider_name] = []
                else:
                    provider_results[provider_name] = result or []
                    logger.debug(f"Provider {provider_name} returned {len(result)} results")
                    
        return provider_results
        
    def _aggregate_results(self, 
                          provider_results: Dict[str, List[SearchResult]],
                          query: SearchQuery) -> List[SearchResult]:
        """Aggregation and ranking of results"""
        all_results = []
        
        # Collect all results
        for provider_name, results in provider_results.items():
            # Add provider information to metadata
            for result in results:
                result.metadata["provider"] = provider_name
                all_results.append(result)
                
        if not all_results:
            return []
            
        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        
        for result in all_results:
            # Normalize URL for comparison
            normalized_url = result.url.lower().rstrip('/')
            
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_results.append(result)
            elif not result.url:  # Results without URL (e.g., direct answers)
                unique_results.append(result)
                
        # Apply additional ranking
        ranked_results = self._rank_results(unique_results, query)
        
        # Limit number of results
        return ranked_results[:query.max_results]
        
    def _rank_results(self, 
                     results: List[SearchResult],
                     query: SearchQuery) -> List[SearchResult]:
        """Additional ranking of results"""
        # Simple ranking by score
        # More complex logic can be added here in the future
        
        # Bonuses for matching query type
        for result in results:
            provider = result.metadata.get("provider", "")
            
            # Bonus for Wikipedia for factual queries
            if query.query_type == "factual" and provider == "wikipedia":
                result.score *= 1.2
                
            # Bonus for RSS for current queries
            elif query.query_type == "current" and provider == "rss":
                result.score *= 1.15
                
            # Normalize score
            result.score = min(result.score, 1.0)
            
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
        
    async def _check_rate_limit(self) -> bool:
        """Check rate limiting"""
        if not self.rate_limiting.get("enabled", False):
            return True
            
        current_time = time.time()
        requests_per_minute = self.rate_limiting.get("requests_per_minute", 60)
        
        # Remove old records (older than a minute)
        self._request_times = [
            t for t in self._request_times 
            if current_time - t < 60
        ]
        
        # Check limit
        if len(self._request_times) >= requests_per_minute:
            return False
            
        # Add current request
        self._request_times.append(current_time)
        return True
        
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        
        for name, provider in self.providers.items():
            status[name] = {
                "available": await provider.is_available(),
                "info": await provider.get_provider_info()
            }
            
        return status
        
    async def health_check(self) -> Dict[str, Any]:
        """Check search system health"""
        health = {
            "enabled": self.enabled,
            "strategy": self.strategy,
            "providers": await self.get_provider_status(),
            "classifier": self.classifier.get_classification_stats(),
            "cache": await self.cache_manager.get_stats()
        }
        
        # Determine overall status
        providers_available = any(
            p["available"] for p in health["providers"].values()
        )
        
        health["status"] = "healthy" if providers_available else "unhealthy"
        
        return health
        
    async def cleanup(self):
        """Clean up resources"""
        # Close provider sessions
        for provider in self.providers.values():
            if hasattr(provider, '__aexit__'):
                await provider.__aexit__(None, None, None)
                
        # Clean up cache
        await self.cache_manager.cleanup_expired()