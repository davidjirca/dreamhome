from redis import asyncio as aioredis
from typing import Optional, Any, Dict, List
import json
import hashlib
from datetime import datetime
from app.core.config import settings


class CacheService:
    """Redis-based caching service for search results and property data"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self._is_connected = False

    async def connect(self):
        """Initialize Redis connection"""
        if not settings.CACHE_ENABLED:
            return

        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            await self.redis.ping()
            self._is_connected = True
            print(f"✅ Connected to Redis at {settings.REDIS_URL}")
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("   Caching will be disabled")
            self._is_connected = False

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis and self._is_connected:
            await self.redis.close()
            self._is_connected = False
            print("✅ Redis connection closed")

    def is_available(self) -> bool:
        """Check if cache is available"""
        return settings.CACHE_ENABLED and self._is_connected

    def _generate_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Generate deterministic cache key from parameters

        Args:
            prefix: Key prefix (e.g., 'search', 'property')
            params: Dictionary of parameters

        Returns:
            Cache key string
        """
        # Sort and serialize parameters
        param_str = json.dumps(params, sort_keys=True, default=str)
        # Create hash for compact key
        hash_val = hashlib.md5(param_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"

    async def get_search_results(
            self,
            params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached search results

        Args:
            params: Search parameters dictionary

        Returns:
            Cached results or None if not found
        """
        if not self.is_available():
            return None

        try:
            cache_key = self._generate_cache_key("search", params)
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)
                print(f"🎯 Cache HIT for search: {cache_key[:30]}...")
                return data

            print(f"❌ Cache MISS for search: {cache_key[:30]}...")
            return None

        except Exception as e:
            print(f"⚠️  Cache get error: {e}")
            return None

    async def set_search_results(
            self,
            params: Dict[str, Any],
            results: Dict[str, Any],
            ttl: Optional[int] = None
    ):
        """
        Cache search results

        Args:
            params: Search parameters dictionary
            results: Search results to cache
            ttl: Time to live in seconds (default from settings)
        """
        if not self.is_available():
            return

        try:
            cache_key = self._generate_cache_key("search", params)
            ttl = ttl or settings.SEARCH_CACHE_TTL

            # Add cache metadata
            cache_data = {
                **results,
                "cached_at": datetime.utcnow().isoformat(),
                "cache_ttl": ttl
            }

            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, default=str)
            )

            print(f"💾 Cached search results: {cache_key[:30]}... (TTL: {ttl}s)")

        except Exception as e:
            print(f"⚠️  Cache set error: {e}")

    async def get_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached property details

        Args:
            property_id: Property UUID

        Returns:
            Cached property data or None
        """
        if not self.is_available():
            return None

        try:
            cache_key = f"property:{property_id}"
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                print(f"🎯 Cache HIT for property: {property_id}")
                return json.loads(cached_data)

            return None

        except Exception as e:
            print(f"⚠️  Cache get error: {e}")
            return None

    async def set_property(
            self,
            property_id: str,
            property_data: Dict[str, Any],
            ttl: int = 3600  # 1 hour default
    ):
        """
        Cache property details

        Args:
            property_id: Property UUID
            property_data: Property data to cache
            ttl: Time to live in seconds
        """
        if not self.is_available():
            return

        try:
            cache_key = f"property:{property_id}"
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(property_data, default=str)
            )
            print(f"💾 Cached property: {property_id}")

        except Exception as e:
            print(f"⚠️  Cache set error: {e}")

    async def invalidate_property(self, property_id: str):
        """
        Invalidate cached property data

        Args:
            property_id: Property UUID
        """
        if not self.is_available():
            return

        try:
            cache_key = f"property:{property_id}"
            deleted = await self.redis.delete(cache_key)

            if deleted:
                print(f"🗑️  Invalidated cache for property: {property_id}")

        except Exception as e:
            print(f"⚠️  Cache invalidate error: {e}")

    async def invalidate_search_cache(self):
        """
        Invalidate all search result caches
        Used when new properties are added or modified
        """
        if not self.is_available():
            return

        try:
            # Find all search cache keys
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match="search:*",
                    count=100
                )

                if keys:
                    deleted = await self.redis.delete(*keys)
                    deleted_count += deleted

                if cursor == 0:
                    break

            print(f"🗑️  Invalidated {deleted_count} search cache entries")

        except Exception as e:
            print(f"⚠️  Cache invalidate error: {e}")

    async def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get popular search queries from cache

        Args:
            limit: Number of results to return

        Returns:
            List of popular search terms with counts
        """
        if not self.is_available():
            return []

        try:
            cache_key = "popular_searches"
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)
                return data[:limit]

            return []

        except Exception as e:
            print(f"⚠️  Cache get error: {e}")
            return []

    async def set_popular_searches(
            self,
            searches: List[Dict[str, Any]],
            ttl: int = 3600  # 1 hour
    ):
        """
        Cache popular search queries

        Args:
            searches: List of search terms with counts
            ttl: Time to live in seconds
        """
        if not self.is_available():
            return

        try:
            cache_key = "popular_searches"
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(searches, default=str)
            )
            print(f"💾 Cached {len(searches)} popular searches")

        except Exception as e:
            print(f"⚠️  Cache set error: {e}")

    async def increment_search_count(self, search_text: str):
        """
        Increment counter for search term (for trending searches)

        Args:
            search_text: Search query text
        """
        if not self.is_available() or not search_text:
            return

        try:
            cache_key = f"search_count:{search_text.lower().strip()}"
            await self.redis.incr(cache_key)
            # Expire after 7 days
            await self.redis.expire(cache_key, 604800)

        except Exception as e:
            print(f"⚠️  Cache increment error: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        if not self.is_available():
            return {"enabled": False}

        try:
            info = await self.redis.info()

            # Count keys by pattern
            search_keys = 0
            property_keys = 0

            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, count=1000)
                for key in keys:
                    if key.startswith("search:"):
                        search_keys += 1
                    elif key.startswith("property:"):
                        property_keys += 1

                if cursor == 0:
                    break

            return {
                "enabled": True,
                "connected": self._is_connected,
                "total_keys": info.get("db0", {}).get("keys", 0),
                "search_cache_keys": search_keys,
                "property_cache_keys": property_keys,
                "memory_used": info.get("used_memory_human", "N/A"),
                "hit_rate": "N/A",  # Would need to track separately
            }

        except Exception as e:
            print(f"⚠️  Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}


# Global cache service instance
cache_service = CacheService()