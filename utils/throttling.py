"""
Cache-aware throttling system for API requests.
Only throttles actual API calls, not cached data retrieval.
"""

import time
import functools
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

class CacheAwareThrottler:
    """
    Throttling system that only applies delays to actual API calls,
    not cached data retrieval.
    """
    
    def __init__(self, calls_per_minute=60, calls_per_second=2):
        self.calls_per_minute = calls_per_minute
        self.calls_per_second = calls_per_second
        self.call_times = defaultdict(deque)
        self.last_call = defaultdict(float)
    
    def throttle(self, cache_check_func=None):
        """
        Decorator that throttles API calls but allows cached responses immediately.
        
        Args:
            cache_check_func: Function that returns True if data is cached
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # If we have a cache check function and data is cached, return immediately
                if cache_check_func and cache_check_func(*args, **kwargs):
                    logger.debug(f"Cache hit for {func.__name__} - returning immediately")
                    return func(*args, **kwargs)
                
                # For actual API calls, apply throttling
                provider_name = args[0].__class__.__name__ if hasattr(args[0], '__class__') else 'default'
                current_time = time.time()
                
                # Clean old call times (older than 1 minute)
                minute_ago = current_time - 60
                call_queue = self.call_times[provider_name]
                while call_queue and call_queue[0] < minute_ago:
                    call_queue.popleft()
                
                # Check per-minute limit
                if len(call_queue) >= self.calls_per_minute:
                    sleep_time = 60 - (current_time - call_queue[0])
                    if sleep_time > 0:
                        logger.info(f"Rate limit: sleeping {sleep_time:.1f}s (minute limit)")
                        time.sleep(sleep_time)
                        current_time = time.time()
                
                # Check per-second limit
                last_call_time = self.last_call[provider_name]
                time_since_last = current_time - last_call_time
                min_interval = 1.0 / self.calls_per_second
                
                if time_since_last < min_interval:
                    sleep_time = min_interval - time_since_last
                    logger.debug(f"Rate limit: sleeping {sleep_time:.1f}s (second limit)")
                    time.sleep(sleep_time)
                    current_time = time.time()
                
                # Record this call
                call_queue.append(current_time)
                self.last_call[provider_name] = current_time
                
                logger.debug(f"Making API call for {func.__name__}")
                
                # Make the actual API call
                return func(*args, **kwargs)
                
            return wrapper
        return decorator

# Global throttler instance with more aggressive limits for FMP
throttler = CacheAwareThrottler(calls_per_minute=300, calls_per_second=5)

def create_cache_checker(cache_instance, cache_key_func):
    """
    Create a cache checking function for a specific cache and key generation function.
    
    Args:
        cache_instance: The cache instance to check
        cache_key_func: Function that generates cache key from args/kwargs
        
    Returns:
        Function that checks if data is cached
    """
    def check_cache(*args, **kwargs):
        try:
            cache_key = cache_key_func(*args, **kwargs)
            # Check if the key exists in cache
            cached_value = cache_instance.get(cache_key)
            return cached_value is not None
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")
            return False
    return check_cache
