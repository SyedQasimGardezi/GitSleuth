"""Rate limiting utilities"""

import time
from typing import Dict, Optional
from collections import defaultdict, deque
from threading import Lock
from utils.exceptions import RateLimitError
from utils.logger import get_logger

logger = get_logger(__name__)

class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket"""
        with self.lock:
            now = time.time()
            # Refill tokens based on time passed
            time_passed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class SlidingWindow:
    """Sliding window rate limiter"""
    
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = defaultdict(deque)
        self.lock = Lock()
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_size
            
            # Clean old requests
            while self.requests[key] and self.requests[key][0] <= window_start:
                self.requests[key].popleft()
            
            # Check if under limit
            if len(self.requests[key]) < self.max_requests:
                self.requests[key].append(now)
                return True
            
            return False

class RateLimiter:
    """Main rate limiter class"""
    
    def __init__(self):
        # Per-IP rate limiting
        self.ip_limiter = SlidingWindow(window_size=60, max_requests=100)  # 100 requests per minute
        
        # Per-session rate limiting
        self.session_limiter = SlidingWindow(window_size=60, max_requests=50)  # 50 requests per minute
        
        # API rate limiting (OpenAI)
        self.api_limiter = TokenBucket(capacity=100, refill_rate=1.0)  # 100 requests, refill 1 per second
        
        # Query rate limiting
        self.query_limiter = SlidingWindow(window_size=300, max_requests=20)  # 20 queries per 5 minutes
    
    def check_ip_limit(self, ip: str) -> bool:
        """Check IP-based rate limit"""
        return self.ip_limiter.is_allowed(ip)
    
    def check_session_limit(self, session_id: str) -> bool:
        """Check session-based rate limit"""
        return self.session_limiter.is_allowed(session_id)
    
    def check_api_limit(self) -> bool:
        """Check API rate limit"""
        return self.api_limiter.consume()
    
    def check_query_limit(self, session_id: str) -> bool:
        """Check query rate limit"""
        return self.query_limiter.is_allowed(session_id)
    
    def is_allowed(self, ip: str, session_id: str, is_query: bool = False) -> bool:
        """Check all applicable rate limits"""
        # Check IP limit
        if not self.check_ip_limit(ip):
            logger.warning(f"IP rate limit exceeded for {ip}")
            raise RateLimitError("Too many requests from this IP address")
        
        # Check session limit
        if not self.check_session_limit(session_id):
            logger.warning(f"Session rate limit exceeded for {session_id}")
            raise RateLimitError("Too many requests for this session")
        
        # Check query limit for queries
        if is_query and not self.check_query_limit(session_id):
            logger.warning(f"Query rate limit exceeded for {session_id}")
            raise RateLimitError("Too many queries for this session")
        
        # Check API limit
        if not self.check_api_limit():
            logger.warning("API rate limit exceeded")
            raise RateLimitError("API rate limit exceeded, please try again later")
        
        return True

# Global rate limiter instance
rate_limiter = RateLimiter()
