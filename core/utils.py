"""
Utility functions untuk caching dan performance
"""
from django.core.cache import cache
from functools import wraps
from django.db.models import Model


def cache_result(timeout=300, key_prefix=''):
    """
    Decorator untuk cache function results
    
    Usage:
        @cache_result(timeout=600, key_prefix='leaderboard')
        def get_leaderboard():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f'{key_prefix}_{func.__name__}_{str(args)}_{str(kwargs)}'
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalidate cache keys matching a pattern
    Note: This is a simplified version. For production, consider using Redis with pattern matching.
    """
    # In production with Redis, you can use:
    # from django_redis import get_redis_connection
    # redis_client = get_redis_connection("default")
    # keys = redis_client.keys(f"*{pattern}*")
    # if keys:
    #     redis_client.delete(*keys)
    pass


def get_or_set_cache(key, callable_func, timeout=300):
    """
    Get value from cache or set it if not exists
    
    Args:
        key: Cache key
        callable_func: Function to call if cache miss
        timeout: Cache timeout in seconds
    
    Returns:
        Cached or computed value
    """
    value = cache.get(key)
    if value is None:
        value = callable_func()
        cache.set(key, value, timeout)
    return value

