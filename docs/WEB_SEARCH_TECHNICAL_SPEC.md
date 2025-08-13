# Техническая спецификация системы веб-поиска

## Структуры данных

### SearchQuery - Структура поискового запроса
```python
@dataclass
class SearchQuery:
    text: str
    query_type: Optional[str] = None
    max_results: int = 10
    language: str = "ru"
    filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### SearchResult - Результат поиска
```python
@dataclass
class SearchResult:
    title: str
    content: str
    url: str
    source: str  # "duckduckgo", "wikipedia", "rss"
    score: float = 0.0
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### SearchResponse - Ответ системы поиска
```python
@dataclass
class SearchResponse:
    query: SearchQuery
    results: List[SearchResult]
    total_results: int
    search_time: float
    cache_hit: bool = False
    sources_used: List[str] = field(default_factory=list)
    classification: Optional[Dict[str, Any]] = None
```

## Интерфейсы компонентов

### 1. SearchProvider - Абстрактный базовый класс

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class SearchProvider(ABC):
    """Абстрактный базовый класс для всех поисковых провайдеров"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()
        
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Выполнить поиск по запросу"""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Проверить доступность провайдера"""
        pass
        
    @abstractmethod
    def get_supported_query_types(self) -> List[str]:
        """Получить список поддерживаемых типов запросов"""
        pass
        
    def get_provider_info(self) -> Dict[str, Any]:
        """Получить информацию о провайдере"""
        return {
            "name": self.name,
            "supported_types": self.get_supported_query_types(),
            "available": self.is_available(),
            "config": {k: v for k, v in self.config.items() 
                      if k not in ["api_key", "secret"]}
        }
```

### 2. QueryClassifier - Классификатор запросов

```python
class QueryClassifier:
    """Классифицирует запросы для выбора оптимального провайдера"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules = self._load_classification_rules()
        
    def classify(self, query: SearchQuery) -> Dict[str, Any]:
        """
        Классифицировать запрос
        
        Returns:
            {
                "primary_type": str,  # "factual", "current", "general"
                "confidence": float,  # 0.0 - 1.0
                "suggested_providers": List[str],
                "reasoning": str
            }
        """
        pass
        
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Загрузить правила классификации из конфигурации"""
        pass
        
    def _extract_temporal_markers(self, text: str) -> List[str]:
        """Извлечь временные маркеры из текста"""
        pass
        
    def _extract_named_entities(self, text: str) -> List[Dict[str, str]]:
        """Извлечь именованные сущности"""
        pass
        
    def _calculate_confidence(self, matches: Dict[str, int]) -> float:
        """Рассчитать уверенность в классификации"""
        pass
```

### 3. DuckDuckGoProvider - Провайдер DuckDuckGo

```python
class DuckDuckGoProvider(SearchProvider):
    """Провайдер для поиска через DuckDuckGo API"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://api.duckduckgo.com/")
        self.session = aiohttp.ClientSession()
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Выполнить поиск через DuckDuckGo"""
        try:
            params = self._build_params(query)
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                return self._parse_response(data, query)
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
            
    def _build_params(self, query: SearchQuery) -> Dict[str, str]:
        """Построить параметры запроса"""
        return {
            "q": query.text,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "safe_search": self.config.get("safe_search", "moderate")
        }
        
    def _parse_response(self, data: Dict, query: SearchQuery) -> List[SearchResult]:
        """Парсинг ответа DuckDuckGo"""
        results = []
        
        # Instant Answer
        if data.get("Abstract"):
            results.append(SearchResult(
                title=data.get("Heading", ""),
                content=data["Abstract"],
                url=data.get("AbstractURL", ""),
                source="duckduckgo",
                score=1.0
            ))
            
        # Related Topics
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and "Text" in topic:
                results.append(SearchResult(
                    title=topic.get("Text", "").split(" - ")[0],
                    content=topic.get("Text", ""),
                    url=topic.get("FirstURL", ""),
                    source="duckduckgo",
                    score=0.8
                ))
                
        return results[:query.max_results]
        
    def is_available(self) -> bool:
        """Проверить доступность DuckDuckGo API"""
        try:
            # Простой тестовый запрос
            import requests
            response = requests.get(self.base_url, 
                                  params={"q": "test", "format": "json"}, 
                                  timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def get_supported_query_types(self) -> List[str]:
        return ["general", "factual", "current"]
```

### 4. WikipediaProvider - Провайдер Wikipedia

```python
class WikipediaProvider(SearchProvider):
    """Провайдер для поиска в Wikipedia"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.language = config.get("language", "ru")
        self.base_url = f"https://{self.language}.wikipedia.org/api/rest_v1/"
        self.session = aiohttp.ClientSession()
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Поиск в Wikipedia"""
        try:
            # Сначала ищем статьи
            search_results = await self._search_articles(query.text)
            results = []
            
            for article in search_results[:query.max_results]:
                # Получаем содержание статьи
                content = await self._get_article_summary(article["title"])
                if content:
                    results.append(SearchResult(
                        title=article["title"],
                        content=content,
                        url=f"https://{self.language}.wikipedia.org/wiki/{article['title']}",
                        source="wikipedia",
                        score=article.get("score", 0.5)
                    ))
                    
            return results
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []
            
    async def _search_articles(self, query: str) -> List[Dict]:
        """Поиск статей в Wikipedia"""
        url = f"{self.base_url}page/title/{query}"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("items", [])
            return []
            
    async def _get_article_summary(self, title: str) -> Optional[str]:
        """Получить краткое содержание статьи"""
        url = f"{self.base_url}page/summary/{title}"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("extract", "")
            return None
            
    def is_available(self) -> bool:
        """Проверить доступность Wikipedia API"""
        try:
            import requests
            response = requests.get(f"{self.base_url}page/random/summary", timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def get_supported_query_types(self) -> List[str]:
        return ["factual", "general"]
```

### 5. RSSProvider - Провайдер RSS

```python
class RSSProvider(SearchProvider):
    """Провайдер для поиска в RSS лентах новостей"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.feeds = config.get("feeds", {})
        self.cache_duration = config.get("cache_duration", 3600)  # 1 час
        self.session = aiohttp.ClientSession()
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Поиск в RSS лентах"""
        try:
            all_articles = await self._fetch_all_feeds()
            relevant_articles = self._filter_relevant_articles(all_articles, query)
            
            return [self._article_to_result(article) for article in relevant_articles[:query.max_results]]
        except Exception as e:
            logger.error(f"RSS search error: {e}")
            return []
            
    async def _fetch_all_feeds(self) -> List[Dict]:
        """Получить все статьи из RSS лент"""
        all_articles = []
        
        for category, feed_urls in self.feeds.items():
            for feed_url in feed_urls:
                try:
                    articles = await self._parse_feed(feed_url)
                    for article in articles:
                        article["category"] = category
                    all_articles.extend(articles)
                except Exception as e:
                    logger.warning(f"Failed to parse feed {feed_url}: {e}")
                    
        return all_articles
        
    async def _parse_feed(self, feed_url: str) -> List[Dict]:
        """Парсинг RSS ленты"""
        async with self.session.get(feed_url) as response:
            if response.status != 200:
                return []
                
            content = await response.text()
            # Здесь используем feedparser для парсинга RSS
            import feedparser
            feed = feedparser.parse(content)
            
            articles = []
            for entry in feed.entries:
                articles.append({
                    "title": entry.get("title", ""),
                    "content": entry.get("summary", entry.get("description", "")),
                    "url": entry.get("link", ""),
                    "published": entry.get("published_parsed"),
                    "source": feed.feed.get("title", feed_url)
                })
                
            return articles
            
    def _filter_relevant_articles(self, articles: List[Dict], query: SearchQuery) -> List[Dict]:
        """Фильтр релевантных статей"""
        keywords = query.text.lower().split()
        relevant = []
        
        for article in articles:
            title_lower = article["title"].lower()
            content_lower = article["content"].lower()
            
            # Простой алгоритм подсчета релевантности
            score = 0
            for keyword in keywords:
                if keyword in title_lower:
                    score += 2
                if keyword in content_lower:
                    score += 1
                    
            if score > 0:
                article["relevance_score"] = score
                relevant.append(article)
                
        # Сортируем по релевантности и дате
        relevant.sort(key=lambda x: (x["relevance_score"], x.get("published", "")), reverse=True)
        return relevant
        
    def _article_to_result(self, article: Dict) -> SearchResult:
        """Конвертация статьи в SearchResult"""
        return SearchResult(
            title=article["title"],
            content=article["content"][:500] + "..." if len(article["content"]) > 500 else article["content"],
            url=article["url"],
            source="rss",
            score=article.get("relevance_score", 0) / 10.0,
            timestamp=datetime(*article["published"][:6]) if article.get("published") else None,
            metadata={
                "category": article.get("category", ""),
                "source_name": article.get("source", "")
            }
        )
        
    def is_available(self) -> bool:
        """Проверить доступность хотя бы одной RSS ленты"""
        import requests
        for category, feeds in self.feeds.items():
            for feed_url in feeds[:1]:  # Проверяем только первую ленту
                try:
                    response = requests.head(feed_url, timeout=5)
                    if response.status_code == 200:
                        return True
                except:
                    continue
        return False
        
    def get_supported_query_types(self) -> List[str]:
        return ["current", "general"]
```

### 6. SearchRouter - Маршрутизатор поиска

```python
class SearchRouter:
    """Центральный компонент для маршрутизации поисковых запросов"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.classifier = QueryClassifier(config.get("classification", {}))
        self.cache_manager = CacheManager(config.get("cache", {}))
        self.providers = self._initialize_providers()
        
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Основной метод поиска"""
        start_time = time.time()
        
        # Проверяем кэш
        cached_result = await self.cache_manager.get(query)
        if cached_result:
            return SearchResponse(
                query=query,
                results=cached_result["results"],
                total_results=len(cached_result["results"]),
                search_time=time.time() - start_time,
                cache_hit=True,
                sources_used=cached_result["sources"]
            )
            
        # Классифицируем запрос
        classification = self.classifier.classify(query)
        
        # Выбираем провайдеров
        selected_providers = self._select_providers(classification)
        
        # Выполняем поиск
        results = await self._execute_search(query, selected_providers)
        
        # Агрегируем и ранжируем результаты
        final_results = self._aggregate_results(results, query)
        
        # Сохраняем в кэш
        await self.cache_manager.store(query, final_results, 
                                     [p.name for p in selected_providers])
        
        search_time = time.time() - start_time
        
        return SearchResponse(
            query=query,
            results=final_results,
            total_results=len(final_results),
            search_time=search_time,
            cache_hit=False,
            sources_used=[p.name for p in selected_providers],
            classification=classification
        )
        
    def _initialize_providers(self) -> Dict[str, SearchProvider]:
        """Инициализация провайдеров"""
        providers = {}
        
        if self.config.get("providers", {}).get("duckduckgo", {}).get("enabled", True):
            providers["duckduckgo"] = DuckDuckGoProvider(
                self.config["providers"]["duckduckgo"]
            )
            
        if self.config.get("providers", {}).get("wikipedia", {}).get("enabled", True):
            providers["wikipedia"] = WikipediaProvider(
                self.config["providers"]["wikipedia"]
            )
            
        if self.config.get("providers", {}).get("rss", {}).get("enabled", True):
            providers["rss"] = RSSProvider(
                self.config["providers"]["rss"]
            )
            
        return providers
        
    def _select_providers(self, classification: Dict[str, Any]) -> List[SearchProvider]:
        """Выбор провайдеров на основе классификации"""
        query_type = classification["primary_type"]
        confidence = classification["confidence"]
        
        selected = []
        
        if query_type == "factual" and confidence > 0.7:
            # Для фактических запросов приоритет Wikipedia
            if "wikipedia" in self.providers:
                selected.append(self.providers["wikipedia"])
            if "duckduckgo" in self.providers:
                selected.append(self.providers["duckduckgo"])
                
        elif query_type == "current" and confidence > 0.7:
            # Для актуальных запросов приоритет RSS и DuckDuckGo
            if "rss" in self.providers:
                selected.append(self.providers["rss"])
            if "duckduckgo" in self.providers:
                selected.append(self.providers["duckduckgo"])
                
        else:
            # Для общих запросов или низкой уверенности используем все
            for provider in self.providers.values():
                if provider.is_available():
                    selected.append(provider)
                    
        return selected
        
    async def _execute_search(self, query: SearchQuery, 
                            providers: List[SearchProvider]) -> Dict[str, List[SearchResult]]:
        """Выполнение поиска через выбранных провайдеров"""
        tasks = []
        for provider in providers:
            if provider.is_available():
                tasks.append(self._safe_search(provider, query))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        provider_results = {}
        for i, result in enumerate(results):
            provider_name = providers[i].name
            if isinstance(result, Exception):
                logger.error(f"Provider {provider_name} failed: {result}")
                provider_results[provider_name] = []
            else:
                provider_results[provider_name] = result
                
        return provider_results
        
    async def _safe_search(self, provider: SearchProvider, 
                          query: SearchQuery) -> List[SearchResult]:
        """Безопасное выполнение поиска с обработкой ошибок"""
        try:
            return await provider.search(query)
        except Exception as e:
            logger.error(f"Search failed for provider {provider.name}: {e}")
            return []
            
    def _aggregate_results(self, provider_results: Dict[str, List[SearchResult]], 
                          query: SearchQuery) -> List[SearchResult]:
        """Агрегация и ранжирование результатов"""
        all_results = []
        
        for provider_name, results in provider_results.items():
            for result in results:
                # Добавляем вес источника
                source_weight = self.config.get("providers", {}).get(provider_name, {}).get("weight", 1.0)
                result.score *= source_weight
                all_results.append(result)
                
        # Удаляем дубликаты по URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
                
        # Сортируем по релевантности
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        return unique_results[:query.max_results]
```

### 7. CacheManager - Менеджер кэша

```python
class CacheManager:
    """Менеджер кэширования результатов поиска"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get("db_path", "search_cache.db")
        self.default_ttl = config.get("default_ttl", 3600)
        self._init_database()
        
    def _init_database(self):
        """Инициализация базы данных SQLite"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                query_type TEXT,
                results TEXT NOT NULL,
                sources TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()
        
    def _hash_query(self, query: SearchQuery) -> str:
        """Создание хэша для запроса"""
        import hashlib
        query_str = f"{query.text}:{query.language}:{query.max_results}"
        return hashlib.md5(query_str.encode()).hexdigest()
        
    async def get(self, query: SearchQuery) -> Optional[Dict[str, Any]]:
        """Получить результат из кэша"""
        query_hash = self._hash_query(query)
        
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT results, sources FROM search_cache 
            WHERE query_hash = ? AND expires_at > CURRENT_TIMESTAMP
        """, (query_hash,))
        
        result = cursor.fetchone()
        
        if result:
            # Обновляем счетчик доступа
            cursor.execute("""
                UPDATE search_cache 
                SET access_count = access_count + 1 
                WHERE query_hash = ?
            """, (query_hash,))
            conn.commit()
            
            import json
            cached_data = {
                "results": [SearchResult(**r) for r in json.loads(result[0])],
                "sources": json.loads(result[1])
            }
            conn.close()
            return cached_data
            
        conn.close()
        return None
        
    async def store(self, query: SearchQuery, results: List[SearchResult], 
                   sources: List[str]):
        """Сохранить результат в кэш"""
        query_hash = self._hash_query(query)
        
        # Определяем TTL на основе типа запроса
        ttl = self._get_ttl_for_query_type(query.query_type)
        
        import sqlite3
        import json
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Сериализуем результаты
        results_json = json.dumps([{
            "title": r.title,
            "content": r.content,
            "url": r.url,
            "source": r.source,
            "score": r.score,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "metadata": r.metadata
        } for r in results])
        
        sources_json = json.dumps(sources)
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        cursor.execute("""
            INSERT OR REPLACE INTO search_cache 
            (query_hash, query_text, query_type, results, sources, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query_hash, query.text, query.query_type, 
              results_json, sources_json, expires_at))
        
        conn.commit()
        conn.close()
        
    def _get_ttl_for_query_type(self, query_type: Optional[str]) -> int:
        """Получить TTL для типа запроса"""
        ttl_map = {
            "factual": 86400,  # 24 часа
            "current": 3600,   # 1 час
            "general": 21600   # 6 часов
        }
        return ttl_map.get(query_type, self.default_ttl)
        
    async def cleanup_expired(self):
        """Очистка устаревших записей"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM search_cache WHERE expires_at < CURRENT_TIMESTAMP")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} expired cache entries")
        
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(CASE WHEN expires_at > CURRENT_TIMESTAMP THEN 1 END) as active_entries,
                AVG(access_count) as avg_access_count,
                MAX(access_count) as max_access_count
            FROM search_cache
        """)
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            "total_entries": stats[0],
            "active_entries": stats[1],
            "avg_access_count": stats[2],
            "max_access_count": stats[3]
        }
```

## Конфигурационная схема

### Структура конфигурации app.config.json
```json
{
  "web_search": {
    "enabled": true,
    "default_language": "ru",
    "max_results": 10,
    "timeout": 30,
    "strategy": "smart_routing",
    
    "classification": {
      "confidence_threshold": 0.7,
      "rules_file": "classification_rules.json",
      "fallback_strategy": "all_providers"
    },
    
    "providers": {
      "duckduckgo": {
        "enabled": true,
        "weight": 0.7,
        "base_url": "https://api.duckduckgo.com/",
        "safe_search": "moderate",
        "region": "ru-ru",
        "timeout": 20
      },
      "wikipedia": {
        "enabled": true,
        "weight": 0.9,
        "language": "ru",
        "fallback_languages": ["en"],
        "max_summary_length": 1000,
        "timeout": 15
      },
      "rss": {
        "enabled": true,
        "weight": 0.8,
        "cache_duration": 3600,
        "feeds": {
          "news": [
            "https://rss.rbc.ru/rbcnews/news.rss",
            "https://tass.ru/rss/v2.xml"
          ],
          "tech": [
            "https://habr.com/ru/rss/hub/programming/"
          ]
        }
      }
    },
    
    "cache": {
      "enabled": true,
      "db_path": "data/search_cache.db",
      "default_ttl": 3600,
      "max_entries": 10000,
      "cleanup_interval": 3600
    },
    
    "rate_limiting": {
      "requests_per_minute": 60,
      "requests_per_hour": 1000,
      "burst_size": 10
    }
  }
}
```

## API интерфейсы

### Главный API для интеграции с AI Provider
```python
async def search_web(query: str, 
                    query_type: Optional[str] = None,
                    max_results: int = 10,
                    language: str = "ru") -> SearchResponse:
    """
    Главная точка входа для веб-поиска
    
    Args:
        query: Поисковый запрос
        query_type: Тип запроса (optional, будет определен автоматически)
        max_results: Максимальное количество результатов
        language: Язык поиска
        
    Returns:
        SearchResponse с результатами поиска
    """
```

### Утилитарные функции
```python
def create_search_router(config: Dict[str, Any]) -> SearchRouter:
    """Создать и настроить SearchRouter"""
    
def validate_search_config(config: Dict[str, Any]) -> bool:
    """Валидация конфигурации веб-поиска"""
    
async def health_check_providers(router: SearchRouter) -> Dict[str, bool]:
    """Проверка состояния всех провайдеров"""
    
def get_search_statistics(router: SearchRouter) -> Dict[str, Any]:
    """Получить статистику использования поиска"""
```

## Зависимости

### Основные пакеты
```txt
aiohttp>=3.8.0          # HTTP клиент для async запросов
feedparser>=6.0.0       # Парсинг RSS лент  
sqlite3                 # Встроенный, для кэша
beautifulsoup4>=4.11.0  # Парсинг HTML (опционально)
lxml>=4.9.0             # XML парсер для RSS
python-dateutil>=2.8.0  # Работа с датами
```

### Дополнительные пакеты для расширенной функциональности
```txt
spacy>=3.4.0            # NLP для классификации запросов
nltk>=3