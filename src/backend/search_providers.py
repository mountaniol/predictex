"""
Base classes and interfaces for search providers
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class SearchProvider(ABC):
    """Abstract base class for all search providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()
        self.enabled = config.get("enabled", True)
        self.weight = config.get("weight", 1.0)
        self.timeout = config.get("timeout", 30)
        
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Execute search for query
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        pass
        
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check provider availability
        
        Returns:
            True if provider is available, False otherwise
        """
        pass
        
    @abstractmethod
    def get_supported_query_types(self) -> List[str]:
        """
        Get list of supported query types
        
        Returns:
            List of query types (e.g.: ["factual", "general"])
        """
        pass
        
    async def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information
        
        Returns:
            Dictionary with provider information
        """
        supported_types = self.get_supported_query_types()
        return {
            "name": self.name,
            "enabled": self.enabled,
            "supported_types": supported_types,
            "available": await self.is_available(),
            "weight": self.weight,
            "timeout": self.timeout,
            "config": {k: v for k, v in self.config.items()
                      if k not in ["api_key", "secret", "password"]}
        }
        
    def validate_query(self, query: SearchQuery) -> bool:
        """
        Validate query before execution
        
        Args:
            query: Search query
            
        Returns:
            True if query is valid, False otherwise
        """
        if not query.text or not query.text.strip():
            logger.warning(f"{self.name}: Empty query text")
            return False
            
        if query.max_results <= 0:
            logger.warning(f"{self.name}: Invalid max_results: {query.max_results}")
            return False
            
        return True
        
    async def safe_search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Safe search execution with error handling
        
        Args:
            query: Search query
            
        Returns:
            List of results or empty list in case of error
        """
        try:
            if not self.enabled:
                logger.info(f"{self.name}: Provider is disabled")
                return []
                
            if not self.validate_query(query):
                return []
                
            if not await self.is_available():
                logger.warning(f"{self.name}: Provider is not available")
                return []
                
            results = await self.search(query)
            
            # Add provider weight to result scores
            for result in results:
                result.score *= self.weight
                
            return results
            
        except Exception as e:
            logger.error(f"{self.name}: Search failed with error: {e}")
            return []