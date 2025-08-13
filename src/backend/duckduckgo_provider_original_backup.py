"""
Провайдер DuckDuckGo для общего веб-поиска
"""
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any
from urllib.parse import urlencode
import re
from bs4 import BeautifulSoup
from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoProvider(SearchProvider):
    """Провайдер для поиска через DuckDuckGo"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.duckduckgo.com/")
        self.html_url = config.get("html_url", "https://html.duckduckgo.com/html/")
        self.safe_search = config.get("safe_search", "moderate")
        self.region = config.get("region", "ru-ru")
        self.session = None
        
    async def search(self, query) -> List[SearchResult]:
        """Выполнить поиск через DuckDuckGo"""
        try:
            # Обработка разных типов query
            query_obj = query
            if isinstance(query, str):
                from .search_models import SearchQuery
                query_obj = SearchQuery(text=query)
                
            # Сначала пробуем API для мгновенных ответов
            instant_results = await self._search_instant_answers(query_obj)
            
            # Если нужно больше результатов, используем HTML версию
            html_results = []
            if len(instant_results) < query_obj.max_results:
                html_results = await self._search_html(query_obj)
            
            # Объединяем результаты
            all_results = instant_results + html_results
            
            # Убираем дубликаты по URL
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    unique_results.append(result)
                    
            return unique_results[:query.max_results]
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
            
    async def _search_instant_answers(self, query) -> List[SearchResult]:
        """Поиск через API мгновенных ответов DuckDuckGo"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Обработка разных типов query
        query_text = query
        if not isinstance(query, str):
            query_text = query.text
            
        params = {
            "q": query_text,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "safe_search": self.safe_search
        }
        
        try:
            async with self.session.get(
                self.base_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"DuckDuckGo API returned status {response.status}")
                    return []
                    
                data = await response.json()
                return self._parse_instant_answer_response(data, query)
                
        except asyncio.TimeoutError:
            logger.error("DuckDuckGo API timeout")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo API error: {e}")
            return []
            
    def _parse_instant_answer_response(self, data: Dict, query: SearchQuery) -> List[SearchResult]:
        """Парсинг ответа API мгновенных ответов"""
        results = []
        
        # Abstract (основной ответ)
        if data.get("Abstract"):
            results.append(SearchResult(
                title=data.get("Heading", "DuckDuckGo Result"),
                content=data["Abstract"],
                url=data.get("AbstractURL", ""),
                source="duckduckgo",
                score=1.0,
                metadata={
                    "type": "abstract",
                    "source_name": data.get("AbstractSource", "")
                }
            ))
            
        # Answer (прямой ответ)
        if data.get("Answer"):
            results.append(SearchResult(
                title="Direct Answer",
                content=data["Answer"],
                url=data.get("AnswerType", ""),
                source="duckduckgo",
                score=0.95,
                metadata={
                    "type": "answer",
                    "answer_type": data.get("AnswerType", "")
                }
            ))
            
        # Definition
        if data.get("Definition"):
            results.append(SearchResult(
                title="Definition",
                content=data["Definition"],
                url=data.get("DefinitionURL", ""),
                source="duckduckgo",
                score=0.9,
                metadata={
                    "type": "definition",
                    "source_name": data.get("DefinitionSource", "")
                }
            ))
            
        # Related Topics
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and "Text" in topic:
                # Извлекаем заголовок из текста
                text = topic["Text"]
                title_match = re.match(r'^([^-]+)\s*-\s*(.+)$', text)
                if title_match:
                    title = title_match.group(1).strip()
                    content = title_match.group(2).strip()
                else:
                    title = text[:50] + "..." if len(text) > 50 else text
                    content = text
                    
                results.append(SearchResult(
                    title=title,
                    content=content,
                    url=topic.get("FirstURL", ""),
                    source="duckduckgo",
                    score=0.7,
                    metadata={
                        "type": "related_topic",
                        "icon": topic.get("Icon", {})
                    }
                ))
                
        return results
        
    async def _search_html(self, query) -> List[SearchResult]:
        """Поиск через HTML версию DuckDuckGo для получения больше результатов"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Обработка разных типов query
        query_text = query
        if not isinstance(query, str):
            query_text = query.text
            
        params = {
            "q": query_text,
            "s": "0",  # начальная позиция
            "dc": "20",  # количество результатов
            "kl": self.region,
            "df": ""  # временной диапазон
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            async with self.session.post(
                self.html_url,
                data=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"DuckDuckGo HTML returned status {response.status}")
                    return []
                    
                html = await response.text()
                return self._parse_html_response(html)
                
        except Exception as e:
            logger.error(f"DuckDuckGo HTML search error: {e}")
            return []
            
    def _parse_html_response(self, html: str) -> List[SearchResult]:
        """Парсинг HTML ответа DuckDuckGo"""
        results = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем результаты поиска
            for result_div in soup.find_all('div', class_='links_main'):
                try:
                    # Заголовок и URL
                    title_elem = result_div.find('a', class_='result__a')
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    
                    # Описание
                    snippet_elem = result_div.find('a', class_='result__snippet')
                    content = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Добавляем результат
                    results.append(SearchResult(
                        title=title,
                        content=content,
                        url=url,
                        source="duckduckgo",
                        score=0.6,
                        metadata={
                            "type": "web_result"
                        }
                    ))
                    
                except Exception as e:
                    logger.debug(f"Error parsing result div: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing HTML response: {e}")
            
        return results
        
    async def is_available(self) -> bool:
        """Проверить доступность DuckDuckGo API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(
                self.base_url,
                params={"q": "test", "format": "json"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"DuckDuckGo availability check failed: {e}")
            return False
            
    def get_supported_query_types(self) -> List[str]:
        """DuckDuckGo поддерживает все типы запросов"""
        return ["general", "factual", "current"]
        
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