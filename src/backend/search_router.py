"""
Центральный маршрутизатор для системы веб-поиска
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
    """Центральный компонент для маршрутизации поисковых запросов"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.strategy = config.get("strategy", "smart_routing")
        self.default_language = config.get("default_language", "ru")
        self.max_results = config.get("max_results", 10)
        self.timeout = config.get("timeout", 30)
        
        # Инициализация компонентов
        self.classifier = QueryClassifier(config.get("classification", {}))
        self.cache_manager = CacheManager(config.get("cache", {}))
        self.providers = self._initialize_providers()
        
        # Rate limiting
        self.rate_limiting = config.get("rate_limiting", {})
        self._request_times = []
        
    def _initialize_providers(self) -> Dict[str, SearchProvider]:
        """Инициализация провайдеров"""
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
            
        if not providers:
            logger.warning("No search providers enabled!")
            
        return providers
        
    async def search(self,
                    query_input,
                    query_type: Optional[str] = None,
                    max_results: Optional[int] = None,
                    language: Optional[str] = None) -> SearchResponse:
        """
        Основной метод поиска
        
        Args:
            query_input: Текст запроса или объект SearchQuery
            query_type: Тип запроса (опционально, будет определен автоматически)
            max_results: Максимальное количество результатов
            language: Язык поиска
            
        Returns:
            SearchResponse с результатами поиска
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
            
        # Проверка rate limiting
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded")
            
        start_time = time.time()
        
        # Создаем объект запроса, если передана строка
        if isinstance(query_input, SearchQuery):
            query = query_input
            # Обновляем параметры, если они переданы явно
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
        
        # Проверяем кэш
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
            
        # Классифицируем запрос
        classification = self.classifier.classify(query)
        query.query_type = classification["primary_type"]
        
        # Выбираем провайдеров
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
            
        # Выполняем поиск
        provider_results = await self._execute_search(query, selected_providers)
        
        # Агрегируем и ранжируем результаты
        final_results = self._aggregate_results(provider_results, query)
        
        # Сохраняем в кэш
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
        """Выбор провайдеров на основе классификации"""
        query_type = classification["primary_type"]
        confidence = classification["confidence"]
        suggested_providers = classification["suggested_providers"]
        
        selected = []
        
        # Если стратегия - использовать все провайдеры
        if self.strategy == "all_providers":
            return list(self.providers.values())
            
        # Smart routing стратегия
        if confidence > self.config.get("classification", {}).get("confidence_threshold", 0.7):
            # Используем рекомендованных провайдеров
            for provider_name in suggested_providers:
                if provider_name in self.providers:
                    provider = self.providers[provider_name]
                    if await provider.is_available():
                        selected.append(provider)
        else:
            # Низкая уверенность - используем больше провайдеров
            for provider in self.providers.values():
                supported_types = provider.get_supported_query_types()
                if await provider.is_available() and query_type in supported_types:
                    selected.append(provider)
                    
        # Если ничего не выбрано, используем DuckDuckGo как fallback
        if not selected and "duckduckgo" in self.providers:
            selected.append(self.providers["duckduckgo"])
            
        return selected
        
    async def _execute_search(self, 
                            query: SearchQuery,
                            providers: List[SearchProvider]) -> Dict[str, List[SearchResult]]:
        """Выполнение поиска через выбранных провайдеров"""
        tasks = []
        provider_names = []
        
        for provider in providers:
            tasks.append(provider.safe_search(query))
            provider_names.append(provider.name)
            
        # Выполняем поиск параллельно с таймаутом
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Search timeout after {self.timeout} seconds")
            results = []
            
        # Собираем результаты
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
        """Агрегация и ранжирование результатов"""
        all_results = []
        
        # Собираем все результаты
        for provider_name, results in provider_results.items():
            # Добавляем информацию о провайдере в метаданные
            for result in results:
                result.metadata["provider"] = provider_name
                all_results.append(result)
                
        if not all_results:
            return []
            
        # Удаляем дубликаты по URL
        seen_urls = set()
        unique_results = []
        
        for result in all_results:
            # Нормализуем URL для сравнения
            normalized_url = result.url.lower().rstrip('/')
            
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_results.append(result)
            elif not result.url:  # Результаты без URL (например, прямые ответы)
                unique_results.append(result)
                
        # Применяем дополнительное ранжирование
        ranked_results = self._rank_results(unique_results, query)
        
        # Ограничиваем количество результатов
        return ranked_results[:query.max_results]
        
    def _rank_results(self, 
                     results: List[SearchResult],
                     query: SearchQuery) -> List[SearchResult]:
        """Дополнительное ранжирование результатов"""
        # Простое ранжирование по score
        # В будущем здесь можно добавить более сложную логику
        
        # Бонусы за соответствие типу запроса
        for result in results:
            provider = result.metadata.get("provider", "")
            
            # Бонус за Wikipedia для фактических запросов
            if query.query_type == "factual" and provider == "wikipedia":
                result.score *= 1.2
                
            # Бонус за RSS для актуальных запросов
            elif query.query_type == "current" and provider == "rss":
                result.score *= 1.15
                
            # Нормализуем score
            result.score = min(result.score, 1.0)
            
        # Сортируем по score
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
        
    async def _check_rate_limit(self) -> bool:
        """Проверка rate limiting"""
        if not self.rate_limiting.get("enabled", False):
            return True
            
        current_time = time.time()
        requests_per_minute = self.rate_limiting.get("requests_per_minute", 60)
        
        # Удаляем старые записи (старше минуты)
        self._request_times = [
            t for t in self._request_times 
            if current_time - t < 60
        ]
        
        # Проверяем лимит
        if len(self._request_times) >= requests_per_minute:
            return False
            
        # Добавляем текущий запрос
        self._request_times.append(current_time)
        return True
        
    async def get_provider_status(self) -> Dict[str, Any]:
        """Получить статус всех провайдеров"""
        status = {}
        
        for name, provider in self.providers.items():
            status[name] = {
                "available": await provider.is_available(),
                "info": await provider.get_provider_info()
            }
            
        return status
        
    async def health_check(self) -> Dict[str, Any]:
        """Проверка состояния системы поиска"""
        health = {
            "enabled": self.enabled,
            "strategy": self.strategy,
            "providers": await self.get_provider_status(),
            "classifier": self.classifier.get_classification_stats(),
            "cache": await self.cache_manager.get_stats()
        }
        
        # Определяем общий статус
        providers_available = any(
            p["available"] for p in health["providers"].values()
        )
        
        health["status"] = "healthy" if providers_available else "unhealthy"
        
        return health
        
    async def cleanup(self):
        """Очистка ресурсов"""
        # Закрываем сессии провайдеров
        for provider in self.providers.values():
            if hasattr(provider, '__aexit__'):
                await provider.__aexit__(None, None, None)
                
        # Очистка кэша
        await self.cache_manager.cleanup_expired()