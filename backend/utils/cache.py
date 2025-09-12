"""Caching utilities"""

import json
import time
from typing import Any, Optional, Dict
from threading import Lock
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

class MemoryCache:
    """In-memory cache with TTL support"""
    
    def __init__(self, default_ttl: int = 3600):  # 1 hour default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            if time.time() > entry['expires_at']:
                del self.cache[key]
                return None
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self.lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl
            }
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        with self.lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now > entry['expires_at']
            ]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)
    
    def size(self) -> int:
        """Get current cache size"""
        with self.lock:
            return len(self.cache)

class FileCache:
    """File-based cache with TTL support"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.lock = Lock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key"""
        # Use hash to avoid filesystem issues with special characters
        import hashlib
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check TTL
            if time.time() > data['expires_at']:
                cache_path.unlink()
                return None
            
            return data['value']
        
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Error reading cache file {cache_path}: {e}")
            cache_path.unlink(missing_ok=True)
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value in file cache"""
        cache_path = self._get_cache_path(key)
        
        try:
            data = {
                'value': value,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        
        except OSError as e:
            logger.error(f"Error writing cache file {cache_path}: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete value from file cache"""
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

class CacheManager:
    """Unified cache manager"""
    
    def __init__(self, use_file_cache: bool = False, cache_dir: str = "cache"):
        if use_file_cache:
            self.cache = FileCache(cache_dir)
        else:
            self.cache = MemoryCache()
        
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = self.cache.get(key)
        if value is not None:
            self.stats['hits'] += 1
        else:
            self.stats['misses'] += 1
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        self.cache.set(key, value, ttl)
        self.stats['sets'] += 1
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        result = self.cache.delete(key)
        if result:
            self.stats['deletes'] += 1
        return result
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()
        if isinstance(self.cache, MemoryCache):
            stats['size'] = self.cache.size()
        return stats

# Global cache manager
cache_manager = CacheManager(use_file_cache=False)
