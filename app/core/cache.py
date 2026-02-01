"""
Redis cache service.
Provides caching layer for frequently accessed data.
"""

import hashlib
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.config import settings


class CacheService:
    """
    Redis-based caching service.
    Falls back to no-op if Redis is not available.
    """

    def __init__(self):
        self._client: redis.Redis | None = None
        self._connected = False

    def connect(self) -> bool:
        """Connect to Redis server."""
        if not REDIS_AVAILABLE:
            return False

        redis_url = getattr(settings, 'REDIS_URL', None)
        if not redis_url:
            return False

        try:
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5
            )
            # Test connection
            self._client.ping()
            self._connected = True
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self._client is not None

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self.is_connected:
            return None
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300
    ) -> bool:
        """Set value in cache with TTL."""
        if not self.is_connected:
            return False
        try:
            self._client.setex(
                key,
                ttl_seconds,
                json.dumps(value, default=str)
            )
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.is_connected:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception:
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.is_connected:
            return 0
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception:
            return 0

    def clear_all(self) -> bool:
        """Clear all cache (use with caution)."""
        if not self.is_connected:
            return False
        try:
            self._client.flushdb()
            return True
        except Exception:
            return False


# Singleton instance
cache_service = CacheService()


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

    Usage:
        @cached("user", ttl_seconds=60)
        def get_user(user_id: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key
            key_suffix = key_builder(*args, **kwargs) if key_builder else cache_key(*args, **kwargs)

            full_key = f"{prefix}:{func.__name__}:{key_suffix}"

            # Try cache first
            cached_value = cache_service.get(full_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            cache_service.set(full_key, result, ttl_seconds)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Build cache key
            key_suffix = key_builder(*args, **kwargs) if key_builder else cache_key(*args, **kwargs)

            full_key = f"{prefix}:{func.__name__}:{key_suffix}"

            # Try cache first
            cached_value = cache_service.get(full_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache_service.set(full_key, result, ttl_seconds)

            return result

        # Return appropriate wrapper based on function type
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

