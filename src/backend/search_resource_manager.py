"""
Search Resource Manager - Centralized management of search resources
Prevents resource leaks in web search operations
"""
import asyncio
import aiohttp
import logging
import weakref
from typing import Dict, Any, Optional, Set
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class SearchResourceManager:
    """
    Centralized manager for all search-related resources
    Ensures proper cleanup and prevents resource leaks
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._session_pool: Dict[str, aiohttp.ClientSession] = {}
        self._active_sessions: Set[aiohttp.ClientSession] = set()
        self._cleanup_tasks: Set[asyncio.Task] = set()
        self._is_closed = False
        
        # Resource limits
        self.max_sessions = config.get('max_sessions', 5)
        self.session_timeout = config.get('session_timeout', 30)
        self.connector_limit = config.get('connector_limit', 100)
        
        logger.info("SearchResourceManager initialized")
    
    async def get_session(self, provider_name: str) -> aiohttp.ClientSession:
        """
        Get or create a managed aiohttp session for a provider
        
        Args:
            provider_name: Name of the search provider
            
        Returns:
            Managed aiohttp.ClientSession
        """
        if self._is_closed:
            raise RuntimeError("SearchResourceManager is closed")
        
        # Return existing session if available
        if provider_name in self._session_pool:
            session = self._session_pool[provider_name]
            if not session.closed:
                return session
            else:
                # Session was closed externally, remove from pool
                del self._session_pool[provider_name]
                self._active_sessions.discard(session)
        
        # Create new session with proper resource management
        connector = aiohttp.TCPConnector(
            limit=self.connector_limit,
            limit_per_host=20,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=self.session_timeout)
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=True
        )
        
        # Track the session
        self._session_pool[provider_name] = session
        self._active_sessions.add(session)
        
        logger.debug(f"Created new session for provider: {provider_name}")
        return session
    
    @asynccontextmanager
    async def managed_search_context(self):
        """
        Context manager for search operations that ensures cleanup
        """
        try:
            yield self
        finally:
            # Cleanup any resources created during this context
            await self._cleanup_stale_sessions()
    
    async def _cleanup_stale_sessions(self):
        """Clean up any stale or closed sessions"""
        stale_providers = []
        
        for provider_name, session in self._session_pool.items():
            if session.closed:
                stale_providers.append(provider_name)
                self._active_sessions.discard(session)
        
        for provider_name in stale_providers:
            del self._session_pool[provider_name]
            logger.debug(f"Removed stale session for provider: {provider_name}")
    
    async def close_provider_session(self, provider_name: str):
        """Close session for a specific provider"""
        if provider_name in self._session_pool:
            session = self._session_pool[provider_name]
            if not session.closed:
                await session.close()
            del self._session_pool[provider_name]
            self._active_sessions.discard(session)
            logger.debug(f"Closed session for provider: {provider_name}")
    
    async def close_all(self):
        """Close all managed resources"""
        if self._is_closed:
            return
        
        self._is_closed = True
        
        # Cancel any pending cleanup tasks
        for task in self._cleanup_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete or be cancelled
        if self._cleanup_tasks:
            await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)
        
        # Close all sessions
        close_tasks = []
        for session in list(self._active_sessions):
            if not session.closed:
                close_tasks.append(session.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Clear tracking sets
        self._session_pool.clear()
        self._active_sessions.clear()
        self._cleanup_tasks.clear()
        
        logger.info("SearchResourceManager closed all resources")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get resource usage statistics"""
        active_count = len([s for s in self._active_sessions if not s.closed])
        return {
            "active_sessions": active_count,
            "total_sessions_created": len(self._session_pool),
            "cleanup_tasks": len(self._cleanup_tasks),
            "is_closed": self._is_closed,
            "max_sessions": self.max_sessions
        }
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        if not self._is_closed and self._active_sessions:
            logger.warning(
                f"SearchResourceManager destroyed with {len(self._active_sessions)} "
                "unclosed sessions. This may indicate a resource leak."
            )


# Global resource manager instance
_global_resource_manager: Optional[SearchResourceManager] = None
_resource_manager_lock = asyncio.Lock()


async def get_global_resource_manager(config: Dict[str, Any]) -> SearchResourceManager:
    """
    Get or create the global resource manager
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Global SearchResourceManager instance
    """
    global _global_resource_manager
    
    async with _resource_manager_lock:
        if _global_resource_manager is None or _global_resource_manager._is_closed:
            _global_resource_manager = SearchResourceManager(config)
            
            # Note: atexit cleanup is problematic with asyncio
            # Instead rely on explicit cleanup or context managers
    
    return _global_resource_manager


async def _cleanup_global_manager():
    """Cleanup global resource manager"""
    global _global_resource_manager
    if _global_resource_manager and not _global_resource_manager._is_closed:
        await _global_resource_manager.close_all()


@asynccontextmanager
async def managed_search_operation(config: Dict[str, Any]):
    """
    Context manager for individual search operations
    Ensures proper resource cleanup even if operation fails
    """
    resource_manager = await get_global_resource_manager(config)
    
    async with resource_manager.managed_search_context() as manager:
        try:
            yield manager
        except Exception as e:
            logger.error(f"Search operation failed: {e}")
            raise
        finally:
            # Force cleanup of any stale resources
            await manager._cleanup_stale_sessions()


# Context manager for thread-safe search operations
class ThreadSafeSearchManager:
    """
    Thread-safe wrapper for search operations
    Handles event loop management across threads
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._loop = None
        self._resource_manager = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        # Try to get existing event loop or create new one
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        # Initialize resource manager
        self._resource_manager = await get_global_resource_manager(self.config)
        return self._resource_manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._resource_manager:
            # Cleanup stale sessions but don't close the global manager
            await self._resource_manager._cleanup_stale_sessions()
        
        # Note: We don't close the loop here as it might be shared
        # The global resource manager will handle final cleanup


def create_thread_safe_search_operation(config: Dict[str, Any]):
    """
    Create a thread-safe search operation context
    
    Args:
        config: Configuration dictionary
        
    Returns:
        ThreadSafeSearchManager instance
    """
    return ThreadSafeSearchManager(config)