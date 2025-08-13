"""
Провайдер RSS для новостей и актуальной информации
"""
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import feedparser
from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class RSSProvider(SearchProvider):
    """Провайдер для поиска в RSS лентах новостей"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.feeds = config.get("feeds", self._get_default_feeds())
        self.cache_duration = config.get("cache_duration", 3600)  # 1 час
        self.session = None
        self._cache = {}  # Простой in-memory кэш для RSS лент
        
    def _get_default_feeds(self) -> Dict[str, List[str]]:
        """Получить стандартные RSS ленты"""
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
        """Поиск в RSS лентах"""
        try:
            # Получаем все статьи из RSS лент
            all_articles = await self._fetch_all_feeds()
            
            # Фильтруем релевантные статьи
            relevant_articles = self._filter_relevant_articles(all_articles, query)
            
            # Конвертируем в SearchResult
            results = [
                self._article_to_result(article) 
                for article in relevant_articles[:query.max_results]
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"RSS search error: {e}")
            return []
            
    async def _fetch_all_feeds(self) -> List[Dict]:
        """Получить все статьи из RSS лент"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        all_articles = []
        tasks = []
        
        # Создаем задачи для параллельной загрузки
        for category, feed_urls in self.feeds.items():
            for feed_url in feed_urls:
                tasks.append(self._fetch_feed(feed_url, category))
                
        # Загружаем все ленты параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Объединяем результаты
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.debug(f"Feed fetch error: {result}")
                
        return all_articles
        
    async def _fetch_feed(self, feed_url: str, category: str) -> List[Dict]:
        """Загрузить и парсить одну RSS ленту"""
        # Проверяем кэш
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
                
                # Сохраняем в кэш
                self._cache[cache_key] = (articles, datetime.now())
                
                return articles
                
        except asyncio.TimeoutError:
            logger.warning(f"RSS feed timeout: {feed_url}")
            return []
        except Exception as e:
            logger.error(f"RSS feed error {feed_url}: {e}")
            return []
            
    def _parse_feed(self, content: str, feed_url: str, category: str) -> List[Dict]:
        """Парсинг RSS ленты"""
        try:
            feed = feedparser.parse(content)
            
            articles = []
            for entry in feed.entries[:50]:  # Ограничиваем количество статей
                try:
                    # Извлекаем дату публикации
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6])
                    else:
                        published = datetime.now()
                        
                    # Извлекаем контент
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
        """Очистка контента от HTML и лишних символов"""
        import re
        from html import unescape
        
        if not content:
            return ""
            
        # Удаляем HTML теги
        content = re.sub(r'<[^>]+>', '', content)
        
        # Декодируем HTML entities
        content = unescape(content)
        
        # Удаляем лишние пробелы
        content = ' '.join(content.split())
        
        # Ограничиваем длину
        if len(content) > 500:
            content = content[:500] + "..."
            
        return content.strip()
        
    def _filter_relevant_articles(self, articles: List[Dict], query: SearchQuery) -> List[Dict]:
        """Фильтр релевантных статей"""
        query_text = query.text
        keywords = query_text.lower().split() if isinstance(query_text, str) else query_text.split()
        relevant = []
        
        for article in articles:
            title_lower = article["title"].lower()
            content_lower = article["content"].lower()
            
            # Подсчет релевантности
            score = 0
            keyword_matches = 0
            
            for keyword in keywords:
                # Точное совпадение в заголовке дает больше очков
                if keyword in title_lower:
                    score += 3
                    keyword_matches += 1
                    
                # Совпадение в контенте
                if keyword in content_lower:
                    score += 1
                    keyword_matches += 1
                    
                # Проверка тегов
                for tag in article.get("tags", []):
                    if keyword in tag.lower():
                        score += 2
                        keyword_matches += 1
                        
            # Требуем совпадения хотя бы половины ключевых слов
            if keyword_matches >= len(keywords) / 2 and score > 0:
                article["relevance_score"] = score
                relevant.append(article)
                
        # Сортируем по релевантности и дате
        relevant.sort(
            key=lambda x: (
                x["relevance_score"], 
                x["published"] if x["published"] else datetime.min
            ), 
            reverse=True
        )
        
        return relevant
        
    def _article_to_result(self, article: Dict) -> SearchResult:
        """Конвертация статьи в SearchResult"""
        # Нормализуем score от 0 до 1
        max_expected_score = 10  # Примерный максимальный score
        normalized_score = min(article.get("relevance_score", 0) / max_expected_score, 1.0)
        
        # Добавляем бонус за свежесть новости
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
        """Проверить доступность хотя бы одной RSS ленты"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        # Проверяем первую ленту из каждой категории
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
        """RSS лучше всего подходит для актуальных запросов"""
        return ["current", "general"]
        
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