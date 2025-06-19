"""
Rate limiter for API calls to prevent exceeding rate limits.

This module provides the RateLimiter class to enforce API rate limits.
"""
import collections
from datetime import datetime, timedelta
import logging
import time
from threading import Lock

import config
from utils import setup_logging

# Set up logger for this module
logger = setup_logging()

class RateLimiter:
    """
    Rate limiter for API calls to prevent exceeding rate limits.
    
    This class tracks API calls and enforces rate limits by time window 
    (per minute and per day). It will block when necessary to stay within limits.
    """
    
    _instances = {}
    _lock = Lock()
    
    @classmethod
    def get_instance(cls, provider_name):
        """Get or create a rate limiter instance for a specific provider."""
        with cls._lock:
            if provider_name not in cls._instances:
                cls._instances[provider_name] = RateLimiter(provider_name)
            return cls._instances[provider_name]
    
    def __init__(self, provider_name):
        """
        Initialize a rate limiter for a specific provider.
        
        Args:
            provider_name (str): Name of the provider (must match keys in config.API_RATE_LIMITS)
        """
        self.provider_name = provider_name
        self.minute_limit = config.API_RATE_LIMITS.get(provider_name)
        self.daily_limit = config.API_DAILY_LIMITS.get(provider_name)
        
        # Call timestamps by the minute and day
        self.minute_calls = collections.deque()
        self.day_calls = collections.deque()
        self.lock = Lock()
        
    def _clean_old_calls(self):
        """Remove calls outside the current time windows."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        # Remove calls older than 1 minute
        while self.minute_calls and self.minute_calls[0] < minute_ago:
            self.minute_calls.popleft()
            
        # Remove calls older than 1 day
        while self.day_calls and self.day_calls[0] < day_ago:
            self.day_calls.popleft()
    
    def wait_if_needed(self):
        """
        Wait if necessary to stay within rate limits.
        
        Returns:
            float: Time waited in seconds
        """
        if not self.minute_limit and not self.daily_limit:
            return 0  # No limits defined
            
        with self.lock:
            self._clean_old_calls()
            now = datetime.now()
            
            # Check minute limit
            wait_time = 0
            if self.minute_limit and len(self.minute_calls) >= self.minute_limit:
                # Need to wait until oldest call is outside the 1-minute window
                oldest_call = self.minute_calls[0]
                wait_until = oldest_call + timedelta(minutes=1)
                wait_seconds = max(0, (wait_until - now).total_seconds())
                
                if wait_seconds > 0:
                    logger.info(f"Rate limit reached for {self.provider_name}. "
                               f"Waiting {wait_seconds:.2f}s to stay within {self.minute_limit} calls/minute limit.")
                    time.sleep(wait_seconds)
                    wait_time = wait_seconds
                    now = datetime.now()  # Update now after waiting
            
            # Check daily limit
            if self.daily_limit and len(self.day_calls) >= self.daily_limit:
                # Need to wait until oldest call is outside the 24-hour window
                oldest_call = self.day_calls[0]
                wait_until = oldest_call + timedelta(days=1)
                wait_seconds = max(0, (wait_until - now).total_seconds())
                
                if wait_seconds > 0:
                    logger.warning(f"Daily rate limit reached for {self.provider_name}. "
                                  f"Waiting {wait_seconds/60:.1f} minutes to stay within {self.daily_limit} calls/day limit.")
                    time.sleep(wait_seconds)
                    wait_time = max(wait_time, wait_seconds)
            
            # Record this call
            now = datetime.now()  # Update now after any waiting
            self.minute_calls.append(now)
            self.day_calls.append(now)
            
            return wait_time
            
    def __call__(self, func):
        """
        Decorator to apply rate limiting to a function.
        
        Args:
            func: Function to decorate
            
        Returns:
            Wrapped function with rate limiting
        """
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
