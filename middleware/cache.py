import json
import hashlib
import logging
from functools import wraps
from typing import Any, Optional, Callable
import redis
from config import Config
from utils.logging_config import get_logger
from middleware.request_logger import log_cache_operation

# Get specialized logger
logger = get_logger('cache')

class CacheManager:
    """Redis-based cache manager for API responses"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.available = True
            logger.info("Redis cache connection established")
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}")
            self.redis_client = None
            self.available = False
    
    def _generate_cache_key(self, endpoint: str, params: dict) -> str:
        """Generate a unique cache key for the request"""
        # Sort params to ensure consistent keys
        sorted_params = sorted(params.items()) if params else []
        key_string = f"{endpoint}:{json.dumps(sorted_params, sort_keys=True)}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[dict]:
        """Get cached data with logging"""
        if not self.available:
            logger.debug(f"CACHE_MISS - Key: {key} - Reason: Cache unavailable")
            return None
        
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"CACHE_HIT - Key: {key} - Size: {len(cached_data)} bytes")
                log_cache_operation('GET', key, hit=True, size=len(cached_data))
                return data
            else:
                logger.debug(f"CACHE_MISS - Key: {key} - Reason: Not found")
                log_cache_operation('GET', key, hit=False)
        except Exception as e:
            logger.error(f"CACHE_ERROR - GET - Key: {key} - Error: {e}")
            log_cache_operation('GET', key, hit=False)
        
        return None
    
    def set(self, key: str, data: dict, ttl: int) -> bool:
        """Set cached data with TTL and logging"""
        if not self.available:
            logger.debug(f"CACHE_SET_SKIP - Key: {key} - Reason: Cache unavailable")
            return False
        
        try:
            json_data = json.dumps(data)
            self.redis_client.setex(key, ttl, json_data)
            logger.debug(f"CACHE_SET - Key: {key} - TTL: {ttl}s - Size: {len(json_data)} bytes")
            log_cache_operation('SET', key, ttl=ttl, size=len(json_data))
            return True
        except Exception as e:
            logger.error(f"CACHE_ERROR - SET - Key: {key} - TTL: {ttl}s - Error: {e}")
            log_cache_operation('SET', key, ttl=ttl)
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cached data with logging"""
        if not self.available:
            logger.debug(f"CACHE_DELETE_SKIP - Key: {key} - Reason: Cache unavailable")
            return False
        
        try:
            self.redis_client.delete(key)
            logger.debug(f"CACHE_DELETE - Key: {key}")
            log_cache_operation('DELETE', key)
            return True
        except Exception as e:
            logger.error(f"CACHE_ERROR - DELETE - Key: {key} - Error: {e}")
            log_cache_operation('DELETE', key)
            return False

# Global cache manager instance
cache_manager = CacheManager()

def cache_response(ttl: int = None, endpoint_type: str = 'static'):
    """
    Decorator to cache API responses
    
    Args:
        ttl: Time to live in seconds (overrides endpoint_type)
        endpoint_type: 'static' (24h) or 'live' (5min)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determine TTL
            if ttl is not None:
                cache_ttl = ttl
            elif endpoint_type == 'live':
                cache_ttl = Config.CACHE_TTL_LIVE
            else:
                cache_ttl = Config.CACHE_TTL_STATIC
            
            # Generate cache key
            endpoint = func.__name__
            cache_key = cache_manager._generate_cache_key(endpoint, kwargs)
            
            # Try to get from cache
            cached_data = cache_manager.get(cache_key)
            if cached_data is not None:
                logger.info(f"Cache hit for {endpoint}")
                return cached_data
            
            # Execute function and cache result
            logger.info(f"Cache miss for {endpoint}, executing function")
            result = func(*args, **kwargs)
            
            # Cache the result - only cache if it's a dict (raw data), not a Flask Response
            if result and isinstance(result, dict):
                cache_manager.set(cache_key, result, cache_ttl)
                logger.info(f"Cached result for {endpoint} with TTL {cache_ttl}s")
            elif result:
                logger.debug(f"Skipping cache for {endpoint} - result is not a dict (type: {type(result).__name__})")
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str) -> bool:
    """Invalidate cache entries matching a pattern"""
    if not cache_manager.available:
        return False
    
    try:
        keys = cache_manager.redis_client.keys(pattern)
        if keys:
            cache_manager.redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries matching {pattern}")
        return True
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")
        return False
