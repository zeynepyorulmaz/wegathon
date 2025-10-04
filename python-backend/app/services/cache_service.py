"""
Simple in-memory cache service to reduce API calls
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json
from app.core.logging import logger

class CacheService:
    """Simple in-memory cache with TTL"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = timedelta(hours=1)
    
    def _generate_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate cache key from data"""
        # Sort keys for consistent hashing
        serialized = json.dumps(data, sort_keys=True)
        hash_digest = hashlib.md5(serialized.encode()).hexdigest()
        return f"{prefix}:{hash_digest}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                # Expired, remove it
                logger.debug(f"Cache EXPIRED: {key}")
                del self._cache[key]
        
        logger.debug(f"Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Set value in cache with TTL"""
        ttl = ttl or self._default_ttl
        expiry = datetime.now() + ttl
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache SET: {key} (expires in {ttl.total_seconds()}s)")
    
    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        active_entries = sum(1 for _, expiry in self._cache.values() if expiry > now)
        
        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": len(self._cache) - active_entries
        }

# Global cache instance
_cache_service = CacheService()

def get_cache() -> CacheService:
    """Get global cache service instance"""
    return _cache_service
