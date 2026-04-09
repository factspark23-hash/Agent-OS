"""
Agent-OS Retry Utility
Provides retry decorator with exponential backoff, jitter, and fine-grained
exception control for resilient browser automation operations.

Key exports:
    RetryConfig     – dataclass holding retry parameters
    retry_async     – async decorator with exponential backoff + jitter
    retry           – simple async decorator (backward-compatible)
    retry_sync      – synchronous retry decorator
"""
import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Tuple, Type, Set

logger = logging.getLogger("agent-os.retry")


# ─── Exception Classification ─────────────────────────────────
# Exceptions that should NEVER be retried (permanent failures)
NON_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = ()
try:
    from playwright._impl._api_types import Error as PlaywrightError
    # Some Playwright errors are permanent
    NON_RETRYABLE_EXCEPTIONS = (PlaywrightError,)
except ImportError:
    pass

# Substrings in error messages that indicate a permanent (non-retryable) failure
PERMANENT_ERROR_MARKERS: Set[str] = {
    "404",
    "401",
    "403",
    "auth",
    "authentication",
    "unauthorized",
    "forbidden",
    "not found",
    "permission denied",
    "net::ERR_NAME_NOT_RESOLVED",
    "net::ERR_CONNECTION_REFUSED",
    "net::ERR_ABORTED",
}

# Substrings that indicate a transient failure worth retrying
RETRYABLE_ERROR_MARKERS: Set[str] = {
    "timeout",
    "timed out",
    "navigation failed",
    "element not found",
    "target closed",
    "page crashed",
    "net::ERR_CONNECTION_RESET",
    "net::ERR_TIMED_OUT",
    "net::ERR_INTERNET_DISCONNECTED",
    "net::ERR_NETWORK_CHANGED",
    "Execution context was destroyed",
    "Protocol error",
}


def _is_permanent_error(exc: Exception) -> bool:
    """Determine whether an exception represents a permanent failure.

    Returns True for auth errors, 404s, and other non-transient failures
    that should not be retried.
    """
    msg = str(exc).lower()
    for marker in PERMANENT_ERROR_MARKERS:
        if marker in msg:
            return True
    return False


def _is_retryable_error(exc: Exception) -> bool:
    """Determine whether an exception is worth retrying."""
    msg = str(exc).lower()
    for marker in RETRYABLE_ERROR_MARKERS:
        if marker in msg:
            return True
    # If it's not classified as permanent, default to retryable
    return not _is_permanent_error(exc)


# ─── RetryConfig ──────────────────────────────────────────────
@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries:          Total retry attempts after the first failure.
        backoff_base:         Base delay in seconds for exponential backoff.
        backoff_max:          Cap on the delay between retries.
        retry_on_exceptions:  Tuple of exception types that trigger a retry.
        skip_on_exceptions:   Tuple of exception types that are never retried.
        jitter:               Whether to add random jitter to backoff delays.
    """
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 30.0
    retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    skip_on_exceptions: Tuple[Type[Exception], ...] = ()
    jitter: bool = True

    def compute_delay(self, attempt: int) -> float:
        """Compute delay for a given retry attempt (0-indexed).

        Formula: min(backoff_base * (2 ** attempt) + random(0, 1), backoff_max)
        """
        base = self.backoff_base * (2 ** attempt)
        if self.jitter:
            base += random.uniform(0, 1)
        return min(base, self.backoff_max)


# ─── retry_async ──────────────────────────────────────────────
def retry_async(
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 30.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    skip_on: Tuple[Type[Exception], ...] = (),
):
    """Async retry decorator with exponential backoff and jitter.

    Uses the formula:
        delay = min(backoff_base * (2 ** attempt) + random(0, 1), backoff_max)

    Permanent failures (auth errors, 404, etc.) are detected by message
    content and never retried, regardless of the *retry_on* filter.

    Args:
        max_retries:   Number of retries after the initial failure.
        backoff_base:  Initial backoff in seconds.
        backoff_max:   Maximum backoff in seconds.
        retry_on:      Exception types that are eligible for retry.
        skip_on:       Exception types that are never retried.

    Returns:
        Decorated async function that retries on transient failures.
    """
    config = RetryConfig(
        max_retries=max_retries,
        backoff_base=backoff_base,
        backoff_max=backoff_max,
        retry_on_exceptions=retry_on,
        skip_on_exceptions=skip_on,
    )
    return _retry_async_decorator(config)


def _retry_async_decorator(config: RetryConfig) -> Callable:
    """Internal factory that builds the actual decorator from a RetryConfig."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.skip_on_exceptions as e:
                    # Explicitly non-retryable — raise immediately
                    logger.debug(f"{func.__name__}: skip_on exception raised: {e}")
                    raise
                except config.retry_on_exceptions as e:
                    # Check permanent error markers
                    if _is_permanent_error(e):
                        logger.info(
                            f"{func.__name__}: permanent error detected, not retrying: {e}"
                        )
                        raise

                    last_exception = e
                    if attempt == config.max_retries:
                        logger.error(
                            f"{func.__name__} failed after {config.max_retries + 1} "
                            f"attempts: {e}"
                        )
                        raise

                    delay = config.compute_delay(attempt)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{config.max_retries + 1} "
                        f"failed: {e}. Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)

            # Should not reach here, but safety net
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__}: retry loop exited unexpectedly")

        return wrapper
    return decorator


# ─── Backward-compatible retry decorator ──────────────────────
def retry(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Backward-compatible async retry decorator with exponential backoff.

    Preserves the original API used throughout the codebase.

    Args:
        max_retries:    Maximum number of retry attempts (default 3).
        base_delay:     Initial delay between retries in seconds (default 0.5).
        max_delay:      Maximum delay between retries in seconds (default 10.0).
        backoff_factor: Multiplier for delay after each retry (default 2.0).
        jitter:         Add random jitter to delays to avoid thundering herd.
        exceptions:     Tuple of exception types to catch and retry on.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception: Optional[Exception] = None
            delay = base_delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if _is_permanent_error(e):
                        logger.info(
                            f"{func.__name__}: permanent error, not retrying: {e}"
                        )
                        raise

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    wait_time = min(delay, max_delay)
                    if jitter:
                        wait_time = wait_time * (0.5 + random.random())

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} "
                        f"failed: {e}. Retrying in {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                    delay *= backoff_factor

            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__}: retry loop exited unexpectedly")

        return wrapper
    return decorator


def retry_sync(
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Synchronous retry decorator with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception: Optional[Exception] = None
            delay = base_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if _is_permanent_error(e):
                        logger.info(
                            f"{func.__name__}: permanent error, not retrying: {e}"
                        )
                        raise

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    wait_time = min(delay, max_delay)
                    if jitter:
                        wait_time = wait_time * (0.5 + random.random())

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} "
                        f"failed: {e}. Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                    delay *= backoff_factor

            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__}: retry loop exited unexpectedly")

        return wrapper
    return decorator
