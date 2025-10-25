"""
Rate Limiter - Token bucket algorithm for rate limiting HTTP requests
"""
import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
from threading import Lock


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 10.0
    burst_size: Optional[int] = None  # Max burst, defaults to rps * 2
    per_domain: bool = True  # Separate limits per domain

    def __post_init__(self):
        if self.burst_size is None:
            self.burst_size = int(self.requests_per_second * 2)


class TokenBucket:
    """
    Token bucket algorithm for rate limiting
    Allows bursts while maintaining average rate
    """

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket
        Returns True if successful, False if insufficient tokens
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate time to wait until tokens available
        Returns seconds to wait (0 if tokens available now)
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.rate

    def _refill(self):
        """Refill bucket based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now

    def reset(self):
        """Reset bucket to full capacity"""
        with self.lock:
            self.tokens = self.capacity
            self.last_update = time.time()


class RateLimiter:
    """
    Rate limiter with per-domain token buckets
    Respects Retry-After headers from servers
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self.retry_after: Dict[str, float] = {}  # domain -> timestamp when retry allowed
        self.lock = Lock()

    def acquire(self, url: str, wait: bool = True) -> float:
        """
        Acquire permission to make request
        Returns delay in seconds (0 if immediate, >0 if must wait)

        Args:
            url: Full URL of request
            wait: If True, blocks until token available. If False, returns wait time.
        """
        domain = self._get_domain(url)

        # Check for Retry-After enforcement
        retry_until = self.retry_after.get(domain)
        if retry_until:
            now = time.time()
            if now < retry_until:
                wait_time = retry_until - now
                print(f"Rate limited on {domain} for {wait_time:.1f}s (Retry-After)")
                if wait:
                    time.sleep(wait_time)
                    return wait_time
                else:
                    return wait_time
            else:
                # Retry-After period expired
                del self.retry_after[domain]

        # Get or create token bucket for domain
        bucket = self._get_bucket(domain)

        # Try to consume token
        if bucket.consume():
            return 0.0  # Immediate

        # Calculate wait time
        wait_time = bucket.wait_time()

        if wait:
            print(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
            bucket.consume()  # Consume after waiting

        return wait_time

    def honor_retry_after(self, url: str, retry_after: float):
        """
        Set Retry-After enforcement for domain
        Args:
            url: URL of the request
            retry_after: Seconds to wait before retrying
        """
        domain = self._get_domain(url)
        retry_until = time.time() + retry_after

        with self.lock:
            self.retry_after[domain] = retry_until

        print(f"Retry-After enforced on {domain} for {retry_after}s")

    def _get_bucket(self, domain: str) -> TokenBucket:
        """Get or create token bucket for domain"""
        with self.lock:
            if domain not in self.buckets:
                self.buckets[domain] = TokenBucket(
                    rate=self.config.requests_per_second,
                    capacity=self.config.burst_size
                )
            return self.buckets[domain]

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if self.config.per_domain:
            parsed = urlparse(url)
            return parsed.netloc or 'global'
        return 'global'

    def reset(self, url: Optional[str] = None):
        """
        Reset rate limiter
        If url provided, resets only that domain. Otherwise resets all.
        """
        if url:
            domain = self._get_domain(url)
            if domain in self.buckets:
                self.buckets[domain].reset()
            if domain in self.retry_after:
                del self.retry_after[domain]
        else:
            with self.lock:
                self.buckets.clear()
                self.retry_after.clear()

    def get_stats(self, url: Optional[str] = None) -> dict:
        """
        Get rate limiting statistics
        Returns dict with current state
        """
        if url:
            domain = self._get_domain(url)
            bucket = self.buckets.get(domain)

            if bucket:
                bucket._refill()  # Update tokens before reading
                return {
                    'domain': domain,
                    'tokens_available': bucket.tokens,
                    'capacity': bucket.capacity,
                    'rate': bucket.rate,
                    'retry_after': self.retry_after.get(domain)
                }
            else:
                return {
                    'domain': domain,
                    'status': 'no_bucket_created'
                }
        else:
            # Return stats for all domains
            stats = {}
            for domain, bucket in self.buckets.items():
                bucket._refill()
                stats[domain] = {
                    'tokens_available': bucket.tokens,
                    'capacity': bucket.capacity,
                    'rate': bucket.rate,
                    'retry_after': self.retry_after.get(domain)
                }
            return stats


class AsyncRateLimiter:
    """
    Async version of rate limiter for use with asyncio
    Useful for concurrent HTTP requests
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self.retry_after: Dict[str, float] = {}
        self.lock = asyncio.Lock()

    async def acquire(self, url: str) -> float:
        """
        Async acquire permission to make request
        Returns delay in seconds that was waited
        """
        domain = self._get_domain(url)

        # Check Retry-After
        retry_until = self.retry_after.get(domain)
        if retry_until:
            now = time.time()
            if now < retry_until:
                wait_time = retry_until - now
                print(f"Rate limited on {domain} for {wait_time:.1f}s (Retry-After)")
                await asyncio.sleep(wait_time)
                return wait_time
            else:
                del self.retry_after[domain]

        # Get bucket
        bucket = await self._get_bucket(domain)

        # Try to consume
        if bucket.consume():
            return 0.0

        # Wait for tokens
        wait_time = bucket.wait_time()
        print(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
        await asyncio.sleep(wait_time)
        bucket.consume()

        return wait_time

    async def honor_retry_after(self, url: str, retry_after: float):
        """Async version of honor_retry_after"""
        domain = self._get_domain(url)
        retry_until = time.time() + retry_after

        async with self.lock:
            self.retry_after[domain] = retry_until

        print(f"Retry-After enforced on {domain} for {retry_after}s")

    async def _get_bucket(self, domain: str) -> TokenBucket:
        """Async get or create token bucket"""
        async with self.lock:
            if domain not in self.buckets:
                self.buckets[domain] = TokenBucket(
                    rate=self.config.requests_per_second,
                    capacity=self.config.burst_size
                )
            return self.buckets[domain]

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if self.config.per_domain:
            parsed = urlparse(url)
            return parsed.netloc or 'global'
        return 'global'


# Decorator for automatic rate limiting
def rate_limited(config: RateLimitConfig = None):
    """
    Decorator to add rate limiting to any function
    Usage:
        @rate_limited(RateLimitConfig(requests_per_second=5))
        def my_api_call(url):
            ...
    """
    limiter = RateLimiter(config)

    def decorator(func):
        def wrapper(url, *args, **kwargs):
            limiter.acquire(url, wait=True)
            return func(url, *args, **kwargs)
        return wrapper
    return decorator
