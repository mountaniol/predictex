"""
Wikipedia provider with full resource management
"""
import aiohttp
import asyncio
import logging
import ssl
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class WikipediaProvider(SearchProvider):
    """Provider for Wikipedia search with full resource management"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.language = config.get("language", "ru")
        self.fallback_languages = config.get("fallback_languages", ["en"])
        self.base_url = f"https://{self.language}.wikipedia.org/api/rest_v1/"
        self.search_url = f"https://{self.language}.wikipedia.org/w/api.php"
        self.max_summary_length = config.get("max_summary_length", 1000)
        self.include_images = config.get("include_images", False)
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search in Wikipedia with proper resource management"""
        # Create connector with proper SSL and connection settings
        connector = aiohttp.TCPConnector(
            ssl=ssl.create_default_context(),
            limit=10,  # Limit total connections
            limit_per_host=5,  # Limit per host
            ttl_dns_cache=300,  # DNS cache timeout
            enable_cleanup_closed=True,  # Enable cleanup of closed connections
            force_close=True  # Force close connections
        )
        
        # Create timeout settings
        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=5,
            sock_connect=5,
            sock_read=10
        )
        
        try:
            # Use connector in session
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                connector_owner=True  # Session owns the connector
            ) as session:
                # First search for articles
                search_results = await self._search_articles(session, query.text, query.max_results * 2)
                
                if not search_results:
                    # Try fallback languages
                    for lang in self.fallback_languages:
                        self.language = lang
                        self.base_url = f"https://{lang}.wikipedia.org/api/rest_v1/"
                        self.search_url = f"https://{lang}.wikipedia.org/w/api.php"
                        search_results = await self._search_articles(session, query.text, query.max_results * 2)
                        if search_results:
                            break
                
                results = []
                for article in search_results[:query.max_results]:
                    # Get detailed article information
                    article_data = await self._get_article_data(session, article["title"])
                    if article_data:
                        results.append(self._article_to_result(article_data, article))
                
                # Ensure all responses are read before closing
                await asyncio.sleep(0.1)  # Small delay to ensure all data is flushed
                
                return results
            
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []
        finally:
            # Explicitly close connector if it wasn't closed
            if not connector.closed:
                await connector.close()
            
    async def _search_articles(self, session: aiohttp.ClientSession, 
                              query_text: str, limit: int = 10) -> List[Dict]:
        """Search articles by query"""
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query_text,
            "srlimit": limit,
            "srprop": "snippet|titlesnippet|size|wordcount|timestamp",
            "utf8": "1"
        }
        
        try:
            async with session.get(self.search_url, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Wikipedia search API returned status {response.status}")
                    return []
                
                # Ensure we read all data
                data = await response.json()
                await response.release()  # Explicitly release the response
                return data.get("query", {}).get("search", [])
                
        except asyncio.TimeoutError:
            logger.error("Wikipedia search timeout")
            return []
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []
            
    async def _get_article_data(self, session: aiohttp.ClientSession, 
                               title: str) -> Optional[Dict]:
        """Get article data including summary"""
        # URL encode title
        encoded_title = quote(title)
        
        # Get summary
        summary_url = f"{self.base_url}page/summary/{encoded_title}"
        
        try:
            async with session.get(summary_url) as response:
                if response.status == 200:
                    summary_data = await response.json()
                    await response.release()  # Explicitly release
                    
                    # Get additional data through main API
                    extra_data = await self._get_extra_article_data(session, title)
                    
                    return {
                        "title": summary_data.get("title", title),
                        "extract": summary_data.get("extract", ""),
                        "description": summary_data.get("description", ""),
                        "thumbnail": summary_data.get("thumbnail"),
                        "timestamp": summary_data.get("timestamp"),
                        "content_urls": summary_data.get("content_urls", {}),
                        "extra": extra_data
                    }
                else:
                    logger.warning(f"Wikipedia article API returned status {response.status} for '{title}'")
                    await response.release()
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Wikipedia article '{title}': {e}")
            return None
            
    async def _get_extra_article_data(self, session: aiohttp.ClientSession, 
                                     title: str) -> Dict:
        """Get additional article data"""
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "categories|info|links",
            "inprop": "url",
            "cllimit": 10,
            "pllimit": 10
        }
        
        try:
            async with session.get(self.search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    await response.release()  # Explicitly release
                    pages = data.get("query", {}).get("pages", {})
                    
                    if pages:
                        page_data = list(pages.values())[0]
                        return {
                            "categories": [cat.get("title", "") for cat in page_data.get("categories", [])],
                            "links_count": len(page_data.get("links", [])),
                            "fullurl": page_data.get("fullurl", "")
                        }
                else:
                    await response.release()
                        
        except Exception as e:
            logger.error(f"Error fetching extra Wikipedia data: {e}")
            
        return {}
        
    def _article_to_result(self, article_data: Dict, search_data: Dict) -> SearchResult:
        """Convert article data to SearchResult"""
        title = article_data.get("title", "")
        
        # Format content
        extract = article_data.get("extract", "")
        if len(extract) > self.max_summary_length:
            extract = extract[:self.max_summary_length] + "..."
            
        # Add snippet from search if available
        snippet = search_data.get("snippet", "")
        if snippet:
            snippet = self._clean_snippet(snippet)
            if snippet not in extract:
                extract = f"{snippet}\n\n{extract}"
                
        # Article URL
        url = article_data.get("content_urls", {}).get("desktop", {}).get("page", "")
        if not url and article_data.get("extra", {}).get("fullurl"):
            url = article_data["extra"]["fullurl"]
            
        # Metadata
        metadata = {
            "description": article_data.get("description", ""),
            "timestamp": article_data.get("timestamp"),
            "word_count": search_data.get("wordcount", 0),
            "size": search_data.get("size", 0),
            "categories": article_data.get("extra", {}).get("categories", []),
            "links_count": article_data.get("extra", {}).get("links_count", 0)
        }
        
        # Add image if enabled
        if self.include_images and article_data.get("thumbnail"):
            metadata["thumbnail"] = article_data["thumbnail"]
            
        # Calculate score based on size and relevance
        base_score = 0.8
        if search_data.get("wordcount", 0) > 1000:
            base_score += 0.1
        if "titlesnippet" in search_data:  # Title contains search words
            base_score += 0.1
            
        return SearchResult(
            title=title,
            content=extract,
            url=url,
            source="wikipedia",
            score=min(base_score, 1.0),
            metadata=metadata
        )
        
    def _clean_snippet(self, snippet: str) -> str:
        """Clean snippet from HTML tags"""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', snippet)
        # Replace HTML entities
        clean = clean.replace('&quot;', '"').replace('&amp;', '&')
        clean = clean.replace('&lt;', '<').replace('&gt;', '>')
        return clean.strip()
        
    async def is_available(self) -> bool:
        """Check Wikipedia API availability"""
        connector = aiohttp.TCPConnector(
            ssl=ssl.create_default_context(),
            force_close=True
        )
        
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                connector_owner=True
            ) as session:
                async with session.get(
                    f"https://{self.language}.wikipedia.org/api/rest_v1/page/random/summary",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    result = response.status == 200
                    await response.release()
                    return result
        except Exception as e:
            logger.error(f"Wikipedia availability check failed: {e}")
            return False
        finally:
            if not connector.closed:
                await connector.close()
            
    def get_supported_query_types(self) -> List[str]:
        """Wikipedia is best suited for factual queries"""
        return ["factual", "general"]