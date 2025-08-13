"""
Менеджер кэширования для результатов поиска
"""
import sqlite3
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from .search_models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class CacheManager:
    """Менеджер кэширования результатов поиска"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.db_path = config.get("db_path", "data/search_cache.db")
        self.default_ttl = config.get("default_ttl", 3600)  # 1 час
        self.max_entries = config.get("max_entries", 10000)
        self.cleanup_interval = config.get("cleanup_interval", 3600)
        
        if self.enabled:
            self._init_database()
            
    def _init_database(self):
        """Инициализация базы данных SQLite"""
        # Создаем директорию если нужно
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
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
                access_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индексы для быстрого поиска
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at 
            ON search_cache(expires_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_type 
            ON search_cache(query_type)
        """)
        
        conn.commit()
        conn.close()
        
    def _hash_query(self, query: SearchQuery) -> str:
        """Создание хэша для запроса"""
        # Создаем уникальный ключ на основе параметров запроса
        query_str = f"{query.text}:{query.language}:{query.max_results}"
        if query.query_type:
            query_str += f":{query.query_type}"
        return hashlib.md5(query_str.encode()).hexdigest()
        
    async def get(self, query: SearchQuery) -> Optional[Dict[str, Any]]:
        """Получить результат из кэша"""
        if not self.enabled:
            return None
            
        query_hash = self._hash_query(query)
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT results, sources, created_at 
                FROM search_cache 
                WHERE query_hash = ? AND expires_at > datetime('now')
            """, (query_hash,))
            
            row = cursor.fetchone()
            
            if row:
                # Обновляем счетчик доступа и время последнего доступа
                cursor.execute("""
                    UPDATE search_cache 
                    SET access_count = access_count + 1,
                        last_accessed = datetime('now')
                    WHERE query_hash = ?
                """, (query_hash,))
                conn.commit()
                
                # Десериализуем результаты
                results_data = json.loads(row["results"])
                results = [SearchResult.from_dict(r) for r in results_data]
                sources = json.loads(row["sources"])
                
                logger.debug(f"Cache hit for query: {query.text[:50]}...")
                
                conn.close()
                return {
                    "results": results,
                    "sources": sources,
                    "cached_at": row["created_at"]
                }
                
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            
        conn.close()
        return None
        
    async def store(self, query: SearchQuery, results: List[SearchResult], 
                   sources: List[str]):
        """Сохранить результат в кэш"""
        if not self.enabled or not results:
            return
            
        query_hash = self._hash_query(query)
        
        # Определяем TTL на основе типа запроса
        ttl = self._get_ttl_for_query_type(query.query_type)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Сериализуем результаты
            results_json = json.dumps([r.to_dict() for r in results])
            sources_json = json.dumps(sources)
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            cursor.execute("""
                INSERT OR REPLACE INTO search_cache 
                (query_hash, query_text, query_type, results, sources, 
                 expires_at, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (query_hash, query.text, query.query_type, 
                  results_json, sources_json, expires_at))
            
            conn.commit()
            
            logger.debug(f"Cached results for query: {query.text[:50]}...")
            
            # Проверяем не превысили ли лимит записей
            await self._check_cache_size(conn)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Cache store error: {e}")
            
    def _get_ttl_for_query_type(self, query_type: Optional[str]) -> int:
        """Получить TTL для типа запроса"""
        ttl_map = {
            "factual": 86400,   # 24 часа для фактических данных
            "current": 3600,    # 1 час для текущих новостей
            "general": 21600    # 6 часов для общих запросов
        }
        return ttl_map.get(query_type, self.default_ttl)
        
    async def _check_cache_size(self, conn: sqlite3.Connection):
        """Проверка и очистка кэша при превышении лимита"""
        cursor = conn.cursor()
        
        # Проверяем количество записей
        cursor.execute("SELECT COUNT(*) FROM search_cache")
        count = cursor.fetchone()[0]
        
        if count > self.max_entries:
            # Удаляем старые и редко используемые записи
            # Оставляем 80% от максимального размера
            keep_count = int(self.max_entries * 0.8)
            
            cursor.execute("""
                DELETE FROM search_cache 
                WHERE query_hash NOT IN (
                    SELECT query_hash FROM search_cache 
                    ORDER BY last_accessed DESC, access_count DESC 
                    LIMIT ?
                )
            """, (keep_count,))
            
            deleted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cache cleanup: removed {deleted} old entries")
            
    async def cleanup_expired(self):
        """Очистка устаревших записей"""
        if not self.enabled:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM search_cache 
                WHERE expires_at < datetime('now')
            """)
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired cache entries")
                
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            
    async def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        if not self.enabled:
            return {"enabled": False}
            
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as active_entries,
                    AVG(access_count) as avg_access_count,
                    MAX(access_count) as max_access_count,
                    SUM(CASE WHEN created_at > datetime('now', '-1 hour') THEN 1 ELSE 0 END) as recent_entries
                FROM search_cache
            """)
            
            stats = dict(cursor.fetchone())
            
            # Статистика по типам запросов
            cursor.execute("""
                SELECT query_type, COUNT(*) as count
                FROM search_cache
                WHERE expires_at > datetime('now')
                GROUP BY query_type
            """)
            
            type_stats = {}
            for row in cursor.fetchall():
                query_type = row["query_type"] or "unknown"
                type_stats[query_type] = row["count"]
                
            stats["by_type"] = type_stats
            
            # Размер базы данных
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            stats["db_size_bytes"] = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "enabled": True,
                "stats": stats,
                "config": {
                    "default_ttl": self.default_ttl,
                    "max_entries": self.max_entries
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"enabled": True, "error": str(e)}
            
    async def clear_cache(self):
        """Полная очистка кэша"""
        if not self.enabled:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM search_cache")
            deleted_count = cursor.rowcount
            
            # Оптимизация базы данных после удаления
            cursor.execute("VACUUM")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cache cleared: removed {deleted_count} entries")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            
    async def invalidate_by_type(self, query_type: str):
        """Инвалидация кэша по типу запроса"""
        if not self.enabled:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM search_cache 
                WHERE query_type = ?
            """, (query_type,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Invalidated {deleted_count} cache entries for type: {query_type}")
            
        except Exception as e:
            logger.error(f"Error invalidating cache by type: {e}")