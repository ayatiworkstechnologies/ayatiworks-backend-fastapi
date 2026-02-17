"""
Caching service with in-memory TTL fallback.
Provides Redis caching when available, falls back to cachetools TTLCache.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from cachetools import TTLCache

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryCache:
    """
    Thread-safe in-memory TTL cache using cachetools.
    Used as fallback when Redis is not available.
    """

    def __init__(self, maxsize: int = 2048, default_ttl: int = 300):
        self._caches: dict[int, TTLCache] = {}
        self._default_ttl = default_ttl
        self._maxsize = maxsize
        # Default cache bucket
        self._caches[default_ttl] = TTLCache(maxsize=maxsize, ttl=default_ttl)

    def _get_cache(self, ttl: int) -> TTLCache:
        """Get or create a TTL-specific cache bucket."""
        if ttl not in self._caches:
            self._caches[ttl] = TTLCache(maxsize=self._maxsize, ttl=ttl)
        return self._caches[ttl]

    def get(self, key: str, ttl: int = None) -> Any | None:
        cache = self._get_cache(ttl or self._default_ttl)
        return cache.get(key)

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        cache = self._get_cache(ttl or self._default_ttl)
        cache[key] = value
        return True

    def delete(self, key: str) -> bool:
        for cache in self._caches.values():
            cache.pop(key, None)
        return True

    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching a simple prefix pattern (supports trailing *)."""
        prefix = pattern.rstrip("*")
        count = 0
        for cache in self._caches.values():
            keys_to_delete = [k for k in cache if k.startswith(prefix)]
            for k in keys_to_delete:
                cache.pop(k, None)
                count += 1
        return count

    def clear_all(self) -> bool:
        for cache in self._caches.values():
            cache.clear()
        return True


class CacheService:
    """
    Caching service with Redis primary and in-memory fallback.
    Always works — never fails silently with no caching.
    """

    def __init__(self):
        self._client: redis.Redis | None = None
        self._connected = False
        self._memory_cache = InMemoryCache(maxsize=2048, default_ttl=300)

    def connect(self) -> bool:
        """Try to connect to Redis. Falls back to in-memory cache."""
        if not REDIS_AVAILABLE:
            logger.info("Redis not installed — using in-memory cache")
            return False

        redis_url = getattr(settings, 'REDIS_URL', None)
        if not redis_url:
            logger.info("REDIS_URL not configured — using in-memory cache")
            return False

        try:
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5
            )
            self._client.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} — using in-memory cache")
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self._client is not None

    def get(self, key: str, ttl: int = 300) -> Any | None:
        """Get value from cache (Redis or memory)."""
        if self.is_connected:
            try:
                value = self._client.get(key)
                if value:
                    return json.loads(value)
                return None
            except Exception:
                pass

        # Fallback to in-memory
        return self._memory_cache.get(key, ttl)

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set value in cache with TTL (Redis or memory)."""
        if self.is_connected:
            try:
                self._client.setex(
                    key,
                    ttl_seconds,
                    json.dumps(value, default=str)
                )
                return True
            except Exception:
                pass

        # Fallback to in-memory
        return self._memory_cache.set(key, value, ttl_seconds)

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self.is_connected:
            try:
                self._client.delete(key)
            except Exception:
                pass
        return self._memory_cache.delete(key)

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        count = 0
        if self.is_connected:
            try:
                keys = self._client.keys(pattern)
                if keys:
                    count = self._client.delete(*keys)
            except Exception:
                pass
        count += self._memory_cache.delete_pattern(pattern)
        return count

    def clear_all(self) -> bool:
        """Clear all cache (use with caution)."""
        if self.is_connected:
            try:
                self._client.flushdb()
            except Exception:
                pass
        return self._memory_cache.clear_all()


# Singleton instance
cache_service = CacheService()

# Try Redis on startup, gracefully fall back to memory
cache_service.connect()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_data = f"{args}:{kwargs}"
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(
    prefix: str,
    ttl_seconds: int = 300,
    key_builder: Callable | None = None
):
    """
    Decorator to cache function results.
    Works with both Redis and in-memory cache.

    Usage:
        @cached("user", ttl_seconds=60)
        def get_user(user_id: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key_suffix = key_builder(*args, **kwargs) if key_builder else cache_key(*args, **kwargs)
            full_key = f"{prefix}:{func.__name__}:{key_suffix}"

            cached_value = cache_service.get(full_key, ttl_seconds)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            cache_service.set(full_key, result, ttl_seconds)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key_suffix = key_builder(*args, **kwargs) if key_builder else cache_key(*args, **kwargs)
            full_key = f"{prefix}:{func.__name__}:{key_suffix}"

            cached_value = cache_service.get(full_key, ttl_seconds)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            cache_service.set(full_key, result, ttl_seconds)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(prefix: str, func_name: str | None = None):
    """
    Invalidate cached data.

    Usage:
        invalidate_cache("user")  # Clear all user cache
        invalidate_cache("user", "get_user")  # Clear specific function cache
    """
    pattern = f'{prefix}:{func_name}:*' if func_name else f'{prefix}:*'
    return cache_service.delete_pattern(pattern)
