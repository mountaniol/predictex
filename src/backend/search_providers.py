"""
Базовые классы и интерфейсы для поисковых провайдеров
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class SearchProvider(ABC):
    """Абстрактный базовый класс для всех поисковых провайдеров"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()
        self.enabled = config.get("enabled", True)
        self.weight = config.get("weight", 1.0)
        self.timeout = config.get("timeout", 30)
        
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Выполнить поиск по запросу
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список результатов поиска
        """
        pass
        
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Проверить доступность провайдера
        
        Returns:
            True если провайдер доступен, False иначе
        """
        pass
        
    @abstractmethod
    def get_supported_query_types(self) -> List[str]:
        """
        Получить список поддерживаемых типов запросов
        
        Returns:
            Список типов запросов (например: ["factual", "general"])
        """
        pass
        
    async def get_provider_info(self) -> Dict[str, Any]:
        """
        Получить информацию о провайдере
        
        Returns:
            Словарь с информацией о провайдере
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
        Валидировать запрос перед выполнением
        
        Args:
            query: Поисковый запрос
            
        Returns:
            True если запрос валиден, False иначе
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
        Безопасное выполнение поиска с обработкой ошибок
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список результатов или пустой список в случае ошибки
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
            
            # Добавляем вес провайдера к оценке результатов
            for result in results:
                result.score *= self.weight
                
            return results
            
        except Exception as e:
            logger.error(f"{self.name}: Search failed with error: {e}")
            return []