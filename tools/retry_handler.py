"""
Retry Handler - Exponential backoff with jitter for HTTP requests
"""
import time
import random
from typing import Callable, Any, Optional
from dataclasses import dataclass
import httpx


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_status: list[int] = None

    def __post_init__(self):
        if self.retry_on_status is None:
            # Retry on server errors and rate limiting
            self.retry_on_status = [429, 500, 502, 503, 504]


@dataclass
class RetryResult:
    """Result of retry operation"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    attempts: int = 0
    total_time: float = 0.0
    retry_delays: list[float] = None

    def __post_init__(self):
        if self.retry_delays is None:
            self.retry_delays = []


class RetryHandler:
    """
    Handle retries with exponential backoff and jitter
    Prevents thundering herd problem with randomized delays
    """

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> RetryResult:
        """
        Execute function with retry logic
        Returns RetryResult with success status and result/error
        """
        start_time = time.time()
        attempts = 0
        retry_delays = []
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            attempts += 1

            try:
                result = func(*args, **kwargs)

                # Check if result is an httpx.Response that should be retried
                if isinstance(result, httpx.Response):
                    if not self.should_retry_response(result):
                        # Success!
                        return RetryResult(
                            success=True,
                            result=result,
                            attempts=attempts,
                            total_time=time.time() - start_time,
                            retry_delays=retry_delays
                        )
                    else:
                        # Response indicates retry needed
                        last_error = Exception(f"HTTP {result.status_code}: {result.reason_phrase}")

                        # Check for Retry-After header
                        retry_after = self._get_retry_after(result)
                        if retry_after:
                            delay = min(retry_after, self.config.max_delay)
                        else:
                            delay = self.calculate_backoff(attempt)

                        if attempt < self.config.max_retries:
                            retry_delays.append(delay)
                            print(f"Retry {attempt + 1}/{self.config.max_retries} after {delay:.2f}s (HTTP {result.status_code})")
                            time.sleep(delay)
                            continue
                else:
                    # Non-HTTP response, consider it success
                    return RetryResult(
                        success=True,
                        result=result,
                        attempts=attempts,
                        total_time=time.time() - start_time,
                        retry_delays=retry_delays
                    )

            except httpx.HTTPError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = self.calculate_backoff(attempt)
                    retry_delays.append(delay)
                    print(f"Retry {attempt + 1}/{self.config.max_retries} after {delay:.2f}s ({type(e).__name__})")
                    time.sleep(delay)
                    continue

            except Exception as e:
                # Non-retryable error
                return RetryResult(
                    success=False,
                    error=e,
                    attempts=attempts,
                    total_time=time.time() - start_time,
                    retry_delays=retry_delays
                )

        # All retries exhausted
        return RetryResult(
            success=False,
            error=last_error or Exception("Max retries exceeded"),
            attempts=attempts,
            total_time=time.time() - start_time,
            retry_delays=retry_delays
        )

    def calculate_backoff(self, retry_num: int) -> float:
        """
        Calculate exponential backoff delay with optional jitter
        Formula: min(max_delay, base_delay * (exponential_base ^ retry_num))
        """
        # Exponential delay
        delay = self.config.base_delay * (self.config.exponential_base ** retry_num)

        # Cap at max delay
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            # Add random jitter of +/- 25%
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)  # Ensure positive

        return delay

    def should_retry_response(self, response: httpx.Response) -> bool:
        """
        Determine if HTTP response should be retried
        Returns True if retry is warranted
        """
        return response.status_code in self.config.retry_on_status

    def _get_retry_after(self, response: httpx.Response) -> Optional[float]:
        """
        Extract Retry-After header value
        Returns delay in seconds, or None if not present
        """
        retry_after = response.headers.get('Retry-After')
        if not retry_after:
            return None

        try:
            # Try parsing as seconds
            return float(retry_after)
        except ValueError:
            # Try parsing as HTTP date (not implemented for simplicity)
            return None


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    Opens circuit after threshold failures, preventing further requests
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        Raises CircuitBreakerOpenError if circuit is open
        """
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = 'HALF_OPEN'
                print(f"Circuit breaker entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. "
                    f"Too many failures ({self.failure_count}). "
                    f"Will retry after {self.timeout}s."
                )

        try:
            result = func(*args, **kwargs)

            # Success - reset if in HALF_OPEN
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                print("Circuit breaker reset to CLOSED state")

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                print(f"Circuit breaker tripped to OPEN state after {self.failure_count} failures")

            raise e

    def reset(self):
        """Manually reset circuit breaker"""
        self.state = 'CLOSED'
        self.failure_count = 0
        self.last_failure_time = None


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


# Decorator for easy retry application
def with_retry(config: RetryConfig = None):
    """
    Decorator to add retry logic to any function
    Usage:
        @with_retry(RetryConfig(max_retries=3))
        def my_function():
            ...
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            handler = RetryHandler(config)
            result = handler.execute_with_retry(func, *args, **kwargs)

            if result.success:
                return result.result
            else:
                raise result.error

        return wrapper
    return decorator
