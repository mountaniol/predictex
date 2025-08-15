"""
Провайдер DuckDuckGo для общего веб-поиска с использованием нового пакета ddgs
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import warnings

from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)

# Suppress the deprecation warning from langchain
warnings.filterwarnings("ignore", category=RuntimeWarning, module="langchain_community.utilities.duckduckgo_search")


class DuckDuckGoProvider(SearchProvider):
    """Провайдер для поиска через DuckDuckGo"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.region = config.get("region", "ru-ru")
        self.safe_search_setting = config.get("safe_search", "moderate")
        self.max_results_setting = config.get("max_results", 10)
        self._ddgs_client = None
        
    def _get_ddgs_client(self):
        """Ленивая инициализация DDGS клиента"""
        if self._ddgs_client is None:
            try:
                # Try to use the new ddgs package directly
                try:
                    from ddgs import DDGS
                    self._ddgs_client = DDGS()
                    logger.info("Using new DDGS package directly")
                except ImportError:
                    # Fallback to duckduckgo_search if ddgs not available
                    from duckduckgo_search import DDGS
                    self._ddgs_client = DDGS()
                    logger.info("Using legacy duckduckgo_search package")
                    
            except ImportError as e:
                logger.error(f"Failed to import DuckDuckGo search package: {e}")
                # Final fallback to LangChain wrapper
                return self._get_langchain_fallback()
            except Exception as e:
                logger.error(f"Failed to initialize DDGS client: {e}")
                raise
                
        return self._ddgs_client
    
    def _get_langchain_fallback(self):
        """Fallback to LangChain wrapper if direct DDGS fails"""
        try:
            from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
            
            safesearch = self._convert_safe_search(self.safe_search_setting)
            
            wrapper = DuckDuckGoSearchAPIWrapper(
                region=self.region,
                safesearch=safesearch,
                time=None,
                max_results=self.max_results_setting,
                backend="auto"
            )
            
            logger.info("Using LangChain DuckDuckGoSearchAPIWrapper as fallback")
            return wrapper
            
        except ImportError as e:
            logger.error(f"Failed to import LangChain wrapper: {e}")
            raise
    
    def _convert_safe_search(self, safe_search: str) -> str:
        """Конвертация safe_search параметра"""
        mapping = {
            "strict": "strict",
            "moderate": "moderate", 
            "off": "off"
        }
        return mapping.get(safe_search, "moderate")
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Выполнить поиск через DuckDuckGo"""
        print(f"🦆 [DUCKDUCKGO] Starting search for: '{query.text}'")
        
        # Validate query
        if not self.validate_query(query):
            print(f"🦆 [DUCKDUCKGO] ❌ Query validation failed")
            return []
        
        try:
            # Get the search client
            client = self._get_ddgs_client()
            
            # Execute search based on client type
            if hasattr(client, 'text'):  # New DDGS API
                results = await self._search_with_ddgs(client, query)
            elif hasattr(client, 'run'):  # LangChain wrapper
                results = await self._search_with_langchain(client, query)
            else:
                logger.error("Unknown search client type")
                return []
                
            print(f"🦆 [DUCKDUCKGO] ✅ Found {len(results)} results")
            return results[:query.max_results]
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            print(f"🦆 [DUCKDUCKGO] ❌ Search error: {e}")
            return []
    
    async def _search_with_ddgs(self, client, query: SearchQuery) -> List[SearchResult]:
        """Search using direct DDGS client"""
        try:
            # Run in executor since DDGS is synchronous
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = []
                # Use text search method - ddgs.text() requires query as first positional argument
                for result in client.text(
                    query.text,  # First positional argument
                    region=self.region,
                    safesearch=self.safe_search_setting,
                    max_results=query.max_results * 2  # Get extra for filtering
                ):
                    results.append(result)
                    if len(results) >= query.max_results * 2:
                        break
                return results
            
            raw_results = await loop.run_in_executor(None, sync_search)
            
            # Convert to SearchResult objects
            search_results = []
            for result in raw_results:
                search_result = SearchResult(
                    title=result.get('title', ''),
                    content=result.get('body', result.get('snippet', '')),
                    url=result.get('href', result.get('link', '')),
                    source='duckduckgo',
                    score=0.7,  # Default score
                    timestamp=datetime.now(),
                    metadata={
                        'snippet': result.get('body', ''),
                        'source_name': 'DuckDuckGo Web Search'
                    }
                )
                search_results.append(search_result)
                
            return search_results
            
        except Exception as e:
            logger.error(f"Error in DDGS search: {e}")
            return []
    
    async def _search_with_langchain(self, wrapper, query: SearchQuery) -> List[SearchResult]:
        """Search using LangChain wrapper (fallback)"""
        try:
            loop = asyncio.get_event_loop()
            
            # Run LangChain search in executor
            raw_results = await loop.run_in_executor(
                None,
                wrapper.run,
                query.text
            )
            
            # Parse string results from LangChain
            search_results = []
            
            if isinstance(raw_results, str):
                # LangChain returns a string with snippets
                # Try to parse individual results
                import re
                snippets = re.split(r'\n\n+', raw_results)
                
                for i, snippet in enumerate(snippets[:query.max_results]):
                    if snippet.strip():
                        search_result = SearchResult(
                            title=f"Result {i+1}",
                            content=snippet.strip(),
                            url='',
                            source='duckduckgo',
                            score=0.6,
                            timestamp=datetime.now(),
                            metadata={
                                'snippet': snippet.strip(),
                                'source_name': 'DuckDuckGo (via LangChain)'
                            }
                        )
                        search_results.append(search_result)
                        
            return search_results
            
        except Exception as e:
            logger.error(f"Error in LangChain search: {e}")
            return []
            
    async def is_available(self) -> bool:
        """Проверить доступность DuckDuckGo"""
        try:
            # Try to initialize client
            client = self._get_ddgs_client()
            return client is not None
        except Exception:
            return False
            
    def get_supported_query_types(self) -> List[str]:
        """DuckDuckGo подходит для всех типов запросов"""
        return ["general", "factual", "current", "news", "technical"]