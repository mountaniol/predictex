"""
Провайдер Wikipedia для энциклопедических запросов
"""
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class WikipediaProvider(SearchProvider):
    """Провайдер для поиска в Wikipedia"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.language = config.get("language", "ru")
        self.fallback_languages = config.get("fallback_languages", ["en"])
        self.base_url = f"https://{self.language}.wikipedia.org/api/rest_v1/"
        self.search_url = f"https://{self.language}.wikipedia.org/w/api.php"
        self.max_summary_length = config.get("max_summary_length", 1000)
        self.include_images = config.get("include_images", False)
        self.session = None
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Поиск в Wikipedia"""
        try:
            # Сначала ищем статьи
            search_results = await self._search_articles(query.text, query.max_results * 2)
            
            if not search_results:
                # Пробуем fallback языки
                for lang in self.fallback_languages:
                    self.language = lang
                    self.base_url = f"https://{lang}.wikipedia.org/api/rest_v1/"
                    self.search_url = f"https://{lang}.wikipedia.org/w/api.php"
                    search_results = await self._search_articles(query.text, query.max_results * 2)
                    if search_results:
                        break
            
            results = []
            for article in search_results[:query.max_results]:
                # Получаем детальную информацию о статье
                article_data = await self._get_article_data(article["title"])
                if article_data:
                    results.append(self._article_to_result(article_data, article))
                    
            return results
            
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []
            
    async def _search_articles(self, query, limit: int = 10) -> List[Dict]:
        """Поиск статей в Wikipedia"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Обработка разных типов query
        query_text = query
        if not isinstance(query, str):
            query_text = query.text
            
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
            async with self.session.get(
                self.search_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"Wikipedia search API returned status {response.status}")
                    return []
                    
                data = await response.json()
                return data.get("query", {}).get("search", [])
                
        except asyncio.TimeoutError:
            logger.error("Wikipedia search timeout")
            return []
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []
            
    async def _get_article_data(self, title: str) -> Optional[Dict]:
        """Получить данные о статье включая summary"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # URL encode title
        encoded_title = quote(title)
        
        # Получаем summary
        summary_url = f"{self.base_url}page/summary/{encoded_title}"
        
        try:
            async with self.session.get(
                summary_url,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    summary_data = await response.json()
                    
                    # Получаем дополнительные данные через основной API
                    extra_data = await self._get_extra_article_data(title)
                    
                    return {
                        **summary_data,
                        "extra": extra_data
                    }
                elif response.status == 404:
                    logger.debug(f"Article not found: {title}")
                    return None
                else:
                    logger.warning(f"Wikipedia summary API returned status {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting article data: {e}")
            return None
            
    async def _get_extra_article_data(self, title: str) -> Dict:
        """Получить дополнительные данные о статье"""
        params = {
            "action": "query",
            "format": "json",
            "prop": "info|categories|links",
            "inprop": "url",
            "titles": title,
            "cllimit": "10",
            "pllimit": "10"
        }
        
        try:
            async with self.session.get(
                self.search_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    pages = data.get("query", {}).get("pages", {})
                    if pages:
                        page_data = list(pages.values())[0]
                        return {
                            "categories": [
                                cat["title"].replace("Категория:", "").strip()
                                for cat in page_data.get("categories", [])
                            ],
                            "links_count": len(page_data.get("links", [])),
                            "full_url": page_data.get("fullurl", "")
                        }
                        
        except Exception as e:
            logger.debug(f"Error getting extra data: {e}")
            
        return {}
        
    def _article_to_result(self, article_data: Dict, search_data: Dict) -> SearchResult:
        """Конвертация данных статьи в SearchResult"""
        # Извлекаем основные данные
        title = article_data.get("title", search_data.get("title", ""))
        
        # Формируем контент
        extract = article_data.get("extract", "")
        if len(extract) > self.max_summary_length:
            extract = extract[:self.max_summary_length] + "..."
            
        # Добавляем snippet из поиска если extract пустой
        if not extract and search_data.get("snippet"):
            extract = self._clean_snippet(search_data["snippet"])
            
        # URL
        url = article_data.get("content_urls", {}).get("desktop", {}).get("page", "")
        if not url and article_data.get("extra", {}).get("full_url"):
            url = article_data["extra"]["full_url"]
        if not url:
            url = f"https://{self.language}.wikipedia.org/wiki/{quote(title)}"
            
        # Метаданные
        metadata = {
            "type": article_data.get("type", "standard"),
            "language": self.language,
            "page_id": article_data.get("pageid", search_data.get("pageid")),
            "size": search_data.get("size", 0),
            "wordcount": search_data.get("wordcount", 0),
            "timestamp": search_data.get("timestamp", ""),
            "categories": article_data.get("extra", {}).get("categories", []),
            "links_count": article_data.get("extra", {}).get("links_count", 0)
        }
        
        # Добавляем изображение если включено
        if self.include_images and article_data.get("thumbnail"):
            metadata["thumbnail"] = article_data["thumbnail"]
            
        # Рассчитываем score на основе размера и соответствия
        base_score = 0.8
        if search_data.get("wordcount", 0) > 1000:
            base_score += 0.1
        if "titlesnippet" in search_data:  # Заголовок содержит искомые слова
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
        """Очистка snippet от HTML тегов"""
        import re
        # Удаляем HTML теги
        clean = re.sub(r'<[^>]+>', '', snippet)
        # Заменяем HTML entities
        clean = clean.replace('&quot;', '"').replace('&amp;', '&')
        clean = clean.replace('&lt;', '<').replace('&gt;', '>')
        return clean.strip()
        
    async def is_available(self) -> bool:
        """Проверить доступность Wikipedia API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # Проверяем доступность API через простой запрос
            async with self.session.get(
                f"https://{self.language}.wikipedia.org/api/rest_v1/page/random/summary",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Wikipedia availability check failed: {e}")
            return False
            
    def get_supported_query_types(self) -> List[str]:
        """Wikipedia лучше всего подходит для фактических запросов"""
        return ["factual", "general"]
        
    async def __aenter__(self):
        """Async context manager enter"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None