"""
Провайдер DuckDuckGo для общего веб-поиска с использованием LangChain
"""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from functools import partial
from datetime import datetime

from .search_providers import SearchProvider
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoProvider(SearchProvider):
    """Провайдер для поиска через DuckDuckGo с использованием LangChain"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.region = config.get("region", "ru-ru")
        self.safe_search_setting = config.get("safe_search", "moderate")
        self.max_results_setting = config.get("max_results", 10)
        self._langchain_wrapper = None
        self._executor = None
        
    def _get_langchain_wrapper(self):
        """Ленивая инициализация LangChain wrapper'а"""
        if self._langchain_wrapper is None:
            try:
                from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
                
                # Преобразуем конфигурацию для LangChain
                safesearch = self._convert_safe_search(self.safe_search_setting)
                
                self._langchain_wrapper = DuckDuckGoSearchAPIWrapper(
                    region=self.region,
                    safesearch=safesearch,
                    time=None,  # Не ограничиваем по времени
                    max_results=self.max_results_setting,
                    backend="auto"  # Используем auto вместо deprecated api
                )
                
                logger.info(f"DuckDuckGo LangChain wrapper initialized with region={self.region}, safesearch={safesearch}")
                
            except ImportError as e:
                logger.error(f"Failed to import LangChain DuckDuckGo wrapper: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize LangChain DuckDuckGo wrapper: {e}")
                raise
                
        return self._langchain_wrapper
        
    def _convert_safe_search(self, safe_search: str) -> str:
        """Конвертирует safe_search параметр в формат LangChain"""
        safe_search_mapping = {
            "strict": "strict",
            "moderate": "moderate", 
            "off": "off"
        }
        return safe_search_mapping.get(safe_search.lower(), "moderate")
        
    async def search(self, query) -> List[SearchResult]:
        """Выполнить поиск через DuckDuckGo с использованием LangChain"""
        try:
            # Обработка разных типов query
            query_obj = query
            if isinstance(query, str):
                from .search_models import SearchQuery
                query_obj = SearchQuery(text=query)
                
            if not self.validate_query(query_obj):
                return []
                
            # Выполняем поиск асинхронно
            results = await self._async_search(query_obj)
            
            # Ограничиваем количество результатов
            return results[:query_obj.max_results]
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
            
    async def _async_search(self, query: SearchQuery) -> List[SearchResult]:
        """Асинхронная обертка для синхронного LangChain API"""
        try:
            wrapper = self._get_langchain_wrapper()
            
            # Выполняем поиск в отдельном потоке
            loop = asyncio.get_event_loop()
            
            # Используем asyncio.wait_for для timeout
            search_task = loop.run_in_executor(
                self._executor,
                partial(wrapper.run, query.text)
            )
            
            raw_results = await asyncio.wait_for(search_task, timeout=self.timeout)
            
            # Конвертируем результаты в наш формат
            return self._convert_langchain_results(raw_results, query)
            
        except asyncio.TimeoutError:
            logger.error(f"DuckDuckGo search timeout after {self.timeout}s")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo async search error: {e}")
            return []
            
    def _convert_langchain_results(self, raw_results: str, query: SearchQuery) -> List[SearchResult]:
        """Конвертирует результаты LangChain в наш формат SearchResult"""
        results = []
        
        if not raw_results:
            return results
            
        try:
            logger.debug(f"Converting raw results: {raw_results}")
            
            # LangChain возвращает результаты в разных форматах
            # Попробуем несколько подходов к парсингу
            
            # Подход 1: Разбиваем по двойным переносам (параграфы)
            paragraphs = [p.strip() for p in raw_results.strip().split('\n\n') if p.strip()]
            
            if not paragraphs:
                # Подход 2: Разбиваем по одинарным переносам
                paragraphs = [p.strip() for p in raw_results.strip().split('\n') if p.strip()]
            
            for i, paragraph in enumerate(paragraphs):
                if not paragraph:
                    continue
                
                title = ""
                url = ""
                description = paragraph
                
                # Пытаемся извлечь информацию разными способами
                
                # Формат 1: [title](url) description
                markdown_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)\s*(.*)', paragraph)
                if markdown_match:
                    title = markdown_match.group(1).strip()
                    url = markdown_match.group(2).strip()
                    description = markdown_match.group(3).strip() or title
                else:
                    # Формат 2: title - description
                    dash_match = re.match(r'^([^-]+)\s*-\s*(.+)$', paragraph)
                    if dash_match:
                        title = dash_match.group(1).strip()
                        description = dash_match.group(2).strip()
                    else:
                        # Формат 3: просто текст, используем первые слова как заголовок
                        words = paragraph.split()
                        if len(words) > 5:
                            title = " ".join(words[:5]) + "..."
                            description = paragraph
                        else:
                            title = paragraph
                            description = paragraph
                
                # Убираем лишние символы и пробелы
                title = re.sub(r'\s+', ' ', title).strip()
                description = re.sub(r'\s+', ' ', description).strip()
                
                # Пропускаем слишком короткие результаты
                if len(title) < 3 and len(description) < 10:
                    continue
                
                # Создаем SearchResult
                result = SearchResult(
                    title=title or f"DuckDuckGo Result {i+1}",
                    content=description,
                    url=url,
                    source="duckduckgo",
                    score=max(0.9 - i * 0.1, 0.1),  # Убывающий score
                    timestamp=datetime.now(),
                    metadata={
                        "type": "web_result",
                        "langchain_source": True,
                        "query_type": query.query_type,
                        "position": i + 1,
                        "raw_paragraph": paragraph[:100]  # For debugging
                    }
                )
                
                results.append(result)
                
                # Ограничиваем количество результатов
                if len(results) >= query.max_results:
                    break
                    
        except Exception as e:
            logger.error(f"Error converting LangChain results: {e}")
            logger.debug(f"Raw results: {raw_results}")
            
        return results
        
    async def is_available(self) -> bool:
        """Проверить доступность DuckDuckGo через LangChain"""
        try:
            wrapper = self._get_langchain_wrapper()
            
            # Выполняем тестовый запрос
            loop = asyncio.get_event_loop()
            test_task = loop.run_in_executor(
                self._executor,
                partial(wrapper.run, "test")
            )
            
            result = await asyncio.wait_for(test_task, timeout=5)
            return bool(result)
            
        except Exception as e:
            logger.error(f"DuckDuckGo availability check failed: {e}")
            return False
            
    def get_supported_query_types(self) -> List[str]:
        """DuckDuckGo поддерживает все типы запросов"""
        return ["general", "factual", "current"]
        
    async def __aenter__(self):
        """Async context manager enter"""
        # Не нужно создавать сессию как в старой версии
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Очищаем ресурсы если нужно
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
            
    def cleanup(self):
        """Очистка ресурсов"""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None


# Для обратной совместимости - экспортируем класс под старым именем
DuckDuckGoLangChainProvider = DuckDuckGoProvider