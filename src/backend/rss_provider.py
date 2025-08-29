"""
RSS provider for news and current information
"""
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import feedparser
from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult
from .search_resource_manager import get_global_resource_manager

logger = logging.getLogger(__name__)


class RSSProvider(SearchProvider):
    """Provider for searching in RSS news feeds"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.feeds = config.get("feeds", self._get_default_feeds())
        self.cache_duration = config.get("cache_duration", 3600)  # 1 hour
        self.session = None
        self._cache = {}  # Simple in-memory cache for RSS feeds
        self._resource_manager: Optional[Any] = None
        
    def _get_default_feeds(self) -> Dict[str, List[str]]:
        """Get default RSS feeds"""
        return {
            "news": [
                "https://rss.rbc.ru/rbcnews/news.rss",
                "https://tass.ru/rss/v2.xml",
                "https://www.interfax.ru/rss.asp"
            ],
            "tech": [
                "https://habr.com/ru/rss/hub/programming/all/",
                "https://www.cnews.ru/inc/rss/news.xml"
            ],
            "international": [
                "https://www.bbc.com/russian/news/rss.xml",
                "https://russian.rt.com/rss"
            ],
            "business": [
                "https://www.vedomosti.ru/rss/news",
                "https://www.kommersant.ru/RSS/news.xml"
            ]
        }
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search in RSS feeds"""
        try:
            # Get all articles from RSS feeds
            all_articles = await self._fetch_all_feeds()
            
            # Filter relevant articles
            relevant_articles = self._filter_relevant_articles(all_articles, query)
            
            # Convert to SearchResult
            results = [
                self._article_to_result(article) 
                for article in relevant_articles[:query.max_results]
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"RSS search error: {e}")
            return []
            
    async def _fetch_all_feeds(self) -> List[Dict]:
        """Get all articles from RSS feeds"""
        if not self._resource_manager:
            self._resource_manager = await get_global_resource_manager(self.config)
        
        if not self.session:
            self.session = await self._resource_manager.get_session("rss")
            
        all_articles = []
        tasks = []
        
        # Create tasks for parallel loading
        for category, feed_urls in self.feeds.items():
            for feed_url in feed_urls:
                tasks.append(self._fetch_feed(feed_url, category))
                
        # Load all feeds in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.debug(f"Feed fetch error: {result}")
                
        return all_articles
        
    async def _fetch_feed(self, feed_url: str, category: str) -> List[Dict]:
        """Load and parse one RSS feed"""
        # Check cache
        cache_key = f"{feed_url}:{category}"
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_duration:
                return cached_data
                
        try:
            async with self.session.get(
                feed_url,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"RSS feed {feed_url} returned status {response.status}")
                    return []
                    
                content = await response.text()
                articles = self._parse_feed(content, feed_url, category)
                
                # Save to cache
                self._cache[cache_key] = (articles, datetime.now())
                
                return articles
                
        except asyncio.TimeoutError:
            logger.warning(f"RSS feed timeout: {feed_url}")
            return []
        except Exception as e:
            logger.error(f"RSS feed error {feed_url}: {e}")
            return []
            
    def _parse_feed(self, content: str, feed_url: str, category: str) -> List[Dict]:
        """Parse RSS feed"""
        try:
            feed = feedparser.parse(content)
            
            articles = []
            for entry in feed.entries[:50]:  # Limit number of articles
                try:
                    # Extract publication date
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6])
                    else:
                        published = datetime.now()
                        
                    # Extract content
                    content = ""
                    if hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                        
                    articles.append({
                        "title": entry.get('title', 'No title'),
                        "content": self._clean_content(content),
                        "url": entry.get('link', ''),
                        "published": published,
                        "source": feed.feed.get('title', feed_url),
                        "category": category,
                        "tags": [tag.term for tag in entry.get('tags', [])][:5]
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing entry: {e}")
                    continue
                    
            return articles
            
        except Exception as e:
            logger.error(f"Feed parsing error: {e}")
            return []
            
    def _clean_content(self, content: str) -> str:
        """Clean content from HTML and extra characters"""
        import re
        from html import unescape
        
        if not content:
            return ""
            
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Decode HTML entities
        content = unescape(content)
        
        # Remove extra spaces
        content = ' '.join(content.split())
        
        # Limit length
        if len(content) > 500:
            content = content[:500] + "..."
            
        return content.strip()
        
    def _filter_relevant_articles(self, articles: List[Dict], query: SearchQuery) -> List[Dict]:
        """Filter relevant articles"""
        query_text = query.text
        keywords = query_text.lower().split() if isinstance(query_text, str) else query_text.split()
        relevant = []
        
        for article in articles:
            title_lower = article["title"].lower()
            content_lower = article["content"].lower()
            
            # Calculate relevance
            score = 0
            keyword_matches = 0
            
            for keyword in keywords:
                # Exact match in title gives more points
                if keyword in title_lower:
                    score += 3
                    keyword_matches += 1
                    
                # Match in content
                if keyword in content_lower:
                    score += 1
                    keyword_matches += 1
                    
                # Check tags
                for tag in article.get("tags", []):
                    if keyword in tag.lower():
                        score += 2
                        keyword_matches += 1
                        
            # Require at least half of keywords to match
            if keyword_matches >= len(keywords) / 2 and score > 0:
                article["relevance_score"] = score
                relevant.append(article)
                
        # Sort by relevance and date
        relevant.sort(
            key=lambda x: (
                x["relevance_score"], 
                x["published"] if x["published"] else datetime.min
            ), 
            reverse=True
        )
        
        return relevant
        
    def _article_to_result(self, article: Dict) -> SearchResult:
        """Convert article to SearchResult"""
        # Normalize score from 0 to 1
        max_expected_score = 10  # Approximate maximum score
        normalized_score = min(article.get("relevance_score", 0) / max_expected_score, 1.0)
        
        # Add bonus for news freshness
        if article.get("published"):
            days_old = (datetime.now() - article["published"]).days
            if days_old == 0:
                normalized_score = min(normalized_score + 0.2, 1.0)
            elif days_old <= 3:
                normalized_score = min(normalized_score + 0.1, 1.0)
                
        metadata = {
            "category": article.get("category", ""),
            "source_name": article.get("source", ""),
            "tags": article.get("tags", []),
            "published_date": article["published"].isoformat() if article.get("published") else None
        }
        
        return SearchResult(
            title=article["title"],
            content=article["content"],
            url=article["url"],
            source="rss",
            score=normalized_score,
            timestamp=article.get("published"),
            metadata=metadata
        )
        
    async def is_available(self) -> bool:
        """Check availability of at least one RSS feed"""
        if not self._resource_manager:
            self._resource_manager = await get_global_resource_manager(self.config)
        
        if not self.session:
            self.session = await self._resource_manager.get_session("rss")
            
        # Check first feed from each category
        for category, feeds in self.feeds.items():
            if feeds:
                try:
                    async with self.session.head(
                        feeds[0],
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status in [200, 301, 302]:
                            return True
                except Exception as e:
                    logger.debug(f"RSS availability check failed for {feeds[0]}: {e}")
                    continue
                    
        return False
        
    def get_supported_query_types(self) -> List[str]:
        """RSS is best suited for current queries"""
        return ["current", "general"]
        
    async def __aenter__(self):
        """Async context manager enter"""
        if not self._resource_manager:
            self._resource_manager = await get_global_resource_manager(self.config)
        
        if not self.session:
            self.session = await self._resource_manager.get_session("rss")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Don't close the session directly - let resource manager handle it
        # This prevents premature closure of shared sessions
        self.session = None